---
title: MaseNet Plant Detector API
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# AgriVision: Plant Disease Detector

AgriVision is a full-stack plant disease inference demo:
- A **FastAPI backend** that loads a custom-trained ViT model checkpoint and predicts top classes from leaf images.
- A **plain HTML/CSS/JS frontend** for upload + preset image testing, with modern result cards and confidence bars.

## Deploy On Hugging Face Spaces (Docker)

1. Create a new Space on Hugging Face with SDK set to `Docker`.
2. Push this repository to that Space repo.
3. The Space will build using `Dockerfile` and start the API on port `7860`.
4. The app downloads model weights from:
   - `https://huggingface.co/shivamhface/masenet-plant/resolve/main/mase_model.pth`

Optional Space variables:
- `MODEL_WEIGHTS_URL` (override default model URL)
- `MODEL_WEIGHTS_AUTH_TOKEN` (private URL bearer token)
- `MODEL_WEIGHTS_SHA256` (checksum validation)
- `MODEL_DEVICE` (default `cpu`)

---

## What Is In This Repo

Core runtime files:
- `server.py` - FastAPI API, model loading, inference, validation, endpoints.
- `mase_class_names.json` - Ordered class label list used by inference.
- `mase_model.pth` - Trained model weights checkpoint (optional local cache when `MODEL_WEIGHTS_URL` is used).
- `disease_knowledge.py` - Disease metadata helper module (for enrichment/extension).
- `index.html`, `styles.css`, `app.js` - Frontend demo UI.
- `requirements.txt` - Runtime Python dependencies.

Optional components (gitignored by default):
- `plantvillage/` - Dataset-style class folders used for model work.
- `tests/` - API test suite.
- `requirements-dev.txt` - Dev/test dependencies.
- `start_server.bat` - Optional Windows startup helper.

Note:
- `.gitignore` affects new/untracked files. If any of these are already tracked in git, untrack them with `git rm --cached <path>`.

Local Python artifacts (gitignored by default):
- `venv/` or `.venv/` - Local virtual environment.
- `__pycache__/`, `*.pyc` - Python runtime cache files.

---

## How It Is Built

### 1) Backend inference pipeline
In `server.py`, the backend:
1. Loads class labels from `mase_class_names.json`.
2. Builds `MASENet` model architecture.
3. Loads weights from local `mase_model.pth` or downloads from `MODEL_WEIGHTS_URL`.
4. Applies preprocessing (`Resize(224,224)` + `ToTensor`).
5. Runs forward pass, softmax, and returns top-3 predictions.

### 2) API layer
Built with FastAPI:
- `GET /` health and model status.
- `POST /analyze` multipart image upload endpoint.
- `POST /analyze-base64` base64 image endpoint.

### 3) Frontend
Frontend is framework-free and uses:
- Drag-and-drop + file upload.
- Preset category/image selection (`PRESET_LIBRARY` in `app.js`).
- Optional metadata inputs.
- Loading state, top prediction + top-3 cards, and confidence bars.

---

## Quick Start

### Prerequisites
- Python 3.9+ recommended.
- Git (optional).

### 1) Install dependencies
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### 2) Start backend
If you host model weights outside git (recommended), set a direct HTTPS file URL before startup:

```bash
# Windows PowerShell
$env:MODEL_WEIGHTS_URL="https://.../mase_model.pth"
# optional: bearer token for private URLs (HF/S3 signed gateway/etc.)
$env:MODEL_WEIGHTS_AUTH_TOKEN="YOUR_TOKEN"
# optional: verify downloaded file integrity
$env:MODEL_WEIGHTS_SHA256="YOUR_SHA256_HEX"
```

```bash
python -m uvicorn server:app --reload --port 8000
```

Optional (if you keep `start_server.bat` locally):
```bat
start_server.bat
```

### 3) Serve frontend
Use a static server from this repo root:
```bash
python -m http.server 5501 --bind 127.0.0.1
```

Open:
- `http://127.0.0.1:5501/index.html`

If you open the frontend on another device (phone/tablet), use your machine IP, for example:
- `http://192.168.1.20:5501/index.html`
The frontend now auto-targets backend at the same host on port `8000`.

Why this matters:
- Backend default CORS includes `http://127.0.0.1:5501`.
- Opening `index.html` directly via `file://` can cause CORS issues.

---

## How To Use The App

1. Open the frontend page.
2. Upload an image or click a preset sample.
3. Optionally fill:
   - Plant Name
   - Soil Moisture
   - Location (frontend field; currently future-facing)
4. Click **Analyze**.
5. Review:
   - Main prediction
   - Confidence
   - Top 3 predictions

---

## API Reference

### `GET /`
Health endpoint.

Example response:
```json
{
  "status": "running",
  "model": "MASE Model",
  "model_weights_path": "C:/.../mase_model.pth",
  "remote_model_configured": true,
  "model_loaded": true,
  "message": "Plant Disease Detector API is ready!"
}
```

