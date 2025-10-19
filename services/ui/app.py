"""Gradio UI for Uppsala Shelter Chatbot with map visualization and streaming."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import gradio as gr
import httpx
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime
import asyncio
import json

from map_generator import MapGenerator
from interactive_map import (
    create_interactive_map, 
    create_initial_interactive_map,
    parse_coordinates,
    calculate_distance
)
from shared.config import UIConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize configuration
config = UIConfig()
map_generator = MapGenerator(vectordb_url=config.VECTORDB_URL)

# Translations (keeping your existing translations)
TRANSLATIONS = {
    "sv": {
        "title": "🏠 Uppsala Skyddsrum Chatbot",
        "description": """Välkommen till Uppsala Skyddsrums-assistenten! 
        Jag kan hjälpa dig hitta information om skyddsrum i Uppsala. 
        Fråga mig om platser, kapacitet, tillgänglighet och mer.""",
        "chat_placeholder": "Skriv din fråga här...",
        "submit": "Skicka",
        "clear": "Rensa",
        "examples_title": "Exempel på frågor:",
        "map_title": "🗺️ Karta över skyddsrum",
        "map_description": "Visa alla skyddsrum på en interaktiv karta",
        "settings_title": "⚙️ Inställningar",
        "language_label": "Språk / Language",
        "max_docs_label": "Max antal källor",
        "filter_district": "Filtrera efter stadsdel",
        "update_map": "Uppdatera karta",
        "all_districts": "Alla",
        "error_message": "⚠️ Kunde inte ansluta till LLM Engine. Kontrollera att tjänsten körs.",
        "sources_title": "📚 Källor:",
        "sources_placeholder": "📚 Källor visas här efter varje fråga",
        "no_sources": "Inga källor hittades.",
        "capacity": "Kapacitet",
        "district": "Stadsdel",
        "people": "personer",
        "about_title": "Om tjänsten",
        "about_text": """Denna chatbot använder:
- **Gemini 2.0 Flash** för AI-svar
- **ChromaDB** för vektorsökning  
- **RAG** (Retrieval Augmented Generation) för noggranna svar
- **Streaming** för snabbare svar""",
        "location_btn": "📍 Dela min plats",
        "location_status": "Plats: Inte delad",
        "location_shared": "✓ Plats delad: {lat:.4f}, {lng:.4f}",
        "location_error": "⚠️ Kunde inte hämta plats",
    },
    "en": {
        "title": "🏠 Uppsala Emergency Shelter Chatbot",
        "description": """Welcome to the Uppsala Emergency Shelter Assistant! 
        I can help you find information about emergency shelters in Uppsala. 
        Ask me about locations, capacity, accessibility, and more.""",
        "chat_placeholder": "Type your question here...",
        "submit": "Send",
        "clear": "Clear",
        "examples_title": "Example questions:",
        "map_title": "🗺️ Shelter Map",
        "map_description": "View all shelters on an interactive map",
        "settings_title": "⚙️ Settings",
        "language_label": "Language / Språk",
        "max_docs_label": "Max sources",
        "filter_district": "Filter by district",
        "update_map": "Update map",
        "all_districts": "All",
        "error_message": "⚠️ Could not connect to LLM Engine. Please check that the service is running.",
        "sources_title": "📚 Sources:",
        "sources_placeholder": "📚 Sources will appear here after each question",
        "no_sources": "No sources found.",
        "capacity": "Capacity",
        "district": "District",
        "people": "people",
        "about_title": "About",
        "about_text": """This chatbot uses:
