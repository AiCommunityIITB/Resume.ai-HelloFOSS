import os
import cv2
import numpy as np
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import pdfplumber
import argparse

# ------------------------------------------------------------
# PDF to Image Conversion
# ------------------------------------------------------------
def pdf_to_images(pdf_path, dpi=200):
    pil_pages = convert_from_path(pdf_path, dpi=dpi)
    images = []
    for pil in pil_pages:
        arr = np.array(pil)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        images.append(gray)
    return images

# ------------------------------------------------------------
# Feature Computation
# ------------------------------------------------------------
def compute_total_whitespace_ratio(img, thresh=200):
    _, bw = cv2.threshold(img, thresh, 255, cv2.THRESH_BINARY)
    return np.count_nonzero(bw == 255) / bw.size

def compute_sectional_whitespace(img, n=4, thresh=200):
    h = img.shape[0]
    return [compute_total_whitespace_ratio(img[int(i*h/n):int((i+1)*h/n), :], thresh)
            for i in range(n)]

def compute_bounding_box_spacing(img):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    boxes = [(data['left'][i], data['top'][i], data['left'][i] + data['width'][i], data['top'][i] + data['height'][i])
             for i, conf in enumerate(data['conf']) if int(conf) > 0]
    boxes.sort(key=lambda b: (b[1], b[0]))
    hor, ver = [], []
    for b0, b1 in zip(boxes, boxes[1:]):
        hor.append(max(0, b1[0] - b0[2]))
        ver.append(max(0, b1[1] - b0[3]))
    return (np.mean(hor) if hor else 0, np.mean(ver) if ver else 0)

def compute_char_density(pdf_path):
    dens = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            txt = p.extract_text() or ''
            dens.append(len(txt) / (p.width * p.height))
    return dens

def compute_block_density(pdf_path, blocks=4):
    bd = []
    with pdfplumber.open(pdf_path) as pdf:
        for p in pdf.pages:
            h = p.height
            vals = []
            for i in range(blocks):
                txt = p.within_bbox((0, i*h/blocks, p.width, (i+1)*h/blocks)).extract_text() or ''
                vals.append(len(txt.split()) / (p.width * h/blocks))
            bd.append(vals)
    return bd

def compute_line_spacing(img):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    lines = {}
    for i, txt in enumerate(data['text']):
        if txt.strip():
            lines.setdefault(data['line_num'][i], []).append(data['top'][i])
    base = sorted(int(np.mean(v)) for v in lines.values())
    diffs = np.diff(base) if len(base) > 1 else []
    return np.mean(diffs) if len(diffs) > 0 else 0

def compute_section_sep(img):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    bottoms = [data['top'][i] + data['height'][i] for i, txt in enumerate(data['text']) if txt.strip()]
    bottoms.sort()
    gaps = np.diff(bottoms) if len(bottoms) > 1 else []
    med = np.median(gaps) if len(gaps) > 0 else 0
    big = [g for g in gaps if g > 1.5 * med]
    return np.mean(big) if big else 0

