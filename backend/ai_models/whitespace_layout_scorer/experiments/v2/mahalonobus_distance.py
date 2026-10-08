#!/usr/bin/env python3
import os
import sys
import cv2
import json
import pickle
import argparse
import numpy as np
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import pdfplumber
from scipy.stats import chi2

# ------------------------------------------------------------
# ----------------- FEATURE EXTRACTION -----------------------
# (Mostly your code; I made minor robustness edits)
# ------------------------------------------------------------

def pdf_to_images(pdf_path, dpi=200):
    pil_pages = convert_from_path(pdf_path, dpi=dpi)
    cv_images = []
    for pil in pil_pages:
        arr = np.array(pil)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        cv_images.append(gray)
    return cv_images

def compute_total_whitespace_ratio(page_img, thresh=200):
    _, bw = cv2.threshold(page_img, thresh, 255, cv2.THRESH_BINARY)
    white = np.count_nonzero(bw == 255)
    total = bw.size
    return white / total if total else 0.0

def compute_sectional_whitespace(page_img, n_sections=4, thresh=200):
    h = page_img.shape[0]
    ratios = []
    for i in range(n_sections):
        y0 = int(i*h/n_sections)
        y1 = int((i+1)*h/n_sections)
        band = page_img[y0:y1, :]
        ratios.append(compute_total_whitespace_ratio(band, thresh=thresh))
    return ratios

def compute_bounding_box_spacing(page_img):
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    n = len(data['level'])
    boxes = []
    for i in range(n):
        # some tesseract builds use -1 for conf on blanks
        try:
            conf = float(data['conf'][i])
        except ValueError:
            conf = -1
        if conf > 0:
            x, y = data['left'][i], data['top'][i]
            w, h = data['width'][i], data['height'][i]
            boxes.append((x, y, x+w, y+h))
    if len(boxes) < 2:
        return 0.0, 0.0
    boxes.sort(key=lambda b: (b[1], b[0]))
    hor_gaps, ver_gaps = [], []
    for (x0, y0, x1, y1), (xx0, yy0, xx1, yy1) in zip(boxes, boxes[1:]):
        hor_gaps.append(max(0, xx0 - x1))
        ver_gaps.append(max(0, yy0 - y1))
    return (float(np.mean(hor_gaps)) if hor_gaps else 0.0,
            float(np.mean(ver_gaps)) if ver_gaps else 0.0)

def compute_characters_per_area(pdf_path):
    densities = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ''
            chars = len(txt)
            w, h = page.width, page.height
            area = w * h if (w and h) else 1.0
            densities.append(chars / area)
    return densities or [0.0]

def compute_block_density(pdf_path, n_blocks=4):
    """
    Split page height into n_blocks equal horizontal bands.
    Return list of dicts: {block_i: density}
    """
    densities = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            h = page.height
            block_h = h / n_blocks
            page_dict = {}
            for i in range(n_blocks):
                y0 = i * block_h
                y1 = y0 + block_h
                txt = page.within_bbox((0, y0, page.width, y1)).extract_text() or ''
                words = len(txt.split())
                area = page.width * block_h if (page.width and block_h) else 1.0
                page_dict[f"block_{i}"] = words / area
            densities.append(page_dict)
    return densities or [{f"block_{i}":0.0 for i in range(n_blocks)}]

def compute_line_spacing(page_img):
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    lines = {}
    for i, text in enumerate(data['text']):
        if str(text).strip():
            line_num = data['line_num'][i]
            y = data['top'][i]
            lines.setdefault(line_num, []).append(y)
    baselines = [int(np.mean(v)) for v in lines.values()]
    baselines.sort()
    if len(baselines) < 2:
        return 0.0
    diffs = np.diff(baselines)
    return float(np.mean(diffs)) if len(diffs) else 0.0

def compute_section_separation(page_img):
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    bottoms = []
    for i in range(len(data['level'])):
        if str(data['text'][i]).strip():
            bottoms.append(data['top'][i] + data['height'][i])
    bottoms.sort()
    if len(bottoms) < 2:
        return 0.0
    gaps = np.diff(bottoms)
    med = np.median(gaps) if len(gaps) else 0.0
    if med <= 0:
        return 0.0
    big = [g for g in gaps if g > 1.5 * med]
    return float(np.mean(big)) if big else 0.0

