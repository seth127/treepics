# Photos Directory

Place your tree photos here for processing.

## Requirements

Your photos should:
- Have GPS coordinates (location services enabled when taken)
- Be in common formats: JPG, JPEG, PNG, TIFF
- Contain EXIF metadata

## Getting Photos from Your iPhone

### Option 1: Direct File Transfer
1. Connect iPhone to computer
2. Use Photos app or Image Capture to export photos
3. Make sure to export "unmodified originals" to preserve metadata

### Option 2: Google Photos
1. Upload photos to Google Photos
2. Use Google Takeout or Google Drive API to download
3. Ensure "high quality" or "original quality" to preserve metadata

### Option 3: AirDrop or iCloud
- AirDrop maintains metadata when transferring to Mac
- iCloud Photos can be downloaded with metadata intact

## File Organization

You can organize photos in subdirectories if desired:
```
photos/
├── 2023/
│   ├── spring/
│   └── summer/
├── 2024/
└── favorites/
```

The metadata extractor will recursively scan all subdirectories.
