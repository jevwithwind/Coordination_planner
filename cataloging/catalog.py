import os
import json
import time
import sys
from .utils import (
    scan_image_files, process_single_image,
    load_wardrobe, save_wardrobe
)

# Load environment variables
import dotenv
dotenv.load_dotenv()

def main():
    # Check for --force flag
    force_process = '--force' in sys.argv
    
    # Get all image files from wardrobe_photos directory
    photos_dir = '../wardrobe_photos'
    image_files = scan_image_files(photos_dir)
    
    if not image_files:
        print(f"No supported image files found in {photos_dir}")
        return
    
    print(f"Found {len(image_files)} image files to process")
    
    # Load existing wardrobe
    wardrobe_path = '../data/wardrobe.json'
    wardrobe = load_wardrobe(wardrobe_path)
    
    # Process each image
    for idx, filename in enumerate(image_files, 1):
        # Skip if file already exists in wardrobe and force flag is not set
        if filename in wardrobe and not force_process:
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
            print(f"  Failed to analyze: {filename}")
    
    # Save the wardrobe
    save_wardrobe(wardrobe, wardrobe_path)
    
    print(f"\nWardrobe catalog saved to {wardrobe_path}")
    print(f"Total items cataloged: {len(wardrobe)}")

if __name__ == "__main__":
    main()