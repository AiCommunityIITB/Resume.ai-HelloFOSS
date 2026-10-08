import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import string
import re

# Download required NLTK data
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('stopwords')

def normalize_whitespace(text):
    return re.sub(r'\s+', ' ', text).strip()

def lowercase(text):
    return text.lower()

def remove_punc(text):
    return ''.join([char for char in text if char not in string.punctuation])

def replace_numbers(text):
    """Replace numbers with <NUM> token instead of removing them"""
    return re.sub(r'\d+', '<NUM>', text)

def remove_stopwords(tokens):
    """Remove English stopwords from token list"""
    stop_words = set(stopwords.words('english'))
    return [token for token in tokens if token.lower() not in stop_words]

def tokenize(text):
    return word_tokenize(text)

def preprocess(text, remove_stops=True):
    """Enhanced preprocessing with optional stopwords removal"""
    text = normalize_whitespace(text)
    text = lowercase(text)
    text = remove_punc(text)
    text = replace_numbers(text)  # Now uses <NUM> token
    tokens = tokenize(text)
    
    if remove_stops:
        tokens = remove_stopwords(tokens)
    
    cleaned = ' '.join(tokens)
    if cleaned.strip() == "":
        print(f"Invalid input for {text}")
    return cleaned

def preprocess_list(sentences, remove_stops=True):
    """Process a list of sentences with optional stopwords removal"""
    return [preprocess(text, remove_stops) for text in sentences]
