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
        
        <div id="date-filters">
            <h3 onclick="toggleFiltersCollapse()">
                📅 Filter Photos by Date
                <span class="collapse-icon">▼</span>
            </h3>
            
            <div class="date-filters-content" id="date-filters-content">
                <div class="filter-section">
                    <h4>Date Range Filter</h4>
                    <div class="timeline-container">
                        <div class="dual-range-container">
                            <div class="timeline-track">
                                <div class="timeline-range-fill" id="timeline-range-fill"></div>
                            </div>
                            <input type="range" 
                                   id="timeline-slider-start" 
                                   class="timeline-slider"
                                   min="0" 
                                   max="100" 
                                   value="0"
                                   step="1">
                            <input type="range" 
                                   id="timeline-slider-end" 
                                   class="timeline-slider"
                                   min="0" 
                                   max="100" 
                                   value="100"
                                   step="1">
                        </div>
                        <div class="timeline-range">
                            <span id="timeline-start">Start Date</span>
                            <span id="timeline-end">End Date</span>
                        </div>
                        <div class="timeline-current" id="timeline-current">
                            Showing all photos
                        </div>
                    </div>
                </div>
                
                <div class="filter-section">
                    <h4>Select Months</h4>
                    <div class="month-controls">
                        <button class="month-control-btn" onclick="selectAllMonths()">All</button>
                        <button class="month-control-btn" onclick="clearAllMonths()">None</button>
                    </div>
                    <div class="month-grid" id="month-grid">
                        <button class="month-btn selected" data-month="0">Jan</button>
                        <button class="month-btn selected" data-month="1">Feb</button>
                        <button class="month-btn selected" data-month="2">Mar</button>
                        <button class="month-btn selected" data-month="3">Apr</button>
                        <button class="month-btn selected" data-month="4">May</button>
                        <button class="month-btn selected" data-month="5">Jun</button>
                        <button class="month-btn selected" data-month="6">Jul</button>
                        <button class="month-btn selected" data-month="7">Aug</button>
                        <button class="month-btn selected" data-month="8">Sep</button>
                        <button class="month-btn selected" data-month="9">Oct</button>
                        <button class="month-btn selected" data-month="10">Nov</button>
                        <button class="month-btn selected" data-month="11">Dec</button>
                    </div>
                </div>
                
                <div class="filter-results" id="filter-results">
                    <strong>All photos shown</strong> (no filters active)
                </div>
                
                <button class="clear-filters" onclick="clearAllFilters()" disabled>
                    Clear All Filters
                </button>
            </div>
        </div>

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
    user-select: none;
}

.photo-modal-content {
    position: relative;
    margin: auto;
    padding: 20px;
    width: 90%;
    max-width: 800px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
}

.photo-modal-image-container {
    position: relative;
    max-width: 100%;
    max-height: 80vh;
    display: flex;
    align-items: center;
    justify-content: center;
}

.photo-modal img {
    max-width: 100%;
    max-height: 80vh;
    border-radius: 4px;
    object-fit: contain;
}

.photo-modal-close {
    position: absolute;
    top: 10px;
    right: 25px;
    color: white;
    font-size: 35px;
    font-weight: bold;
    cursor: pointer;
    z-index: 2001;
    background: rgba(0,0,0,0.5);
    border-radius: 50%;
    width: 50px;
    height: 50px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s;
}

.photo-modal-close:hover {
    background: rgba(0,0,0,0.8);
}

/* Gallery navigation arrows */
.photo-modal-nav {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(0,0,0,0.5);
    color: white;
    border: none;
    font-size: 30px;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s, opacity 0.2s;
    z-index: 2001;
    user-select: none;
}

.photo-modal-nav:hover {
    background: rgba(0,0,0,0.8);
}

.photo-modal-nav:disabled {
    opacity: 0.3;
    cursor: not-allowed;
}

.photo-modal-nav:disabled:hover {
    background: rgba(0,0,0,0.5);
}

.photo-modal-prev {
    left: 20px;
}

.photo-modal-next {
    right: 20px;
}

/* Photo info in modal */
.photo-modal-info {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0,0,0,0.7);
    color: white;
    padding: 10px 20px;
    border-radius: 20px;
    text-align: center;
    max-width: 80%;
    z-index: 2001;
}

.photo-modal-info .photo-title {
    font-weight: bold;
    margin-bottom: 5px;
}

.photo-modal-info .photo-details {
    font-size: 0.9em;
    opacity: 0.9;
}

