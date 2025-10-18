# Map & Location-Based Query Fix - Summary

## 🎯 Objective
Enable users to:
1. **Click on map** to select a location → Automatically find 5 nearest shelters
2. **Ask chatbot** general questions about shelters in Uppsala
3. **See results** on the interactive map with proper markers
4. **Get distance information** when location is selected

---

## 🔧 What Was Fixed

### 1. **Location State Management** (UI)
**File**: `services/ui/app.py`

**Changes**:
- Added `user_location_state` to persist selected location across queries
- Updated all handlers to pass and receive location state
- Location persists until user clears chat or selects new location

**Before**:
```python
# Location was lost after each query
async def respond(message, history, lang, max_d):
    ...
```

**After**:
```python
# Location persists across queries
user_location_state = gr.State(None)

async def respond(message, history, lang, max_d, user_loc):
    # user_loc is maintained throughout session
    ...
```

---

### 2. **Geographic Distance Calculation** (RAG Engine)
**File**: `services/llm-engine/rag_engine.py`

**Changes**:
- Added `_calculate_distance()` using Haversine formula
- Modified `retrieve_context()` to accept `user_location` parameter
- Retrieves 2x documents, calculates geographic distances, re-sorts by distance
- Returns top 5 nearest shelters when location is provided

**How it works**:
```python
async def retrieve_context(
    self,
    query: str,
    max_docs: int = 5,
    user_location: Optional[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    # 1. Get semantic matches from vector DB (10 docs if location provided)
    # 2. If user_location:
    #    - Calculate geographic distance for each
    #    - Sort by distance
    #    - Return top 5 nearest
    # 3. Else: return semantic matches as-is
```

**Example**:
- User clicks map at Central Station (59.8586, 17.6389)
- System queries vector DB for relevant shelters (gets 10)
- Calculates distance from Central Station to each
- Sorts by distance: 0.5km, 0.8km, 1.2km, 1.5km, 2.0km
- Returns top 5 nearest

---

### 3. **Enhanced Location Context** (RAG Engine)
**File**: `services/llm-engine/rag_engine.py`

**Changes**:
- Updated prompt to inform LLM that shelters are pre-sorted by distance
- Instructs LLM to mention distances in response
- Passes precise user coordinates to LLM

**Prompt Enhancement**:
```
VIKTIG: Användarens valda plats är 59.8586° N, 17.6389° E. 
De skyddsrum som visas i kontexten har redan sorterats efter 
geografiskt avstånd från denna plats, med det närmaste först. 
Inkludera avståndet i kilometer i ditt svar.
```

---

### 4. **Distance Display** (UI)
**File**: `services/ui/app.py`

**Changes**:
- Modified `format_sources()` to show distance when available
- Displays in meters if < 1km, kilometers if ≥ 1km
- Shows distance icon 📏

**Example Output**:
```
📚 Källor:

**1. Skyddsrum Centralstationen**
   📍 Kungsgatan 65, 753 18 Uppsala
   👥 Kapacitet: 500 personer
   🏙️ Stadsdel: Centrum
   📏 Avstånd: 0.54km

**2. Skyddsrum Domkyrkan**
   📍 Domkyrkoplan, 753 10 Uppsala
   👥 Kapacitet: 300 personer
   🏙️ Stadsdel: Centrum
   📏 Avstånd: 0.82km
```

---

### 5. **Map Click Handler** (UI)
**File**: `services/ui/app.py`

**Changes**:
- Updated `handle_location_selection()` to:
  - Parse clicked coordinates
  - Store in `user_location_state`
  - Generate automatic query "Vilka är de 5 närmaste..."
  - Pass location to streaming handler
  - Update map with results

**Flow**:
```
User clicks map at (59.8586, 17.6389)
         ↓
Coordinates captured by JavaScript
         ↓
Sent to Python via postMessage
         ↓
Parsed and validated
         ↓
Stored in user_location_state
         ↓
Auto-query: "Vilka är de 5 närmaste..."
         ↓
RAG retrieves & sorts by distance
         ↓
LLM generates response with distances
         ↓
Map updates with 5 nearest shelters + user marker
```

---

## 🎬 Usage Scenarios

