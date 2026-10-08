import json
import sys
import torch
import pandas as pd
import os
from collections import Counter
from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification
)
from ai_models.classification.preprocess import preprocess_list
from ai_models.classification.tokenize_n_dataset import load_tokenizer

# Simple fallback preprocessing function in case the import fails
def simple_preprocess(text_list, remove_stops=True):
    """Simple fallback preprocessing function"""
    import re
    processed = []
    for text in text_list:
        if text is None:
            processed.append("")
            continue
        # Basic cleaning
        text = str(text).lower()
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        processed.append(text)
    return processed

class ProjectClassifier:
    """
    A class to load a trained DistilBERT model and classify projects.
    """
    
    def __init__(self, model_path="Resume.ai/backend/ai_models/classification/my_distilbert_model"):
        """
        Initialize the classifier by loading the trained model and tokenizer.
        
        Args:
            model_path (str): Path to the saved model directory
        """
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        try:
            # Load label mappings
            with open(os.path.join(model_path, 'label_mappings.json'), 'r') as f:
                self.label_mappings = json.load(f)
            
            self.id_to_label = {int(k): v for k, v in self.label_mappings['id_to_label'].items()}
            self.label_to_id = self.label_mappings['label_to_id']
            self.max_length = self.label_mappings['max_length']
            self.num_classes = self.label_mappings['num_classes']
            
            # Load tokenizer
            self.tokenizer = DistilBertTokenizer.from_pretrained(model_path)
            
            # Load model
            self.model = DistilBertForSequenceClassification.from_pretrained(model_path)
            self.model.to(self.device)
            self.model.eval()
            
            print(f"Model loaded successfully from {model_path}")
            print(f"Device: {self.device}")
            print(f"Number of classes: {self.num_classes}")
            print(f"Available classes: {list(self.label_to_id.keys())}")
            
        except Exception as e:
            raise Exception(f"Error loading model: {str(e)}")
    
    def _extract_text_from_project(self, project_dict):
        """
        Extract and combine text from a project dictionary.
        
        Args:
            project_dict (dict): Project dictionary from json.loads(row["project"])
            
        Returns:
            str: Combined text from the project
        """
        parts = []
        
        # Add title if available
        if project_dict.get("title"): 
            parts.append(project_dict["title"])
        
        # Add description if available
        if project_dict.get("description"): 
            parts.append(project_dict["description"])
        
        # Add key points if available
        parts += project_dict.get("key_points", [])
        
        # Add technologies used if available
        techs = project_dict.get("technologies_used", [])
        if techs: 
            parts.append("Technologies used: " + ", ".join(techs))
        
        # Combine all parts
        text = ' '.join([str(p) for p in parts if p])
        return text
    
    def predict_single(self, project_dict):
        """
        Predict the classification for a single project.
        
        Args:
            project_dict (dict): Project dictionary from json.loads(row["project"])
            
        Returns:
            dict: Prediction results including class, confidence, and probabilities
        """
        try:
            # Extract text from project
            text = self._extract_text_from_project(project_dict)
            
            if not text or not text.strip():
                return {
                    'error': 'No text found in project',
                    'predicted_class': None,
                    'confidence': None
                }
            
            # Debug: print extracted text
            print(f"DEBUG: Extracted text: {text[:200]}...")
            
            # Try preprocessing with error handling
            try:
                processed_text = preprocess_list([text], remove_stops=True)[0]
                if not processed_text or processed_text.strip() == "":
                    # Fallback: use original text if preprocessing fails
                    processed_text = text
                print(f"DEBUG: Processed text: {processed_text[:200]}...")
            except Exception as preprocess_error:
                print(f"DEBUG: Preprocessing failed: {preprocess_error}")
                try:
                    # Try simple fallback preprocessing
                    processed_text = simple_preprocess([text], remove_stops=True)[0]
                    print(f"DEBUG: Used fallback preprocessing")
                except Exception as fallback_error:
                    print(f"DEBUG: Fallback preprocessing also failed: {fallback_error}")
                    processed_text = text  # Use original text as final fallback
            
            # Ensure processed_text is not None or empty
            if not processed_text or not isinstance(processed_text, str):
                processed_text = text
            
            # Tokenize with error handling
            try:
                inputs = self.tokenizer(
                    str(processed_text),  # Ensure it's a string
                    truncation=True,
                    padding=True,
                    max_length=self.max_length,
                    return_tensors="pt"
                )
            except Exception as tokenize_error:
                return {
                    'error': f'Tokenization failed: {tokenize_error}',
                    'predicted_class': None,
                    'confidence': None
                }
            
            # Move to device
            input_ids = inputs["input_ids"].to(self.device)
            attention_mask = inputs["attention_mask"].to(self.device)
            
            # Make prediction
            with torch.no_grad():
                outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
                predicted_class_id = logits.argmax(dim=-1).item()
                confidence = probabilities[0][predicted_class_id].item()
            
            # Get all class probabilities
            all_probs = {}
            for i, prob in enumerate(probabilities[0]):
                class_name = self.id_to_label.get(i, f"Class_{i}")
                all_probs[class_name] = prob.item()
            
            predicted_class = self.id_to_label.get(predicted_class_id, f"Class_{predicted_class_id}")
            
            return {
                'predicted_class': predicted_class,
                'confidence': confidence,
                'predicted_class_id': predicted_class_id,
                'all_probabilities': all_probs,
                'input_text': text,
                'processed_text': processed_text
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"DEBUG: Full error traceback:\n{error_details}")
            return {
                'error': f"Error during prediction: {str(e)}",
                'predicted_class': None,
                'confidence': None,
                'error_details': error_details
            }
    
    def classify_project_list(self, project_list, aggregation_method='majority_vote', 
                            confidence_threshold=0.7, return_details=False, debug=True):
        """
        Classify a list of projects and return an overall classification.
        
        Args:
            project_list (list): List of project dictionaries from json.loads(row["project"])
            aggregation_method (str): Method to aggregate classifications
                - 'majority_vote': Most common classification
                - 'weighted_confidence': Weighted by confidence scores
                - 'highest_confidence': Classification with highest confidence
            confidence_threshold (float): Minimum confidence threshold (0.0 to 1.0)
            return_details (bool): Whether to return detailed results for each project
            debug (bool): Whether to print debug information
            
        Returns:
            dict: Overall classification results
        """
        if not project_list:
            return {
                'overall_classification': None,
                'confidence': 0.0,
                'error': 'Empty project list provided',
                'valid_predictions': 0
            }
        
        if debug:
            print(f"\n=== DEBUG: Starting classification of {len(project_list)} projects ===")
            print(f"Confidence threshold: {confidence_threshold}")
            print(f"Aggregation method: {aggregation_method}")
        
        # Get predictions for all projects
        individual_predictions = []
        valid_predictions = []
        all_confidences = []  # Track all confidences for debugging
        
        for i, project in enumerate(project_list):
            try:
                if debug:
                    print(f"\n--- Processing Project {i+1}: {project.get('title', 'No Title')} ---")
                
                prediction = self.predict_single(project)
                individual_predictions.append(prediction)
                
                if debug:
                    if 'error' not in prediction:
                        print(f"Predicted class: {prediction.get('predicted_class', 'None')}")
                        confidence = prediction.get('confidence')
                        if confidence is not None:
                            print(f"Confidence: {confidence:.4f}")
                        else:
                            print(f"Confidence: None")
                        print(f"Top 3 probabilities:")
                        all_probs = prediction.get('all_probabilities', {})
                        if all_probs:
                            sorted_probs = sorted(all_probs.items(), 
                                                key=lambda x: x[1], reverse=True)[:3]
                            for class_name, prob in sorted_probs:
                                print(f"  {class_name}: {prob:.4f}")
                        else:
                            print("  No probabilities available")
                    else:
                        print(f"ERROR in prediction: {prediction.get('error', 'Unknown error')}")
                        if 'error_details' in prediction:
                            print(f"Error details: {prediction['error_details']}")
                
                # Track all confidences regardless of threshold
                if prediction.get('confidence') is not None:
                    all_confidences.append(prediction['confidence'])
                
                # Only include predictions above confidence threshold
                if (prediction.get('predicted_class') and 
                    prediction.get('confidence') is not None and
                    prediction.get('confidence') >= confidence_threshold):
                    valid_predictions.append(prediction)
                    if debug:
                        print(f"✓ Prediction accepted (confidence >= {confidence_threshold})")
                else:
                    if debug:
                        conf = prediction.get('confidence')
                        if conf is not None:
                            print(f"✗ Prediction rejected (confidence {conf:.4f} < {confidence_threshold})")
                        else:
                            print(f"✗ Prediction rejected (confidence is None)")
                    
            except Exception as e:
                error_msg = f"Error processing project {i}: {str(e)}"
                if debug:
                    print(f"ERROR: {error_msg}")
                    import traceback
                    print(f"Full traceback: {traceback.format_exc()}")
                individual_predictions.append({
                    'error': error_msg,
                    'predicted_class': None,
                    'confidence': None
                })
        
        if debug:
            print(f"\n=== SUMMARY ===")
            print(f"Total projects processed: {len(project_list)}")
            print(f"Valid predictions (>= {confidence_threshold}): {len(valid_predictions)}")
            if all_confidences:
                print(f"Confidence statistics:")
                print(f"  Min: {min(all_confidences):.4f}")
                print(f"  Max: {max(all_confidences):.4f}")
                print(f"  Average: {sum(all_confidences)/len(all_confidences):.4f}")
                print(f"  Median: {sorted(all_confidences)[len(all_confidences)//2]:.4f}")
            
            # Show all predictions with their confidences
            print(f"\nAll predictions summary:")
            for i, pred in enumerate(individual_predictions):
                if 'error' not in pred and pred.get('predicted_class'):
                    status = "✓" if pred.get('confidence', 0) >= confidence_threshold else "✗"
                    print(f"  Project {i+1}: {pred['predicted_class']} ({pred.get('confidence', 0):.4f}) {status}")
        
        # If no valid predictions, consider lowering threshold or using all predictions
        if not valid_predictions:
            if debug:
                print(f"\nWARNING: No predictions above threshold {confidence_threshold}")
                if all_confidences:
                    suggested_threshold = max(0.1, min(all_confidences) * 0.9)
                    print(f"Consider lowering threshold to ~{suggested_threshold:.2f}")
            
            # Option 1: Return error as before
            result = {
                'overall_classification': None,
                'confidence': 0.0,
                'total_projects': len(project_list),
                'valid_predictions': 0,
                'error': f'No predictions above confidence threshold {confidence_threshold}',
                'confidence_stats': {
                    'min': min(all_confidences) if all_confidences else None,
                    'max': max(all_confidences) if all_confidences else None,
                    'average': sum(all_confidences)/len(all_confidences) if all_confidences else None,
                    'all_confidences': all_confidences
                } if debug else None
            }
            
            if return_details:
                result['individual_predictions'] = individual_predictions
            
            return result
        
        # Aggregate classifications based on method
        if aggregation_method == 'majority_vote':
            # Count occurrences of each class
            class_counts = Counter([pred['predicted_class'] for pred in valid_predictions])
            most_common_class = class_counts.most_common(1)[0][0]
            # Calculate average confidence for the most common class
            same_class_confidences = [pred['confidence'] for pred in valid_predictions 
                                    if pred['predicted_class'] == most_common_class]
            overall_confidence = sum(same_class_confidences) / len(same_class_confidences)
            overall_classification = most_common_class
            
        elif aggregation_method == 'weighted_confidence':
            # Weight each class by its confidence scores
            class_weighted_scores = {}
            for pred in valid_predictions:
                class_name = pred['predicted_class']
                confidence = pred['confidence']
                if class_name not in class_weighted_scores:
                    class_weighted_scores[class_name] = []
                class_weighted_scores[class_name].append(confidence)
            
            # Calculate weighted average for each class
            class_avg_scores = {}
            for class_name, confidences in class_weighted_scores.items():
                class_avg_scores[class_name] = sum(confidences) / len(confidences)
            
            # Get class with highest weighted score
            overall_classification = max(class_avg_scores, key=class_avg_scores.get)
            overall_confidence = class_avg_scores[overall_classification]
            
        elif aggregation_method == 'highest_confidence':
            # Select the prediction with highest confidence
            best_prediction = max(valid_predictions, key=lambda x: x['confidence'])
            overall_classification = best_prediction['predicted_class']
            overall_confidence = best_prediction['confidence']
        
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation_method}")
        
        # Calculate class distribution
        class_distribution = Counter([pred['predicted_class'] for pred in valid_predictions])
        class_distribution_percent = {
            class_name: (count / len(valid_predictions)) * 100 
            for class_name, count in class_distribution.items()
        }
        
        if debug:
            print(f"\n=== FINAL RESULT ===")
            print(f"Overall classification: {overall_classification}")
            print(f"Overall confidence: {overall_confidence:.4f}")
            print(f"Class distribution: {dict(class_distribution)}")
        
        result = {
            'overall_classification': overall_classification,
            'confidence': overall_confidence,
            'aggregation_method': aggregation_method,
            'total_projects': len(project_list),
            'valid_predictions': len(valid_predictions),
            'confidence_threshold': confidence_threshold,
            'class_distribution': dict(class_distribution),
            'class_distribution_percent': class_distribution_percent
        }
        
        if return_details:
            result['individual_predictions'] = individual_predictions
            
        if debug and all_confidences:
            result['debug_info'] = {
                'confidence_stats': {
                    'min': min(all_confidences),
                    'max': max(all_confidences),
                    'average': sum(all_confidences)/len(all_confidences),
                    'median': sorted(all_confidences)[len(all_confidences)//2]
                },
                'all_confidences': all_confidences
            }
        
        return result

    def classify_with_adaptive_threshold(self, project_list, aggregation_method='majority_vote', 
                                       min_threshold=0.3, return_details=False, debug=True):
        """
        Classify projects with adaptive confidence threshold.
        If no predictions meet the initial threshold, automatically lower it.
        
        Args:
            project_list (list): List of project dictionaries
            aggregation_method (str): Method to aggregate classifications
            min_threshold (float): Minimum acceptable confidence threshold
            return_details (bool): Whether to return detailed results
            debug (bool): Whether to print debug information
            
        Returns:
            dict: Classification results with adaptive threshold
        """
        # Try with standard threshold first
        result = self.classify_project_list(
            project_list, 
            aggregation_method=aggregation_method,
            confidence_threshold=0.7,
            return_details=return_details,
            debug=debug
        )
        
        # If no valid predictions, try with adaptive threshold
        if 'valid_predictions' in result and result['valid_predictions'] == 0 and 'debug_info' in result:
            all_confidences = result['debug_info']['all_confidences']
            if all_confidences:
                # Use 90% of the maximum confidence as new threshold, but not below min_threshold
                adaptive_threshold = max(min_threshold, max(all_confidences) * 0.9)
                
                if debug:
                    print(f"\n=== ADAPTIVE THRESHOLD ===")
                    print(f"Retrying with adaptive threshold: {adaptive_threshold:.3f}")
                
                result = self.classify_project_list(
                    project_list,
                    aggregation_method=aggregation_method,
                    confidence_threshold=adaptive_threshold,
                    return_details=return_details,
                    debug=debug
                )
                result['adaptive_threshold_used'] = adaptive_threshold
        
        return result


# Usage example with your project data:
