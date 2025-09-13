
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
