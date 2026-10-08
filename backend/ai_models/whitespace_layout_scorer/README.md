# Whitespace and Layout Scorer

Basically Scores the new resumes based on its distance from the mean and the Optimum resume features (weighted sum)

common.py - feature that which feature has optimal direction - higher is good or lower is good.


**How to Run** :
 - python3 compute_features.py resume_layout_features_500.csv output_stats.csv ::: This saves the mean and optimum(min/max) features into a csv

 - python3 score.py output_stat.py /path_to_new_resume/ ::: this prints out the score 0-100
  
  You can set the weights of W_mean and W_optim and also the offest


- main.py :::: for integration into backend
example :: 

 from main import score_pdf_resume

score, feats = score_pdf_resume('/absolute/path/to/new_resume.pdf')
print(f'Resume score: {score}')


 