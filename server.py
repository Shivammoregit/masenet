"""
Plant Disease Detector API Server - Using ViT Model
Uses a pre-trained Vision Transformer for accurate disease classification.
"""

import base64
import csv
import hashlib
import io
import json
import logging
import os
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from model.MASENET_MODEL import MASENet
from disease_knowledge import get_disease_info
from torchvision import transforms
# Initialize FastAPI app
app = FastAPI(
    title="Plant Disease Detector API",
    description="AI-powered plant disease detection using ViT model",
    version="2.0.0"
)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("plantdoc")

MAX_IMAGE_MB = int(os.getenv("MAX_IMAGE_MB", "10"))
MAX_IMAGE_BYTES = MAX_IMAGE_MB * 1024 * 1024
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.15"))
MODEL_DEVICE = os.getenv("MODEL_DEVICE", "auto")
PRESETS_DIR_ENV = os.getenv("PRESETS_DIR", "presets")
PRESET_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
BASE_DIR = Path(__file__).resolve().parent
MODEL_CLASS_NAMES_PATH_ENV = os.getenv("MODEL_CLASS_NAMES_PATH", "mase_class_names.json")
_model_class_names_path = Path(MODEL_CLASS_NAMES_PATH_ENV)
MODEL_CLASS_NAMES_PATH = _model_class_names_path if _model_class_names_path.is_absolute() else BASE_DIR / _model_class_names_path
MODEL_WEIGHTS_PATH_ENV = os.getenv("MODEL_WEIGHTS_PATH", "mase_model.pth")
_model_weights_path = Path(MODEL_WEIGHTS_PATH_ENV)
MODEL_WEIGHTS_PATH = _model_weights_path if _model_weights_path.is_absolute() else BASE_DIR / _model_weights_path
DEFAULT_MODEL_WEIGHTS_URL = "https://huggingface.co/shivamhface/masenet-plant/resolve/main/mase_model.pth"
MODEL_WEIGHTS_URL = os.getenv("MODEL_WEIGHTS_URL", DEFAULT_MODEL_WEIGHTS_URL).strip()
MODEL_WEIGHTS_AUTH_TOKEN = os.getenv("MODEL_WEIGHTS_AUTH_TOKEN", "").strip()
MODEL_WEIGHTS_SHA256 = os.getenv("MODEL_WEIGHTS_SHA256", "").strip().lower()
MODEL_DOWNLOAD_FORCE = os.getenv("MODEL_DOWNLOAD_FORCE", "0").strip().lower() in {"1", "true", "yes", "on"}
try:
    MODEL_DOWNLOAD_TIMEOUT_SECONDS = int(os.getenv("MODEL_DOWNLOAD_TIMEOUT_SECONDS", "900"))
except ValueError:
    MODEL_DOWNLOAD_TIMEOUT_SECONDS = 900
_presets_path = Path(PRESETS_DIR_ENV)
PRESETS_DIR = _presets_path if _presets_path.is_absolute() else BASE_DIR / _presets_path
PRESET_METADATA_JSON_ENV = os.getenv("PRESET_METADATA_JSON", "preset_metadata.json")
_preset_metadata_json_path = Path(PRESET_METADATA_JSON_ENV)
PRESET_METADATA_JSON = _preset_metadata_json_path if _preset_metadata_json_path.is_absolute() else PRESETS_DIR / _preset_metadata_json_path
PRESET_METADATA_CSV_ENV = os.getenv("PRESET_METADATA_CSV", "preset_metadata.csv")
_preset_metadata_csv_path = Path(PRESET_METADATA_CSV_ENV)
PRESET_METADATA_CSV = _preset_metadata_csv_path if _preset_metadata_csv_path.is_absolute() else PRESETS_DIR / _preset_metadata_csv_path
PRESET_METADATA_IDENTIFIER_KEYS = {
    "image",
    "image_path",
    "src",
    "folder",
    "filename",
    "file",
    "plant",
    "plant_folder",
}

try:
    MAX_PRESET_IMAGES_PER_PLANT = int(os.getenv("MAX_PRESET_IMAGES_PER_PLANT", "0"))
    if MAX_PRESET_IMAGES_PER_PLANT < 0:
        MAX_PRESET_IMAGES_PER_PLANT = 0
