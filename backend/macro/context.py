"""
Macro execution context.
Carries data between nodes during pipeline execution.
Every node reads from context and writes results back to context.
This is how Step 1 output becomes Step 3 input.
"""
import copy
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MacroContext:
    """
    Shared state that flows through the entire macro execution.

    Key naming convention:
        {node_id}.output          raw output of a node
        {node_id}.confidence      model confidence score
        {node_id}.success         bool — did node succeed
        {node_id}.duration        seconds taken
        {node_id}.error           error message if failed

    Special keys:
        pipeline.pair             trading pair e.g. "XRPUSDT"
        pipeline.timeframe        timeframe e.g. "15m"
        pipeline.start_time       epoch time when pipeline started
        pipeline.attempt          current attempt number
        results.clusters          list of detected clusters
        results.ocr_text          extracted OCR text
        results.price             extracted price float
        results.usd_value         extracted dollar value float
        results.json_output       final assembled output dict
    """

    def __init__(self, initial: dict = None):
        self._data: dict = {}
        self._history: list = []  # list of (key, old_val, new_val) for debugging

        if initial:
            self._data.update(initial)

    # ── BASIC GET / SET ──────────────────────────────────────────

    def set(self, key: str, value: Any):
        old = self._data.get(key)
        self._data[key] = value
        self._history.append((key, old, value))
        logger.debug(f"Context set: {key} = {repr(value)[:80]}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._data

    def delete(self, key: str):
        self._data.pop(key, None)

    # ── NODE-SCOPED HELPERS ───────────────────────────────────────

    def set_node_output(self, node_id: str, output: Any):
        self.set(f"{node_id}.output", output)

    def get_node_output(self, node_id: str, default: Any = None) -> Any:
        return self.get(f"{node_id}.output", default)

    def set_node_success(self, node_id: str, success: bool,
                         error: str = None):
        self.set(f"{node_id}.success", success)
        if error:
            self.set(f"{node_id}.error", error)

    def node_succeeded(self, node_id: str) -> bool:
        return bool(self.get(f"{node_id}.success", False))

    def set_node_confidence(self, node_id: str, confidence: float):
        self.set(f"{node_id}.confidence", confidence)

    def get_node_confidence(self, node_id: str) -> float:
        return float(self.get(f"{node_id}.confidence", 0.0))

    # ── RESULTS HELPERS ───────────────────────────────────────────

    def add_cluster(self, cluster: dict):
        clusters = self.get("results.clusters", [])
        clusters.append(cluster)
        self.set("results.clusters", clusters)

    def get_clusters(self) -> list:
        return self.get("results.clusters", [])

    def set_ocr_result(self, price: float = None,
                       usd: float = None,
                       value_str: str = None,
                       raw_text: str = None):
        if price is not None:
            self.set("results.price", price)
        if usd is not None:
            self.set("results.usd_value", usd)
        if value_str is not None:
            self.set("results.value_str", value_str)
        if raw_text is not None:
            self.set("results.raw_text", raw_text)

    # ── ITERATION SUPPORT (For Each node) ────────────────────────

    def set_iteration_item(self, item: Any):
        """Set the current item in a for-each loop."""
        self.set("iteration.current_item", item)

    def get_iteration_item(self) -> Any:
        return self.get("iteration.current_item")

    def set_iteration_results(self, results: list):
        self.set("iteration.results", results)

    def append_iteration_result(self, result: Any):
        results = self.get("iteration.results", [])
        results.append(result)
        self.set("iteration.results", results)

    # ── CONDITION EVALUATION ──────────────────────────────────────

    def evaluate_condition(self, condition: str) -> bool:
        """
        Safely evaluate a condition string against context data.

        Example conditions:
            "results.clusters|len > 0"
            "node_abc123.confidence > 0.8"
            "results.usd_value > 1000000"
            "node_xyz.success == True"
        """
        if not condition or not condition.strip():
            return True

        # Build evaluation namespace
        flat = {}
        for key, val in self._data.items():
            # Replace dots with underscores for safe eval
            safe_key = key.replace(".", "_").replace("-", "_")
            flat[safe_key] = val
            # Also support pipe syntax: key|len
            if isinstance(val, (list, dict, str)):
                flat[f"{safe_key}_len"] = len(val)

        # Direct key access support
        flat["ctx"] = self._data
        flat["clusters"] = self.get("results.clusters", [])
        flat["cluster_count"] = len(self.get("results.clusters", []))
        flat["price"] = self.get("results.price", 0)
        flat["usd_value"] = self.get("results.usd_value", 0)

        # Normalize pipe syntax
        cond = condition.replace("|len", "_len").replace(".", "_")

        try:
            result = bool(eval(cond, {"__builtins__": {}}, flat))
            logger.debug(f"Condition '{condition}' → {result}")
            return result
        except Exception as e:
            logger.warning(f"Condition eval error '{condition}': {e}")
            return False

    # ── SNAPSHOT / RESTORE ────────────────────────────────────────

    def snapshot(self) -> dict:
        return copy.deepcopy(self._data)

    def restore(self, snapshot: dict):
        self._data = copy.deepcopy(snapshot)

    # ── FINAL OUTPUT ASSEMBLY ─────────────────────────────────────

    def build_output_json(self, pair: str = None,
                          timeframe: str = None) -> dict:
        """
        Assemble the final output JSON from all collected results.
        This is the JSON that gets saved to data/{PAIR}_{TF}.json
        """
        import time
        from datetime import datetime, timezone

        clusters = self.get("results.clusters", [])
        short_liq = [
            c for c in clusters if c.get("side") == "short"
        ]
        long_liq = [
            c for c in clusters if c.get("side") == "long"
        ]

        strongest = None
        if clusters:
            strongest = max(clusters, key=lambda c: c.get("usd", 0))

        output = {
            "pair":             pair or self.get("pipeline.pair", "UNKNOWN"),
            "timeframe":        timeframe or self.get("pipeline.timeframe", "?"),
            "current_price":    self.get("results.price"),
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(
                time.time() - self.get("pipeline.start_time", time.time()), 2
            ),
            "short_liquidations": short_liq,
            "long_liquidations":  long_liq,
            "strongest_wall": {
                "side":  strongest.get("side") if strongest else None,
                "price": strongest.get("price") if strongest else None,
                "usd":   strongest.get("usd")   if strongest else None,
            } if strongest else None,
            "model_confidence": self.get("results.model_confidence", {}),
            "cluster_count":    len(clusters),
        }

        self.set("results.json_output", output)
        return output

    def dump(self) -> dict:
        """Return full context for debugging."""
        return copy.deepcopy(self._data)
