class OverfittingMonitor:
    def __init__(self, max_gap: float = 0.10, window: int = 5):
        self.max_gap = max_gap
        self.window  = window
        self.train_h = []
        self.val_h   = []

    def update(self, train: float, val: float):
        self.train_h.append(train)
        self.val_h.append(val)

    def is_overfitting(self) -> bool:
        if len(self.train_h) < self.window:
            return False
        t = sum(self.train_h[-self.window:]) / self.window
        v = sum(self.val_h[-self.window:])   / self.window
        return (t - v) > self.max_gap

    def get_status(self) -> dict:
        if not self.train_h:
            return {"train": 0, "val": 0, "gap": 0, "status": "no_data"}
        t   = self.train_h[-1]
        v   = self.val_h[-1] if self.val_h else 0
        gap = round(t - v, 4)
        return {
            "train":  round(t,   4),
            "val":    round(v,   4),
            "gap":    gap,
            "status": "overfitting" if self.is_overfitting() else "healthy"
        }
