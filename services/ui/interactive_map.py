"""Interactive map module using Folium for click-to-select location functionality."""
import folium
from folium import plugins
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Uppsala center coordinates
UPPSALA_CENTER = [59.8586, 17.6389]


def create_interactive_map(
    shelters: List[Dict] = None,
    user_location: Optional[Tuple[float, float]] = None,
    show_all_shelters: bool = False
) -> str:
    """Create an interactive Folium map with click-to-select functionality.
    
    Args:
        shelters: List of shelter dictionaries with coordinates and details
        user_location: User's selected location as (lat, lng) tuple
        show_all_shelters: If True, show all shelters. Otherwise show only nearest 5.
        
    Returns:
        HTML string of the interactive map
    """
    # Create base map centered on Uppsala
    center = user_location if user_location else UPPSALA_CENTER
    m = folium.Map(
        location=center,
        zoom_start=13 if user_location else 12,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Add click handler for location selection
    # This JavaScript captures clicks and stores coordinates
    # Uses postMessage to communicate with parent window since HTML component is isolated
    click_handler = """
    <script>
    var selectedMarker = null;
    var selectedCoords = null;
    
    function onMapClick(e) {
        var lat = e.latlng.lat.toFixed(6);
        var lng = e.latlng.lng.toFixed(6);
        
        // Remove previous marker if exists
        if (selectedMarker) {
            selectedMarker.remove();
        }
        
        // Add new marker
        selectedMarker = L.marker([lat, lng], {
            icon: L.icon({
                iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
                shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                iconSize: [25, 41],
                iconAnchor: [12, 41],
                popupAnchor: [1, -34],
                shadowSize: [41, 41]
            })
        }).addTo(map_""" + m.get_name() + """);
        
        selectedMarker.bindPopup("📍 Din plats / Your location<br>Lat: " + lat + "<br>Lng: " + lng).openPopup();
        selectedCoords = {lat: parseFloat(lat), lng: parseFloat(lng)};
        
        // Use postMessage to send coordinates to parent window
        var message = {
            type: 'map_click',
            coordinates: lat + ',' + lng
        };
        
        // Try to access parent window (for iframe context)
        try {
            if (window.parent) {
                window.parent.postMessage(message, '*');
            } else if (window.top) {
                window.top.postMessage(message, '*');
            }
        } catch (e) {
            console.log('Could not send postMessage:', e);
        }
        
        // Also try direct DOM access as fallback
        try {
            var coordInput = document.getElementById('selected_coordinates');
            if (!coordInput && window.parent && window.parent.document) {
                coordInput = window.parent.document.getElementById('selected_coordinates');
            }
            if (!coordInput && window.top && window.top.document) {
                coordInput = window.top.document.getElementById('selected_coordinates');
            }
            if (coordInput) {
                coordInput.value = lat + ',' + lng;
                coordInput.dispatchEvent(new Event('input', { bubbles: true }));
                coordInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
        } catch (e) {
            console.log('Could not access coordinate input directly:', e);
        }
    }
    
    map_""" + m.get_name() + """.on('click', onMapClick);
    </script>
    """
    
    # Add user location marker if provided
    if user_location:
        folium.Marker(
            location=user_location,
            popup=folium.Popup("📍 Din plats / Your location", max_width=200),
            tooltip="Selected location",
            icon=folium.Icon(color='red', icon='user', prefix='fa')
        ).add_to(m)
    
    # Add shelter markers
    if shelters:
        # Determine which shelters to show
        shelters_to_show = shelters[:5] if not show_all_shelters else shelters
        
        for idx, shelter in enumerate(shelters_to_show):
            # Get coordinates from metadata
            lat = shelter.get('coordinates_lat') or shelter.get('metadata', {}).get('coordinates_lat')
            lng = shelter.get('coordinates_lng') or shelter.get('metadata', {}).get('coordinates_lng')
            
            if not lat or not lng:
                continue
            
            # Calculate distance if user location is provided
            distance_text = ""
            if user_location:
                distance = calculate_distance(user_location[0], user_location[1], lat, lng)
                if distance < 1:
                    distance_text = f"<br><b>📏 Avstånd: {int(distance * 1000)}m</b>"
                else:
                    distance_text = f"<br><b>📏 Avstånd: {distance:.1f}km</b>"
            
            # Create popup content
            name = shelter.get('name', 'Unknown Shelter')
            address = shelter.get('address', '')
            capacity = shelter.get('capacity', 'N/A')
            map_url = shelter.get('map_url', '')
            
            popup_html = f"""
            <div style="min-width: 200px;">
                <h4 style="margin: 0 0 10px 0;">{name}</h4>
                <p style="margin: 5px 0;">
                    📍 <b>Adress:</b> {address}<br>
                    👥 <b>Kapacitet:</b> {capacity} personer
                    {distance_text}
                </p>
                {'<a href="' + map_url + '" target="_blank" style="color: #1a73e8;">🗺️ Öppna i Google Maps</a>' if map_url else ''}
            </div>
            """
            
            # Different colors for different positions
            color = 'blue' if idx == 0 else 'green'
            icon_name = 'home' if idx == 0 else 'info-sign'
            
            folium.Marker(
                location=[lat, lng],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=name,
                icon=folium.Icon(color=color, icon=icon_name)
            ).add_to(m)
        
        # Add circle around user location if provided
        if user_location and len(shelters_to_show) > 0:
            # Find max distance to show all shelters
            max_distance = 0
            for shelter in shelters_to_show:
                lat = shelter.get('coordinates_lat') or shelter.get('metadata', {}).get('coordinates_lat')
                lng = shelter.get('coordinates_lng') or shelter.get('metadata', {}).get('coordinates_lng')
                if lat and lng:
                    distance = calculate_distance(user_location[0], user_location[1], lat, lng)
                    max_distance = max(max_distance, distance)
            
            if max_distance > 0:
                folium.Circle(
                    location=user_location,
                    radius=max_distance * 1000,  # Convert km to meters
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.1,
                    popup=f"Sökradie: {max_distance:.1f}km"
                ).add_to(m)
    
    # Add fullscreen button
    plugins.Fullscreen(
        position='topright',
        title='Fullskärm',
        title_cancel='Avsluta fullskärm',
        force_separate_button=True
    ).add_to(m)
    
    # Add locate control (use current GPS location)
    plugins.LocateControl(
        auto_start=False,
        position='topleft'
    ).add_to(m)
    
    # Get HTML and add click handler
    # The click handler needs to be injected into the iframe's document
    map_html = m._repr_html_()
    
    # Inject the click handler script before the closing </script> tag in the iframe content
    # We need to escape it properly for the iframe srcdoc attribute
    injection_point = '&lt;/script&gt;\n&lt;/html&gt;'
    if injection_point in map_html:
        map_html = map_html.replace(injection_point, click_handler.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;') + injection_point)
    
    return map_html


def create_initial_interactive_map() -> str:
    """Create an initial interactive map centered on Uppsala."""
    return create_interactive_map()


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        Distance in kilometers
    """
    from math import radians, sin, cos, sqrt, atan2
    
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c
    return distance


def parse_coordinates(coord_string: str) -> Optional[Tuple[float, float]]:
    """Parse coordinate string like '59.8586,17.6389' into (lat, lng) tuple.
    
    Args:
        coord_string: Comma-separated coordinates
        
    Returns:
        Tuple of (lat, lng) or None if invalid
    """
    if not coord_string:
        return None
    
    try:
        parts = coord_string.strip().split(',')
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            
            # Validate Uppsala area (rough bounds)
            if 59.7 <= lat <= 60.0 and 17.5 <= lng <= 17.8:
                return (lat, lng)
    except (ValueError, AttributeError):
        pass
    
    return None
