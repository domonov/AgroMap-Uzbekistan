// Global variables
let map;
let userMarker;
let cropMarkers = new Map();
let drawnItems;
let currentLayer = 'osm';
let markerClusterGroup;
let currentEditingId = null;
let heatmapLayer;
let isSelectingLocationForSuggestion = false;

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
        
        // Auto-locate user
        await autoLocateUser();
        
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

// Trends and Analytics Functions
async function showTrendsModal() {
    document.getElementById('trends-modal').style.display = 'block';
    await loadTrendsData();
}

function closeTrendsModal() {
    document.getElementById('trends-modal').style.display = 'none';
}

async function loadTrendsData() {
    try {
        // Load crop trends
        const trendsResponse = await fetch('/api/crop-trends');
        const trendsData = await trendsResponse.json();
        
        // Display crop distribution
        displayCropDistribution(trendsData.crop_distribution);
        
        // Load price predictions for popular crops
        await loadPricePredictions(['wheat', 'cotton', 'potato']);
        
        // Display monthly trends
        displayMonthlyTrends(trendsData.monthly_trends);
        
    } catch (error) {
        console.error('Error loading trends data:', error);
        document.getElementById('trends-content').innerHTML = '<p>Error loading trends data</p>';
    }
}

function displayCropDistribution(distribution) {
    const container = document.getElementById('crop-distribution');
    let html = '<h3>Crop Distribution</h3><div class="stats-grid">';
    
    distribution.forEach(crop => {
        html += `
            <div class="stat-card">
                <h4>${crop.crop_type.charAt(0).toUpperCase() + crop.crop_type.slice(1)}</h4>
                <p>Reports: ${crop.count}</p>
                <p>Total Area: ${crop.total_area.toFixed(1)} ha</p>
                <p>Avg Field: ${crop.avg_field_size.toFixed(1)} ha</p>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

async function loadPricePredictions(crops) {
    const container = document.getElementById('price-predictions');
    let html = '<h3>Price Predictions</h3><div class="predictions-grid">';
    
    for (const crop of crops) {
        try {
            const response = await fetch(`/api/price-prediction/${crop}`);
            const prediction = await response.json();
            
            const trendIcon = prediction.trend === 'increasing' ? '📈' : 
                            prediction.trend === 'decreasing' ? '📉' : '➡️';
            
            html += `
                <div class="prediction-card">
                    <h4>${crop.charAt(0).toUpperCase() + crop.slice(1)} ${trendIcon}</h4>
                    <p>Current: ${prediction.current_price} UZS/kg</p>
                    <p>Predicted: ${prediction.predicted_price} UZS/kg</p>
                    <p>Confidence: ${(prediction.confidence * 100).toFixed(0)}%</p>
                </div>
            `;
        } catch (error) {
            console.error(`Error loading prediction for ${crop}:`, error);
        }
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function displayMonthlyTrends(trends) {
    const container = document.getElementById('monthly-trends');
    let html = '<h3>Monthly Planting Trends</h3>';
    
    if (Object.keys(trends).length === 0) {
        html += '<p>No historical data available yet.</p>';
    } else {
        html += '<div class="trends-chart"><pre>' + JSON.stringify(trends, null, 2) + '</pre></div>';
        // TODO: Replace with actual chart library like Chart.js
    }
    
    container.innerHTML = html;
}

// Map Suggestions Functions
function showSuggestionsModal() {
    document.getElementById('suggestions-modal').style.display = 'block';
    isSelectingLocationForSuggestion = true;
    
    // Update status
    if (locationStatus) {
        locationStatus.textContent = 'Click on the map to select location for your suggestion';
        locationStatus.className = 'info';
    }
}

function closeSuggestionsModal() {
    document.getElementById('suggestions-modal').style.display = 'none';
    isSelectingLocationForSuggestion = false;
    
    // Clear form
    document.getElementById('suggestion-form').reset();
    document.getElementById('suggestion-lat').value = '';
    document.getElementById('suggestion-lng').value = '';
}

// Enhanced map click handler
function handleMapClick(e) {
    const lat = e.latlng.lat.toFixed(6);
    const lng = e.latlng.lng.toFixed(6);
    
    if (isSelectingLocationForSuggestion) {
        // Handle suggestion location selection
        document.getElementById('suggestion-lat').value = lat;
        document.getElementById('suggestion-lng').value = lng;
        
        if (locationStatus) {
            locationStatus.textContent = `Location selected: ${lat}, ${lng}`;
            locationStatus.className = 'success';
        }
    } else {
        // Handle normal crop report location selection
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
        // Get current weather, forecast, and alerts in parallel
        const [weatherResponse, forecastResponse, alertsResponse] = await Promise.all([
            fetch(`/api/weather?lat=${lat}&lon=${lon}`),
            fetch(`/api/weather/forecast?lat=${lat}&lon=${lon}&days=3`),
            fetch(`/api/weather/alerts?lat=${lat}&lon=${lon}`)
        ]);
        
        const weather = await weatherResponse.json();
        const forecast = await forecastResponse.json();
        const alerts = await alertsResponse.json();
        
        // Create or update weather panel
        let weatherPanel = document.getElementById('weather-panel');
        if (!weatherPanel) {
            weatherPanel = document.createElement('div');
            weatherPanel.id = 'weather-panel';
            weatherPanel.className = 'weather-panel';
            document.body.appendChild(weatherPanel);
        }
        
        if (weather.error) {
            weatherPanel.innerHTML = `
                <div class="weather-header">
                    <h4>🌤️ Weather</h4>
                    <span class="error">No data available</span>
                </div>
            `;
            return;
        }
        
        const main = weather.main || {};
        const agricultural = weather.agricultural || {};
        const cropRecommendations = weather.crop_recommendations || {};
        const isOffline = weather.fallback;
        
        // Build alerts HTML
        let alertsHtml = '';
        if (alerts.alerts && alerts.alerts.length > 0) {
            alertsHtml = '<div class="weather-alerts">';
            alerts.alerts.forEach(alert => {
                alertsHtml += `
                    <div class="alert alert-${alert.severity}">
                        ${alert.icon} ${alert.message}
                    </div>
                `;
            });
            alertsHtml += '</div>';
        }
        
        // Build crop recommendations HTML
        let cropHtml = '<div class="crop-recommendations">';
        for (const [crop, status] of Object.entries(cropRecommendations)) {
            const statusIcon = getStatusIcon(status);
            const statusText = getStatusText(status);
            cropHtml += `
                <div class="crop-status">
                    <span class="crop-name">${crop.charAt(0).toUpperCase() + crop.slice(1)}:</span>
                    <span class="status ${status}">${statusIcon} ${statusText}</span>
                </div>
            `;
        }
        cropHtml += '</div>';
        
        // Build agricultural metrics HTML
        const agriMetrics = `
            <div class="agricultural-metrics">
                <div class="metric">
                    <span class="metric-label">Growing Degree Days:</span>
                    <span class="metric-value">${agricultural.growing_degree_days?.toFixed(1) || 'N/A'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Heat Stress Risk:</span>
                    <span class="metric-value risk-${agricultural.heat_stress_risk}">${agricultural.heat_stress_risk || 'unknown'}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Irrigation Need:</span>
                    <span class="metric-value need-${agricultural.irrigation_need}">${agricultural.irrigation_need || 'unknown'}</span>
                </div>
            </div>
        `;
        
        // Forecast summary
        let forecastHtml = '';
        if (forecast.agricultural_summary) {
            const summary = forecast.agricultural_summary;
            forecastHtml = `
                <div class="forecast-summary">
                    <h5>3-Day Outlook</h5>
                    <div class="forecast-metrics">
                        <div class="forecast-metric">
                            <span>Avg Temp:</span> ${summary.avg_temp}°C
                        </div>
                        <div class="forecast-metric">
                            <span>Total Rain:</span> ${summary.total_rainfall?.toFixed(1) || 0}mm
                        </div>
                        <div class="forecast-metric">
                            <span>Optimal Days:</span> ${summary.optimal_days || 0}/24
                        </div>
                    </div>
                </div>
            `;
        }
        
        weatherPanel.innerHTML = `
            <div class="weather-header">
                <h4>🌤️ Weather ${isOffline ? '(Offline Mode)' : ''}</h4>
                <button class="close-weather" onclick="closeWeatherPanel()">×</button>
            </div>
            
            ${alertsHtml}
            
            <div class="current-weather">
                <div class="main-stats">
                    <div class="temp-display">
                        <span class="temperature">${main.temp?.toFixed(1) || 'N/A'}°C</span>
                        <span class="feels-like">Feels like ${main.feels_like?.toFixed(1) || 'N/A'}°C</span>
                    </div>
                    <div class="weather-details">
                        <div class="detail-item">
                            <span class="icon">💧</span>
                            <span>Humidity: ${main.humidity || 'N/A'}%</span>
                        </div>
                        <div class="detail-item">
                            <span class="icon">💨</span>
                            <span>Wind: ${weather.wind?.speed?.toFixed(1) || 'N/A'} m/s</span>
                        </div>
                        <div class="detail-item">
                            <span class="icon">📊</span>
                            <span>Pressure: ${main.pressure || 'N/A'} hPa</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="agricultural-info">
                <h5>🌾 Agricultural Conditions</h5>
                ${agriMetrics}
                ${cropHtml}
            </div>
            
            ${forecastHtml}
            
            <div class="weather-actions">
                <button onclick="showDetailedForecast(${lat}, ${lon})" class="btn-secondary">
                    📈 Detailed Forecast
                </button>
                <button onclick="refreshWeather(${lat}, ${lon})" class="btn-primary">
                    🔄 Refresh
                </button>
            </div>
        `;
        
    } catch (error) {
        console.error("Weather display error:", error);
        let weatherPanel = document.getElementById('weather-panel');
        if (weatherPanel) {
            weatherPanel.innerHTML = `
                <div class="weather-header">
                    <h4>🌤️ Weather</h4>
                    <span class="error">Connection error</span>
                </div>
            `;
        }
    }
}

function getStatusIcon(status) {
    const icons = {
        'excellent_conditions': '✅',
        'favorable_conditions': '✅',
        'ideal_conditions': '✅',
        'optimal_growth': '✅',
        'heat_stress_risk': '⚠️',
        'heat_stress': '🔥',
        'heat_protection_needed': '🔥',
        'too_cold': '❄️',
        'frost_risk': '🧊',
        'monitor_conditions': '👁️',
        'monitor_humidity': '👁️',
        'monitor_temperature': '👁️',
        'acceptable_conditions': '👌'
    };
    return icons[status] || '📊';
}

function getStatusText(status) {
    const texts = {
        'excellent_conditions': 'Excellent',
        'favorable_conditions': 'Favorable',
        'ideal_conditions': 'Ideal',
        'optimal_growth': 'Optimal',
        'heat_stress_risk': 'Heat Risk',
        'heat_stress': 'Heat Stress',
        'heat_protection_needed': 'Need Protection',
        'too_cold': 'Too Cold',
        'frost_risk': 'Frost Risk',
        'monitor_conditions': 'Monitor',
        'monitor_humidity': 'Monitor Humidity',
        'monitor_temperature': 'Monitor Temp',
        'acceptable_conditions': 'Acceptable'
    };
    return texts[status] || status.replace(/_/g, ' ');
}

function closeWeatherPanel() {
    const weatherPanel = document.getElementById('weather-panel');
    if (weatherPanel) {
        weatherPanel.remove();
    }
}

function refreshWeather(lat, lon) {
    displayWeatherForLocation(lat, lon);
}

async function showDetailedForecast(lat, lon) {
    try {
        const response = await fetch(`/api/weather/forecast?lat=${lat}&lon=${lon}&days=7`);
        const forecast = await response.json();
        
        if (forecast.error) {
            alert('Forecast data unavailable');
            return;
        }
        
        // Create detailed forecast modal
        const modal = document.createElement('div');
        modal.className = 'modal forecast-modal';
        modal.id = 'forecast-modal';
        
        let forecastHtml = '<div class="forecast-days">';
        if (forecast.list) {
            // Group by days
            const days = {};
            forecast.list.forEach(item => {
                const date = new Date(item.dt * 1000);
                const dayKey = date.toDateString();
                if (!days[dayKey]) {
                    days[dayKey] = [];
                }
                days[dayKey].push(item);
            });
            
            Object.entries(days).slice(0, 7).forEach(([day, entries]) => {
                const dayTemps = entries.map(e => e.main.temp);
                const minTemp = Math.min(...dayTemps);
                const maxTemp = Math.max(...dayTemps);
                const avgHumidity = entries.reduce((sum, e) => sum + e.main.humidity, 0) / entries.length;
                
                forecastHtml += `
                    <div class="forecast-day">
                        <div class="day-header">
                            <h6>${new Date(day).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</h6>
                        </div>
                        <div class="day-temps">
                            <span class="max-temp">${maxTemp.toFixed(1)}°</span>
                            <span class="min-temp">${minTemp.toFixed(1)}°</span>
                        </div>
                        <div class="day-details">
                            <span>💧 ${avgHumidity.toFixed(0)}%</span>
                        </div>
                    </div>
                `;
            });
        }
        forecastHtml += '</div>';
        
        // Add planting advice
        let adviceHtml = '';
        if (forecast.planting_advice && forecast.planting_advice.length > 0) {
            adviceHtml = '<div class="planting-advice"><h6>🌱 Planting Advice</h6>';
            forecast.planting_advice.forEach(advice => {
                adviceHtml += `<div class="advice-item">${advice}</div>`;
            });
            adviceHtml += '</div>';
        }
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h4>📈 7-Day Weather Forecast</h4>
                    <button class="close-modal" onclick="closeForecastModal()">×</button>
                </div>
                <div class="modal-body">
                    ${forecastHtml}
                    ${adviceHtml}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
    } catch (error) {
        console.error('Forecast error:', error);
        alert('Failed to load detailed forecast');
    }
}

function closeForecastModal() {
    const modal = document.getElementById('forecast-modal');
    if (modal) {
        modal.remove();
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

// Handle suggestion form submission
document.addEventListener('DOMContentLoaded', function() {
    const suggestionForm = document.getElementById('suggestion-form');
    if (suggestionForm) {
        suggestionForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = {
                suggestion_type: document.getElementById('suggestion-type').value,
                name: document.getElementById('suggestion-name').value,
                latitude: document.getElementById('suggestion-lat').value,
                longitude: document.getElementById('suggestion-lng').value
            };
            
            try {
                const response = await fetch('/api/map-suggestions', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    
                    if (locationStatus) {
                        locationStatus.textContent = 'Suggestion submitted successfully!';
                        locationStatus.className = 'success';
                        setTimeout(() => { locationStatus.textContent = ''; }, 3000);
                    }
                    
                    closeSuggestionsModal();
                } else {
                    throw new Error('Failed to submit suggestion');
                }
            } catch (error) {
                console.error('Error submitting suggestion:', error);
                
                if (locationStatus) {
                    locationStatus.textContent = 'Error submitting suggestion';
                    locationStatus.className = 'error';
                    setTimeout(() => { locationStatus.textContent = ''; }, 3000);
                }
            }
        });
    }
});

// Auto-locate user on startup
async function autoLocateUser() {
    try {
        // Try to get location from IP
        const response = await fetch('/api/location-from-ip');
        const location = await response.json();
        
        if (location.latitude && location.longitude) {
            map.setView([location.latitude, location.longitude], 10);
            
            // Add user location marker
            if (userMarker) {
                map.removeLayer(userMarker);
            }
            
            userMarker = L.marker([location.latitude, location.longitude], {
                icon: L.icon({
                    iconUrl: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="blue"><circle cx="12" cy="12" r="8"/></svg>',
                    iconSize: [16, 16],
                    iconAnchor: [8, 8]
                })
            }).addTo(map);
            
            userMarker.bindPopup(`Your approximate location: ${location.city}, ${location.country}`);
            
            if (locationStatus) {
                locationStatus.textContent = `Located: ${location.city}, ${location.country}`;
                locationStatus.className = 'success';
                setTimeout(() => { locationStatus.textContent = ''; }, 3000);
            }
        }
    } catch (error) {
        console.error('Error getting user location:', error);
        
        // Try browser geolocation as fallback
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    map.setView([lat, lng], 12);
                    
                    if (userMarker) {
                        map.removeLayer(userMarker);
                    }
                    
                    userMarker = L.marker([lat, lng], {
                        icon: L.icon({
                            iconUrl: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="blue"><circle cx="12" cy="12" r="8"/></svg>',
                            iconSize: [16, 16],
                            iconAnchor: [8, 8]
                        })
                    }).addTo(map);
                    
                    userMarker.bindPopup('Your current location');
                    
                    if (locationStatus) {
                        locationStatus.textContent = `Located using GPS: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
                        locationStatus.className = 'success';
                        setTimeout(() => { locationStatus.textContent = ''; }, 3000);
                    }
                },
                function(error) {
                    console.log('Geolocation error:', error);
                    if (locationStatus) {
                        locationStatus.textContent = 'Could not determine location';
                        locationStatus.className = 'warning';
                        setTimeout(() => { locationStatus.textContent = ''; }, 3000);
                    }
                }
            );
        }
    }
}

