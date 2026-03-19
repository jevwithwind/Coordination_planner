import os
import sys
import json
from .utils import process_single_image, load_wardrobe, save_wardrobe
import dotenv

# Load environment variables
dotenv.load_dotenv()

def main():
    if len(sys.argv) != 2:
        print("Usage: python add_item.py <image_filename>")
        sys.exit(1)
    
    image_filename = sys.argv[1]
    
    # Check if the file exists in wardrobe_photos
    photos_dir = '../wardrobe_photos'
    image_path = os.path.join(photos_dir, image_filename)
    
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
    result = process_single_image(image_path)
    
    if result:
        try:
            # Parse the JSON response
            item_data = json.loads(result)
            
            # Load existing wardrobe
            wardrobe_path = '../data/wardrobe.json'
            wardrobe = load_wardrobe(wardrobe_path)
            
            # Add the new item
            wardrobe[image_filename] = item_data
            
            # Save the updated wardrobe
            save_wardrobe(wardrobe, wardrobe_path)
            
            print(f"Successfully added {image_filename} to wardrobe catalog")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            sys.exit(1)
    else:
        print(f"Failed to analyze {image_filename}")
        sys.exit(1)

if __name__ == "__main__":
    main()