.photo-modal-counter {
    position: absolute;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0,0,0,0.5);
    color: white;
    padding: 8px 16px;
    border-radius: 15px;
    font-size: 0.9em;
    z-index: 2001;
}

/* Date Filters */
#date-filters {
    position: fixed;
    top: 120px;
    left: 20px;
    width: 320px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 1000;
    max-height: calc(100vh - 140px);
    overflow-y: auto;
}

#date-filters h3 {
    margin: 0 0 1rem 0;
    padding: 1rem 1rem 0 1rem;
    color: #2d5a27;
    border-bottom: 2px solid #4a7c59;
    padding-bottom: 0.5rem;
    cursor: pointer;
    user-select: none;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.collapse-icon {
    font-size: 1.2rem;
    transition: transform 0.3s ease;
}

.collapse-icon.collapsed {
    transform: rotate(-90deg);
}

.date-filters-content {
    transition: max-height 0.3s ease, opacity 0.3s ease;
    overflow: hidden;
}

.date-filters-content.collapsed {
    max-height: 0;
    opacity: 0;
}

.filter-section {
    padding: 0 1rem 1rem 1rem;
}

.filter-section h4 {
    margin: 1rem 0 0.5rem 0;
    color: #2d5a27;
    font-size: 0.95rem;
}

.filter-section:first-of-type h4 {
    margin-top: 0;
}

/* Timeline Slider */
.timeline-container {
    margin: 1rem 0;
}

.dual-range-container {
    position: relative;
    margin: 10px 0;
}

.timeline-slider {
    position: absolute;
    width: 100%;
    height: 8px;
    border-radius: 4px;
    background: transparent;
    outline: none;
    -webkit-appearance: none;
    pointer-events: none;
}

.timeline-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #4a7c59;
    cursor: pointer;
    border: 2px solid #2d5a27;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    pointer-events: auto;
    position: relative;
    z-index: 2;
}

.timeline-slider::-moz-range-thumb {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #4a7c59;
    cursor: pointer;
    border: 2px solid #2d5a27;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    pointer-events: auto;
    position: relative;
    z-index: 2;
}

.timeline-track {
    width: 100%;
    height: 8px;
    border-radius: 4px;
    background: #ddd;
    position: relative;
}

.timeline-range-fill {
    height: 100%;
    border-radius: 4px;
    background: linear-gradient(90deg, #4a7c59, #2d5a27);
    position: absolute;
    top: 0;
}

.timeline-range {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: #666;
    margin-top: 5px;
}

.timeline-current {
    text-align: center;
    font-weight: bold;
    color: #2d5a27;
    margin: 0.5rem 0;
    background: #f8f9fa;
    padding: 0.5rem;
    border-radius: 4px;
    font-size: 0.9rem;
}

/* Month Selection */
.month-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.5rem;
    margin: 1rem 0;
}

.month-btn {
    padding: 0.5rem 0.25rem;
    border: 2px solid #ddd;
    background: white;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
    text-align: center;
    transition: all 0.2s;
    color: #333;
}

.month-btn:hover {
    border-color: #4a7c59;
    background: #f8f9fa;
}

.month-btn.selected {
    border-color: #2d5a27;
    background: #4a7c59;
    color: white;
    font-weight: bold;
}

.month-controls {
    display: flex;
    justify-content: space-between;
    margin: 0.5rem 0 1rem 0;
}

.month-control-btn {
    padding: 0.4rem 0.8rem;
    border: 1px solid #4a7c59;
    background: white;
    color: #4a7c59;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.2s;
}

.month-control-btn:hover {
    background: #4a7c59;
    color: white;
}

/* Filter Results */
.filter-results {
    background: #f8f9fa;
    padding: 0.5rem;
    border-radius: 4px;
    margin: 1rem 0 0 0;
    font-size: 0.85rem;
    color: #666;
    border-top: 1px solid #eee;
}

.filter-results strong {
    color: #2d5a27;
}

/* Clear Filters */
.clear-filters {
    width: 100%;
    padding: 0.6rem;
    background: #dc3545;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    margin: 1rem 0 0 0;
    transition: background 0.2s;
}

.clear-filters:hover {
    background: #c82333;
}

.clear-filters:disabled {
    background: #6c757d;
    cursor: not-allowed;
}

