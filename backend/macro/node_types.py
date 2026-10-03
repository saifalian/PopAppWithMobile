"""
All macro node type definitions and base classes.
Each node type knows how to execute itself given a MacroContext.
Node execution is synchronous — the executor calls node.execute()
and awaits the result before moving to the next node.
"""
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── NODE RESULT ──────────────────────────────────────────────────

@dataclass
class NodeResult:
    success:    bool
    output:     Any  = None
    confidence: float = 1.0
    error:      str  = None
    duration:   float = 0.0
    skip_next:  bool = False  # True = skip to after the next node
    branch:     str  = None  # "yes" | "no" for condition nodes


# ── BASE NODE ────────────────────────────────────────────────────

class BaseNode(ABC):
    """
    All macro nodes inherit from this.
    Must implement execute() and validate().
    """

    NODE_TYPE: str = "base"
    NODE_COLOR: str = "#475569"
    NODE_ICON:  str = "⚙"

    def __init__(self, node_id: str, config: dict):
        self.node_id = node_id
        self.config  = config
        self.timeout = config.get("timeout_seconds", 30)
        self.on_fail = config.get("on_fail", "stop")
        # "stop" | "skip" | "retry" | "fallback"
        self.retry_limit    = config.get("retry_limit", 3)
        self.fallback_node  = config.get("fallback_node_id")
        self.label          = config.get("label", self.NODE_TYPE)

    @abstractmethod
    def execute(self, context) -> NodeResult:
        """Execute this node. Read from context, write results back."""
        pass

    def validate(self) -> list:
        """
        Return list of validation error strings.
        Empty list = node is valid and ready.
        """
        return []

    def to_dict(self) -> dict:
        return {
            "id":       self.node_id,
            "type":     self.NODE_TYPE,
            "label":    self.label,
            "config":   self.config,
            "on_fail":  self.on_fail,
            "timeout":  self.timeout,
        }


# ═══════════════════════════════════════════════════════════════════
# MODEL NODES — Run trained ML models
# ═══════════════════════════════════════════════════════════════════