// Function to handle map clicks
function handleMapClick(e) {
    const lat = e.latlng.lat.toFixed(6);
    const lng = e.latlng.lng.toFixed(6);
    
    if (isSelectingLocationForSuggestion) {
        // Handle suggestion location selection
        document.getElementById('suggestion-lat').value = lat;
        document.getElementById('suggestion-lng').value = lng;
        
        if (locationStatus) {
            locationStatus.textContent = `Location selected: ${lat}, ${lng}`;
            locationStatus.className = 'success';
        }
    } else {
        // Handle normal crop report location selection
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
}

// Market Analysis Functions
async function showMarketAnalysisModal() {
    document.getElementById('market-modal').style.display = 'block';
    showMarketTab('overview');
    await loadCropAnalysis();
    await loadPlantingRecommendations();
}

function closeMarketAnalysisModal() {
    document.getElementById('market-modal').style.display = 'none';
}

function showMarketTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(`market-${tabName}`).classList.add('active');
    event.target.classList.add('active');
    
    // Load content based on tab
    if (tabName === 'regional') {
        loadRegionalAnalysis();
    }
}

async function loadCropAnalysis() {
    const cropSelect = document.getElementById('analysis-crop-select');
    const selectedCrop = cropSelect.value;
    const resultsContainer = document.getElementById('market-analysis-results');
    
    try {
        resultsContainer.innerHTML = '<div class="loading">Loading market analysis...</div>';
        
        const response = await fetch(`/api/market-analysis/${selectedCrop}`);
        const analysis = await response.json();
        
        if (analysis.error) {
            resultsContainer.innerHTML = `<div class="error">Error: ${analysis.error}</div>`;
            return;
        }
        
        displayMarketAnalysis(analysis);
        
    } catch (error) {
        console.error('Error loading market analysis:', error);
        resultsContainer.innerHTML = '<div class="error">Failed to load market analysis</div>';
    }
}

