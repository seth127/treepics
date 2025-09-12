#!/usr/bin/env python3
"""
Tree Photos Map - Main entry point
Processes tree photos to create an interactive map website.
"""

import argparse
import os
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from treepics_map.metadata_extractor import process_photo_directory, save_metadata_csv
from treepics_map.static_site_generator import generate_static_site


def main():
    parser = argparse.ArgumentParser(description='Generate an interactive map from tree photos')
    parser.add_argument('--photos-dir', '-p', 
                       default='web_photos',
                       help='Directory containing web-ready photos (default: web_photos)')
    parser.add_argument('--output-dir', '-o',
                       default='output/site', 
                       help='Output directory for generated site (default: output/site)')
    parser.add_argument('--metadata-only', '-m',
                       action='store_true',
                       help='Only extract metadata, don\'t generate site')
    
    args = parser.parse_args()
    
    photos_dir = Path(args.photos_dir)
    output_dir = Path(args.output_dir)
    metadata_dir = Path('output')
    metadata_csv = metadata_dir / 'photo_metadata.csv'
    
    # Create output directories
    metadata_dir.mkdir(exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if photos directory exists
    if not photos_dir.exists():
        print(f"Photos directory '{photos_dir}' not found.")
        print("💡 Run 'python convert_photos.py' first to convert HEIC files to web-ready JPGs")
        print("\nWorkflow:")
        print("1. Add HEIC photos to 'photos/' directory") 
        print("2. Run 'python convert_photos.py' to create web-ready JPGs")
        print("3. Run 'python main.py' to build the site")
        return
    
    print(f"Processing photos from: {photos_dir}")
    print(f"Output directory: {output_dir}")
    
    # Extract metadata from photos
    print("\n📸 Extracting metadata from photos...")
    try:
        metadata_df = process_photo_directory(str(photos_dir))
        
        if len(metadata_df) == 0:
            print("❌ No photos with GPS coordinates found!")
            print("Make sure your photos were taken with location services enabled.")
            return
            
        # Save metadata to CSV
        save_metadata_csv(metadata_df, str(metadata_csv))
        print(f"✅ Metadata extraction complete: {len(metadata_df)} photos processed")
        
        if args.metadata_only:
            print(f"📄 Metadata saved to: {metadata_csv}")
            return
        
        # Generate static site
        print("\n🗺️  Generating interactive map...")
        generate_static_site(str(metadata_csv), str(photos_dir), str(output_dir))
        
        print(f"\n🎉 Success! Your tree photos map is ready!")
        print(f"📁 Site files: {output_dir}")
        print(f"🌐 Open {output_dir / 'index.html'} in a web browser to view your map")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    main()
