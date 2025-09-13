"""Generate static HTML site for the tree photos map."""

import pandas as pd
import json
from jinja2 import Template, Environment, FileSystemLoader
import os
import shutil
from pathlib import Path
from typing import Dict, List


def prepare_photos_for_web(photos_df: pd.DataFrame, photos_dir: str, output_dir: str) -> pd.DataFrame:
    """Copy web-ready photos to output directory. Expects photos to already be converted to web formats."""
    photos_web_dir = os.path.join(output_dir, 'photos')
    os.makedirs(photos_web_dir, exist_ok=True)
    
    # Create a copy of the dataframe to modify
    web_df = photos_df.copy()
    
    for idx, row in web_df.iterrows():
        original_path = row['filepath']
        filename = row['filename']
            
        destination = os.path.join(photos_web_dir, filename)
        
        try:
            # Copy web-ready photos directly
            shutil.copy2(original_path, destination)
            
            # Update the filepath to be relative to the web root
            web_df.at[idx, 'web_path'] = f'photos/{filename}'
            
        except Exception as e:
            print(f"Error copying {original_path}: {e}")
            # Remove this row if we can't copy the photo
            web_df = web_df.drop(idx)
    
    return web_df.reset_index(drop=True)


def group_photos_by_proximity(df: pd.DataFrame, proximity_threshold: float = 0.001) -> List[Dict]:
    """Group photos by geographic proximity."""
    # Simple clustering by proximity threshold (in decimal degrees)
    # This is a basic implementation - could be enhanced with proper clustering
    
    clusters = []
    processed = set()
    
    for idx, row in df.iterrows():
        if idx in processed:
            continue
            
        # Start a new cluster
        cluster = {
            'center_lat': row['latitude'],
            'center_lon': row['longitude'],
            'photos': [row.to_dict()]
        }
        processed.add(idx)
        
        # Find nearby photos
        for idx2, row2 in df.iterrows():
            if idx2 in processed:
                continue
                
            lat_diff = abs(row['latitude'] - row2['latitude'])
            lon_diff = abs(row['longitude'] - row2['longitude'])
            
            if lat_diff <= proximity_threshold and lon_diff <= proximity_threshold:
                cluster['photos'].append(row2.to_dict())
                processed.add(idx2)
        
        # Sort photos in cluster by datetime
        cluster['photos'].sort(key=lambda x: x['datetime_taken'] if x['datetime_taken'] else '')
        
        # Update cluster center to average of all photos
        if len(cluster['photos']) > 1:
            avg_lat = sum(p['latitude'] for p in cluster['photos']) / len(cluster['photos'])
            avg_lon = sum(p['longitude'] for p in cluster['photos']) / len(cluster['photos'])
            cluster['center_lat'] = avg_lat
            cluster['center_lon'] = avg_lon
        
        cluster['photo_count'] = len(cluster['photos'])
        clusters.append(cluster)
    
    return clusters


def generate_map_html(clusters: List[Dict], output_path: str) -> None:
    """Generate the main HTML file with embedded map."""
    
    # Convert datetime objects to strings for JSON serialization
    json_clusters = []
    for cluster in clusters:
        json_cluster = cluster.copy()
        json_cluster['photos'] = []
        
        for photo in cluster['photos']:
            json_photo = photo.copy()
            if json_photo['datetime_taken']:
                json_photo['datetime_taken'] = json_photo['datetime_taken'].isoformat()
            json_clusters.append(json_photo)
        
        json_clusters.append(json_cluster)
    
    # Prepare data for template
    clusters_json = json.dumps(clusters, default=str, indent=2)
    
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tree Photos Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div id="container">
        <header>
            <h1>Tree Photos Explorer</h1>
            <p>Click on map markers to explore tree photos by location</p>
        </header>
        
        <div id="map"></div>
        
        <div id="sidebar">
            <div id="photo-viewer">
                <h3>Select a location on the map</h3>
                <p>Click on any tree marker to view photos from that location.</p>
            </div>
        </div>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="js/map.js"></script>
    <script>
        // Photo clusters data
        const photoClusters = {{ clusters_json|safe }};
        
        // Initialize the map when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initializeMap(photoClusters);
        });
    </script>
