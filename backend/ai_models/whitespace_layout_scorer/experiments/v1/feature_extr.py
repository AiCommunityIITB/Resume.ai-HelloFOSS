import os
import cv2
import numpy as np
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output
import pdfplumber

# ------------------------------------------------------------
# Helper: load PDF and convert to images (one per page)
# ------------------------------------------------------------
def pdf_to_images(pdf_path, dpi=200):
    """
    Convert each page of PDF to PIL image at given DPI.
    Returns list of OpenCV grayscale images.
    """
    pil_pages = convert_from_path(pdf_path, dpi=dpi)
    cv_images = []
    for pil in pil_pages:
        arr = np.array(pil)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        cv_images.append(gray)
    return cv_images

# ------------------------------------------------------------
# a. Whitespace Ratio Calculation
# ------------------------------------------------------------
def compute_total_whitespace_ratio(page_img, thresh=200):
    """
    Compute ratio of white (background) pixels to total.
    """
    _, bw = cv2.threshold(page_img, thresh, 255, cv2.THRESH_BINARY)
    white = np.count_nonzero(bw == 255)
    total = bw.size
    return white / total


def compute_sectional_whitespace(page_img, n_sections=4, thresh=200):
    """
    Split page into horizontal bands and compute whitespace ratios per section.
    Returns list of ratios.
    """
    h = page_img.shape[0]
    ratios = []
    for i in range(n_sections):
        y0 = int(i*h/n_sections)
        y1 = int((i+1)*h/n_sections)
        band = page_img[y0:y1, :]
        ratios.append(compute_total_whitespace_ratio(band, thresh=thresh))
    return ratios


def compute_bounding_box_spacing(page_img):
    """
    Use OCR to extract word boxes and compute mean gap between adjacent boxes.
    Returns mean horizontal and vertical spacing.
    """
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    n = len(data['level'])
    boxes = []
    for i in range(n):
        if int(data['conf'][i]) > 0:
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            boxes.append((x, y, x+w, y+h))
    # sort boxes by y then x
    boxes.sort(key=lambda b: (b[1], b[0]))
    hor_gaps, ver_gaps = [], []
    for (x0, y0, x1, y1), (xx0, yy0, xx1, yy1) in zip(boxes, boxes[1:]):
        hor_gaps.append(max(0, xx0 - x1))
        ver_gaps.append(max(0, yy0 - y1))
    return np.mean(hor_gaps) if hor_gaps else 0, np.mean(ver_gaps) if ver_gaps else 0

# ------------------------------------------------------------
# b. Text Density Metrics
# ------------------------------------------------------------
def compute_characters_per_area(pdf_path):
    """
    Using pdfplumber, count characters and divide by total page area.
    Returns list of char densities per page.
    """
    densities = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ''
            chars = len(txt)
            w, h = page.width, page.height
            densities.append(chars / (w * h))
    return densities


def compute_block_density(pdf_path, block_height_ratio=0.25):
    """
    Split page into blocks (top, mid, bottom) and compute word counts per block area.
    Returns dict of densities.
    """
    densities = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            h = page.height
            blocks = []
            for i in range(4):
                y0 = i * h * block_height_ratio
                y1 = y0 + h * block_height_ratio
                txt = page.within_bbox((0, y0, page.width, y1)).extract_text() or ''
                blocks.append(len(txt.split()))
            areas = [page.width * h * block_height_ratio] * 4
            densities.append({f"block_{i}": blocks[i] / areas[i] for i in range(4)})
    return densities

# ------------------------------------------------------------
# c. Line and Paragraph Spacing
# ------------------------------------------------------------
def compute_line_spacing(page_img):
    """
    Detect text lines via OCR and compute average vertical distance between baselines.
    """
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    # collect y positions of text lines
    lines = {}
    for i, text in enumerate(data['text']):
        if text.strip():
            line_num = data['line_num'][i]
            y = data['top'][i]
            lines.setdefault(line_num, []).append(y)
    baselines = [int(np.mean(v)) for v in lines.values()]
    baselines.sort()
    diffs = np.diff(baselines)
    return np.mean(diffs) if len(diffs) > 0 else 0


