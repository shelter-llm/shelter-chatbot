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

# Translations
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


async def chat_with_llm_stream(
    message: str, 
    history: List[Dict], 
    language: str, 
    max_docs: int = 5,
    user_location: Optional[Dict] = None
) -> tuple:
    """
    Stream responses from LLM Engine and update UI progressively.
    
    Args:
        message: User's message
        history: Chat history in messages format
        language: Selected language
        max_docs: Maximum context documents
        user_location: Optional dict with 'lat' and 'lng' keys
        
    Yields:
        Tuple of (updated history, formatted sources, map HTML)
    """
    if not message.strip():
        return
    
    # Add user message to history
    history.append({"role": "user", "content": message})
    
    # Add empty assistant message that we'll update
    history.append({"role": "assistant", "content": ""})
    
    try:
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
                                # Don't update map yet, wait for sources
                                yield history, format_sources([], language), create_initial_map()
                            
                            elif chunk_type == "sources":
                                # Sources received - update both sources and map
                                sources = chunk_data.get("sources", [])
                                yield history, format_sources(sources, language), create_dynamic_map(sources)
                            
                            elif chunk_type == "error":
                                # Error received
                                error_msg = chunk_data.get("message", "Unknown error")
                                history[-1]["content"] = error_msg
                                yield history, "", create_initial_map()
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
        yield history, "", create_initial_map()
    
    except Exception as e:
        logger.error(f"Unexpected error during streaming: {e}")
        error_msg = TRANSLATIONS[language]["error_message"]
        history[-1]["content"] = error_msg
        yield history, "", create_initial_map()


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
            sources_text += f"   🏘️ {t['district']}: {source['district']}\n"
        sources_text += "\n"
    
    return sources_text


def create_initial_map() -> str:
    """Create an initial interactive map centered on Uppsala."""
    return create_initial_interactive_map()


def create_dynamic_map(sources: List[Dict]) -> str:
    """Create an interactive Folium map with shelter markers.
    
    Shows up to 5 shelters with clickable markers.
    """
    if not sources:
        return create_initial_interactive_map()
    
    # Pass sources to the interactive map generator
    return create_interactive_map(shelters=sources, show_all_shelters=False)


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
            height: 600px;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
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
                        height=550,
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
                    
                    # Example questions
                    examples_title = gr.Markdown(f"### {TRANSLATIONS['sv']['examples_title']}")
                    examples = gr.Examples(
                        examples=EXAMPLES_SV,
                        inputs=msg,
                        label=None
                    )
                
                # Right column: Interactive map only
                with gr.Column(scale=1):
                    map_title = gr.Markdown("### 🗺️ Klicka på kartan för att välja plats / Click on map to select location")
                    
                    # Hidden input to store coordinates from map clicks
                    coordinates_input = gr.Textbox(
                        label="",
                        visible=False,
                        elem_id="selected_coordinates"
                    )
                    
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
        
        # Event handlers - streaming generator must be async
        async def respond(message, history, lang, max_d):
            """Handle chat submission with streaming."""
            if not message.strip():
                yield history, ""
                return
            
            # No location needed - Google Maps handles navigation
            location = None
            
            # Yield from the streaming generator (only history and map, no sources)
            async for update in chat_with_llm_stream(message, history, lang, max_d, location):
                # update is (history, sources_text, map_html)
                # We only need history and map_html
                history_update, _, map_update = update
                yield history_update, map_update
        
        msg.submit(
            respond,
            inputs=[msg, chatbot, language, max_docs],
            outputs=[chatbot, map_display]
        ).then(
            lambda: "",
            outputs=[msg]
        )
        
        submit_btn.click(
            respond,
            inputs=[msg, chatbot, language, max_docs],
            outputs=[chatbot, map_display]
        ).then(
            lambda: "",
            outputs=[msg]
        )
        
        clear_btn.click(
            lambda: ([], create_initial_interactive_map()),
            outputs=[chatbot, map_display]
        )
        
        # Handle coordinate selection from map
        async def handle_location_selection(coords_str, history, lang, max_d):
            """Handle when user clicks on map to select location."""
            if not coords_str:
                yield history, create_initial_interactive_map()
                return
            
            # Parse coordinates
            coords = parse_coordinates(coords_str)
            if not coords:
                yield history, create_initial_interactive_map()
                return
            
            lat, lng = coords
            
            # Create automatic query for nearest shelters
            query = f"Vilka är de närmaste skyddsrummen till koordinaterna {lat}, {lng}?"
            if lang == "en":
                query = f"What are the nearest shelters to coordinates {lat}, {lng}?"
            
            # Stream response (only history and map)
            async for update in chat_with_llm_stream(query, history, lang, max_d, None):
                history_update, _, map_update = update
                yield history_update, map_update
        
        coordinates_input.change(
            handle_location_selection,
            inputs=[coordinates_input, chatbot, language, max_docs],
            outputs=[chatbot, map_display]
        )
        
        # Update UI language - Complete language switching
        def update_language(lang):
            """Update all UI elements to selected language."""
            t = TRANSLATIONS[lang]
            examples_list = EXAMPLES_SV if lang == "sv" else EXAMPLES_EN
            
            return {
                # Update all text elements
                title_md: gr.update(value=f"# {t['title']}"),
                desc_md: gr.update(value=t['description']),
                msg: gr.update(placeholder=t["chat_placeholder"]),
                submit_btn: gr.update(value=t["submit"]),
                clear_btn: gr.update(value=t["clear"]),
                examples_title: gr.update(value=f"### {t['examples_title']}"),
                map_title: gr.update(value=f"### 🗺️ {t['map_title'] if 'map_title' in t else 'Skyddsrum på kartan'}"),
                settings_title_md: gr.update(value=f"## {t['settings_title']}"),
                language: gr.update(label=t["language_label"]),
                max_docs: gr.update(label=t["max_docs_label"]),
                about_md: gr.update(value=f"### {t['about_title']}\n\n{t['about_text']}"),
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
