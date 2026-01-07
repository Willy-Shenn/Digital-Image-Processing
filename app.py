import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import cv2
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pywt
from flask import (Flask, abort, flash, redirect, render_template, request,
                   send_file, url_for)
from skimage import img_as_float
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

matplotlib.use("Agg")

app = Flask(__name__)
app.secret_key = "color-image-processing"

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
RESULT_DIR = BASE_DIR / "result"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


# ---------- utilities ----------

def ensure_dirs() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    RESULT_DIR.mkdir(exist_ok=True)


def timestamp() -> str:
    return datetime.now().strftime("%y%m%d%H%M%S")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), rgb)


def rel_path(path: Path) -> str:
    return path.relative_to(BASE_DIR).as_posix()


def to_gray(image: np.ndarray) -> np.ndarray:
    """Convert RGB image to grayscale, handling float images from denoise pipeline."""
    arr = image
    if arr.dtype == np.float64 or arr.dtype == np.float32:
        arr = arr.astype(np.float32)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)


def diff_image(reference: np.ndarray, target: np.ndarray) -> np.ndarray:
    ref = reference.astype(np.float32)
    tgt = target.astype(np.float32)
    diff = np.abs(ref - tgt)
    max_val = diff.max() if diff.size else 0
    if max_val > 0:
        diff = diff / max_val * 255.0
    return diff.clip(0, 255).astype(np.uint8)


def compute_metrics(reference: np.ndarray, target: np.ndarray) -> Dict[str, float]:
    ref_f = img_as_float(reference)
    tgt_f = img_as_float(target)
    mse = float(np.mean((ref_f - tgt_f) ** 2))
    psnr = float(peak_signal_noise_ratio(ref_f, tgt_f, data_range=1.0))
    ssim = float(structural_similarity(ref_f, tgt_f, channel_axis=2, data_range=1.0))
    return {"mse": mse, "psnr": psnr, "ssim": ssim}


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def calc_entropy(channel: np.ndarray) -> float:
    hist, _ = np.histogram(channel.flatten(), bins=256, range=(0, 255), density=True)
    hist = hist[hist > 0]
    return float(-np.sum(hist * np.log2(hist))) if hist.size else 0.0


def rms_contrast(channel: np.ndarray) -> float:
    return float(np.std(channel.astype(np.float32)))


def edge_preservation_index(noisy: np.ndarray, denoised: np.ndarray) -> float:
    g_noisy_x = np.gradient(noisy, axis=1)
    g_noisy_y = np.gradient(noisy, axis=0)
    g_denoise_x = np.gradient(denoised, axis=1)
    g_denoise_y = np.gradient(denoised, axis=0)
    num = np.sum(np.abs(g_denoise_x)) + np.sum(np.abs(g_denoise_y))
    den = np.sum(np.abs(g_noisy_x)) + np.sum(np.abs(g_noisy_y))
    return float(num / den) if den != 0 else 0.0


def save_meta(ts: str, data: Dict) -> None:
    path = RESULT_DIR / f"{ts}_meta.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- processing pipelines ----------

def process_interpolation(image: np.ndarray, ts: str, method: str = "bicubic", scale: float = 1.5) -> Dict:
    flag = cv2.INTER_CUBIC if method == "bicubic" else cv2.INTER_LINEAR
    h, w, _ = image.shape
    down_size = (max(1, int(w / scale)), max(1, int(h / scale)))
    down = cv2.resize(image, down_size, interpolation=cv2.INTER_AREA)
    restored = cv2.resize(down, (w, h), interpolation=flag)
    metrics = compute_metrics(image, restored)

    diff = diff_image(image, restored)
    processed_path = RESULT_DIR / f"{ts}_interp_{method}.png"
    diff_path = RESULT_DIR / f"{ts}_diff_interp_{method}.png"
    save_image(processed_path, restored)
    save_image(diff_path, diff)

    abs_error = np.abs(img_as_float(image) - img_as_float(restored)).flatten()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(abs_error, bins=50, color="#4f46e5", alpha=0.8)
    ax.set_title("Interpolation Self-Consistency Error")
    ax.set_xlabel("Absolute Error")
    ax.set_ylabel("Count")
    error_plot_path = RESULT_DIR / f"{ts}_interp_error_hist.png"
    save_figure(fig, error_plot_path)

    return {
        "key": "interpolation",
        "title": f"Interpolation ({method.title()})",
        "description": f"Scale {scale}x, method {method}",
        "processed": rel_path(processed_path),
        "diff": rel_path(diff_path),
        "charts": [rel_path(error_plot_path)],
        "metrics": metrics,
    }


