import os
import json
import logging
from pathlib import Path
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

def create_sync_app(models_root: Path):
    app = Flask(__name__)

    @app.route('/upload_replay', methods=['POST'])
    def upload_replay():
        """
        Expects a multipart request with 'metadata' (JSON) and multiple 'image_X' files.
        """
        try:
            model_name = request.form.get('model_name')
            run_id = request.form.get('run_id')
            metadata_str = request.form.get('metadata')
            
            if not model_name or not run_id:
                return jsonify({"error": "Missing model_name or run_id"}), 400

            # Target directory: models/[model_name]/live_recordings/[run_id]
            target_dir = models_root / model_name / "live_recordings" / run_id
            target_dir.mkdir(parents=True, exist_ok=True)

            # Save metadata
            if metadata_str:
                with open(target_dir / "metadata.json", "w") as f:
                    f.write(metadata_str)

            # Save uploaded images
            for file_key in request.files:
                file = request.files[file_key]
                file.save(target_dir / file.filename)

            logger.info(f"Received replay {run_id} for model {model_name}")
            return jsonify({"status": "success", "run_id": run_id}), 200

        except Exception as e:
            logger.error(f"Sync error: {e}")
            return jsonify({"error": str(e)}), 500

    return app

def start_sync_service(models_root: Path, port: int = 8765):
    """Entry point to run the sync listener in a background thread."""
    app = create_sync_app(models_root)
    # Using threaded=True to handle multiple parallel uploads from the phone
    app.run(host='0.0.0.0', port=port, threaded=True, debug=False)
