"""
Checkpoint & Model Version Manager.
Handles saving, loading, versioning, and pruning model weights.
"""
import logging
import os
import shutil
import glob
from pathlib import Path

logger = logging.getLogger(__name__)

class CheckpointManager:
    def __init__(self, base_dir="models", max_keep=5):
        """
        base_dir: Root directory for models.
        max_keep: Number of checkpoints to keep per model before pruning oldest.
        """
        self.base_dir = Path(base_dir)
        self.max_keep = max_keep

    def _get_model_dir(self, model_name: str) -> Path:
        return self.base_dir / model_name / "checkpoints"

    def save_checkpoint(self, model_name: str, version_name: str, model_obj, is_best=False):
        """
        Save a Keras model object to disk under a specific version.
        If is_best is True, also copies to models/model_name/best/.
        """
        try:
            model_dir = self._get_model_dir(model_name)
            version_path = model_dir / version_name
            version_path.mkdir(parents=True, exist_ok=True)
            
            # Save using Keras SavedModel format
            logger.info(f"Saving checkpoint to: {version_path}")
            model_obj.save(str(version_path))
            
            # If best, copy it
            if is_best:
                best_path = self.base_dir / model_name / "best"
                if best_path.exists():
                    shutil.rmtree(best_path)
                shutil.copytree(version_path, best_path)
                logger.info(f"Updated best model for {model_name}")

            # Prune old checkpoints
            self._prune_old_checkpoints(model_name)
            return True
        except Exception as e:
            logger.error(f"Failed to save checkpoint {version_name}: {e}")
            return False

    def load_checkpoint(self, model_name: str, version_name: str, load_best=False):
        """Load a Keras model from disk."""
        import tensorflow as tf
        
        try:
            if load_best:
                path = self.base_dir / model_name / "best"
            else:
                path = self._get_model_dir(model_name) / version_name
                
            if not path.exists():
                logger.error(f"Checkpoint not found: {path}")
                return None
                
            logger.info(f"Loading model from {path}")
            return tf.keras.models.load_model(str(path))
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return None

    def list_versions(self, model_name: str) -> list:
        """List all available checkpoints for a model, sorted newest first."""
        model_dir = self._get_model_dir(model_name)
        if not model_dir.exists():
            return []
            
        versions = []
        for p in model_dir.iterdir():
            if p.is_dir():
                # Sort by modification time
                mtime = p.stat().st_mtime
                versions.append((p.name, mtime))
                
        versions.sort(key=lambda x: x[1], reverse=True)
        return [v[0] for v in versions]

    def _prune_old_checkpoints(self, model_name: str):
        """Remove oldest checkpoints if we exceed max_keep."""
        model_dir = self._get_model_dir(model_name)
        versions = self.list_versions(model_name)
        
        while len(versions) > self.max_keep:
            oldest = versions.pop() # Last element is oldest
            oldest_path = model_dir / oldest
            try:
                shutil.rmtree(oldest_path)
                logger.debug(f"Pruned old checkpoint: {oldest}")
            except Exception as e:
                logger.warning(f"Failed to prune {oldest}: {e}")

    def backup_model(self, model_name: str, backup_path: str) -> bool:
        """Create a full backup of the entire model directory structure."""
        src = self.base_dir / model_name
        dst = Path(backup_path) / model_name
        
        if not src.exists():
            logger.error(f"Cannot backup, {model_name} does not exist.")
            return False
            
        try:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            logger.info(f"Model {model_name} successfully backed up to {dst}")
            return True
        except Exception as e:
            logger.error(f"Backup failed for {model_name}: {e}")
            return False
