import os
import sys
import json
import base64
from PIL import Image
from pillow_heif import register_heif_opener
from anthropic import Anthropic
import dotenv

# Register HEIF opener to support HEIC files
register_heif_opener()

# Load environment variables
dotenv.load_dotenv()

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

def analyze_clothing_item(image_path):
    """Analyze a single clothing item using Anthropic API"""
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
        "respond ONLY with a JSON object (no markdown, no backticks) with these fields: "
        "category (one of: top, bottom, outerwear, footwear, accessory, base_layer, dress), "
        "subcategory (e.g., t-shirt, jeans, sneakers, scarf), "
        "color (primary color), "
        "secondary_color (if applicable, else null), "
        "material (best guess: cotton, wool, polyester, nylon, leather, denim, silk, fleece, synthetic, mixed), "
        "thickness (one of: ultralight, light, medium, heavy, extra_heavy), "
        "season (array, one or more of: spring, summer, fall, winter), "
        "formality (one of: casual, smart_casual, business, formal, athletic), "
        "description (one natural-language sentence describing the item)."
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

def main():
    if len(sys.argv) != 2:
        print("Usage: python add_item.py <image_filename>")
        sys.exit(1)
    
    image_filename = sys.argv[1]
    
    # Check if the file exists in wardrobe_photos
    photos_dir = '../wardrobe_photos'
    image_path = os.path.join(photos_dir, image_filename)
    
    # Check if the file exists in wardrobe_photos with supported extensions
    if not os.path.exists(image_path):
        # Check for case variations of HEIC
        possible_paths = [
            os.path.join(photos_dir, image_filename.lower()),
            os.path.join(photos_dir, image_filename.upper())
        ]
        found = False
        for path in possible_paths:
            if os.path.exists(path):
                image_path = path
                found = True
                break
        if not found:
            print(f"File {image_path} does not exist in {photos_dir}")
            sys.exit(1)
    
    print(f"Analyzing {image_filename}...")
    
    # Analyze the clothing item
    result = analyze_clothing_item(image_path)
    
    if result:
        try:
            # Parse the JSON response
            item_data = json.loads(result)
            
            # Load existing wardrobe
            wardrobe_path = '../data/wardrobe.json'
            wardrobe = {}
            
            if os.path.exists(wardrobe_path):
                with open(wardrobe_path, 'r', encoding='utf-8') as f:
                    wardrobe = json.load(f)
            
            # Add the new item
            wardrobe[image_filename] = item_data
            
            # Save the updated wardrobe
            os.makedirs(os.path.dirname(wardrobe_path), exist_ok=True)
            
            with open(wardrobe_path, 'w', encoding='utf-8') as f:
                json.dump(wardrobe, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully added {image_filename} to wardrobe catalog")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            sys.exit(1)
    else:
        print(f"Failed to analyze {image_filename}")
        sys.exit(1)

if __name__ == "__main__":
    main()