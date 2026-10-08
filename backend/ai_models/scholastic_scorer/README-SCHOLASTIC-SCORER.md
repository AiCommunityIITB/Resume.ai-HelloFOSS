# Achievement Classification and Scoring System

## Overview
This project provides a complete pipeline for extracting, classifying, and scoring academic and extracurricular achievements from resumes or structured data sources. It uses a Large Language Model (Google Gemini) to standardize raw achievement descriptions into a canonical set of predefined achievement types and assigns a configurable score to each.

The system is designed to:
- **Extract** achievements from a CSV file.
- **Map** extracted items to a controlled vocabulary of canonical achievements.
- **Classify** arbitrary descriptions against the canonical set.
- **Score** classified achievements based on a JSON-based scoring configuration.

The output is a structured format suitable for further processing, analysis, or integration into scoring/ranking systems.

---

## Features

1. **Extraction (AchievementsPipeline)**  
   - Reads a CSV file (e.g., resumes) and isolates the `Achievements & Awards` column.
   - Cleans and normalizes text entries.
   - Sends each entry to the Google Gemini API for classification into the canonical list.
   - Saves the canonical achievements in JSON format.

2. **Classification (AchievementClassifier & AchievementAPI)**  
   - Takes arbitrary achievement text/dictionaries and maps them to the closest matching canonical achievement.
   - Supports keyword-based boosts and rank-aware classification.
   - Batch classification support.

3. **Scoring**  
   - Reads a JSON file containing canonical achievements with their assigned scores (string or numeric).
   - Enriches classification results with the score configured for each predicted class.

4. **Flexible Input Format**  
   - Accepts:
     - Raw strings
     - Dictionaries containing `title`, `description`, etc.
   - Canonical achievements JSON can be:
     - Key-value pairs `{ "Achievement Name": "score" }`
     - Or a list of objects `[{ "type": "...", "score": ... }, ...]`

5. **Extensible**  
   - Scoring system and classification logic can be extended to fit different achievement taxonomies or rating models.

---
