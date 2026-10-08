import json
import re
from difflib import SequenceMatcher

class AchievementClassifier:
    def __init__(self, file='extracted_achievements.json'):
        self.canonical_achievements = []
        with open(file, 'r') as f:
            achievements_dict = json.load(f)
            self.canonical_achievements = list(achievements_dict.keys())
    
    def _preprocess_text(self, text):
        if not text:
            return ""
        
        text = str(text).strip().lower()
        
        # Remove common noise words
        noise_words = ['achieved', 'received', 'awarded', 'got', 'obtained', 'secured']
        for word in noise_words:
            text = text.replace(word, '')
        
        # Clean punctuation and extra whitespace
        text = re.sub(r'[^\w\s]', ' ', text)
        return ' '.join(text.split())
    
    def _extract_keywords(self, text):
        clean_text = self._preprocess_text(text)
        
        patterns = {
            'jee_advanced': r'jee\s*adv',
            'jee_main': r'jee\s*main',
            'rank': r'rank\s*(\d+)',
            'percentile': r'(\d+\.?\d*)\s*percentile',
            'olympiad': r'olympiad|imo|inmo|inpho|incho|inao',
            'kvpy': r'kvpy',
            'ntse': r'ntse',
            'scholarship': r'scholarship',
            'competition': r'competition',
            'national': r'national',
            'state': r'state',
            'international': r'international'
        }
        
        keywords = []
        for key, pattern in patterns.items():
            if re.search(pattern, clean_text):
                keywords.append(key)
        
        return keywords, clean_text
    
    def _rank_matches_category(self, rank, canonical):
        canonical_lower = canonical.lower()
        
        ranges = [
            (r'1[–-]10', 1, 10),
            (r'11[–-]50', 11, 50),
            (r'51[–-]100', 51, 100),
            (r'101[–-]500', 101, 500),
            (r'201[–-]500', 201, 500),
            (r'501[–-]1000', 501, 1000),
            (r'1001[–-]5000', 1001, 5000),
            (r'1001[–-]2000', 1001, 2000),
            (r'2001[–-]5000', 2001, 5000),
        ]
        
        for pattern, min_rank, max_rank in ranges:
            if re.search(pattern, canonical_lower):
                return min_rank <= rank <= max_rank
        
        return False
    
    def _combine_achievement_text(self, achievement_dict):
        if isinstance(achievement_dict, str):
            return achievement_dict
        
        if not isinstance(achievement_dict, dict):
            return str(achievement_dict)
        
        title = achievement_dict.get('title', '')
        description = achievement_dict.get('description', '')
        
        combined_text = title
        if description:
            combined_text += f" - {description}"
        
        return combined_text.strip()
    
    def classify(self, achievement, threshold=0.3):
        # Handle both string and dictionary inputs
        text = self._combine_achievement_text(achievement)
        
        if not text or not text.strip():
            return None, 0.0
        
        keywords, clean_text = self._extract_keywords(text)
        best_match = None
        best_score = 0.0
        
        for canonical in self.canonical_achievements:
            canonical_clean = self._preprocess_text(canonical)
            
            # Base similarity score
            score = SequenceMatcher(None, clean_text, canonical_clean).ratio()
            
            # Boost score for keyword matches
            canonical_keywords, _ = self._extract_keywords(canonical)
            keyword_overlap = len(set(keywords) & set(canonical_keywords))
            if keyword_overlap > 0:
                score += 0.2 * keyword_overlap
            
            # Special handling for JEE ranks
            if 'jee' in clean_text and 'jee' in canonical_clean:
                rank_match = re.search(r'rank\s*(\d+)', clean_text)
                if rank_match and self._rank_matches_category(int(rank_match.group(1)), canonical):
                    score += 0.3
            
            if score > best_score:
                best_score = score
                best_match = canonical
        
        if best_score >= threshold:
            return best_match, best_score
        else:
            return "Unknown Achievement", best_score
    
    def classify_batch(self, achievements, threshold=0.3):
        """Classify multiple achievements (strings or dictionaries)"""
        return [self.classify(achievement, threshold) for achievement in achievements]
    
    def get_similar(self, achievement, k=5):
        """Get top k most similar canonical achievements"""
        text = self._combine_achievement_text(achievement)
        
        if not text or not text.strip():
            return []
        
        keywords, clean_text = self._extract_keywords(text)
        scores = []
        
        for canonical in self.canonical_achievements:
            canonical_clean = self._preprocess_text(canonical)
            score = SequenceMatcher(None, clean_text, canonical_clean).ratio()
            
            # Boost for keyword matches
            canonical_keywords, _ = self._extract_keywords(canonical)
            keyword_overlap = len(set(keywords) & set(canonical_keywords))
            if keyword_overlap > 0:
                score += 0.2 * keyword_overlap
            
            scores.append((canonical, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]
    
    def get_classified_achievements(self, achievement_list, threshold=0.3):
        """
        Returns a simple list of all classified achievements
        
        Args:
            achievement_list: List of achievement dictionaries
            threshold: Minimum confidence threshold
            
        Returns:
            List of classified achievement names (strings)
        """
        if not isinstance(achievement_list, list):
            raise ValueError("Input must be a list of achievement dictionaries")
        
        classified_achievements = []
        
        for achievement in achievement_list:
            try:
                predicted, confidence = self.classify(achievement, threshold)
                
                # Only include if classified (above threshold)
                if confidence >= threshold:
                    classified_achievements.append(predicted)
                    
            except Exception:
                # Skip achievements that cause errors
                continue
        
        return classified_achievements


# Simple API wrapper
class AchievementAPI:    
    def __init__(self, canonical_file='extracted_achievements_with_scores.json'):
        """
        canonical_file: path to a JSON dict like:
            {
                "KVPY Fellowship": "90",
                "JEE Advanced Rank 201-500": "50",
                ...
            }
        """
        self.classifier = AchievementClassifier(canonical_file)
        
        # Load scores mapping (your JSON format is already dict)
        with open(canonical_file, 'r') as f:
            score_data = json.load(f)

        if isinstance(score_data, dict):
            # Use as is, convert empty strings to "Not Available"
            self.scores = {k: (v if v != "" else "Not Available") for k, v in score_data.items()}
        else:
            raise ValueError("Scores file must be a JSON object with achievement: score pairs")

    def classify_multiple(self, achievements, threshold=0.3):
        """
        Returns a list of dicts: original achievement data
        + predicted_class + score.
        """
        batch_results = self.classifier.classify_batch(achievements, threshold)
        output = []

        for achievement, (predicted, confidence) in zip(achievements, batch_results):
            enriched = dict(achievement)  # Copy the original input dict
            enriched["predicted_class"] = predicted
            enriched["score"] = self.scores.get(predicted, "Not Available")
            output.append(enriched)

        return output