def compute_margins(img, thresh=200):
    _, inv = cv2.threshold(img, thresh, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(inv)
    if coords is None:
        return (0, 0, 0, 0)
    x = coords[:, :, 0].flatten()
    y = coords[:, :, 1].flatten()
    h, w = img.shape
    return (x.min(), w - x.max(), y.min(), h - y.max())

def compute_padding(img, pad=5, thresh=200):
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    pads = []
    for i, txt in enumerate(data['text']):
        if txt.strip():
            x, y, w0, h0 = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            crop = img[max(0, y-pad):y+h0+pad, max(0, x-pad):x+w0+pad]
            pads.append(np.count_nonzero(crop > thresh) / crop.size)
    return np.mean(pads) if pads else 0

# ------------------------------------------------------------
# Visualization with Labels
# ------------------------------------------------------------
def annotate_image(img, feats, out_path, pad=5, n_sections=4):
    vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    h, w = img.shape

    # 1) Section bands + whitespace ratio labels
    for i in range(n_sections):
        y0 = int(i * h / n_sections)
        y1 = int((i + 1) * h / n_sections)
        cv2.rectangle(vis, (0, y0), (w-1, y1), (0, 255, 255), 2)
        key = f'sect_whitespace_{i}_avg'
        val = feats.get(key, 0)
        cv2.putText(vis, f'{key}:{val:.2f}', (5, y0 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    # 2) Margin box + labels
    left, right, top, bottom = compute_margins(img)
    cv2.rectangle(vis, (left, top), (w-right, h-bottom), (0, 0, 255), 2)
    cv2.putText(vis, f'Margins L,R,T,B={left},{right},{top},{bottom}', (10, h - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

    # 3) Padding around words (blue) + padding avg
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    for i, txt in enumerate(data['text']):
        if txt.strip():
            x, y, w0, h0 = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            cv2.rectangle(vis, (max(0, x-pad), max(0, y-pad)), (min(w-1, x+w0+pad), min(h-1, y+h0+pad)), (255, 0, 0), 1)
    cv2.putText(vis, f'padding_avg:{feats.get("padding_avg",0):.2f}', (10, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    # 4) Word boxes (green) + bbox spacing
    for i, conf in enumerate(data['conf']):
        if int(conf) > 0:
            x, y, w0, h0 = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            cv2.rectangle(vis, (x, y), (x+w0, y+h0), (0, 255, 0), 1)
    hsp = feats.get('bbox_h_avg', 0)
    vsp = feats.get('bbox_v_avg', 0)
    cv2.putText(vis, f'bbox_h_avg:{hsp:.2f}', (10, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
    cv2.putText(vis, f'bbox_v_avg:{vsp:.2f}', (150, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

    # 5) Other metrics header (white)
    y0 = 15
    for k, v in feats.items():
        if k not in [f'sect_whitespace_{i}_avg' for i in range(n_sections)] + ['padding_avg', 'bbox_h_avg', 'bbox_v_avg', 'file']:
            cv2.putText(vis, f'{k}:{v:.3f}', (w//2, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            y0 += 15

    cv2.imwrite(out_path, vis)

# ------------------------------------------------------------
# Main: single-PDF
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf')
    parser.add_argument('--csv', default='output_features.csv')
    parser.add_argument('--img', default='annotated.png')
    args = parser.parse_args()

    images = pdf_to_images(args.pdf)
    feats = {}

    # Compute all metrics and average per PDF
    feats['whitespace_avg'] = np.mean([compute_total_whitespace_ratio(im) for im in images])
    sects = [compute_sectional_whitespace(im) for im in images]
    for i in range(len(sects[0])):
        feats[f'sect_whitespace_{i}_avg'] = np.mean([s[i] for s in sects])
    hb, vb = zip(*[compute_bounding_box_spacing(im) for im in images])
    feats['bbox_h_avg'], feats['bbox_v_avg'] = np.mean(hb), np.mean(vb)
    cd = compute_char_density(args.pdf)
    feats['char_density_avg'] = np.mean(cd)
    bd = compute_block_density(args.pdf)
    for i in range(len(bd[0])):
        feats[f'block_density_{i}_avg'] = np.mean([b[i] for b in bd])
    feats['line_spacing_avg']    = np.mean([compute_line_spacing(im) for im in images])
    feats['section_sep_avg']     = np.mean([compute_section_sep(im)    for im in images])
    marg = [compute_margins(im) for im in images]
    for idx,nm in enumerate(['left','right','top','bottom']): feats[f'margin_{nm}_avg'] = np.mean([m[idx] for m in marg])
    feats['padding_avg'] = np.mean([compute_padding(im) for im in images])
    feats['file'] = os.path.basename(args.pdf)

    # Save CSV and annotated image
    pd.DataFrame([feats]).to_csv(args.csv, index=False)
    print(f"Features -> {args.csv}")
    annotate_image(images[0], feats, args.img)
    print(f"Annotated -> {args.img}")
