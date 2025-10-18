# Quick Reference: Using the Map Feature

## 🗺️ Two Ways to Find Shelters

### Method 1: Click on Map 📍
**When to use**: You want to find shelters nearest to a specific location

**How**:
1. Click anywhere on the map (right side of screen)
2. Red marker appears at your click point
3. System automatically finds 5 nearest shelters
4. Bot explains each shelter with distance info
5. Map shows all 5 with colored markers

**Example**:
```
You click → Uppsala Central Station area
Bot says → "Here are the 5 nearest shelters:"
           1. Centralstationen (0.5 km)
           2. Domkyrkan (0.8 km)
           3. ...
Map shows → Red marker (your location)
           Blue marker (closest shelter)
           Green markers (other 4 shelters)
```

---

### Method 2: Ask in Chat 💬
**When to use**: You want general information about shelters

**How**:
1. Type your question in the chat box
2. Press Enter or click "Skicka"
3. Bot answers based on content, not distance
4. Map shows relevant shelters

**Example Questions**:
- "Vilka skyddsrum finns i Uppsala centrum?"
- "Finns det tillgängliga skyddsrum för rullstolsanvändare?"
- "Vilket är det största skyddsrummet?"
- "Skyddsrum nära Ångström"

---

## 🎯 Understanding the Map

### Markers
- **🔴 Red marker**: Your selected location (where you clicked)
- **🔵 Blue marker**: Closest shelter to you
- **🟢 Green markers**: Other nearby shelters
- **⭕ Circle**: Search radius showing how far shelters are

### Clicking Map
- Click anywhere in Uppsala area
- Click multiple times to change location
- Each click updates the results

---

## 📏 Reading Distance Information

### In Chat Response
```
1. Skyddsrum Centralstationen (0.54 km)
   ↑ Shelter name           ↑ Distance from your location
```

### In Sources Panel
```
📚 Källor:

**1. Skyddsrum Centralstationen**
   📍 Kungsgatan 65, 753 18 Uppsala
   👥 Kapacitet: 500 personer
   🏙️ Stadsdel: Centrum
   📏 Avstånd: 0.54km  ← Distance shown here
```

### Distance Units
- **Meters** (m): If less than 1 km (e.g., 850m)
- **Kilometers** (km): If 1 km or more (e.g., 2.3km)

---

## 🔄 Location Memory

### Your location is remembered!
After clicking the map, your location stays active for:
- Follow-up questions
- Multiple queries
- Different filters

**Example**:
```
1. Click map → Get 5 nearest shelters
2. Ask "Finns det större?" → Get larger shelters, still near clicked location
3. Ask "Tillgängliga?" → Get accessible shelters, still near clicked location
```

### To reset location:
Click **"Rensa"** (Clear) button to:
- Clear chat history
- Reset location
- Start fresh

---

## 💡 Pro Tips

### Finding Nearest Shelters
1. **Zoom in** on the map for more precision
2. **Click on landmarks** you know (stations, buildings)
3. **Check the circle** to see search radius
4. **Look at blue marker first** - it's always closest

### Better Questions
Instead of: "Where are shelters?"  
Try: "Vilka skyddsrum finns nära Centralstationen?"

Instead of: "Big shelters?"  
Try: "Vilka skyddsrum har kapacitet för över 400 personer?"

### Using Both Methods Together
1. **Click map** to find 5 nearest
2. **Ask follow-up** about specific features
3. **Location stays** for filtered results

Example flow:
```
Click map → Get 5 nearest
Ask "Vilka har hiss?" → Get those with elevator, from the 5 found
```

---

## 🌐 Language Support

### Svenska (Swedish)
- Default language
- "Avstånd" for distance
- "Kapacitet" for capacity

### English
1. Click **"⚙️ Inställningar"** tab
2. Select **"English"**
3. Return to **"💬 Chat"** tab

All responses, distances, and labels update to English!

---

## ❓ Common Questions

### Q: Why don't I see distances?
**A**: You need to click the map first! Distances only show when you select a location.

### Q: Can I use my current GPS location?
**A**: Click the 📍 locate button on the map (top-left) to use your device's GPS.

### Q: How accurate are the distances?
**A**: Very accurate! We use the Haversine formula for geographic distance (±0.5%).

### Q: Why do results change when I click different places?
**A**: The system finds the 5 nearest shelters to wherever you click!

### Q: Can I search without clicking the map?
**A**: Yes! Just type your question. The bot will use semantic search instead of distance.

### Q: What if I click outside Uppsala?
**A**: The map validates clicks are within Uppsala area. Invalid clicks are ignored.

---

## 🎮 Try These Examples

### Example 1: Find Nearest to You
```
Action: Click map at your approximate location
Result: 5 nearest shelters with exact distances
```

### Example 2: Accessible Shelters
```
Action: Click map, then ask "Tillgängliga skyddsrum?"
Result: Accessible shelters near your clicked location
```

### Example 3: Large Capacity Near Central Station
```
Action: Click on Central Station area
        Wait for results
        Ask "Vilka har kapacitet över 400?"
Result: Large shelters near Central Station with distances
```

### Example 4: General Search
```
Action: Type "Skyddsrum i Gottsunda" (don't click map)
Result: All shelters in Gottsunda district
```

---

## 📱 Mobile Users

### Touch Interactions
- **Tap map** to select location (works like click)
- **Pinch zoom** to zoom in/out
- **Swipe** to pan around Uppsala
- **Tap markers** to see popup info

### Best Practices
- Use portrait mode for better chat visibility
- Zoom in before tapping for precision
- Use fullscreen button (↗️) for bigger map view

---

## 🔧 If Something Doesn't Work

### Map not responding to clicks?
1. Refresh the page (F5)
2. Check you're clicking the map, not markers
3. Try clicking a different area

### No shelters shown on map?
1. Wait for response to complete (streaming)
2. Check if sources panel shows shelters
3. Look for console errors (F12)

### Wrong distances?
1. Verify your click was where you intended
2. Check the red marker position
3. Compare with Google Maps for sanity check

---

## 📞 Need More Help?

- **Documentation**: See `TESTING_GUIDE.md` for detailed testing
- **Technical**: See `MAP_FIX_SUMMARY.md` for technical details
- **General**: See `ENHANCEMENT_SUMMARY.md` for overview

---

**Quick Access**: http://localhost:7860  
**Version**: 1.2.0  
**Updated**: October 18, 2025

---

## 🎯 Quick Shortcuts

| Action | Shortcut |
|--------|----------|
| Submit query | `Enter` key |
| Clear chat | Click "Rensa" |
| Change language | ⚙️ → Language |
| Fullscreen map | ↗️ button on map |
| Use GPS location | 📍 button on map |
| Example questions | Click on examples below chat |

---

**Happy Shelter Hunting! 🏠**