function displayMarketAnalysis(analysis) {
    const container = document.getElementById('market-analysis-results');
    
    const riskColor = {
        'low': '#28a745',
        'medium': '#ffc107', 
        'high': '#dc3545'
    }[analysis.risk_assessment] || '#6c757d';
    
    const recommendationColor = {
        'recommended': '#28a745',
        'consider': '#17a2b8',
        'caution': '#ffc107',
        'avoid': '#dc3545'
    }[analysis.market_recommendation] || '#6c757d';
    
    const trendIcon = {
        'increasing': '📈',
        'decreasing': '📉',
        'stable': '➡️'
    }[analysis.price_trend] || '❓';
    
    container.innerHTML = `
        <div class="analysis-grid">
            <div class="analysis-card">
                <h4>📊 Market Overview</h4>
                <p><strong>Crop:</strong> ${analysis.crop_type.charAt(0).toUpperCase() + analysis.crop_type.slice(1)}</p>
                <p><strong>Total Planted Area:</strong> ${analysis.total_planted_area} ha</p>
                <p><strong>Number of Farms:</strong> ${analysis.number_of_farms}</p>
                <p><strong>Current Price:</strong> ${analysis.current_price} UZS/kg</p>
            </div>
            
            <div class="analysis-card">
                <h4>📈 Price & Trends</h4>
                <p><strong>Price Trend:</strong> ${trendIcon} ${analysis.price_trend}</p>
                <p><strong>Supply Score:</strong> ${analysis.supply_score}/100</p>
                <p><strong>Market Saturation:</strong> ${analysis.saturation_level}</p>
            </div>
            
            <div class="analysis-card" style="border-left: 4px solid ${recommendationColor}">
                <h4>💡 Recommendation</h4>
                <p class="recommendation" style="color: ${recommendationColor}">
                    <strong>${analysis.market_recommendation.toUpperCase()}</strong>
                </p>
                <p class="risk-level" style="color: ${riskColor}">
                    Risk Level: <strong>${analysis.risk_assessment.toUpperCase()}</strong>
                </p>
            </div>
        </div>
        
        <div class="detailed-analysis">
            <h4>🔍 Detailed Analysis</h4>
            <div class="progress-bars">
                <div class="progress-item">
                    <label>Supply Level</label>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${analysis.supply_score}%; background-color: ${analysis.supply_score > 70 ? '#dc3545' : analysis.supply_score > 50 ? '#ffc107' : '#28a745'}"></div>
                    </div>
                    <span>${analysis.supply_score}%</span>
                </div>
            </div>
        </div>
    `;
}

async function loadPlantingRecommendations() {
    try {
        const response = await fetch('/api/planting-recommendations');
        const data = await response.json();
        
        displayPlantingRecommendations(data.recommendations);
        
    } catch (error) {
        console.error('Error loading recommendations:', error);
        document.getElementById('planting-recommendations').innerHTML = 
            '<div class="error">Failed to load recommendations</div>';
    }
}

