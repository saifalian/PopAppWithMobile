"""
Core logic for executing a list of macro nodes sequentially.
Handles branching (yes/no), looping, early exits, retries,
and fallbacks.

The Executor uses the Context to pass state between nodes.
"""
import logging
import time
from typing import List, Dict, Any, Optional

from backend.macro.context import MacroContext
from backend.macro.node_types import build_node

logger = logging.getLogger(__name__)


def build_pipeline_from_dict(raw_nodes: List[Dict]) -> List[Any]:
    """
    Convert raw UI JSON dictionaries into instantiated Node objects.
    Recursively builds children for Loop, ForEach, and Parallel nodes.
    """
    pipeline = []
    for num, rnd in enumerate(raw_nodes):
        node_id = rnd.get("id", f"node_{num}")
        n_type  = rnd.get("type", "base")

        if n_type in ("loop", "for_each"):
            children = build_pipeline_from_dict(
                rnd.get("child_nodes", [])
            )
            pipeline.append(build_node(rnd, children))
        elif n_type == "parallel":
            raw_branches = rnd.get("branches", {})
            built_branches = {}
            for b_name, b_nodes in raw_branches.items():
                built_branches[b_name] = build_pipeline_from_dict(b_nodes)
            pipeline.append(build_node(rnd, branches=built_branches))
        else:
            pipeline.append(build_node(rnd))

    return pipeline


def execute_macro(
    nodes: List[Dict],
    initial_context: Dict[str, Any] = None,
    dry_run: bool = False
) -> MacroContext:
    """
    Main entry point for running a complete macro.
    Nodes is the raw JSON list from the DB/file.
    Returns the final mutated context.
    """
    start_time = time.time()

    ctx = MacroContext(initial_context or {})
    ctx.set("pipeline.start_time", start_time)
    ctx.set("pipeline.dry_run", dry_run)
    ctx.set("pipeline.stopped_early", False)

    if dry_run:
        logger.info("Executing macro in DRY RUN mode")
        _execute_dry_run(nodes, ctx)
        return ctx

    # Convert dicts -> objects
    pipeline = build_pipeline_from_dict(nodes)

    logger.info(f"Starting macro execution with {len(pipeline)} root nodes")

    # Run the top-level list
    results = execute_node_list(pipeline, ctx)

    duration = time.time() - start_time
    ctx.set("pipeline.total_duration", duration)
    ctx.set("pipeline.final_results", results)

    logger.info(
        f"Macro finished in {duration:.2f}s "
        f"(early_stop: {ctx.get('pipeline.stopped_early')})"
    )

    return ctx


def execute_node_list(
    nodes: List[Any],
    context: MacroContext,
    start_index: int = 0
) -> List[Dict]:
    """
    Execute a linear list of instantiated nodes.
    Supports branching (jumping indices) and loop/for-each (via recursion inside the node).
    """
    results  = []
    i        = start_index
    total    = len(nodes)

    while i < total:
        if context.get("pipeline.stopped_early"):
            break

        node = nodes[i]
        logger.debug(f">> Running [{node.node_id}] {node.label} ({node.NODE_TYPE})")

        # Basic retry loop for this specific node
        attempt       = 0
        max_attempts  = getattr(node, "retry_limit", 1)
        on_fail       = getattr(node, "on_fail", "stop")
        result_obj    = None

        while attempt < max_attempts:
            attempt += 1
            context.set(f"{node.node_id}.attempt", attempt)

            try:
                result_obj = node.execute(context)
                if result_obj.success:
                    break  # Worked, exit retry loop
            except Exception as e:
                logger.error(
                    f"Node {node.node_id} crashed on attempt "
                    f"{attempt}: {e}"
                )
                from backend.macro.node_types import NodeResult
                result_obj = NodeResult(
                    success=False, error=str(e)
                )

            # Failed. Wait briefly before retry if we have more attempts
            if not result_obj.success and attempt < max_attempts:
                time.sleep(1.0)
                logger.warning(
                    f"Retrying node {node.node_id} "
                    f"({attempt}/{max_attempts})"
                )

        # Build output dict for history
        node_res_dict = {
            "node_id":   node.node_id,
            "type":      node.NODE_TYPE,
            "success":   result_obj.success,
            "output":    result_obj.output,
            "error":     result_obj.error,
            "duration":  result_obj.duration,
            "attempts":  attempt,
        }
        results.append(node_res_dict)

        # ── Handle Failure Strategy ────────────────────────────────────────

        if not result_obj.success:
            logger.error(f"Node {node.node_id} failed: {result_obj.error}")

            if on_fail == "skip":
                i += 1
                continue
            elif on_fail == "fallback" and getattr(node, "fallback_node", None):
                target = getattr(node, "fallback_node")
                idx = _find_node_index(nodes, target)
                if idx != -1:
                    logger.info(f"Falling back to node {target}")
                    i = idx
                    continue
                else:
                    logger.error(f"Fallback {target} not found. Stopping.")
                    break
            else:
                # "stop" or unrecognized
                logger.error("Stopping sequence execution due to node failure.")
                break

        # ── Handle Branching ───────────────────────────────────────────────

        if result_obj.branch:
            # Node specifically requested a branch (e.g., ConditionNode)
            # Find the branch container node immediately following this one
            branch = result_obj.branch
            if branch in getattr(node, "branches", {}):
                # Using built-in branching (deprecated in favor of flat list + targets)
                pass

            # Flat-list branching: Check the config for branch_yes / branch_no targets
            target_node_id = node.config.get(f"branch_{branch}")
            if target_node_id:
                idx = _find_node_index(nodes, target_node_id)
                if idx != -1:
                    logger.info(f"Branching ({branch}) to node {target_node_id}")
                    i = idx
                    continue

        if getattr(result_obj, "skip_next", False):
            # E.g., StopPipeline skips the rest
            break

        # Move to next linear node
        i += 1

    return results


def _find_node_index(nodes: List[Any], node_id: str) -> int:
    for i, n in enumerate(nodes):
        if n.node_id == node_id:
            return i
    return -1


def _execute_dry_run(nodes: List[Dict], context: MacroContext):
    """
    Fake execution that just logs what WOULD happen.
    Used for UI validation and debugging.
    """
    for rnd in nodes:
        lbl  = rnd.get('label', rnd.get('type'))
        nid  = rnd.get('id', 'unknown')
        conf = rnd.get('config', {})
        logger.info(f"[DRY RUN] Node {nid} ({lbl})")
        logger.info(f"          Config: {conf}")

        if rnd.get("type") in ("loop", "for_each"):
            _execute_dry_run(rnd.get("child_nodes", []), context)
