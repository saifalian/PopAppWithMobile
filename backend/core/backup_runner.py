"""
Backup system.
Copies models, macros, datasets, configs to backup location.
Handles scheduled and manual backups.
Enforces keep-last-N-days policy.
"""
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class BackupRunner:

    def __init__(self, settings_manager):
        self._settings = settings_manager

    def run_backup(
        self,
        progress_cb: Optional[Callable[[str], None]] = None
    ) -> dict:
        """
        Execute a full backup.
        progress_cb(message) called with status updates.
        Returns result dict.
        """
        s            = self._settings
        backup_root  = Path(s.get("backup_path", "backups"))
        ts           = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir   = backup_root / f"backup_{ts}"

        def log(msg: str):
            logger.info(f"Backup: {msg}")
            if progress_cb:
                progress_cb(msg)

        log(f"Starting backup to {backup_dir}")
        backup_dir.mkdir(parents=True, exist_ok=True)

        total_size = 0
        errors     = []

        # What to back up — controlled by settings checkboxes
        tasks = [
            {
                "name":    "Model weights and checkpoints",
                "src":     Path("models"),
                "dst":     backup_dir / "models",
                "enabled": True,
            },
            {
                "name":    "Macros",
                "src":     Path("macros"),
                "dst":     backup_dir / "macros",
                "enabled": True,
            },
            {
                "name":    "Data outputs",
                "src":     Path("data"),
                "dst":     backup_dir / "data",
                "enabled": True,
            },
        ]

        for task in tasks:
            if not task["enabled"]:
                continue
            if not task["src"].exists():
                log(f"Skip {task['name']} (not found)")
                continue
            try:
                log(f"Copying {task['name']}...")
                shutil.copytree(
                    str(task["src"]), str(task["dst"]),
                    dirs_exist_ok=True
                )
                size = _dir_size(task["dst"])
                total_size += size
                log(f"  ✓ {task['name']} ({size // (1024*1024)} MB)")
            except Exception as e:
                errors.append(f"{task['name']}: {e}")
                log(f"  ✗ {task['name']}: {e}")

        # Copy config files
        for fname in ["settings.json", "calibration.json", "modelfactory.db"]:
            src = Path(fname)
            if src.exists():
                try:
                    shutil.copy(str(src), str(backup_dir / fname))
                    log(f"  ✓ {fname}")
                except Exception as e:
                    errors.append(f"{fname}: {e}")

        # Write backup manifest
        manifest = {
            "timestamp":    ts,
            "total_size_mb": total_size // (1024 * 1024),
            "errors":       errors,
            "success":      len(errors) == 0,
        }
        with open(backup_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Clean old backups
        keep_days = s.get("backup_keep_days", 7)
        cleaned   = self._cleanup_old_backups(backup_root, keep_days)
        if cleaned:
            log(f"Cleaned {cleaned} old backup(s)")

        log(
            f"Backup complete: {total_size // (1024*1024)} MB "
            f"{'✓' if not errors else '✗ with errors'}"
        )

        return {
            "success":      len(errors) == 0,
            "path":         str(backup_dir),
            "size_mb":      total_size // (1024 * 1024),
            "errors":       errors,
            "timestamp":    ts,
        }

    def list_backups(self) -> list:
        backup_root = Path(
            self._settings.get("backup_path", "backups")
        )
        if not backup_root.exists():
            return []

        backups = []
        for d in sorted(backup_root.iterdir(), reverse=True):
            manifest_path = d / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        m = json.load(f)
                    m["path"] = str(d)
                    m["name"] = d.name
                    backups.append(m)
                except Exception:
                    pass
        return backups

    def restore_backup(
        self,
        backup_path: str,
        progress_cb: Optional[Callable] = None,
    ) -> bool:
        """
        Restore from a backup. Overwrites current files.
        Returns True on success.
        """
        src = Path(backup_path)
        if not src.exists():
            return False

        def log(msg):
            logger.info(f"Restore: {msg}")
            if progress_cb:
                progress_cb(msg)

        log(f"Restoring from {backup_path}")

        for item in ["models", "macros", "data"]:
            src_item = src / item
            dst_item = Path(item)
            if src_item.exists():
                try:
                    if dst_item.exists():
                        shutil.rmtree(str(dst_item))
                    shutil.copytree(str(src_item), str(dst_item))
                    log(f"  ✓ Restored {item}")
                except Exception as e:
                    log(f"  ✗ {item}: {e}")
                    return False

        for fname in ["settings.json", "calibration.json"]:
            src_file = src / fname
            if src_file.exists():
                try:
                    shutil.copy(str(src_file), fname)
                    log(f"  ✓ Restored {fname}")
                except Exception as e:
                    log(f"  ✗ {fname}: {e}")

        log("Restore complete ✓")
        return True

    def _cleanup_old_backups(
        self,
        backup_root: Path,
        keep_days:   int,
    ) -> int:
        """Delete backups older than keep_days. Returns count deleted."""
        if not backup_root.exists():
            return 0
        cutoff  = datetime.now() - timedelta(days=keep_days)
        deleted = 0
        for d in backup_root.iterdir():
            if not d.is_dir():
                continue
            try:
                mtime = datetime.fromtimestamp(d.stat().st_mtime)
                if mtime < cutoff:
                    shutil.rmtree(str(d))
                    deleted += 1
                    logger.info(f"Deleted old backup: {d.name}")
            except Exception as e:
                logger.warning(f"Cleanup error for {d.name}: {e}")
        return deleted


def _dir_size(path: Path) -> int:
    """Return total size of directory in bytes."""
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except Exception:
                    pass
    return total
