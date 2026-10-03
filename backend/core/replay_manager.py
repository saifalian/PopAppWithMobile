import os
import json
import time
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class ReplayManager:
    """
    Manages structured 'Experience Replays' for training attempts.
    Each replay contains:
    - Metadata (timestamp, model_name, score, success)
    - Sequential Events (Action + Screenshots before/after)
    """
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.base_dir = Path("models") / model_name / "replays"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
    def start_replay(self, attempt_id: int) -> Path:
        """Create a folder for a new attempt replay."""
        replay_dir = self.base_dir / f"attempt_{attempt_id:04d}_{int(time.time())}"
        replay_dir.mkdir(exist_ok=True)
        return replay_dir

    def add_event(self, replay_dir: Path, step: int, action: str, 
                  screenshot_before: bytes, screenshot_after: bytes, 
                  confidence: float = 1.0):
        """Save a single action event with before/after screenshots."""
        try:
            event_dir = replay_dir / f"step_{step:02d}"
            event_dir.mkdir(exist_ok=True)
            
            # Save images
            with open(event_dir / "before.png", "wb") as f:
                f.write(screenshot_before)
            with open(event_dir / "after.png", "wb") as f:
                f.write(screenshot_after)
                
            # Save meta
            meta = {
                "step": step,
                "action": action,
                "confidence": confidence,
                "timestamp": time.time()
            }
            with open(event_dir / "meta.json", "w") as f:
                json.dump(meta, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to add replay event: {e}")

    def finalize_replay(self, replay_dir: Path, total_score: float, success: bool):
        """Write the final attempt summary."""
        summary = {
            "model": self.model_name,
            "total_score": total_score,
            "success": success,
            "end_time": time.time()
        }
        with open(replay_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
            
    def list_replays(self) -> List[Dict]:
        """Returns a list of all available replays with their summaries."""
        replays = []
        for d in self.base_dir.iterdir():
            if d.is_dir() and (d / "summary.json").exists():
                try:
                    with open(d / "summary.json") as f:
                        s = json.load(f)
                        s["path"] = str(d)
                        replays.append(s)
                except: pass
        return sorted(replays, key=lambda x: x.get("end_time", 0), reverse=True)