/* Mobile responsiveness for modal */
@media (max-width: 768px) {
    .photo-modal-content {
        padding: 10px;
    }
    
    .photo-modal-nav {
        width: 50px;
        height: 50px;
        font-size: 24px;
    }
    
    .photo-modal-prev {
        left: 10px;
    }
    
    .photo-modal-next {
        right: 10px;
    }
    
    .photo-modal-close {
        top: 10px;
        right: 10px;
        width: 40px;
        height: 40px;
        font-size: 24px;
    }
    
    .photo-modal-info {
        bottom: 10px;
        padding: 8px 16px;
        max-width: 90%;
        font-size: 0.9em;
    }

    /* Mobile adjustments for filters */
    #date-filters {
        position: relative;
        top: auto;
        left: auto;
        width: 100%;
        margin-bottom: 1rem;
        max-height: none;
    }
    
    #sidebar {
        position: relative;
        top: auto;
        right: auto;
        width: 100%;
        max-height: 300px;
    }
    
    .month-grid {
        grid-template-columns: repeat(4, 1fr);
        gap: 0.4rem;
    }
    
    .month-btn {
        font-size: 0.75rem;
        padding: 0.4rem 0.2rem;
    }
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
let filteredPhotos = []; // Photos after applying date filters
let currentZoom = 10;
let currentClusterPhotos = []; // Photos in the currently viewed cluster
let currentPhotoIndex = 0; // Index of currently displayed photo in modal

// Date filtering state
let timelineStart = null;
let timelineEnd = null;
let selectedMonths = new Set([0,1,2,3,4,5,6,7,8,9,10,11]); // All months selected by default
let filtersCollapsed = false;

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
    
    // Sort photos by date for timeline initialization
    allPhotos.sort((a, b) => {
        const dateA = a.datetime_taken ? new Date(a.datetime_taken) : new Date(0);
        const dateB = b.datetime_taken ? new Date(b.datetime_taken) : new Date(0);
        return dateA - dateB;
    });
    
    // Initialize filtered photos to include all photos initially
    filteredPhotos = [...allPhotos];
    
    // Initialize date filters
    initializeDateFilters();
    
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
    
    // Perform dynamic clustering using filtered photos
    const dynamicClusters = performDynamicClustering(filteredPhotos, clusteringThreshold);
    
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
    let threshold = baseThreshold * Math.pow(3, zoomFactor - 7);
    
    // Set minimum clustering distance (approximately 2-3 city blocks)
    // ~0.002 degrees ≈ 200-250 meters ≈ 2-3 city blocks in most cities
    const minimumClusterDistance = 0.002;
    
    // Ensure threshold never goes below minimum, even at high zoom levels
    return Math.max(threshold, minimumClusterDistance);
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
    
    // Store current cluster photos for gallery navigation
    currentClusterPhotos = cluster.photos;
    
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
                     onclick="showPhotoGallery(${index})"
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

function showPhotoGallery(photoIndex) {
    currentPhotoIndex = photoIndex;
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('photo-modal');
    if (!modal) {
        createPhotoModal();
        modal = document.getElementById('photo-modal');
    }
    
    // Update modal content with current photo
    updateModalPhoto();
    
    // Show the modal
    modal.style.display = 'block';
}

