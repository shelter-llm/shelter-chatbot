"""Geocoding service using Google Maps Geocoding API."""
import os
import logging
import httpx
from typing import Optional, Tuple, Dict
import re

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for converting location names to coordinates.
    
    Supports both Google Maps API and free Nominatim (OpenStreetMap).
    By default, uses Nominatim which is free and doesn't require an API key.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_nominatim: bool = True):
        """Initialize geocoding service.
        
        Args:
            api_key: Google Maps API key. If None, forces Nominatim.
            use_nominatim: If True, use free Nominatim service. Default: True
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        
        # Use Nominatim if no API key or explicitly requested
        self.use_nominatim = use_nominatim or (self.api_key is None)
        
        if self.use_nominatim:
            self.base_url = "https://nominatim.openstreetmap.org/search"
            logger.info("🌍 Using Nominatim (OpenStreetMap) for geocoding - FREE, no API key needed!")
        else:
            self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
            logger.info("🗺️ Using Google Maps Geocoding API")
        
        self.default_bounds = {
            # Uppsala kommun bounds (approximate)
            "southwest": {"lat": 59.7, "lng": 17.4},
            "northeast": {"lat": 60.0, "lng": 17.8}
        }
    
    async def geocode_location(
        self, 
        location_query: str,
        bias_to_uppsala: bool = True
    ) -> Optional[Dict]:
        """Convert a location name/address to coordinates.
        
        Args:
            location_query: Location name or address (e.g., "Centralstationen Uppsala", "Kungsgatan")
            bias_to_uppsala: If True, bias results towards Uppsala area
            
        Returns:
            Dict with 'lat', 'lng', 'formatted_address', 'place_name' or None if not found
        """
        if self.use_nominatim:
            return await self._geocode_nominatim(location_query, bias_to_uppsala)
        else:
            return await self._geocode_google(location_query, bias_to_uppsala)
    
    async def _geocode_nominatim(
        self,
        location_query: str,
        bias_to_uppsala: bool = True
    ) -> Optional[Dict]:
        """Geocode using free Nominatim (OpenStreetMap) service.
        
        Nominatim is free and doesn't require an API key!
        Rate limit: 1 request per second (enforced by server)
        """
        try:
            # Prepare the query - add "Uppsala" if not present and bias is enabled
            query = location_query.strip()
            if bias_to_uppsala and "uppsala" not in query.lower():
                query = f"{query}, Uppsala, Sweden"
            
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }
            
            # Add viewbox to bias results towards Uppsala
            if bias_to_uppsala:
                # Format: left,top,right,bottom (lng_min,lat_max,lng_max,lat_min)
                params["viewbox"] = "17.4,60.0,17.8,59.7"  # Uppsala bounds
                params["bounded"] = 1  # Restrict to viewbox
            
            headers = {
                "User-Agent": "Uppsala-Emergency-Shelter-Chatbot/1.0 (Educational Project)"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.base_url,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
            
            if not data or len(data) == 0:
                logger.warning(f"No geocoding results for query: {location_query}")
                return None
            
            result = data[0]
            
            # Extract place name from address components
            place_name = location_query
            address = result.get("address", {})
            if address:
                # Try to get a nice place name
                place_name = (
                    address.get("amenity") or
                    address.get("building") or
                    address.get("road") or
                    address.get("suburb") or
                    address.get("neighbourhood") or
                    address.get("town") or
                    location_query
                )
            
            geocoded = {
                "lat": float(result["lat"]),
                "lng": float(result["lon"]),
                "formatted_address": result.get("display_name", location_query),
                "place_name": place_name,
                "query": location_query
            }
            
            logger.info(
                f"✅ Geocoded '{location_query}' to ({geocoded['lat']:.4f}, {geocoded['lng']:.4f}) "
                f"via Nominatim - {geocoded['formatted_address']}"
            )
            
            return geocoded
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during Nominatim geocoding: {e}")
            return None
        except Exception as e:
            logger.error(f"Error geocoding with Nominatim '{location_query}': {e}", exc_info=True)
            return None
    
    async def _geocode_google(
        self,
        location_query: str,
        bias_to_uppsala: bool = True
    ) -> Optional[Dict]:
        """Geocode using Google Maps API (requires API key and billing)."""
        if not self.api_key:
            logger.error("Cannot geocode with Google: No API key available")
            return None
        
        try:
            # Prepare the query - add "Uppsala" if not present and bias is enabled
            query = location_query.strip()
            if bias_to_uppsala and "uppsala" not in query.lower():
                query = f"{query}, Uppsala, Sweden"
            
            params = {
                "address": query,
                "key": self.api_key
            }
            
            # Add bounds to bias results towards Uppsala
            if bias_to_uppsala:
                bounds = (
                    f"{self.default_bounds['southwest']['lat']},"
                    f"{self.default_bounds['southwest']['lng']}|"
                    f"{self.default_bounds['northeast']['lat']},"
                    f"{self.default_bounds['northeast']['lng']}"
                )
                params["bounds"] = bounds
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # Log the full response for debugging
            status = data.get("status")
            logger.info(f"Geocoding API status: {status}")
            
            if status != "OK":
                logger.warning(f"Geocoding failed for '{location_query}': {status}")
                if status == "ZERO_RESULTS":
                    logger.info("No results found - try a different query format")
                elif status == "REQUEST_DENIED":
                    logger.error("Geocoding API request denied - check API key and billing")
                return None
            
            if not data.get("results"):
                logger.warning(f"No geocoding results for query: {location_query}")
                return None
            
            # Get the first (best) result
            result = data["results"][0]
            location = result["geometry"]["location"]
            
            # Extract place name (usually the first component)
            place_name = location_query
            if result.get("address_components"):
                # Try to get a nice place name from components
                for component in result["address_components"]:
                    if any(t in component.get("types", []) for t in ["locality", "neighborhood", "sublocality"]):
                        place_name = component["long_name"]
                        break
            
            geocoded = {
                "lat": location["lat"],
                "lng": location["lng"],
                "formatted_address": result.get("formatted_address", location_query),
                "place_name": place_name,
                "query": location_query
            }
            
            logger.info(
                f"Geocoded '{location_query}' to ({geocoded['lat']:.4f}, {geocoded['lng']:.4f}) - "
                f"{geocoded['formatted_address']}"
            )
            
            return geocoded
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during geocoding: {e}")
            return None
        except Exception as e:
            logger.error(f"Error geocoding location '{location_query}': {e}", exc_info=True)
            return None
    
    def extract_location_from_query(self, query: str) -> Optional[str]:
        """Extract location mentions from a natural language query.
        
        Args:
            query: Natural language query (e.g., "find shelters near Centralstationen")
            
        Returns:
            Extracted location string or None
        """
        # Common location patterns in Swedish and English
        patterns = [
            r"(?:near|nära|vid|i närheten av)\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
            r"(?:på|at|in|i)\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
            r"(?:around|runt)\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
            r"([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)\s+(?:area|område|district|stadsdel)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                location = match.group(1).strip()
                # Filter out common non-location words
                if location.lower() not in ["uppsala", "sweden", "sverige"]:
                    return location
        
        return None


# Singleton instance
_geocoding_service = None


def get_geocoding_service() -> GeocodingService:
    """Get or create the geocoding service singleton."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
