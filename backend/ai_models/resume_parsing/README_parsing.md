# Parsing Script - Project Evaluator

This script is designed to parse and evaluate technical project descriptions using a rubric-based system. It mimics the structure of a human evaluator to score projects across key dimensions such as complexity, technical depth, innovation, and authenticity.

---

## 🚀 Features

- Parses structured project input (title and description)
- Applies scoring across 6 evaluation categories
- Uses rules and keyword patterns to infer score
- Outputs evaluation in standardized dictionary format

---

## 🧾 Input Format

Each evaluation run expects the following input format:

```python
{
    "Project Title": "<title of the project>",
    "Project Description": "<detailed description of the project>"
}
```

---

## 🧮 Output Format

Returns a dictionary with scoring and justification for each category:

```python
{
    "Technical Complexity": ["Score (1-5)", "Brief explanation of score"],
    "Academic Level": ["Score (1-5)", "Brief explanation of score"],
    "Technology Stack": ["Score (1-5)", "Brief explanation of score"],
    "Project Scope": ["Score (1-5)", "Brief explanation of score"],
    "Innovation/Novelty": ["Score (1-5)", "Brief explanation of score"],
    "Authenticity": ["Score (1-5)", "Brief explanation of score"]
}
```

---

## 🛠 How to Use

```bash
python parsing.py
```

Make sure the project input dictionary is properly defined in the script or imported from a file.

---

## 📚 Dependencies

- `re` for regular expressions
- Standard Python 3 libraries (no external packages required)

---

## 📏 Evaluation Criteria Summary

This script uses heuristic rules inspired by human evaluation rubrics to assess:

1. **Technical Complexity**
2. **Academic Knowledge Level**
3. **Technology Stack Difficulty**
4. **Project Scope and Scale**
5. **Innovation and Novelty**
6. **Authenticity Indicators**

---

## 💡 Example Usage

```python
input_data = {
    "Project Title": "AI Resume Parser",
    "Project Description": "Built a resume parser using NLP with spaCy and custom regex rules..."
}

result = evaluate_project(input_data)
print(result)
```

---

## 🔍 Notes

This script is ideal for initial triage or review of multiple project submissions in academic or hiring contexts.
