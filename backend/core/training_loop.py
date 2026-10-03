"""
Self-Improving Training Loop.
Runs in a QThread via training_worker.py.
Every attempt: Reset → Verify → Confirm → Execute → Score → Learn.
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import tensorflow as tf

from backend.core.model_factory import build_model, load_model, save_model
from backend.core.reset_controller import ResetController
from backend.core.score_calculator import ScoreCalculator
from backend.core.checkpoint_manager import CheckpointManager
from backend.core.overfitting_monitor import OverfittingMonitor
from backend.core.drift_detector import DriftDetector
from backend.core.gpu_manager import get_live_gpu_stats, ComputeDevice
from backend.data.dataset_builder import load_tf_datasets
from backend.vision.screen_capture import capture_region
from backend.desktop.action_executor import execute_action
from backend.vision.preprocessor import preprocess_single

logger = logging.getLogger(__name__)


class TrainingState:
    def __init__(self):
        self.running       = False
        self.paused        = False
        self.iteration     = 0
        self.best_score    = 0.0
        self.current_score = 0.0
        self.score_history = []
        self.reset_status  = "idle"
        self.start_time    = None
        self.stop_reason   = None
        self.gpu_stats     = {}
        self.overfitting   = {"train": 0, "val": 0, "gap": 0, "status": "ok"}
        self.log_lines     = []

    def elapsed_str(self) -> str:
        if not self.start_time:
            return "00:00:00"
        e = int(time.time() - self.start_time)
        return f"{e//3600:02d}:{(e%3600)//60:02d}:{e%60:02d}"

    def trend(self, n: int = 5) -> float:
        if len(self.score_history) < n + 1:
            return 0.0
        return self.score_history[-1] - self.score_history[-(n+1)]

    def to_dict(self) -> dict:
        return {
            "running":       self.running,
            "paused":        self.paused,
            "iteration":     self.iteration,
            "best_score":    round(self.best_score, 2),
            "current_score": round(self.current_score, 2),
            "score_history": self.score_history[-50:],
            "reset_status":  self.reset_status,
            "elapsed":       self.elapsed_str(),
            "trend":         round(self.trend(), 2),
            "gpu":           self.gpu_stats,
            "overfitting":   self.overfitting,
        }


def run_training_loop(
    model_id:       str,
    model_name:     str,
    model_config:   dict,
    train_config:   dict,
    scoring_config: dict,
    device:         ComputeDevice,
    state:          TrainingState,
    log_cb:         Callable[[str], None],
    status_cb:      Callable[[dict], None],
):
    """
    Main training loop function.
    Called from TrainingWorker.run() inside a QThread.
    All UI updates go through log_cb and status_cb callbacks.
    """

    def log(msg: str):
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {model_name}  {msg}"
        state.log_lines.append(line)
        log_cb(line)

    def emit():
        status_cb(state.to_dict())

    state.running    = True
    state.start_time = time.time()
    model_dir = Path("models") / model_name

    log(f"Training loop started on {device.name}")
    log(f"Mode: {train_config.get('mode', 'self_improving')}")
    log(f"Stop: {train_config.get('stop_condition', 'manual')}")
    log(f"Device string: {device.tf_device_string}")
    emit()

    # ── LOAD OR BUILD MODEL ──────────────────────────────────────
    ckpt_mgr  = CheckpointManager(model_dir)
    best_path = str(model_dir / "best" / "model")
    try:
        # Load weights and persistence state
        model, loaded_state = ckpt_mgr.load(str(model_dir / "best"))
        state.iteration  = loaded_state.get("attempt", 0)
        state.best_score = loaded_state.get("best_score", 0.0)
        state.score_history = loaded_state.get("score_history", [])
        log(f"Resumed from checkpoint: attempt {state.iteration}, best {state.best_score}")
    except Exception as e:
        log("No checkpoint found or load failed — building new model")
        model = build_model(
            task_type     = model_config.get("task_type", "visual_detection"),
            output_type   = model_config.get("output_type", "yes_no"),
            num_classes   = model_config.get("num_classes", 2),
            device_string = device.tf_device_string,
            learning_rate = model_config.get("learning_rate", 0.001),
            dense_units   = model_config.get("dense_units", 256),
            dropout_rate  = model_config.get("dropout_rate", 0.3),
        )

    # ── LOAD DATASET ─────────────────────────────────────────────
    train_ds = val_ds = None
    try:
        train_ds, val_ds = load_tf_datasets(
            model_name   = model_name,
            batch_size   = model_config.get("batch_size", 32),
            augment      = True,
            streaming    = train_config.get("use_streaming", True),
            advanced_aug = model_config.get("augmentation", {}).get("advanced", True)
        )
        log(f"Dataset loaded (Streaming={'ON' if train_config.get('use_streaming', True) else 'OFF'})")
    except Exception as e:
        log(f"Dataset not ready ({e}) — pure RL mode")

    # ── SUPPORT OBJECTS ──────────────────────────────────────────
    reset_ctrl  = ResetController(model_name, model_config)
    scorer      = ScoreCalculator(scoring_config)
    # ckpt_mgr created above for loading
    overfit_mon = OverfittingMonitor()
    drift_det   = DriftDetector()

    stop_at_score    = train_config.get("stop_at_score")
    stop_at_attempts = train_config.get("stop_at_attempts")
    save_every       = model_config.get("save_every_n_attempts", 10)

    # ── MAIN LOOP ─────────────────────────────────────────────────
    while state.running:

        # Pause support
        while state.paused and state.running:
            time.sleep(0.3)
        if not state.running:
            break

        state.iteration += 1
        attempt_start = time.time()
        log(f"Attempt {state.iteration} starting")
        emit()

        # ── LAYER 1: MASTER RESET ────────────────────────────────
        state.reset_status = "resetting"
        emit()
        log("Master Reset: running sequence")

        reset_ok = reset_ctrl.execute_master_reset()
        if not reset_ok:
            log("Master Reset FAILED — pausing training")
            state.paused = True
            _save_error_checkpoint(ckpt_mgr, model, state, "master_reset_failed")
            continue

        # ── LAYER 2: VERIFY ──────────────────────────────────────
        state.reset_status = "verifying"
        emit()
        log("Verify: running pixel checks")

        verify_ok, verify_detail = reset_ctrl.verify()
        if not verify_ok:
            log(f"Verify FAILED: {verify_detail} — attempting recovery")
            reset_ctrl.auto_recover()
            verify_ok, verify_detail = reset_ctrl.verify()
            if not verify_ok:
                log(f"Recovery failed ({verify_detail}) — skipping attempt")
                state.iteration -= 1
                state.reset_status = "idle"
                continue

        log(f"Verify: all checks passed ✓")

        # ── LAYER 3: CONFIRM ─────────────────────────────────────
        state.reset_status = "confirming"
        emit()

        confirm_score, confirm_ok = reset_ctrl.confirm()
        if not confirm_ok:
            log(f"Confirm: {confirm_score:.0%} match — below threshold")
            
            if reset_ctrl.on_fail == "Retry Reset":
                max_retries = reset_ctrl.max_retries
                for retry_n in range(max_retries):
                    reset_ctrl.execute_master_reset()
                    confirm_score, confirm_ok = reset_ctrl.confirm()
                    if confirm_ok:
                        break
                    log(f"Confirm retry {retry_n+1}/{max_retries} failed ({confirm_score:.0%})")
            
            if not confirm_ok:
                if reset_ctrl.on_fail == "Stop Training":
                    log("Confirm FAILED — on_fail=Stop. Ending training loop.")
                    state.running = False
                    break
                elif reset_ctrl.on_fail == "Pause & Manual Intervention":
                    log("Confirm FAILED — on_fail=Pause. Waiting for user...")
                    state.paused = True
                    continue
                else:
                    log(f"Confirm failed after retries — skipping attempt")
                    state.reset_status = "idle"
                    continue

        log(f"Confirm: {confirm_score:.0%} match ✓")
        state.reset_status = "ready"
        emit()

        # ── RUN ATTEMPT ───────────────────────────────────────────
        log("Model attempting task on live app...")
        attempt_result = _run_attempt(
            model         = model,
            model_config  = model_config,
            device_string = device.tf_device_string
        )

        # ── CALCULATE SCORE ───────────────────────────────────────
        attempt_result["confirm_score"] = confirm_score
        score = scorer.calculate(
            result     = attempt_result,
            attempt_n  = state.iteration
        )
        state.current_score = score
        state.score_history.append(round(score, 2))
        success = (score >= 50)

        duration = time.time() - attempt_start
        log(
            f"Attempt {state.iteration}: "
            f"score={score:.1f}  "
            f"best={state.best_score:.1f}  "
            f"{'✓' if success else '✗'}  "
            f"{duration:.1f}s"
        )

        # ── SAVE IF NEW BEST ──────────────────────────────────────
        if score > state.best_score:
            state.best_score = score
            save_model(model, best_path)
            log(f"✓ New best: {score:.1f} — model saved")

        # ── GPU STATS ─────────────────────────────────────────────
        if state.iteration % 5 == 0:
            state.gpu_stats = get_live_gpu_stats(device)

        # ── SUPERVISED TRAINING EPOCH ────────────────────────────
        if train_ds is not None and state.iteration % 10 == 0:
            log("Running supervised epoch on dataset...")
            with tf.device(device.tf_device_string):
                h = model.fit(
                    train_ds,
                    epochs=1,
                    validation_data=val_ds,
                    verbose=0,
                    workers=1,
                    use_multiprocessing=False,
                )
            t_acc = h.history.get('accuracy', [0])[-1]
            v_acc = h.history.get('val_accuracy', [0])[-1]
            log(f"Epoch done: train={t_acc:.3f}  val={v_acc:.3f}")
            
            # TRACK BEST VAL ACCURACY AS ALTERNATE "BEST"
            best_v_acc = state.overfitting.get("best_val_acc", 0.0)
            if v_acc > best_v_acc:
                log(f"✓ New validation high: {v_acc:.3f} — checkpointing")
                save_model(model, best_path)
                state.overfitting["patience_counter"] = 0
            else:
                state.overfitting["patience_counter"] = state.overfitting.get("patience_counter", 0) + 1
            
            overfit_mon.update(t_acc, v_acc)
            state.overfitting = overfit_mon.get_status()
            state.overfitting["best_val_acc"] = max(v_acc, best_v_acc)
            
            # EARLY STOPPING LOGIC
            if train_config.get("early_stop", True):
                patience = train_config.get("early_stop_patience", 5) # Epochs every 10 attempts -> 50 attempts
                counter  = state.overfitting.get("patience_counter", 0)
                if counter >= patience:
                    log(f"🛑 Early Stopping: No val improvement for {patience} epochs.")
                    state.stop_reason = "early_stopping"
                    state.running = False
            
            if overfit_mon.is_overfitting():
                log("⚠ Overfitting detected — consider stopping")

        # ── AUTO CHECKPOINT ───────────────────────────────────────
        if state.iteration % save_every == 0:
            ckpt_mgr.save(
                model        = model,
                attempt      = state.iteration,
                score        = score,
                best_score   = state.best_score,
                score_history = state.score_history,
                reason       = "auto"
            )
            log(f"Checkpoint saved (attempt {state.iteration})")

        # ── STOP CONDITIONS ───────────────────────────────────────
        if stop_at_score and state.best_score >= stop_at_score:
            log(f"Target score {stop_at_score} reached — stopping")
            state.stop_reason = "score_reached"
            state.running = False

        if stop_at_attempts and state.iteration >= stop_at_attempts:
            log(f"Max {stop_at_attempts} attempts reached — stopping")
            state.stop_reason = "attempts_reached"
            state.running = False

        state.reset_status = "idle"
        emit()
        time.sleep(0.1)

    # ── FINAL SAVE ────────────────────────────────────────────────
    log(f"Training ended: {state.stop_reason or 'manual'}")
    ckpt_mgr.save(
        model        = model,
        attempt      = state.iteration,
        score        = state.current_score,
        best_score   = state.best_score,
        score_history = state.score_history,
        reason       = state.stop_reason or "manual"
    )
    log("Final checkpoint saved ✓")
    emit()


def _run_attempt(
    model: tf.keras.Model,
    model_config: dict,
    device_string: str
) -> dict:
    region = _get_active_focus_region(model_config)
    start  = time.time()

    try:
        screenshot = capture_region(region)
        if screenshot is None:
            return {
                "success": False, "error": "capture_failed",
                "output": None, "confidence": 0.0,
                "duration": time.time() - start
            }

        img_tensor = preprocess_single(screenshot, device_string)

        with tf.device(device_string):
            prediction = model(img_tensor, training=False)
            pred_np    = prediction.numpy()[0]

        confidence = float(np.max(pred_np))
        threshold  = model_config.get("confidence_threshold", 0.65)
        output_type = model_config.get("output_type", "yes_no")

        action  = None
        executed = False

        if confidence >= threshold:
            action = _pred_to_action(
                pred_np, output_type, region, model_config
            )
            if action:
                execute_action(action)
                executed = True

        return {
            "success":     executed,
            "confidence":  confidence,
            "prediction":  pred_np.tolist(),
            "action":      action,
            "output":      action,
            "duration":    time.time() - start,
            "error":       None,
        }
    except Exception as e:
        logger.error(f"Attempt execution error: {e}")
        return {
            "success": False, "error": str(e),
            "output": None, "confidence": 0.0,
            "duration": time.time() - start
        }


def _pred_to_action(
    prediction, output_type, region, config
) -> Optional[dict]:
    if output_type == "yes_no":
        idx = int(np.argmax(prediction))
        return {
            "type":       "decision",
            "value":      idx == 0,
            "confidence": float(prediction[idx])
        }
    elif output_type == "click_coords":
        x_n, y_n = float(prediction[0]), float(prediction[1])
        if region:
            x = int(region['x1'] + x_n * (region['x2'] - region['x1']))
            y = int(region['y1'] + y_n * (region['y2'] - region['y1']))
        else:
            import mss
            with mss.mss() as s:
                m = s.monitors[1]
                x = int(x_n * m['width'])
                y = int(y_n * m['height'])
        return {"type": "click", "x": x, "y": y}
    elif output_type in ("numeric", "scroll_amount"):
        return {"type": "numeric", "value": float(prediction[0])}
    return None


def _get_active_focus_region(model_config: dict) -> Optional[dict]:
    """Helper to get focus region based on new focus_config or legacy screen_region."""
    fcfg = model_config.get("focus_config", {})
    if fcfg.get("mode") == "whole_screen":
        return None
        
    regions = fcfg.get("regions", [])
    if regions:
        return regions[0]
        
    return model_config.get("screen_region")


def _save_error_checkpoint(ckpt_mgr, model, state, reason):
    try:
        ckpt_mgr.save(
            model=model, attempt=state.iteration,
            score=state.current_score, best_score=state.best_score,
            score_history=state.score_history, reason=reason
        )
    except Exception as e:
        logger.error(f"Emergency checkpoint save failed: {e}")
