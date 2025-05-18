// Enhanced touch controls for the map
document.addEventListener('DOMContentLoaded', function() {
    // Get map container
    const mapContainer = document.getElementById('map');
    if (!mapContainer || !map) return;

    // Enable touch zoom and pan by default in Leaflet
    map.touchZoom.enable();
    map.dragging.enable();
    map.tap.enable();

    // Variables for touch gesture detection
    let touchStartTime;
    let touchEndTime;
    let lastTap = 0;
    let touchZoomStart;

    // Touch gesture handlers
    mapContainer.addEventListener('touchstart', function(e) {
        touchStartTime = new Date().getTime();
        if (e.touches.length === 2) {
            touchZoomStart = getTouchDistance(e.touches);
        }
    }, false);

    mapContainer.addEventListener('touchend', function(e) {
        touchEndTime = new Date().getTime();
        const tapLength = touchEndTime - touchStartTime;
        
        // Detect double tap
        const currentTime = new Date().getTime();
        const tapGap = currentTime - lastTap;
        lastTap = currentTime;

        // Handle double tap to zoom
        if (tapGap < 300 && tapLength < 300) {
            const center = map.getCenter();
            map.setZoom(map.getZoom() + 1);
            map.panTo(center);
            e.preventDefault();
        }
    }, false);

    // Custom two-finger zoom handler
    mapContainer.addEventListener('touchmove', function(e) {
        if (e.touches.length === 2) {
            const newTouchDistance = getTouchDistance(e.touches);
            if (touchZoomStart) {
                const diff = newTouchDistance - touchZoomStart;
                if (Math.abs(diff) > 10) {
                    const direction = diff > 0 ? 1 : -1;
                    map.setZoom(map.getZoom() + direction * 0.5);
                    touchZoomStart = newTouchDistance;
                }
            }
            e.preventDefault();
        }
    }, false);

    // Prevent default browser touch actions
    mapContainer.addEventListener('touchmove', function(e) {
        if (e.touches.length > 1) {
            e.preventDefault();
        }
    }, { passive: false });

    // Helper function to calculate distance between two touch points
    function getTouchDistance(touches) {
        return Math.hypot(
            touches[0].clientX - touches[1].clientX,
            touches[0].clientY - touches[1].clientY
        );
    }

    // Add touch-friendly markers
    const originalAddMarker = window.addMarker || function() {};
    window.addMarker = function(latlng, options = {}) {
        const markerOptions = {
            ...options,
            // Increase marker size for touch targets
            icon: L.icon({
                iconUrl: options.icon?.options?.iconUrl || 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
                iconSize: [30, 45],     // Bigger than default
                iconAnchor: [15, 45],   // Adjusted for new size
                popupAnchor: [0, -45]   // Adjusted for new size
            })
        };
        return originalAddMarker(latlng, markerOptions);
    };

    // Add touch feedback for markers
    map.on('click', function(e) {
        // Add touch ripple effect
        const ripple = document.createElement('div');
        ripple.className = 'map-touch-ripple';
        ripple.style.left = e.containerPoint.x + 'px';
        ripple.style.top = e.containerPoint.y + 'px';
        mapContainer.appendChild(ripple);
        
        // Remove ripple after animation
        setTimeout(() => ripple.remove(), 500);
    });
});
