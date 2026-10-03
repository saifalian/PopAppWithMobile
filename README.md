# Pop App With Mobile

Pop App With Mobile is a mixed Python and Android automation/modeling project. It includes a desktop-facing Python app, backend vision/video modules, macro data structures, trained model artifacts, and an Android mobile subproject under `app/mobile`.

The repository is configured to keep source code in Git while excluding generated model files, recordings, logs, virtual environments, and build output.

## Features

- Python main launcher and settings
- Backend vision modules for screen capture, OCR, heatmaps, goal matching, and cluster detection
- Video processing module
- Macro and model-oriented workflow files
- Android mobile app module
- Batch launcher for local startup

## Tech Stack

- Python
- Computer vision / OCR modules
- Android Gradle project
- Local JSON settings and macro definitions

## Project Layout

```text
backend/
├── video/
└── vision/
app/mobile/
main.py
settings.json
requirements.txt
start_model_factory.bat
```

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open `app/mobile` in Android Studio to work on the mobile component.

## Notes

Large generated model outputs, extracted frames, recordings, and logs are excluded from Git. Keep those artifacts in local storage or a release/artifact system instead of the source repository.

