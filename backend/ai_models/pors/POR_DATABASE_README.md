# POR Similarity Search System

This project allows storing and searching Positions of Responsibility (PORs) using sentence embeddings and cosine similarity. It includes two main scripts:
- `por_sql_storage.py`: Stores POR entries in a SQLite database.
- `topk_por_search.py`: Retrieves top-k most similar PORs from the database.

## Usage

1. Run `por_sql_storage.py` to save PORs to a local SQLite database.
2. Run `topk_por_search.py` to search for similar PORs by title and organization.

## Requirements

Install dependencies using:

pip install numpy pandas sentence-transformers

Requires Python 3.7+

## File Overview

- `por_sql_storage.py`: Reads and embeds POR entries, then stores them in a SQLite database.
- `topk_por_search.py`: Loads PORs from the database and finds the top-k most similar entries using cosine similarity.

## Project Structure

Edit the script variables (DB_PATH, TARGET_TITLE, TARGET_ORG, etc.) as needed.