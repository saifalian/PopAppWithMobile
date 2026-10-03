"""
Backend processor for extracting metadata, thumbnails, and frames 
from video recording sessions.
"""
import os
import cv2
import time
import shutil
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
import logging

logger = logging.getLogger(__name__)

class VideoMetadata:
    @staticmethod
    def get_info(video_path: str) -> dict:
        """Returns metadata and generates a temporary thumbnail."""
        path = Path(video_path)
        if not path.exists():
            return {}
            
        size_mb = path.stat().st_size / (1024 * 1024)
        
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            return {"error": "Could not open video"}
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        duration_sec = frame_count / fps if fps > 0 else 0
        mins, secs = divmod(int(duration_sec), 60)
        
        # Read a frame at 10% in to avoid pure black start screens
        target_frame = int(frame_count * 0.1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        
        thumb_path = ""
        if ret:
            # Save thumbnail to temp dir
            temp_dir = Path("data/temp")
            temp_dir.mkdir(parents=True, exist_ok=True)
            thumb_path = str(temp_dir / f"thumb_{path.stem}.jpg")
            # Resize thumbnail to save space
            thumb_frame = cv2.resize(frame, (600, int(600 * (height/width))))
            cv2.imwrite(thumb_path, thumb_frame)
            
        cap.release()
        
        return {
            "duration": f"{mins:02d}:{secs:02d}",
            "resolution": f"{width}x{height}",
            "size": f"{size_mb:.1f} MB",
            "fps": int(fps) if fps > 0 else 30,
            "thumb_path": thumb_path,
            "frame_count": frame_count
        }

class VideoExtractionWorker(QThread):
    progress = pyqtSignal(int)
    log_msg = pyqtSignal(str, str) # level, message
    finished = pyqtSignal(bool, str) # success, msg
    
    def __init__(self, video_path: str, extract_every_n_frames: int = 30, auto_label: bool = False):
        super().__init__()
        self.video_path = str(Path(video_path).resolve())
        self.extract_interval = extract_every_n_frames
        self.auto_label = auto_label
        self.is_stopped = False
        
    def run(self):
        self.log_msg.emit("info", f"Starting extraction for {Path(self.video_path).name}")
        
        if not os.path.exists(self.video_path):
            self.log_msg.emit("error", "Video file not found.")
            self.finished.emit(False, "File not found")
            return
            
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.log_msg.emit("error", "Failed to open video file (OpenCV error).")
            self.finished.emit(False, "OpenCV Failure")
            return
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = 1000 # Fallback
            
        dataset_name = Path(self.video_path).stem
        output_dir = Path("data/datasets") / dataset_name
        
        try:
            if output_dir.exists():
                shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            extracted = 0
            current_frame = 0
            
            while not self.is_stopped:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                if current_frame % self.extract_interval == 0:
                    out_path = output_dir / f"frame_{current_frame:06d}.jpg"
                    cv2.imwrite(str(out_path), frame)
                    extracted += 1
                    
                    if self.auto_label:
                        self.log_msg.emit("info", f"Auto-labeling not fully implemented (skipping {out_path.name})")
                        # Here you would call GoalMatcher or OCR to label the frame
                    
                current_frame += 1
                
                # Update progress every interval
                if current_frame % max(1, (total_frames // 100)) == 0:
                    pct = int((current_frame / total_frames) * 100)
                    self.progress.emit(min(pct, 100))
                    
        except Exception as e:
            self.log_msg.emit("error", f"Extraction crashed: {e}")
            self.finished.emit(False, str(e))
            cap.release()
            return
            
        cap.release()
        
        if self.is_stopped:
            self.log_msg.emit("warning", "Extraction stopped by user.")
            self.finished.emit(False, "Stopped")
        else:
            self.progress.emit(100)
            self.log_msg.emit("success", f"Extraction complete! Saved {extracted} frames to {output_dir}")
            self.finished.emit(True, str(output_dir))
            
    def stop(self):
        self.is_stopped = True
