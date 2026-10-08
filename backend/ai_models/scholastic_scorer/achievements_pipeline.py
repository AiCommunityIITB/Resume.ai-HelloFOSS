import os
import re
import json
import logging
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor
import time

class AchievementsPipeline:
    class PipelineError(Exception): pass
    class MissingColumnError(PipelineError): pass
    class EmptyInputError(PipelineError): pass
    class LLMError(PipelineError): pass

    class GeminiLLMClient:
        def __init__(self, api_key: Optional[str] = None, raise_on_missing=True):
            self.api_key = api_key or os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                if raise_on_missing:
                    raise AchievementsPipeline.LLMError("Missing Google Gemini API key.")
                else:
                    return
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-2.5-pro")

        def complete(self, system_prompt: str, user_content: str, temperature=0.0) -> str:
            try:
                rsp = self.model.generate_content([system_prompt, user_content])
                return rsp.text
            except Exception as e:
                logging.error(f"Gemini API error: {e}")
                raise AchievementsPipeline.LLMError(f"Gemini API error: {e}")

    def __init__(self, csv_path: str, column: str = "Achievements & Awards", 
                 st_model: str = "all-mpnet-base-v2", max_workers: int = 10,
                 api_key: Optional[str] = None):
        load_dotenv()
        logging.basicConfig(
            level=logging.INFO, 
            format="%(asctime)s — %(levelname)s — %(message)s"
        )
        self.logger = logging.getLogger(__name__)
        self.csv_path = csv_path
        self.column = column
        self.st_model = st_model
        self.max_workers = max_workers
        self.api_key = api_key

    # --------------------
    # CSV Loading
    # --------------------
    def load_achievements_column(self) -> List[str]:
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(self.csv_path)
        df = pd.read_csv(self.csv_path, dtype=str)
        if self.column not in df.columns:
            raise self.MissingColumnError(f"Column '{self.column}' missing")
        entries = df[self.column].fillna("").astype(str).tolist()
        self.logger.info("Loaded %d entries.", len(entries))
        return entries

    # --------------------
    # Preprocessing
    # --------------------
    def preprocess_entries(self, entries: List[str]) -> List[str]:
        cleaned = []
        for ent in entries:
            t = str(ent or "").strip().lower()
            t = re.sub(r"\s+", " ", t)
            if t in {"", "nan", "none", "-", "n/a"}: continue
            cleaned.append(t)
        if not cleaned:
            raise self.EmptyInputError("No entries after cleaning.")
        self.logger.info("%d valid preprocessed entries.", len(cleaned))
        return cleaned

    # --------------------
    # Vectorization
    # --------------------
    def load_sentence_transformer(self):
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(self.st_model)

    def vectorize_texts(self, model, texts: List[str], batch_size: int = 32) -> np.ndarray:
        return model.encode(texts, batch_size=batch_size, show_progress_bar=True, convert_to_numpy=True)

    # --------------------
    # Prompt
    # --------------------
    def build_system_prompt(self) -> str:
        return (
                    """
You are an Achievements & Awards Data Extraction Assistant.
You analyze a single text entry from the “Achievements & Awards” column of a resume, extract relevant awards/achievements, and map them to a predefined set of 50–200 canonical achievement types.

Controlled Vocabulary Requirement
- Maintain a master list of canonical achievement types (e.g., “JEE Advanced Rank 1–10”, “National Science Olympiad Medal”, “KVPY Fellowship”, “NTSE Scholarship”, “International Mathematics Olympiad Medal”, “Hackathon Winner”, etc.).
- All extracted text must be normalized to one of these canonical types.
- If a new achievement does not fit any existing category, map it to the closest applicable canonical type (e.g., “Inter-School Debate Winner” → “Debate Competition Winner”).
- Ignore micro-level variations (e.g., “2nd Place”, “Silver Medal”) if the main category is already covered in the canonical set.

Processing & Normalization Rules
1. Match & Map
   - Extract raw achievements from the input.
   - Match each achievement to the closest category from the canonical set using keyword and concept similarity.
   - Output only the mapped canonical name, never the raw phrase.

2. Merge Duplicates
   - If multiple entries map to the same canonical type, include it only once in the output JSON.

3. Ignore Noise
   - Ignore internal awards or non-standard items unless they fit a canonical type.
   - Drop overly specific, one-off events (e.g., “Annual Department Sports Day” → ignore).

4. Maintain Key Format
   - All keys are Title Case.
   - All values are empty strings.
   - Only include keys from the canonical set.

Output Specification
- Flat JSON object with only canonical keys present.
- Example:

{
  "JEE Advanced Rank 201–500": "",
  "INPhO Stage II": "",
  "International Mathematics Olympiad Medal": ""
}

Example Reduction
Input:
JEE Advanced Rank 245, INPhO Stage II Gold Medal, IMO Bronze Medal, Paint Fiesta Winner, Inter-School Drama 2nd Place

Output:
{
  "JEE Advanced Rank 201–500": "",
  "INPhO Stage II": "",
  "International Mathematics Olympiad Medal": "",
  "Art & Design Competition Winner": "",
  "Drama Competition Winner": ""
}

"""
        )

    def build_single_achievement_payload(self, text: str) -> str:
        return f"Analyze this achievement entry: {text}"

    # --------------------
    # Output Parsing
    # --------------------
    def extract_json_from_text(self, text: str) -> Dict[str, str]:
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                self.logger.warning(f"No JSON found in LLM output: {text[:100]}...")
                return {}
            parsed = json.loads(match.group(0))
            return {k: "" for k in parsed.keys()}
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON decode error: {e}, text: {text[:100]}...")
            return {}
        except Exception as e:
            self.logger.warning(f"Error extracting JSON: {e}")
            return {}

    # --------------------
    # Processing
    # --------------------
    def process_single_entry(self, entry: str, llm_client: GeminiLLMClient, system_prompt: str) -> Dict[str, str]:
        try:
            user_content = self.build_single_achievement_payload(entry)
            llm_text = llm_client.complete(system_prompt, user_content)
            result = self.extract_json_from_text(llm_text)
            return result
        except Exception as e:
            self.logger.error(f"Error processing entry '{entry[:50]}...': {e}")
            return {}

    def run_concurrent_processing(self, entries: List[str], llm_client: GeminiLLMClient, 
                                  system_prompt: str) -> Dict[str, str]:
        final_result = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_entry = {
                executor.submit(self.process_single_entry, entry, llm_client, system_prompt): entry
                for entry in entries
            }
            completed = 0
            total = len(entries)
            for future in future_to_entry:
                try:
                    result = future.result(timeout=30)
                    for key in result:
                        final_result[key] = ""
                    completed += 1
                    if completed % 10 == 0:
                        self.logger.info(f"Processed {completed}/{total} entries...")
                except Exception as e:
                    entry = future_to_entry[future]
                    self.logger.error(f"Failed to process entry '{entry[:50]}...': {e}")
                    completed += 1
        return final_result

    # --------------------
    # Main Run
    # --------------------
    def run(self) -> Dict[str, str]:
        start_time = time.time()
        
        raw = self.load_achievements_column()
        cleaned = self.preprocess_entries(raw)
        
        st = self.load_sentence_transformer()
        _ = self.vectorize_texts(st, cleaned)
        
        system_prompt = self.build_system_prompt()
        llm_client = self.GeminiLLMClient(api_key=self.api_key)
        
        self.logger.info(f"Processing {len(cleaned)} entries with {self.max_workers} concurrent workers...")
        final_result = self.run_concurrent_processing(cleaned, llm_client, system_prompt)
        
        end_time = time.time()
        processing_time = end_time - start_time
        self.logger.info(f"Total unique achievements extracted: {len(final_result)}")
        self.logger.info(f"Total processing time: {processing_time:.2f} seconds")
        self.logger.info(f"Average time per entry: {processing_time/len(cleaned):.2f} seconds")
        return final_result


# =====================
# Example Usage
# =====================