### Scenario 1: User Clicks Map
**Steps**:
1. User clicks on map (e.g., Central Station)
2. Red marker appears at clicked location
3. System automatically asks: "What are the 5 nearest shelters?"
4. RAG finds nearest shelters, calculates distances
5. LLM responds with detailed info including distances
6. Map shows:
   - Red marker at user's location
   - Blue marker for closest shelter
   - Green markers for next 4 shelters
   - Circle showing search radius

**Example Response**:
```
Här är de 5 närmaste skyddsrummen till din valda plats:

1. **Skyddsrum Centralstationen** (0.54 km)
   - Adress: Kungsgatan 65, 753 18 Uppsala
   - Kapacitet: 500 personer
   - Detta är det närmaste skyddsrummet, beläget under Centralstationen

2. **Skyddsrum Domkyrkan** (0.82 km)
   - Adress: Domkyrkoplan, 753 10 Uppsala
   - Kapacitet: 300 personer
   ...
```

---

### Scenario 2: General Query Without Location
**Steps**:
1. User types: "Vilka skyddsrum finns i Flogsta?"
2. System does semantic search (no distance calculation)
3. Returns relevant shelters based on semantic match
4. Map shows all found shelters
5. No distance information (since no location selected)

**Example Response**:
```
I Flogsta och närområdet finns flera skyddsrum:

1. **Skyddsrum Flogsta**
   - Adress: Flogstavägen 25
   - Kapacitet: 250 personer
   ...
```

---

### Scenario 3: Follow-up Query With Persistent Location
**Steps**:
1. User clicks map → location stored
2. Bot shows 5 nearest shelters
3. User asks: "Finns det tillgängliga skyddsrum för rullstolsanvändare?"
4. System uses **same location** to find accessible shelters
5. Filters results + calculates distances from stored location

**Flow**:
```
Location: (59.8586, 17.6389) ← Persisted
Query: "accessible shelters"
         ↓
RAG: Get 10 shelters with "accessible" features
Calculate distances from stored location
Sort by distance
Return top 5
```

---

## 📊 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INTERACTION                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Option A: Click Map          Option B: Type Query          │
│       ↓                             ↓                        │
│  Coordinates captured         Text query entered            │
│       ↓                             ↓                        │
└───────┬─────────────────────────────┬───────────────────────┘
        │                             │
        │         ┌───────────────────┴────────────────┐
        │         │      UI SERVICE (Gradio)           │
        │         │  - Manages user_location_state     │
        │         │  - Formats questions               │
        │         └───────────────┬────────────────────┘
        │                         │
        └─────────────────────────┤
                                  │
                    ┌─────────────▼────────────────┐
                    │   LLM ENGINE SERVICE         │
                    │  - RAG Engine                │
                    │  - Enhance query with context│
                    └─────────────┬────────────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │   VECTORDB SERVICE           │
                    │  - Semantic search           │
                    │  - Return top 10 matches     │
                    └─────────────┬────────────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │   RAG ENGINE (Post-process)  │
                    │  - Calculate geo distances   │
                    │  - Sort by distance          │
                    │  - Return top 5              │
                    └─────────────┬────────────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │   LLM (Gemini)               │
                    │  - Generate response         │
                    │  - Include distances         │
                    └─────────────┬────────────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │   UI SERVICE (Display)       │
                    │  - Update chat               │
                    │  - Update sources with dist  │
                    │  - Update map with markers   │
                    └──────────────────────────────┘
```

---

## 🧪 Testing Instructions

### Test 1: Click Map for Nearest Shelters
```bash
1. Open UI at http://localhost:7860
2. Click on the map at Central Station area
3. Verify:
   ✓ Red marker appears at clicked location
   ✓ Coordinate input shows "59.8586,17.6389"
   ✓ Auto-query appears in chat
   ✓ Bot responds with 5 shelters
   ✓ Distances shown (e.g., "0.54km")
   ✓ Map updates with shelter markers
   ✓ Blue marker for closest, green for others
```

### Test 2: General Query Without Location
```bash
1. Type: "Vilka skyddsrum finns i Uppsala centrum?"
2. Press Enter
3. Verify:
   ✓ Bot responds with relevant shelters
   ✓ No distance information shown
   ✓ Map shows found shelters
   ✓ Semantic relevance (not distance) determines order
