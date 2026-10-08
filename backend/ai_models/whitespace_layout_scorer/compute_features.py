# compute_feature_stats.py

import pandas as pd
from ai_models.whitespace_layout_scorer.common import FEATURE_NAMES, higher_is_better

def compute_stats(feature_csv, out_stats_csv):
    df = pd.read_csv(feature_csv)
    stats = []
    for f in FEATURE_NAMES:
        mean = df[f].mean()
        if higher_is_better(f):
            optimum = df[f].max()
        else:
            optimum = df[f].min()
        stats.append({'feature': f, 'mean': mean, 'optimum': optimum})
    stats_df = pd.DataFrame(stats)
    stats_df.to_csv(out_stats_csv, index=False)
    print(stats_df.to_string(index=False))
    print(f"\nStats CSV saved to '{out_stats_csv}'")
    return stats_df
