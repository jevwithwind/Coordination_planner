import json
import os
import re
from datetime import datetime
from collections import defaultdict
from openai import OpenAI
from .config import CHAT_API_KEY, QWEN_BASE_URL, QWEN_MODEL


def get_season_from_temp_or_date(user_message):
    """Extract temperature from user message or use current date to determine season."""
    # Look for temperature patterns in the message
    temp_match = re.search(r'(\d+)\s*°?[CF]', user_message, re.IGNORECASE)
    if temp_match:
        temp = int(temp_match.group(1))
        if temp < 10:
            return ['winter']
        elif 10 <= temp <= 20:
            return ['fall', 'spring']  # Could be either
        else:
            return ['summer']
    
    # Fallback to current month
    current_month = datetime.now().month
    if current_month in [12, 1, 2]:  # Dec, Jan, Feb
        return ['winter']
    elif current_month in [3, 4, 5]:  # Mar, Apr, May
        return ['spring']
    elif current_month in [6, 7, 8]:  # Jun, Jul, Aug
        return ['summer']
    else:  # Sep, Oct, Nov
        return ['fall']


def get_formality_keywords(user_message):
    """Parse user message for formality keywords and return appropriate formality levels."""
    user_msg_lower = user_message.lower()
    
    # Business/formal keywords
    if any(keyword in user_msg_lower for keyword in ["office", "meeting", "work", "interview", "business", "conference"]):
        return ["business", "formal", "smart_casual"]
    
    # Athletic/casual keywords
    elif any(keyword in user_msg_lower for keyword in ["golf", "hiking", "gym", "running", "workout", "sports"]):
        return ["athletic", "casual"]
    
    # Social/formal events
    elif any(keyword in user_msg_lower for keyword in ["date", "dinner", "party", "wedding", "event"]):
        return ["smart_casual", "formal", "business"]
    
    # Casual activities
    elif any(keyword in user_msg_lower for keyword in ["casual", "hangout", "weekend", "errand", "shopping"]):
        return ["casual", "smart_casual"]
    
    # No specific keywords found, return None to not filter by formality
    else:
        return None


def get_recommendations(user_message: str, wardrobe_path: str) -> dict:
    """Get outfit recommendations based on user message and wardrobe."""
    # Load wardrobe data
    if not os.path.exists(wardrobe_path):
        return {
            "outfits": [],
            "styling_tips": "No wardrobe data found. Please catalog your clothes first."
        }
    
    with open(wardrobe_path, 'r', encoding='utf-8') as f:
        wardrobe = json.load(f)
    
    # Determine season from user message or current date
    seasons = get_season_from_temp_or_date(user_message)
    
    # Get formality keywords from user message
    formality_levels = get_formality_keywords(user_message)
    
    # Multi-step filtering: season first, then formality
    filtered_wardrobe = {}
    for filename, item in wardrobe.items():
        # Season filter
        season_match = False
        if isinstance(item.get('season'), list):
            # Check if any of the item's seasons match the target seasons
            if any(season in item['season'] for season in seasons):
                season_match = True
        elif isinstance(item.get('season'), str):
            # Handle case where season is a single string
            if item['season'] in seasons:
                season_match = True
        
        if not season_match:
            continue
            
        # Formality filter (only if keywords were found)
        if formality_levels is not None:
            if item.get('formality') in formality_levels:
                filtered_wardrobe[filename] = item
        else:
            # If no formality keywords, include all items that passed season filter
            filtered_wardrobe[filename] = item
    
    # If we still have more than 60 items, truncate to 60 with balanced categories
    if len(filtered_wardrobe) > 60:
        # Group items by category
        items_by_category = defaultdict(list)
        for filename, item in filtered_wardrobe.items():
            category = item.get('category', 'other')
            items_by_category[category].append((filename, item))
        
        # Take a proportional sample from each category
        sampled_wardrobe = {}
        remaining_slots = 60
        categories = list(items_by_category.keys())
        
        # Distribute slots among categories
        for i, category in enumerate(categories):
            if i == len(categories) - 1:  # Last category gets remaining slots
                slots_for_category = remaining_slots
            else:
                # Allocate proportionally
                category_size = len(items_by_category[category])
                total_remaining_items = sum(len(items_by_category[c]) for c in categories[i:])
                slots_for_category = max(1, int((category_size / total_remaining_items) * remaining_slots))
            
            # Take items from this category
            selected_items = items_by_category[category][:slots_for_category]
            for filename, item in selected_items:
                sampled_wardrobe[filename] = item
            
            remaining_slots -= len(selected_items)
            if remaining_slots <= 0:
                break
        
        filtered_wardrobe = sampled_wardrobe
    
    # Create compact version of the wardrobe for the prompt
    compact_wardrobe = {}
    for filename, item in filtered_wardrobe.items():
        compact_wardrobe[filename] = {
            "file": filename,
            "cat": item.get("category", ""),
            "sub": item.get("subcategory", ""),
            "color": item.get("color", ""),
            "material": item.get("material", ""),
            "thick": item.get("thickness", ""),
            "desc": item.get("description", "")
        }
    
    # Create OpenAI client with Qwen configuration
    client = OpenAI(
        api_key=CHAT_API_KEY,
        base_url=QWEN_BASE_URL
    )
    
    # Prepare system prompt
    system_prompt = (
        "You are a personal styling assistant. Given the user's situation and their available wardrobe items (provided as JSON), "
        "recommend one or more complete outfits. Respond ONLY with a JSON object (no markdown, no backticks) with this structure: "
        "{ \"outfits\": [ { \"name\": \"Outfit name\", \"reasoning\": \"Why this works for the situation\", "
        "\"items\": [\"filename1.jpg\", \"filename2.jpg\", ...] } ], \"styling_tips\": \"Any extra advice\" }. "
        "Only use filenames that exist in the provided wardrobe. Recommend 1-3 outfits."
    )
    
    # Prepare user message with compact filtered wardrobe
    user_prompt = f"User request: {user_message}\n\nAvailable wardrobe items: {json.dumps(compact_wardrobe, indent=2)}"
    
    try:
        # Call the Qwen API
        response = client.chat.completions.create(
            model=QWEN_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Extract content from response
        content = response.choices[0].message.content
        
        # Remove any thinking blocks wrapped in <thinking> tags
        content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL).strip()
        
        # Attempt to parse the JSON response
        try:
            result = json.loads(content)
            return result
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the content
            # Look for JSON between curly braces
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(0)
                return json.loads(json_content)
            else:
                # If we still can't parse, return an error response
                return {
                    "outfits": [],
                    "styling_tips": "Sorry, I couldn't generate recommendations at this time."
                }
                
    except Exception as e:
        print(f"Error getting recommendations: {str(e)}")
        return {
            "outfits": [],
            "styling_tips": "Sorry, I encountered an error while generating recommendations."
        }