```

### Test 3: Location Persistence
```bash
1. Click map at a location
2. Wait for response
3. Type: "Finns det större skyddsrum?"
4. Verify:
   ✓ Bot considers location from step 1
   ✓ Shows larger shelters near that location
   ✓ Distances calculated from original click point
```

### Test 4: Clear and Reset
```bash
1. Click map, get nearest shelters
2. Click "Clear" button
3. Verify:
   ✓ Chat history cleared
   ✓ Location reset (user_location_state = None)
   ✓ Map reset to initial Uppsala view
```

---

## 🔍 Technical Details

### Haversine Formula
Used to calculate great-circle distance between two points on Earth:

```python
def _calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    
    # Convert to radians
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c  # Distance in km
```

**Accuracy**: ±0.5% for most distances

---

### Coordinate System
- **Format**: Decimal degrees (DD)
- **Example**: 59.8586° N, 17.6389° E
- **Precision**: 6 decimal places ≈ 0.1 meter accuracy
- **Range**: 
  - Latitude: -90 to +90
  - Longitude: -180 to +180
- **Uppsala bounds**: 
  - Lat: 59.7 to 60.0
  - Lng: 17.5 to 17.8

---

### Vector Search vs Geographic Search

| Aspect | Vector (Semantic) Search | Geographic Search |
|--------|-------------------------|-------------------|
| **Method** | Embeddings + cosine similarity | Haversine formula |
| **Input** | Text query | Lat/Lng coordinates |
| **Output** | Semantically relevant documents | Geographically nearest points |
| **Use Case** | "Tillgängliga skyddsrum" | "Nearest to 59.8586, 17.6389" |
| **Speed** | Fast (indexed) | Slower (post-processing) |
| **Accuracy** | Context-aware | Distance-accurate |

**Our Approach**: Hybrid
1. First: Semantic search (get relevant candidates)
2. Then: Geographic filter (sort by distance)
3. Best of both: Relevant AND nearest

---

## 📝 Files Modified

| File | Changes | Impact |
|------|---------|--------|
| `services/ui/app.py` | - Added `user_location_state`<br>- Updated handlers<br>- Enhanced `format_sources()` | High |
| `services/llm-engine/rag_engine.py` | - Added `_calculate_distance()`<br>- Updated `retrieve_context()`<br>- Enhanced prompts | High |
| `services/ui/interactive_map.py` | *(No changes needed - already working)* | - |

**Total Lines Changed**: ~150 lines

---

## 🚀 Benefits

### For Users
✅ **Intuitive**: Just click on map  
✅ **Accurate**: True geographic distances  
✅ **Fast**: Real-time streaming responses  
✅ **Informative**: Distances shown clearly  
✅ **Flexible**: Works with or without location  

### For System
✅ **Hybrid Search**: Semantic + Geographic  
✅ **Persistent State**: Location remembered  
✅ **Efficient**: Only calculates distance when needed  
✅ **Scalable**: Works with any number of shelters  

---

## 🐛 Known Limitations

1. **Distance Accuracy**: ±0.5% (good enough for city-scale)
2. **No Routing**: Shows straight-line distance, not walking distance
3. **No Real-time Updates**: Doesn't track user's moving location
4. **Browser Compatibility**: Map clicks work on modern browsers only

---

## 🎯 Future Enhancements

1. **Walking Directions**: Integrate Google Directions API
2. **Live Tracking**: Use browser geolocation for real-time position
3. **Multi-point Route**: Find optimal route to visit multiple shelters
4. **Traffic Awareness**: Adjust recommendations based on travel time
5. **Mobile Optimization**: Better touch interactions on mobile
6. **Offline Support**: Cache map tiles for offline use

---

## ✅ Success Criteria

- [x] Users can click map to select location
- [x] System finds 5 nearest shelters
- [x] Distances calculated accurately
- [x] Map displays user marker + shelter markers
- [x] Location persists across queries
- [x] General queries work without location
- [x] Sources show distance information
- [x] Streaming responses work correctly

---

**Enhancement Date**: October 18, 2025  
**Status**: ✅ Implemented & Documented  
**Version**: 1.2.0
