import os
import pandas as pd
from ai_models.whitespace_layout_scorer.extract_features_single import extract_features_for_pdf
from ai_models.whitespace_layout_scorer.common import FEATURE_NAMES
from ai_models.whitespace_layout_scorer.score import score_resume
import math

class WhiteSpaceScorer:
    def __init__(self, stats_csv_path=None, offset=40, w_mean=0.2, w_best=0.8):

        if stats_csv_path is None:
            stats_csv_path = os.getenv('LAYOUT_STATS_CSV') or os.path.join(os.path.dirname(__file__), 'output_stats.csv')
        
        self.stats_df = pd.read_csv(stats_csv_path)
        self.offset = offset
        self.w_mean = w_mean
        self.w_best = w_best

    def score(self, pdf_bytes):
        """
        Scores a single PDF resume from its byte content.
        Returns:tuple: (score (float), features (dict))
        """
        features = extract_features_for_pdf(pdf_bytes)
        score = score_resume(features, self.stats_df, w_mean=self.w_mean, w_best=self.w_best, offset=self.offset)
        return math.floor(score), features

    def print_features(self, features):
        """
        Utility to print the extracted features nicely.
        """
        for k in FEATURE_NAMES:
            print(f"{k}: {features[k]}")