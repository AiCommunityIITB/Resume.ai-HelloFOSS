#!/usr/bin/env python3
"""
BEGINNER LayoutLMv3 SCORER.

Loads model from config.EMB_MODEL_PKL.
Embeds each PDF in config.NEW_PDFS_DIR.
Computes cosine similarity to centroid -> percentile score relative to training sims.
Writes config.EMB_SCORED_CSV
"""

import os
import pickle
import numpy as np
import pandas as pd

import config as cfg
from train_layoutlmv3 import embed_pdf  # reuse training embed function


def _load_model():
    with open(cfg.EMB_MODEL_PKL,"rb") as f:
        return pickle.load(f)


def _l2(v,eps=1e-9):
    n=np.linalg.norm(v,axis=-1,keepdims=True)
    n=np.maximum(n,eps)
    return v/n

def _sim_to_score(s, sims_train):
    return 100.0*np.mean(sims_train<=s)


def score_pdf(pdf_path, model=None):
    if model is None: model=_load_model()
    emb=embed_pdf(pdf_path)
    emb=_l2(emb[None,:])[0]
    sim=float(np.dot(emb, model["centroid"]))
    score=_sim_to_score(sim, model["sims_train"])
    return {
        "file":os.path.basename(pdf_path),
        "emb_score":score,
        "emb_sim":sim,
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
                print(f"[emb] {f}")
            except Exception as e:
                print(f"[emb:ERR] {f}: {e}")
    pd.DataFrame(rows).to_csv(cfg.EMB_SCORED_CSV,index=False)
    print(f"[emb] wrote {cfg.EMB_SCORED_CSV} (n={len(rows)})")
