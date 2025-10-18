# Testing Guide: Map & Location Features

## 🎯 Testing Objectives

Test the new map and location-based query functionality to ensure:
1. Users can click map to select location
2. System finds and displays 5 nearest shelters
3. Distances are calculated correctly
4. General queries work without location
5. Location persists across queries
6. Map updates dynamically with results

---

## 🚀 Quick Start

### 1. Access the Application
```bash
# Open in browser
http://localhost:7860
```

### 2. Services Status Check
```bash
# Check all services are running
docker ps | grep shelter

# Expected output:
# shelter-ui          Up
# shelter-llm-engine  Up
# shelter-vectordb    Up (healthy)
# shelter-scraper     Up
```

---

## 🧪 Test Scenarios

### Test 1: Click Map for Nearest Shelters ⭐ PRIMARY

**Objective**: Verify location-based search works

**Steps**:
1. Open UI at http://localhost:7860
2. Look at the right side - you'll see an interactive map
3. **Click somewhere on the map** (e.g., center of Uppsala)
4. Observe the changes

**Expected Results**:
✅ A red marker appears where you clicked  
✅ Coordinate input shows coordinates (e.g., `59.8586,17.6389`)  
✅ Chat automatically updates with query: "Vilka är de 5 närmaste skyddsrummen..."  
✅ Bot streams response mentioning 5 shelters with distances  
✅ Sources panel shows shelters with distance info (e.g., "📏 Avstånd: 0.54km")  
✅ Map updates showing:
  - Red marker at your location
  - Blue marker for closest shelter
  - Green markers for other 4 shelters
  - Circle showing search radius

**Example Response**:
```
Här är de 5 närmaste skyddsrummen till din valda plats:

1. Skyddsrum Centralstationen (0.54 km)
   - Beläget vid Kungsgatan 65
   - Kapacitet: 500 personer
   - Detta är det närmaste skyddsrummet

2. Skyddsrum Domkyrkan (0.82 km)
   ...
```

**If it fails**:
- Check browser console for JavaScript errors
- Verify coordinates_input is updating
- Check LLM engine logs: `docker logs shelter-llm-engine -f`

---

### Test 2: General Query Without Location

**Objective**: Verify semantic search works without location

**Steps**:
1. **Without clicking the map**, type in the chat:
   ```
   Vilka skyddsrum finns i Uppsala centrum?
   ```
2. Press Enter or click "Skicka"

**Expected Results**:
✅ Bot responds with relevant shelters in Uppsala centrum  
✅ NO distance information shown (since no location selected)  
✅ Map shows the found shelters  
✅ Shelters ordered by semantic relevance, not distance  

**Example Response**:
```
I Uppsala centrum finns flera skyddsrum:

1. Skyddsrum Centralstationen
   - Adress: Kungsgatan 65, 753 18 Uppsala
   - Kapacitet: 500 personer
   - Beläget under Centralstationen

2. Skyddsrum Domkyrkan
   ...
```

**Note**: No "📏 Avstånd" shown in sources!

---

### Test 3: Location Persistence

**Objective**: Verify location is remembered across queries

**Steps**:
1. Click map at a specific location (e.g., Central Station)
2. Wait for response showing 5 nearest shelters
3. **Without clicking map again**, type:
   ```
   Finns det större skyddsrum?
   ```
4. Press Enter

**Expected Results**:
✅ Bot considers the same location from step 1  
✅ Shows larger capacity shelters near that location  
✅ Distances still calculated from original click point  
✅ Map markers update but user's red marker stays  

**Example**:
```
Click map → Get 5 nearest (200-500 capacity)
Ask "större skyddsrum?" → Get larger ones (500+ capacity) still near clicked location
```

---

### Test 4: Multiple Queries with Different Locations

**Objective**: Verify location can be changed

**Steps**:
1. Click map in **north Uppsala** (e.g., Boländerna area)
2. Note the 5 nearest shelters
3. Click map in **south Uppsala** (e.g., Gottsunda area)
4. Note the NEW 5 nearest shelters

**Expected Results**:
✅ First click shows shelters near north Uppsala  
✅ Second click updates to shelters near south Uppsala  
✅ Different shelters shown based on new location  
✅ Distances recalculated from new position  

---

### Test 5: Clear and Reset

**Objective**: Verify reset functionality

**Steps**:
1. Click map and get nearest shelters
2. Do a few queries
3. Click **"Rensa"** (Clear) button

**Expected Results**:
✅ Chat history cleared  
✅ Location reset (internal state cleared)  
✅ Map resets to initial Uppsala overview  
✅ No red user marker visible  
✅ Next query will be semantic (not location-based) unless map clicked again  

---

### Test 6: Specific Location Queries

**Objective**: Test enhanced location detection

**Steps**:
Try these queries:
```
1. "Skyddsrum nära Ångström"
2. "Shelter near Central Station"
3. "Närmaste skyddsrum till Ekonomikum"
4. "Skyddsrum i Flogsta"
```

**Expected Results**:
✅ Bot identifies the location from query  
✅ Uses geographic knowledge to find nearby shelters  
✅ Explains proximity based on districts/addresses  
✅ Map shows relevant shelters  

**Example for "Skyddsrum nära Ångström"**:
```
Vid Ångströmlaboratoriet i norra Uppsala finns följande skyddsrum i närheten:

1. Skyddsrum Boländerna
   - Ligger i samma område som Ångström
   ...
```

---

### Test 7: Accessibility Query

**Objective**: Test specific feature queries

**Steps**:
1. Click map somewhere
2. Type:
   ```
   Finns det tillgängliga skyddsrum för rullstolsanvändare?
   ```