function displayPlantingRecommendations(recommendations) {
    const container = document.getElementById('planting-recommendations');
    
    let html = '<h3>🌱 Planting Recommendations</h3>';
    html += '<div class="recommendations-list">';
    
    recommendations.forEach((rec, index) => {
        const scoreColor = rec.opportunity_score > 70 ? '#28a745' : 
                          rec.opportunity_score > 50 ? '#ffc107' : '#dc3545';
        
        const rankEmoji = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '📍';
        
        html += `
            <div class="recommendation-card" style="border-left: 4px solid ${scoreColor}">
                <div class="rec-header">
                    <h4>${rankEmoji} ${rec.crop_type.charAt(0).toUpperCase() + rec.crop_type.slice(1)}</h4>
                    <div class="opportunity-score" style="background-color: ${scoreColor}">
                        ${rec.opportunity_score}/100
                    </div>
                </div>
                <p class="recommendation-text"><strong>${rec.recommendation.toUpperCase()}</strong></p>
                <p class="reasoning">${rec.reasoning}</p>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

async function loadRegionalAnalysis() {
    try {
        const response = await fetch('/api/regional-analysis');
        const data = await response.json();
        
        displayRegionalAnalysis(data.regions);
        
    } catch (error) {
        console.error('Error loading regional analysis:', error);
        document.getElementById('regional-analysis').innerHTML = 
            '<div class="error">Failed to load regional analysis</div>';
    }
}

function displayRegionalAnalysis(regions) {
    const container = document.getElementById('regional-analysis');
    
    if (!regions || regions.length === 0) {
        container.innerHTML = '<p>No regional data available yet. More data needed for analysis.</p>';
        return;
    }
    
    let html = '<h3>🗺️ Regional Crop Distribution</h3>';
    html += '<div class="regional-grid">';
    
    regions.forEach(region => {
        const totalFarms = Object.values(region.crops).reduce((sum, crop) => sum + crop.farm_count, 0);
        const totalArea = Object.values(region.crops).reduce((sum, crop) => sum + crop.total_area, 0);
        
        html += `
            <div class="region-card">
                <h5>📍 Region ${region.latitude.toFixed(1)}, ${region.longitude.toFixed(1)}</h5>
                <p><strong>Total Farms:</strong> ${totalFarms}</p>
                <p><strong>Total Area:</strong> ${totalArea.toFixed(1)} ha</p>
                <div class="crop-breakdown">
                    <h6>Crops:</h6>
        `;
        
        Object.entries(region.crops).forEach(([crop, data]) => {
            html += `
                <div class="crop-item">
                    <span class="crop-name">${crop}:</span>
                    <span class="crop-stats">${data.farm_count} farms, ${data.total_area.toFixed(1)} ha</span>
                </div>
            `;
        });
        
        html += '</div></div>';
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Price prediction for specific field
async function getPricePrediction(cropType, plantingDate, fieldSize) {
    try {
        const params = new URLSearchParams({
            crop_type: cropType,
            planting_date: plantingDate,
            field_size: fieldSize
        });
        
        const response = await fetch(`/api/harvest-price-prediction?${params}`);
        const prediction = await response.json();
        
        return prediction;
    } catch (error) {
        console.error('Error getting price prediction:', error);
        return null;
    }
}

// Mobile optimization and touch handling
function initializeMobileControls() {
    // Create mobile controls if on mobile device
    if (window.innerWidth <= 768) {
        createMobileControls();
        createMobileToggle();
    }
    
    // Handle window resize
    window.addEventListener('resize', () => {
        if (window.innerWidth <= 768) {
            if (!document.getElementById('mobile-controls')) {
                createMobileControls();
            }
            if (!document.getElementById('mobile-toggle')) {
                createMobileToggle();
            }
        } else {
            removeMobileControls();
            removeMobileToggle();
        }
    });
}

function createMobileToggle() {
    if (document.getElementById('mobile-toggle')) return;
    
    const toggle = document.createElement('button');
    toggle.id = 'mobile-toggle';
    toggle.className = 'mobile-toggle';
    toggle.innerHTML = '☰';
    toggle.addEventListener('click', toggleSidebar);
    document.body.appendChild(toggle);
}

function removeMobileToggle() {
    const toggle = document.getElementById('mobile-toggle');
    if (toggle) toggle.remove();
}

function createMobileControls() {
    if (document.getElementById('mobile-controls')) return;
    
    const controls = document.createElement('div');
    controls.id = 'mobile-controls';
    controls.className = 'mobile-controls';
    
    const controlButtons = [
        {
            id: 'mobile-map',
            icon: '🗺️',
            label: 'Map',
            action: () => scrollToElement('map-container')
        },
        {
            id: 'mobile-weather',
            icon: '🌤️',
            label: 'Weather',
            action: () => {
                if (currentLocation) {
                    displayWeatherForLocation(currentLocation.lat, currentLocation.lng);
                } else {
                    showMessage('Location not available', 'error');
                }
            }
        },
        {
            id: 'mobile-report',
            icon: '📝',
            label: 'Report',
            action: () => openCropReportModal()
        },
        {
            id: 'mobile-analysis',
            icon: '📊',
            label: 'Analysis',
            action: () => openMarketAnalysisModal()
        },
        {
            id: 'mobile-suggest',
            icon: '💡',
            label: 'Suggest',
            action: () => openMapSuggestionModal()
        }
    ];
    
    controlButtons.forEach(button => {
        const btn = document.createElement('button');
        btn.id = button.id;
        btn.className = 'mobile-control-btn';
        btn.innerHTML = `
            <span class="icon">${button.icon}</span>
            <span class="label">${button.label}</span>
        `;
        btn.addEventListener('click', button.action);
        controls.appendChild(btn);
    });
    
    document.body.appendChild(controls);
}

function removeMobileControls() {
    const controls = document.getElementById('mobile-controls');
    if (controls) controls.remove();
}

function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
}

function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

// Touch gesture handling for map
function initializeTouchHandling() {
    if (!map) return;
    
    let touchStartTime = 0;
    let touchStartPos = null;
    
    map.on('touchstart', function(e) {
        touchStartTime = Date.now();
        touchStartPos = e.latlng;
    });
    
    map.on('touchend', function(e) {
        const touchEndTime = Date.now();
        const touchDuration = touchEndTime - touchStartTime;
        
        // Quick tap (less than 300ms) - show weather
        if (touchDuration < 300 && touchStartPos) {
            const distance = map.distance(touchStartPos, e.latlng);
            if (distance < 100) { // Less than 100 meters movement
                displayWeatherForLocation(e.latlng.lat, e.latlng.lng);
            }
        }
    });
}

// Performance optimizations
function optimizePerformance() {
    // Debounce map events
    let mapMoveTimeout;
    if (map) {
        map.on('move', function() {
            clearTimeout(mapMoveTimeout);
            mapMoveTimeout = setTimeout(() => {
                updateWeatherForCurrentView();
            }, 500);
        });
    }
    
    // Lazy load images
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
    
    // Prefetch critical resources
    prefetchCriticalResources();
}

function prefetchCriticalResources() {
    // Prefetch weather data for current location
    if (currentLocation) {
        const link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = `/api/weather?lat=${currentLocation.lat}&lon=${currentLocation.lng}`;
        document.head.appendChild(link);
    }
    
    // Prefetch map tiles for current view
    if (map) {
        const bounds = map.getBounds();
        const center = bounds.getCenter();
        // Leaflet handles tile prefetching automatically
    }
}

// Progressive Web App features
function initializePWA() {
    // Register service worker
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/js/service-worker.js')
            .then(registration => {
                console.log('Service Worker registered:', registration);
            })
            .catch(error => {
                console.log('Service Worker registration failed:', error);
            });
    }
    
    // Handle install prompt
    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        showInstallButton();
    });
    
    // Handle app installation
    window.addEventListener('appinstalled', () => {
        hideInstallButton();
        showMessage('App installed successfully!', 'success');
    });
}

function showInstallButton() {
    const installBtn = document.createElement('button');
    installBtn.id = 'install-btn';
    installBtn.className = 'btn btn-secondary';
    installBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        display: flex;
        align-items: center;
        gap: 8px;
    `;
    installBtn.innerHTML = '📱 Install App';
    installBtn.addEventListener('click', installApp);
    document.body.appendChild(installBtn);
}

function hideInstallButton() {
    const installBtn = document.getElementById('install-btn');
    if (installBtn) installBtn.remove();
}

async function installApp() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === 'accepted') {
            console.log('User accepted the install prompt');
        }
        deferredPrompt = null;
        hideInstallButton();
    }
}

