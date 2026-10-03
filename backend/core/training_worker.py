"""
QThread wrapper for the self-improving training loop.
Runs training in background — UI never freezes.
Emits Qt signals for all UI updates.
This is the bridge between the training_loop.py backend
and the PyQt6 frontend.
"""
import logging
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class TrainingWorker(QThread):
    """
    Background training thread.
    Connect these signals to UI slots.

    Signals:
        log_line(model_name, text)
            Every log message from training loop.
            Connect to terminal widget.

        status_update(status_dict)
            Full training state every attempt.
            Connect to live monitor cards and sparkline.
            Dict keys: running, paused, iteration, best_score,
                       current_score, score_history, reset_status,
                       elapsed, trend, gpu, overfitting

        attempt_done(model_name, score, attempt_number)
            After each attempt completes.
            Connect to model card update.

        training_error(model_name, error_message)
            When training hits an unrecoverable error.
            Connect to error alert banner.

        training_finished(model_name, reason)
            When training stops for any reason.
            reason: "manual" | "satisfied" | "score_reached" |
                    "attempts_reached" | "error"
            Connect to button state reset and final save notification.

        overfitting_alert(model_name, train_score, val_score, gap)
            When overfitting gap exceeds threshold.
            Connect to overfitting warning display.

        new_best(model_name, score, attempt)
            When a new best score is achieved.
            Connect to best score display and notification.

        checkpoint_saved(model_name, attempt, path)
            After each auto-checkpoint save.
            Connect to checkpoint status display.

        reset_status_changed(model_name, status)
            As reset pipeline progresses through layers.
            status: "idle" | "resetting" | "verifying" |
                    "confirming" | "ready"
            Connect to reset pipeline indicator.

        gpu_stats_updated(stats_dict)
            GPU memory, utilization, temperature every 5 attempts.
            Connect to GPU bar widget.
    """

    # ── SIGNALS ──────────────────────────────────────────────────
    log_line              = pyqtSignal(str, str)    # model_name, text
    status_update         = pyqtSignal(dict)
    attempt_done          = pyqtSignal(str, float, int)  # name, score, n
    training_error        = pyqtSignal(str, str)    # name, error
    training_finished     = pyqtSignal(str, str)    # name, reason
    overfitting_alert     = pyqtSignal(str, float, float, float)  # name, train, val, gap
    new_best              = pyqtSignal(str, float, int)  # name, score, attempt
    checkpoint_saved      = pyqtSignal(str, int, str)    # name, attempt, path
    reset_status_changed  = pyqtSignal(str, str)    # name, status
    gpu_stats_updated     = pyqtSignal(dict)

    def __init__(
        self,
        model_id:        str,
        model_name:      str,
        model_config:    dict,
        train_config:    dict,
        scoring_config:  dict,
        device,          # ComputeDevice object from gpu_manager
        parent=None
    ):
        super().__init__(parent)
        self.model_id       = model_id
        self.model_name     = model_name
        self.model_config   = model_config
        self.train_config   = train_config
        self.scoring_config = scoring_config
        self.device         = device
        self._state         = None

    # ── PUBLIC CONTROL ────────────────────────────────────────────

    def pause(self):
        if self._state:
            self._state.paused = True
            self._emit_log("Training paused by user")

    def resume(self):
        if self._state:
            self._state.paused = False
            self._emit_log("Training resumed")

    def stop(self, reason: str = "manual"):
        if self._state:
            self._state.running    = False
            self._state.stop_reason = reason
            self._emit_log(f"Stop requested: {reason}")

    def satisfied(self):
        """User clicked I AM SATISFIED — save best and stop."""
        self.stop("satisfied")

    # ── THREAD ENTRY POINT ────────────────────────────────────────

    def run(self):
        """Called by QThread.start(). Runs in background thread."""
        from backend.core.training_loop import (
            TrainingState, run_training_loop
        )

        self._state = TrainingState()
        self._emit_log("Training worker started")

        try:
            run_training_loop(
                model_id        = self.model_id,
                model_name      = self.model_name,
                model_config    = self.model_config,
                train_config    = self.train_config,
                scoring_config  = self.scoring_config,
                device          = self.device,
                state           = self._state,
                log_cb          = self._on_log,
                status_cb       = self._on_status,
            )
        except Exception as e:
            logger.exception(f"Training worker error: {e}")
            self.training_error.emit(self.model_name, str(e))
        finally:
            reason = self._state.stop_reason if self._state else "error"
            self.training_finished.emit(self.model_name, reason or "manual")
            self._emit_log(f"Training worker finished: {reason}")

    # ── CALLBACKS (called from training_loop, not UI thread) ──────

    def _on_log(self, line: str):
        """Called by training_loop for every log message."""
        self.log_line.emit(self.model_name, line)

        # Detect special events in log lines and emit specific signals
        if "new best" in line.lower() and self._state:
            self.new_best.emit(
                self.model_name,
                self._state.best_score,
                self._state.iteration
            )
        if "checkpoint saved" in line.lower() and self._state:
            self.checkpoint_saved.emit(
                self.model_name,
                self._state.iteration,
                ""
            )
        if "overfitting detected" in line.lower() and self._state:
            ov = self._state.overfitting
            self.overfitting_alert.emit(
                self.model_name,
                ov.get("train", 0),
                ov.get("val", 0),
                ov.get("gap", 0)
            )

    def _on_status(self, status: dict):
        """Called by training_loop on every state change."""
        self.status_update.emit(status)

        # Emit specific signals from status dict
        name = self.model_name

        reset_status = status.get("reset_status", "idle")
        self.reset_status_changed.emit(name, reset_status)

        if status.get("gpu"):
            self.gpu_stats_updated.emit(status["gpu"])

        if status.get("iteration") and status.get("current_score") is not None:
            self.attempt_done.emit(
                name,
                status["current_score"],
                status["iteration"]
            )

    def _emit_log(self, msg: str):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {self.model_name}  {msg}"
        self.log_line.emit(self.model_name, line)
