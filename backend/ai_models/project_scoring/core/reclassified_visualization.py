import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def visualize_reclassified_data(category):
    df = pd.read_csv(f'reclassified_data/{category}_reclassified.csv')
    
    # Extract skill columns (all columns except Title and Description)
    skill_columns = df.columns[2:]
    
    # Convert skill columns to numeric
    for col in skill_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Calculate skill frequency
    skill_counts = df[skill_columns].sum().sort_values(ascending=False)
    
    # Create visualizations in separate windows
    
    # 1. All skills usage (bar chart)
    plt.figure(figsize=(12, 8))
    plt.barh(range(len(skill_counts)), skill_counts.values)
    plt.yticks(range(len(skill_counts)), skill_counts.index, fontsize=6)
    plt.xlabel('Number of Projects')
    plt.title(f'{category} - All Skills Usage')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(f'reclassified_data/{category}_skills_usage.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 2. Skill usage distribution
    plt.figure(figsize=(10, 6))
    plt.hist(skill_counts.values, bins=30, edgecolor='black', alpha=0.7)
    plt.xlabel('Number of Projects Using Skill')
    plt.ylabel('Number of Skills')
    plt.title(f'{category} - Distribution of Skill Usage')
    plt.tight_layout()
    plt.savefig(f'reclassified_data/{category}_skill_distribution.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 3. Skills per project distribution
    skills_per_project = df[skill_columns].sum(axis=1)
    plt.figure(figsize=(10, 6))
    plt.hist(skills_per_project, bins=30, edgecolor='black', alpha=0.7)
    plt.xlabel('Number of Skills per Project')
    plt.ylabel('Number of Projects')
    plt.title(f'{category} - Skills per Project Distribution')
    plt.tight_layout()
    plt.savefig(f'reclassified_data/{category}_skills_per_project.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # 4. Heatmap of skills correlation
    plt.figure(figsize=(12, 10))
    if len(skill_columns) <= 50:
        corr_matrix = df[skill_columns].corr()
        im = plt.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
        plt.xticks(range(len(skill_columns)), skill_columns, rotation=90, ha='right', fontsize=6)
        plt.yticks(range(len(skill_columns)), skill_columns, fontsize=6)
        plt.title(f'{category} - All Skills Correlation Heatmap')
        plt.colorbar(im, shrink=0.8)
    else:
        # For large number of skills, show top correlations
        top_50_skills = skill_counts.head(50).index
        corr_matrix = df[top_50_skills].corr()
        im = plt.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
        plt.xticks(range(len(top_50_skills)), top_50_skills, rotation=90, ha='right', fontsize=6)
        plt.yticks(range(len(top_50_skills)), top_50_skills, fontsize=6)
        plt.title(f'{category} - Top 50 Skills Correlation Heatmap')
        plt.colorbar(im, shrink=0.8)
    plt.tight_layout()
    plt.savefig(f'reclassified_data/{category}_correlation_heatmap.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Print summary statistics
    print(f"\n{category} Analysis Summary:")
    print(f"Total projects: {len(df)}")
    print(f"Total skills analyzed: {len(skill_columns)}")
    print(f"Average skills per project: {skills_per_project.mean():.2f}")
    print(f"Most used skill: {skill_counts.index[0]} ({skill_counts.iloc[0]} projects)")
    print(f"Skills used in 0 projects: {(skill_counts == 0).sum()}")
    
    return df, skill_counts

visualize_reclassified_data('AI Developer')