class ModelNode(BaseNode):
    """
    Runs a trained ModelFactory ML model.
    Captures screen region, runs inference, executes predicted action.
    Writes confidence and output to context.

    This is the most important node type.
    """
    NODE_TYPE  = "model"
    NODE_COLOR = "#10b981"
    NODE_ICON  = "⊞"

    def execute(self, context) -> NodeResult:
        from backend.core.model_factory import load_model
        from backend.vision.screen_capture import capture_region
        from backend.vision.preprocessor import preprocess_single
        from backend.desktop.action_executor import execute_action
        import numpy as np
        import tensorflow as tf

        start = time.time()

        model_name    = self.config.get("model_name")
        output_type   = self.config.get("output_type", "yes_no")
        screen_region = self.config.get("screen_region")
        conf_threshold = self.config.get(
            "confidence_threshold",
            context.get("pipeline.confidence_threshold", 0.65)
        )
        device_string = context.get(
            "pipeline.device_string", "/CPU:0"
        )

        if not model_name:
            return NodeResult(
                success=False, error="No model_name configured"
            )

        try:
            # Load model
            model_path = str(
                Path("models") / model_name / "best" / "model"
            )
            model = load_model(model_path, device_string)

            # Capture screen
            screenshot = capture_region(screen_region)
            if screenshot is None:
                return NodeResult(
                    success=False,
                    error="Screen capture failed",
                    duration=time.time() - start
                )

            # Inference on GPU/CPU
            img_tensor = preprocess_single(screenshot, device_string)
            with tf.device(device_string):
                prediction = model(img_tensor, training=False)
                pred_np    = prediction.numpy()[0]

            confidence = float(np.max(pred_np))

            # Write confidence to context
            context.set_node_confidence(self.node_id, confidence)
            context.set(
                f"results.model_confidence.{model_name}", confidence
            )

            # Decide action
            action = None
            executed = False

            if confidence >= conf_threshold:
                action = self._pred_to_action(
                    pred_np, output_type,
                    screen_region, context
                )
                if action:
                    # Apply humanization if configured
                    humanize = context.get("pipeline.humanize")
                    execute_action(action, humanize)
                    executed = True

            # Store output in context
            output = {
                "prediction":  pred_np.tolist(),
                "confidence":  confidence,
                "action":      action,
                "executed":    executed,
                "model_name":  model_name,
            }
            context.set_node_output(self.node_id, output)
            context.set_node_success(self.node_id, executed)

            # Special handling per output type
            if output_type == "yes_no":
                import numpy as np
                decision = bool(np.argmax(pred_np) == 0)
                context.set(f"{self.node_id}.decision", decision)

            elif output_type == "click_coords" and executed:
                context.set(
                    f"{self.node_id}.click_pos",
                    {"x": action.get("x"), "y": action.get("y")}
                )

            return NodeResult(
                success=executed,
                output=output,
                confidence=confidence,
                duration=time.time() - start
            )

        except Exception as e:
            logger.error(f"ModelNode {model_name} error: {e}")
            return NodeResult(
                success=False,
                error=str(e),
                duration=time.time() - start
            )

    def _pred_to_action(
        self, pred, output_type, region, context
    ) -> Optional[dict]:
        import numpy as np

        if output_type == "yes_no":
            idx = int(np.argmax(pred))
            return {
                "type": "decision",
                "value": idx == 0,
                "confidence": float(pred[idx])
            }

        elif output_type == "click_coords":
            x_n, y_n = float(pred[0]), float(pred[1])
            if region:
                x = int(
                    region['x1'] + x_n * (region['x2'] - region['x1'])
                )
                y = int(
                    region['y1'] + y_n * (region['y2'] - region['y1'])
                )
            else:
                import mss
                with mss.mss() as s:
                    m = s.monitors[1]
                    x = int(x_n * m['width'])
                    y = int(y_n * m['height'])
            return {"type": "click", "x": x, "y": y}

        elif output_type in ("numeric", "scroll_amount"):
            return {"type": "numeric", "value": float(pred[0])}

        return None

    def validate(self) -> list:
        errors = []
        if not self.config.get("model_name"):
            errors.append("model_name is required")
        model_path = Path("models") / self.config.get(
            "model_name", ""
        ) / "best" / "model"
        if not model_path.exists():
            errors.append(
                f"Model not trained yet: {self.config.get('model_name')}"
            )
        return errors


# ═══════════════════════════════════════════════════════════════════
# VISION NODES
# ═══════════════════════════════════════════════════════════════════

class WaitForImageNode(BaseNode):
    """
    Wait until a template image appears on screen.
    Uses OpenCV template matching.
    """
    NODE_TYPE  = "wait_for_image"
    NODE_COLOR = "#06b6d4"
    NODE_ICON  = "👁"

    def execute(self, context) -> NodeResult:
        import cv2
        import numpy as np
        from backend.vision.screen_capture import capture_full

        start         = time.time()
        template_path = self.config.get("template_path")
        threshold     = self.config.get("match_threshold", 0.8)
        timeout       = self.config.get("timeout_seconds", 30)
        check_every   = self.config.get("check_every_seconds", 0.5)

        if not template_path or not Path(template_path).exists():
            return NodeResult(
                success=False,
                error=f"Template not found: {template_path}"
            )

        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template is None:
            return NodeResult(
                success=False, error="Could not load template image"
            )

        deadline = time.time() + timeout
        while time.time() < deadline:
            screenshot = capture_full()
            if screenshot is None:
                time.sleep(check_every)
                continue

            gray   = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            result = cv2.matchTemplate(
                gray, template, cv2.TM_CCOEFF_NORMED
            )
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= threshold:
                match_center = (
                    max_loc[0] + template.shape[1] // 2,
                    max_loc[1] + template.shape[0] // 2
                )
                context.set_node_output(self.node_id, {
                    "found":      True,
                    "confidence": float(max_val),
                    "location":   max_loc,
                    "center":     match_center,
                })
                context.set_node_success(self.node_id, True)
                return NodeResult(
                    success=True,
                    output={"location": max_loc, "center": match_center},
                    confidence=float(max_val),
                    duration=time.time() - start
                )

            time.sleep(check_every)

        context.set_node_success(self.node_id, False,
                                  "Timeout waiting for image")
        return NodeResult(
            success=False,
            error=f"Image not found within {timeout}s",
            duration=time.time() - start
        )

    def validate(self) -> list:
        errors = []
        path = self.config.get("template_path")
        if not path:
            errors.append("template_path is required")
        elif not Path(path).exists():
            errors.append(f"Template file not found: {path}")
        return errors


