const API_ORIGIN = resolveApiOrigin();
const API_PRESET_ENDPOINT = `${API_ORIGIN}/analyze-preset`;
const PRESET_LIBRARY_ENDPOINT = `${API_ORIGIN}/preset-library`;
const KNOWN_FORM_KEYS = new Set(["soil_type", "temperature", "humidity", "moisture"]);
const MODEL_DISPLAY_NAME = "MASE-Net";

const state = {
    selectedPreset: null,
    isLoading: false,
    presetLibrary: [],
    maxPresetImagesPerPlant: 3,
    presetSheetCloseTimer: null
};

const ui = {
    uploadBox: document.getElementById("uploadBox"),
    uploadPreviewImage: document.getElementById("uploadPreviewImage"),
    uploadPlaceholder: document.getElementById("uploadPlaceholder"),
    presetSheet: document.getElementById("presetSheet"),
    presetSheetBackdrop: document.getElementById("presetSheetBackdrop"),
    closePresetSheetBtn: document.getElementById("closePresetSheetBtn"),
    presetCategories: document.getElementById("presetCategories"),
    soilType: document.getElementById("soilType"),
    temperature: document.getElementById("temperature"),
    humidity: document.getElementById("humidity"),
    moisture: document.getElementById("moisture"),
    analyzeBtn: document.getElementById("analyzeBtn"),
    analyzeBtnText: document.getElementById("analyzeBtnText"),
    clearBtn: document.getElementById("clearBtn"),
    statusText: document.getElementById("statusText"),
    selectedChip: document.getElementById("selectedChip"),
    resultsSection: document.getElementById("resultsSection"),
    resultMeta: document.getElementById("resultMeta"),
    topPrediction: document.getElementById("topPrediction")
};

init();

function resolveApiOrigin() {
    const protocol = window.location.protocol || "http:";
    const hostname = window.location.hostname;

    if (!hostname) {
        return "http://localhost:8000";
    }

    if (hostname === "localhost" || hostname === "127.0.0.1") {
        return "http://localhost:8000";
    }

    return `${protocol}//${hostname}:8000`;
}

async function init() {
    bindEvents();
    await loadPresetLibrary();
    updateAnalyzeButton();
}

function bindEvents() {
    ui.uploadBox.addEventListener("click", onUploadBoxClick);
    ui.uploadBox.addEventListener("keydown", onUploadBoxKeyDown);
    ui.analyzeBtn.addEventListener("click", onAnalyzeClick);
    ui.clearBtn.addEventListener("click", clearSelection);
    ui.presetSheetBackdrop.addEventListener("click", closePresetSheet);
    ui.closePresetSheetBtn.addEventListener("click", closePresetSheet);
    document.addEventListener("keydown", onDocumentKeyDown);
    ui.soilType.addEventListener("input", updateAnalyzeButton);
    ui.temperature.addEventListener("input", updateAnalyzeButton);
    ui.humidity.addEventListener("input", updateAnalyzeButton);
    ui.moisture.addEventListener("input", updateAnalyzeButton);
}

function onUploadBoxClick() {
    openPresetSheet();
}

function onUploadBoxKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openPresetSheet();
    }
}

function onDocumentKeyDown(event) {
    if (event.key !== "Escape") {
        return;
    }
    closePresetSheet();
}

function openPresetSheet() {
    if (state.presetSheetCloseTimer) {
        window.clearTimeout(state.presetSheetCloseTimer);
        state.presetSheetCloseTimer = null;
    }

    ui.presetSheet.classList.remove("hidden");
    requestAnimationFrame(() => {
        ui.presetSheet.classList.add("is-open");
    });
    ui.presetSheet.setAttribute("aria-hidden", "false");
    document.body.classList.add("sheet-open");
}

function closePresetSheet() {
    ui.presetSheet.classList.remove("is-open");
    ui.presetSheet.setAttribute("aria-hidden", "true");
    document.body.classList.remove("sheet-open");

    if (state.presetSheetCloseTimer) {
        window.clearTimeout(state.presetSheetCloseTimer);
    }

    state.presetSheetCloseTimer = window.setTimeout(() => {
        ui.presetSheet.classList.add("hidden");
        state.presetSheetCloseTimer = null;
    }, 260);
}

async function loadPresetLibrary() {
    try {
        const response = await fetch(PRESET_LIBRARY_ENDPOINT);
        if (!response.ok) {
            throw new Error(`Preset library request failed (${response.status}).`);
        }

        const payload = await response.json();
        state.maxPresetImagesPerPlant = normalizeMaxCount(payload?.max_images_per_plant);
        state.presetLibrary = normalizePresetLibrary(payload?.plants);

        renderPresetCategories();
    } catch (error) {
        state.presetLibrary = [];
        renderPresetCategories();
        setStatus("Preset images are unavailable right now.", "error");
    }
}

