"""Extract metadata from photo files, including GPS coordinates and timestamps."""

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pandas as pd
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List

# Enable HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    print("Warning: pillow-heif not available. HEIC files may not be processed.")


def get_decimal_from_dms(dms_coord: Tuple, ref: str) -> float:
    """Convert GPS coordinates from degrees/minutes/seconds to decimal format."""
    degrees = dms_coord[0]
    minutes = dms_coord[1] 
    seconds = dms_coord[2]
    
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    
    if ref in ('S', 'W'):
        decimal = -decimal
    
    return decimal


def extract_photo_metadata(image_path: str) -> Dict:
    """Extract metadata from a single photo file."""
    metadata = {
        'filename': os.path.basename(image_path),
        'filepath': image_path,
        'latitude': None,
        'longitude': None,
        'datetime_taken': None,
        'camera_make': None,
        'camera_model': None,
        'image_width': None,
        'image_height': None
    }
    
    try:
        with Image.open(image_path) as image:
            # Get basic image info
            metadata['image_width'] = image.size[0]
            metadata['image_height'] = image.size[1]
            
            # Extract EXIF data - use getexif() instead of _getexif() for better compatibility
            exif_data = image.getexif()
            
            if exif_data is not None and len(exif_data) > 0:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    if tag == 'DateTime':
                        try:
                            metadata['datetime_taken'] = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                        except ValueError:
                            pass
                    elif tag == 'Make':
                        metadata['camera_make'] = value
                    elif tag == 'Model':
                        metadata['camera_model'] = value
                
                # Handle GPS data - check for GPS IFD
                if 34853 in exif_data:  # GPS IFD tag
                    try:
                        gps_ifd = exif_data.get_ifd(34853)
                        gps_data = {}
                        for gps_tag_id, gps_value in gps_ifd.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_data[gps_tag] = gps_value
                        
                        # Extract GPS coordinates
                        if 'GPSLatitude' in gps_data and 'GPSLatitudeRef' in gps_data:
                            lat = get_decimal_from_dms(gps_data['GPSLatitude'], gps_data['GPSLatitudeRef'])
                            metadata['latitude'] = lat
                        
                        if 'GPSLongitude' in gps_data and 'GPSLongitudeRef' in gps_data:
                            lon = get_decimal_from_dms(gps_data['GPSLongitude'], gps_data['GPSLongitudeRef'])
                            metadata['longitude'] = lon
                    except Exception as gps_error:
                        print(f"GPS extraction error for {image_path}: {gps_error}")
    
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
    
    return metadata


def process_photo_directory(photos_dir: str) -> pd.DataFrame:
    """Process all photos in a directory and return a DataFrame with metadata."""
    # Only process web-ready formats (no HEIC conversion here)
    photo_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
    metadata_list = []
    
    photos_path = Path(photos_dir)
    
    for image_file in photos_path.rglob('*'):
        if image_file.suffix.lower() in photo_extensions:
            metadata = extract_photo_metadata(str(image_file))
            metadata_list.append(metadata)
    
    df = pd.DataFrame(metadata_list)
    
    if len(df) == 0:
        print(f"❌ No web-ready photos found in {photos_dir}")
        print("💡 Run 'python convert_photos.py' first to convert HEIC files to JPG")
        return pd.DataFrame()
    
    # Filter out photos without GPS coordinates
    df_with_gps = df.dropna(subset=['latitude', 'longitude'])
    
    print(f"Processed {len(df)} photos, {len(df_with_gps)} have GPS coordinates")
    
    return df_with_gps


def save_metadata_csv(df: pd.DataFrame, output_path: str) -> None:
    """Save the metadata DataFrame to a CSV file."""
    df.to_csv(output_path, index=False)
    print(f"Metadata saved to {output_path}")


if __name__ == "__main__":
    # Example usage
    photos_directory = "../photos"
    output_csv = "../output/photo_metadata.csv"
    
    if os.path.exists(photos_directory):
        metadata_df = process_photo_directory(photos_directory)
        save_metadata_csv(metadata_df, output_csv)
    else:
        print(f"Photos directory {photos_directory} not found")