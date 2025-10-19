# Google Geocoding API Setup Guide

## Current Status
❌ **Geocoding API Not Enabled** - Getting `REQUEST_DENIED` response

## Issue
The Google Cloud project needs the **Geocoding API** enabled separately from the Gemini API.

## Solution Options

### Option 1: Enable Google Geocoding API (Recommended for Production)

#### Step 1: Enable Geocoding API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** → **Library**
4. Search for "Geocoding API"
5. Click "Enable"

#### Step 2: Check Billing
1. Go to **Billing** section
2. Ensure billing account is linked
3. Note: Geocoding API has a **free tier**:
   - **$200 free credit** per month (for new users)
   - First **40,000 requests** per month are free
   - After that: **$5 per 1,000 requests**

#### Step 3: Verify API Key
Your existing `GOOGLE_API_KEY` should work once Geocoding API is enabled:
```bash
# Test the API directly
curl "https://maps.googleapis.com/maps/api/geocode/json?address=Uppsala&key=YOUR_API_KEY"

# Should return: {"status": "OK", ...}
# If still denied: Check API key restrictions in Cloud Console
```

#### Step 4: Restart Services
```bash
docker compose restart llm-engine ui
```

### Option 2: Use Alternative Geocoding (No Cost, But Limited)

If you can't enable Google Geocoding API, use **Nominatim** (OpenStreetMap's free geocoding service):

#### Modify `services/llm-engine/geocoding.py`:
```python
class GeocodingService:
    def __init__(self, api_key: Optional[str] = None, use_nominatim: bool = True):
        self.use_nominatim = use_nominatim or (api_key is None)
        self.api_key = api_key
        
        if self.use_nominatim:
            self.base_url = "https://nominatim.openstreetmap.org/search"
            logger.info("Using Nominatim (OSM) for geocoding - FREE but rate-limited")
        else:
            self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
            logger.info("Using Google Maps Geocoding API")
    
    async def geocode_location(self, location_query: str, bias_to_uppsala: bool = True):
        if self.use_nominatim:
            return await self._geocode_nominatim(location_query, bias_to_uppsala)
        else:
            return await self._geocode_google(location_query, bias_to_uppsala)
    
    async def _geocode_nominatim(self, location_query: str, bias_to_uppsala: bool):
        """Free geocoding using OpenStreetMap Nominatim."""
        try:
            query = location_query.strip()
            if bias_to_uppsala and "uppsala" not in query.lower():
                query = f"{query}, Uppsala, Sweden"
            
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }
            
            # Add viewbox to bias towards Uppsala
            if bias_to_uppsala:
                params["viewbox"] = "17.4,59.7,17.8,60.0"  # Uppsala bounds
                params["bounded"] = 1
            
            headers = {
                "User-Agent": "Uppsala-Shelter-Chatbot/1.0"  # Required by Nominatim
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
            
            return {
                "lat": float(result["lat"]),
                "lng": float(result["lon"]),
                "formatted_address": result.get("display_name", location_query),
                "place_name": result.get("address", {}).get("town", location_query),
                "query": location_query
            }
            
        except Exception as e:
            logger.error(f"Error geocoding with Nominatim: {e}", exc_info=True)
            return None
```

**Pros**:
- ✅ Free (no API key needed)
- ✅ No billing setup required
- ✅ Open source data (OpenStreetMap)

**Cons**:
- ❌ Rate limited (1 request/second)
- ❌ Less accurate than Google
- ❌ Requires User-Agent header

### Option 3: Static Location Database (Offline)

Create a JSON file with common Uppsala locations:

```json
{
  "centralstationen": {"lat": 59.8586, "lng": 17.6389, "name": "Uppsala Central Station"},
  "uppsala slott": {"lat": 59.8585, "lng": 17.6342, "name": "Uppsala Castle"},
  "kungsgatan": {"lat": 59.8575, "lng": 17.6362, "name": "Kungsgatan"},
  "fyrishov": {"lat": 59.8456, "lng": 17.6722, "name": "Fyrishov"},
  // ... add more
}
```

Load and search this file first, fallback to API if not found.

## Recommended Approach

### For Development/Testing:
Use **Option 2 (Nominatim)** - it's free and works immediately

### For Production:
Use **Option 1 (Google Geocoding API)** - better accuracy and performance

## Cost Analysis

### Google Geocoding API Pricing
- **Free tier**: 40,000 requests/month
- **After free tier**: $5 per 1,000 requests
- **Typical usage** (100 users/day, 3 searches each): ~9,000 requests/month
- **Cost**: **FREE** (within free tier)

### Nominatim (OSM)
- **Cost**: $0
- **Rate limit**: 1 request/second
- **Fair use policy**: Must cache results, provide User-Agent
- **Typical usage**: Works fine for low traffic

## Implementation Status

### Current Code
- ✅ Geocoding service implemented (`services/llm-engine/geocoding.py`)
- ✅ API endpoint created (`POST /geocode`)
- ✅ UI search box added
- ✅ Error handling in place
- ❌ **Google Geocoding API not enabled** (needs setup)

### Quick Fix (Use Nominatim)
```bash
# Modify environment variable to force Nominatim
echo "USE_NOMINATIM=true" >> .env

# Or modify geocoding.py constructor:
# GeocodingService(api_key=None)  # This forces Nominatim mode
```

## Testing Without Geocoding API

You can still test other features:
1. **Map click selection** - Works without geocoding
2. **Direct coordinate input** - Works
3. **Chat queries** - Works if user provides coordinates

Only the **location search box** requires geocoding.

## Next Steps

### For This Session (Quick Demo):
1. Document that Geocoding API needs setup
2. Optionally implement Nominatim fallback
3. Test map click functionality (works without geocoding)

### For Production Deployment:
1. Enable Google Geocoding API in Cloud Console
2. Test with real queries
3. Monitor usage and costs
4. Implement caching to reduce API calls

## Alternative: LLM-Based Geocoding

Another creative solution: Use Gemini to extract coordinates!

```python
async def llm_geocode(location_name: str) -> Optional[Dict]:
    """Use LLM to estimate coordinates for well-known locations."""
    prompt = f"""Given the location name: "{location_name}"
    
    If this is a well-known location in Uppsala, Sweden, provide the approximate
    latitude and longitude coordinates.
    
    Respond ONLY with JSON format:
    {{"lat": 59.XXXX, "lng": 17.XXXX}}
    
    If you don't know the location, respond with: {{"error": "unknown"}}
    """
    
    # Call Gemini API...
    # Parse response...
    return coordinates
```

**Pros**:
- Uses existing Gemini API (already paid for)
- Works for well-known landmarks
- Creative workaround

**Cons**:
- Less accurate than real geocoding
- LLM might hallucinate coordinates
- Slower than geocoding API

## Conclusion

The location search feature is **fully implemented** but needs Google Geocoding API enabled to work. This is a simple 5-minute setup in Google Cloud Console.

For immediate testing without API setup, use the **map click** feature which works perfectly and doesn't need geocoding!