def process_hist_eq(image: np.ndarray, ts: str, clip_limit: float = 2.0, tile_grid_size: int = 8) -> Dict:
    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
    l_eq = clahe.apply(l)
    lab_eq = cv2.merge([l_eq, a, b])
    processed = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2RGB)

    diff = diff_image(image, processed)
    processed_path = RESULT_DIR / f"{ts}_histeq_clahe.png"
    diff_path = RESULT_DIR / f"{ts}_diff_histeq.png"
    save_image(processed_path, processed)
    save_image(diff_path, diff)

    entropy_before = calc_entropy(l)
    entropy_after = calc_entropy(l_eq)
    contrast_before = rms_contrast(l)
    contrast_after = rms_contrast(l_eq)
    cii = float(contrast_after / contrast_before) if contrast_before else 0.0

    # histogram plot
    fig1, ax1 = plt.subplots(1, 2, figsize=(10, 4))
    ax1[0].hist(l.flatten(), bins=256, color="gray", alpha=0.8)
    ax1[0].set_title("Histogram Before")
    ax1[1].hist(l_eq.flatten(), bins=256, color="#16a34a", alpha=0.8)
    ax1[1].set_title("Histogram After")
    hist_path = RESULT_DIR / f"{ts}_hist_before_after.png"
    save_figure(fig1, hist_path)

    # enhancement / CDF curve
    hist, bins = np.histogram(l.flatten(), bins=256, range=(0, 255), density=True)
    cdf = hist.cumsum()
    cdf = cdf / cdf[-1] if cdf[-1] else cdf
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.plot(bins[:-1], cdf * 255, color="#2563eb", label="CDF")
    ax2.set_title("Enhancement Curve (CDF)")
    ax2.set_xlabel("Input L")
    ax2.set_ylabel("Mapped Value")
    ax2.legend()
    curve_path = RESULT_DIR / f"{ts}_curve_histeq.png"
    save_figure(fig2, curve_path)

    metrics = {
        "entropy_before": entropy_before,
        "entropy_after": entropy_after,
        "contrast_before": contrast_before,
        "contrast_after": contrast_after,
        "cii": cii,
    }

    return {
        "key": "hist_eq",
        "title": "Histogram Equalization / CLAHE",
        "description": f"CLAHE clipLimit={clip_limit}, tileGridSize={tile_grid_size}",
        "processed": rel_path(processed_path),
        "diff": rel_path(diff_path),
        "charts": [rel_path(hist_path), rel_path(curve_path)],
        "metrics": metrics,
    }


def soft_threshold(coeff: np.ndarray, thresh: float) -> np.ndarray:
    return np.sign(coeff) * np.maximum(np.abs(coeff) - thresh, 0)


def denoise_channel(channel: np.ndarray, wavelet: str, level: int):
    coeffs = pywt.wavedec2(channel, wavelet=wavelet, level=level)
    cA, detail_coeffs = coeffs[0], coeffs[1:]
    hh = detail_coeffs[0][2]
    sigma = np.median(np.abs(hh)) / 0.6745 if hh.size else 0.0
    thresh = sigma * np.sqrt(2 * np.log(channel.size)) if channel.size else 0.0
    new_details = []
    for cH, cV, cD in detail_coeffs:
        new_details.append((soft_threshold(cH, thresh), soft_threshold(cV, thresh), soft_threshold(cD, thresh)))
    reconstructed = pywt.waverec2([cA] + new_details, wavelet=wavelet)
    reconstructed = reconstructed[: channel.shape[0], : channel.shape[1]]
    return np.clip(reconstructed, 0, 1), thresh, hh


