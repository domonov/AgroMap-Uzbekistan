# Asset bundles configuration for Flask-Assets

BUNDLES = {
    'css_all': Bundle(
        'css/map.css',
        'css/responsive.css',
        filters='cssmin',
        output='dist/css/bundle.%(version)s.css'
    ),
    'js_all': Bundle(
        'js/app.js',
        'js/map-touch.js',
        filters='jsmin',
        output='dist/js/bundle.%(version)s.js'
    ),
}

# Cache configuration for assets
CACHE_CONFIG = {
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache',
    'CACHE_DEFAULT_TIMEOUT': 3600
}