</body>
</html>
"""
    
    template = Template(html_template)
    html_content = template.render(clusters_json=clusters_json)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_css(output_path: str) -> None:
    """Generate CSS file for the site."""
    css_content = """
body {
    margin: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f5f5f5;
}

#container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

header {
    background: linear-gradient(135deg, #2d5a27, #4a7c59);
    color: white;
    padding: 1rem 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

header h1 {
    margin: 0 0 0.5rem 0;
    font-size: 1.8rem;
}

header p {
    margin: 0;
    opacity: 0.9;
    font-size: 0.9rem;
}

#map {
    flex: 1;
    min-height: 400px;
}

#sidebar {
    position: fixed;
    top: 120px;
    right: 20px;
    width: 300px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 1000;
    max-height: calc(100vh - 140px);
    overflow-y: auto;
}

#photo-viewer {
    padding: 1rem;
}

#photo-viewer h3 {
    margin-top: 0;
    color: #2d5a27;
    border-bottom: 2px solid #4a7c59;
    padding-bottom: 0.5rem;
}

.photo-item {
    margin-bottom: 1rem;
    border-bottom: 1px solid #eee;
    padding-bottom: 1rem;
}

.photo-item:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.photo-item img {
    width: 100%;
    height: 200px;
    object-fit: cover;
    border-radius: 4px;
    cursor: pointer;
    transition: transform 0.2s;
}

.photo-item img:hover {
    transform: scale(1.05);
}

.photo-info {
    font-size: 0.8rem;
    color: #666;
    margin-top: 0.5rem;
}

.photo-date {
    font-weight: bold;
    color: #2d5a27;
}

/* Custom marker styles */
.tree-marker {
    background: transparent !important;
    border: none !important;
    cursor: pointer;
}

.tree-marker div {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.tree-marker:hover div {
    transform: scale(1.1);
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

/* Responsive design */
@media (max-width: 768px) {
    #sidebar {
        position: relative;
        top: auto;
        right: auto;
        width: 100%;
        max-height: 300px;
    }
    
    header {
        padding: 0.8rem 1rem;
    }
    
    header h1 {
        font-size: 1.5rem;
    }
}

/* Modal for full-size photos */
.photo-modal {
    display: none;
    position: fixed;
    z-index: 2000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.9);
}

.photo-modal-content {
    position: relative;
    margin: auto;
    padding: 20px;
    width: 90%;
    max-width: 800px;
    top: 50%;
    transform: translateY(-50%);
}

.photo-modal img {
    width: 100%;
    height: auto;
    border-radius: 4px;
}

.photo-modal-close {
    position: absolute;
    top: 10px;
    right: 25px;
    color: white;
    font-size: 35px;
    font-weight: bold;
    cursor: pointer;
}

.photo-modal-close:hover {
    opacity: 0.7;
}
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(css_content)


