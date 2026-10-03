"""
PyQt QThread worker for executing a macro without freezing the UI.
Emits logs and progress back to the MacroTracker / Dashboard widget.
"""
import logging
import traceback
from typing import Dict, List
from PyQt6.QtCore import QThread, pyqtSignal

from backend.macro.executor import execute_macro
from backend.macro.context import MacroContext

class MacroWorker(QThread):
    finished     = pyqtSignal(bool, dict)  # success, results_dict
    progress     = pyqtSignal(int, int)    # current_node, total_nodes
    log_msg      = pyqtSignal(str, str)    # level, message

    def __init__(self, macro_data: dict, init_context: dict = None,
                 dry_run: bool = False):
        super().__init__()
        self.macro_data = macro_data
        self.init_ctx   = init_context or {}
        self.dry_run    = dry_run
        self._is_stopped = False

    def run(self):
        self.log_msg.emit(
            "info",
            f"Starting macro '{self.macro_data.get('name', 'Unnamed')}'"
        )
        nodes = self.macro_data.get("nodes", [])

        if not nodes:
            self.log_msg.emit("error", "Macro has no nodes to execute")
            self.finished.emit(False, {"error": "Empty pipeline"})
            return

        try:
            # We wrap the logger temporarily or just let executor log.
            # To get node-progress, we'd ideally pass a callback to execute_macro.
            # For now, executor logs to standard Python logger.
            final_ctx = execute_macro(nodes, self.init_ctx, self.dry_run)

            results = final_ctx.dump()
            success = not final_ctx.get("pipeline.stopped_early", False)

            if success:
                self.log_msg.emit(
                    "success", "Macro execution completed successfully."
                )
            else:
                self.log_msg.emit("warning", "Macro execution stopped early.")

            self.finished.emit(success, results)

        except Exception as e:
            err = traceback.format_exc()
            self.log_msg.emit(
                "error", f"Macro execution crashed: {e}\n{err}"
            )
            self.finished.emit(False, {"error": str(e), "traceback": err})

    def stop(self):
        """Request the macro to stop execution."""
        # This requires executor to check a flag. We'd inject it via context.
        # But for now, QThread termination is harsh.
        self._is_stopped = True
        self.log_msg.emit("warning", "Stop request sent to worker.")
        # If executor is checking context.get("pipeline.stop_requested")
        # we can't easily mutate context from here if it's already running.
        # A proper implementation shares a threading.Event.
