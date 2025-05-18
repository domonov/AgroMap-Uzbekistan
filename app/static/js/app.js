/**
 * AgroMap Uzbekistan - Main Application JavaScript
 * Handles mobile optimization, performance improvements, and PWA features
 */

// DOM Ready handler
document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile navigation
    initMobileNav();
    
    // Initialize lazy loading
    initLazyLoading();
    
    // Initialize responsive images
    initResponsiveImages();
    
    // Initialize offline form handling
    initOfflineForms();
    
    // Initialize touch optimizations
    initTouchOptimizations();
    
    // Initialize performance monitoring
    initPerformanceMonitoring();
});

/**
 * Mobile Navigation
 */
function initMobileNav() {
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const desktopNav = document.querySelector('.desktop-nav');
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            this.classList.toggle('active');
            
            // Toggle desktop nav visibility on mobile
            if (desktopNav) {
                desktopNav.classList.toggle('visible');
            }
        });
    }
    
    // Handle swipe gestures for navigation
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    document.addEventListener('touchend', e => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
    
    function handleSwipe() {
        const swipeThreshold = 100;
        
        // Right swipe (open menu)
        if (touchEndX - touchStartX > swipeThreshold) {
            if (desktopNav && !desktopNav.classList.contains('visible')) {
                desktopNav.classList.add('visible');
                if (mobileMenuToggle) mobileMenuToggle.classList.add('active');
            }
        }
        
        // Left swipe (close menu)
        if (touchStartX - touchEndX > swipeThreshold) {
            if (desktopNav && desktopNav.classList.contains('visible')) {
                desktopNav.classList.remove('visible');
                if (mobileMenuToggle) mobileMenuToggle.classList.remove('active');
            }
        }
    }
}

/**
 * Lazy Loading Images
 */
function initLazyLoading() {
    // Check if IntersectionObserver is supported
    if ('IntersectionObserver' in window) {
        const lazyImages = document.querySelectorAll('img[data-src]');
        
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    
                    // Load srcset if available
                    if (img.dataset.srcset) {
                        img.srcset = img.dataset.srcset;
                    }
                    
                    img.classList.add('loaded');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    } else {
        // Fallback for browsers that don't support IntersectionObserver
        const lazyImages = document.querySelectorAll('img[data-src]');
        
        function lazyLoad() {
            const scrollTop = window.pageYOffset;
            
            lazyImages.forEach(img => {
                if (img.offsetTop < window.innerHeight + scrollTop) {
                    img.src = img.dataset.src;
                    
                    if (img.dataset.srcset) {
                        img.srcset = img.dataset.srcset;
                    }
                    
                    img.classList.add('loaded');
                }
            });
            
            // If all images are loaded, stop listening
            if (lazyImages.length === 0) {
                document.removeEventListener('scroll', lazyLoad);
                window.removeEventListener('resize', lazyLoad);
                window.removeEventListener('orientationChange', lazyLoad);
            }
        }
        
        document.addEventListener('scroll', lazyLoad);
        window.addEventListener('resize', lazyLoad);
        window.addEventListener('orientationChange', lazyLoad);
    }
}

/**
 * Responsive Images
 */
function initResponsiveImages() {
    // Add srcset and sizes to images that don't have them
    const images = document.querySelectorAll('img:not([srcset])');
    
    images.forEach(img => {
        // Skip images that are already optimized or decorative
        if (img.classList.contains('icon') || img.classList.contains('logo') || 
            img.width < 100 || img.hasAttribute('data-src')) {
            return;
        }
        
        // Get the image source
        const src = img.src;
        if (!src || src.includes('data:image')) return;
        
        // Extract the file name and extension
        const lastSlash = src.lastIndexOf('/');
        const lastDot = src.lastIndexOf('.');
        
        if (lastSlash === -1 || lastDot === -1) return;
        
        const basePath = src.substring(0, lastSlash + 1);
        const fileName = src.substring(lastSlash + 1, lastDot);
        const extension = src.substring(lastDot);
        
        // Check if responsive versions exist
        const img300 = new Image();
        img300.src = `${basePath}${fileName}-300w${extension}`;
        
        img300.onload = function() {
            // If responsive image exists, create srcset
            const srcset = `
                ${basePath}${fileName}-300w${extension} 300w,
                ${basePath}${fileName}-600w${extension} 600w,
                ${src} 1200w
            `;
            
            img.setAttribute('srcset', srcset);
            img.setAttribute('sizes', '(max-width: 600px) 300px, (max-width: 1200px) 600px, 1200px');
        };
    });
}

