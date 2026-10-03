"""
SQLAlchemy table definitions for ModelFactory.
SQLite database: modelfactory.db
All JSON fields store Python dicts/lists serialized as JSON strings.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    DateTime, Text, JSON
)
from backend.database.db import Base


class ModelRecord(Base):
    """
    One row per created model.
    Stores all configuration, status, and metadata.
    """
    __tablename__ = "models"

    # Identity
    id              = Column(String, primary_key=True)
    name            = Column(String, unique=True, nullable=False)
    description     = Column(String, default="")
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow)

    # Classification
    task_types      = Column(JSON, default=list)
    # List of strings from:
    # "visual_detection", "click_navigation", "data_extraction",
    # "decision_making", "settings_adjustment", "sequence"

    output_types    = Column(JSON, default=list)
    # List of strings from:
    # "click_coords", "yes_no", "extracted_text", "numeric",
    # "ranked_list", "conditional_branch", "scroll_amount",
    # "wait_duration", "keyboard_input"

    # Training status
    status          = Column(String, default="untrained")
    # "untrained", "training", "trained", "paused", "error"

    # Performance
    best_score      = Column(Float, default=0.0)
    current_score   = Column(Float, default=0.0)
    total_attempts  = Column(Integer, default=0)
    success_rate    = Column(Float, default=0.0)
    live_confidence = Column(Float, default=0.0)
    drift_alert     = Column(Boolean, default=False)

    # ── DATA TAB ────────────────────────────────────────────────
    screen_region   = Column(JSON, default=dict)
    # {"x1": 60, "y1": 110, "x2": 1150, "y2": 720}

    preprocessing   = Column(JSON, default=lambda: {
        "resize": [224, 224],
        "color_space": "RGB",
        "normalize": "0_to_1",
        "contrast_enhancement": True
    })

    augmentation    = Column(JSON, default=lambda: {
        "brightness": 0.2,
        "color_jitter": 0.15,
        "zoom": 0.1,
        "horizontal_flip": True,
        "rotation": 0.0,
        "gaussian_noise": False,
        "multiplier": 4
    })

    extraction_config = Column(JSON, default=lambda: {
        "every_n_frames": 5,
        "max_frames": 10000,
        "output_size": [224, 224]
    })

    frame_count     = Column(Integer, default=0)
    video_count     = Column(Integer, default=0)
    image_count     = Column(Integer, default=0)

    # ── LABEL TAB ───────────────────────────────────────────────
    class_definitions = Column(JSON, default=list)
    # [{"name": "buy_button", "color": "#10b981", "shortcut": "C"},
    #  {"name": "chart_area", "color": "#3b82f6", "shortcut": "Z"}]

    label_config    = Column(JSON, default=lambda: {
        "auto_label_enabled": True,
        "auto_label_method": "pixel_delta",
        "dataset_split": {"train": 0.80, "val": 0.15, "test": 0.05},
        "test_set_locked": True
    })

    labels_compiled = Column(Boolean, default=False)
    label_counts    = Column(JSON, default=dict)
    # {"click": 423, "no_action": 1203, "unlabeled": 47}

    # ── ACTIONS TAB ─────────────────────────────────────────────
    reset_sequence_id = Column(String, nullable=True)
    # FK to action_sequences.id — the sequence tagged as reset

    humanization    = Column(JSON, default=lambda: {
        "mouse_speed_variance": 0.2,
        "click_duration_ms": [50, 150],
        "landing_offset_px": 3,
        "random_wait_between_steps": [0.05, 0.2]
    })

    # ── RESET TAB ───────────────────────────────────────────────
    reset_config    = Column(JSON, default=lambda: {
        "master_reset_sequence_id": None,
        "verify_checks": {
            "no_popup": True,
            "heatmap_present": True,
            "not_overzoomed": True,
            "window_focused": True
        },
        "verify_custom_checks": [],
        "confirm_threshold": 0.75,
        "confirm_goal_image": None,
        "on_confirm_fail": "retry_3x",
        # "retry_3x", "skip", "pause"
        "safety_timeout_seconds": 30
    })

    # ── TRAIN TAB ───────────────────────────────────────────────
    train_config    = Column(JSON, default=lambda: {
        "mode": "self_improving",
        # "self_improving", "single_pass", "fine_tune"
        "stop_condition": "manual",
        # "manual", "score", "attempts", "satisfied"
        "stop_at_score": 95.0,
        "stop_at_attempts": 200,
        "training_variety": [],
        # [{"pair": "XRPUSDT", "timeframe": "15m"}, ...]
        "transfer_from_model": None,
        "pipeline_paired_with": None,
        "auto_record_runs": True,
        "scheduler": {
            "enabled": False,
            "start_time": "02:00",
            "stop_time": "06:00",
            "max_attempts": 50,
            "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]
        }
    })

    hyperparameters = Column(JSON, default=lambda: {
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs_per_update": 1,
        "base_model": "MobileNetV2",
        "fine_tune_from_layer": 100,
        "dropout_rate": 0.3,
        "dense_units": 256
    })

    checkpoint_config = Column(JSON, default=lambda: {
        "save_every_n_attempts": 10,
        "save_on_new_best": True,
        "save_on_error": True,
        "save_on_pause": True,
        "best_criteria": "score"
        # "score" or "val_loss"
    })

    # ── SCORING TAB ─────────────────────────────────────────────
    scoring_config  = Column(JSON, default=lambda: {
        "mode": "auto",
        # "auto", "manual", "goal_only"
        "layer1": {
            "enabled": True,
            "weight": 0.30,
            "requires_goal_image": True
        },
        "layer2": {
            "enabled": True,
            "weight": 0.50,
            "rewards": [],
            "penalties": [],
            "penalty_weight_multiplier": 2.0
        },
        "layer3": {
            "enabled": True,
            "weight": 0.20,
            "click_spread": True,
            "sequence_quality": True,
            "retry_detection": True,
            "time_distribution": True
        },
        "diminishing_returns": True,
        "curriculum": {
            "enabled": True,
            "phases": [
                {"from_attempt": 1,  "to_attempt": 20,  "active_layers": [1]},
                {"from_attempt": 21, "to_attempt": 60,  "active_layers": [1, 2]},
                {"from_attempt": 61, "to_attempt": 9999, "active_layers": [1, 2, 3]}
            ]
        },
        "reward_timing": "dense",
        # "dense", "sparse", "mixed"
        "confidence_threshold": 0.65
    })

    # ── GOALS TAB ───────────────────────────────────────────────
    goals_config    = Column(JSON, default=lambda: {
        "goal_images": [],
        # list of filenames in goals/ folder
        "primary_goal_image": None,
        "similarity_threshold": 0.75,
        "similarity_method": "ssim"
        # "ssim", "ncc", "mse"
    })

    # ── RESULTS TAB ─────────────────────────────────────────────
    results_config  = Column(JSON, default=lambda: {
        "export_formats": ["keras", "savedmodel"],
        # "keras", "savedmodel", "tflite", "onnx"
        "drift_baseline_confidence": None,
        "specializations": {}
        # {"XRP": "model_id", "BTC": "model_id"}
    })

    score_history   = Column(JSON, default=list)
    # last 100 scores as floats


class TrainingSession(Base):
    """
    One row per training attempt.
    Complete record of every attempt ever made.
    """
    __tablename__ = "training_sessions"

    id              = Column(String, primary_key=True)
    model_id        = Column(String, nullable=False)
    attempt_number  = Column(Integer, nullable=False)
    score           = Column(Float, default=0.0)
    duration_sec    = Column(Float, default=0.0)
    success         = Column(Boolean, default=False)

    # Reset system results
    master_reset_ok = Column(Boolean, default=True)
    verify_ok       = Column(Boolean, default=True)
    verify_details  = Column(String, default="ok")
    confirm_score   = Column(Float, default=0.0)
    confirm_ok      = Column(Boolean, default=True)

    # Attempt results
    error_type      = Column(String, nullable=True)
    # "reset_error", "vision_error", "click_error",
    # "ocr_error", "app_error", None

    confidence      = Column(Float, default=0.0)
    output_json     = Column(JSON, default=dict)
    # The actual output produced by the model

    # GPU stats at time of attempt
    gpu_memory_mb   = Column(Integer, default=0)
    gpu_util_pct    = Column(Integer, default=0)
    gpu_temp_c      = Column(Integer, default=0)

    # Paths
    snapshot_path   = Column(String, nullable=True)
    replay_path     = Column(String, nullable=True)

    created_at      = Column(DateTime, default=datetime.utcnow)


class ActionSequence(Base):
    """
    One row per recorded or manually created action sequence.
    Sequences belong to a model. One sequence can be tagged as the reset sequence.
    """
    __tablename__ = "action_sequences"

    id          = Column(String, primary_key=True)
    model_id    = Column(String, nullable=False)
    name        = Column(String, nullable=False)
    is_reset    = Column(Boolean, default=False)
    steps       = Column(JSON, default=list)
    # [
    #   {"type": "click",  "x": 460, "y": 55},
    #   {"type": "key",    "key": "Escape"},
    #   {"type": "scroll", "amount": -8},
    #   {"type": "wait",   "seconds": 1.5},
    #   {"type": "drag",   "x1": 100, "y1": 200,
    #                      "x2": 300, "y2": 200, "duration": 0.3},
    #   {"type": "type",   "text": "Coinglass"},
    #   {"type": "double_click", "x": 460, "y": 55},
    # ]
    step_count  = Column(Integer, default=0)
    duration_estimate_sec = Column(Float, default=0.0)
    created_at  = Column(DateTime, default=datetime.utcnow)


class CheckpointRecord(Base):
    """
    One row per saved training checkpoint.
    Links model ID to weights path and training state at that point.
    """
    __tablename__ = "checkpoints"

    id              = Column(String, primary_key=True)
    model_id        = Column(String, nullable=False)
    attempt_number  = Column(Integer, nullable=False)
    score           = Column(Float, default=0.0)
    best_score      = Column(Float, default=0.0)
    stop_reason     = Column(String, default="auto")
    # "auto", "new_best", "error", "manual", "satisfied",
    # "score_reached", "attempts_reached"
    weights_path    = Column(String, nullable=False)
    state_path      = Column(String, nullable=False)
    score_history   = Column(JSON, default=list)
    is_best         = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)


class MacroRecord(Base):
    """
    One row per saved macro pipeline.
    """
    __tablename__ = "macros"

    id          = Column(String, primary_key=True)
    name        = Column(String, nullable=False)
    description = Column(String, default="")
    nodes       = Column(JSON, default=list)
    edges       = Column(JSON, default=list)
    settings    = Column(JSON, default=dict)
    last_run    = Column(DateTime, nullable=True)
    run_count   = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow,
                         onupdate=datetime.utcnow)


class LiveRunRecord(Base):
    """
    One row per live agent deployment run (not training — actual live use).
    Stores the JSON output of each run for the Daily Operations view.
    """
    __tablename__ = "live_runs"

    id          = Column(String, primary_key=True)
    macro_id    = Column(String, nullable=True)
    pair        = Column(String, default="XRPUSDT")
    timeframe   = Column(String, default="15m")
    success     = Column(Boolean, default=False)
    duration_sec = Column(Float, default=0.0)
    score       = Column(Float, default=0.0)
    output_json = Column(JSON, default=dict)
    error_msg   = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
