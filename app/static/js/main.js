// Global variables
let map;
let userMarker;
let cropMarkers = new Map();
let drawnItems;
let currentLayer = 'osm';
let markerClusterGroup;
let currentEditingId = null;
let heatmapLayer;

// Constants
const defaultCenter = [41.3775, 64.5853]; // Uzbekistan
const defaultZoom = 6;

// Map layers
const layers = {
    osm: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }),
    satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri'
    }),
    terrain: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://opentopomap.org">OpenTopoMap</a> contributors',
        maxZoom: 17
    })
};

// Crop icon definitions
const cropIcons = {
    wheat: L.icon({
        iconUrl: "/static/images/markers/wheat.png",
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    }),
    cotton: L.icon({
        iconUrl: "/static/images/markers/cotton.png",
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    }),
    potato: L.icon({
        iconUrl: "/static/images/markers/potato.png",
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
    })
};

// DOM Elements
const loadingElement = document.getElementById('loading');
const locationStatus = document.getElementById('location-status');

// Initialize map with all features
async function initializeMap() {
    console.log("Map initialization started");
    console.log("Map element:", document.getElementById('map'));
    console.log("Map element dimensions:", document.getElementById('map').getBoundingClientRect());
    
    try {
        // Create map instance
        map = L.map('map').setView(defaultCenter, defaultZoom);
        console.log("Map object created:", map);
        
        // Add default layer
        layers.osm.addTo(map);
        
        // Initialize marker cluster group
        markerClusterGroup = L.markerClusterGroup();
        map.addLayer(markerClusterGroup);
        
        // Initialize drawing controls
        drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);
        
        const drawControl = new L.Control.Draw({
            draw: {
                marker: false,
                circle: false,
                circlemarker: false,
                rectangle: false,
                polyline: false,
                polygon: {
                    allowIntersection: false,
                    drawError: {
                        color: '#e1e100',
                        message: '<strong>Field boundary cannot intersect!</strong>'
                    },
                    shapeOptions: {
                        color: '#97009c'
                    }
                }
            },
            edit: {
                featureGroup: drawnItems
            }
        });
        map.addControl(drawControl);
        
        // Initialize date picker
        flatpickr("#planting-date", {
            dateFormat: "Y-m-d",
            maxDate: "today"
        });
        
        // Add event listeners
        map.on('draw:created', handleDrawCreated);
        map.on('click', handleMapClick);
        
        // Load existing reports
        await loadCropReports();
        
        // Initialize additional features
        updateWeatherForCurrentView();
        updateCropAdvisory();
        
        // Inside initializeMap after the map is created
        addControlsPanelToggle();
        
        // Add this to your initializeMap function, after creating the layers
        Object.values(layers).forEach(layer => {
            layer.on('tileerror', function(error) {
                console.error('Tile loading error:', error);
                
                // If it's the terrain layer that failed, show a notification
                if (layer === layers.terrain && currentLayer === 'terrain') {
                    const statusEl = document.getElementById('location-status');
                    if (statusEl) {
                        statusEl.textContent = 'Terrain tiles failed to load. Switching back to default layer.';
                        statusEl.className = 'error';
                        setTimeout(() => { statusEl.textContent = ''; }, 3000);
                    }
                    
                    // Fall back to OSM if terrain fails
                    switchLayer('osm');
                }
            });
        });
        
        console.log("Map initialization completed successfully");
    } catch (error) {
        console.error('Map initialization error:', error);
        if (locationStatus) {
            locationStatus.textContent = 'Error initializing map: ' + error.message;
            locationStatus.className = 'error';
        }
    }
    
    // Hide loading indicator
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }

    // Add to your initialization code
    if (window.innerWidth <= 768) {
        const form = document.getElementById('report-form');
        if (form) {
            form.classList.add('collapsed');
            form.addEventListener('click', function(e) {
                if (e.target === form || e.target.nodeName !== 'INPUT') {
                    form.classList.toggle('collapsed');
                }
            });
        }
    }
}

// Function to handle map clicks
function handleMapClick(e) {
    const lat = e.latlng.lat.toFixed(6);
    const lng = e.latlng.lng.toFixed(6);
    
    document.getElementById('latitude').value = lat;
    document.getElementById('longitude').value = lng;
    
    document.getElementById('report-id').value = '';
    document.getElementById('delete-button').style.display = 'none';
    document.getElementById('report-form').style.display = 'block';
    
    // Show coordinates in status
    if (locationStatus) {
        locationStatus.textContent = `Selected location: ${lat}, ${lng}`;
        locationStatus.className = 'info';
    }
}

