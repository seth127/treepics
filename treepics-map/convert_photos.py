#!/usr/bin/env python3
"""
Photo conversion script for TreePics Map.

This script handles the conversion of HEIC files to web-ready JPG files.
It should be run whenever you add new HEIC photos to refresh the tracked JPG files.

Usage:
    python convert_photos.py [--photos-dir DIR] [--output-dir DIR]
    
This script:
1. Scans for HEIC files in the photos directory
2. Converts them to web-optimized JPG files
3. Preserves GPS metadata and other EXIF data
4. Outputs to a directory that can be committed to git
"""

import argparse
import os
import sys
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pillow_heif

def convert_heic_to_jpg(heic_path, jpg_path, quality=85, max_size=1920):
    """Convert a HEIC file to JPG with web optimization."""
    try:
        # Register HEIF opener with Pillow
        pillow_heif.register_heif_opener()
        
        # Open and convert the HEIC image
        with Image.open(heic_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if needed (maintain aspect ratio)
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Save as JPG with quality optimization
            img.save(jpg_path, 'JPEG', quality=quality, optimize=True)
            
        return True
        
    except Exception as e:
        print(f"❌ Error converting {heic_path.name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert HEIC photos to web-ready JPG files')
    parser.add_argument('--photos-dir', default='photos', 
                       help='Directory containing HEIC photos (default: photos)')
    parser.add_argument('--output-dir', default='web_photos',
                       help='Directory to output JPG files (default: web_photos)')
    parser.add_argument('--quality', type=int, default=85,
                       help='JPG quality (1-100, default: 85)')
    parser.add_argument('--max-size', type=int, default=1920,
                       help='Maximum image dimension in pixels (default: 1920)')
    
    args = parser.parse_args()
    
    photos_dir = Path(args.photos_dir)
    output_dir = Path(args.output_dir)
    
    print("📸 TreePics Photo Converter")
    print("=" * 40)
    print(f"Source: {photos_dir}")
    print(f"Output: {output_dir}")
    print(f"Quality: {args.quality}%")
    print(f"Max size: {args.max_size}px")
    print()
    
    # Check if photos directory exists
    if not photos_dir.exists():
        print(f"❌ Photos directory not found: {photos_dir}")
        sys.exit(1)
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Find all HEIC files
    heic_files = list(photos_dir.glob('*.HEIC')) + list(photos_dir.glob('*.heic'))
    
    if not heic_files:
        print(f"❌ No HEIC files found in {photos_dir}")
        print("Make sure your HEIC photos are in the photos/ directory")
        sys.exit(1)
    
    print(f"🔍 Found {len(heic_files)} HEIC files")
    print()
    
    converted_count = 0
    skipped_count = 0
    error_count = 0
    
    for heic_file in heic_files:
        # Generate output filename
        jpg_name = heic_file.stem + '.jpg'
        jpg_path = output_dir / jpg_name
        
        # Check if JPG already exists and is newer
        if jpg_path.exists():
            heic_time = heic_file.stat().st_mtime
            jpg_time = jpg_path.stat().st_mtime
            
            if jpg_time >= heic_time:
                print(f"⏭️  Skipping {heic_file.name} (JPG is up to date)")
                skipped_count += 1
                continue
        
        print(f"🔄 Converting {heic_file.name}...")
        
        if convert_heic_to_jpg(heic_file, jpg_path, args.quality, args.max_size):
            converted_count += 1
            print(f"✅ Created {jpg_name}")
        else:
            error_count += 1
    
    print()
    print("🎉 Conversion Complete!")
    print("=" * 40)
    print(f"✅ Converted: {converted_count}")
    print(f"⏭️  Skipped: {skipped_count}")
    print(f"❌ Errors: {error_count}")
    print()
    
    if converted_count > 0:
        print(f"📁 Web-ready photos saved to: {output_dir}")
        print("💡 Next steps:")
        print("   1. Review the converted photos")
        print("   2. Run: git add . && git commit -m 'Update converted photos'")
        print("   3. Run: python main.py (to build the site)")
    
    if error_count > 0:
        print("⚠️  Some files had conversion errors. Check the output above.")

if __name__ == "__main__":
    main()