// Improved error handling and user feedback
function showMessage(message, type = 'info', duration = 3000) {
    const messageEl = document.createElement('div');
    messageEl.className = `message message-${type}`;
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#f44336' : type === 'success' ? '#4caf50' : '#2196f3'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        transform: translateX(100%);
        transition: transform 0.3s ease;
    `;
    messageEl.textContent = message;
    
    document.body.appendChild(messageEl);
    
    // Animate in
    setTimeout(() => {
        messageEl.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto remove
    setTimeout(() => {
        messageEl.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 300);
    }, duration);
}

// Connection status handling
function initializeConnectionStatus() {
    window.addEventListener('online', () => {
        showMessage('Connection restored', 'success');
        refreshCurrentData();
    });
    
    window.addEventListener('offline', () => {
        showMessage('Connection lost - Using offline mode', 'error', 5000);
    });
}

function refreshCurrentData() {
    // Refresh weather data if panel is open
    const weatherPanel = document.getElementById('weather-panel');
    if (weatherPanel && currentLocation) {
        displayWeatherForLocation(currentLocation.lat, currentLocation.lng);
    }
    
    // Refresh crop reports
    loadCropReports();
}

// Accessibility improvements
function initializeAccessibility() {
    // Add keyboard navigation
    document.addEventListener('keydown', (e) => {
        // ESC to close modals
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal');
            modals.forEach(modal => modal.remove());
            
            const weatherPanel = document.getElementById('weather-panel');
            if (weatherPanel) weatherPanel.remove();
        }
        
        // Tab navigation improvements
        if (e.key === 'Tab') {
            // Ensure focus stays within modals
            const activeModal = document.querySelector('.modal');
            if (activeModal) {
                const focusableElements = activeModal.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
                );
                const firstElement = focusableElements[0];
                const lastElement = focusableElements[focusableElements.length - 1];
                
                if (e.shiftKey && document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                } else if (!e.shiftKey && document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        }
    });
    
    // Add ARIA labels
    const mapContainer = document.getElementById('map-container');
    if (mapContainer) {
        mapContainer.setAttribute('aria-label', 'Interactive map of Uzbekistan showing crop data');
        mapContainer.setAttribute('role', 'application');
    }
    
    // Announce important changes to screen readers
    const announcer = document.createElement('div');
    announcer.setAttribute('aria-live', 'polite');
    announcer.setAttribute('aria-atomic', 'true');
    announcer.style.cssText = 'position: absolute; left: -10000px; width: 1px; height: 1px; overflow: hidden;';
    document.body.appendChild(announcer);
    
    window.announceToScreenReader = function(message) {
        announcer.textContent = message;
        setTimeout(() => {
            announcer.textContent = '';
        }, 1000);
    };
}

// Initialize all mobile and performance features
function initializeMobileAndPerformance() {
    initializeMobileControls();
    initializeTouchHandling();
    optimizePerformance();
    initializePWA();
    initializeConnectionStatus();
    initializeAccessibility();
}

// Analytics and Advanced Planning Classes

class AnalyticsDashboard {
    constructor() {
        this.currentData = null;
        this.lastUpdated = null;
    }
    
    async showDashboard() {
        const modal = this.createDashboardModal();
        document.body.appendChild(modal);
        await this.loadDashboardData();
    }
    
    createDashboardModal() {
        const modal = document.createElement('div');
        modal.className = 'modal large-modal analytics-modal';
        modal.id = 'analytics-modal';
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>📊 Analytics Dashboard</h3>
                    <div class="header-actions">
                        <button onclick="analyticsService.exportData('json')" class="btn-secondary">
                            📄 Export JSON
                        </button>
                        <button onclick="analyticsService.exportData('csv')" class="btn-secondary">
                            📈 Export CSV
                        </button>
                        <button onclick="analyticsService.refreshDashboard()" class="btn-primary">
                            🔄 Refresh
                        </button>
                        <button onclick="analyticsService.closeDashboard()" class="close-modal">×</button>
                    </div>
                </div>
                
                <div class="modal-body">
                    <div class="analytics-tabs">
                        <button class="tab-button active" onclick="analyticsService.showTab('overview')">
                            📊 Overview
                        </button>
                        <button class="tab-button" onclick="analyticsService.showTab('diversity')">
                            🌾 Crop Diversity
                        </button>
                        <button class="tab-button" onclick="analyticsService.showTab('trends')">
                            📈 Temporal Trends
                        </button>
                        <button class="tab-button" onclick="analyticsService.showTab('sustainability')">
                            🌱 Sustainability
                        </button>
                    </div>
                    
                    <div class="tab-content active" id="analytics-overview">
                        <div id="overview-metrics" class="loading">Loading overview...</div>
                    </div>
                    
                    <div class="tab-content" id="analytics-diversity">
                        <div id="diversity-analysis" class="loading">Loading diversity analysis...</div>
                    </div>
                    
                    <div class="tab-content" id="analytics-trends">
                        <div class="trends-controls">
                            <label for="trends-months">Analysis Period:</label>
                            <select id="trends-months" onchange="analyticsService.loadTrends()">
                                <option value="6">6 Months</option>
                                <option value="12" selected>12 Months</option>
                                <option value="24">24 Months</option>
                            </select>
                            <label for="trends-crop">Crop Filter:</label>
                            <select id="trends-crop" onchange="analyticsService.loadTrends()">
                                <option value="">All Crops</option>
                                <option value="wheat">Wheat</option>
                                <option value="cotton">Cotton</option>
                                <option value="potato">Potato</option>
                                <option value="corn">Corn</option>
                                <option value="rice">Rice</option>
                            </select>
                        </div>
                        <div id="trends-analysis" class="loading">Loading trends...</div>
                    </div>
                    
                    <div class="tab-content" id="analytics-sustainability">
                        <div id="sustainability-metrics" class="loading">Loading sustainability metrics...</div>
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }
    
    async loadDashboardData() {
        try {
            const response = await fetch('/api/analytics/dashboard');
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            this.currentData = data;
            this.lastUpdated = new Date();
            
            this.displayOverview(data);
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            document.getElementById('overview-metrics').innerHTML = 
                `<div class="error">Error loading data: ${error.message}</div>`;
        }
    }
    
    displayOverview(data) {
        const container = document.getElementById('overview-metrics');
        const stats = data.basic_statistics;
        
        container.innerHTML = `
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-icon">🌾</div>
                    <div class="metric-value">${stats.total_reports}</div>
                    <div class="metric-label">Total Reports</div>
                </div>
                <div class="metric-card">
                    <div class="metric-icon">📏</div>
                    <div class="metric-value">${stats.total_area.toFixed(1)}</div>
                    <div class="metric-label">Total Area (ha)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-icon">🌱</div>
                    <div class="metric-value">${stats.unique_crops}</div>
                    <div class="metric-label">Crop Types</div>
                </div>
                <div class="metric-card">
                    <div class="metric-icon">📊</div>
                    <div class="metric-value">${stats.average_field_size.toFixed(1)}</div>
                    <div class="metric-label">Avg Field Size (ha)</div>
                </div>
            </div>
            
            <div class="analysis-grid">
                <div class="analysis-section">
                    <h4>🏆 Top Crops by Area</h4>
                    <div class="crop-ranking">
                        ${stats.crop_distribution.map((crop, idx) => `
                            <div class="crop-rank-item">
                                <span class="rank">#${idx + 1}</span>
                                <span class="crop-name">${crop.crop_type}</span>
                                <span class="crop-area">${crop.total_area.toFixed(1)} ha</span>
                                <div class="crop-bar">
                                    <div class="crop-bar-fill" style="width: ${(crop.total_area / stats.crop_distribution[0].total_area) * 100}%"></div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="analysis-section">
                    <h4>📈 Key Insights</h4>
                    <div class="insights-list">
                        <div class="insight-item">
                            <span class="insight-icon">🎯</span>
                            <span>Market readiness score: ${data.market_readiness?.score || 'N/A'}</span>
                        </div>
                        <div class="insight-item">
                            <span class="insight-icon">🌿</span>
                            <span>Sustainability score: ${data.sustainability_metrics?.score || 'N/A'}</span>
                        </div>
                        <div class="insight-item">
                            <span class="insight-icon">⚡</span>
                            <span>Data freshness: ${this.getDataFreshness()}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    async loadDiversityAnalysis() {
        try {
            const response = await fetch('/api/analytics/crop-diversity');
            const data = await response.json();
            
            this.displayDiversityAnalysis(data.diversity_analysis);
            
        } catch (error) {
            console.error('Error loading diversity analysis:', error);
            document.getElementById('diversity-analysis').innerHTML = 
                `<div class="error">Error loading diversity data: ${error.message}</div>`;
        }
    }
    
    displayDiversityAnalysis(diversity) {
        const container = document.getElementById('diversity-analysis');
        
        container.innerHTML = `
            <div class="diversity-metrics">
                <div class="diversity-score">
                    <h4>Shannon Diversity Index</h4>
                    <div class="score-display">
                        <span class="score-value">${diversity.diversity_index}</span>
                        <span class="score-label">Higher is better</span>
                    </div>
                </div>
                
                <div class="concentration-metrics">
                    <h4>Concentration Analysis</h4>
                    <div class="concentration-grid">
                        ${Object.entries(diversity.concentration_metrics).map(([key, value]) => `
                            <div class="concentration-item">
                                <span class="metric-name">${key.replace('_', ' ')}</span>
                                <span class="metric-value">${typeof value === 'number' ? value.toFixed(3) : value}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
            
            <div class="diversity-distribution">
                <h4>Crop Distribution Details</h4>
                <div class="distribution-chart">
                    ${diversity.area_distribution.map(crop => `
                        <div class="crop-distribution-item">
                            <div class="crop-info">
                                <span class="crop-name">${crop.crop_type}</span>
                                <span class="crop-stats">${crop.total_area.toFixed(1)} ha (${crop.count} fields)</span>
                            </div>
                            <div class="area-bar">
                                <div class="area-fill" style="width: ${(crop.total_area / diversity.area_distribution[0].total_area) * 100}%"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    async loadTrends() {
        const months = document.getElementById('trends-months').value;
        const cropFilter = document.getElementById('trends-crop').value;
        
        try {
            let url = `/api/analytics/temporal-trends?months=${months}`;
            if (cropFilter) {
                url += `&crop_type=${cropFilter}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            this.displayTrends(data.temporal_trends);
            
        } catch (error) {
            console.error('Error loading trends:', error);
            document.getElementById('trends-analysis').innerHTML = 
                `<div class="error">Error loading trends: ${error.message}</div>`;
        }
    }
    
    displayTrends(trends) {
        const container = document.getElementById('trends-analysis');
        
        container.innerHTML = `
            <div class="trends-overview">
                <div class="trend-metric">
                    <h4>Monthly Growth Rate</h4>
                    <div class="growth-rate ${trends.growth_rate >= 0 ? 'positive' : 'negative'}">
                        ${trends.growth_rate >= 0 ? '📈' : '📉'} ${trends.growth_rate.toFixed(1)}%
                    </div>
                </div>
                
                <div class="trend-metric">
                    <h4>Peak Season</h4>
                    <div class="peak-season">
                        🌟 ${trends.peak_season || 'N/A'}
                    </div>
                </div>
            </div>
            
            <div class="monthly-breakdown">
                <h4>Monthly Activity</h4>
                <div class="month-chart">
                    ${Object.entries(trends.monthly_distribution || {}).map(([month, count]) => `
                        <div class="month-bar">
                            <div class="month-fill" style="height: ${(count / Math.max(...Object.values(trends.monthly_distribution))) * 100}%"></div>
                            <div class="month-label">${month.substring(0, 3)}</div>
                            <div class="month-count">${count}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="seasonal-analysis">
                <h4>Seasonal Patterns</h4>
                <div class="seasonal-grid">
                    ${Object.entries(trends.seasonal_patterns || {}).map(([season, data]) => `
                        <div class="seasonal-item">
                            <h5>${season}</h5>
                            <p>Reports: ${data.count || 0}</p>
                            <p>Area: ${(data.total_area || 0).toFixed(1)} ha</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    showTab(tabName) {
        // Hide all tabs
        document.querySelectorAll('.analytics-modal .tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.analytics-modal .tab-button').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Show selected tab
        document.getElementById(`analytics-${tabName}`).classList.add('active');
        event.target.classList.add('active');
        
        // Load content based on tab
        switch(tabName) {
            case 'diversity':
                this.loadDiversityAnalysis();
                break;
            case 'trends':
                this.loadTrends();
                break;
            case 'sustainability':
                this.loadSustainabilityMetrics();
                break;
        }
    }
    
    async loadSustainabilityMetrics() {
        // Use existing data if available
        if (this.currentData && this.currentData.sustainability_metrics) {
            this.displaySustainabilityMetrics(this.currentData.sustainability_metrics);
            return;
        }
        
        // Otherwise load fresh data
        try {
            const response = await fetch('/api/analytics/dashboard');
            const data = await response.json();
            this.displaySustainabilityMetrics(data.sustainability_metrics);
        } catch (error) {
            document.getElementById('sustainability-metrics').innerHTML = 
                `<div class="error">Error loading sustainability data: ${error.message}</div>`;
        }
    }
    
    displaySustainabilityMetrics(metrics) {
        const container = document.getElementById('sustainability-metrics');
        
        container.innerHTML = `
            <div class="sustainability-overview">
                <div class="sustainability-score">
                    <h4>Overall Sustainability Score</h4>
                    <div class="score-circle ${this.getScoreClass(metrics.score)}">
                        <span class="score-number">${metrics.score}</span>
                        <span class="score-max">/100</span>
                    </div>
                </div>
            </div>
            
            <div class="sustainability-factors">
                <h4>Sustainability Factors</h4>
                <div class="factors-grid">
                    ${metrics.factors ? Object.entries(metrics.factors).map(([factor, value]) => `
                        <div class="factor-item">
                            <div class="factor-name">${factor.replace('_', ' ')}</div>
                            <div class="factor-value">${typeof value === 'number' ? value.toFixed(1) : value}</div>
                        </div>
                    `).join('') : '<p>No detailed factors available</p>'}
                </div>
            </div>
            
            <div class="recommendations">
                <h4>Sustainability Recommendations</h4>
                <div class="recommendations-list">
                    ${metrics.recommendations ? metrics.recommendations.map(rec => `
                        <div class="recommendation-item">
                            <span class="rec-icon">💡</span>
                            <span class="rec-text">${rec}</span>
                        </div>
                    `).join('') : '<p>No specific recommendations available</p>'}
                </div>
            </div>
        `;
    }
    
    getScoreClass(score) {
        if (score >= 80) return 'excellent';
        if (score >= 60) return 'good';
        if (score >= 40) return 'fair';
        return 'poor';
    }
    
    getDataFreshness() {
        if (!this.lastUpdated) return 'Unknown';
        
        const now = new Date();
        const diff = now - this.lastUpdated;
        const minutes = Math.floor(diff / (1000 * 60));
        
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes} min ago`;
        
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        
        const days = Math.floor(hours / 24);
        return `${days} day${days > 1 ? 's' : ''} ago`;
    }
    
    async refreshDashboard() {
        const buttons = document.querySelectorAll('.analytics-modal .btn-primary, .analytics-modal .btn-secondary');
        buttons.forEach(btn => btn.disabled = true);
        
        try {
            await this.loadDashboardData();
            
            // Reload current tab content
            const activeTab = document.querySelector('.analytics-modal .tab-button.active');
            if (activeTab) {
                const tabName = activeTab.textContent.toLowerCase().split(' ')[1]; // Extract tab name
                if (tabName !== 'overview') {
                    this.showTab(tabName);
                }
            }
        } finally {
            buttons.forEach(btn => btn.disabled = false);
        }
    }
    
    async exportData(format) {
        try {
            const response = await fetch(`/api/analytics/export?format=${format}&include_raw=true`);
            
            if (format === 'csv') {
                const csvData = await response.text();
                this.downloadFile(csvData, `agromap_analytics_${new Date().toISOString().split('T')[0]}.csv`, 'text/csv');
            } else {
                const jsonData = await response.json();
                this.downloadFile(JSON.stringify(jsonData.data, null, 2), `agromap_analytics_${new Date().toISOString().split('T')[0]}.json`, 'application/json');
            }
        } catch (error) {
            console.error('Export error:', error);
            alert('Failed to export data: ' + error.message);
        }
    }
    
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }
    
    closeDashboard() {
        const modal = document.getElementById('analytics-modal');
        if (modal) {
            modal.remove();
        }
    }
}

class CropRotationPlanner {
    constructor() {
        this.currentPlan = null;
        this.availableCrops = null;
    }
    
    async showPlanner() {
        const modal = this.createPlannerModal();
        document.body.appendChild(modal);
        await this.loadAvailableCrops();
        this.setupLocationSelector();
    }
    
    createPlannerModal() {
        const modal = document.createElement('div');
        modal.className = 'modal large-modal rotation-modal';
        modal.id = 'rotation-modal';
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>🔄 Crop Rotation Planner</h3>
                    <div class="header-actions">
                        <button onclick="rotationPlanner.exportPlan('json')" class="btn-secondary" disabled id="export-json-btn">
                            📄 Export JSON
                        </button>
                        <button onclick="rotationPlanner.exportPlan('csv')" class="btn-secondary" disabled id="export-csv-btn">
                            📈 Export CSV
                        </button>
                        <button onclick="rotationPlanner.closePlanner()" class="close-modal">×</button>
                    </div>
                </div>
                
                <div class="modal-body">
                    <div class="planner-wizard">
                        <div class="wizard-steps">
                            <div class="wizard-step active" data-step="1">
                                <span class="step-number">1</span>
                                <span class="step-label">Location & Size</span>
                            </div>
                            <div class="wizard-step" data-step="2">
                                <span class="step-number">2</span>
                                <span class="step-label">Preferences</span>
                            </div>
                            <div class="wizard-step" data-step="3">
                                <span class="step-number">3</span>
                                <span class="step-label">Plan Review</span>
                            </div>
                        </div>
                        
                        <div class="wizard-content">
                            <div class="wizard-panel active" id="step-1">
                                <h4>Field Location and Size</h4>
                                <div class="form-grid">
                                    <div class="form-group">
                                        <label for="rotation-lat">Latitude:</label>
                                        <input type="number" id="rotation-lat" step="0.000001" placeholder="Click map to select">
                                    </div>
                                    <div class="form-group">
                                        <label for="rotation-lng">Longitude:</label>
                                        <input type="number" id="rotation-lng" step="0.000001" placeholder="Click map to select">
                                    </div>
                                    <div class="form-group">
                                        <label for="rotation-field-size">Field Size (hectares):</label>
                                        <input type="number" id="rotation-field-size" step="0.1" min="0.1" value="1.0">
                                    </div>
                                    <div class="form-group">
                                        <label for="rotation-years">Planning Period (years):</label>
                                        <select id="rotation-years">
                                            <option value="2">2 Years</option>
                                            <option value="3" selected>3 Years</option>
                                            <option value="4">4 Years</option>
                                            <option value="5">5 Years</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="location-selector">
                                    <button onclick="rotationPlanner.enableLocationPicking()" class="btn-secondary">
                                        📍 Select Location on Map
                                    </button>
                                    <span id="location-status" class="location-status"></span>
                                </div>
                            </div>
                            
                            <div class="wizard-panel" id="step-2">
                                <h4>Crop Preferences</h4>
                                <div class="preferences-grid">
                                    <div class="preference-section">
                                        <h5>Preferred Crops (optional)</h5>
                                        <div id="preferred-crops" class="crop-checkboxes">
                                            <!-- Will be populated dynamically -->
                                        </div>
                                    </div>
                                    <div class="preference-section">
                                        <h5>Crops to Avoid (optional)</h5>
                                        <div id="avoid-crops" class="crop-checkboxes">
                                            <!-- Will be populated dynamically -->
                                        </div>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="wizard-panel" id="step-3">
                                <div id="rotation-plan-display">
                                    <div class="loading">Click "Generate Plan" to create your rotation plan...</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="wizard-actions">
                            <button onclick="rotationPlanner.previousStep()" class="btn-secondary" id="prev-btn" disabled>
                                ← Previous
                            </button>
                            <button onclick="rotationPlanner.nextStep()" class="btn-primary" id="next-btn">
                                Next →
                            </button>
                            <button onclick="rotationPlanner.generatePlan()" class="btn-success" id="generate-btn" style="display: none;">
                                🌱 Generate Plan
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return modal;
    }
    
    async loadAvailableCrops() {
        try {
            const response = await fetch('/api/crop-rotation/available-crops');
            const data = await response.json();
            
            this.availableCrops = data.available_crops;
            this.populateCropSelectors();
            
        } catch (error) {
            console.error('Error loading available crops:', error);
        }
    }
    
    populateCropSelectors() {
        const preferredContainer = document.getElementById('preferred-crops');
        const avoidContainer = document.getElementById('avoid-crops');
        
        if (!this.availableCrops) return;
        
        let preferredHtml = '';
        let avoidHtml = '';
        
        this.availableCrops.forEach(crop => {
            const cropInfo = `${crop.crop_type} (${crop.water_requirement} water, ${crop.growth_period_days} days)`;
            
            preferredHtml += `
                <label class="crop-checkbox">
                    <input type="checkbox" name="preferred" value="${crop.crop_type}">
                    <span class="checkmark"></span>
                    ${cropInfo}
                </label>
            `;
            
            avoidHtml += `
                <label class="crop-checkbox">
                    <input type="checkbox" name="avoid" value="${crop.crop_type}">
                    <span class="checkmark"></span>
                    ${cropInfo}
                </label>
            `;
        });
        
        preferredContainer.innerHTML = preferredHtml;
        avoidContainer.innerHTML = avoidHtml;
    }
    
    setupLocationSelector() {
        this.isSelectingLocation = false;
        
        // If map is available and user clicks on it during location selection
        if (window.map) {
            this.originalMapClickHandler = window.handleMapClick;
            
            window.handleMapClick = (e) => {
                if (this.isSelectingLocation) {
                    document.getElementById('rotation-lat').value = e.latlng.lat.toFixed(6);
                    document.getElementById('rotation-lng').value = e.latlng.lng.toFixed(6);
                    document.getElementById('location-status').textContent = 
                        `Location selected: ${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`;
                    this.disableLocationPicking();
                } else if (this.originalMapClickHandler) {
                    this.originalMapClickHandler(e);
                }
            };
        }
    }
    
    enableLocationPicking() {
        this.isSelectingLocation = true;
        document.getElementById('location-status').textContent = 'Click on the map to select field location...';
        document.body.style.cursor = 'crosshair';
    }
    
    disableLocationPicking() {
        this.isSelectingLocation = false;
        document.body.style.cursor = 'default';
    }
    
    nextStep() {
        const currentStep = document.querySelector('.wizard-step.active');
        const currentPanel = document.querySelector('.wizard-panel.active');
        const stepNumber = parseInt(currentStep.dataset.step);
        
        if (stepNumber < 3) {
            // Validate current step
            if (stepNumber === 1 && !this.validateStep1()) {
                return;
            }
            
            // Move to next step
            currentStep.classList.remove('active');
            currentPanel.classList.remove('active');
            
            const nextStep = document.querySelector(`[data-step="${stepNumber + 1}"]`);
            const nextPanel = document.getElementById(`step-${stepNumber + 1}`);
            
            nextStep.classList.add('active');
            nextPanel.classList.add('active');
            
            // Update buttons
            document.getElementById('prev-btn').disabled = false;
            
            if (stepNumber + 1 === 3) {
                document.getElementById('next-btn').style.display = 'none';
                document.getElementById('generate-btn').style.display = 'inline-block';
            }
        }
    }
    
    previousStep() {
        const currentStep = document.querySelector('.wizard-step.active');
        const currentPanel = document.querySelector('.wizard-panel.active');
        const stepNumber = parseInt(currentStep.dataset.step);
        
        if (stepNumber > 1) {
            currentStep.classList.remove('active');
            currentPanel.classList.remove('active');
            
            const prevStep = document.querySelector(`[data-step="${stepNumber - 1}"]`);
            const prevPanel = document.getElementById(`step-${stepNumber - 1}`);
            
            prevStep.classList.add('active');
            prevPanel.classList.add('active');
            
            // Update buttons
            if (stepNumber - 1 === 1) {
                document.getElementById('prev-btn').disabled = true;
            }
            
            document.getElementById('next-btn').style.display = 'inline-block';
            document.getElementById('generate-btn').style.display = 'none';
        }
    }
    
    validateStep1() {
        const lat = document.getElementById('rotation-lat').value;
        const lng = document.getElementById('rotation-lng').value;
        const fieldSize = document.getElementById('rotation-field-size').value;
        
        if (!lat || !lng || !fieldSize) {
            alert('Please fill in all required fields: latitude, longitude, and field size.');
            return false;
        }
        
        if (parseFloat(fieldSize) <= 0) {
            alert('Field size must be greater than 0.');
            return false;
        }
        
        return true;
    }
    
    async generatePlan() {
        const generateBtn = document.getElementById('generate-btn');
        generateBtn.disabled = true;
        generateBtn.textContent = '⏳ Generating...';
        
        const planDisplay = document.getElementById('rotation-plan-display');
        planDisplay.innerHTML = '<div class="loading">Generating your crop rotation plan...</div>';
        
        try {
            const params = this.collectPlanningParameters();
            const response = await fetch(`/api/crop-rotation/plan?${params}`);
            const planData = await response.json();
            
            if (planData.error) {
                throw new Error(planData.error);
            }
            
            this.currentPlan = planData;
            this.displayRotationPlan(planData);
            
            // Enable export buttons
            document.getElementById('export-json-btn').disabled = false;
            document.getElementById('export-csv-btn').disabled = false;
            
        } catch (error) {
            console.error('Error generating rotation plan:', error);
            planDisplay.innerHTML = `<div class="error">Error generating plan: ${error.message}</div>`;
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = '🌱 Generate Plan';
        }
    }
    
    collectPlanningParameters() {
        const lat = document.getElementById('rotation-lat').value;
        const lng = document.getElementById('rotation-lng').value;
        const fieldSize = document.getElementById('rotation-field-size').value;
        const years = document.getElementById('rotation-years').value;
        
        const preferredCrops = Array.from(document.querySelectorAll('input[name="preferred"]:checked'))
            .map(cb => cb.value);
        const avoidCrops = Array.from(document.querySelectorAll('input[name="avoid"]:checked'))
            .map(cb => cb.value);
        
        const params = new URLSearchParams({
            lat: lat,
            lng: lng,
            field_size: fieldSize,
            years: years
        });
        
        if (preferredCrops.length > 0) {
            params.append('preferred_crops', preferredCrops.join(','));
        }
        
        if (avoidCrops.length > 0) {
            params.append('avoid_crops', avoidCrops.join(','));
        }
        
        return params.toString();
    }
    
    displayRotationPlan(planData) {
        const container = document.getElementById('rotation-plan-display');
        const scores = planData.scores;
        
        container.innerHTML = `
            <div class="plan-header">
                <h4>🌱 Your Crop Rotation Plan</h4>
                <div class="plan-info">
                    <span>Field: ${planData.field_size} ha</span>
                    <span>Period: ${planData.years_planned} years</span>
                    <span>Generated: ${new Date(planData.generated_at).toLocaleDateString()}</span>
                </div>
            </div>
            
            <div class="plan-scores">
                <div class="score-card ${this.getScoreClass(scores.sustainability)}">
                    <div class="score-icon">🌿</div>
                    <div class="score-value">${scores.sustainability}</div>
                    <div class="score-label">Sustainability</div>
                </div>
                <div class="score-card ${this.getScoreClass(scores.economic)}">
                    <div class="score-icon">💰</div>
                    <div class="score-value">${scores.economic}</div>
                    <div class="score-label">Economic</div>
                </div>
                <div class="score-card ${this.getRiskClass(scores.risk)}">
                    <div class="score-icon">⚠️</div>
                    <div class="score-value">${scores.risk}</div>
                    <div class="score-label">Risk</div>
                </div>
            </div>
            
            <div class="rotation-timeline">
                <h5>Planting Schedule</h5>
                <div class="timeline-grid">
                    ${planData.seasons.map(season => `
                        <div class="season-card">
                            <div class="season-header">
                                <h6>Year ${season.year} - ${season.season}</h6>
                            </div>
                            <div class="crop-info">
                                <div class="crop-name">🌾 ${season.crop_type}</div>
                                <div class="crop-yield">
                                    Expected: ${season.expected_yield.estimated_tons_per_hectare} t/ha
                                </div>
                                <div class="crop-price">
                                    Price: $${season.economic_potential.estimated_price_per_ton}/t
                                </div>
                            </div>
                            ${season.risk_factors.length > 0 ? `
                                <div class="risk-factors">
                                    <strong>Risks:</strong>
                                    <ul>
                                        ${season.risk_factors.map(risk => `<li>${risk}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <div class="recommendations">
                <h5>📋 Recommendations</h5>
                <div class="recommendations-list">
                    ${planData.recommendations.map(rec => `
                        <div class="recommendation-item">
                            <span class="rec-icon">💡</span>
                            <span class="rec-text">${rec}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    getScoreClass(score) {
        if (score >= 80) return 'excellent';
        if (score >= 60) return 'good';
        if (score >= 40) return 'fair';
        return 'poor';
    }
    
    getRiskClass(risk) {
        if (risk <= 20) return 'excellent';
        if (risk <= 40) return 'good';
        if (risk <= 60) return 'fair';
        return 'poor';
    }
    
    async exportPlan(format) {
        if (!this.currentPlan) {
            alert('No plan available to export. Please generate a plan first.');
            return;
        }
        
        try {
            const params = this.collectPlanningParameters();
            const response = await fetch(`/api/crop-rotation/export?format=${format}&${params}`);
            
            if (format === 'csv') {
                const csvData = await response.text();
                this.downloadFile(csvData, `rotation_plan_${this.currentPlan.field_id}.csv`, 'text/csv');
            } else {
                const jsonData = await response.json();
                this.downloadFile(jsonData.data, `rotation_plan_${this.currentPlan.field_id}.json`, 'application/json');
            }
        } catch (error) {
            console.error('Export error:', error);
            alert('Failed to export plan: ' + error.message);
        }
    }
    
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }
    
    closePlanner() {
        // Restore original map click handler
        if (this.originalMapClickHandler) {
            window.handleMapClick = this.originalMapClickHandler;
        }
        
        this.disableLocationPicking();
        
        const modal = document.getElementById('rotation-modal');
        if (modal) {
            modal.remove();
        }
    }
}

// Global instances
const marketIntelligence = new MarketIntelligence();
const smartRecommendations = new SmartRecommendations();
const analyticsService = new AnalyticsDashboard();
const rotationPlanner = new CropRotationPlanner();

// Enhanced modal functions
function showMarketIntelligence(cropType, location = null) {
    marketIntelligence.show(cropType, location);
}

function showSmartRecommendations(location = null) {
    smartRecommendations.show(location);
}

function showAnalyticsDashboard() {
    analyticsService.showDashboard();
}

function showRotationPlanner() {
    rotationPlanner.showPlanner();
}

// Enhanced crop data integration for analytics
function updateAnalyticsData() {
    // Trigger analytics refresh when crop data changes
    if (analyticsService) {
        analyticsService.refreshData();
    }
}

// Enhanced location picker for rotation planner
function selectLocationForRotation() {
    if (rotationPlanner) {
        rotationPlanner.enableLocationPicking();
    }
}

// Initialize advanced features
document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile and performance features
    if (typeof initializeMobileAndPerformance === 'function') {
        initializeMobileAndPerformance();
    }
    
    // Add analytics refresh when crop reports are loaded
    const originalLoadCropReports = window.loadCropReports;
    if (originalLoadCropReports) {
        window.loadCropReports = async function() {
            await originalLoadCropReports();
            updateAnalyticsData();
        };
    }
    
    // Initialize advanced analytics on page load
    setTimeout(() => {
        updateAnalyticsData();
    }, 2000);
});