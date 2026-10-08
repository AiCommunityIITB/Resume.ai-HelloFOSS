#!/usr/bin/env python3
"""Train a One-Class SVM layout scorer on *excellent* resume feature data.

Edit TRAIN_CSV / MODEL_OUT paths below, run the script once, and it will:
  1. Load the training CSV of excellent resumes (numeric layout features).
  2. Fit a StandardScaler + OneClassSVM (RBF) model.
  3. Save the trained pipeline + training raw scores for percentile mapping.
  4. Print a quick summary + 0-100 score stats on the training set.

Expected CSV columns (example):
    whitespace_ratio_avg, section_whitespace_avg_0, ..., padding_avg, file

"file" (string) is ignored for training if present.
All other *numeric* columns are used.

Simple. No CLI args. Paths are hard-coded.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import joblib
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

# ------------------------------------------------------------------
# Config: change these paths as needed
# ------------------------------------------------------------------
TRAIN_CSV = Path("resume_layout_features.csv")      # your 250 excellent resume features
MODEL_OUT = Path("layout_scorer_ocsvm.pkl")    # where the trained model bundle goes

# One-Class SVM hyperparams (edit if you want)
NU = 0.05       # approx upper bound on outlier frac among training goods
GAMMA = "scale" # RBF width; "scale" usually fine w/ StandardScaler

# ------------------------------------------------------------------
# Data loading
# ------------------------------------------------------------------
def load_training_data(path: Path = TRAIN_CSV):
    df = pd.read_csv(path)
    # Select numeric columns only (ignore text cols like 'file')
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    # In case some numeric columns are actually IDs you don't want, edit here.
    feature_cols = numeric_cols.copy()
    # If your 'file' column is non-numeric it won't be in numeric_cols anyway.
    X = df[feature_cols].astype(float).values
    return df, feature_cols, X

# ------------------------------------------------------------------
# Train OC-SVM pipeline
# ------------------------------------------------------------------
def train_ocsvm(X, nu: float = NU, gamma = GAMMA):
    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("ocsvm", OneClassSVM(kernel="rbf", gamma=gamma, nu=nu))
    ])
    pipe.fit(X)
    raw = pipe.decision_function(X)  # +ve inlier, -ve outlier region
    return pipe, raw

# ------------------------------------------------------------------
# Save / load model bundle
# ------------------------------------------------------------------
def save_model(pipe, train_scores_raw, feature_cols, path: Path = MODEL_OUT):
    payload = {
        "model": pipe,
        "train_scores_raw": train_scores_raw,
        "train_scores_sorted": np.sort(train_scores_raw),
        "feature_cols": feature_cols,
    }
    joblib.dump(payload, path)
    return path


def load_scorer(path: Path = MODEL_OUT):
    return joblib.load(path)

# ------------------------------------------------------------------
# Scoring helpers (percentile -> 0-100)
# ------------------------------------------------------------------
def raw_to_percentile(raw_score: float, train_scores_sorted: np.ndarray) -> float:
    # fraction of training scores <= raw_score
    return float(np.searchsorted(train_scores_sorted, raw_score, side="right") / len(train_scores_sorted))


def percentile_to_score(p: float) -> float:
    return float(round(100.0 * p, 2))


def score_rows(df_features: pd.DataFrame, scorer_payload) -> np.ndarray:
    pipe = scorer_payload["model"]
    train_sorted = scorer_payload["train_scores_sorted"]
    feature_cols = scorer_payload["feature_cols"]

    X = df_features[feature_cols].astype(float).values
    raw = pipe.decision_function(X)
    p = np.array([raw_to_percentile(r, train_sorted) for r in raw])
    return np.array([percentile_to_score(pi) for pi in p])

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    print(f"Loading training data: {TRAIN_CSV}")
    df, feature_cols, X = load_training_data()
    print(f"Loaded shape: {X.shape[0]} samples, {X.shape[1]} features.")

    print("Training One-Class SVM...")
    pipe, raw = train_ocsvm(X)

    out_path = save_model(pipe, raw, feature_cols)
    print(f"Model saved to: {out_path}")

    # Quick training-set score sanity check
    payload = load_scorer(out_path)
    train_scores = score_rows(df, payload)
    print("\nTraining-set 0-100 score summary:\n", pd.Series(train_scores).describe())
    print("\nFirst 5 training rows (score):")
    for fname, sc in zip(df.index[:5], train_scores[:5]):
        print(f"  row {fname}: {sc}")
