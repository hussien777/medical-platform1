# ============================================================
# ai_server.py
# Eye Care — Diabetic Retinopathy Detection Local AI Server
# 4-Model Ensemble + TTA + Weighted Geometric Mean
# ============================================================

import os
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

import torch
import torch.nn as nn
import torch.nn.functional as F

from torchvision import transforms
from torchvision.transforms import InterpolationMode
from torchvision.models import (
    efficientnet_b4,
    efficientnet_b2,
    convnext_base,
    swin_b,
)

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# CONFIG
# ============================================================

NUM_CLASSES = 5

SIZE_B4 = 512
SIZE_B2 = 260
SIZE_CONV = 224
SIZE_SWIN = 224

# Ensemble weights
W_B4 = 0.40
W_B2 = 0.25
W_CONV = 0.25
W_SWIN = 0.10

CLASS_NAMES = {
    0: "No DR",
    1: "Mild",
    2: "Moderate",
    3: "Severe",
    4: "Proliferative DR",
}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_MB = 10
MIN_RESOLUTION = 200

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

B4_PATH = os.path.join(MODELS_DIR, "b4_best.pth")
B2_PATH = os.path.join(MODELS_DIR, "b2_best.pth")
CONV_PATH = os.path.join(MODELS_DIR, "convnext_base_best.pth")
SWIN_PATH = os.path.join(MODELS_DIR, "swin_best.pth")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Eye Care AI Local Server",
    description="Diabetic Retinopathy Detection API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # During development. Later set frontend/backend URL only.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RESPONSE HELPERS
# ============================================================

def error_response(code: str, message: str):
    return {
        "success": False,
        "code": code,
        "message": message,
    }


# ============================================================
# VALIDATION
# ============================================================

def check_extension(filename: str):
    if filename is None:
        return False, "INVALID_FILENAME", "Invalid file name."

    ext = os.path.splitext(filename.lower())[1]

    if ext not in ALLOWED_EXTENSIONS:
        return False, "INVALID_EXTENSION", "Invalid file type. Allowed formats are JPG, JPEG, and PNG."

    return True, None, None


def check_file_size(file_bytes: bytes):
    size_mb = len(file_bytes) / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        return False, "FILE_TOO_LARGE", "File size exceeds the 10 MB limit."

    return True, None, None


def check_image_readable(file_bytes: bytes):
    try:
        image = Image.open(BytesIO(file_bytes))
        image.verify()

        image = Image.open(BytesIO(file_bytes))
        image = image.convert("RGB")

        return True, image, None, None

    except Exception:
        return False, None, "IMAGE_NOT_READABLE", "Cannot open image. Please upload a valid image file."


def check_resolution(image: Image.Image):
    width, height = image.size

    if width < MIN_RESOLUTION or height < MIN_RESOLUTION:
        return False, "LOW_RESOLUTION", "Image resolution is too small. Minimum resolution is 200×200 pixels."

    return True, None, None


def check_fundus_structure(image: Image.Image):
    """
    Basic fundus image validation.

    Criteria:
    1. Red/orange dominant color
    2. Dark corners
    3. Bright center region
    """

    img = np.array(image.convert("RGB").resize((256, 256)))

    red = img[:, :, 0]
    green = img[:, :, 1]
    blue = img[:, :, 2]

    mean_red = red.mean()
    mean_green = green.mean()
    mean_blue = blue.mean()

    if not (mean_red > mean_blue * 1.1 or mean_green > mean_blue * 1.1):
        return False, "INVALID_FUNDUS_IMAGE", "Invalid image. Please upload a valid fundus retinal image."

    h, w = img.shape[:2]
    corner_size = 20

    corners = [
        img[:corner_size, :corner_size],
        img[:corner_size, -corner_size:],
        img[-corner_size:, :corner_size],
        img[-corner_size:, -corner_size:],
    ]

    corner_brightness = np.mean([corner.mean() for corner in corners])

    if corner_brightness > 80:
        return False, "INVALID_FUNDUS_IMAGE", "Invalid image. Please upload a valid fundus retinal image."

    gray = np.mean(img, axis=2)

    center_region = gray[
        h // 4: 3 * h // 4,
        w // 4: 3 * w // 4
    ]

    if center_region.mean() < 20:
        return False, "INVALID_FUNDUS_IMAGE", "Invalid image. Please upload a valid fundus retinal image."

    return True, None, None


def validate_image(file_bytes: bytes, filename: str):
    valid, code, message = check_extension(filename)
    if not valid:
        return False, None, code, message

    valid, code, message = check_file_size(file_bytes)
    if not valid:
        return False, None, code, message

    valid, image, code, message = check_image_readable(file_bytes)
    if not valid:
        return False, None, code, message

    valid, code, message = check_resolution(image)
    if not valid:
        return False, None, code, message

    valid, code, message = check_fundus_structure(image)
    if not valid:
        return False, None, code, message

    return True, image, None, None