/**
 * Offline Form Handling
 */
function initOfflineForms() {
    // Check if service worker and IndexedDB are supported
    if ('serviceWorker' in navigator && 'indexedDB' in window) {
        const forms = document.querySelectorAll('form[data-offline-submit]');
        
        forms.forEach(form => {
            form.addEventListener('submit', async function(e) {
                // If we're offline, store the form data
                if (!navigator.onLine) {
                    e.preventDefault();
                    
                    const formData = new FormData(form);
                    const formObject = {};
                    
                    formData.forEach((value, key) => {
                        formObject[key] = value;
                    });
                    
                    try {
                        // Open the database
                        const dbPromise = indexedDB.open('agromap-offline', 1);
                        
                        dbPromise.onsuccess = function(event) {
                            const db = event.target.result;
                            const transaction = db.transaction('formData', 'readwrite');
                            const store = transaction.objectStore('formData');
                            
                            // Store the form data
                            store.add({
                                url: form.action,
                                method: form.method,
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(formObject),
                                timestamp: new Date().getTime()
                            });
                            
                            // Show a message to the user
                            alert('You are currently offline. Your form data has been saved and will be submitted when you are back online.');
                            
                            // Register for background sync if available
                            if ('sync' in navigator.serviceWorker) {
                                navigator.serviceWorker.ready.then(function(registration) {
                                    registration.sync.register('sync-forms');
                                });
                            }
                        };
                    } catch (error) {
                        console.error('Error saving form data:', error);
                    }
                }
            });
        });
    }
}

/**
 * Touch Optimizations
 */
function initTouchOptimizations() {
    // Add touch feedback to buttons and links
    const touchElements = document.querySelectorAll('a, button, .btn, .nav-link');
    
    touchElements.forEach(el => {
        el.addEventListener('touchstart', function() {
            this.classList.add('touch-active');
        }, { passive: true });
        
        el.addEventListener('touchend', function() {
            this.classList.remove('touch-active');
        }, { passive: true });
    });
    
    // Improve map touch interactions if Leaflet map exists
    const map = document.getElementById('map');
    if (map && window.L) {
        // Ensure map controls are touch-friendly
        if (map._leaflet_id) {
            const leafletMap = window.L.map._instances[map._leaflet_id];
            if (leafletMap) {
                // Adjust zoom control buttons for touch
                const zoomControl = leafletMap.zoomControl;
                if (zoomControl) {
                    const zoomInButton = zoomControl._zoomInButton;
                    const zoomOutButton = zoomControl._zoomOutButton;
                    
                    if (zoomInButton) zoomInButton.style.fontSize = '22px';
                    if (zoomOutButton) zoomOutButton.style.fontSize = '22px';
                }
            }
        }
    }
}

/**
 * Performance Monitoring
 */
function initPerformanceMonitoring() {
    // Check if Performance API is supported
    if ('performance' in window && 'getEntriesByType' in performance) {
        // Get navigation timing
        const navigationTiming = performance.getEntriesByType('navigation')[0];
        
        if (navigationTiming) {
            // Calculate key metrics
            const pageLoadTime = navigationTiming.loadEventEnd - navigationTiming.startTime;
            const domContentLoaded = navigationTiming.domContentLoadedEventEnd - navigationTiming.startTime;
            
            // Log performance metrics
            console.log('Page Load Time:', pageLoadTime.toFixed(2) + 'ms');
            console.log('DOM Content Loaded:', domContentLoaded.toFixed(2) + 'ms');
            
            // Send metrics to server if needed
            if (pageLoadTime > 3000) {
                // Page is loading slowly, consider sending telemetry
                // This could be implemented with a fetch call to a server endpoint
            }
        }
    }
}

/**
 * Utility Functions
 */

// Debounce function to limit how often a function can be called
function debounce(func, wait) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

// Throttle function to limit how often a function can be called
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const context = this;
        const args = arguments;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Check if device is touch-enabled
function isTouchDevice() {
    return (('ontouchstart' in window) ||
            (navigator.maxTouchPoints > 0) ||
            (navigator.msMaxTouchPoints > 0));
}

// Add touch class to body if on touch device
if (isTouchDevice()) {
    document.body.classList.add('touch-device');
}