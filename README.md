# Transcriber

Local audio/video transcriber with a PyQt6 UI. Supports YouTube URLs and playlists.

## Requirements

- Python 3.10+
- `yt-dlp` in PATH
- `ffmpeg` in PATH

The app will auto-install `torch`, `torch-directml` (AMD), and `openai-whisper` if needed.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install PyQt6
```

## Run

```bash
python main.py
```

## Tool Paths

If `ffmpeg` or `yt-dlp` are not in PATH, set them in the Settings tab and the app will use those paths.

## Output

Transcripts are saved to `./transcripts/<video_id>.txt` with a metadata header and the full text.