**Expected Results**:
✅ Bot filters for accessible shelters  
✅ Shows only those with accessibility features  
✅ Distances shown from clicked location  
✅ Map shows only accessible shelters  

---

### Test 8: Capacity Query

**Objective**: Test capacity filtering

**Steps**:
1. Type (without clicking map):
   ```
   Vilka skyddsrum har kapacitet för över 400 personer?
   ```

**Expected Results**:
✅ Bot shows large capacity shelters  
✅ Mentions capacity in response  
✅ No distance info (no location clicked)  
✅ Map shows high-capacity shelters  

---

### Test 9: Language Switch

**Objective**: Verify bilingual support

**Steps**:
1. Click "⚙️ Inställningar" (Settings) tab
2. Switch language to "English"
3. Go back to "💬 Chat" tab
4. Click map
5. Observe auto-query is in English

**Expected Results**:
✅ Auto-query: "What are the 5 nearest shelters..."  
✅ Bot responds in English  
✅ Distance shown as "Distance" not "Avstånd"  
✅ Map tooltips update to English  

---

### Test 10: Distance Accuracy Check

**Objective**: Verify distance calculations are reasonable

**Steps**:
1. Click map at Uppsala Central Station (~59.8586, 17.6389)
2. Check distances in the response

**Expected Approximate Distances** (from Central Station):
- Centralstationen shelter: < 0.5 km (very close)
- Domkyrkan shelter: ~0.8 km
- Studentstaden shelters: ~2-3 km
- Gottsunda shelters: ~5-8 km

**How to verify**:
✅ Use Google Maps to check rough distances  
✅ Closer shelters should have smaller km values  
✅ Shelters should be listed in ascending distance order  

---

## 🐛 Troubleshooting

### Map Click Not Working

**Symptoms**: Clicking map doesn't do anything

**Checks**:
1. Open browser Developer Tools (F12)
2. Look at Console tab for JavaScript errors
3. Check if coordinates_input updates when clicking

**Solution**:
```bash
# Restart UI service
docker restart shelter-ui

# Check logs
docker logs shelter-ui -f
```

---

### No Distance Shown

**Symptoms**: Sources don't show "📏 Avstånd: X.XXkm"

**Possible Causes**:
1. Location not set (didn't click map)
2. Shelter missing coordinates
3. Distance calculation failed

**Check**:
```bash
# Check if shelters have coordinates
curl http://localhost:8000/collections/uppsala_shelters/documents | jq '.documents[0].metadata'

# Should show coordinates_lat and coordinates_lng
```

---

### Wrong Shelters Shown

**Symptoms**: Shelters shown are not nearest to clicked location

**Check**:
1. Verify coordinates are being passed to LLM engine
2. Check LLM engine logs for "user_location"
3. Verify distance calculation is working

```bash
# Check LLM engine logs
docker logs shelter-llm-engine -f

# Look for:
# "Filtering by user location: {'lat': 59.8586, 'lng': 17.6389}"
# "Filtered to 5 nearest shelters"
```

---

### Map Shows No Shelters

**Symptoms**: Map shows only red user marker, no shelter markers

**Possible Causes**:
1. Shelters in sources missing coordinates
2. Map generation failed
3. Coordinates in wrong format

**Check**:
```bash
# Check UI logs
docker logs shelter-ui --tail 50 | grep -i "map\|coord\|marker"
```

---

## 📊 Performance Benchmarks

Expected response times:

| Action | Expected Time |
|--------|--------------|
| Map click detection | < 100ms |
| Coordinate parsing | < 10ms |
| Vector search | 100-300ms |
| Distance calculation (5 shelters) | < 50ms |
| LLM response (streaming) | 2-5 seconds |
| Map update | < 500ms |
| **Total (click to response)** | **3-6 seconds** |

---

## ✅ Success Checklist

After testing, verify:

- [ ] Map click adds red marker
- [ ] Coordinates captured correctly
- [ ] Auto-query generates
- [ ] Bot responds with 5 shelters
- [ ] Distances calculated accurately
- [ ] Distances displayed in sources
- [ ] Map updates with shelter markers
- [ ] Location persists across queries
- [ ] General queries work without location
- [ ] Clear button resets everything
- [ ] Language switching works
- [ ] Semantic search still functional
- [ ] Streaming responses work
- [ ] No console errors
- [ ] Mobile responsive (if testing on mobile)

---

## 🎓 Tips for Best Results

1. **Click clearly on map**: Click directly on the map, not on existing markers
2. **Wait for streaming**: Let the bot finish streaming before next query
3. **Use the search radius circle**: Visual indicator of how far shelters are
4. **Try both modes**: Test with and without clicking map to see the difference
5. **Check all distances**: Verify they make geographic sense
6. **Test edge cases**: Try clicking outside Uppsala bounds
7. **Test on mobile**: Responsive design should work on phones too

---

## 📸 Expected Screenshots

### After Map Click:
- Red marker at clicked location
- Chat showing auto-query
- Bot response with 5 shelters listed
- Distance shown for each (0.5km, 1.2km, etc.)
- Map with multiple colored markers
- Search radius circle

### General Query (no click):
- Chat showing user's question
- Bot response with relevant shelters
- NO distance information
- Map showing found shelters
- No red user marker

---

## 🔗 Quick Links

- **UI**: http://localhost:7860
- **LLM Engine API**: http://localhost:8001/docs
- **VectorDB API**: http://localhost:8000/docs
- **Scraper API**: http://localhost:8002/docs

---

## 📝 Feedback & Issues

If you find bugs or have suggestions, note:
- What you did (exact steps)
- What you expected
- What actually happened
- Browser and device used
- Screenshots if possible
- Console errors if any

---

**Last Updated**: October 18, 2025  
**Version**: 1.2.0  
**Status**: Ready for Testing ✅