# ============================================================
# PREPROCESSING
# crop_from_gray → circle_crop → crop_from_gray → resize → Ben Graham
# ============================================================

def crop_from_gray(img, tol=7):
    if img.ndim == 2:
        mask = img > tol

        if mask.any():
            return img[np.ix_(mask.any(1), mask.any(0))]

        return img

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    mask = gray > tol

    if mask.any():
        return img[np.ix_(mask.any(1), mask.any(0))]

    return img


def circle_crop(img):
    h, w, _ = img.shape

    x = int(w / 2)
    y = int(h / 2)
    r = int(min(x, y) * 0.95)

    circle_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(circle_mask, (x, y), r, 1, thickness=-1)

    out = img.copy()
    out[circle_mask == 0] = 0

    return out


def ben_preprocess(img, sigma=10):
    return cv2.addWeighted(
        img,
        4,
        cv2.GaussianBlur(img, (0, 0), sigma),
        -4,
        128
    )


def preprocess_pil_image(pil_img: Image.Image, out_size: int = 512, sigma: int = 10):
    img = np.array(pil_img.convert("RGB"))

    img = crop_from_gray(img)
    img = circle_crop(img)
    img = crop_from_gray(img)

    if img is None or img.size == 0:
        img = np.array(pil_img.convert("RGB"))

    img = cv2.resize(img, (out_size, out_size), interpolation=cv2.INTER_AREA)
    img = ben_preprocess(img, sigma=sigma)
    img = np.clip(img, 0, 255).astype(np.uint8)

    return Image.fromarray(img)


# ============================================================
# MODEL COMPONENTS
# ============================================================

class AvgMaxPool(nn.Module):
    def forward(self, x):
        avg = F.adaptive_avg_pool2d(x, 1)
        mx = F.adaptive_max_pool2d(x, 1)

        return torch.cat([avg, mx], dim=1).flatten(1)


def custom_head(in_features, num_classes):
    return nn.Sequential(
        nn.Linear(in_features * 2, 512),
        nn.BatchNorm1d(512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, num_classes),
    )


def build_b4():
    model = efficientnet_b4(weights=None)

    in_features = model.classifier[1].in_features
    model.avgpool = AvgMaxPool()
    model.classifier = custom_head(in_features, NUM_CLASSES)

    return model


def build_b2():
    model = efficientnet_b2(weights=None)

    in_features = model.classifier[1].in_features
    model.avgpool = AvgMaxPool()
    model.classifier = custom_head(in_features, NUM_CLASSES)

    return model


def build_convnext():
    model = convnext_base(weights=None)

    in_features = model.classifier[2].in_features

    model.classifier = nn.Sequential(
        nn.Flatten(),
        nn.Linear(in_features, 512),
        nn.BatchNorm1d(512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, NUM_CLASSES),
    )

    return model


def build_swin():
    model = swin_b(weights=None)

    in_features = model.head.in_features

    model.head = nn.Sequential(
        nn.Linear(in_features, 512),
        nn.BatchNorm1d(512),
        nn.ReLU(),
        nn.Dropout(0.3),
        nn.Linear(512, NUM_CLASSES),
    )

    return model


# ============================================================
# TRANSFORMS
# ============================================================

def get_transform(size: int):
    return transforms.Compose([
        transforms.Resize((size, size), interpolation=InterpolationMode.BICUBIC),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ])


def to_tensor(pil_img: Image.Image, transform):
    tensor = transform(pil_img).unsqueeze(0)
    return tensor.to(device)


# ============================================================
# TTA — 11 VIEWS
# ============================================================

@torch.no_grad()
def tta_predict(model, tensor):
    h, w = tensor.shape[2], tensor.shape[3]

    ch95, cw95 = int(h * 0.95), int(w * 0.95)
    sy95, sx95 = (h - ch95) // 2, (w - cw95) // 2
    crop95 = tensor[:, :, sy95:sy95 + ch95, sx95:sx95 + cw95]
    crop95 = F.interpolate(crop95, size=(h, w), mode="bilinear", align_corners=False)

    ch90, cw90 = int(h * 0.90), int(w * 0.90)
    sy90, sx90 = (h - ch90) // 2, (w - cw90) // 2
    crop90 = tensor[:, :, sy90:sy90 + ch90, sx90:sx90 + cw90]
    crop90 = F.interpolate(crop90, size=(h, w), mode="bilinear", align_corners=False)

    views = [
        (tensor, 1.00),
        (torch.flip(tensor, dims=[3]), 0.90),
        (torch.flip(tensor, dims=[2]), 0.70),
        (torch.rot90(tensor, k=1, dims=[2, 3]), 0.75),
        (torch.rot90(tensor, k=2, dims=[2, 3]), 0.65),
        (torch.rot90(tensor, k=3, dims=[2, 3]), 0.75),
        (torch.flip(torch.rot90(tensor, k=1, dims=[2, 3]), dims=[3]), 0.60),
        (torch.flip(torch.rot90(tensor, k=3, dims=[2, 3]), dims=[3]), 0.60),
        (crop95, 0.85),
        (crop90, 0.70),
        (torch.flip(crop95, dims=[3]), 0.65),
    ]

    logits_sum = None
    weight_sum = 0.0

    for aug_tensor, weight in views:
        logits = model(aug_tensor)

        if logits_sum is None:
            logits_sum = logits * weight
        else:
            logits_sum = logits_sum + logits * weight

        weight_sum += weight

    return logits_sum / weight_sum


