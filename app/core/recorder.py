"""
Input recorder using pynput.
Used for recording macros and generating training data passively.
"""
import logging
import time
import threading

logger = logging.getLogger(__name__)

class Recorder:
    def __init__(self):
        self.events = []
        self._recording = False
        self._start_time = 0
        self.mouse_listener = None
        self.kb_listener = None

    def start(self):
        """Start listening to global mouse and keyboard events."""
        if self._recording:
            return

        try:
            from pynput import mouse, keyboard
            
            self._recording = True
            self.events = []
            self._start_time = time.time()
            
            self.mouse_listener = mouse.Listener(
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            self.kb_listener = keyboard.Listener(
                on_press=self._on_press
            )
            
            self.mouse_listener.start()
            self.kb_listener.start()
            logger.info("Recording started...")
        except ImportError:
            logger.error("pynput is not installed. Recording disabled.")
        except Exception as e:
            logger.error(f"Failed to start recorder: {e}")

    def stop(self):
        """Stop listening and return the recorded events."""
        if not self._recording:
            return []

        self._recording = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.kb_listener:
            self.kb_listener.stop()
            
        logger.info(f"Recording stopped. Captured {len(self.events)} events.")
        return self.events

    def is_recording(self):
        return self._recording

    def _on_click(self, x, y, button, pressed):
        if pressed and self._recording:
            t = time.time() - self._start_time
            self.events.append({
                'type': 'click',
                'x': int(x),
                'y': int(y),
                'button': str(button).replace('Button.', ''),
                'time': round(t, 3)
            })

    def _on_scroll(self, x, y, dx, dy):
        if self._recording:
            t = time.time() - self._start_time
            self.events.append({
                'type': 'scroll',
                'x': int(x),
                'y': int(y),
                'dx': int(dx),
                'dy': int(dy),
                'time': round(t, 3)
            })

    def _on_press(self, key):
        if self._recording:
            t = time.time() - self._start_time
            try:
                k = key.char
            except AttributeError:
                # Special keys (e.g. Key.enter)
                k = str(key).replace('Key.', '')
                
            self.events.append({
                'type': 'key',
                'key': k,
                'time': round(t, 3)
            })
