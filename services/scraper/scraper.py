"""Web scraper for Uppsala shelter data."""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import logging
import re
import json

logger = logging.getLogger(__name__)


class ShelterScraper:
    """Scraper for allaskyddsrum.se shelter data."""
    
    def __init__(self, base_url: str = "https://www.allaskyddsrum.se"):
        """Initialize scraper.
        
        Args:
            base_url: Base URL for the shelter website
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
    
    def scrape_uppsala_shelters(self, uppsala_url: str) -> List[Dict[str, Any]]:
        """Scrape shelter data for Uppsala.
        
        Args:
            uppsala_url: URL for Uppsala shelter data
            
        Returns:
            List of shelter data dictionaries
        """
        try:
            logger.info(f"Scraping shelters from: {uppsala_url}")
            response = self.session.get(uppsala_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            shelters = []
            
            # Find the badplatslista div containing all shelters
            badplatslista = soup.find('div', class_='badplatslista')
            
            if badplatslista:
                # Find all <li> elements with shelter links
                shelter_links = badplatslista.find_all('li')
                logger.info(f"Found {len(shelter_links)} shelter links")
                
                # Scrape all shelters (removed limit)
                for idx, li in enumerate(shelter_links):
                    link_elem = li.find('a')
                    if link_elem:
                        shelter_url = link_elem.get('href')
                        shelter_text = link_elem.get_text(strip=True)
                        
                        # Parse the link text (format: "Name, Address" or just "Address")
                        # Example: "Tensta-Åsby 3:27, Gullsjövägen"
                        parts = shelter_text.split(', ', 1)
                        name = parts[0] if len(parts) > 0 else f"Skyddsrum {idx + 1}"
                        address = parts[1] if len(parts) > 1 else parts[0]
                        
                        shelter = {
                            'id': f"uppsala_shelter_{idx + 1}",
                            'name': f"Skyddsrum {name}",
                            'address': address if address else f"{name}, Uppsala",
                            'capacity': None,
                            'coordinates': None,
                            'district': 'Uppsala',
                            'accessibility_features': [],
                            'facilities': ['Ventilation', 'Nödbelysning'],  # Standard features
                            'description': f'Skyddsrum vid {address if address else name} i Uppsala.',
                            'contact_info': 'Uppsala Kommun: 018-727 00 00',
                            'detail_url': shelter_url,
                            'map_url': None
                        }
                        
                        
                        # Fetch detailed information from individual page
                        try:
                            details = self.scrape_shelter_details(shelter_url)
                            if details:
                                if details.get('capacity'):
                                    shelter['capacity'] = details['capacity']
                                if details.get('coordinates'):
                                    shelter['coordinates'] = details['coordinates']
                                if details.get('description'):
                                    shelter['description'] = details['description']
                                if details.get('map_url'):
                                    shelter['map_url'] = details['map_url']
                                
                                logger.info(f"Enriched shelter {idx + 1} with coordinates: {shelter['coordinates']}")
                        except Exception as e:
                            logger.warning(f"Could not fetch details for shelter {idx + 1}: {e}")
                        
                        shelters.append(shelter)
                        
                        # Rate limiting - delay every 10 shelters
                        if idx > 0 and idx % 10 == 0:
                            import time
                            time.sleep(1)  # Increased to 1 second
                            logger.info(f"Processed {idx + 1} shelters...")
                
                logger.info(f"Successfully scraped {len(shelters)} shelters from list")
            else:
                logger.warning("Could not find badplatslista div")
            
            return shelters
            
        except requests.RequestException as e:
            logger.error(f"Error fetching shelter data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing shelter data: {e}")
            raise
    
    def _parse_shelter_element(self, element: BeautifulSoup, idx: int) -> Optional[Dict[str, Any]]:
        """Parse a single shelter element.
        
        Args:
            element: BeautifulSoup element containing shelter data
            idx: Index for generating ID
            
        Returns:
            Shelter data dictionary or None
        """
        try:
            shelter = {
                'id': f"uppsala_shelter_{idx + 1}",
                'name': '',
                'address': '',
                'capacity': None,
                'coordinates': None,
                'district': 'Uppsala',
                'accessibility_features': [],
                'facilities': [],
                'description': '',
                'contact_info': ''
            }
            
            # Extract name
            name_elem = element.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'(name|title|heading)', re.I))
            if name_elem:
                shelter['name'] = name_elem.get_text(strip=True)
            
            # Extract address
            address_elem = element.find(['p', 'span', 'div'], class_=re.compile(r'(address|location)', re.I))
            if address_elem:
                shelter['address'] = address_elem.get_text(strip=True)
            
            # Extract capacity
            capacity_elem = element.find(text=re.compile(r'(kapacitet|capacity|platser|personer)', re.I))
            if capacity_elem:
                capacity_match = re.search(r'\d+', capacity_elem)
                if capacity_match:
                    shelter['capacity'] = int(capacity_match.group())
            
            # Extract description
            desc_elem = element.find(['p', 'div'], class_=re.compile(r'(description|desc|info)', re.I))
            if desc_elem:
                shelter['description'] = desc_elem.get_text(strip=True)
            
            # Extract facilities/features
            features_elem = element.find_all('li')
            if features_elem:
                shelter['facilities'] = [li.get_text(strip=True) for li in features_elem]
            
            # Only return if we have at least a name or address
            if shelter['name'] or shelter['address']:
                return shelter
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing shelter element {idx}: {e}")
            return None
    
    def _scrape_from_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract shelter data from tables.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of shelter dictionaries
        """
        shelters = []
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(['th', 'td'])]
            
            for idx, row in enumerate(rows[1:], 1):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    shelter = {
                        'id': f"uppsala_shelter_table_{idx}",
                        'name': cells[0].get_text(strip=True) if len(cells) > 0 else '',
                        'address': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                        'capacity': None,
                        'district': 'Uppsala',
                        'accessibility_features': [],
                        'facilities': [],
                        'description': '',
                        'contact_info': ''
                    }
                    
                    # Try to extract capacity
                    if len(cells) > 2:
                        capacity_text = cells[2].get_text(strip=True)
                        capacity_match = re.search(r'\d+', capacity_text)
                        if capacity_match:
                            shelter['capacity'] = int(capacity_match.group())
                    
                    if shelter['name'] or shelter['address']:
                        shelters.append(shelter)
        
        return shelters
    
    def scrape_shelter_details(self, shelter_url: str) -> Dict[str, Any]:
        """Scrape detailed information for a specific shelter.
        
        Args:
            shelter_url: URL of the shelter detail page
            
        Returns:
            Detailed shelter information including coordinates and map URL
        """
        try:
            response = self.session.get(shelter_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            details = {
                'capacity': None,
                'coordinates': None,
                'description': '',
                'facilities': [],
                'map_url': None
            }
            
            # Extract the full page content
            page_text = soup.get_text()
            
            # Extract capacity from description text
            # Look for pattern: "kapacitet för XX personer"
            capacity_match = re.search(r'kapacitet för (\d+) personer', page_text, re.IGNORECASE)
            if capacity_match:
                details['capacity'] = int(capacity_match.group(1))
            
            # Extract coordinates from JavaScript variables
            # Look for: var latitude = XX.XXXX; var longitude = XX.XXXX;
            # Or: $Latitude = XX.XXXX; $Longitude = XX.XXXX;
            lat_match = re.search(r'(?:var\s+latitude|\$Latitude)\s*=\s*[\'"]?([0-9.]+)[\'"]?', page_text, re.IGNORECASE)
            lng_match = re.search(r'(?:var\s+longitude|\$Longitude)\s*=\s*[\'"]?([0-9.]+)[\'"]?', page_text, re.IGNORECASE)
            
            if lat_match and lng_match:
                details['coordinates'] = {
                    'lat': float(lat_match.group(1)),
                    'lng': float(lng_match.group(1))
                }
            
            # Extract Google Maps URL
            # Look for links to google.com/maps
            map_links = soup.find_all('a', href=re.compile(r'google\.com/maps|maps\.google\.com'))
            if map_links:
                map_url = map_links[0].get('href')
                details['map_url'] = map_url
                
                # Extract coordinates from the map URL if we don't have them yet
                # Pattern: query=LAT,LNG or q=LAT,LNG
                if not details['coordinates']:
                    coords_match = re.search(r'(?:query|q)=([0-9.]+),([0-9.]+)', map_url)
                    if coords_match:
                        details['coordinates'] = {
                            'lat': float(coords_match.group(1)),
                            'lng': float(coords_match.group(2))
                        }
            
            # If no direct Google Maps link, construct one from coordinates
            if not details['map_url'] and details['coordinates']:
                lat = details['coordinates']['lat']
                lng = details['coordinates']['lng']
                details['map_url'] = f"https://www.google.com/maps?q={lat},{lng}"
            
            # Extract main description paragraph
            # Look for the description with shelter details
            desc_paragraph = soup.find('p')
            if desc_paragraph:
                desc_text = desc_paragraph.get_text(strip=True)
                # Only use if it's a meaningful description
                if len(desc_text) > 20:
                    details['description'] = desc_text
            
            # Extract address from table if available
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'adress' in key and value:
                            details['address'] = value
            
            return details
            
        except Exception as e:
            logger.warning(f"Error scraping shelter details from {shelter_url}: {e}")
            return {}
    
    def get_mock_data(self) -> List[Dict[str, Any]]:
        """Generate mock shelter data for testing.
        
        Returns:
            List of mock shelter data
        """
        return [
            {
                'id': 'uppsala_shelter_1',
                'name': 'Skyddsrum Centralstationen',
                'address': 'Kungsgatan 65, 753 18 Uppsala',
                'capacity': 500,
                'coordinates': {'lat': 59.8586, 'lng': 17.6389},
                'district': 'Centrum',
                'accessibility_features': ['Rullstolsanpassad', 'Hiss finns'],
                'facilities': ['Toaletter', 'Ventilation', 'Nödbelysning', 'Första hjälpen'],
                'description': 'Stort skyddsrum under Centralstationen med plats för 500 personer. Fullt utrustat med moderna faciliteter.',
                'contact_info': 'Uppsala Kommun: 018-727 00 00'
            },
            {
                'id': 'uppsala_shelter_2',
                'name': 'Skyddsrum Domkyrkan',
                'address': 'Domkyrkoplan, 753 10 Uppsala',
                'capacity': 300,
                'coordinates': {'lat': 59.8583, 'lng': 17.6319},
                'district': 'Centrum',
                'accessibility_features': ['Rullstolsanpassad'],
                'facilities': ['Toaletter', 'Ventilation', 'Nödbelysning'],
                'description': 'Historiskt skyddsrum nära Domkyrkan. God tillgänglighet från centrum.',
                'contact_info': 'Uppsala Kommun: 018-727 00 00'
            },
            {
                'id': 'uppsala_shelter_3',
                'name': 'Skyddsrum Studentstaden',
                'address': 'Rackarbergsgatan 50, 752 38 Uppsala',
                'capacity': 400,
                'coordinates': {'lat': 59.8472, 'lng': 17.6467},
                'district': 'Studentstaden',
                'accessibility_features': ['Hiss finns', 'Rullstolsanpassad'],
                'facilities': ['Toaletter', 'Ventilation', 'Nödbelysning', 'Vatten', 'Första hjälpen'],
                'description': 'Modernt skyddsrum i studentområdet med god kapacitet och moderna faciliteter.',
                'contact_info': 'Uppsala Kommun: 018-727 00 00'
            },
            {
                'id': 'uppsala_shelter_4',
                'name': 'Skyddsrum Gottsunda',
                'address': 'Gottsundavägen 10, 729 30 Uppsala',
                'capacity': 250,
                'coordinates': {'lat': 59.8246, 'lng': 17.6789},
                'district': 'Gottsunda',
                'accessibility_features': ['Rullstolsanpassad'],
                'facilities': ['Toaletter', 'Ventilation', 'Nödbelysning', 'Vatten'],
                'description': 'Skyddsrum i Gottsunda med bra tillgänglighet för lokalbefolkningen.',
                'contact_info': 'Uppsala Kommun: 018-727 00 00'
            },
            {
                'id': 'uppsala_shelter_5',
                'name': 'Skyddsrum Sävja',
                'address': 'Sävjavägen 25, 756 45 Uppsala',
                'capacity': 200,
                'coordinates': {'lat': 59.8789, 'lng': 17.6123},
                'district': 'Sävja',
                'accessibility_features': ['Rullstolsanpassad', 'Hiss finns'],
                'facilities': ['Toaletter', 'Ventilation', 'Nödbelysning'],
                'description': 'Skyddsrum i norra Uppsala med god kapacitet för området.',
                'contact_info': 'Uppsala Kommun: 018-727 00 00'
            }
        ]