function createPhotoModal() {
    const modal = document.createElement('div');
    modal.id = 'photo-modal';
    modal.className = 'photo-modal';
    modal.innerHTML = `
        <div class="photo-modal-content">
            <div class="photo-modal-counter"></div>
            <span class="photo-modal-close">&times;</span>
            <button class="photo-modal-nav photo-modal-prev" onclick="navigateGallery(-1)">
                &#8249;
            </button>
            <div class="photo-modal-image-container">
                <img id="modal-image" src="" alt="">
            </div>
            <button class="photo-modal-nav photo-modal-next" onclick="navigateGallery(1)">
                &#8250;
            </button>
            <div class="photo-modal-info">
                <div class="photo-title"></div>
                <div class="photo-details"></div>
            </div>
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

function updateModalPhoto() {
    if (currentClusterPhotos.length === 0) return;
    
    const photo = currentClusterPhotos[currentPhotoIndex];
    const modal = document.getElementById('photo-modal');
    
    // Update image
    const modalImage = document.getElementById('modal-image');
    modalImage.src = photo.web_path;
    modalImage.alt = photo.filename;
    
    // Update counter
    const counter = modal.querySelector('.photo-modal-counter');
    counter.textContent = `${currentPhotoIndex + 1} of ${currentClusterPhotos.length}`;
    
    // Update photo info
    const title = modal.querySelector('.photo-title');
    const details = modal.querySelector('.photo-details');
    
    title.textContent = photo.filename;
    
    const dateStr = photo.datetime_taken ? 
        new Date(photo.datetime_taken).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }) : 'Date unknown';
    
    let detailsText = dateStr;
    if (photo.camera_make && photo.camera_model) {
        detailsText += ` • ${photo.camera_make} ${photo.camera_model}`;
    }
    details.textContent = detailsText;
    
    // Update navigation button states
    const prevBtn = modal.querySelector('.photo-modal-prev');
    const nextBtn = modal.querySelector('.photo-modal-next');
    
    prevBtn.disabled = currentPhotoIndex === 0;
    nextBtn.disabled = currentPhotoIndex === currentClusterPhotos.length - 1;
    
    // Hide navigation buttons if only one photo
    if (currentClusterPhotos.length <= 1) {
        prevBtn.style.display = 'none';
        nextBtn.style.display = 'none';
    } else {
        prevBtn.style.display = 'flex';
        nextBtn.style.display = 'flex';
    }
}

function navigateGallery(direction) {
    const newIndex = currentPhotoIndex + direction;
    
    if (newIndex >= 0 && newIndex < currentClusterPhotos.length) {
        currentPhotoIndex = newIndex;
        updateModalPhoto();
    }
}

// Keyboard navigation for modal
document.addEventListener('keydown', function(e) {
    const modal = document.getElementById('photo-modal');
    if (modal && modal.style.display === 'block') {
        switch(e.key) {
            case 'Escape':
                modal.style.display = 'none';
                break;
            case 'ArrowLeft':
                navigateGallery(-1);
                e.preventDefault();
                break;
            case 'ArrowRight':
                navigateGallery(1);
                e.preventDefault();
                break;
        }
    }
});

// Date filtering functions
function initializeDateFilters() {
    if (allPhotos.length === 0) return;
    
    // Find date range from all photos
    const validPhotos = allPhotos.filter(photo => photo.datetime_taken);
    if (validPhotos.length === 0) return;
    
    const dates = validPhotos.map(photo => new Date(photo.datetime_taken));
    timelineStart = new Date(Math.min(...dates));
    timelineEnd = new Date(Math.max(...dates));
    
    // Initialize timeline sliders
    const startSlider = document.getElementById('timeline-slider-start');
    const endSlider = document.getElementById('timeline-slider-end');
    const timelineStartEl = document.getElementById('timeline-start');
    const timelineEndEl = document.getElementById('timeline-end');
    
    timelineStartEl.textContent = formatDate(timelineStart);
    timelineEndEl.textContent = formatDate(timelineEnd);
    
    // Set up timeline slider event listeners
    startSlider.addEventListener('input', function() {
        // Ensure start doesn't exceed end
        if (parseInt(this.value) > parseInt(endSlider.value)) {
            this.value = endSlider.value;
        }
        updateTimelineFilter();
        applyFilters();
    });
    
    endSlider.addEventListener('input', function() {
        // Ensure end doesn't go below start
        if (parseInt(this.value) < parseInt(startSlider.value)) {
            this.value = startSlider.value;
        }
        updateTimelineFilter();
        applyFilters();
    });
    
    // Set up month button event listeners
    const monthButtons = document.querySelectorAll('.month-btn');
    monthButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            toggleMonth(parseInt(this.dataset.month));
            applyFilters();
        });
    });
    
    // Initial filter results display
    updateFilterResults();
}

function updateTimelineFilter() {
    const startSlider = document.getElementById('timeline-slider-start');
    const endSlider = document.getElementById('timeline-slider-end');
    const currentEl = document.getElementById('timeline-current');
    const rangeFill = document.getElementById('timeline-range-fill');
    
    const startPercentage = startSlider.value / 100;
    const endPercentage = endSlider.value / 100;
    
    // Update visual range fill
    rangeFill.style.left = (startPercentage * 100) + '%';
    rangeFill.style.width = ((endPercentage - startPercentage) * 100) + '%';
    
    if (startPercentage === 0 && endPercentage === 1) {
        currentEl.innerHTML = '<strong>Showing all photos</strong>';
        return { startDate: null, endDate: null };
    }
    
    // Calculate actual dates based on percentages
    const totalTime = timelineEnd.getTime() - timelineStart.getTime();
    const startTime = timelineStart.getTime() + (totalTime * startPercentage);
    const endTime = timelineStart.getTime() + (totalTime * endPercentage);
    const startDate = new Date(startTime);
    const endDate = new Date(endTime);
    
    if (startPercentage === 0) {
        currentEl.innerHTML = `<strong>Photos through:</strong><br>${formatDate(endDate)}`;
    } else if (endPercentage === 1) {
        currentEl.innerHTML = `<strong>Photos from:</strong><br>${formatDate(startDate)}`;
    } else {
        currentEl.innerHTML = `<strong>Photos from:</strong><br>${formatDate(startDate)}<br><strong>to:</strong> ${formatDate(endDate)}`;
    }
    
    return { startDate, endDate };
}

function applyFilters() {
    // Get current timeline range
    const timelineRange = updateTimelineFilter();
    
    // Filter photos based on timeline and selected months
    filteredPhotos = allPhotos.filter(photo => {
        if (!photo.datetime_taken) return false;
        
        const photoDate = new Date(photo.datetime_taken);
        
        // Check timeline filter
        if (timelineRange.startDate && photoDate < timelineRange.startDate) {
            return false;
        }
        if (timelineRange.endDate && photoDate > timelineRange.endDate) {
            return false;
        }
        
        // Check month filter
        const photoMonth = photoDate.getMonth();
        if (!selectedMonths.has(photoMonth)) {
            return false;
        }
        
        return true;
    });
    
    // Update markers on map
    updateMarkersForZoom();
    
    // Update filter results display
    updateFilterResults();
    
    // Update clear filters button
    updateClearFiltersButton();
    
    // Clear photo viewer if current cluster is no longer visible
    updatePhotoViewer();
}

function toggleMonth(monthIndex) {
    const monthBtn = document.querySelector(`[data-month="${monthIndex}"]`);
    
    if (selectedMonths.has(monthIndex)) {
        selectedMonths.delete(monthIndex);
        monthBtn.classList.remove('selected');
    } else {
        selectedMonths.add(monthIndex);
        monthBtn.classList.add('selected');
    }
}

function selectAllMonths() {
    selectedMonths = new Set([0,1,2,3,4,5,6,7,8,9,10,11]);
    document.querySelectorAll('.month-btn').forEach(btn => {
        btn.classList.add('selected');
    });
    applyFilters();
}

function clearAllMonths() {
    selectedMonths = new Set();
    document.querySelectorAll('.month-btn').forEach(btn => {
        btn.classList.remove('selected');
    });
    applyFilters();
}

function clearAllFilters() {
    // Reset timeline sliders
    const startSlider = document.getElementById('timeline-slider-start');
    const endSlider = document.getElementById('timeline-slider-end');
    startSlider.value = 0;
    endSlider.value = 100;
    
    // Reset month selection
    selectAllMonths();
    
    // Apply filters (which will show all photos)
    applyFilters();
}

function updateFilterResults() {
    const resultsEl = document.getElementById('filter-results');
    const totalPhotos = allPhotos.length;
    const filteredCount = filteredPhotos.length;
    
    if (filteredCount === totalPhotos) {
        resultsEl.innerHTML = '<strong>All photos shown</strong> (no filters active)';
    } else {
        const percentage = Math.round((filteredCount / totalPhotos) * 100);
        resultsEl.innerHTML = `<strong>${filteredCount} of ${totalPhotos} photos shown</strong> (${percentage}%)`;
    }
}

function updateClearFiltersButton() {
    const clearBtn = document.querySelector('.clear-filters');
    const startSlider = document.getElementById('timeline-slider-start');
    const endSlider = document.getElementById('timeline-slider-end');
    const isTimelineFiltered = startSlider.value > 0 || endSlider.value < 100;
    const isMonthFiltered = selectedMonths.size < 12;
    
    clearBtn.disabled = !isTimelineFiltered && !isMonthFiltered;
}

function updatePhotoViewer() {
    // If a cluster is currently being displayed, check if it still has visible photos
    if (currentClusterPhotos.length > 0) {
        const visiblePhotos = currentClusterPhotos.filter(photo => 
            filteredPhotos.some(fp => fp.filename === photo.filename)
        );
        
        if (visiblePhotos.length === 0) {
            // No photos in current cluster are visible, clear the viewer
            const photoViewer = document.getElementById('photo-viewer');
            photoViewer.innerHTML = `
                <h3>Select a location on the map</h3>
                <p>Click on any tree marker to view photos from that location.</p>
            `;
            currentClusterPhotos = [];
        }
    }
}

function formatDate(date) {
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Collapse/expand functionality
function toggleFiltersCollapse() {
    const content = document.getElementById('date-filters-content');
    const icon = document.querySelector('.collapse-icon');
    
    filtersCollapsed = !filtersCollapsed;
    
    if (filtersCollapsed) {
        content.classList.add('collapsed');
        icon.classList.add('collapsed');
    } else {
        content.classList.remove('collapsed');
        icon.classList.remove('collapsed');
    }
}
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