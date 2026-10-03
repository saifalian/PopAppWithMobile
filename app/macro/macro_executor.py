import logging
import time
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

class MacroExecutor(QThread):
    log_line = pyqtSignal(str)
    pipeline_finished = pyqtSignal(bool)

    def __init__(self, steps: list, parent=None):
        super().__init__(parent)
        self.steps = steps
        self.running = False

    def run(self):
        self.running = True
        self.log_line.emit("[SYSTEM] Starting Pipeline Execution...")
        
        try:
            for i, step in enumerate(self.steps):
                if not self.running:
                    self.log_line.emit(f"[SYSTEM] Pipeline canceled at step {i+1}")
                    break
                    
                self.log_line.emit(f"> Executing Step {i+1}: {step}")
                # Mock execution logic replacing real module calls for now
                time.sleep(1.0)
                self.log_line.emit(f"  Step {i+1} complete ✓")
                
            if self.running:
                self.log_line.emit("[SYSTEM] Pipeline Completed Successfully.")
                self.pipeline_finished.emit(True)
            else:
                self.pipeline_finished.emit(False)
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.log_line.emit(f"[ERROR] Pipeline crashed: {e}")
            self.pipeline_finished.emit(False)

    def stop(self):
        self.running = False
