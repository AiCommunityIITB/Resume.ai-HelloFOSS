# score_new_resume.py

import pandas as pd
from ai_models.whitespace_layout_scorer.common import FEATURE_NAMES, higher_is_better
from ai_models.whitespace_layout_scorer.extract_features_single import extract_features_for_pdf

def normalize(value, mean, optimum, higher_better):
    # 1. Distance from mean (ideal/typical)
    if optimum == mean:
        dist_to_mean = 1.0
    else:
        dist_to_mean = 1 - abs((value - mean)/(optimum - mean))
        dist_to_mean = max(0.0, min(1.0, dist_to_mean))
    # 2. Distance from best (optimum)
    if optimum == mean:  # avoid divide by zero
        dist_to_best = 1.0
    else:
        dist_to_best = 1 - abs((value - optimum)/(optimum - mean))
        dist_to_best = max(0.0, min(1.0, dist_to_best))
    # Return both
    return dist_to_mean, dist_to_best

def score_resume(feats, stats_df, w_mean=0.2, w_best=0.8, offset=40):
    total = 0
    for i, row in stats_df.iterrows():
        f = row['feature']
        higher_better = higher_is_better(f)
        val = feats[f]
        mean = row['mean']
        optimum = row['optimum']
        # Use separate normalization for higher/lower is better
        if higher_better:
            dist_to_mean = 1 - abs((val - mean) / (optimum - mean)) if optimum != mean else 1.0
            dist_to_best = (val - mean) / (optimum - mean) if optimum != mean else 1.0
        else:
            dist_to_mean = 1 - abs((val - mean) / (mean - optimum)) if optimum != mean else 1.0
            dist_to_best = (mean - val) / (mean - optimum) if optimum != mean else 1.0
        dist_to_mean = max(0.0, min(1.0, dist_to_mean))
        dist_to_best = max(0.0, min(1.0, dist_to_best))
        score = w_mean * dist_to_mean + w_best * dist_to_best
        total += score
    raw_score = (total / len(stats_df)) * 100
    # === ADD OFFSET and CLIP ===
    final_score = min(100, max(0, raw_score + offset))
    final_scorev2 = ((final_score - 55)/30)*100
    final_scale = max(0, min(100, final_scorev2))

    return final_scale