class ExtractTextNode(BaseNode):
    """
    OCR text extraction from a screen region.
    Stores result in context for use by later nodes.
    """
    NODE_TYPE  = "extract_text"
    NODE_COLOR = "#06b6d4"
    NODE_ICON  = "📝"

    def execute(self, context) -> NodeResult:
        from backend.vision.screen_capture import capture_region
        from backend.vision.ocr_reader import read_popup

        start  = time.time()
        region = self.config.get("screen_region")
        store_as = self.config.get("store_as", f"{self.node_id}.text")

        screenshot = capture_region(region)
        if screenshot is None:
            return NodeResult(
                success=False, error="Screen capture failed",
                duration=time.time() - start
            )

        result = read_popup(screenshot)

        # Store parsed values in context
        context.set_node_output(self.node_id, result)
        context.set_node_success(self.node_id, result.get("success", False))
        context.set(store_as, result.get("raw_text", ""))

        if result.get("price"):
            context.set("results.price", result["price"])
        if result.get("usd"):
            context.set("results.usd_value", result["usd"])
        if result.get("value_str"):
            context.set("results.value_str", result["value_str"])

        return NodeResult(
            success=result.get("success", False),
            output=result,
            duration=time.time() - start
        )


class DetectClustersNode(BaseNode):
    """
    Run OpenCV heatmap cluster detection on chart region.
    Stores cluster list in context.results.clusters.
    """
    NODE_TYPE  = "detect_clusters"
    NODE_COLOR = "#06b6d4"
    NODE_ICON  = "🔥"

    def execute(self, context) -> NodeResult:
        from backend.vision.screen_capture import capture_region
        from backend.vision.cluster_detector import detect_clusters

        start    = time.time()
        region   = self.config.get("screen_region")
        min_area = self.config.get("min_area", 200)

        screenshot = capture_region(region)
        if screenshot is None:
            return NodeResult(
                success=False, error="Screen capture failed"
            )

        clusters = detect_clusters(screenshot, min_area=min_area)
        context.set_node_output(self.node_id, clusters)
        context.set_node_success(self.node_id, len(clusters) > 0)
        context.set("results.clusters", clusters)

        return NodeResult(
            success=len(clusters) > 0,
            output=clusters,
            duration=time.time() - start
        )


class TakeScreenshotNode(BaseNode):
    """
    Capture and save a screenshot at this point in the pipeline.
    """
    NODE_TYPE  = "screenshot"
    NODE_COLOR = "#06b6d4"
    NODE_ICON  = "📷"

    def execute(self, context) -> NodeResult:
        import cv2
        from backend.vision.screen_capture import capture_region, capture_full
        from datetime import datetime

        start  = time.time()
        region = self.config.get("screen_region")
        save_to = self.config.get("save_to", "data/screenshots/")

        Path(save_to).mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = str(Path(save_to) / f"screenshot_{ts}.png")

        img = capture_region(region) if region else capture_full()
        if img is None:
            return NodeResult(success=False, error="Capture failed")

        cv2.imwrite(path, img)
        context.set_node_output(self.node_id, {"path": path})
        context.set_node_success(self.node_id, True)

        return NodeResult(
            success=True, output={"path": path},
            duration=time.time() - start
        )