# ============================================================
# PREDICTOR CLASS
# ============================================================

class DRPredictor:
    def __init__(self):
        self.b4_model = self.load_model(build_b4, B4_PATH)
        self.b2_model = self.load_model(build_b2, B2_PATH)
        self.conv_model = self.load_model(build_convnext, CONV_PATH)
        self.swin_model = self.load_model(build_swin, SWIN_PATH)

        self.tf_b4 = get_transform(SIZE_B4)
        self.tf_b2 = get_transform(SIZE_B2)
        self.tf_conv = get_transform(SIZE_CONV)
        self.tf_swin = get_transform(SIZE_SWIN)

    def load_model(self, build_fn, weight_path):
        if not os.path.exists(weight_path):
            raise FileNotFoundError(f"Weight file not found: {weight_path}")

        model = build_fn()

        checkpoint = torch.load(
            weight_path,
            map_location=device,
            weights_only=False
        )

        if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)

        model.to(device)
        model.eval()

        return model

    @torch.no_grad()
    def predict(self, pil_img: Image.Image):
        preprocessed_img = preprocess_pil_image(pil_img, out_size=512, sigma=10)

        t_b4 = to_tensor(preprocessed_img, self.tf_b4)
        t_b2 = to_tensor(preprocessed_img, self.tf_b2)
        t_conv = to_tensor(preprocessed_img, self.tf_conv)
        t_swin = to_tensor(preprocessed_img, self.tf_swin)

        with torch.amp.autocast(
            device_type="cuda",
            enabled=torch.cuda.is_available()
        ):
            logits_b4 = tta_predict(self.b4_model, t_b4)
            logits_b2 = tta_predict(self.b2_model, t_b2)
            logits_conv = tta_predict(self.conv_model, t_conv)
            logits_swin = tta_predict(self.swin_model, t_swin)

        probs_b4 = F.softmax(logits_b4, dim=1).float().cpu().numpy()[0]
        probs_b2 = F.softmax(logits_b2, dim=1).float().cpu().numpy()[0]
        probs_conv = F.softmax(logits_conv, dim=1).float().cpu().numpy()[0]
        probs_swin = F.softmax(logits_swin, dim=1).float().cpu().numpy()[0]

        eps = 1e-8

        log_probs = (
            W_B4 * np.log(probs_b4 + eps) +
            W_B2 * np.log(probs_b2 + eps) +
            W_CONV * np.log(probs_conv + eps) +
            W_SWIN * np.log(probs_swin + eps)
        )

        final_probs = np.exp(log_probs)
        final_probs = final_probs / final_probs.sum()

        predicted_class = int(np.argmax(final_probs))
        confidence = float(final_probs[predicted_class])

        return {
            "predicted_class": predicted_class,
            "class_name": CLASS_NAMES[predicted_class],
            "confidence": round(confidence, 4),
            "probabilities": {
                CLASS_NAMES[i]: round(float(final_probs[i]), 4)
                for i in range(NUM_CLASSES)
            }
        }


# ============================================================
# LOAD MODELS ON SERVER STARTUP
# ============================================================

print("Starting Eye Care AI Local Server...")
print("Base directory:", BASE_DIR)
print("Models directory:", MODELS_DIR)
print("Device:", device)

predictor = DRPredictor()

print("All models loaded successfully.")


# ============================================================
# API ROUTES
# ============================================================

@app.get("/")
def root():
    return {
        "success": True,
        "message": "Eye Care AI Local Server is running.",
        "docs": "/docs",
        "health": "/api/health",
        "predict": "/api/predict"
    }


@app.get("/api/health")
def health_check():
    return {
        "success": True,
        "message": "Eye Care AI API is running.",
        "device": str(device),
        "models_loaded": True
    }


@app.post("/api/predict")
async def predict(file: UploadFile = File(...)):
    try:
        if file is None:
            return error_response(
                "NO_FILE",
                "No image file was uploaded."
            )

        file_bytes = await file.read()

        valid, image, code, message = validate_image(
            file_bytes=file_bytes,
            filename=file.filename
        )

        if not valid:
            return error_response(code, message)

        result = predictor.predict(image)

        return {
            "success": True,
            "result": result
        }

    except Exception as error:
        print("Prediction error:", str(error))

        return error_response(
            "PREDICTION_ERROR",
            "An error occurred while processing the image."
        )