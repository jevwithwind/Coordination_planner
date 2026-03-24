import json
import os
from datetime import datetime
from typing import Dict, List, Any

def load_preferences(username: str) -> Dict[str, Any]:
    """
    Load user preferences from file.
    
    Args:
        username: The username whose preferences to load
        
    Returns:
        Dictionary containing user preferences
    """
    pref_path = f"../users/{username}/preferences.json"
    
    if not os.path.exists(pref_path):
        # Create default preferences
        default_prefs = {
            "item_scores": {},  # Maps filename to scenario feature scores
            "decisions_since_last_decay": 0
        }
        save_preferences(username, default_prefs)
        return default_prefs
    
    with open(pref_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_preferences(username: str, preferences: Dict[str, Any]):
    """
    Save user preferences to file.
    
    Args:
        username: The username whose preferences to save
        preferences: The preferences dictionary to save
    """
    pref_path = f"../users/{username}/preferences.json"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(pref_path), exist_ok=True)
    
    with open(pref_path, 'w', encoding='utf-8') as f:
        json.dump(preferences, f, indent=2, ensure_ascii=False)


def get_item_score(username: str, filename: str, scenario_features: List[str]) -> float:
    """
    Get the preference score for an item given scenario features.
    
    Args:
        username: The user
        filename: The item filename
        scenario_features: List of scenario features (e.g., ["golf", "winter", "athletic"])
        
    Returns:
        Combined preference score (defaults to 1.0)
    """
    preferences = load_preferences(username)
    item_scores = preferences.get("item_scores", {})
    
    if filename not in item_scores:
        return 1.0
    
    # Calculate combined score based on matching scenario features
    total_score = 0.0
    feature_count = 0
    
    for feature in scenario_features:
        if feature in item_scores[filename]:
            total_score += item_scores[filename][feature]
            feature_count += 1
    
    if feature_count == 0:
        return 1.0
    
    # Return average score for matching features
    avg_score = total_score / feature_count
    # Clamp between 0.5 and 2.0
    return max(0.5, min(2.0, avg_score))


def record_decision(username: str, chosen_items: List[str], scenario_features: List[str]):
    """
    Record a decision to update item preferences.
    
    Args:
        username: The user
        chosen_items: List of filenames that were chosen in the outfit
        scenario_features: List of scenario features (e.g., ["golf", "winter", "athletic"])
    """
    preferences = load_preferences(username)
    item_scores = preferences.get("item_scores", {})
    
    for filename in chosen_items:
        if filename not in item_scores:
            item_scores[filename] = {}
        
        for feature in scenario_features:
            # Get current score for this feature, default to 1.0
            current_score = item_scores[filename].get(feature, 1.0)
            
            # Apply diminishing returns formula
            effective_increment = 0.08 * (1.0 / (1.0 + abs(current_score - 1.0)))
            new_score = current_score + effective_increment
            
            # Clamp between 0.5 and 2.0
            new_score = max(0.5, min(2.0, new_score))
            
            item_scores[filename][feature] = new_score
    
    preferences["item_scores"] = item_scores
    preferences["decisions_since_last_decay"] = preferences.get("decisions_since_last_decay", 0) + 1
    
    # Apply decay every 30 decisions
    if preferences["decisions_since_last_decay"] >= 30:
        apply_decay(username, preferences)
    
    save_preferences(username, preferences)


def apply_decay(username: str, preferences: Dict[str, Any] = None):
    """
    Apply global decay to all scores, bringing them closer to 1.0.
    
    Args:
        username: The user
        preferences: Optional preferences dict to update (will load if not provided)
    """
    if preferences is None:
        preferences = load_preferences(username)
    
    item_scores = preferences.get("item_scores", {})
    
    for filename in item_scores:
        for feature in item_scores[filename]:
            current_score = item_scores[filename][feature]
            # Apply decay: bring score 5% closer to 1.0
            new_score = 1.0 + (current_score - 1.0) * 0.95
            item_scores[filename][feature] = new_score
    
    preferences["item_scores"] = item_scores
    preferences["decisions_since_last_decay"] = 0
    
    save_preferences(username, preferences)


def enrich_wardrobe_with_preferences(wardrobe: Dict[str, Any], username: str, scenario_features: List[str]) -> Dict[str, Any]:
    """
    Add preference scores to wardrobe items.
    
    Args:
        wardrobe: The wardrobe dictionary
        username: The user
        scenario_features: List of scenario features to calculate preference for
        
    Returns:
        Enriched wardrobe with preference scores
    """
    enriched = {}
    
    for filename, item in wardrobe.items():
        # Create a copy of the item
        enriched_item = item.copy()
        
        # Calculate preference score based on matching scenario features
        preference_score = get_item_score(username, filename, scenario_features)
        enriched_item["preference_score"] = preference_score
        
        enriched[filename] = enriched_item
    
    return enriched