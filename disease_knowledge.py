"""
Disease Knowledge Base
Provides descriptions, symptoms, and reasoning for plant diseases.
"""                                   
                                          
# Export for server use
DISEASES = None  # Will be set after DISEASE_INFO is defined

DISEASE_INFO = {
    "healthy": {
        "name": "Healthy Plant",
        "description": "No disease detected. The plant appears to be in good health.",
        "symptoms": [
            "Vibrant green color throughout leaves",
            "No visible spots, lesions, or discoloration",
            "Leaves are firm and not wilting",
            "Normal growth patterns"
        ],
        "reasoning": "The leaf tissue shows uniform coloration without any visible signs of pathogen infection, nutrient deficiency, or environmental stress.",
        "treatment": "Continue regular care with proper watering, sunlight, and fertilization."
    },
    "blight": {
        "name": "Blight Disease",
        "description": "Blight is a rapid and complete chlorosis, browning, then death of plant tissues.",
        "symptoms": [
            "Brown or black water-soaked lesions on leaves",
            "Rapid wilting and browning of foliage",
            "Dark spots with concentric rings (target pattern)",
            "White fuzzy growth on leaf undersides (late blight)",
            "Stem lesions and fruit rot"
        ],
        "reasoning": "The observed dark lesions with characteristic patterns and rapid tissue death are consistent with blight infection, typically caused by Phytophthora or Alternaria species.",
        "treatment": "Remove infected parts, apply copper-based fungicide, improve air circulation, avoid overhead watering."
    },
    "mildew": {
        "name": "Powdery/Downy Mildew",
        "description": "Fungal disease causing white powdery coating or fuzzy growth on leaves.",
        "symptoms": [
            "White or gray powdery coating on leaf surfaces",
            "Yellow patches on upper leaf surface",
            "Curling or distorted leaves",
            "Stunted growth",
            "Premature leaf drop"
        ],
        "reasoning": "The powdery white appearance on leaf surfaces indicates fungal growth characteristic of mildew. The pattern of infection and leaf distortion supports this diagnosis.",
        "treatment": "Apply sulfur or potassium bicarbonate spray, improve air circulation, remove affected leaves, avoid wetting foliage."
    },
    "scab": {
        "name": "Scab Disease",
        "description": "Fungal disease causing rough, scabby lesions on leaves or fruit.",
        "symptoms": [
            "Olive-green or dark scab-like lesions",
            "Cracked or corky tissue on fruit",
            "Distorted leaves or fruit"
        ],
        "reasoning": "The rough, scabby lesions and cracking patterns are consistent with scab fungi infection.",
        "treatment": "Apply a protective fungicide early, remove infected debris, and improve airflow."
    },
    "rot": {
        "name": "Plant Rot",
        "description": "Tissue decay often caused by fungal or bacterial pathogens in moist conditions.",
        "symptoms": [
            "Soft, water-soaked lesions",
            "Darkened or mushy tissue",
            "Foul odor in severe cases",
            "Leaf or fruit collapse"
        ],
        "reasoning": "Soft, decaying tissue and water-soaked lesions indicate rot-related infection.",
        "treatment": "Remove infected tissue, reduce excess moisture, and apply a suitable fungicide or bactericide."
    },
    "leaf_spot": {
        "name": "Leaf Spot Disease",
        "description": "Fungal or bacterial infection causing distinct spots on leaves.",
        "symptoms": [
            "Circular or irregular brown/tan spots",
            "Yellow halos around lesions",
            "Spots may have dark borders",
            "Premature leaf yellowing and drop"
        ],
        "reasoning": "The distinct circular lesions with defined margins are characteristic of leaf spot diseases. The progression pattern from older to newer leaves supports fungal origin.",
        "treatment": "Remove infected leaves, avoid overhead watering, apply appropriate fungicide, ensure proper spacing."
    },
    "bacterial": {
        "name": "Bacterial Disease",
        "description": "Bacterial infection causing lesions, spots, or wilting depending on the pathogen.",
        "symptoms": [
            "Water-soaked or greasy-looking lesions",
            "Yellow halos around spots",
            "Leaf wilting or collapse",
            "Stem discoloration"
        ],
        "reasoning": "The presence of water-soaked lesions and rapid tissue breakdown suggests bacterial involvement.",
        "treatment": "Remove infected tissue, avoid overhead irrigation, apply copper-based bactericide."
    },
    "bacterial_wilt": {
        "name": "Bacterial Wilt",
        "description": "Bacterial infection causing rapid wilting of plants.",
        "symptoms": [
            "Sudden wilting of leaves and stems",
            "Wilting persists even with adequate water",
            "Brown discoloration in stem vascular tissue",
            "Sticky bacterial ooze when stem is cut"
        ],
        "reasoning": "The rapid, irreversible wilting pattern despite adequate moisture indicates vascular blockage typical of bacterial wilt infection.",
        "treatment": "Remove and destroy infected plants, rotate crops, use disease-resistant varieties, control insect vectors."
    },
    "mosaic_virus": {
        "name": "Mosaic Virus",
        "description": "Viral infection causing mottled color patterns on leaves.",
        "symptoms": [
            "Mottled light and dark green patterns",
            "Leaf curling and distortion",
            "Stunted plant growth",
            "Reduced fruit quality"
        ],
        "reasoning": "The characteristic mosaic pattern of light and dark areas on leaves, combined with leaf distortion, indicates viral infection.",
        "treatment": "No cure available. Remove infected plants, control aphid vectors, use virus-free seeds."
    },
    "virus": {
        "name": "Viral Disease",
        "description": "Viral infection causing mottling, distortion, or stunted growth.",
        "symptoms": [
            "Mottled or mosaic leaf patterns",
            "Leaf curling or distortion",
            "Stunted growth",
            "Reduced fruit quality"
        ],
        "reasoning": "The mottled patterns and distortion are consistent with plant virus infection.",
        "treatment": "No cure. Remove infected plants and control insect vectors."
    },
    "nutrient_deficiency": {
        "name": "Nutrient Deficiency",
        "description": "Lack of essential nutrients causing visual symptoms.",
        "symptoms": [
            "Yellowing between leaf veins (interveinal chlorosis)",
            "Pale or yellow leaves",
            "Purple or red discoloration",
            "Stunted growth",
            "Leaf tip browning"
        ],
        "reasoning": "The uniform color changes without distinct lesions or pathogen signs suggest nutritional issues rather than disease.",
        "treatment": "Soil test to identify deficiency, apply appropriate fertilizer, adjust soil pH if needed."
    },
    "rust": {
        "name": "Rust Disease",
        "description": "Fungal infection causing rust-colored pustules on leaves.",
        "symptoms": [
            "Orange, yellow, or brown pustules on leaf undersides",
            "Yellow spots on upper leaf surface",
            "Dusty spore masses when touched",
            "Premature leaf drop"
        ],
        "reasoning": "The characteristic colored pustules and dusty spore appearance are diagnostic of rust fungi infection.",
        "treatment": "Remove infected leaves, apply fungicide, improve air circulation, avoid overhead watering."
    },
    "anthracnose": {
        "name": "Anthracnose",
        "description": "Fungal disease causing dark, sunken lesions.",
        "symptoms": [
            "Dark, sunken lesions on leaves, stems, or fruit",
            "Lesions may have pink or orange spore masses",
            "Leaf distortion and curling",
            "Fruit rot with circular spots"
        ],
        "reasoning": "The characteristic sunken lesions with potential sporulation indicate anthracnose fungal infection.",
        "treatment": "Remove infected parts, apply copper fungicide, avoid overhead irrigation, rotate crops."
    }
}

