#!/usr/bin/env python3
import os
import cv2
import numpy as np
import pandas as pd
import argparse
import pickle

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import pdfplumber
from sklearn.ensemble import IsolationForest

# ----------------------------------------------------------------
# 1. All your feature‐extraction functions (unchanged)
# ----------------------------------------------------------------
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
    return np.count_nonzero(bw == 255) / bw.size

def compute_sectional_whitespace(page_img, n_sections=4, thresh=200):
    h = page_img.shape[0]
    ratios = []
    for i in range(n_sections):
        y0 = int(i*h/n_sections)
        y1 = int((i+1)*h/n_sections)
        band = page_img[y0:y1, :]
        ratios.append(compute_total_whitespace_ratio(band, thresh))
    return ratios

def compute_bounding_box_spacing(page_img):
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    boxes = []
    for i, txt in enumerate(data['text']):
        if txt.strip() and int(data['conf'][i]) > 0:
            x,y,w,h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            boxes.append((x,y,x+w,y+h))
    boxes.sort(key=lambda b: (b[1],b[0]))
    hor, ver = [], []
    for (x0,y0,x1,y1),(x2,y2,x3,y3) in zip(boxes, boxes[1:]):
        hor.append(max(0, x2 - x1))
        ver.append(max(0, y2 - y1))
    return (np.mean(hor) if hor else 0, np.mean(ver) if ver else 0)

def compute_characters_per_area(pdf_path):
    densities = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ''
            densities.append(len(txt) / (page.width * page.height))
    return densities

def compute_block_density(pdf_path, block_height_ratio=0.25):
    densities = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            h = page.height
            blocks = []
            for i in range(4):
                y0 = i * h * block_height_ratio
                y1 = y0 + h * block_height_ratio
                txt = page.within_bbox((0,y0,page.width,y1)).extract_text() or ''
                blocks.append(len(txt.split()))
            area = page.width * h * block_height_ratio
            densities.append({f"block_{i}": blocks[i]/area for i in range(4)})
    return densities

def compute_line_spacing(page_img):
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    lines = {}
    for i, txt in enumerate(data['text']):
        if txt.strip():
            ln = data['line_num'][i]
            lines.setdefault(ln, []).append(data['top'][i])
    baselines = sorted(int(np.mean(v)) for v in lines.values())
    diffs = np.diff(baselines)
    return np.mean(diffs) if len(diffs) else 0

def compute_section_separation(page_img):
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    bottoms = []
    for i, txt in enumerate(data['text']):
        if txt.strip():
            bottoms.append(data['top'][i] + data['height'][i])
    bottoms.sort()
    gaps = np.diff(bottoms)
    med = np.median(gaps) if len(gaps) else 0
    big = [g for g in gaps if g > 1.5 * med]
    return np.mean(big) if big else 0

