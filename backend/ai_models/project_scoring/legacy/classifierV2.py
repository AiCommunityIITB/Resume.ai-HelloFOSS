"""
AI Developer - o
IT-Software - o
Quantitative Finance - o
Design - o
Analytics - o
Strategy - o
Finance - o
Consult - o
"""

import os
import pandas as pd
from cerebras.cloud.sdk import Cerebras
import re

def reclassify_projects(category, display_output=False, batch_size=10):
    with open('prompts/reclassificationPromptV2.md', 'r', encoding='utf-8') as file:
        base_prompt = file.read()
    
    with open(f'TechStack/{category}_technologies.txt', 'r', encoding='utf-8') as file:
        technologies = file.read().strip()
    
    tech_list = technologies.split('\n')
    df = pd.read_csv(f'scores/{category}_scores.csv')
    
    api_key = os.getenv('CEREBRAS_API_KEY')
    client = Cerebras(api_key=api_key)
    
    all_results = []
    
    # Process skills in batches or all at once if batch_size is 0
    if batch_size == 0:
        batch_size = len(tech_list)
    
    for i in range(0, len(tech_list), batch_size):
        batch_skills = tech_list[i:i+batch_size]
        limited_technologies = '\n'.join(batch_skills)
        
        prompt = base_prompt.replace("SKILLS LIST:", f"SKILLS LIST:\n{limited_technologies}")
        
        batch_results = []
        
        for _, row in df.iterrows():
            title = row['Title']
            description = row['Description']
            
            full_prompt = f"{prompt}\n\nTitle: {title}\nDescription: {description}"
            
            response = client.chat.completions.create(
                model="qwen-3-235b-a22b-instruct-2507",
                messages=[{"role": "user", "content": full_prompt}],
                seed=42
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse the response to get list of used skills
            used_skills = [skill.strip() for skill in response_text.split('\n') if skill.strip()]
            
            # Create binary scores list: 1 if skill is used, 0 if not
            scores = []
            for skill in batch_skills:
                if skill in used_skills:
                    scores.append('1')
                else:
                    scores.append('0')
            
            if display_output:
                print(f"Title: {title}")
                print(f"Description: {description}")
                print(f"Used skills: {', '.join(used_skills)}")
                print(f"Scores: {' '.join(scores)}")
                print()
            
            batch_results.append(scores)
        
        all_results.append(batch_results)
    
    # Combine all batch results
    final_results = []
    for proj_idx in range(len(df)):
        title = df.iloc[proj_idx]['Title']
        description = df.iloc[proj_idx]['Description']
        combined_scores = []
        
        for batch_idx in range(len(all_results)):
            combined_scores.extend(all_results[batch_idx][proj_idx])
        
        final_results.append([title, description] + combined_scores)
    
    columns = ['Title', 'Description'] + tech_list
    results_df = pd.DataFrame(final_results, columns=columns)
    
    os.makedirs('reclassified_data', exist_ok=True)
    results_df.to_csv(f'reclassified_data/{category}_reclassified.csv', index=False)


reclassify_projects('AI Developer', True, 0)