# ═══════════════════════════════════════════════════════════════════
# DESKTOP ACTION NODES
# ═══════════════════════════════════════════════════════════════════

class ClickNode(BaseNode):
    """Click, double-click, or right-click at coordinates."""
    NODE_TYPE  = "click"
    NODE_COLOR = "#8b5cf6"
    NODE_ICON  = "👆"

    def execute(self, context) -> NodeResult:
        from backend.desktop.action_executor import execute_action

        start     = time.time()
        click_type = self.config.get("click_type", "click")
        humanize  = context.get("pipeline.humanize")

        # Coordinates can come from config or from context
        x = self.config.get("x")
        y = self.config.get("y")

        # Dynamic coord from previous node
        coord_from = self.config.get("coords_from_node")
        if coord_from:
            pos = context.get(f"{coord_from}.click_pos")
            if pos:
                x, y = pos.get("x", x), pos.get("y", y)

        # Or from iteration item
        if self.config.get("use_iteration_item"):
            item = context.get_iteration_item()
            if item and isinstance(item, dict):
                x = item.get("cx", x) or item.get("x", x)
                y = item.get("cy", y) or item.get("y", y)

        if x is None or y is None:
            return NodeResult(
                success=False, error="No coordinates available"
            )

        ok = execute_action(
            {"type": click_type, "x": int(x), "y": int(y)},
            humanize
        )

        context.set_node_success(self.node_id, ok)
        return NodeResult(
            success=ok,
            output={"x": x, "y": y},
            duration=time.time() - start
        )

    def validate(self) -> list:
        errors = []
        if (self.config.get("x") is None and
                not self.config.get("coords_from_node") and
                not self.config.get("use_iteration_item")):
            errors.append("Coordinates required: set x/y or coords_from_node")
        return errors


class DragScrollNode(BaseNode):
    """Drag from one point to another, or scroll."""
    NODE_TYPE  = "drag_scroll"
    NODE_COLOR = "#8b5cf6"
    NODE_ICON  = "↔"

    def execute(self, context) -> NodeResult:
        from backend.desktop.action_executor import execute_action

        start    = time.time()
        action_t = self.config.get("action_type", "scroll")
        humanize = context.get("pipeline.humanize")

        if action_t == "scroll":
            ok = execute_action(
                {"type": "scroll",
                 "amount": self.config.get("amount", -3),
                 "x": self.config.get("x"),
                 "y": self.config.get("y")},
                humanize
            )
        else:  # drag
            ok = execute_action(
                {"type": "drag",
                 "x1": self.config.get("x1", 0),
                 "y1": self.config.get("y1", 0),
                 "x2": self.config.get("x2", 100),
                 "y2": self.config.get("y2", 100),
                 "duration": self.config.get("duration", 0.3)},
                humanize
            )

        context.set_node_success(self.node_id, ok)
        return NodeResult(success=ok, duration=time.time() - start)


class TypewriteNode(BaseNode):
    """Type text or press a key/hotkey."""
    NODE_TYPE  = "typewrite"
    NODE_COLOR = "#8b5cf6"
    NODE_ICON  = "⌨"

    def execute(self, context) -> NodeResult:
        from backend.desktop.action_executor import execute_action

        start    = time.time()
        action_t = self.config.get("action_type", "type")
        humanize = context.get("pipeline.humanize")

        text = self.config.get("text", "")

        # Dynamic text from context
        text_from = self.config.get("text_from_context")
        if text_from:
            text = str(context.get(text_from, text))

        if action_t == "key":
            ok = execute_action(
                {"type": "key",
                 "key": self.config.get("key", "Enter")},
                humanize
            )
        else:
            ok = execute_action(
                {"type": "type", "text": text}, humanize
            )

        context.set_node_success(self.node_id, ok)
        return NodeResult(success=ok, duration=time.time() - start)


# ═══════════════════════════════════════════════════════════════════
# LOGIC & FLOW NODES
# ═══════════════════════════════════════════════════════════════════

