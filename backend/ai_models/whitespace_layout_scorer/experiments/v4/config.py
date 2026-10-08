# config.py
"""
Basic configuration shared by all scripts.
Edit these paths & weights before running.
"""

# --- where your data lives ---
GOOD_PDFS_DIR   = "../all_resumes"      # folder of ~250 good resumes
NEW_PDFS_DIR    = "../target_pdfs"       # folder of resumes to score

# --- features CSV for good resumes (you ALREADY have this) ---
# if this file is missing, train_knn.py will extract features from GOOD_PDFS_DIR and write it.
GOOD_FEATURES_CSV = "resume_layout_features_500.csv"

# --- model pickle filenames ---
KNN_MODEL_PKL      = "knn_model.pkl"
EMB_MODEL_PKL      = "layoutlmv3_model.pkl"


# --- LayoutLMv3 embedding training outputs ---
EMB_CSV_GOOD     = "good_emb.csv"  # where to store embeddings for GOOD_PDFS_DIR

# --- Minimum tokens per page before falling back to dummy token ---
MIN_TOKENS_PAGE  = 5               # small integer; 5 is usually fine

# --- where to save scoring outputs ---
KNN_SCORED_CSV     = "new_knn_scores.csv"
EMB_SCORED_CSV     = "new_emb_scores.csv"
FINAL_SCORED_CSV   = "new_final_scores.csv"

# --- KNN params ---
K_NEIGHBORS   = 5            # average distance to k nearest good resumes
KNN_METRIC    = "euclidean"  # see sklearn.neighbors.NearestNeighbors

# --- embedding model name (HuggingFace) ---
LAYOUTLMV3_NAME = "microsoft/layoutlmv3-base"
MAX_SEQ_LEN     = 512

# --- feature extraction DPI (used when extracting features or page images) ---
PDF_DPI = 200
