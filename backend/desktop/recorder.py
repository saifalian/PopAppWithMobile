import logging
import time
from pynput import mouse, keyboard

logger = logging.getLogger(__name__)


class ActionRecorder:
    def __init__(self):
        self.recording    = False
        self.paused       = False
        self.events       = []
        self._start       = None
        self._pause_start = None
        self._total_paused = 0.0
        self._ml          = None
        self._kl          = None

    def start(self, start_paused=False):
        self.events       = []
        self._start       = time.time()
        self._total_paused = 0.0
        self.recording    = True
        self.paused       = start_paused
        if start_paused:
            self._pause_start = self._start
            
        self._ml = mouse.Listener(
            on_click=self._click, on_scroll=self._scroll
        )
        self._kl = keyboard.Listener(on_press=self._key)
        self._ml.start()
        self._kl.start()
        logger.info(f"Recording started{' (paused)' if start_paused else ''}")

    def pause(self):
        if self.recording and not self.paused:
            self.paused = True
            self._pause_start = time.time()
            logger.info("Recording paused")

    def resume(self):
        if self.recording and self.paused:
            self.paused = False
            self._total_paused += time.time() - self._pause_start
            logger.info("Recording resumed")

    def stop(self) -> list:
        self.recording = False
        if self.paused:
            self._total_paused += time.time() - self._pause_start
            self.paused = False
        if self._ml:
            self._ml.stop()
        if self._kl:
            self._kl.stop()
        steps = self._to_steps(self.events)
        logger.info(f"Recording stopped: {len(steps)} steps")
        return steps

    def _click(self, x, y, button, pressed):
        if self.recording and not self.paused and pressed:
            self.events.append({
                "type": "click",
                "x": int(x), "y": int(y),
                "t": time.time() - self._start - self._total_paused
            })

    def _scroll(self, x, y, dx, dy):
        if self.recording and not self.paused:
            self.events.append({
                "type": "scroll",
                "amount": int(dy * 3),
                "t": time.time() - self._start - self._total_paused
            })

    def _key(self, key):
        if not self.recording or self.paused:
            return
        try:
            k = key.char if hasattr(key, 'char') and key.char else key.name
        except AttributeError:
            k = str(key).replace("Key.", "")
        self.events.append({
            "type": "key", "key": k,
            "t": time.time() - self._start - self._total_paused
        })

    def _to_steps(self, events: list) -> list:
        if not events:
            return []
        steps   = []
        prev_t  = 0
        for ev in events:
            t = ev.get("t", 0)
            if t - prev_t > 0.3:
                steps.append({
                    "type": "wait",
                    "seconds": round(t - prev_t, 2)
                })
            step = {k: v for k, v in ev.items() if k != "t"}
            steps.append(step)
            prev_t = t
        return steps