def generate_javascript(output_path: str) -> None:
    """Generate JavaScript file for map functionality."""
    js_content = """
let map;
let currentMarkers = [];
let allPhotos = []; // Store all individual photos for dynamic clustering
let currentZoom = 10;

function initializeMap(photoClusters) {
    // Initialize the map
    map = L.map('map').setView([40.7128, -74.0060], 10); // Default to NYC, will be updated
    
    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Flatten all photos from clusters into a single array for dynamic clustering
    allPhotos = [];
    photoClusters.forEach(cluster => {
        cluster.photos.forEach(photo => {
            allPhotos.push(photo);
        });
    });
    
    // Add initial markers
    updateMarkersForZoom();
    
    // Fit map to show all markers
    if (allPhotos.length > 0) {
        const group = new L.featureGroup(currentMarkers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
    
    // Listen for zoom changes to update clustering
    map.on('zoomend', () => {
        currentZoom = map.getZoom();
        updateMarkersForZoom();
    });
}

function updateMarkersForZoom() {
    // Clear existing markers
    currentMarkers.forEach(marker => map.removeLayer(marker));
    currentMarkers = [];
    
    // Calculate clustering threshold based on zoom level
    const clusteringThreshold = getClusteringThreshold(currentZoom);
    
    // Perform dynamic clustering
    const dynamicClusters = performDynamicClustering(allPhotos, clusteringThreshold);
    
    // Add new markers
    addPhotoMarkers(dynamicClusters);
}

function getClusteringThreshold(zoomLevel) {
    // Adjust clustering distance based on zoom level
    // Higher zoom = smaller threshold (less clustering)
    // Lower zoom = larger threshold (more clustering)
    
    // Very aggressive clustering - merge pins before they visually overlap
    const baseThreshold = 0.03; // Further increased base threshold
    const zoomFactor = Math.max(1, 18 - zoomLevel); // Zoom levels typically go from 1-18
    
    // Even more aggressive exponential curve (base 3 instead of 2.5)
    // and offset adjustment to make clustering kick in even earlier
    return baseThreshold * Math.pow(3, zoomFactor - 7);
}

function performDynamicClustering(photos, threshold) {
    const clusters = [];
    const processed = new Set();
    
    photos.forEach((photo, index) => {
        if (processed.has(index)) return;
        
        // Start a new cluster
        const cluster = {
            center_lat: photo.latitude,
            center_lon: photo.longitude,
            photos: [photo],
            photo_count: 1
        };
        processed.add(index);
        
        // Find nearby photos within threshold
        photos.forEach((otherPhoto, otherIndex) => {
            if (processed.has(otherIndex)) return;
            
            const distance = calculateDistance(
                photo.latitude, photo.longitude,
                otherPhoto.latitude, otherPhoto.longitude
            );
            
            if (distance <= threshold) {
                cluster.photos.push(otherPhoto);
                cluster.photo_count++;
                processed.add(otherIndex);
            }
        });
        
        // Calculate cluster center (average position)
        if (cluster.photos.length > 1) {
            const avgLat = cluster.photos.reduce((sum, p) => sum + p.latitude, 0) / cluster.photos.length;
            const avgLon = cluster.photos.reduce((sum, p) => sum + p.longitude, 0) / cluster.photos.length;
            cluster.center_lat = avgLat;
            cluster.center_lon = avgLon;
        }
        
        // Sort photos in cluster by datetime
        cluster.photos.sort((a, b) => {
            const dateA = a.datetime_taken ? new Date(a.datetime_taken) : new Date(0);
            const dateB = b.datetime_taken ? new Date(b.datetime_taken) : new Date(0);
            return dateA - dateB;
        });
        
        clusters.push(cluster);
    });
    
    return clusters;
}

function calculateDistance(lat1, lon1, lat2, lon2) {
    // Simple Euclidean distance for clustering purposes
    // For more accuracy over large distances, could use Haversine formula
    const latDiff = lat2 - lat1;
    const lonDiff = lon2 - lon1;
    return Math.sqrt(latDiff * latDiff + lonDiff * lonDiff);
}

function addPhotoMarkers(clusters) {
    clusters.forEach(cluster => {
        // Scale marker size based on photo count
        const markerSize = getMarkerSize(cluster.photo_count);
        const fontSize = getMarkerFontSize(cluster.photo_count, markerSize);
        
        const marker = L.marker([cluster.center_lat, cluster.center_lon], {
            icon: L.divIcon({
                className: 'tree-marker',
                html: `<div style="background: #4a7c59; color: white; border-radius: 50%; width: ${markerSize}px; height: ${markerSize}px; display: flex; align-items: center; justify-content: center; font-size: ${fontSize}px; font-weight: bold; border: 2px solid #2d5a27;">${cluster.photo_count}</div>`,
                iconSize: [markerSize, markerSize],
                iconAnchor: [markerSize/2, markerSize/2]
            })
        }).addTo(map);
        
        marker.on('click', () => showPhotosForCluster(cluster));
        currentMarkers.push(marker);
    });
}

function getMarkerSize(photoCount) {
    // Scale marker size based on photo count
    if (photoCount === 1) return 20;
    if (photoCount <= 5) return 25;
    if (photoCount <= 10) return 30;
    if (photoCount <= 20) return 35;
    return 40; // For very large clusters
}

function getMarkerFontSize(photoCount, markerSize) {
    // Adjust font size based on marker size and number of digits
    const digits = photoCount.toString().length;
    let baseFontSize = Math.max(10, markerSize * 0.4);
    
    // Reduce font size for larger numbers
    if (digits > 2) {
        baseFontSize *= 0.8;
    }
    
    return Math.max(8, Math.floor(baseFontSize));
}

function showPhotosForCluster(cluster) {
    const photoViewer = document.getElementById('photo-viewer');
    
    let html = `<h3>Photos from this location (${cluster.photo_count})</h3>`;
    
    cluster.photos.forEach((photo, index) => {
        const dateStr = photo.datetime_taken ? 
            new Date(photo.datetime_taken).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }) : 'Date unknown';
        
        html += `
            <div class="photo-item">
                <img src="${photo.web_path}" 
                     alt="${photo.filename}"
                     onclick="showPhotoModal('${photo.web_path}', '${photo.filename}')"
                     loading="lazy">
                <div class="photo-info">
                    <div class="photo-date">${dateStr}</div>
                    <div>${photo.filename}</div>
                    ${photo.camera_make && photo.camera_model ? 
                        `<div>${photo.camera_make} ${photo.camera_model}</div>` : ''}
                </div>
            </div>
        `;
    });
    
    photoViewer.innerHTML = html;
}

function showPhotoModal(imageSrc, filename) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('photo-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'photo-modal';
        modal.className = 'photo-modal';
        modal.innerHTML = `
            <div class="photo-modal-content">
                <span class="photo-modal-close">&times;</span>
                <img id="modal-image" src="" alt="">
            </div>
        `;
        document.body.appendChild(modal);
        
        // Add close functionality
        modal.querySelector('.photo-modal-close').onclick = () => {
            modal.style.display = 'none';
        };
        
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        };
    }
    
    // Show the modal with the selected image
    document.getElementById('modal-image').src = imageSrc;
    document.getElementById('modal-image').alt = filename;
    modal.style.display = 'block';
}

// Close modal with Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('photo-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
});
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(js_content)


def generate_static_site(metadata_csv: str, photos_dir: str, output_dir: str) -> None:
    """Generate the complete static site."""
    print(f"Generating static site from {metadata_csv}")
    
    # Read metadata
    df = pd.read_csv(metadata_csv)
    df['datetime_taken'] = pd.to_datetime(df['datetime_taken'])
    
    # Create output directory structure
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'css'), exist_ok=True)
    os.makedirs(os.path.join(output_dir, 'js'), exist_ok=True)
    
    # Prepare photos for web
    web_df = prepare_photos_for_web(df, photos_dir, output_dir)
    
    # Group photos by proximity
    clusters = group_photos_by_proximity(web_df)
    
    # Generate HTML
    generate_map_html(clusters, os.path.join(output_dir, 'index.html'))
    
    # Generate CSS
    generate_css(os.path.join(output_dir, 'css', 'style.css'))
    
    # Generate JavaScript
    generate_javascript(os.path.join(output_dir, 'js', 'map.js'))
    
    print(f"Static site generated successfully in {output_dir}")
    print(f"Found {len(clusters)} photo locations with {len(web_df)} total photos")


if __name__ == "__main__":
    # Example usage
    metadata_csv = "../output/photo_metadata.csv"
    photos_directory = "../photos"
    site_output_dir = "../output/site"
    
    if os.path.exists(metadata_csv):
        generate_static_site(metadata_csv, photos_directory, site_output_dir)
    else:
        print(f"Metadata CSV {metadata_csv} not found. Run metadata extraction first.")