// Handle drawing creation
function handleDrawCreated(e) {
    drawnItems.clearLayers();
    drawnItems.addLayer(e.layer);
}

// Layer switching
function switchLayer(layerName) {
    if (!map || currentLayer === layerName) return;
    
    // Show loading indicator
    const statusEl = document.getElementById('location-status');
    if (statusEl) {
        statusEl.textContent = `Loading ${layerName} layer...`;
        statusEl.className = 'info';
    }
    
    try {
        // Remove current layer
        map.removeLayer(layers[currentLayer]);
        
        // Add the selected layer
        if (layers[layerName]) {
            layers[layerName].addTo(map);
            currentLayer = layerName;
            
            // Clear status message after successful switch
            setTimeout(() => {
                if (statusEl) statusEl.textContent = '';
            }, 1000);
        } else {
            throw new Error(`Layer "${layerName}" not found`);
        }
    } catch (error) {
        console.error('Error switching layer:', error);
        
        // Fallback to OSM if there's an error
        if (currentLayer !== 'osm' && layers.osm) {
            layers.osm.addTo(map);
            currentLayer = 'osm';
        }
        
        // Show error message
        if (statusEl) {
            statusEl.textContent = `Error loading ${layerName} layer. Falling back to default.`;
            statusEl.className = 'error';
            setTimeout(() => { statusEl.textContent = ''; }, 3000);
        }
    }
}

// Load crop reports from API
async function loadCropReports() {
    if (loadingElement) {
        loadingElement.style.display = 'block';
    }
    
    try {
        const response = await fetch('/api/crop-reports');
        if (!response.ok) {
            throw new Error('Failed to fetch reports');
        }
        
        const reports = await response.json();
        
        markerClusterGroup.clearLayers();
        cropMarkers.clear();
        
        reports.forEach(report => {
            const icon = cropIcons[report.crop_type] || L.Icon.Default();
            
            const marker = L.marker([report.latitude, report.longitude], {icon: icon})
                .bindPopup(`
                    <div class="report-popup">
                        <h3>${capitalizeFirstLetter(report.crop_type)}</h3>
                        <p>Field size: ${report.field_size} hectares</p>
                        <p>Planting date: ${formatDate(report.planting_date)}</p>
                        <p>Reported: ${formatDate(report.timestamp)}</p>
                        ${report.is_owner ? '<button onclick="editReport(' + report.id + ')">Edit</button>' : ''}
                    </div>
                `);
            
            markerClusterGroup.addLayer(marker);
            cropMarkers.set(report.id, {
                marker,
                data: report
            });
        });
        
    } catch (error) {
        console.error('Error loading crop reports:', error);
        if (locationStatus) {
            locationStatus.textContent = 'Error loading reports';
            locationStatus.className = 'error';
        }
    }
    
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}

