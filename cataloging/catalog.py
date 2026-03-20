import os
import json
import time
import sys
import argparse
from .utils import (
    scan_image_files, process_single_image,
    load_wardrobe, save_wardrobe
)

# Load environment variables
import dotenv
dotenv.load_dotenv()

def main():
    parser = argparse.ArgumentParser(description='Catalog wardrobe photos')
    parser.add_argument('--user', required=True, help='Username for the user whose photos to catalog')
    parser.add_argument('--force', action='store_true', help='Force re-processing of all photos')
    args = parser.parse_args()
    
    username = args.user
    
    # Get all image files from user's wardrobe_photos directory
    photos_dir = f'../users/{username}/wardrobe_photos'
    image_files = scan_image_files(photos_dir)
    
    if not image_files:
        print(f"No supported image files found in {photos_dir}")
        return
    
    print(f"Found {len(image_files)} image files to process")
    
    # Load existing wardrobe
    wardrobe_path = f'../users/{username}/wardrobe.json'
    wardrobe = load_wardrobe(wardrobe_path)
    
    # Process each image
    for idx, filename in enumerate(image_files, 1):
        # Skip if file already exists in wardrobe and force flag is not set
        if filename in wardrobe and not args.force:
            print(f"Skipping {idx}/{len(image_files)}: {filename} (already processed)")
            continue
        
        print(f"Processing {idx}/{len(image_files)}: {filename}")
        
        image_path = os.path.join(photos_dir, filename)
        
        # Analyze the clothing item
        result = process_single_image(image_path)
        
        if result:
            try:
                # Parse the JSON response
                item_data = json.loads(result)
                wardrobe[filename] = item_data
                print(f"  Successfully analyzed: {filename}")
                
                # Add delay to avoid rate limiting
                time.sleep(1)
            except json.JSONDecodeError as e:
                print(f"  Error parsing JSON response for {filename}: {e}")
        else:
            print(f"  Failed to analyze {filename}")
    
    # Save the wardrobe
    save_wardrobe(wardrobe, wardrobe_path)
    
    print(f"\nWardrobe catalog saved to {wardrobe_path}")
    print(f"Total items cataloged: {len(wardrobe)}")

if __name__ == "__main__":
    main()