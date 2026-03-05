import torch
import torch.nn as nn
from transformers import ViTModel

class MASENet(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        self.vit = ViTModel.from_pretrained(
            "google/vit-base-patch16-224"
        )

        dim = self.vit.config.hidden_size

        self.attention = nn.Sequential(
            nn.Linear(dim, dim),
            nn.ReLU(),
            nn.Linear(dim, dim),
            nn.Sigmoid()
        )

        self.classifier = nn.Linear(dim, num_classes)

    def forward(self, x):
        outputs = self.vit(pixel_values=x)
        cls_token = outputs.last_hidden_state[:, 0]

        attn_weights = self.attention(cls_token)
        refined = cls_token * attn_weights

        out = self.classifier(refined)
        return out