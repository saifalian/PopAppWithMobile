# Pop App With Mobile

Pop App With Mobile is a mixed Python and Android project.

In simple words, this project contains a desktop-style Python app, backend vision tools, video processing files, macro/model work, and an Android mobile app inside `app/mobile`.

The project is set up so source code can be uploaded to GitHub while large generated files, recordings, logs, virtual environments, and build output stay out of Git.

## What This Project Can Do

- Run from a Python main launcher.
- Use backend vision modules.
- Work with screen capture, OCR, heatmaps, goal matching, and cluster detection.
- Include video processing code.
- Store macro and model workflow files.
- Include an Android mobile app module.
- Start locally with a batch launcher.

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

Large model outputs, extracted frames, recordings, and logs are excluded from Git.

Keep those files in local storage or another artifact system instead of saving them directly in the source repository.
