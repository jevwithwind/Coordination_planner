import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Union

def log_decision(username: str, scenario: str, scenario_breakdown: Dict, outfits_presented: List[Dict], user_choice: Optional[int]):
    """
    Log a decision event to the user's decision log file.
    
    Args:
        username: The username whose decision is being logged
        scenario: The original user scenario text
        scenario_breakdown: The AI's interpretation of the scenario
        outfits_presented: The 3 outfits that were shown to the user
        user_choice: Index of chosen outfit (0, 1, 2) or None if "none of the above"
    """
    log_path = f"../users/{username}/decision_log.jsonl"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    # Prepare the log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "scenario": scenario,
        "scenario_breakdown": scenario_breakdown,
        "outfits_presented": outfits_presented,
        "user_choice": user_choice,
        "chosen_outfit_name": outfits_presented[user_choice]["name"] if user_choice is not None else None
    }
    
    # Append the log entry to the JSONL file
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')


def get_decision_count(username: str) -> int:
    """
    Get the number of decisions logged for a user.
    
    Args:
        username: The username to count decisions for
        
    Returns:
        Number of logged decisions
    """
    log_path = f"../users/{username}/decision_log.jsonl"
    
    if not os.path.exists(log_path):
        return 0
    
    count = 0
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():  # Count non-empty lines
                count += 1
    
    return count