- **Gemini 2.0 Flash** for AI responses
- **ChromaDB** for vector search
- **RAG** (Retrieval Augmented Generation) for accurate answers
- **Streaming** for faster responses""",
        "location_btn": "📍 Share my location",
        "location_status": "Location: Not shared",
        "location_shared": "✓ Location shared: {lat:.4f}, {lng:.4f}",
        "location_error": "⚠️ Could not get location",
    }
}

# Example questions
EXAMPLES_SV = [
    "Hitta skyddsrum nära Centralstationen",
    "Vilket är det största skyddsrummet i Uppsala?",
    "Finns det tillgängliga skyddsrum för rullstolsanvändare?",
    "Visa skyddsrum i Gottsunda",
    "Hur många personer ryms i skyddsrummen?",
]

EXAMPLES_EN = [
    "Find shelters near Central Station",
    "What is the largest shelter in Uppsala?",
    "Are there accessible shelters for wheelchair users?",
    "Show shelters in Gottsunda",
    "How many people can the shelters accommodate?",
]


async def extract_location_from_query(query: str) -> Optional[str]:
    """
    Extract location names from user queries using pattern matching.
    
    Supports patterns like:
    - "från [location]" (Swedish: "from [location]")
    - "near [location]" (English)
    - "vid [location]" (Swedish: "at [location]")
    - "i [location]" (Swedish: "in [location]")
    - "nära [location]" (Swedish: "near [location]")
    
    Returns the first matched location or None.
    """
    import re
    
    # Pattern to match location references
    # Matches capitalized words, stops at punctuation, spaces followed by lowercase, or conjunctions
    patterns = [
        r"från\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
        r"from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"vid\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
        r"nära\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)",
        r"near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"i\s+([A-ZÅÄÖ][a-zåäö]+(?:\s+[A-ZÅÄÖ][a-zåäö]+)*)\??",  # Allow optional ?
        r"in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            location = match.group(1).strip()
            # Stop at conjunctions manually
            for conjunction in [" eller", " or", ","]:
                if conjunction in location:
                    location = location.split(conjunction)[0].strip()
            # Filter out common non-location words
            exclude_words = ["Vilka", "Visa", "Find", "Show", "Which", "What"]
            if location and location not in exclude_words:
                return location
    
    return None


async def chat_with_llm_stream(
    message: str, 
    history: List[Dict], 
    language: str, 
    max_docs: int,
    user_location: Optional[Dict] = None
):
    """
    Stream responses from LLM engine and update UI progressively.
    """
    if not message.strip():
        return
    
    # Add user message to history
    history.append({"role": "user", "content": message})
    
    # Add empty assistant message that we'll update
    history.append({"role": "assistant", "content": ""})
    
    try:
        # Extract location from message if mentioned
        extracted_location = await extract_location_from_query(message)
        
        # If location extracted and we don't already have user location, geocode it
        if extracted_location and not (user_location and user_location.get("lat")):
            logger.info(f"Extracted location from query: {extracted_location}")
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    geocode_response = await client.post(
                        f"{config.LLM_ENGINE_URL}/geocode",
                        json={"location": extracted_location}
                    )
                    geocode_response.raise_for_status()
                    geocode_data = geocode_response.json()
                    
                    if geocode_data.get("success"):
                        # Update user_location with geocoded coordinates
                        user_location = {
                            "lat": geocode_data["lat"],
                            "lng": geocode_data["lng"],
                            "name": extracted_location,
                            "max_radius_km": 5.0  # Default 5km radius
                        }
                        logger.info(f"Geocoded '{extracted_location}' to ({geocode_data['lat']}, {geocode_data['lng']})")
            except Exception as e:
                logger.warning(f"Failed to geocode extracted location '{extracted_location}': {e}")
        
        # Prepare request payload
        payload = {
            "message": message,
            "conversation_history": [msg for msg in history[:-1]],
            "language": language,
            "max_context_docs": max_docs
        }
        
        # Add location context if available
        if user_location and user_location.get("lat") and user_location.get("lng"):
            payload["user_location"] = {
                "latitude": user_location["lat"],
                "longitude": user_location["lng"]
            }
            # Add radius if specified
            if user_location.get("max_radius_km"):
                payload["user_location"]["max_radius_km"] = user_location["max_radius_km"]
        
        # Call streaming endpoint
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{config.LLM_ENGINE_URL}/chat/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                assistant_text = ""
                sources = []
                current_map = create_initial_map()
                
                # Read SSE stream
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            chunk_data = json.loads(data_str)
                            chunk_type = chunk_data.get("type")
                            
                            if chunk_type == "context":
                                # Context info received
                                logger.info(f"Found {chunk_data.get('count', 0)} relevant documents")
                            
                            elif chunk_type == "chunk":
                                # Text chunk received - append to response
                                assistant_text += chunk_data.get("text", "")
                                # Update the last message (assistant) in history
                                history[-1]["content"] = assistant_text
                                # Yield with current state
                                yield history, format_sources(sources, language), current_map, user_location
                            
                            elif chunk_type == "sources":
                                # Sources received - update both sources and map
                                sources = chunk_data.get("sources", [])
                                logger.info(f"Received {len(sources)} sources for map")
                                # Create map with user location if available
                                user_loc = None
                                if user_location and user_location.get("lat") and user_location.get("lng"):
                                    user_loc = (user_location["lat"], user_location["lng"])
                                    # Add location name to popup if available
                                    location_name = user_location.get("name", "Selected Location")
                                current_map = create_dynamic_map(sources, user_loc)
                                yield history, format_sources(sources, language), current_map, user_location
                            
                            elif chunk_type == "error":
                                # Error received
                                error_msg = chunk_data.get("message", "Unknown error")
                                history[-1]["content"] = error_msg
                                yield history, "", create_initial_map(), user_location
                                return
                            
                            elif chunk_type == "done":
                                # Streaming complete
                                logger.info("Streaming complete")
                        
                        except json.JSONDecodeError:
                            logger.warning(f"Could not parse SSE data: {data_str}")
                            continue
    
    except httpx.HTTPError as e:
        logger.error(f"HTTP error during streaming: {e}")
        error_msg = TRANSLATIONS[language]["error_message"]
        history[-1]["content"] = error_msg
        yield history, "", create_initial_map(), user_location
    
    except Exception as e:
        logger.error(f"Unexpected error during streaming: {e}")
        error_msg = TRANSLATIONS[language]["error_message"]
        history[-1]["content"] = error_msg
        yield history, "", create_initial_map(), user_location


def format_sources(sources: List[Dict], language: str) -> str:
    """Format sources for display."""
    t = TRANSLATIONS[language]
    
    if not sources:
        return f"{t['sources_title']}\n\n{t['no_sources']}"
    
    sources_text = f"{t['sources_title']}\n\n"
    for i, source in enumerate(sources, 1):
        sources_text += f"**{i}. {source.get('name', 'Unknown')}**\n"
        if source.get('address'):
            sources_text += f"   📍 {source['address']}\n"
        if source.get('capacity'):
            sources_text += f"   👥 {t['capacity']}: {source['capacity']} {t['people']}\n"
        if source.get('district'):
            sources_text += f"   🏙️ {t['district']}: {source['district']}\n"
        
        # Add distance if available (from geo-location filtering)
        if source.get('geo_distance'):
            distance = source['geo_distance']
            if distance < 1:
                sources_text += f"   📏 Avstånd: {int(distance * 1000)}m\n" if language == "sv" else f"   📏 Distance: {int(distance * 1000)}m\n"
            else:
                sources_text += f"   📏 Avstånd: {distance:.2f}km\n" if language == "sv" else f"   📏 Distance: {distance:.2f}km\n"
        
        sources_text += "\n"
    
    return sources_text


def create_initial_map() -> str:
    """Create an initial interactive map centered on Uppsala."""
    try:
        map_html = create_initial_interactive_map()
        logger.info(f"Initial map created, HTML length: {len(map_html)} characters")
        return map_html
    except Exception as e:
        logger.error(f"Error creating initial map: {e}", exc_info=True)
        return """
        <div style="height: 100%; display: flex; align-items: center; justify-content: center; background: #f0f0f0;">
            <div style="text-align: center; padding: 20px;">
                <h3>⚠️ Map Initialization Error</h3>
                <p>Could not load the interactive map. Check logs for details.</p>
            </div>
        </div>
        """


def create_dynamic_map(sources: List[Dict], user_location: Optional[Tuple[float, float]] = None) -> str:
    """Create an interactive Folium map with shelter markers.
    
    Shows up to 5 shelters with clickable markers.
    """
    if not sources:
        logger.info("No sources provided, creating initial map")
        return create_initial_interactive_map()
    
    logger.info(f"Creating map with {len(sources)} shelters and user_location={user_location}")
    
    # Log first shelter to check data structure
    if sources:
        logger.info(f"First shelter data: {sources[0]}")
    
    # Pass sources and user location to the interactive map generator
    map_html = create_interactive_map(shelters=sources, user_location=user_location, show_all_shelters=False)
    logger.info(f"Map HTML length: {len(map_html)} characters")
    return map_html


def create_ui():
    """Create Gradio interface."""
    
    with gr.Blocks(
        title="Uppsala Shelter Chatbot",
        theme=gr.themes.Soft(),
        css="""
        .source-box {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        .map-container {
            height: 600px !important;
            min-height: 600px !important;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: visible !important;
        }
        .map-container > div {
            height: 600px !important;
            min-height: 600px !important;
        }
        .map-container iframe {
            width: 100% !important;
            height: 600px !important;
            min-height: 600px !important;
            border: none !important;
        }
        /* Ensure Gradio HTML component has height */
        div[data-testid="HTML"] {
            height: 600px !important;
            min-height: 600px !important;
        }
        """
    ) as demo:
        
        # State for language
        language_state = gr.State("sv")
        
        # Dynamic title and description that we can update
        title_md = gr.Markdown("# 🏠 Uppsala Skyddsrum Chatbot")
        desc_md = gr.Markdown(TRANSLATIONS["sv"]["description"])
        
        with gr.Tab("💬 Chat"):
            with gr.Row(equal_height=True):
                # Left column: Chat interface
                with gr.Column(scale=1):
                    chatbot = gr.Chatbot(
                        height=400,
                        label="Conversation",
                        type="messages",
                        bubble_full_width=False,
                        avatar_images=(None, "🤖")
                    )
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            placeholder=TRANSLATIONS["sv"]["chat_placeholder"],
                            show_label=False,
                            scale=4
                        )
                        submit_btn = gr.Button(
                            TRANSLATIONS["sv"]["submit"],
                            variant="primary",
                            scale=1
                        )
                    
                    clear_btn = gr.Button(TRANSLATIONS["sv"]["clear"])
                    
                    # Sources display - REMOVED for cleaner UI
                    sources_display = gr.Markdown(
                        value="",
                        visible=False,  # Hidden for cleaner UI
                        elem_classes=["source-box"]
                    )
                    
                    # Example questions
                    examples_title = gr.Markdown(f"### {TRANSLATIONS['sv']['examples_title']}")
                    examples = gr.Examples(
                        examples=EXAMPLES_SV,
                        inputs=msg,
                        label=None
                    )
                
                # Right column: Interactive map
                with gr.Column(scale=1):
                    map_title = gr.Markdown("### 🗺️ Shelter Map")
                    
                    # Location search with radius/count control
                    with gr.Row():
                        location_search = gr.Textbox(
                            label="🔍 Search Location",
                            placeholder="Enter location (e.g., 'Centralstationen', 'Kungsgatan')...",
                            scale=4
                        )
                        shelter_count = gr.Dropdown(
                            choices=[3, 5, 7, 10],
                            value=5,
                            label="# Shelters",
                            scale=1
                        )
                    
                    with gr.Row():
                        max_radius = gr.Slider(
                            minimum=0.5,
                            maximum=10,
                            value=5,
                            step=0.5,
                            label="Max Distance (km)",
                            scale=2
                        )
                        find_btn = gr.Button("Find Shelters", variant="primary", scale=1)
                    
                    # Coordinate input for map clicks - HIDDEN for cleaner UI
                    coordinates_input = gr.Textbox(
                        label="",
                        placeholder="",
                        elem_id="selected_coordinates",
                        interactive=False,
                        visible=False  # Hidden - still works in background
                    )
                    
                    # Create map with explicit sizing
                    map_display = gr.HTML(
                        value=create_initial_interactive_map(),
                        elem_classes=["map-container"]
                    )
        
        with gr.Tab("⚙️ Inställningar"):
            settings_title_md = gr.Markdown(f"## {TRANSLATIONS['sv']['settings_title']}")
            
            with gr.Group():
                language = gr.Radio(
                    choices=[("Svenska", "sv"), ("English", "en")],
                    value="sv",
                    label=TRANSLATIONS["sv"]["language_label"]
                )
                
                max_docs = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=5,
                    step=1,
                    label=TRANSLATIONS["sv"]["max_docs_label"]
                )
                
                about_md = gr.Markdown(f"""
### {TRANSLATIONS['sv']['about_title']}

{TRANSLATIONS['sv']['about_text']}
                """)
        
        # Listen for postMessage from iframe
        demo.load(None, None, None, js="""
        () => {
            window.addEventListener('message', function(event) {
                if (event.data && event.data.type === 'map_click') {
                    var coordInput = document.querySelector('#selected_coordinates input, #selected_coordinates textarea');
                    if (coordInput) {
                        coordInput.value = event.data.coordinates;
                        coordInput.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            });
        }
        """)
        
        # State for user location (shared across handlers)
        user_location_state = gr.State(None)
        
        # Event handlers
        async def respond(message, history, lang, max_d, user_loc):
            """Handle chat submission with streaming."""
            if not message.strip():
                yield history, "", create_initial_map(), user_loc
                return
            
            # Stream updates (now includes user_location in yields)
            async for history_update, sources_update, map_update, updated_location in chat_with_llm_stream(
                message, history, lang, max_d, user_loc
            ):
                # Use updated_location if location was extracted from query
                yield history_update, sources_update, map_update, updated_location
        
        msg.submit(
            respond,
            inputs=[msg, chatbot, language, max_docs, user_location_state],
            outputs=[chatbot, sources_display, map_display, user_location_state]
        ).then(
            lambda: "",
            outputs=[msg]
        )
        
        submit_btn.click(
            respond,
            inputs=[msg, chatbot, language, max_docs, user_location_state],
            outputs=[chatbot, sources_display, map_display, user_location_state]
        ).then(
            lambda: "",
            outputs=[msg]
        )
        
        clear_btn.click(
            lambda: ([], TRANSLATIONS["sv"]["sources_placeholder"], create_initial_interactive_map(), None),
            outputs=[chatbot, sources_display, map_display, user_location_state]
        )
        
        # Handle location search with geocoding
        async def handle_location_search(location_name, count, radius, history, lang, max_d):
            """Handle location search by name - geocode then find shelters with radius limit."""
            if not location_name or not location_name.strip():
                yield history, "", create_initial_map(), None
                return
            
            try:
                # Call LLM engine geocoding endpoint
                async with httpx.AsyncClient(timeout=30.0) as client:
                    geocode_response = await client.post(
                        f"{config.LLM_ENGINE_URL}/geocode",
                        json={"location": location_name, "bias_to_uppsala": True}
                    )
                    geocode_data = geocode_response.json()
                
                if not geocode_data.get("success"):
                    # Add error message to chat
                    error_msg = f"⚠️ Could not find location: '{location_name}'. Please try a different search."
                    if lang == "sv":
                        error_msg = f"⚠️ Kunde inte hitta platsen: '{location_name}'. Prova en annan sökning."
                    
                    history.append((location_name, error_msg))
                    yield history, "", create_initial_map(), None
                    return
                
                lat = geocode_data["lat"]
                lng = geocode_data["lng"]
                place_name = geocode_data.get("place_name", location_name)
                formatted_address = geocode_data.get("formatted_address", "")
                
                # Store location with radius for future queries
                location = {"lat": lat, "lng": lng, "max_radius_km": radius}
                
                # Create automatic query with radius constraint
                query = f"Vilka är de {count} närmaste skyddsrummen inom {radius}km från {place_name} ({lat:.4f}, {lng:.4f})?"
                if lang == "en":
                    query = f"What are the {count} nearest shelters within {radius}km of {place_name} ({lat:.4f}, {lng:.4f})?"
                
                logger.info(f"Geocoded '{location_name}' to ({lat:.4f}, {lng:.4f}) - Searching {count} shelters within {radius}km")
                
                # Stream response with location and radius
                async for history_update, sources_update, map_update, updated_location in chat_with_llm_stream(
                    query, history, lang, count, location  # Use count instead of max_d
                ):
                    yield history_update, sources_update, map_update, updated_location
                    
            except Exception as e:
                logger.error(f"Error during location search: {e}", exc_info=True)
                error_msg = f"⚠️ Error searching location. Please try again."
                if lang == "sv":
                    error_msg = f"⚠️ Fel vid sökning av plats. Försök igen."
                history.append((location_name, error_msg))
                yield history, "", create_initial_map(), None
        
        # Handle coordinate selection from map
        async def handle_location_selection(coords_str, history, lang, max_d):
            """Handle when user clicks on map to select location."""
            if not coords_str:
                yield history, "", create_initial_map(), None
                return
            
            # Parse coordinates
            coords = parse_coordinates(coords_str)
            if not coords:
                yield history, "", create_initial_map(), None
                return
            
            lat, lng = coords
            
            # Store location for future queries (default 5km radius)
            location = {"lat": lat, "lng": lng, "max_radius_km": 5.0}
            
            # Create automatic query for nearest shelters
            query = f"Vilka är de 5 närmaste skyddsrummen inom 5km från plats ({lat:.4f}, {lng:.4f})?"
            if lang == "en":
                query = f"What are the 5 nearest shelters within 5km of location ({lat:.4f}, {lng:.4f})?"
            
            # Stream response with location
            async for history_update, sources_update, map_update, updated_location in chat_with_llm_stream(
                query, history, lang, max_d, location
            ):
                yield history_update, sources_update, map_update, updated_location
        
        # Wire up location search button
        # Wire up location search button with radius and count
        find_btn.click(
            handle_location_search,
            inputs=[location_search, shelter_count, max_radius, chatbot, language, max_docs],
            outputs=[chatbot, sources_display, map_display, user_location_state]
        ).then(
            lambda: "",  # Clear search box after search
            outputs=[location_search]
        )
        
        coordinates_input.change(
            handle_location_selection,
            inputs=[coordinates_input, chatbot, language, max_docs],
            outputs=[chatbot, sources_display, map_display, user_location_state]
        )
        
        # Update UI language
        def update_language(lang):
            """Update all UI elements to selected language."""
            t = TRANSLATIONS[lang]
            examples_list = EXAMPLES_SV if lang == "sv" else EXAMPLES_EN
            
            return {
                title_md: gr.update(value=f"# {t['title']}"),
                desc_md: gr.update(value=t['description']),
                msg: gr.update(placeholder=t["chat_placeholder"]),
                submit_btn: gr.update(value=t["submit"]),
                clear_btn: gr.update(value=t["clear"]),
                examples_title: gr.update(value=f"### {t['examples_title']}"),
                map_title: gr.update(value=f"### 🗺️ {t['map_title']}"),
                settings_title_md: gr.update(value=f"## {t['settings_title']}"),
                language: gr.update(label=t["language_label"]),
                max_docs: gr.update(label=t["max_docs_label"]),
                about_md: gr.update(value=f"### {t['about_title']}\n\n{t['about_text']}"),
                sources_display: gr.update(value=t["sources_placeholder"]),
                language_state: lang,
            }
        
        language.change(
            update_language,
            inputs=[language],
            outputs=[
                title_md,
                desc_md,
                msg,
                submit_btn,
                clear_btn,
                examples_title,
                map_title,
                settings_title_md,
                language,
                max_docs,
                about_md,
                sources_display,
                language_state,
            ]
        )
    
    return demo


if __name__ == "__main__":
    logger.info(f"Starting UI service...")
    logger.info(f"LLM Engine URL: {config.LLM_ENGINE_URL}")
    logger.info(f"Vector DB URL: {config.VECTORDB_URL}")
    
    demo = create_ui()
    demo.launch(
        server_name=config.GRADIO_SERVER_NAME,
        server_port=config.GRADIO_SERVER_PORT,
        share=False
    )