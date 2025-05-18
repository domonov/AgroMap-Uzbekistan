# Map Controls CSS

This CSS file addresses the UI/UX issue where map controls were being blocked by other elements. The main changes include:

1. **Increased z-index for map controls**: All Leaflet controls now have a higher z-index to ensure they appear above other elements.
2. **Proper positioning**: Controls are positioned to avoid overlapping with the navigation bar and other elements.
3. **Responsive design**: Media queries ensure the controls are properly positioned and sized on different screen sizes.
4. **Touch-friendly controls**: Larger touch targets for touch devices.

## How to Use

The CSS is automatically loaded on the map page. No additional configuration is needed.

## Implementation Details

- Map container has z-index: 1
- Leaflet controls have z-index: 1000-1500
- Navigation bar has z-index: 2500
- Media queries adjust positioning for screens smaller than 768px
- Special styling for touch devices