except ValueError:
    MAX_PRESET_IMAGES_PER_PLANT = 0

PRESETS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CORS_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5501",
]
CORS_ORIGINS_ENV = os.getenv("CORS_ORIGINS")
if CORS_ORIGINS_ENV:
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_ENV.split(",") if origin.strip()]
else:
    CORS_ORIGINS = DEFAULT_CORS_ORIGINS

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/presets", StaticFiles(directory=str(PRESETS_DIR), check_dir=False), name="presets")

# ==================== Model Loading ====================
logger.info("Loading Plant Disease Detection Model...")

model = None
class_names = []
model_loaded = False
model_name = "MASE Model"
# Try different models in order of preference
# MODELS_TO_TRY = [
#     ("wambugu71/crop_leaf_diseases_vit", "ViT Crop Disease Model"),
#     ("ozair23/mobilenet_v2_1.0_224-finetuned-plantdisease", "MobileNet PlantDisease"),
#     ("linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification", "MobileNet PlantVillage"),
# ]
transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
])
MODEL_IDS_ENV = os.getenv("MODEL_IDS")
if MODEL_IDS_ENV:
    MODELS_TO_TRY = [(model_id.strip(), model_id.strip()) for model_id in MODEL_IDS_ENV.split(",") if model_id.strip()]


def resolve_device(device_setting: str) -> int:
    """Resolve MODEL_DEVICE to a transformers device id."""
    value = device_setting.lower().strip()
    if value in {"cpu", "-1"}:
        return -1
    if value in {"cuda", "gpu", "0"}:
        return 0
    if value.isdigit():
        return int(value)
    if value == "auto":
        return 0 if torch.cuda.is_available() else -1
    return -1


