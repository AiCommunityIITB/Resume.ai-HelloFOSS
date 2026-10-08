#!/usr/bin/env python3
"""
BEGINNER FINAL SCORER

Loads:
  - KNN layout model
  - LayoutLMv3 embedding model

Scores every PDF in config.NEW_PDFS_DIR with both models, then
combines them using simple weights and one tuning shift.

Edit the weights and FINAL_SHIFT below if you want to tweak.

Output: config.FINAL_SCORED_CSV
"""

import os
import pandas as pd

import config as cfg
import score_knn as knn_scorer
import score_layoutlmv3 as emb_scorer

# ----------- SIMPLE TUNING -----------
FINAL_WEIGHT_EMB = 0.6   # embedding weight
FINAL_WEIGHT_KNN = 0.4   # layout (KNN) weight
FINAL_SHIFT      = 70.0   # add to final blended score (can be negative)

# clip results
FINAL_MIN = 0.0
FINAL_MAX = 100.0
# -------------------------------------


def main():
    knn_model = knn_scorer._load_model()
    emb_model = emb_scorer._load_model()

    rows=[]
    for root,_,files in os.walk(cfg.NEW_PDFS_DIR):
        for f in files:
            if not f.lower().endswith(".pdf"): continue
            p=os.path.join(root,f)

            # sub-scores
            try:
                knn_row = knn_scorer.score_pdf(p,knn_model)
                knn_score = knn_row["knn_score"]
            except Exception as e:
                print(f"[final:knnERR] {f}: {e}")
                knn_row={"knn_score":None,"knn_dist":None}
                knn_score=None

            try:
                emb_row = emb_scorer.score_pdf(p,emb_model)
                emb_score = emb_row["emb_score"]
            except Exception as e:
                print(f"[final:embERR] {f}: {e}")
                emb_row={"emb_score":None,"emb_sim":None}
                emb_score=None

            # blend
            if emb_score is not None and knn_score is not None:
                s=(FINAL_WEIGHT_EMB*emb_score)+(FINAL_WEIGHT_KNN*knn_score)
            elif emb_score is not None:
                s=emb_score
            elif knn_score is not None:
                s=knn_score
            else:
                s=None

            if s is not None:
                s+=FINAL_SHIFT
                s=max(FINAL_MIN,min(FINAL_MAX,s))

            row={
                "file":f,
                "emb_score":emb_row.get("emb_score"),
                "emb_sim":emb_row.get("emb_sim"),
                "knn_score":knn_row.get("knn_score"),
                "knn_dist":knn_row.get("knn_dist"),
                "final_score":s,
            }
            rows.append(row)
            print(f"[final] {f}: {s if s is not None else 'NA'}")

    pd.DataFrame(rows).to_csv(cfg.FINAL_SCORED_CSV,index=False)
    print(f"[final] wrote {cfg.FINAL_SCORED_CSV} (n={len(rows)})")