function normalizeMaxCount(value) {
    const maxValue = Number(value);
    if (!Number.isInteger(maxValue) || maxValue < 0) {
        return 0;
    }
    return maxValue;
}

function normalizePresetLibrary(plants) {
    if (!Array.isArray(plants)) {
        return [];
    }

    return plants.map((group) => {
        const name = String(group?.name || group?.folder || "Plant").trim() || "Plant";
        const rawImages = Array.isArray(group?.images) ? group.images : [];
        const limitedImages = state.maxPresetImagesPerPlant > 0
            ? rawImages.slice(0, state.maxPresetImagesPerPlant)
            : rawImages;
        const images = limitedImages
            .map((image) => ({
                label: String(image?.label || "Sample").trim() || "Sample",
                src: resolvePresetUrl(image?.src || ""),
                metadata: normalizeMetadata(image?.metadata)
            }))
            .filter((image) => image.src);

        return { name, images };
    });
}

function normalizeMetadata(metadata) {
    if (!metadata || typeof metadata !== "object") {
        return {};
    }

    const normalized = {};
    Object.entries(metadata).forEach(([rawKey, rawValue]) => {
        const key = normalizeMetadataKey(rawKey);
        const value = String(rawValue ?? "").trim();
        if (!key || !value) {
            return;
        }
        normalized[key] = value;
    });
    return normalized;
}

function normalizeMetadataKey(value) {
    return String(value ?? "")
        .trim()
        .toLowerCase()
        .replace(/[-\s]+/g, "_");
}

function firstMetadataValue(metadata, keys) {
    for (const key of keys) {
        const value = metadata?.[key];
        if (typeof value === "string" && value.trim()) {
            return value.trim();
        }
    }
    return "";
}

function applyPresetMetadata(metadata) {
    const data = normalizeMetadata(metadata);
    ui.soilType.value = firstMetadataValue(data, ["soil_type", "soiltype", "soil"]);
    ui.temperature.value = firstMetadataValue(data, ["temperature", "temp"]);
    ui.humidity.value = firstMetadataValue(data, ["humidity"]);
    ui.moisture.value = firstMetadataValue(data, ["moisture", "soil_moisture"]);
}

function clearParameterInputs() {
    ui.soilType.value = "";
    ui.temperature.value = "";
    ui.humidity.value = "";
    ui.moisture.value = "";
}

function appendExtraMetadataFields(formData, metadata) {
    const data = normalizeMetadata(metadata);
    Object.entries(data).forEach(([key, value]) => {
        if (!value || KNOWN_FORM_KEYS.has(key)) {
            return;
        }
        formData.append(key, value);
    });
}

function resolvePresetUrl(path) {
    try {
        return new URL(String(path || "").trim(), PRESET_LIBRARY_ENDPOINT).href;
    } catch (_error) {
        return "";
    }
}

function renderPresetCategories() {
    ui.presetCategories.innerHTML = "";

    if (!state.presetLibrary.length) {
        ui.presetCategories.appendChild(createPresetPlaceholder(
            "No images available."
        ));
        return;
    }

    state.presetLibrary.forEach((group) => {
        const category = document.createElement("section");
        category.className = "preset-category";

        const title = document.createElement("h4");
        title.textContent = group.name;
        category.appendChild(title);

        const grid = document.createElement("div");
        grid.className = "preset-grid";

        if (!group.images.length) {
            const emptyItem = document.createElement("div");
            emptyItem.className = "preset-empty";
            emptyItem.textContent = "No photos yet";
            grid.appendChild(emptyItem);
        } else {
            group.images.forEach((preset) => {
                const card = document.createElement("button");
                card.type = "button";
                card.className = "preset-card";
                card.dataset.src = preset.src;
                card.dataset.label = preset.label;
                card.dataset.category = group.name;

                const thumb = document.createElement("div");
                thumb.className = "preset-thumb";

                const img = document.createElement("img");
                img.src = preset.src;
                img.alt = preset.label;
                img.loading = "lazy";
                img.onerror = () => {
                    thumb.textContent = "Image missing";
                };
                thumb.appendChild(img);

                const name = document.createElement("p");
                name.className = "preset-name";
                name.textContent = preset.label;

                card.appendChild(thumb);
                card.appendChild(name);
                card.addEventListener("click", () => selectPreset(group.name, preset, card));
                grid.appendChild(card);
            });
        }

        category.appendChild(grid);
        ui.presetCategories.appendChild(category);
    });
}

function createPresetPlaceholder(titleText, subtitleText = "") {
    const placeholder = document.createElement("div");
    placeholder.className = "preset-placeholder";

    const title = document.createElement("p");
    title.className = "preset-placeholder-title";
    title.textContent = titleText;

    placeholder.appendChild(title);
    if (subtitleText) {
        const subtitle = document.createElement("p");
        subtitle.className = "preset-placeholder-subtitle";
        subtitle.textContent = subtitleText;
        placeholder.appendChild(subtitle);
    }
    return placeholder;
}