def file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash for checksum validation."""
    digest = hashlib.sha256()
    with file_path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_model_weights(download_url: str, destination_path: Path) -> None:
    """Download model weights from URL and replace destination atomically."""
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = destination_path.with_suffix(f"{destination_path.suffix}.download")
    headers = {}
    if MODEL_WEIGHTS_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {MODEL_WEIGHTS_AUTH_TOKEN}"

    request = Request(download_url, headers=headers)
    bytes_downloaded = 0
    try:
        with urlopen(request, timeout=MODEL_DOWNLOAD_TIMEOUT_SECONDS) as response, temp_path.open("wb") as output_file:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                output_file.write(chunk)
                bytes_downloaded += len(chunk)

        if MODEL_WEIGHTS_SHA256:
            downloaded_checksum = file_sha256(temp_path)
            if downloaded_checksum != MODEL_WEIGHTS_SHA256:
                raise RuntimeError("Downloaded model checksum does not match MODEL_WEIGHTS_SHA256.")

        temp_path.replace(destination_path)
        logger.info("Model weights downloaded (%0.2f MB).", bytes_downloaded / (1024 * 1024))
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise


def ensure_model_weights_file() -> Path:
    """Ensure model weights exist locally; download at startup when configured."""
    local_weights = MODEL_WEIGHTS_PATH
    file_exists = local_weights.is_file()
    checksum_mismatch = False

    if file_exists and not MODEL_DOWNLOAD_FORCE:
        if MODEL_WEIGHTS_SHA256:
            local_checksum = file_sha256(local_weights)
            if local_checksum == MODEL_WEIGHTS_SHA256:
                return local_weights
            checksum_mismatch = True
            logger.warning("Local model checksum mismatch. Re-downloading weights from remote URL.")
        else:
            return local_weights

    if not MODEL_WEIGHTS_URL:
        if checksum_mismatch:
            raise RuntimeError(
                "Local model checksum mismatch and MODEL_WEIGHTS_URL is not set for refresh."
            )
        if file_exists:
            return local_weights
        raise FileNotFoundError(
            f"Model weights not found at '{local_weights}' and MODEL_WEIGHTS_URL is not set."
        )

    logger.info("Downloading model weights from MODEL_WEIGHTS_URL to %s", local_weights)
    download_model_weights(MODEL_WEIGHTS_URL, local_weights)
    return local_weights


def load_model():
    global model, model_loaded, class_names

    try:
        with MODEL_CLASS_NAMES_PATH.open("r", encoding="utf-8") as f:
            class_names = json.load(f)

        weights_path = ensure_model_weights_file()
        model = MASENet(len(class_names))
        model.load_state_dict(torch.load(weights_path, map_location=device))

        model.to(device)
        model.eval()

        model_loaded = True
        logger.info("MASE model loaded successfully from %s.", weights_path)

    except Exception as e:
        logger.error("Model load failed: %s", str(e))


@app.on_event("startup")
async def startup_event():
    load_model()

def get_rarity_info(name: str) -> dict:
    """Derive rarity info for UI display."""
    n = name.lower()
    if "healthy" in n or "blight" in n or "spot" in n:
        return {"label": "Common", "cls": "common", "icon": "circle"}
    if "rust" in n or "rot" in n or "mold" in n:
        return {"label": "Moderate", "cls": "moderate", "icon": "exclamation-circle"}
    if "virus" in n or "mosaic" in n or "curl" in n:
        return {"label": "Rare", "cls": "rare", "icon": "exclamation-triangle"}
    return {"label": "Moderate", "cls": "moderate", "icon": "circle"}


def get_cause_info(name: str, is_healthy: bool) -> str:
    """Provide a brief cause summary."""
    if is_healthy:
        return "No disease - plant shows healthy growth."
    n = name.lower()
    if "blight" in n:
        return "Fungal pathogens spreading in humid conditions."
    if "spot" in n:
        return "Bacterial or fungal infection from poor air flow."
    if "mildew" in n:
        return "Fungal spores in high humidity environments."
    if "rust" in n:
        return "Rust fungi spread by wind-borne spores."
    if "rot" in n:
        return "Pathogens attacking plant tissue in moist conditions."
    if "virus" in n:
        return "Plant viruses transmitted by insects. No cure."
    return "Environmental stress or pathogen infection."


def get_plant_info(name: str) -> str:
    """Provide a short plant description for UI."""
    n = name.lower()
    if "tomato" in n:
        return "Tomato - Warm-season nightshade crop."
    if "potato" in n:
        return "Potato - Cool-season root vegetable."
    if "corn" in n:
        return "Corn - Warm-season grain crop."
    if "apple" in n:
        return "Apple - Temperate fruit tree."
    if "grape" in n:
        return "Grape - Woody vine fruit."
    if "pepper" in n:
        return "Pepper - Warm-season vegetable."
    if "strawberry" in n:
        return "Strawberry - Perennial fruit plant."
    return "Plant identified from visual characteristics."


def validate_image_bytes(image_bytes: bytes) -> None:
    """Validate image payload size."""
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Max {MAX_IMAGE_MB}MB."
        )


def resolve_preset_image_path(preset_src: str) -> Path:
    """Resolve and validate preset image path from preset src/url."""
    raw = (preset_src or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Preset image source is required.")

    parsed = urlparse(raw)
    path_value = parsed.path if parsed.scheme else raw
    path_value = unquote(path_value).replace("\\", "/").strip()

    prefix = "/presets/"
    if path_value.startswith(prefix):
        relative = path_value[len(prefix):]
    elif path_value.startswith("presets/"):
        relative = path_value[len("presets/"):]
    else:
        raise HTTPException(status_code=400, detail="Invalid preset image source.")

    relative = relative.lstrip("/")
    if not relative:
        raise HTTPException(status_code=400, detail="Invalid preset image source.")

    base_dir = PRESETS_DIR.resolve()
    candidate = (base_dir / relative).resolve()

    if base_dir not in candidate.parents and candidate != base_dir:
        raise HTTPException(status_code=400, detail="Invalid preset image path.")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Preset image not found.")
    if candidate.suffix.lower() not in PRESET_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported preset file type.")

    return candidate


def humanize_text(value: str) -> str:
    """Convert folder/file names into user-facing labels."""
    return " ".join(part.capitalize() for part in value.replace("_", " ").replace("-", " ").split())


def normalize_metadata_key(value: str) -> str:
    """Normalize metadata keys for stable matching."""
    return "_".join(str(value or "").strip().lower().replace("-", " ").split())


def normalize_image_identifier(value: str) -> str:
    """Normalize image identifiers from CSV and preset paths."""
    text = unquote(str(value or "").strip()).replace("\\", "/")
    text = text.lstrip("/")
    if text.lower().startswith("presets/"):
        text = text[len("presets/"):]
    return text.lower()


def extract_preset_metadata_entry(raw_entry: dict[str, object]) -> tuple[list[str], dict[str, str]]:
    """Normalize one metadata entry and compute lookup keys."""
    normalized_row: dict[str, str] = {}
    for raw_key, raw_value in raw_entry.items():
        key = normalize_metadata_key(raw_key)
        if not key:
            continue
        if isinstance(raw_value, (dict, list, tuple, set)):
            continue
        value = str(raw_value or "").strip()
        if value:
            normalized_row[key] = value

    if not normalized_row:
        return [], {}

    candidate_keys: list[str] = []
    image_value = normalized_row.get("image_path") or normalized_row.get("image") or normalized_row.get("src")
    if image_value:
        candidate_keys.append(normalize_image_identifier(image_value))

    folder = normalized_row.get("folder") or normalized_row.get("plant") or normalized_row.get("plant_folder")
    filename = normalized_row.get("filename") or normalized_row.get("file")
    if folder and filename:
        candidate_keys.append(normalize_image_identifier(f"{folder}/{filename}"))

    metadata_payload = {
        key: value
        for key, value in normalized_row.items()
        if key not in PRESET_METADATA_IDENTIFIER_KEYS
    }

    return [key for key in candidate_keys if key], metadata_payload


def load_preset_metadata_map_from_json() -> dict[str, dict[str, str]]:
    """Load preset metadata from JSON."""
    metadata_map: dict[str, dict[str, str]] = {}
    with PRESET_METADATA_JSON.open("r", encoding="utf-8") as json_file:
        payload = json.load(json_file)

    entries: list[dict[str, object]] = []
    if isinstance(payload, list):
        entries = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        if isinstance(payload.get("entries"), list):
            entries = [item for item in payload["entries"] if isinstance(item, dict)]
        else:
            for identifier, metadata in payload.items():
                if isinstance(metadata, dict):
                    entry: dict[str, object] = {"image_path": identifier}
                    entry.update(metadata)
                    entries.append(entry)

    for entry in entries:
        candidate_keys, metadata_payload = extract_preset_metadata_entry(entry)
        if not metadata_payload:
            continue
        for key in candidate_keys:
            metadata_map[key] = metadata_payload

    return metadata_map


def load_preset_metadata_map_from_csv() -> dict[str, dict[str, str]]:
    """Load preset metadata from CSV."""
    metadata_map: dict[str, dict[str, str]] = {}
    with PRESET_METADATA_CSV.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            return metadata_map

        for row in reader:
            candidate_keys, metadata_payload = extract_preset_metadata_entry(row)
            if not metadata_payload:
                continue
            for key in candidate_keys:
                metadata_map[key] = metadata_payload

    return metadata_map


def load_preset_metadata_map() -> dict[str, dict[str, str]]:
    """Load preset metadata map, preferring JSON and falling back to CSV."""
    if PRESET_METADATA_JSON.exists():
        try:
            return load_preset_metadata_map_from_json()
        except Exception as exc:
            logger.warning("Failed to load preset metadata JSON '%s': %s", PRESET_METADATA_JSON, exc)

    if PRESET_METADATA_CSV.exists():
        try:
            return load_preset_metadata_map_from_csv()
        except Exception as exc:
            logger.warning("Failed to load preset metadata CSV '%s': %s", PRESET_METADATA_CSV, exc)

    return {}


def build_preset_library() -> list[dict]:
    """Build preset metadata from folders under PRESETS_DIR."""
    library = []
    if not PRESETS_DIR.exists():
        return library

    metadata_map = load_preset_metadata_map()

    for plant_dir in sorted((item for item in PRESETS_DIR.iterdir() if item.is_dir()), key=lambda p: p.name.lower()):
        image_paths = []
        for file_path in sorted(plant_dir.iterdir(), key=lambda p: p.name.lower()):
            if file_path.is_file() and file_path.suffix.lower() in PRESET_EXTENSIONS:
                image_paths.append(file_path)
            if MAX_PRESET_IMAGES_PER_PLANT > 0 and len(image_paths) >= MAX_PRESET_IMAGES_PER_PLANT:
                break

        images = [
            {
                "label": humanize_text(path.stem),
                "src": f"/presets/{quote(plant_dir.name)}/{quote(path.name)}",
                "metadata": metadata_map.get(normalize_image_identifier(path.relative_to(PRESETS_DIR).as_posix()), {}),
            }
            for path in image_paths
        ]

        library.append(
            {
                "name": humanize_text(plant_dir.name),
                "folder": plant_dir.name,
                "images": images,
            }
        )

    return library


def parse_label(label: str) -> dict:
    """Parse model output label into structured info."""
    raw_label = (label or "").strip()
    is_healthy = "healthy" in raw_label.lower()

    if "___" in raw_label:
        plant_raw, disease_raw = raw_label.split("___", 1)
    else:
        clean_label = " ".join(raw_label.replace("_", " ").split())
        parts = clean_label.split(" ", 1)
        plant_raw = parts[0] if parts else "Unknown"
        disease_raw = parts[1] if len(parts) > 1 else clean_label

    plant = humanize_text(plant_raw.replace("(", " ").replace(")", " "))
    disease = "Healthy" if is_healthy else humanize_text(disease_raw)

    return {
        "plant": plant,
        "disease": disease,
        "is_healthy": is_healthy,
        "full_name": f"{plant} - {disease}",
        "disease_query": "healthy" if is_healthy else disease_raw
    }


def normalize_plant_key(value: str) -> str:
    """Normalize plant names for stable comparisons."""
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def extract_label_plant_raw(label: str) -> str:
    """Extract raw plant token from class label."""
    raw_label = (label or "").strip()
    if "___" in raw_label:
        plant_raw, _ = raw_label.split("___", 1)
        return plant_raw

    clean_label = " ".join(raw_label.replace("_", " ").split())
    parts = clean_label.split(" ", 1)
    return parts[0] if parts else ""


def label_matches_allowed_plant(label: str, allowed_key: str) -> bool:
    """Match folder plant name against class label plant name."""
    label_key = normalize_plant_key(extract_label_plant_raw(label))
    if not label_key or not allowed_key:
        return False

    return (
        label_key == allowed_key
        or label_key.startswith(allowed_key)
        or allowed_key.startswith(label_key)
    )


def classify_plant_disease(image: Image.Image, allowed_plant: str = None) -> dict:
    global model, model_loaded, class_names

    if not model_loaded or model is None:
        return {
            "error": "model_not_loaded",
            "message": "Model is not loaded.",
            "diseases": []
        }

    try:
        image = transform(image).unsqueeze(0).to(device)

        with torch.no_grad():
             
            outputs = model(image)
            probs = torch.softmax(outputs, dim=1)

        prediction_indices: list[int] = []
        prediction_probs: list[float] = []

        if allowed_plant:
            allowed_key = normalize_plant_key(allowed_plant)
            candidate_indices = [
                idx
                for idx, label in enumerate(class_names)
                if label_matches_allowed_plant(label, allowed_key)
            ]

            if not candidate_indices:
                return {
                    "error": "plant_restriction_mismatch",
                    "message": "Selected image category is not configured in model classes.",
                    "diseases": []
                }

            candidate_probs = probs[0, candidate_indices]
            top_k = min(3, len(candidate_indices))
            top_probs, local_top_indices = torch.topk(candidate_probs, top_k)
            prediction_indices = [candidate_indices[idx.item()] for idx in local_top_indices]
            prediction_probs = [top_probs[i].item() for i in range(top_k)]
        else:
            top_k = min(3, probs.shape[1])
            top_probs, top_indices = torch.topk(probs, top_k)
            prediction_indices = [idx.item() for idx in top_indices[0]]
            prediction_probs = [top_probs[0][i].item() for i in range(top_k)]

        diseases = []

        for idx, prob in zip(prediction_indices, prediction_probs):
            confidence = round(prob * 100, 2)
            label = class_names[idx]
            info = parse_label(label)

            disease_details = get_disease_info(info["disease_query"])
            symptoms = disease_details.get("symptoms") or []
            treatment = disease_details.get("treatment") or "Consult a local agricultural expert."
            cause = get_cause_info(info["disease_query"], info["is_healthy"])
            rarity = get_rarity_info(info["disease_query"])

            diseases.append(
                {
                    "name": info["full_name"],
                    "raw_name": label,
                    "plant": info["plant"],
                    "disease": info["disease"],
                    "confidence": confidence,
                    "cause": cause,
                    "treatment": treatment,
                    "symptoms": symptoms,
                    "rarity": rarity,
                    "description": disease_details.get("description"),
                    "reasoning": disease_details.get("reasoning"),
                    "plant_info": get_plant_info(info["plant"]),
                    "is_healthy": info["is_healthy"],
                }
            )

        if not diseases:
            return {
                "error": "no_predictions",
                "message": "Image is unclear or not a plant leaf. Please use a clear plant image.",
                "diseases": []
            }

        if diseases[0]["confidence"] < MIN_CONFIDENCE * 100:
            return {
                "error": "low_confidence",
                "message": "Image is unclear or not a plant leaf. Please use a clear plant image.",
                "diseases": []
            }

        return {
            "detected_plant": diseases[0]["plant"],
            "diseases": diseases
        }

    except Exception as e:
        return {
            "error": str(e),
            "message": "Image could not be analyzed. Please use a clear plant image.",
            "diseases": []
        }
@app.get("/")
async def root():
    """API health check."""
    return {
        "status": "running",
        "model": model_name if model_loaded else "None",
        "model_weights_path": str(MODEL_WEIGHTS_PATH),
        "remote_model_configured": bool(MODEL_WEIGHTS_URL),
        "model_loaded": model_loaded,
        "message": "Plant Disease Detector API is ready!" if model_loaded else "Model not loaded - check dependencies"
    }


@app.get("/preset-library")
async def preset_library():
    """Return folder-driven preset image metadata for frontend rendering."""
    plants = build_preset_library()
    has_presets = any(plant["images"] for plant in plants)
    return {
        "max_images_per_plant": MAX_PRESET_IMAGES_PER_PLANT,
        "plants": plants,
        "has_presets": has_presets,
    }


@app.post("/analyze")
async def analyze_plant(
    file: UploadFile = File(...),
    soil_type: str = Form(None),
    temperature: str = Form(None),
    humidity: str = Form(None),
    moisture: str = Form(None)
):
    """Analyze plant image for diseases."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Unsupported file type. Please upload an image.")

    contents = await file.read()
    validate_image_bytes(contents)

    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    results = classify_plant_disease(image)
    return results


