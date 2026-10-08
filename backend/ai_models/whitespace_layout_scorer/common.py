# common.py
FEATURES = [
    ('whitespace_ratio_avg', False),
    ('section_whitespace_avg_0', False),
    ('section_whitespace_avg_1', False),
    ('section_whitespace_avg_2', False),
    ('section_whitespace_avg_3', False),
    ('bbox_h_spacing_avg', False),
    ('bbox_v_spacing_avg', False),
    ('char_density_avg', True),
    ('block_density_avg_0', True),
    ('block_density_avg_1', True),
    ('block_density_avg_2', True),
    ('block_density_avg_3', True),
    ('line_spacing_avg', False),
    ('section_sep_avg', False),
    ('margin_left_avg', False),
    ('margin_right_avg', False),
    ('margin_top_avg', False),
    ('margin_bottom_avg', False),
    ('padding_avg', False),
]
FEATURE_NAMES = [f for f, _ in FEATURES]
def higher_is_better(feature):
    return dict(FEATURES)[feature]
