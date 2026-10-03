import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

MODELS_DIR = Path("models")

def list_models() -> List[Dict]:
    """List all models in the models directory."""
    if not MODELS_DIR.exists():
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        return []
    
    models = []
    for item in MODELS_DIR.iterdir():
        if item.is_dir():
            score = 0.0
            attempts = 0
            best_state = item / "best" / "state.json"
            if best_state.exists():
                try:
                    import json
                    with open(best_state) as f:
                        bs = json.load(f)
                    score = bs.get("best_score", bs.get("score", 0.0))
                    attempts = bs.get("attempt", 0)
                except Exception:
                    pass

            models.append({
                "name": item.name,
                "path": str(item),
                "status": "trained" if best_state.exists() else "untrained",
                "score": score,
                "attempts": attempts
            })
    return sorted(models, key=lambda x: x["name"])

def load_model_config(model_name: str) -> Dict:
    """Load model configuration from config.json."""
    config_path = MODELS_DIR / model_name / "config.json"
    if not config_path.exists():
        return {"name": model_name, "tasks": [], "outputs": [], "description": ""}
    
    try:
        import json
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config for {model_name}: {e}")
        return {"name": model_name, "tasks": [], "outputs": [], "description": ""}

def save_model_config(model_name: str, config: dict) -> bool:
    """Save model configuration to config.json."""
    config_path = MODELS_DIR / model_name / "config.json"
    try:
        import json
        # Ensure name match
        config["name"] = model_name
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Failed to save config for {model_name}: {e}")
        return False

def rename_model(old_name: str, new_name: str) -> bool:
    """Rename a model directory."""
    old_path = MODELS_DIR / old_name
    new_path = MODELS_DIR / new_name
    
    if not old_path.exists():
        logger.error(f"Rename failed: Model '{old_name}' not found.")
        return False
    
    if new_path.exists():
        logger.error(f"Rename failed: Model '{new_name}' already exists.")
        return False
    
    try:
        old_path.rename(new_path)
        logger.info(f"Renamed model '{old_name}' to '{new_name}'")
        return True
    except Exception as e:
        logger.error(f"Rename failed for '{old_name}': {e}")
        return False

def delete_model(model_name: str) -> bool:
    """Delete a model directory and all its contents."""
    model_path = MODELS_DIR / model_name
    
    if not model_path.exists():
        logger.error(f"Delete failed: Model '{model_name}' not found.")
        return False
    
    try:
        shutil.rmtree(model_path)
        logger.info(f"Deleted model '{model_name}'")
        return True
    except Exception as e:
        logger.error(f"Delete failed for '{model_name}': {e}")
        return False
def create_model(model_name: str, description: str = "", tasks: list = None, outputs: list = None) -> bool:
    """Create a new model directory structure and save metadata."""
    model_path = MODELS_DIR / model_name
    
    if model_path.exists():
        logger.error(f"Create failed: Model '{model_name}' already exists.")
        return False
    
    subdirs = [
        "reference", "extracted", "labeled", "augmented", "goals", 
        "checkpoints", "best", "logs", "attempts", "test_data", 
        "live_recordings", "results"
    ]
    
    try:
        import json
        model_path.mkdir(parents=True, exist_ok=True)
        for sub in subdirs:
            (model_path / sub).mkdir(exist_ok=True)
        
        # Save metadata config
        config = {
            "name": model_name,
            "description": description,
            "tasks": tasks or [],
            "outputs": outputs or [],
            "created_at": None # Could add timestamp if needed
        }
        with open(model_path / "config.json", "w") as f:
            json.dump(config, f, indent=4)
            
        logger.info(f"Created model structure and config for '{model_name}'")
        return True
    except Exception as e:
        logger.error(f"Create failed for '{model_name}': {e}")
        return False
