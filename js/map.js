
let map;
let currentMarkers = [];

function initializeMap(photoClusters) {
    // Initialize the map
    map = L.map('map').setView([40.7128, -74.0060], 10); // Default to NYC, will be updated
    
    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Add markers for photo clusters
    addPhotoMarkers(photoClusters);
    
    // Fit map to show all markers
    if (photoClusters.length > 0) {
        const group = new L.featureGroup(currentMarkers);
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

function addPhotoMarkers(clusters) {
    clusters.forEach(cluster => {
        const marker = L.marker([cluster.center_lat, cluster.center_lon], {
            icon: L.divIcon({
                className: 'tree-marker',
                html: `<div style="background: #4a7c59; color: white; border-radius: 50%; width: 25px; height: 25px; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: bold; border: 2px solid #2d5a27;">${cluster.photo_count}</div>`,
                iconSize: [25, 25],
                iconAnchor: [12, 12]
            })
        }).addTo(map);
        
        marker.on('click', () => showPhotosForCluster(cluster));
        currentMarkers.push(marker);
    });
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