class WaitNode(BaseNode):
    """Static delay."""
    NODE_TYPE  = "wait"
    NODE_COLOR = "#06b6d4"
    NODE_ICON  = "⏱"

    def execute(self, context) -> NodeResult:
        start   = time.time()
        seconds = float(self.config.get("seconds", 1.0))
        time.sleep(seconds)
        context.set_node_success(self.node_id, True)
        return NodeResult(success=True, duration=time.time() - start)


class WaitForConditionNode(BaseNode):
    """
    Wait until a context condition becomes true.
    Polls at interval up to timeout.
    """
    NODE_TYPE  = "wait_condition"
    NODE_COLOR = "#06b6d4"
    NODE_ICON  = "⏳"

    def execute(self, context) -> NodeResult:
        start       = time.time()
        condition   = self.config.get("condition", "True")
        timeout     = self.config.get("timeout_seconds", 30)
        check_every = self.config.get("check_every_seconds", 0.5)
        deadline    = time.time() + timeout

        while time.time() < deadline:
            if context.evaluate_condition(condition):
                context.set_node_success(self.node_id, True)
                return NodeResult(
                    success=True, duration=time.time() - start
                )
            time.sleep(check_every)

        context.set_node_success(
            self.node_id, False, f"Timeout: condition never met"
        )
        return NodeResult(
            success=False,
            error=f"Condition '{condition}' not met within {timeout}s",
            duration=time.time() - start
        )


class ConditionNode(BaseNode):
    """
    Conditional branch node.
    Evaluates a condition against context.
    Routes to YES path or NO path.
    """
    NODE_TYPE  = "condition"
    NODE_COLOR = "#f59e0b"
    NODE_ICON  = "◆"

    def execute(self, context) -> NodeResult:
        start     = time.time()
        condition = self.config.get("condition", "True")
        result    = context.evaluate_condition(condition)

        context.set_node_output(self.node_id, {"branch": "yes" if result else "no"})
        context.set_node_success(self.node_id, True)

        return NodeResult(
            success=True,
            output={"result": result},
            branch="yes" if result else "no",
            duration=time.time() - start
        )


class ConfidenceGateNode(BaseNode):
    """
    Only proceed if a previous model's confidence was above threshold.
    Routes to fallback if below.
    """
    NODE_TYPE  = "confidence_gate"
    NODE_COLOR = "#f59e0b"
    NODE_ICON  = "🛡"

    def execute(self, context) -> NodeResult:
        start         = time.time()
        source_node   = self.config.get("source_node_id")
        threshold     = float(self.config.get("threshold", 0.70))

        confidence = context.get_node_confidence(source_node) \
                     if source_node else 0.0

        passed = confidence >= threshold
        context.set_node_success(self.node_id, passed)

        return NodeResult(
            success=passed,
            output={"confidence": confidence, "threshold": threshold},
            branch="yes" if passed else "no",
            duration=time.time() - start
        )


class LoopNode(BaseNode):
    """
    Repeat a set of child nodes N times, or until condition is true.
    """
    NODE_TYPE  = "loop"
    NODE_COLOR = "#3b82f6"
    NODE_ICON  = "↺"

    def __init__(self, node_id: str, config: dict,
                 child_nodes: list = None):
        super().__init__(node_id, config)
        self.child_nodes = child_nodes or []

    def execute(self, context) -> NodeResult:
        start     = time.time()
        loop_type = self.config.get("loop_type", "repeat")
        max_iter  = int(self.config.get("max_iterations", 5))
        condition = self.config.get("until_condition")

        results     = []
        iteration   = 0
        success     = False

        from backend.macro.executor import execute_node_list

        while iteration < max_iter:
            iteration += 1
            context.set("loop.current_iteration", iteration)

            if loop_type == "until" and condition:
                if context.evaluate_condition(condition):
                    success = True
                    break

            # Run child nodes
            child_results = execute_node_list(
                self.child_nodes, context
            )
            results.append(child_results)

            if loop_type == "repeat" and iteration >= max_iter:
                success = True
                break

        context.set_node_output(self.node_id, {
            "iterations": iteration,
            "results":    results,
        })
        context.set_node_success(self.node_id, success)

        return NodeResult(
            success=success,
            output={"iterations": iteration},
            duration=time.time() - start
        )


