# features_extract.py
"""
Extract numeric layout features from resume PDFs.
Based on the code you provided; cleaned + safe defaults.
"""

import os
import cv2
import numpy as np
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import pdfplumber

import config


# ---------------- PDF -> images ----------------
def _pdf_to_images(pdf_path, dpi=None):
    if dpi is None:
        dpi = config.PDF_DPI
    pil_pages = convert_from_path(pdf_path, dpi=dpi)
    cv_images = []
    for pil in pil_pages:
        arr = np.array(pil)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        cv_images.append(gray)
    return cv_images


# -------------- Whitespace ---------------------
def _total_whitespace_ratio(img, thresh=200):
    _, bw = cv2.threshold(img, thresh, 255, cv2.THRESH_BINARY)
    white = np.count_nonzero(bw == 255)
    return white / bw.size if bw.size else 0.0

def _sectional_whitespace(img, n_sections=4, thresh=200):
    h = img.shape[0]
    ratios = []
    for i in range(n_sections):
        y0 = int(i*h/n_sections); y1 = int((i+1)*h/n_sections)
        ratios.append(_total_whitespace_ratio(img[y0:y1, :], thresh))
    return ratios


# -------------- OCR boxes spacing --------------
def _bbox_spacing(img):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    boxes = []
    for i in range(len(data['level'])):
        try:
            conf = float(data['conf'][i])
        except ValueError:
            conf = -1
        if conf > 0 and str(data['text'][i]).strip():
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            boxes.append((x, y, x+w, y+h))
    if len(boxes) < 2:
        return 0.0, 0.0
    boxes.sort(key=lambda b: (b[1], b[0]))
    hg, vg = [], []
    for (x0,y0,x1,y1),(xx0,yy0,xx1,yy1) in zip(boxes, boxes[1:]):
        hg.append(max(0, xx0 - x1))
        vg.append(max(0, yy0 - y1))
    return (float(np.mean(hg)) if hg else 0.0,
            float(np.mean(vg)) if vg else 0.0)


# -------------- Text density via pdfplumber ----
def _char_density(pdf_path):
    dens = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            txt = p.extract_text() or ''
            area = (p.width * p.height) or 1.0
            dens.append(len(txt) / area)
    return dens or [0.0]

def _block_density(pdf_path, n_blocks=4):
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            h = p.height; block_h = h / n_blocks
            row = {}
            for i in range(n_blocks):
                y0 = i*block_h; y1 = y0 + block_h
                txt = p.within_bbox((0,y0,p.width,y1)).extract_text() or ''
                area = (p.width * block_h) or 1.0
                row[f"block_{i}"] = len(txt.split()) / area
            rows.append(row)
    return rows or [{f"block_{i}":0.0 for i in range(n_blocks)}]


# -------------- Line spacing & section sep -----
def _line_spacing(img):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    lines = {}
    for i, txt in enumerate(data['text']):
        if str(txt).strip():
            ln = data['line_num'][i]
            y = data['top'][i]
            lines.setdefault(ln, []).append(y)
    if not lines: return 0.0
    baselines = sorted(int(np.mean(v)) for v in lines.values())
    if len(baselines) < 2: return 0.0
    return float(np.mean(np.diff(baselines)))

def _section_sep(img):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    bottoms = []
    for i in range(len(data['level'])):
        if str(data['text'][i]).strip():
            bottoms.append(data['top'][i] + data['height'][i])
    if len(bottoms) < 2: return 0.0
    gaps = np.diff(sorted(bottoms))
    med = np.median(gaps) if len(gaps) else 0
    if med <= 0: return 0.0
    big = [g for g in gaps if g > 1.5*med]
    return float(np.mean(big)) if big else 0.0


# -------------- Margins & padding --------------
def _margins(img, thresh=200):
    _, inv = cv2.threshold(img, thresh, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(inv)
    if coords is None:
        return (0.0,0.0,0.0,0.0)
    xs = coords[:,:,0].flatten(); ys = coords[:,:,1].flatten()
    h,w = img.shape
    return (float(np.min(xs)),
            float(w - np.max(xs)),
            float(np.min(ys)),
            float(h - np.max(ys)))

def _padding(img, pad=5, thresh=200):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    paddings = []
    H,W = img.shape
    for i in range(len(data['level'])):
        if str(data['text'][i]).strip():
            x,y = data['left'][i], data['top'][i]
            w,h = data['width'][i], data['height'][i]
            x0=max(0,x-pad); y0=max(0,y-pad); x1=min(W,x+w+pad); y1=min(H,y+h+pad)
            crop = img[y0:y1, x0:x1]
            if crop.size==0: continue
            paddings.append(np.count_nonzero(crop>thresh)/crop.size)
    return float(np.mean(paddings)) if paddings else 0.0


# -------------- Public API ---------------------
def extract_features_for_pdf(pdf_path):
    feats = {}
    images = _pdf_to_images(pdf_path)

    # whitespace
    whites = [_total_whitespace_ratio(i) for i in images]
    feats['whitespace_ratio_avg'] = float(np.mean(whites)) if whites else 0.0

    sects = [_sectional_whitespace(i) for i in images] if images else []
    n_sec = len(sects[0]) if sects else 0
    for j in range(n_sec):
        feats[f'section_whitespace_avg_{j}'] = float(np.mean([s[j] for s in sects]))

    # bbox spacing
    hb, vb = zip(*[_bbox_spacing(i) for i in images]) if images else ([0],[0])
    feats['bbox_h_spacing_avg'] = float(np.mean(hb))
    feats['bbox_v_spacing_avg'] = float(np.mean(vb))

    # char density
    cd = _char_density(pdf_path)
    feats['char_density_avg'] = float(np.mean(cd))

    # block density
    bd = _block_density(pdf_path)
    for key in bd[0].keys():
        idx = key.split("_")[-1]
        feats[f'block_density_avg_{idx}'] = float(np.mean([row[key] for row in bd]))

    # line spacing / section sep
    ls = [_line_spacing(i) for i in images]
    feats['line_spacing_avg'] = float(np.mean(ls))
    ss = [_section_sep(i) for i in images]
    feats['section_sep_avg'] = float(np.mean(ss))

    # margins & padding
    mgs = [_margins(i) for i in images]
    if mgs:
        l = [m[0] for m in mgs]; r=[m[1] for m in mgs]; t=[m[2] for m in mgs]; b=[m[3] for m in mgs]
        feats['margin_left_avg']   = float(np.mean(l))
        feats['margin_right_avg']  = float(np.mean(r))
        feats['margin_top_avg']    = float(np.mean(t))
        feats['margin_bottom_avg'] = float(np.mean(b))
    else:
        for name in ['left','right','top','bottom']:
            feats[f'margin_{name}_avg']=0.0

    pads = [_padding(i) for i in images]
    feats['padding_avg'] = float(np.mean(pads)) if pads else 0.0

    feats['file'] = os.path.basename(pdf_path)
    return feats


def extract_folder(folder, out_csv):
    rows = []
    for root,_,files in os.walk(folder):
        for f in files:
            if not f.lower().endswith(".pdf"): continue
            path = os.path.join(root,f)
            try:
                feats = extract_features_for_pdf(path)
                rows.append(feats)
                print(f"[feat] {f}")
            except Exception as e:
                print(f"[feat:ERROR] {f}: {e}")
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"[feat] wrote {out_csv} (n={len(rows)})")