def process_wavelet(image: np.ndarray, ts: str, wavelet: str = "db2", level: int = 2) -> Dict:
    img_f = img_as_float(image)
    noisy = img_f + np.random.normal(0, 0.01, img_f.shape)
    noisy = np.clip(noisy, 0, 1)

    denoised_channels = []
    hh_samples = None
    thresholds = []
    for i in range(3):
        channel_denoised, t, hh = denoise_channel(noisy[:, :, i], wavelet, level)
        denoised_channels.append(channel_denoised)
        thresholds.append(t)
        if hh_samples is None:
            hh_samples = hh
    denoised = np.stack(denoised_channels, axis=2)
    processed_uint8 = (denoised * 255).clip(0, 255).astype(np.uint8)

    diff = diff_image(image, processed_uint8)
    processed_path = RESULT_DIR / f"{ts}_wavelet_denoise.png"
    diff_path = RESULT_DIR / f"{ts}_diff_wavelet.png"
    save_image(processed_path, processed_uint8)
    save_image(diff_path, diff)

    metrics = {
        "psnr": float(peak_signal_noise_ratio(img_as_float(image), denoised, data_range=1.0)),
        "ssim": float(structural_similarity(img_as_float(image), denoised, channel_axis=2, data_range=1.0)),
    }
    epi = edge_preservation_index(to_gray(noisy), to_gray(denoised))
    metrics["epi"] = epi
    metrics["threshold"] = float(np.mean(thresholds)) if thresholds else 0.0

    fig1, ax1 = plt.subplots(figsize=(6, 4))
    if hh_samples is not None:
        ax1.hist(hh_samples.flatten(), bins=50, alpha=0.7, color="#0ea5e9")
        ax1.set_title("HH Coefficient Distribution (level 1)")
        ax1.set_xlabel("Coefficient value")
    coeff_hist_path = RESULT_DIR / f"{ts}_wavelet_coeff_hist.png"
    save_figure(fig1, coeff_hist_path)

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    x = np.linspace(-0.5, 0.5, 400)
    y = np.sign(x) * np.maximum(np.abs(x) - metrics["threshold"], 0)
    ax2.plot(x, y, color="#f97316")
    ax2.axvline(metrics["threshold"], color="gray", linestyle="--", linewidth=1)
    ax2.axvline(-metrics["threshold"], color="gray", linestyle="--", linewidth=1)
    ax2.set_title("Soft-threshold Curve")
    ax2.set_xlabel("Input coefficient")
    ax2.set_ylabel("Output")
    threshold_curve_path = RESULT_DIR / f"{ts}_wavelet_threshold_curve.png"
    save_figure(fig2, threshold_curve_path)

    return {
        "key": "wavelet",
        "title": "Wavelet Denoising (DWT + Soft-threshold)",
        "description": f"Wavelet={wavelet}, level={level}",
        "processed": rel_path(processed_path),
        "diff": rel_path(diff_path),
        "charts": [rel_path(coeff_hist_path), rel_path(threshold_curve_path)],
        "metrics": metrics,
    }


# ---------- routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    ensure_dirs()
    file = request.files.get("image")
    if not file or file.filename == "":
        flash("請選擇上傳圖片 (jpg/png)")
        return redirect(url_for("index"))
    if not allowed_file(file.filename):
        flash("僅支援 jpg/png")
        return redirect(url_for("index"))

    ts = timestamp()
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img_bgr is None:
        flash("檔案讀取失敗，請確認圖片格式")
        return redirect(url_for("index"))
    image = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    orig_path = INPUT_DIR / f"{ts}_orig.png"
    save_image(orig_path, image)

    techniques = request.form.getlist("techniques")
    results: List[Dict] = []

    if "interpolation" in techniques:
        method = request.form.get("interp_method", "bicubic")
        try:
            scale = float(request.form.get("interp_scale", 1.5))
        except ValueError:
            scale = 1.5
        results.append(process_interpolation(image, ts, method=method, scale=scale))

    if "hist_eq" in techniques:
        try:
            clip_limit = float(request.form.get("clip_limit", 2.0))
        except ValueError:
            clip_limit = 2.0
        try:
            tile = int(request.form.get("tile_grid", 8))
        except ValueError:
            tile = 8
        results.append(process_hist_eq(image, ts, clip_limit=clip_limit, tile_grid_size=tile))

    if "wavelet" in techniques:
        wavelet = request.form.get("wavelet", "db2") or "db2"
        try:
            level = int(request.form.get("level", 2))
        except ValueError:
            level = 2
        results.append(process_wavelet(image, ts, wavelet=wavelet, level=level))

    meta = {
        "timestamp": ts,
        "original": rel_path(orig_path),
        "techniques": results,
    }
    save_meta(ts, meta)

    return redirect(url_for("result_page", ts=ts))


@app.route("/result/<ts>")
def result_page(ts: str):
    meta_path = RESULT_DIR / f"{ts}_meta.json"
    if not meta_path.exists():
        abort(404)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return render_template("result.html", meta=meta)


@app.route("/files/<path:filepath>")
def serve_file(filepath: str):
    safe_base = BASE_DIR.resolve()
    full_path = (BASE_DIR / filepath).resolve()
    if not str(full_path).startswith(str(safe_base)):
        abort(404)
    if not full_path.exists():
        abort(404)
    return send_file(full_path)


if __name__ == "__main__":
    ensure_dirs()
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.run(debug=True)
