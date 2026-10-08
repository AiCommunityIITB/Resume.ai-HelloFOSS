import pandas as pd
import os

def remove_columns_from_reclassified(category, columns_to_remove=None):
    file_path = f'reclassified_data/{category}_reclassified.csv'
    
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist")
        return
    
    df = pd.read_csv(file_path)
    
    if columns_to_remove is None:
        # Auto-remove skills used in >= 11 or <= 2 projects
        skill_columns = df.columns[2:]  # Skip Title and Description
        skill_counts = df[skill_columns].sum()
        columns_to_remove = skill_counts[(skill_counts >= 60) | (skill_counts <= 1)].index.tolist()
        print(f"Auto-removing {len(columns_to_remove)} skills (used in >= 11 or <= 2 projects)")
    
    # Check which columns exist in the dataframe
    existing_columns = [col for col in columns_to_remove if col in df.columns]
    missing_columns = [col for col in columns_to_remove if col not in df.columns]
    
    if missing_columns:
        print(f"Warning: The following columns were not found: {missing_columns}")
    
    if existing_columns:
        df = df.drop(columns=existing_columns)
        df.to_csv(file_path, index=False)
        print(f"Removed {len(existing_columns)} columns from {category}_reclassified.csv")
        print(f"Removed columns: {existing_columns}")
    else:
        print("No valid columns to remove")
    
    return df


remove_columns_from_reclassified('AI Developer')