@app.post("/analyze-base64")
async def analyze_plant_base64(
    image_base64: str = Form(...),
    soil_type: str = Form(None),
    temperature: str = Form(None),
    humidity: str = Form(None),
    moisture: str = Form(None)
):
    """Analyze plant image from base64 string."""
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]

    try:
        image_data = base64.b64decode(image_base64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data.")

    validate_image_bytes(image_data)

    try:
        image = Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data.")

    results = classify_plant_disease(image)
    return results


@app.post("/analyze-preset")
async def analyze_preset_image(
    preset_src: str = Form(...),
    soil_type: str = Form(None),
    temperature: str = Form(None),
    humidity: str = Form(None),
    moisture: str = Form(None)
):
    """Analyze a preset image using server-side preset path resolution."""
    image_path = resolve_preset_image_path(preset_src)
    try:
        allowed_plant = image_path.relative_to(PRESETS_DIR).parts[0]
    except Exception:
        allowed_plant = image_path.parent.name

    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid preset image.")

    results = classify_plant_disease(image, allowed_plant=allowed_plant)
    return results


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Plant Disease Detector Server...")
    logger.info("Server running at: http://localhost:8000")
    logger.info("Open index.html in your browser to use the app.")
    uvicorn.run(app, host="0.0.0.0", port=8000)
