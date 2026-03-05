import torch
import json
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from transformers import ViTForImageClassification
from torch.utils.data import Subset
import random

# ---- SETTINGS ----

DATASET_PATH = "C:\christ\mahalakshmiprojectplant\plant-disease-detector\model-building\Agrivision\plantvillage"
MODEL_PATH = "plant_model.pth"
CLASS_PATH = "class_names.json"
BATCH_SIZE = 16

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---- Load class names ----
with open(CLASS_PATH) as f:
    class_names = json.load(f)

# ---- Load dataset ----
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

dataset = datasets.ImageFolder(DATASET_PATH, transform=transform)

indices = list(range(len(dataset)))
random.shuffle(indices)

subset_size = int(0.4 * len(dataset))  # 40% of data
subset_indices = indices[:subset_size]

dataset = Subset(dataset, subset_indices)
loader = DataLoader(dataset, batch_size=BATCH_SIZE)

# ---- Load model ----
model = ViTForImageClassification.from_pretrained(
    "google/vit-base-patch16-224",
    num_labels=len(class_names),
    ignore_mismatched_sizes=True
)

model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
print("Model loaded successfully.")
model.to(device)
model.eval()

# ---- Evaluate ----
correct = 0
total = 0

with torch.no_grad():
    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        outputs = model(pixel_values=images).logits
        preds = torch.argmax(outputs, dim=1)

        correct += (preds == labels).sum().item()
        total += labels.size(0)

accuracy = correct / total
print("Old Model Accuracy:", accuracy)