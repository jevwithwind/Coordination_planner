import os
import json
import base64
import time
from PIL import Image
from pillow_heif import register_heif_opener
from anthropic import Anthropic
import dotenv

# Register HEIF opener to support HEIC files
register_heif_opener()

"""
Category Definitions:
- outerwear: anything worn as the outermost layer — coats, jackets, puffer jackets, parkas, blazers worn as outerwear, raincoats
- layered_wear: mid-layers worn over inner_wear but under outerwear — cardigans, sweaters, hoodies, fleece pullovers, vests
- inner_wear: items worn directly on the upper body or as the base layer — t-shirts, dress shirts, polo shirts, tank tops, blouses, turtlenecks
- bottoms: everything below the waist — jeans, chinos, dress pants, shorts, skirts, joggers
- shoes: all footwear
- accessories: scarves, belts, hats, bags, watches, ties, gloves
"""

def get_supported_extensions():
    """Return the set of supported image extensions."""
    return ('.jpg', '.jpeg', '.png', '.webp', '.heic', '.HEIC')

def scan_image_files(folder_path):
    """Scan the folder and return a list of image filenames."""
    if not os.path.exists(folder_path):
        print(f"Directory {folder_path} does not exist.")
        return []
    
    supported_formats = get_supported_extensions()
    image_files = []
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(supported_formats):
            image_files.append(filename)
    
    return image_files

def process_single_image(image_path):
    """Process a single image file with Anthropic API and return the parsed result."""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    client = Anthropic(api_key=api_key)
    
    # Encode image to base64
    base64_string = encode_image_to_base64(image_path)
    
    # Define the system prompt
    system_prompt = (
        "You are a clothing analysis assistant. For the given clothing image, "
        "respond ONLY with a JSON object (no markdown, no backticks) with these exact fields:\n\n"
        "- primary_category: one of: outerwear, layered_wear, inner_wear, bottoms, shoes, accessories\n"
        "- sub_category: be specific, e.g., long_coat, trench_coat, puffer_jacket, blazer, cardigan, hoodie, sweater, dress_shirt, t_shirt, polo, tank_top, jeans, chinos, dress_pants, shorts, joggers, sneakers, boots, loafers, oxford_shoes, sandals, scarf, belt, hat, bag\n"
        "- primary_color: single dominant color (e.g., navy, black, cream, olive, burgundy, charcoal)\n"
        "- secondary_color: if applicable, else null\n"
        "- primary_material: one of: cotton, wool, cashmere, polyester, nylon, leather, suede, denim, silk, linen, fleece, synthetic, corduroy, tweed, knit, mixed\n"
        "- thickness: one of: ultralight, light, medium, heavy, extra_heavy\n"
        "- occasion: array, one or more of: casual, smart_casual, business_casual, business_formal, formal, athletic, outdoor\n"
        "- silhouette: one of: slim, regular, relaxed, oversized, tapered, straight, wide, cropped, longline\n"
        "- season: array, one or more of: spring, summer, fall, winter\n"
        "- description: one natural-language sentence describing the item"
    )
    
    # Prepare the message
    message = {
        "role": "user",
        "content": [
            {
                "type": "image", 
                "source": {
                    "type": "base64", 
                    "media_type": "image/jpeg", 
                    "data": base64_string
                }
            },
            {
                "type": "text", 
                "text": "Analyze this clothing item."
            }
        ]
    }
    
    try:
        # Call the Anthropic API
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[message]
        )
        
        # Extract the content
        content = response.content[0].text
        return content
    except Exception as e:
        print(f"Error analyzing {image_path}: {str(e)}")
        return None

def resize_image(image_path, max_size=1024):
    """Resize image to max 1024px on the longest side"""
    with Image.open(image_path) as img:
        # Calculate the scaling factor
        width, height = img.size
        if width > height:
            new_width = min(max_size, width)
            new_height = int((height * new_width) / width)
        else:
            new_height = min(max_size, height)
            new_width = int((width * new_height) / height)
        
        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized_img

def encode_image_to_base64(image_path):
    """Encode image to base64 string"""
    # First resize the image
    resized_img = resize_image(image_path)
    
    # Convert HEIC to JPEG in memory if needed
    import io
    buffer = io.BytesIO()
    
    # Check if the original image was HEIC and convert to JPEG
    if image_path.lower().endswith(('.heic', '.heif')):
        # Convert to RGB if needed (HEIC might be in different color space)
        if resized_img.mode in ('RGBA', 'LA', 'P'):
            # Convert to RGB for JPEG compatibility
            rgb_img = Image.new('RGB', resized_img.size, (255, 255, 255))
            if resized_img.mode == 'P':
                resized_img = resized_img.convert('RGBA')
            if resized_img.mode in ('RGBA', 'LA'):
                rgb_img.paste(resized_img, mask=resized_img.split()[-1] if resized_img.mode == 'RGBA' else None)
            else:
                rgb_img.paste(resized_img)
            resized_img = rgb_img
        resized_img.save(buffer, format='JPEG', quality=85)
    else:
        resized_img.save(buffer, format='JPEG', quality=85)
    
    img_bytes = buffer.getvalue()
    
    # Encode to base64
    base64_str = base64.b64encode(img_bytes).decode('utf-8')
    return base64_str

def load_wardrobe(json_path):
    """Load existing wardrobe from JSON file."""
    if not os.path.exists(json_path):
        return {}
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_wardrobe(data, json_path):
    """Save wardrobe data to JSON file with pretty formatting."""
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)