def compute_section_separation(page_img):
    """
    Compute spacing between large gaps of text clusters -> section breaks.
    Returns mean separation.
    """
    # reuse line spacing detection
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    # get all y-bottom of boxes
    bottoms = []
    for i in range(len(data['level'])):
        if data['text'][i].strip():
            bottoms.append(data['top'][i] + data['height'][i])
    bottoms.sort()
    gaps = np.diff(bottoms)
    # consider gaps larger than 1.5x median as section breaks
    med = np.median(gaps) if len(gaps) else 0
    big = [g for g in gaps if g > 1.5 * med]
    return np.mean(big) if big else 0

# ------------------------------------------------------------
# d. Margins and Padding
# ------------------------------------------------------------
def compute_margins(page_img, thresh=200):
    """
    Estimate left/right/top/bottom margins by scanning for first/last text pixel.
    """
    _, bw = cv2.threshold(page_img, thresh, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(bw)
    if coords is None:
        return (0,0,0,0)
    x_vals = coords[:,:,0].flatten()
    y_vals = coords[:,:,1].flatten()
    h, w = page_img.shape
    left = np.min(x_vals)
    right = w - np.max(x_vals)
    top = np.min(y_vals)
    bottom = h - np.max(y_vals)
    return (left, right, top, bottom)


def compute_padding_around_elements(page_img, pad=5, thresh=200):
    """
    Detect word boxes and compute average whitespace padding around each.
    """
    data = pytesseract.image_to_data(page_img, output_type=Output.DICT)
    paddings = []
    for i in range(len(data['level'])):
        if data['text'][i].strip():
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            # crop around box padded by pad
            crop = page_img[max(0,y-pad):y+h+pad, max(0,x-pad):x+w+pad]
            whites = np.count_nonzero(crop > thresh)
            total = crop.size
            paddings.append(whites/total)
    return np.mean(paddings) if paddings else 0

# ------------------------------------------------------------
# Main: iterate folders, extract features, save CSV
# ------------------------------------------------------------
def extract_features_for_pdf(pdf_path):
    """
    Run all extractors for one PDF, return flat dict of features.
    """
    feats = {}
    images = pdf_to_images(pdf_path)

    # whitespace
    whites = [compute_total_whitespace_ratio(img) for img in images]
    feats['whitespace_ratio_avg'] = np.mean(whites)
    sects = [compute_sectional_whitespace(img) for img in images]
    # flatten sectional ratios
    for i in range(len(sects[0])):
        feats[f'section_whitespace_avg_{i}'] = np.mean([s[i] for s in sects])
    # bounding box spacing
    hb, vb = zip(*[compute_bounding_box_spacing(img) for img in images])
    feats['bbox_h_spacing_avg'] = np.mean(hb)
    feats['bbox_v_spacing_avg'] = np.mean(vb)

    # text density
    char_dens = compute_characters_per_area(pdf_path)
    feats['char_density_avg'] = np.mean(char_dens)
    block_dicts = compute_block_density(pdf_path)
    # average per block index
    for i in range(len(block_dicts[0])):
        feats[f'block_density_avg_{i}'] = np.mean([bd[f'block_{i}'] for bd in block_dicts])

    # spacing
    ls = [compute_line_spacing(img) for img in images]
    feats['line_spacing_avg'] = np.mean(ls)
    ss = [compute_section_separation(img) for img in images]
    feats['section_sep_avg'] = np.mean(ss)

    # margins & padding
    margins = [compute_margins(img) for img in images]
    # unpack and avg
    for idx, name in enumerate(['left','right','top','bottom']):
        feats[f'margin_{name}_avg'] = np.mean([m[idx] for m in margins])
    pads = [compute_padding_around_elements(img) for img in images]
    feats['padding_avg'] = np.mean(pads)

    feats['file'] = os.path.basename(pdf_path)
    return feats


def process_folder(main_folder, output_csv="resume_layout_features.csv"):
    # track whether we’ve already written the header
    header_written = os.path.isfile(output_csv)
    for root, _, files in os.walk(main_folder):
        for f in files:
            if not f.lower().endswith('.pdf'):
                continue
            path = os.path.join(root, f)
            try:
                feats = extract_features_for_pdf(path)
                # wrap single-record dict in a DataFrame
                df = pd.DataFrame([feats])
                # append: header only if this is the first write
                df.to_csv(output_csv,
                          mode='a',
                          header=not header_written,
                          index=False)
                header_written = True
                print(f"Processed and updated CSV for: {path}")
            except Exception as e:
                print(f"Error processing {path}: {e}")

# Example usage:
