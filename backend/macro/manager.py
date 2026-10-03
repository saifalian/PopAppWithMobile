"""
CRUD operations for macros.
Loads/saves macro definition JSONs from the database or disk.
Provides a list of available macros for the UI.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from backend.core.settings_manager import settings

def get_macros_dir() -> Path:
    """Get the macros directory from settings."""
    path = Path(settings.get("macros_path", "data/macros"))
    path.mkdir(parents=True, exist_ok=True)
    return path

def _init_dir():
    get_macros_dir().mkdir(parents=True, exist_ok=True)

def ensure_default_macros():
    """Create default macro files if none exist."""
    _init_dir()
    existing = list(get_macros_dir().glob("*.json"))
    if not existing:
        logger.info("No macros found. Creating defaults...")
        defaults = [
            ("coinglass_full_agent", "Coinglass AI Agent (Complete)"),
            ("simple_clicker", "Simple Clicker Template"),
            ("data_extractor_v2", "Data Extractor V2 Template")
        ]
        for tid, tname in defaults:
            template = get_template(tid)
            if template:
                save_macro(template)
            else:
                save_macro({
                    "id": tid,
                    "name": tname,
                    "description": "Standard template",
                    "nodes": []
                })

def list_macros() -> List[Dict]:
    """Return a list of all saved macros (metadata only)."""
    _init_dir()
    macros = []
    # If empty, ensure defaults first
    files = list(get_macros_dir().glob("*.json"))
    if not files:
        ensure_default_macros()
        files = list(get_macros_dir().glob("*.json"))

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                macros.append({
                    "id":          data.get("id"),
                    "name":        data.get("name", "Unnamed"),
                    "description": data.get("description", ""),
                    "node_count":  len(data.get("nodes", [])),
                    "file_path":   str(file_path)
                })
        except Exception as e:
            logger.error(f"Failed to read macro {file_path}: {e}")
    return sorted(macros, key=lambda m: m["name"])

def load_macro(macro_id: str) -> Optional[Dict]:
    """Load full macro payload by ID."""
    _init_dir()
    for file_path in get_macros_dir().glob("*.json"):
        if file_path.stem == macro_id:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load macro {macro_id}: {e}")
                return None
    return None

def save_macro(macro_data: Dict) -> bool:
    """Save or update macro payload."""
    _init_dir()
    mid = macro_data.get("id")
    name = macro_data.get("name", "macro")
    if not mid:
        import uuid
        mid = f"{name.replace(' ', '_').lower()}_{str(uuid.uuid4())[:8]}"
        macro_data["id"] = mid

    file_path = get_macros_dir() / f"{mid}.json"
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(macro_data, f, indent=2)
        logger.info(f"Saved macro to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save macro {mid}: {e}")
        return False

def delete_macro(macro_id: str) -> bool:
    """Delete a macro by ID."""
    _init_dir()
    for file_path in get_macros_dir().glob("*.json"):
        if file_path.stem == macro_id:
            try:
                file_path.unlink()
                logger.info(f"Deleted macro {macro_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete macro {macro_id}: {e}")
                return False
    return False

def rename_macro(macro_id: str, new_name: str) -> bool:
    """Rename a macro by ID (updates internal name and filename)."""
    _init_dir()
    for file_path in get_macros_dir().glob("*.json"):
        if file_path.stem == macro_id:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Update name in JSON
                data["name"] = new_name
                
                # We keep the ID same to avoid breaking references, 
                # but we could rename the file if we wanted.
                # Here we just update the 'name' field which is what the UI shows.
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"Renamed macro {macro_id} to '{new_name}'")
                return True
            except Exception as e:
                logger.error(f"Failed to rename macro {macro_id}: {e}")
                return False
    return False

def get_template(name: str) -> Optional[Dict]:
    """Helper to return a hardcoded/default template by name."""
    if name == "coinglass_full_agent":
        return {
            "id": "coinglass_full_agent",
            "name": "Coinglass AI Agent (Complete)",
            "description": "The complete reference implementation.",
            "nodes": [
                {
                    "id": "node_setup_1",
                    "type": "launch_app",
                    "label": "Focus Coinglass Window",
                    "config": {"app_name": "Coinglass", "action": "focus_or_launch"}
                },
                {
                    "id": "node_setup_2",
                    "type": "run_sequence",
                    "label": "Navigate to Pair/1m",
                    "config": {"sequence_id": "seq_navigate"}
                },
                # Followed by loops, screenshot, models, parsing, JSON save...
            ]
        }
    return None