function selectPreset(categoryName, preset, element) {
    state.selectedPreset = {
        category: categoryName,
        label: preset.label,
        src: preset.src,
        metadata: normalizeMetadata(preset.metadata)
    };

    clearPresetActiveState();
    element.classList.add("active");

    setPreview(preset.src);
    applyPresetMetadata(state.selectedPreset.metadata);
    ui.selectedChip.textContent = `Source: Preset (${categoryName} / ${preset.label})`;
    ui.selectedChip.classList.remove("hidden");
    closePresetSheet();

    setStatus("Image selected.", "success");
    updateAnalyzeButton();
    clearResults();
}

function clearPresetActiveState() {
    document.querySelectorAll(".preset-card.active").forEach((card) => card.classList.remove("active"));
}

function clearSelection() {
    state.selectedPreset = null;

    clearPresetActiveState();
    clearParameterInputs();
    clearPreview();
    clearResults();
    closePresetSheet();

    setStatus("Selection cleared.");
    updateAnalyzeButton();
}

function setPreview(src) {
    ui.uploadPreviewImage.src = src;
    ui.uploadPreviewImage.style.display = "block";
    ui.uploadPlaceholder.style.display = "none";
    ui.uploadBox.classList.add("has-image");
}

function clearPreview() {
    ui.uploadPreviewImage.src = "";
    ui.uploadPreviewImage.style.display = "none";
    ui.uploadPlaceholder.style.display = "grid";
    ui.uploadBox.classList.remove("has-image");
    ui.selectedChip.textContent = "";
    ui.selectedChip.classList.add("hidden");
}

function setStatus(message, type = "") {
    ui.statusText.textContent = message;
    ui.statusText.classList.remove("error", "success");
    if (type) {
        ui.statusText.classList.add(type);
    }
}

function updateAnalyzeButton() {
    const ready = Boolean(state.selectedPreset) && hasRequiredParams();
    ui.analyzeBtn.disabled = state.isLoading || !ready;
}

function hasRequiredParams() {
    const soilReady = Boolean(ui.soilType.value.trim());
    const temperatureReady = isRequiredFieldFilled(ui.temperature);
    const humidityReady = isRequiredFieldFilled(ui.humidity);
    const moistureReady = isRequiredFieldFilled(ui.moisture);

    return soilReady && temperatureReady && humidityReady && moistureReady;
}

function isRequiredFieldFilled(field) {
    if (!field.value.trim()) {
        return false;
    }
    return field.checkValidity();
}

function setLoading(active) {
    state.isLoading = active;

    if (active) {
        ui.analyzeBtnText.innerHTML = '<span class="spinner"></span> Analyzing...';
    } else {
        ui.analyzeBtnText.textContent = "Analyze";
    }

    updateAnalyzeButton();
}

async function onAnalyzeClick() {
    if (!state.selectedPreset) {
        setStatus("Select a preset image before analysis.", "error");
        return;
    }
    if (!hasRequiredParams()) {
        setStatus("Fill all parameters before analysis.", "error");
        return;
    }

    setLoading(true);
    setStatus("Sending request to backend...");

    let response = null;
    let payload = null;
    try {
        const analysisContext = {
            soilType: ui.soilType.value.trim(),
            temperature: ui.temperature.value.trim(),
            humidity: ui.humidity.value.trim(),
            moisture: ui.moisture.value.trim(),
            imageLabel: state.selectedPreset
                ? `Preset (${state.selectedPreset.category} / ${state.selectedPreset.label})`
                : "Preset image",
            modelName: MODEL_DISPLAY_NAME
        };

        const formData = new FormData();
        formData.append("preset_src", state.selectedPreset.src);
        formData.append("soil_type", analysisContext.soilType);
        formData.append("temperature", analysisContext.temperature);
        formData.append("humidity", analysisContext.humidity);
        formData.append("moisture", analysisContext.moisture);
        appendExtraMetadataFields(formData, state.selectedPreset?.metadata);

        response = await fetch(API_PRESET_ENDPOINT, {
            method: "POST",
            body: formData
        });

        try {
            payload = await response.json();
        } catch (_error) {
            payload = null;
        }

        if (!response.ok) {
            const detail = payload?.detail || payload?.message || `Request failed with status ${response.status}`;
            console.error("[Analyze] Request failed", {
                status: response.status,
                statusText: response.statusText,
                detail,
                payload,
                preset: state.selectedPreset
            });
            throw new Error(detail);
        }

        renderResults(payload, analysisContext);
        setStatus("Analysis complete.", "success");
    } catch (error) {
        console.error("[Analyze] Exception", {
            message: error?.message || String(error),
            error,
            responseStatus: response?.status,
            payload,
            preset: state.selectedPreset
        });
        renderError(error.message || "Analysis failed.");
        setStatus(error.message || "Analysis failed.", "error");
    } finally {
        setLoading(false);
    }
}