def compute_margins(page_img, thresh=200):
    _, bw = cv2.threshold(page_img, thresh, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(bw)
    if coords is None:
        return (0,0,0,0)
    xs = coords[:,:,0].flatten()
    ys = coords[:,:,1].flatten()
    h, w = page_img.shape
    return (xs.min(), w - xs.max(), ys.min(), h - ys.max())

def compute_padding_around_elements(page_img, pad=5, thresh=200):
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    pads = []
    for i, txt in enumerate(data['text']):
        if txt.strip():
            x,y,w,h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            crop = page_img[max(0,y-pad):y+h+pad, max(0,x-pad):x+w+pad]
            whites = np.count_nonzero(crop > thresh)
            pads.append(whites / crop.size)
    return np.mean(pads) if pads else 0

def extract_features_for_pdf(pdf_path):
    feats = {}
    images = pdf_to_images(pdf_path)

    # whitespace
    ws = [compute_total_whitespace_ratio(im) for im in images]
    feats['whitespace_ratio_avg'] = np.mean(ws)
    secs = [compute_sectional_whitespace(im) for im in images]
    for i in range(len(secs[0])):
        feats[f'section_whitespace_avg_{i}'] = np.mean([s[i] for s in secs])

    # bbox spacing
    hb, vb = zip(*[compute_bounding_box_spacing(im) for im in images])
    feats['bbox_h_spacing_avg'] = np.mean(hb)
    feats['bbox_v_spacing_avg'] = np.mean(vb)

    # text density
    cd = compute_characters_per_area(pdf_path)
    feats['char_density_avg'] = np.mean(cd)
    bd = compute_block_density(pdf_path)
    for i in range(len(bd[0])):
        feats[f'block_density_avg_{i}'] = np.mean([b[f'block_{i}'] for b in bd])

    # line & section spacing
    ls = [compute_line_spacing(im) for im in images]
    feats['line_spacing_avg'] = np.mean(ls)
    ss = [compute_section_separation(im) for im in images]
    feats['section_sep_avg'] = np.mean(ss)

    # margins & padding
    ms = [compute_margins(im) for im in images]
    for idx,nm in enumerate(['left','right','top','bottom']):
        feats[f'margin_{nm}_avg'] = np.mean([m[idx] for m in ms])
    pads = [compute_padding_around_elements(im) for im in images]
    feats['padding_avg'] = np.mean(pads)

    feats['file'] = os.path.basename(pdf_path)
    return feats

# ----------------------------------------------------------------
# 2. TRAIN OUTLIER MODEL (only needs --csv)
# ----------------------------------------------------------------
def train_outlier_model(feature_csv, model_path, contamination=0.05):
    df = pd.read_csv(feature_csv)
    X = df.drop(columns=['file']).values
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(X)
    raw = model.decision_function(X)
    meta = {'model': model, 'raw_min': raw.min(), 'raw_max': raw.max()}
    with open(model_path, 'wb') as f:
        pickle.dump(meta, f)
    print(f"Model trained and saved to {model_path}")
    print(f"Raw‐score range: {meta['raw_min']:.4f} – {meta['raw_max']:.4f}")

# ----------------------------------------------------------------
# 3. SCORE A SINGLE PDF (does NOT require --csv)
# ----------------------------------------------------------------
def score_single_pdf(pdf_path, model_path, output_csv):
    with open(model_path, 'rb') as f:
        meta = pickle.load(f)
    model, rmin, rmax = meta['model'], meta['raw_min'], meta['raw_max']

    feats = extract_features_for_pdf(pdf_path)
    df = pd.DataFrame([feats])
    X = df.drop(columns=['file']).values

    raw = model.decision_function(X)[0]
    norm = 100 * (raw - rmin) / (rmax - rmin) if rmax > rmin else 0

    df['score_raw']  = raw
    df['score_norm'] = np.clip(norm, 0, 100)
    df.to_csv(output_csv, index=False)
    print(f"Scored '{os.path.basename(pdf_path)}' → {output_csv}")

# ----------------------------------------------------------------
# 4. CLI: --csv only for training; --pdf-file only for scoring
# ----------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description="Train outlier model on CSV or score a single PDF"
    )
    p.add_argument(
        "--csv", help="Features CSV (only needed with --train-model)"
    )
    p.add_argument(
        "--model-path", default="resume_outlier_model.pkl",
        help="Path to save/load the IsolationForest model"
    )
    p.add_argument(
        "--train-model", action="store_true",
        help="Train the outlier model from --csv"
    )
    p.add_argument(
        "--contamination", type=float, default=0.05,
        help="Contamination rate for training"
    )
    p.add_argument(
        "--pdf-file", help="Single PDF resume to score"
    )
    p.add_argument(
        "--output-csv", default="scored_resume.csv",
        help="Where to write the one‐row scored CSV"
    )
    args = p.parse_args()

    if args.train_model:
        if not args.csv:
            p.error("--csv is required when using --train-model")
        train_outlier_model(args.csv, args.model_path, args.contamination)

    if args.pdf_file:
        score_single_pdf(args.pdf_file, args.model_path, args.output_csv)