// Helper function to capitalize first letter
function capitalizeFirstLetter(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

// Edit an existing report
function editReport(id) {
    const reportData = cropMarkers.get(parseInt(id))?.data;
    if (!reportData) return;
    
    document.getElementById('report-id').value = reportData.id;
    document.getElementById('crop-type').value = reportData.crop_type;
    document.getElementById('field-size').value = reportData.field_size;
    document.getElementById('planting-date').value = reportData.planting_date || '';
    document.getElementById('latitude').value = reportData.latitude;
    document.getElementById('longitude').value = reportData.longitude;
    
    document.getElementById('delete-button').style.display = 'block';
    document.getElementById('report-form').style.display = 'block';
    
    map.setView([reportData.latitude, reportData.longitude], 15);
}

// Submit a new or updated report
async function submitReport() {
    const reportId = document.getElementById('report-id').value;
    const cropType = document.getElementById('crop-type').value;
    const fieldSize = document.getElementById('field-size').value;
    const plantingDate = document.getElementById('planting-date').value;
    const latitude = document.getElementById('latitude').value;
    const longitude = document.getElementById('longitude').value;
    
    if (!cropType || !fieldSize || !latitude || !longitude) {
        alert('Please fill all required fields');
        return;
    }
    
    const reportData = {
        crop_type: cropType,
        field_size: parseFloat(fieldSize),
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        planting_date: plantingDate || null
    };
    
    if (reportId) {
        reportData.id = parseInt(reportId);
    }
    
    try {
        const method = reportId ? 'PUT' : 'POST';
        
        const response = await fetch('/api/crop-reports', {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(reportData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Submission failed');
        }
        
        resetForm();
        await loadCropReports();
        
        // Show success message
        if (locationStatus) {
            locationStatus.textContent = 'Report submitted successfully';
            locationStatus.className = 'success';
            setTimeout(() => { locationStatus.textContent = ''; }, 3000);
        }
    } catch (error) {
        console.error('Error submitting report:', error);
        
        // Show error message
        if (locationStatus) {
            locationStatus.textContent = 'Failed to submit report: ' + error.message;
            locationStatus.className = 'error';
        }
    }
}

// Delete a report
async function deleteReport() {
    const reportId = document.getElementById('report-id').value;
    if (!reportId) return;
    
    if (!confirm('Are you sure you want to delete this report?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/crop-reports?id=${reportId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Delete failed');
        }
        
        resetForm();
        await loadCropReports();
        
        // Show success message
        if (locationStatus) {
            locationStatus.textContent = 'Report deleted successfully';
            locationStatus.className = 'success';
            setTimeout(() => { locationStatus.textContent = ''; }, 3000);
        }
    } catch (error) {
        console.error('Error deleting report:', error);
        
        // Show error message
        if (locationStatus) {
            locationStatus.textContent = 'Failed to delete report';
            locationStatus.className = 'error';
        }
    }
}

// Reset the form
function resetForm() {
    document.getElementById('report-id').value = '';
    document.getElementById('crop-type').value = '';
    document.getElementById('field-size').value = '';
    document.getElementById('planting-date').value = '';
    document.getElementById('latitude').value = '';
    document.getElementById('longitude').value = '';
    document.getElementById('delete-button').style.display = 'none';
    
    if (drawnItems) {
        drawnItems.clearLayers();
    }
}

// Search for a location
async function searchLocation() {
    const query = document.getElementById('search-input').value;
    if (!query) return;
    
    if (locationStatus) {
        locationStatus.textContent = `Searching for: ${query}...`;
        locationStatus.className = 'info';
    }
    
    try {
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.length > 0) {
            const { lat, lon } = data[0];
            map.setView([lat, lon], 13);
            
            if (locationStatus) {
                locationStatus.textContent = `Found: ${data[0].display_name}`;
                setTimeout(() => { locationStatus.textContent = ''; }, 3000);
            }
        } else {
            if (locationStatus) {
                locationStatus.textContent = 'Location not found';
                locationStatus.className = 'error';
                setTimeout(() => { locationStatus.textContent = ''; }, 3000);
            }
        }
    } catch (error) {
        console.error('Search error:', error);
        if (locationStatus) {
            locationStatus.textContent = 'Error searching location';
            locationStatus.className = 'error';
        }
    }
}

// Change language
function changeLanguage(lang) {
    document.cookie = `language=${lang};path=/;max-age=31536000`;
    window.location.reload();
}

// Weather display
async function displayWeatherForLocation(lat, lon) {
    try {
        const response = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
        const data = await response.json();
        
        // Create or update weather panel
        let weatherPanel = document.getElementById('weather-panel');
        if (!weatherPanel) {
            weatherPanel = document.createElement('div');
            weatherPanel.id = 'weather-panel';
            weatherPanel.className = 'weather-panel';
            document.body.appendChild(weatherPanel);
        }
        
        if (!data || data.error) {
            weatherPanel.innerHTML = `
                <h4>Weather</h4>
                <p>No data available</p>
            `;
            return;
        }
        
        weatherPanel.innerHTML = `
            <h4>${data.location || 'Weather'}</h4>
            <div class="weather-details">
                <p><strong>Temperature:</strong> ${data.temperature}°C</p>
                <p><strong>Humidity:</strong> ${data.humidity}%</p>
                <p><strong>Wind:</strong> ${data.wind_speed} m/s</p>
                <p><strong>Precipitation:</strong> ${data.precipitation || 0} mm</p>
            </div>
        `;
    } catch (error) {
        console.error("Weather display error:", error);
    }
}

// Update weather for current view
function updateWeatherForCurrentView() {
    if (!map) return;
    
    const center = map.getCenter();
    displayWeatherForLocation(center.lat, center.lng);
}

// Crop advisory
async function displayCropAdvisory(lat, lon) {
    try {
        const response = await fetch(`/api/crop-advisor?lat=${lat}&lon=${lon}`);
        const data = await response.json();
        
        // Create or update advisory panel
        let advisoryPanel = document.getElementById('crop-advisory');
        if (!advisoryPanel) {
            advisoryPanel = document.createElement('div');
            advisoryPanel.id = 'crop-advisory';
            advisoryPanel.className = 'crop-advisory';
            document.body.appendChild(advisoryPanel);
        }
        
        const cropTiming = data.planting_times || {};
        
        // Only show up to 5 crops to save space
        const cropsToShow = Object.keys(cropTiming).slice(0, 5);
        
        const cropsList = cropsToShow.map(crop => {
            const timing = cropTiming[crop];
            const isOptimal = timing.is_optimal_now ? 
                `<span class="optimal-now">★</span>` : '';
            
            return `
                <div class="crop-timing">
                    <strong>${capitalizeFirstLetter(crop)}</strong>: 
                    ${timing.start_month}-${timing.end_month} ${isOptimal}
                </div>
            `;
        }).join('');
        
        advisoryPanel.innerHTML = `
            <h4>Planting Advisory</h4>
            <div class="crop-timings">
                ${cropsList}
            </div>
        `;
    } catch (error) {
        console.error("Crop advisory error:", error);
    }
}

// Update crop advisory
function updateCropAdvisory() {
    if (!map) return;
    
    const center = map.getCenter();
    displayCropAdvisory(center.lat, center.lng);
}

// Initialize map when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM fully loaded, initializing map");
    
    // Show loading indicator
    if (loadingElement) {
        loadingElement.style.display = 'block';
    }
    
    // Initialize map
    initializeMap();
    
    // Add move event for weather updates
    if (map) {
        let weatherUpdateTimeout;
        map.on('moveend', function() {
            clearTimeout(weatherUpdateTimeout);
            weatherUpdateTimeout = setTimeout(updateWeatherForCurrentView, 1000);
        });
    }
});

