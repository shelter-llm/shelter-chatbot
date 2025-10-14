"""Map generator for shelter locations using Folium."""
import folium
from folium.plugins import MarkerCluster
import httpx
import logging
from typing import Optional, List, Dict, Any
import asyncio

logger = logging.getLogger(__name__)


class MapGenerator:
    """Generate interactive maps of shelter locations."""
    
    def __init__(self, vectordb_url: str):
        """
        Initialize map generator.
        
        Args:
            vectordb_url: URL of the vector database service
        """
        self.vectordb_url = vectordb_url
        self.uppsala_center = [59.8586, 17.6389]  # Uppsala coordinates
    
    def _get_all_shelters_sync(self, district: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all shelters from vector database (synchronous).
        
        Args:
            district: Optional district filter
            
        Returns:
            List of shelter documents
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                # Use the new get all documents endpoint (no semantic search needed)
                response = client.get(
                    f"{self.vectordb_url}/collections/uppsala_shelters/documents",
                    params={"limit": 1000}  # Get up to 1000 shelters
                )
                response.raise_for_status()
                data = response.json()
                
                shelters = data.get("documents", [])
                logger.info(f"Retrieved {len(shelters)} shelters for map")
                
                # Filter by district if specified
                if district and district != "Alla":
                    shelters = [
                        s for s in shelters
                        if s.get("metadata", {}).get("district", "").lower() == district.lower()
                    ]
                
                return shelters
                
        except Exception as e:
            logger.error(f"Error retrieving shelters for map: {e}")
            return []
    
    def generate_map(self, district: Optional[str] = None) -> str:
        """
        Generate HTML map of shelters.
        
        Args:
            district: Optional district filter
            
        Returns:
            HTML string of the map
        """
        try:
            # Get shelters
            shelters = self._get_all_shelters_sync(district)
            
            # Create map centered on Uppsala
            m = folium.Map(
                location=self.uppsala_center,
                zoom_start=12,
                tiles='OpenStreetMap'
            )
            
            # Add marker cluster for better performance with many markers
            marker_cluster = MarkerCluster().add_to(m)
            
            # Add markers for each shelter
            added_count = 0
            for shelter in shelters:
                metadata = shelter.get("metadata", {})
                
                # Get coordinates
                lat = metadata.get("coordinates_lat")
                lng = metadata.get("coordinates_lng")
                
                if lat is None or lng is None:
                    continue
                
                try:
                    lat = float(lat)
                    lng = float(lng)
                except (ValueError, TypeError):
                    continue
                
                # Get shelter info
                name = metadata.get("name", "Unknown Shelter")
                address = metadata.get("address", "No address")
                capacity = metadata.get("capacity", "Unknown")
                district_name = metadata.get("district", "Unknown")
                
                # Create popup HTML
                popup_html = f"""
                <div style="font-family: Arial, sans-serif; min-width: 200px;">
                    <h4 style="margin-bottom: 10px;">{name}</h4>
                    <p style="margin: 5px 0;">
                        <b>📍 Address:</b> {address}
                    </p>
                    <p style="margin: 5px 0;">
                        <b>👥 Capacity:</b> {capacity} people
                    </p>
                    <p style="margin: 5px 0;">
                        <b>🏘️ District:</b> {district_name}
                    </p>
                </div>
                """
                
                # Determine marker color based on capacity
                if isinstance(capacity, (int, float)):
                    if capacity >= 400:
                        icon_color = 'red'
                    elif capacity >= 200:
                        icon_color = 'orange'
                    else:
                        icon_color = 'blue'
                else:
                    icon_color = 'gray'
                
                # Add marker
                folium.Marker(
                    location=[lat, lng],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=name,
                    icon=folium.Icon(color=icon_color, icon='home', prefix='fa')
                ).add_to(marker_cluster)
                
                added_count += 1
            
            logger.info(f"Added {added_count} shelters to map")
            
            # Add legend
            legend_html = """
            <div style="position: fixed; 
                        bottom: 50px; left: 50px; width: 200px; height: 120px; 
                        background-color: white; border:2px solid grey; z-index:9999; 
                        font-size:14px; padding: 10px">
                <p style="margin: 5px 0;"><b>Capacity Legend</b></p>
                <p style="margin: 5px 0;">
                    <i class="fa fa-map-marker" style="color:red"></i> 400+ people
                </p>
                <p style="margin: 5px 0;">
                    <i class="fa fa-map-marker" style="color:orange"></i> 200-399 people
                </p>
                <p style="margin: 5px 0;">
                    <i class="fa fa-map-marker" style="color:blue"></i> < 200 people
                </p>
            </div>
            """
            m.get_root().html.add_child(folium.Element(legend_html))
            
            # Return HTML
            return m._repr_html_()
            
        except Exception as e:
            logger.error(f"Error generating map: {e}")
            return f"""
            <div style="padding: 20px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px;">
                <h3>⚠️ Error generating map</h3>
                <p>Could not load shelter locations. Please check that the Vector DB service is running.</p>
                <p>Error: {str(e)}</p>
            </div>
            """
