# 🚀 Quick Start: Intelligent Location Extraction

## Try It Now!

Open your browser: **http://localhost:7860**

## Example Queries

### Swedish 🇸🇪

```
5 närmaste skyddsrummen från Ångströmlaboratoriet
```
→ Extracts "Ångströmlaboratoriet", geocodes it, finds 5 nearest shelters

```
Jag är vid Centralstationen, var finns närmaste skyddsrummet?
```
→ Extracts "Centralstationen", finds closest shelter

```
Skyddsrum nära Uppsala Slott
```
→ Extracts "Uppsala Slott", shows nearby shelters

### English 🇬🇧

```
Find 3 nearest shelters from Fyrishov
```
→ Extracts "Fyrishov", finds 3 nearest shelters

```
I'm at Central Station, where is the nearest shelter?
```
→ Extracts "Central Station", finds closest shelter

```
Shelters near Resecentrum
```
→ Extracts "Resecentrum", shows nearby shelters

## What to Look For

### ✅ Map Markers

- 🔴 **Red** - Your location (extracted from chat)
- 🔵 **Blue** - Closest shelter
- 🟢 **Green** - Other nearby shelters
- ⭕ **Circle** - Search radius (5km default)

### ✅ Chat Response

The LLM will respond with shelter details including:
- Name
- Address
- Capacity
- District
- **Distance** from your location

## Test the Feature

### 1. Location Extraction Test

Try queries with different formats:
- "från [location]" (Swedish)
- "near [location]" (English)
- "vid [location]" (Swedish)
- "i [location]" (Swedish)

### 2. Multi-Turn Conversation

```
User: "5 skyddsrum från Ångströmlaboratoriet"
→ System finds 5 shelters

User: "Visa mig fler"
→ System uses same location, finds more shelters
```

### 3. Different Radius

Use the slider to adjust radius (0.5-10km):
1. Search "Centralstationen"
2. Adjust radius to 2km
3. Click "Find Shelters"
4. See only shelters within 2km

## Supported Location Keywords

### Swedish
- `från` (from)
- `vid` (at)
- `nära` (near)
- `i` (in)

### English
- `from`
- `at`
- `near`
- `in`

## Known Uppsala Locations

Test with these popular locations:

1. **Ångströmlaboratoriet** - University physics building
2. **Centralstationen** - Central train station
3. **Uppsala Slott** - Uppsala Castle
4. **Fyrishov** - Swimming complex
5. **Resecentrum** - Travel center
6. **Gottsunda** - District
7. **Centrum** - City center

## Performance

- **Location Extraction**: <1ms
- **Geocoding**: ~300ms
- **Search & Results**: ~150ms
- **Total**: < 500ms overhead

## Troubleshooting

### Location not extracted?
✅ Ensure capitalization: "Centralstationen" not "centralstationen"
✅ Use supported keywords: från, near, vid, etc.

### No results?
✅ Location might be too far from Uppsala
✅ Try increasing radius slider
✅ Check spelling of location name

### Map not updating?
✅ Wait for response to complete (streaming)
✅ Check browser console for errors
✅ Refresh page if needed

## Services Status

Check if all services are running:

```bash
docker ps
```

Should show 4 containers:
- ✅ shelter-ui (7860)
- ✅ shelter-llm-engine (8001)
- ✅ shelter-vectordb (8000)
- ✅ shelter-scraper (8002)

## View Logs

```bash
docker logs shelter-ui
docker logs shelter-llm-engine
```

Look for:
```
INFO - Extracted location from query: Ångströmlaboratoriet
INFO - Geocoded 'Ångströmlaboratoriet' to (59.8395, 17.6470)
INFO - Filtered by 5.0km radius: 87 → 12 shelters
```

## Stop Services

```bash
cd /home/habenhadush/github/mia/y2/p5/llm/project/shelter-chatbot
docker compose down
```

## Start Services

```bash
cd /home/habenhadush/github/mia/y2/p5/llm/project/shelter-chatbot
docker compose up -d
```

## Full Documentation

See these files for complete details:
- `INTELLIGENT_LOCATION_EXTRACTION.md` - Feature documentation
- `IMPLEMENTATION_SUMMARY.md` - Implementation details
- `FREE_GEOCODING_GUIDE.md` - Geocoding setup
- `RADIUS_SEARCH_FEATURE.md` - Radius filtering

## 🎉 Enjoy Your Smart Shelter Chatbot!

The system will now automatically understand location references in your natural language queries and find the nearest emergency shelters in Uppsala! 🚀