// Error handling
window.onerror = function(msg, url, lineNo, columnNo, error) {
    console.error('Error: ' + msg + '\nURL: ' + url + '\nLine: ' + lineNo + '\nColumn: ' + columnNo);
    return false;
};

function addControlsPanelToggle() {
    // Create a custom control
    const uiToggleControl = L.Control.extend({
        options: {
            position: 'topright'
        },
        
        onAdd: function() {
            const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control ui-toggle-control');
            container.innerHTML = '<a href="#" title="Toggle panels">👁️</a>';
            
            container.onclick = function() {
                const weatherPanel = document.getElementById('weather-panel');
                const cropAdvisory = document.getElementById('crop-advisory');
                
                if (weatherPanel) {
                    weatherPanel.style.display = 
                        weatherPanel.style.display === 'none' ? 'block' : 'none';
                }
                
                if (cropAdvisory) {
                    cropAdvisory.style.display = 
                        cropAdvisory.style.display === 'none' ? 'block' : 'none';
                }
                
                return false;
            };
            
            return container;
        }
    });
    
    map.addControl(new uiToggleControl());
}

function addLayerControls() {
    const layerControl = L.control({position: 'topright'});
    
    layerControl.onAdd = function() {
        const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control layer-control');
        
        container.innerHTML = `
            <a href="#" id="osm-toggle" class="active" onclick="switchLayer('osm'); return false;" title="OpenStreetMap">OSM</a>
            <a href="#" id="satellite-toggle" onclick="switchLayer('satellite'); return false;" title="Satellite">SAT</a>
            <a href="#" id="terrain-toggle" onclick="switchLayer('terrain'); return false;" title="Terrain">TER</a>
        `;
        
        return container;
    };
    
    layerControl.addTo(map);
    
    // Function to update active layer button
    window.updateLayerControls = function(activeLayer) {
        document.querySelectorAll('.layer-control a').forEach(btn => {
            btn.classList.remove('active');
        });
        
        const activeBtn = document.getElementById(`${activeLayer}-toggle`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
    };
    
    // Update the switchLayer function to call updateLayerControls
    const originalSwitchLayer = window.switchLayer;
    window.switchLayer = function(layerName) {
        originalSwitchLayer(layerName);
        updateLayerControls(layerName);
    };
}