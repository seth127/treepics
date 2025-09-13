
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
    
    // Initialize timeline slider
    const slider = document.getElementById('timeline-slider');
    const timelineStartEl = document.getElementById('timeline-start');
    const timelineEndEl = document.getElementById('timeline-end');
    
    timelineStartEl.textContent = formatDate(timelineStart);
    timelineEndEl.textContent = formatDate(timelineEnd);
    
    // Set up timeline slider event listener
    slider.addEventListener('input', function() {
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
    const slider = document.getElementById('timeline-slider');
    const currentEl = document.getElementById('timeline-current');
    const percentage = slider.value / 100;
    
    if (percentage === 1) {
        currentEl.innerHTML = '<strong>Showing all photos</strong>';
        return null;
    }
    
    // Calculate cutoff date based on percentage
    const totalTime = timelineEnd.getTime() - timelineStart.getTime();
    const cutoffTime = timelineStart.getTime() + (totalTime * percentage);
    const cutoffDate = new Date(cutoffTime);
    
    currentEl.innerHTML = `<strong>Photos through:</strong><br>${formatDate(cutoffDate)}`;
    return cutoffDate;
}

function applyFilters() {
    // Get current timeline cutoff
    const timelineCutoff = updateTimelineFilter();
    
    // Filter photos based on timeline and selected months
    filteredPhotos = allPhotos.filter(photo => {
        if (!photo.datetime_taken) return false;
        
        const photoDate = new Date(photo.datetime_taken);
        
        // Check timeline filter
        if (timelineCutoff && photoDate > timelineCutoff) {
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
    // Reset timeline slider
    const slider = document.getElementById('timeline-slider');
    slider.value = 100;
    
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
    const slider = document.getElementById('timeline-slider');
    const isTimelineFiltered = slider.value < 100;
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