class ForEachNode(BaseNode):
    """
    Iterate over a list from context.
    For each item, runs child nodes with item available via
    context.get_iteration_item().
    """
    NODE_TYPE  = "for_each"
    NODE_COLOR = "#3b82f6"
    NODE_ICON  = "⟳"

    def __init__(self, node_id: str, config: dict,
                 child_nodes: list = None):
        super().__init__(node_id, config)
        self.child_nodes = child_nodes or []

    def execute(self, context) -> NodeResult:
        start      = time.time()
        source_key = self.config.get("source_key", "results.clusters")
        max_items  = self.config.get("max_items")
        on_item_fail = self.config.get("on_item_fail", "skip")

        items = context.get(source_key, [])
        if not isinstance(items, list):
            return NodeResult(
                success=False,
                error=f"Source '{source_key}' is not a list"
            )

        if max_items:
            items = items[:int(max_items)]

        from backend.macro.executor import execute_node_list

        results   = []
        succeeded = 0

        for i, item in enumerate(items):
            context.set("iteration.index",        i)
            context.set("iteration.total",        len(items))
            context.set("iteration.is_last",      i == len(items) - 1)
            context.set_iteration_item(item)

            child_results = execute_node_list(self.child_nodes, context)
            iteration_success = all(
                r.get("success", False) for r in child_results
            )

            if iteration_success:
                succeeded += 1
                context.append_iteration_result({
                    "item":    item,
                    "results": child_results,
                    "success": True,
                })
            else:
                if on_item_fail == "stop":
                    break
                # "skip" continues to next item

            results.append({"index": i, "success": iteration_success})

        all_ok = succeeded == len(items) if items else True
        context.set_node_output(self.node_id, {
            "total":     len(items),
            "succeeded": succeeded,
            "results":   results,
        })
        context.set_node_success(self.node_id, all_ok)

        return NodeResult(
            success=all_ok,
            output={"total": len(items), "succeeded": succeeded},
            duration=time.time() - start
        )


class ParallelNode(BaseNode):
    """
    Run two or more branches simultaneously using threads.
    Waits for ALL branches to complete before proceeding.
    """
    NODE_TYPE  = "parallel"
    NODE_COLOR = "#8b5cf6"
    NODE_ICON  = "⟦⟧"

    def __init__(self, node_id: str, config: dict,
                 branches: dict = None):
        super().__init__(node_id, config)
        self.branches = branches or {}
        # {"branch_a": [node_list], "branch_b": [node_list]}

    def execute(self, context) -> NodeResult:
        import threading
        import copy

        start         = time.time()
        wait_for      = self.config.get("wait_for", "all")
        # "all" or "first"
        timeout       = self.config.get("timeout_seconds", 60)

        from backend.macro.executor import execute_node_list

        branch_results = {}
        threads = []
        lock    = threading.Lock()

        def run_branch(name, nodes, ctx_snapshot):
            branch_ctx = MacroContext(ctx_snapshot)
            results    = execute_node_list(nodes, branch_ctx)
            with lock:
                branch_results[name] = {
                    "results":     results,
                    "ctx_snapshot": branch_ctx.snapshot(),
                }

        ctx_snapshot = context.snapshot()

        for branch_name, branch_nodes in self.branches.items():
            t = threading.Thread(
                target=run_branch,
                args=(branch_name, branch_nodes, ctx_snapshot),
                daemon=True
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=timeout)

        # Merge branch outputs back to main context
        for branch_name, result in branch_results.items():
            context.set(
                f"{self.node_id}.{branch_name}",
                result["results"]
            )

        all_success = all(
            all(r.get("success", False)
                for r in v["results"])
            for v in branch_results.values()
        )

        context.set_node_output(self.node_id, branch_results)
        context.set_node_success(self.node_id, all_success)

        return NodeResult(
            success=all_success,
            output={"branches": list(branch_results.keys())},
            duration=time.time() - start
        )