### `POST /analyze`
Multipart form endpoint.

Form fields:
- `file` (required, image/*)
- `soil_type` (optional)
- `temperature` (optional)
- `humidity` (optional)
- `moisture` (optional)

### `POST /analyze-preset`
Preset image endpoint (used by current frontend), avoids browser-side image fetch.

Form fields:
- `preset_src` (required, e.g. `/presets/Potato/img1.JPG`)
- `soil_type` (optional)
- `temperature` (optional)
- `humidity` (optional)
- `moisture` (optional)
- any extra metadata keys (optional)

Example success response:
```json
{
  "detected_plant": "Tomato___Early_blight",
  "diseases": [
    { "name": "Tomato___Early_blight", "confidence": 92.14 },
    { "name": "Tomato___Late_blight", "confidence": 6.83 },
    { "name": "Tomato___healthy", "confidence": 1.03 }
  ]
}
```

### `POST /analyze-base64`
Alternative form endpoint with:
- `image_base64` (required)
- optional metadata fields same as above.

---

## Preset Images (Frontend)

The UI loads presets from backend endpoint `GET /preset-library`.

To use your own preset images:
1. Add files under folders like:
   - `presets/Tomato/...`
   - `presets/Potato/...`
   - `presets/Pepper/...`

Optional: auto-fill form fields from JSON metadata:
1. Create or edit `presets/preset_metadata.json`.
2. Recommended format:
```json
{
  "Tomato/leaf_01.jpg": {
    "soil_type": "loamy",
    "temperature": "28",
    "humidity": "65",
    "moisture": "40",
    "ph": "6.4"
  }
}
```
3. Keys can be:
   - relative image path (`Tomato/leaf_01.jpg`), or
   - use `entries` array with `folder` + `filename`.
4. Extra keys are allowed and are sent in analyze form data.
5. CSV fallback is still supported via `presets/preset_metadata.csv` when JSON file is absent.

---

## Configuration (Environment Variables)

Supported in `server.py`:
- `LOG_LEVEL` (default: `INFO`)
- `MAX_IMAGE_MB` (default: `10`)
- `MIN_CONFIDENCE` (default: `0.15`)  
  Note: compared against percentage output internally (`* 100`).
- `MODEL_CLASS_NAMES_PATH` (default: `mase_class_names.json`)
- `MODEL_WEIGHTS_PATH` (default: `mase_model.pth`)
- `MODEL_WEIGHTS_URL` (defaults to `https://huggingface.co/shivamhface/masenet-plant/resolve/main/mase_model.pth`; override with your own URL)
- `MODEL_WEIGHTS_AUTH_TOKEN` (optional bearer token for private model URLs)
- `MODEL_WEIGHTS_SHA256` (optional checksum verification)
- `MODEL_DOWNLOAD_FORCE` (default: `0`; set `1` to force fresh download on startup)
- `MODEL_DOWNLOAD_TIMEOUT_SECONDS` (default: `900`)
- `CORS_ORIGINS` (comma-separated origins)
- `MAX_PRESET_IMAGES_PER_PLANT` (default: `0` = no limit)
- `PRESETS_DIR` (default: `presets`)
- `PRESET_METADATA_JSON` (default: `preset_metadata.json`, resolved inside `PRESETS_DIR`)
- `PRESET_METADATA_CSV` (default: `preset_metadata.csv`, resolved inside `PRESETS_DIR`)

Also present (legacy/not active in current checkpoint flow):
- `MODEL_DEVICE`
- `MODEL_IDS`

---

## Testing

If you keep the optional test files (`tests/`, `requirements-dev.txt`), install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

Run tests:
```bash
pytest
```

Current tests focus on API behavior via monkeypatching/mocked classification.

---

## Troubleshooting

### `model_not_loaded`
Check that these files exist in repo root:
- `mase_class_names.json`
- `mase_model.pth` (required only if `MODEL_WEIGHTS_URL` is not set)

If using remote weights:
- Ensure `MODEL_WEIGHTS_URL` is reachable from your host.
- If URL is private, set `MODEL_WEIGHTS_AUTH_TOKEN`.
- If checksum is configured, ensure `MODEL_WEIGHTS_SHA256` matches the file.

### CORS error from browser
- Serve frontend from `http://127.0.0.1:5501` (or set `CORS_ORIGINS` accordingly).

### Preset image not loading
- Verify file paths in `PRESET_LIBRARY`.
- Ensure files are served by your static server.

### Large image upload rejected
- Default limit is 10MB.
- Increase with `MAX_IMAGE_MB`.

---

## Notes

- `disease_knowledge.py` is available for richer disease explanations and can be integrated/expanded further.
- `split.py` is currently an empty placeholder file.