# Map common disease terms to our knowledge base
DISEASE_ALIASES = {
    "early blight": "blight",
    "late blight": "blight",
    "northern leaf blight": "blight",
    "septoria": "leaf_spot",
    "septoria leaf spot": "leaf_spot",
    "isariopsis leaf spot": "leaf_spot",
    "leaf blight (isariopsis leaf spot)": "leaf_spot",
    "bacterial spot": "leaf_spot",
    "spot": "leaf_spot",
    "powdery mildew": "mildew",
    "downy mildew": "mildew",
    "target spot": "leaf_spot",
    "yellow leaf curl": "mosaic_virus",
    "yellow leaf curl virus": "mosaic_virus",
    "tomato yellow leaf curl virus": "mosaic_virus",
    "tomato mosaic": "mosaic_virus",
    "leaf mold": "mildew",
    "scab": "scab",
    "apple scab": "scab",
    "common rust": "rust",
    "cedar apple rust": "rust",
    "black rot": "rot",
    "root rot": "rot",
    "fruit rot": "rot",
    "bacterial": "bacterial",
    "virus": "virus",
    "spider mites": "nutrient_deficiency",  # Similar visual symptoms
}


def get_disease_info(disease_name: str) -> dict:
    """Get detailed information about a disease."""
    def normalize_key(value: str) -> str:
        return " ".join(value.lower().replace("_", " ").split())

    disease_key = normalize_key(disease_name)

    # Check aliases first
    if disease_key in DISEASE_ALIASES:
        disease_key = normalize_key(DISEASE_ALIASES[disease_key])
    else:
        for alias, target in DISEASE_ALIASES.items():
            if alias in disease_key:
                disease_key = normalize_key(target)
                break

    # Look for partial matches
    for key in DISEASE_INFO:
        normalized_key = normalize_key(key)
        if normalized_key in disease_key or disease_key in normalized_key:
            return DISEASE_INFO[key]

    # Default to generic info
    return {
        "name": disease_name.title(),
        "description": f"Detected: {disease_name}",
        "symptoms": ["Visual symptoms detected in the uploaded image"],
        "reasoning": f"The image analysis detected patterns consistent with {disease_name}.",
        "treatment": "Consult a local agricultural expert for specific treatment recommendations."
    }

# Set DISEASES export
DISEASES = DISEASE_INFO
