# Testing the Location Search Feature

## Quick Test Guide

### Prerequisites
```bash
# Make sure services are running
docker compose ps

# All should show "Up" status:
# - shelter-vectordb
# - shelter-scraper  
# - shelter-llm-engine
# - shelter-ui

# Access UI at: http://localhost:7860
```

### Test 1: Location Name Search
**Goal**: Verify geocoding and shelter finding works

1. Open UI: http://localhost:7860
2. Look for the search box labeled "🔍 Search Location"
3. Type: **Centralstationen**
4. Click the **📍 Find Shelters** button

**Expected Result:**
- Chat should show automatic query: "Vilka är de 5 närmaste skyddsrummen till Centralstationen..."
- Map updates with markers showing shelters
- Red marker at Uppsala Central Station
- Blue/green markers for nearby shelters
- Chat response lists 5 shelters with distances

### Test 2: Map Click Selection
**Goal**: Verify click-to-search functionality

1. Click anywhere on the map
2. Wait for automatic query

**Expected Result:**
- "Selected Coordinates" textbox updates with lat/lng
- Chat shows query with coordinates
- Map updates with shelters near clicked location
- Red marker appears where you clicked

### Test 3: Different Locations
**Goal**: Test various Uppsala locations

Try searching for:
- **Uppsala Slott** (Uppsala Castle)
- **Kungsgatan**
- **Fyrishov** (Swimming center)
- **Polacksbacken** (University area)
- **Stenhagen** (Neighborhood)

**Expected Result:**
- Each location should geocode successfully
- Should find 5 nearest shelters
- Map should center on the location
- Distances should be reasonable (< 5 km in central Uppsala)

### Test 4: Error Handling
**Goal**: Verify graceful failure handling

Try searching for:
- **Invalid location** (e.g., "asdfasdf")
- **Empty search** (click Find without typing)
- **Non-Uppsala location** (e.g., "Stockholm")

**Expected Result:**
- Invalid: Error message shown in chat
- Empty: No action or error message
- Non-Uppsala: Should still work but bias warnings may appear

### Test 5: Natural Language Queries
**Goal**: Test location extraction from chat

Type these in the chat (not search box):
- "Find shelters near Centralstationen"
- "Vilka skyddsrum finns vid Uppsala Slott?"
- "Show me shelters around Kungsgatan"

**Expected Result:**
- LLM should understand location context
- May or may not auto-geocode (depends on LLM interpretation)
- Should provide relevant shelter information

### Test 6: Distance Accuracy
**Goal**: Verify distance calculations

1. Search for "Centralstationen"
2. Note the distances shown for each shelter
3. Manually verify on Google Maps

**Expected Result:**
- Distances should be within ±100m of Google Maps
- Closest shelter should actually be the nearest one
- All 5 shelters should be in Uppsala

### Test 7: State Persistence
**Goal**: Verify location state persists across queries

1. Search for "Centralstationen"
2. Wait for results
3. Type a follow-up question: "Tell me more about the first shelter"

**Expected Result:**
- Location context should persist
- LLM should remember the previous shelter list
- Can ask follow-up questions about specific shelters

### Test 8: Clear and Reset
**Goal**: Verify state cleanup

1. Search for a location
2. Click "Clear" button

**Expected Result:**
- Chat history clears
- Map resets to initial Uppsala view
- Location state resets
- Can start fresh search

## API Testing

### Test Geocoding Endpoint Directly
```bash
# Test geocoding API
curl -X POST http://localhost:8001/geocode \
  -H "Content-Type: application/json" \
  -d '{"location":"Centralstationen Uppsala", "bias_to_uppsala":true}'

# Expected response:
# {
#   "success": true,
#   "lat": 59.8586,
#   "lng": 17.6389,
#   "formatted_address": "Uppsala Central Station, Uppsala, Sweden",
#   "place_name": "Centralstationen",
#   "query": "Centralstationen Uppsala"
# }
```

### Test with Different Locations
```bash
# Test Uppsala Castle
curl -X POST http://localhost:8001/geocode \
  -H "Content-Type: application/json" \
  -d '{"location":"Uppsala Slott"}'

# Test neighborhood
curl -X POST http://localhost:8001/geocode \
  -H "Content-Type: application/json" \
  -d '{"location":"Stenhagen Uppsala"}'

# Test street address
curl -X POST http://localhost:8001/geocode \
  -H "Content-Type: application/json" \
  -d '{"location":"Kungsgatan 55 Uppsala"}'
```

