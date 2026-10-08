from transformers import AutoTokenizer
from datasets import Dataset

def load_tokenizer(model_name="distilbert-base-uncased"):
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
    special_tokens = {"additional_special_tokens": ["<NUM>"]}
    tokenizer.add_special_tokens(special_tokens)
    
    return tokenizer

def tokenize_text(texts, labels, tokenizer, max_length=128):
    dataset = Dataset.from_dict({
        "texts": texts,
        "label": labels
    })

    def tokenize_fxn(ex):
        return tokenizer(
            ex["texts"],
            truncation=True,
            padding="max_length",
            max_length=max_length
        )

    tokenized_dataset = dataset.map(tokenize_fxn, batched=True)
    tokenized_dataset.set_format(
        type="torch",
        columns=["input_ids", "attention_mask", "label"]
    )
    
    return tokenized_dataset