def compute_margins(page_img, thresh=200):
    """
    Return (left, right, top, bottom) margin (pixels) between content and page edge.
    """
    # invert: text -> white so we can find content
    _, inv = cv2.threshold(page_img, thresh, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(inv)
    if coords is None:
        return (0.0, 0.0, 0.0, 0.0)
    x_vals = coords[:,:,0].flatten()
    y_vals = coords[:,:,1].flatten()
    h, w = page_img.shape
    left = float(np.min(x_vals))
    right = float(w - np.max(x_vals))
    top = float(np.min(y_vals))
    bottom = float(h - np.max(y_vals))
    return (left, right, top, bottom)

def compute_padding_around_elements(page_img, pad=5, thresh=200):
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    paddings = []
    h_img, w_img = page_img.shape
    for i in range(len(data['level'])):
        if str(data['text'][i]).strip():
            x, y = data['left'][i], data['top'][i]
            w, h = data['width'][i], data['height'][i]
            x0 = max(0, x-pad)
            y0 = max(0, y-pad)
            x1 = min(w_img, x+w+pad)
            y1 = min(h_img, y+h+pad)
            crop = page_img[y0:y1, x0:x1]
            if crop.size == 0:
                continue
            whites = np.count_nonzero(crop > thresh)
            paddings.append(whites / crop.size)
    return float(np.mean(paddings)) if paddings else 0.0

def extract_features_for_pdf(pdf_path):
    feats = {}
    images = pdf_to_images(pdf_path)

    # whitespace
    whites = [compute_total_whitespace_ratio(img) for img in images]
    feats['whitespace_ratio_avg'] = float(np.mean(whites))
    sects = [compute_sectional_whitespace(img) for img in images]
    n_sections = len(sects[0]) if sects else 0
    for i in range(n_sections):
        feats[f'section_whitespace_avg_{i}'] = float(np.mean([s[i] for s in sects]))

    # bounding box spacing
    hb, vb = zip(*[compute_bounding_box_spacing(img) for img in images]) if images else ([0],[0])
    feats['bbox_h_spacing_avg'] = float(np.mean(hb))
    feats['bbox_v_spacing_avg'] = float(np.mean(vb))

    # text density
    char_dens = compute_characters_per_area(pdf_path)
    feats['char_density_avg'] = float(np.mean(char_dens))

    block_dicts = compute_block_density(pdf_path)
    first = block_dicts[0]
    for key in first.keys():
        feats[f'block_density_avg_{key.split("_")[-1]}'] = float(np.mean([bd[key] for bd in block_dicts]))

    # spacing
    ls = [compute_line_spacing(img) for img in images]
    feats['line_spacing_avg'] = float(np.mean(ls))
    ss = [compute_section_separation(img) for img in images]
    feats['section_sep_avg'] = float(np.mean(ss))

    # margins & padding
    margins = [compute_margins(img) for img in images]
    if margins:
        for idx, name in enumerate(['left','right','top','bottom']):
            feats[f'margin_{name}_avg'] = float(np.mean([m[idx] for m in margins]))
    else:
        for name in ['left','right','top','bottom']:
            feats[f'margin_{name}_avg'] = 0.0

    pads = [compute_padding_around_elements(img) for img in images]
    feats['padding_avg'] = float(np.mean(pads)) if pads else 0.0

    feats['file'] = os.path.basename(pdf_path)
    return feats

# ------------------------------------------------------------
# ----------------- MODEL UTILITIES --------------------------
# ------------------------------------------------------------

def robust_center_scale(X):
    """
    Median / IQR scaling. Returns scaled_X, medians, iqrs (replace 0 IQR with 1).
    """
    med = np.nanmedian(X, axis=0)
    q75 = np.nanpercentile(X, 75, axis=0)
    q25 = np.nanpercentile(X, 25, axis=0)
    iqr = q75 - q25
    iqr[iqr == 0] = 1.0
    Xs = (X - med) / iqr
    return Xs, med, iqr

def mahalanobis_prep(Xs, eps=1e-6):
    """
    Compute mean & inverse covariance in scaled space.
    """
    mu = np.nanmean(Xs, axis=0)
    # rowvar=False => features columns
    cov = np.cov(Xs, rowvar=False)
    # regularize
    cov += np.eye(cov.shape[0]) * eps
    cov_inv = np.linalg.pinv(cov)
    return mu, cov, cov_inv

def mahalanobis_d2(x, mu, cov_inv):
    diff = x - mu
    return float(diff @ cov_inv @ diff.T)

def empirical_score(d2, d2_train, add=0.5):
    """
    Smoothed tail: rank-based survival.
    add=0.5 avoids 0/100 extremes.
    """
    d2_train = np.asarray(d2_train)
    n = len(d2_train)
    # # of training points >= d2
    k = np.sum(d2_train >= d2)
    frac_farther = (k + add) / (n + 2*add)
    return 100.0 * frac_farther

def chi2_score(d2, df):
    """
    Score high if d2 small. Use survival fn (1-CDF).
    """
    return 100.0 * chi2.sf(d2, df=df)

# ------------------------------------------------------------
# ----------------- TRAINING ---------------------------------
# ------------------------------------------------------------

def train_model(csv_path, model_out, score_method="empirical", feature_drop=("file",)):
    df = pd.read_csv(csv_path)
    # remove non-feature cols
    features = [c for c in df.columns if c not in feature_drop]
    X = df[features].values.astype(float)

    # robust scale
    Xs, med, iqr = robust_center_scale(X)

    # fit mahalanobis
    mu, cov, cov_inv = mahalanobis_prep(Xs)

    # training d2
    d2_train = np.array([mahalanobis_d2(x, mu, cov_inv) for x in Xs])

    # pack
    model = {
        "features": features,
        "median": med,
        "iqr": iqr,
        "mu": mu,
        "cov": cov,
        "cov_inv": cov_inv,
        "d2_train": d2_train,
        "score_method": score_method,
        "df": len(features)  # for chi2
    }
    with open(model_out, "wb") as f:
        pickle.dump(model, f)

    # quick training scores preview
    if score_method == "empirical":
        scores = [empirical_score(d, d2_train) for d in d2_train]
    else:
        scores = [chi2_score(d, len(features)) for d in d2_train]
    df_out = df.copy()
    df_out["mahal_score"] = scores
    print(f"[train] mean score={np.mean(scores):.2f}, min={np.min(scores):.2f}, max={np.max(scores):.2f}")
    return df_out

# ------------------------------------------------------------
# ----------------- SCORING ----------------------------------
# ------------------------------------------------------------

def load_model(model_path):
    with open(model_path, "rb") as f:
        return pickle.load(f)

def transform_features(feat_dict, model):
    """
    Align feature vector to training feature order; fill missing with training median.
    Extra keys ignored.
    """
    feats = []
    for col, med in zip(model["features"], model["median"]):
        val = feat_dict.get(col, med)
        try:
            val = float(val)
        except Exception:
            val = med
        feats.append(val)
    x = np.array(feats, dtype=float)
    # scale
    Xs = (x - model["median"]) / model["iqr"]
    return Xs

def score_vector(x_scaled, model):
    d2 = mahalanobis_d2(x_scaled, model["mu"], model["cov_inv"])
    if model["score_method"] == "empirical":
        score = empirical_score(d2, model["d2_train"])
    else:
        score = chi2_score(d2, model["df"])
    # hard clip
    if score < 0: score = 0.0
    if score > 100: score = 100.0
    return score, d2

def score_pdf(pdf_path, model):
    feat_dict = extract_features_for_pdf(pdf_path)
    x_scaled = transform_features(feat_dict, model)
    score, d2 = score_vector(x_scaled, model)
    feat_dict["mahal_d2"] = d2
    feat_dict["mahal_score"] = score
    return feat_dict

def score_features_csv(row_csv, model):
    """
    Score one or many rows (features already extracted).
    """
    df = pd.read_csv(row_csv)
    out_rows = []
    for _, r in df.iterrows():
        feat_dict = r.to_dict()
        x_scaled = transform_features(feat_dict, model)
        score, d2 = score_vector(x_scaled, model)
        feat_dict["mahal_d2"] = d2
        feat_dict["mahal_score"] = score
        out_rows.append(feat_dict)
    return pd.DataFrame(out_rows)

# ------------------------------------------------------------
# ----------------- CLI --------------------------------------
# ------------------------------------------------------------

def build_argparser():
    ap = argparse.ArgumentParser(description="Mahalanobis Resume Layout Scorer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # train
    ap_train = sub.add_parser("train", help="Train Mahalanobis model on good resumes CSV")
    ap_train.add_argument("--csv", required=True, help="CSV of good resume features")
    ap_train.add_argument("--model-out", required=True, help="Path to save model .pkl")
    ap_train.add_argument("--score-method", choices=["empirical","chi2"], default="empirical")

    # score-pdf
    ap_pdf = sub.add_parser("score-pdf", help="Extract & score a single PDF resume")
    ap_pdf.add_argument("--model", required=True, help="Trained model .pkl")
    ap_pdf.add_argument("--pdf-file", required=True, help="Path to resume PDF")
    ap_pdf.add_argument("--output-csv", help="Optional CSV to append result")

    # score-features
    ap_feat = sub.add_parser("score-features", help="Score one/many feature rows from CSV")
    ap_feat.add_argument("--model", required=True, help="Trained model .pkl")
    ap_feat.add_argument("--features-csv", required=True, help="CSV w/ same cols as training (subset ok)")
    ap_feat.add_argument("--output-csv", help="Where to write scored CSV")

    return ap

def main():
    ap = build_argparser()
    args = ap.parse_args()

    if args.cmd == "train":
        df_scored = train_model(args.csv, args.model_out, score_method=args.score_method)
        # write scored training preview next to model (optional)
        preview_path = os.path.splitext(args.model_out)[0] + "_train_preview.csv"
        df_scored.to_csv(preview_path, index=False)
        print(f"[train] wrote preview scores: {preview_path}")

    elif args.cmd == "score-pdf":
        model = load_model(args.model)
        result = score_pdf(args.pdf_file, model)
        print(json.dumps(result, indent=2))
        if args.output_csv:
            pd.DataFrame([result]).to_csv(args.output_csv, index=False)
            print(f"[score-pdf] wrote: {args.output_csv}")

    elif args.cmd == "score-features":
        model = load_model(args.model)
        df_scored = score_features_csv(args.features_csv, model)
        print(df_scored.head())
        if args.output_csv:
            df_scored.to_csv(args.output_csv, index=False)
            print(f"[score-features] wrote: {args.output_csv}")