### Test Error Cases
```bash
# Invalid location
curl -X POST http://localhost:8001/geocode \
  -H "Content-Type: application/json" \
  -d '{"location":"InvalidLocationName12345"}'

# Should return: {"success": false}
```

## Debugging

### Check Logs
```bash
# LLM Engine logs (geocoding happens here)
docker logs shelter-llm-engine --tail 50

# UI logs (search button handler)
docker logs shelter-ui --tail 50

# Look for:
# - "Geocoding location: ..."
# - "Successfully geocoded to (lat, lng)"
# - "Failed to geocode location: ..."
```

### Common Issues

**Issue**: "⚠️ Could not find location" error
- **Cause**: Google API key not set or invalid
- **Fix**: Check GOOGLE_API_KEY in environment
- **Verify**: `docker exec shelter-llm-engine env | grep GOOGLE_API_KEY`

**Issue**: Search button doesn't respond
- **Cause**: UI event handler not connected
- **Fix**: Check browser console for JavaScript errors
- **Verify**: Refresh page and try again

**Issue**: Map doesn't update after search
- **Cause**: Map rendering issue
- **Fix**: Check map HTML generation in logs
- **Verify**: Look for "Map HTML generated successfully"

**Issue**: Distances seem wrong
- **Cause**: Coordinate parsing or Haversine calculation error
- **Fix**: Check lat/lng values in logs
- **Verify**: Compare with Google Maps manually

### Verify Google API
```bash
# Test if Geocoding API is enabled
curl "https://maps.googleapis.com/maps/api/geocode/json?address=Uppsala&key=YOUR_API_KEY"

# Should return JSON with status: "OK"
# If status is "REQUEST_DENIED", API not enabled in Google Cloud Console
```

## Performance Benchmarks

### Expected Timings
- **Geocoding**: 200-500ms
- **Semantic search**: 50-150ms  
- **Distance calculation**: <1ms
- **LLM streaming**: 2-5s (first token)
- **Map rendering**: 50-100ms

**Total**: 3-6 seconds from button click to first response

### Load Testing
```bash
# Test geocoding performance
for i in {1..10}; do
  time curl -X POST http://localhost:8001/geocode \
    -H "Content-Type: application/json" \
    -d '{"location":"Centralstationen"}'
done

# Average should be < 500ms
```

## Success Criteria

✅ **Functional**:
- [ ] Can search by location name
- [ ] Can click map to select location
- [ ] Finds 5 nearest shelters
- [ ] Shows distances in km/m
- [ ] Updates map with markers
- [ ] Handles errors gracefully

✅ **Performance**:
- [ ] Response time < 6 seconds
- [ ] Geocoding < 500ms
- [ ] No timeouts or crashes

✅ **UX**:
- [ ] Intuitive search box placement
- [ ] Clear button labels
- [ ] Helpful error messages
- [ ] Bilingual support works

## Screenshots to Capture

1. **Before search**: Initial map view
2. **Search box**: Typing location name
3. **After search**: Map with markers and chat response
4. **Distance display**: Showing km/m values
5. **Error case**: Invalid location error message

## Reporting Bugs

If you find issues, please report:
- **What you did**: Step-by-step
- **What happened**: Actual behavior
- **What you expected**: Expected behavior
- **Logs**: Relevant log entries
- **Screenshot**: If UI-related

Example:
```
Bug: Geocoding fails for "Uppsala Slott"

Steps:
1. Type "Uppsala Slott" in search box
2. Click "Find Shelters"

Actual: Shows error "Could not find location"
Expected: Should find Uppsala Castle

Logs:
2025-10-18 20:15:45 - geocoding - WARNING - No geocoding results for query: Uppsala Slott

Environment:
- Docker version: 24.0.5
- Browser: Chrome 118
- API Key: Set (last 4 chars: ab12)
```

## Next Steps After Testing

If all tests pass:
1. ✅ Feature is ready for production
2. 📝 Update user documentation
3. 🎓 Create user tutorial video
4. 📊 Set up monitoring/analytics

If tests fail:
1. 📋 Document failures
2. 🔍 Debug with logs
3. 🛠️ Fix issues
4. 🔄 Retest

## Conclusion

This testing guide covers all major functionality of the location search feature. Complete these tests to ensure the feature works correctly before considering it production-ready.

For more details, see:
- `LOCATION_SEARCH_ENHANCEMENT.md` - Full implementation docs
- `TESTING_GUIDE.md` - General testing procedures
- `QUICK_REFERENCE.md` - API endpoints reference