# ═══════════════════════════════════════════════════════════════════
# SYSTEM NODES
# ═══════════════════════════════════════════════════════════════════

class LaunchAppNode(BaseNode):
    """Launch an application or bring its window to front."""
    NODE_TYPE  = "launch_app"
    NODE_COLOR = "#475569"
    NODE_ICON  = "🚀"

    def execute(self, context) -> NodeResult:
        from backend.desktop.window_controller import (
            focus_coinglass, launch, find_window, bring_to_front
        )

        start      = time.time()
        app_name   = self.config.get("app_name", "Coinglass")
        exe_path   = self.config.get("exe_path")
        action     = self.config.get("action", "focus_or_launch")

        if action == "focus_or_launch":
            from backend.desktop.window_controller import is_running
            if is_running(app_name):
                ok = focus_coinglass() if app_name == "Coinglass" \
                     else bring_to_front(find_window(app_name))
            else:
                if exe_path:
                    ok = launch(exe_path)
                    time.sleep(3.0)  # wait for app to open
                else:
                    ok = False
        elif action == "focus":
            ok = focus_coinglass() if app_name == "Coinglass" \
                 else bring_to_front(find_window(app_name))
        elif action == "launch":
            ok = launch(exe_path) if exe_path else False
            if ok:
                time.sleep(3.0)
        else:
            ok = False

        context.set_node_success(self.node_id, ok)
        return NodeResult(success=ok, duration=time.time() - start)


class SaveJsonNode(BaseNode):
    """
    Assemble and save the final output JSON.
    This is typically the last node in the Coinglass pipeline.
    """
    NODE_TYPE  = "save_json"
    NODE_COLOR = "#475569"
    NODE_ICON  = "💾"

    def execute(self, context) -> NodeResult:
        import json as json_mod

        start    = time.time()
        pair     = context.get("pipeline.pair", "UNKNOWN")
        tf_str   = context.get("pipeline.timeframe", "?")
        out_path = self.config.get("output_path",
                                   f"data/{pair}_{tf_str}.json")

        output = context.build_output_json(pair, tf_str)

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json_mod.dump(output, f, indent=2)

        context.set_node_output(self.node_id, {
            "path": out_path, "data": output
        })
        context.set_node_success(self.node_id, True)

        return NodeResult(
            success=True,
            output={"path": out_path},
            duration=time.time() - start
        )

    def validate(self) -> list:
        return []


class LogMessageNode(BaseNode):
    """Write a message to log. Supports context variable substitution."""
    NODE_TYPE  = "log_message"
    NODE_COLOR = "#475569"
    NODE_ICON  = "📋"

    def execute(self, context) -> NodeResult:
        start   = time.time()
        message = self.config.get("message", "Log node")

        # Simple template substitution {key}
        for key, val in context.dump().items():
            message = message.replace(f"{{{key}}}", str(val))

        level = self.config.get("level", "info")
        getattr(logger, level, logger.info)(f"[MacroLog] {message}")

        context.set_node_success(self.node_id, True)
        return NodeResult(success=True, duration=time.time() - start)


class RunSequenceNode(BaseNode):
    """Run a saved action sequence from the Actions tab."""
    NODE_TYPE  = "run_sequence"
    NODE_COLOR = "#475569"
    NODE_ICON  = "▶"

    def execute(self, context) -> NodeResult:
        from backend.desktop.action_executor import execute_sequence
        from backend.database.db import SessionLocal
        from backend.database.models import ActionSequence

        start       = time.time()
        sequence_id = self.config.get("sequence_id")
        humanize    = context.get("pipeline.humanize")

        if not sequence_id:
            return NodeResult(
                success=False, error="No sequence_id configured"
            )

        db  = SessionLocal()
        seq = db.query(ActionSequence).filter(
            ActionSequence.id == sequence_id
        ).first()
        db.close()

        if not seq:
            return NodeResult(
                success=False,
                error=f"Sequence {sequence_id} not found"
            )

        ok = execute_sequence(seq.steps, humanize)
        context.set_node_success(self.node_id, ok)

        return NodeResult(success=ok, duration=time.time() - start)


