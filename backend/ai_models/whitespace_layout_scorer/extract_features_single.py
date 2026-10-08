# extract_features_single.py

from ai_models.whitespace_layout_scorer.common import FEATURE_NAMES
import numpy as np
import cv2
from pdf2image import convert_from_bytes
import pytesseract
from pytesseract import Output
import pdfplumber, os

PDF_DPI = 200  # Or set via config

# === Crop settings (in centimeters) ===
TOP_CROP_CM = 6.0
SIDE_CROP_CM = 1.0
BOTTOM_CROP_CM = 1.0

CM_PER_INCH = 2.54
PT_PER_INCH = 72.0

def cm_to_px(cm, dpi=PDF_DPI):
    return int(round(cm * dpi / CM_PER_INCH))

def cm_to_pt(cm):
    return (cm * PT_PER_INCH) / CM_PER_INCH

def _crop_image_cm(img, dpi=PDF_DPI,
                   top_cm=TOP_CROP_CM, side_cm=SIDE_CROP_CM, bottom_cm=BOTTOM_CROP_CM):
    """Crop an OpenCV grayscale image by cm margins; returns cropped ROI (safe-clipped)."""
    H, W = img.shape[:2]
    left_px   = cm_to_px(side_cm, dpi)
    right_px  = cm_to_px(side_cm, dpi)
    top_px    = cm_to_px(top_cm, dpi)
    bottom_px = cm_to_px(bottom_cm, dpi)

    x0 = min(max(0, left_px), W)
    x1 = max(x0, min(W, W - right_px))
    y0 = min(max(0, top_px), H)
    y1 = max(y0, min(H, H - bottom_px))

    # If margins collapse the ROI, fall back to original
    if (x1 - x0) < 1 or (y1 - y0) < 1:
        return img
    return img[y0:y1, x0:x1]

import io

def _pdf_to_images(pdf_bytes, dpi=PDF_DPI):
    pil_pages = convert_from_bytes(pdf_bytes, dpi=dpi)
    cv_images = []
    for pil in pil_pages:
        arr = np.array(pil)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        gray = _crop_image_cm(gray, dpi=dpi)
        cv_images.append(gray)
    return cv_images

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

def _char_density(pdf_bytes):
    """Characters per unit area inside cropped ROI (cm margins applied in PDF point space)."""
    dens = []
    left_pt   = cm_to_pt(SIDE_CROP_CM)
    right_pt  = cm_to_pt(SIDE_CROP_CM)
    top_pt    = cm_to_pt(TOP_CROP_CM)
    bottom_pt = cm_to_pt(BOTTOM_CROP_CM)

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p in pdf.pages:
            W = max(0.0, p.width  - (left_pt + right_pt))
            H = max(0.0, p.height - (top_pt + bottom_pt))
            if W > 0 and H > 0:
                x0 = left_pt
                y0 = top_pt
                x1 = left_pt + W
                y1 = top_pt + H
                region = p.within_bbox((x0, y0, x1, y1))
                txt = region.extract_text() or ''
                area = (W * H) or 1.0
            else:
                # Fallback to full page if margins are too large
                txt = p.extract_text() or ''
                area = (p.width * p.height) or 1.0
            dens.append(len(txt) / area)
    return dens or [0.0]

def _block_density(pdf_bytes, n_blocks=4):
    """
    Word density per vertical block inside cropped ROI.
    Blocks partition the cropped height equally; width is the cropped width.
    """
    rows = []
    left_pt   = cm_to_pt(SIDE_CROP_CM)
    right_pt  = cm_to_pt(SIDE_CROP_CM)
    top_pt    = cm_to_pt(TOP_CROP_CM)
    bottom_pt = cm_to_pt(BOTTOM_CROP_CM)

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p in pdf.pages:
            W = max(0.0, p.width  - (left_pt + right_pt))
            H = max(0.0, p.height - (top_pt + bottom_pt))
            if W <= 0 or H <= 0:
                # Fallback to full page partitioning if margins collapse ROI
                left = 0.0; top = 0.0; W = p.width; H = p.height
            else:
                left = left_pt; top = top_pt

            block_h = H / n_blocks if n_blocks > 0 else H
            row = {}
            for i in range(n_blocks):
                y0 = top + i*block_h
                y1 = y0 + block_h
                region = p.within_bbox((left, y0, left + W, y1))
                txt = region.extract_text() or ''
                area = (W * block_h) or 1.0
                row[f"block_{i}"] = len(txt.split()) / area
            rows.append(row)
    return rows or [{f"block_{i}":0.0 for i in range(n_blocks)}]

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

def _margins(img, thresh=200):
    """Margins of content inside the *cropped* ROI image."""
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

def extract_features_for_pdf(pdf_bytes):
    feats = {}
    images = _pdf_to_images(pdf_bytes)

    whites = [_total_whitespace_ratio(i) for i in images]
    feats['whitespace_ratio_avg'] = float(np.mean(whites)) if whites else 0.0

    sects = [_sectional_whitespace(i) for i in images] if images else []
    n_sec = len(sects[0]) if sects else 0
    for j in range(n_sec):
        feats[f'section_whitespace_avg_{j}'] = float(np.mean([s[j] for s in sects]))

    hb, vb = zip(*[_bbox_spacing(i) for i in images]) if images else ([0],[0])
    feats['bbox_h_spacing_avg'] = float(np.mean(hb))
    feats['bbox_v_spacing_avg'] = float(np.mean(vb))

    cd = _char_density(pdf_bytes)
    feats['char_density_avg'] = float(np.mean(cd))

    bd = _block_density(pdf_bytes)
    for key in bd[0].keys():
        idx = key.split("_")[-1]
        feats[f'block_density_avg_{idx}'] = float(np.mean([row[key] for row in bd]))

    ls = [_line_spacing(i) for i in images] if images else []
    feats['line_spacing_avg'] = float(np.mean(ls)) if ls else 0.0
    ss = [_section_sep(i) for i in images] if images else []
    feats['section_sep_avg'] = float(np.mean(ss)) if ss else 0.0

    mgs = [_margins(i) for i in images] if images else []
    if mgs:
        l = [m[0] for m in mgs]; r=[m[1] for m in mgs]; t=[m[2] for m in mgs]; b=[m[3] for m in mgs]
        feats['margin_left_avg']   = float(np.mean(l))
        feats['margin_right_avg']  = float(np.mean(r))
        feats['margin_top_avg']    = float(np.mean(t))
        feats['margin_bottom_avg'] = float(np.mean(b))
    else:
        for name in ['left','right','top','bottom']:
            feats[f'margin_{name}_avg']=0.0

    pads = [_padding(i) for i in images] if images else []
    feats['padding_avg'] = float(np.mean(pads)) if pads else 0.0

    return feats
