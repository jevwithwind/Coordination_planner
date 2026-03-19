import os
import sys
import json
import argparse
from utils import (
    get_supported_extensions, scan_image_files, process_single_image,
    load_wardrobe, save_wardrobe
)

def main():
    parser = argparse.ArgumentParser(description='Sync wardrobe photos with catalog')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without making changes')
    args = parser.parse_args()
    
    photos_dir = '../wardrobe_photos'
    wardrobe_path = '../data/wardrobe.json'
    
    # Get current image files
    image_files = set(scan_image_files(photos_dir))
    
    # Load existing wardrobe
    wardrobe = load_wardrobe(wardrobe_path)
    existing_files = set(wardrobe.keys())
    
    # Determine changes
    new_files = image_files - existing_files
    removed_files = existing_files - image_files
    unchanged_files = existing_files.intersection(image_files)
    
    # Print summary
    print("Wardrobe Sync Summary:")
    print()
    print(f"New items to catalog: {len(new_files)}", end="")
    if new_files:
        print(f" ({', '.join(sorted(new_files))})")
    else:
        print()
    
    print(f"Removed items to clean up: {len(removed_files)}", end="")
    if removed_files:
        print(f" ({', '.join(sorted(removed_files))})")
    else:
        print()
    
    print(f"Unchanged items: {len(unchanged_files)} (skipped)")
    print()
    
    if args.dry_run:
        print("Dry run completed. No changes were made.")
        return
    
    if not args.yes:
        response = input("Proceed? [y/N] ").lower().strip()
        if response not in ['y', 'yes']:
            print("Operation cancelled.")
            return
    
    # Process changes
    added_count = 0
    for filename in sorted(new_files):
        print(f"Processing new item: {filename}")
        image_path = os.path.join(photos_dir, filename)
        
        result = process_single_image(image_path)
        if result:
            try:
                item_data = json.loads(result)
                wardrobe[filename] = item_data
                added_count += 1
                print(f"  Successfully added: {filename}")
            except json.JSONDecodeError as e:
                print(f"  Error parsing JSON response for {filename}: {e}")
        else:
            print(f"  Failed to analyze: {filename}")
    
    # Remove deleted files
    removed_count = len(removed_files)
    for filename in removed_files:
        del wardrobe[filename]
        print(f"Removed: {filename}")
    
    # Save updated wardrobe
    save_wardrobe(wardrobe, wardrobe_path)
    
    print()
    print("Sync complete:")
    print()
    print(f"Added: {added_count} items")
    print(f"Removed: {removed_count} items")
    print(f"Total wardrobe: {len(wardrobe)} items")

if __name__ == "__main__":
    main()