class ExecutePythonNode(BaseNode):
    """
    Execute a custom Python script snippet.
    Has access to context object.
    Use sparingly — power user feature.
    """
    NODE_TYPE  = "execute_python"
    NODE_COLOR = "#475569"
    NODE_ICON  = "🐍"

    def execute(self, context) -> NodeResult:
        start  = time.time()
        script = self.config.get("script", "")

        if not script.strip():
            return NodeResult(success=True, duration=0)

        safe_globals = {
            "__builtins__": {
                "print": print, "len": len, "str": str,
                "int": int, "float": float, "list": list,
                "dict": dict, "bool": bool, "range": range,
                "enumerate": enumerate, "zip": zip,
                "min": min, "max": max, "sum": sum,
                "round": round, "abs": abs,
            },
            "context": context,
            "time": time,
            "logger": logger,
        }

        try:
            exec(script, safe_globals)
            context.set_node_success(self.node_id, True)
            return NodeResult(
                success=True, duration=time.time() - start
            )
        except Exception as e:
            logger.error(f"Python node error: {e}")
            return NodeResult(
                success=False, error=str(e),
                duration=time.time() - start
            )


class StopPipelineNode(BaseNode):
    """Gracefully stop the pipeline with a message."""
    NODE_TYPE  = "stop_pipeline"
    NODE_COLOR = "#ef4444"
    NODE_ICON  = "⏹"

    def execute(self, context) -> NodeResult:
        message = self.config.get("message", "Pipeline stopped by node")
        context.set("pipeline.stop_reason", message)
        context.set("pipeline.stopped_early", True)
        logger.info(f"Pipeline stopped: {message}")
        return NodeResult(
            success=True,
            output={"message": message},
            skip_next=True
        )


# ── NODE REGISTRY ────────────────────────────────────────────────

NODE_REGISTRY: dict[str, type] = {
    # Model
    "model":            ModelNode,
    # Vision
    "wait_for_image":   WaitForImageNode,
    "extract_text":     ExtractTextNode,
    "detect_clusters":  DetectClustersNode,
    "screenshot":       TakeScreenshotNode,
    # Desktop actions
    "click":            ClickNode,
    "drag_scroll":      DragScrollNode,
    "typewrite":        TypewriteNode,
    # Logic
    "wait":             WaitNode,
    "wait_condition":   WaitForConditionNode,
    "condition":        ConditionNode,
    "confidence_gate":  ConfidenceGateNode,
    "loop":             LoopNode,
    "for_each":         ForEachNode,
    "parallel":         ParallelNode,
    # System
    "launch_app":       LaunchAppNode,
    "save_json":        SaveJsonNode,
    "log_message":      LogMessageNode,
    "run_sequence":     RunSequenceNode,
    "execute_python":   ExecutePythonNode,
    "stop_pipeline":    StopPipelineNode,
}


def build_node(node_dict: dict, child_nodes=None,
               branches=None) -> BaseNode:
    """Factory function — builds correct node from dict."""
    node_type = node_dict.get("type", "log_message")
    node_id   = node_dict.get("id", f"node_{id(node_dict)}")
    config    = node_dict.get("config", {})
    config["label"]   = node_dict.get("label", node_type)
    config["on_fail"] = node_dict.get("on_fail", "stop")
    config["timeout_seconds"] = node_dict.get("timeout", 30)

    cls = NODE_REGISTRY.get(node_type, LogMessageNode)

    if node_type in ("loop", "for_each"):
        return cls(node_id, config, child_nodes or [])
    elif node_type == "parallel":
        return cls(node_id, config, branches or {})
    else:
        return cls(node_id, config)
