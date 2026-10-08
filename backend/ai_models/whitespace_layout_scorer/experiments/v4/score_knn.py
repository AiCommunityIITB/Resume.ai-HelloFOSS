#!/usr/bin/env python3
"""
BEGINNER KNN SCORER (layout features).

Loads model from config.KNN_MODEL_PKL.
Extracts features for each PDF in config.NEW_PDFS_DIR.
Computes KNN distance -> 0-100 percentile score.
Writes config.KNN_SCORED_CSV
"""

import os
import pickle
import numpy as np
import pandas as pd

import config as cfg
import features_extract as fx


def _load_model():
    with open(cfg.KNN_MODEL_PKL,"rb") as f:
        return pickle.load(f)


def _score_feat_dict(feat_dict, model):
    # align features
    xs=[]
    for col,mu in zip(model["feat_cols"], model["mean"]):
        v=feat_dict.get(col,mu)
        try: v=float(v)
        except: v=mu
        xs.append(v)
    xs=np.array(xs,dtype=float)[None,:]
    xs=(xs-model["mean"])/model["std"]

    k=min(model["k"], len(model["dist_train"]))
    dists,_=model["knn"].kneighbors(xs,n_neighbors=k,return_distance=True)
    d=float(np.mean(dists[0]))

    # percentile relative to training distances (smaller better)
    dist_train=model["dist_train"]
    score=100.0*np.mean(dist_train>=d)
    return score,d


def score_pdf(pdf_path, model=None):
    if model is None: model=_load_model()
    feats=fx.extract_features_for_pdf(pdf_path)
    score,d=_score_feat_dict(feats,model)
    return {
        "file":os.path.basename(pdf_path),
        "knn_score":score,
        "knn_dist":d,
    }


def main():
    model=_load_model()
    rows=[]
    for root,_,files in os.walk(cfg.NEW_PDFS_DIR):
        for f in files:
            if not f.lower().endswith(".pdf"): continue
            p=os.path.join(root,f)
            try:
                rows.append(score_pdf(p,model))
                print(f"[knn] {f}")
            except Exception as e:
                print(f"[knn:ERR] {f}: {e}")
    pd.DataFrame(rows).to_csv(cfg.KNN_SCORED_CSV,index=False)
    print(f"[knn] wrote {cfg.KNN_SCORED_CSV} (n={len(rows)})")
