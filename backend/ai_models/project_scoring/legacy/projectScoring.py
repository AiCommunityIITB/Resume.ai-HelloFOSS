import os
import argparse
from cerebras.cloud.sdk import Cerebras
from tabulate import tabulate
import re
import json
import pandas as pd

tech = set()

def get_project_score(client, prompt, title, description):
    full_prompt = f"{prompt}\n\nTitle: {title}\nDescription: {description}"
    
    response = client.chat.completions.create(
        model="qwen-3-235b-a22b",
        messages=[
            {"role": "user", "content": full_prompt}
        ],
        seed=42)

    response_text = response.choices[0].message.content.strip()
    response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
    scores, tech_used = response_text.split('[')
    scores = scores.strip().split(' ')
    tech_used = tech_used[:-1].split(', ')
    print(response_text)
    print('#' * 30)
    return (scores, tech_used)


def print_scores(title, scores):
    print(f"{'='*60}")
    print(f"Title: {title}")
    print(f"{'='*60}")
    
    table_data = []
    factors = ['Technical Complexity', 'Technology Stack Relevance', 'Innovation & Uniqueness', 'Project Scope & Completeness']
    for factor, score in zip(factors, scores):
        table_data.append([factor, score])
    
    headers = ["Factor", "Score"]
    print(tabulate(table_data, headers=headers, tablefmt="grid", maxcolwidths=[20, 8, 50]))

def score_project(title, description, prompt, category, display_output=True):
    global tech
    api_key = os.getenv('CEREBRAS_API_KEY')
    client = Cerebras(api_key=api_key)
    scores, tech_used = get_project_score(client, prompt, title, description)
    tech = tech.union(set(tech_used))

    if scores:        
        if display_output:
            print_scores(title, scores)
        return scores
        

def scoreCSV(csv_file, class_arg):
    global tech
    df = pd.read_csv(csv_file)
    results = []
    
    with open('prompts/promptV2.md', 'r', encoding='utf-8') as file:
        prompt = file.read()
    
    for _, row in df.iterrows():
        if row['classification'] == class_arg:
            project_json = json.loads(row['project'])
            title = project_json['title']
            description = project_json.get('description', '') or ''
            key_points = ' '.join(project_json.get('key_points', []))
            total_description = f"{description}\n{key_points}".strip()

            print(title)
            print(total_description)
            print('#' * 20)
            
            scores = score_project(title, total_description, prompt, class_arg, display_output=False)
            if scores:
                results.append([class_arg, title, total_description] + scores)
    
    results_df = pd.DataFrame(results, columns=['Domain', 'Title', 'Description', 'Technical Complexity', 'Technology Stack Relevance', 'Innovation & Uniqueness', 'Project Scope & Completeness'])
    results_df.to_csv(f'{class_arg}_scores.csv', index=False)

    with open(f'{class_arg}_technologies.txt', 'w', encoding='utf-8') as f:
        f.truncate(0)
        for technology in tech:
            f.write(f"{technology}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', type=str, required=True)
    args = parser.parse_args()
    
    scoreCSV("projects.csv", args.domain)




"""
AI Developer: 311 projects
IT-Software: 253 projects
Quantitative Finance: 108 projects
Design: 72 projects
Analytics: 70 projects
Strategy: 21 projects
Finance: 15 projects
Consult: 5 projects
"""