function renderResults(payload, analysisContext = {}) {
    const top = Array.isArray(payload?.diseases) ? payload.diseases[0] : null;

    if (payload?.error || !top) {
        if (payload?.error) {
            console.error("[Analyze] Backend error payload", {
                error: payload.error,
                message: payload.message,
                payload,
                preset: state.selectedPreset
            });
        }
        renderError(getUserFriendlyError(payload, "No valid prediction returned from backend."));
        return;
    }

    ui.resultsSection.classList.remove("hidden");

    const topName = safeText(top.name || top.disease || "Unknown");
    const topConfidence = formatConfidence(top.confidence);
    const topCause = safeText(top.cause || "Not provided");
    const topTreatment = safeText(top.treatment || "Not provided");
    const topSymptoms = Array.isArray(top.symptoms) && top.symptoms.length
        ? top.symptoms.map((item) => `<li>${safeText(item)}</li>`).join("")
        : "<li>No symptoms listed</li>";
    const consideredImage = safeText(analysisContext.imageLabel || "Preset image");
    const consideredSoil = safeText(analysisContext.soilType || "-");
    const consideredTemperature = safeText(analysisContext.temperature || "-");
    const consideredHumidity = safeText(analysisContext.humidity || "-");
    const consideredMoisture = safeText(analysisContext.moisture || "-");
    const modelUsed = safeText(payload?.model || analysisContext.modelName || MODEL_DISPLAY_NAME);

    ui.resultMeta.textContent = payload.detected_plant
        ? `Detected plant: ${payload.detected_plant}`
        : "Model output from backend analysis";

    ui.topPrediction.innerHTML = `
        <article class="result-primary">
            <div class="result-title">
                <h3>${topName}</h3>
                <span class="confidence-pill">${topConfidence}% confidence</span>
            </div>
            <div class="confidence-track">
                <div class="confidence-fill" style="width:${topConfidence}%"></div>
            </div>
            <div class="detail-grid">
                <div class="detail-box">
                    <h4>Disease Name</h4>
                    <p>${topName}</p>
                </div>
                <div class="detail-box">
                    <h4>Confidence</h4>
                    <p>${topConfidence}%</p>
                </div>
                <div class="detail-box">
                    <h4>Cause</h4>
                    <p>${topCause}</p>
                </div>
                <div class="detail-box">
                    <h4>Treatment</h4>
                    <p>${topTreatment}</p>
                </div>
                <div class="detail-box" style="grid-column: 1 / -1;">
                    <h4>Symptoms</h4>
                    <ul>${topSymptoms}</ul>
                </div>
            </div>
            <div class="considered-box">
                <h4>Things Considered</h4>
                <div class="considered-list">
                    <span class="considered-item">Image: ${consideredImage}</span>
                    <span class="considered-item">Soil Type: ${consideredSoil}</span>
                    <span class="considered-item">Temperature: ${consideredTemperature}</span>
                    <span class="considered-item">Humidity: ${consideredHumidity}</span>
                    <span class="considered-item">Moisture: ${consideredMoisture}</span>
                    <span class="considered-item">Model: ${modelUsed}</span>
                </div>
            </div>
        </article>
    `;
}

function renderError(message) {
    ui.resultsSection.classList.remove("hidden");
    ui.resultMeta.textContent = "Could not identify the image.";
    ui.topPrediction.innerHTML = `
        <article class="result-primary">
            <div class="result-title">
                <h3>Analysis Failed</h3>
                <span class="confidence-pill">0% confidence</span>
            </div>
            <p>${safeText(message || "Unable to analyze image.")}</p>
        </article>
    `;
}

function clearResults() {
    ui.resultsSection.classList.add("hidden");
    ui.resultMeta.textContent = "Model output from backend analysis";
    ui.topPrediction.innerHTML = "";
}

function getUserFriendlyError(payload, fallbackMessage) {
    const errorCode = String(payload?.error || "").toLowerCase();
    const message = String(payload?.message || "").toLowerCase();

    if (errorCode === "low_confidence" || message.includes("low confidence")) {
        return "Image is unclear or not a plant leaf. Please use a clear plant image.";
    }

    if (message.includes("invalid image") || message.includes("unsupported")) {
        return "Image is unclear or unsupported. Please use a clear plant image.";
    }

    return payload?.message || fallbackMessage;
}

function formatConfidence(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) {
        return 0;
    }
    return Math.max(0, Math.min(100, Number(num.toFixed(1))));
}

function safeText(value) {
    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
}
