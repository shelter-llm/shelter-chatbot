"""RAG (Retrieval Augmented Generation) Engine using LangChain and Gemini."""
import logging
from typing import List, Dict, Any, Optional, Tuple, AsyncIterator
import httpx
import google.generativeai as genai
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG Engine for shelter chatbot using Gemini and Vector DB."""
    
    def __init__(
        self,
        api_key: str,
        vectordb_url: str,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """
        Initialize RAG Engine.
        
        Args:
            api_key: Google API key
            vectordb_url: URL of the vector database service
            model_name: Gemini model name
            temperature: Model temperature
            max_tokens: Maximum tokens for response
        """
        self.vectordb_url = vectordb_url
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        
        # System prompts for different languages
        self.system_prompts = {
            "sv": """Du är en hjälpsam assistent som svarar på frågor om skyddsrum i Uppsala.

VIKTIG INFORMATION: Vår databas innehåller totalt {total_shelters} skyddsrum i Uppsala.

UPPSALA GEOGRAFI OCH VIKTIGA PLATSER:

**Centrala Uppsala:**
- Uppsala Centralstation: Bangårdsgatan/Kungsgatan i centrala Uppsala (59.8586°N, 17.6389°E)
- Stora Torget: Centrala torget i Uppsala
- Uppsala Domkyrka: St Eriks torg
- Uppsala Slott: På Kasåsen ovanför centrum

**Uppsala Universitet och Campus:**
- Ångströmlaboratoriet: Lägerhyddsvägen, norra delen av Uppsala (59.8395°N, 17.6470°E)
- Ekonomikum: Kyrkogårdsgatan vid centrum
- BMC (Biomedicinskt centrum): Husargatan
- Polacksbacken: Campus öster om centrum

**Stadsdelar och områden:**
- Centrum: Området kring Stora torget, Fyristorg, St Eriks torg
- Flogsta: Väster om centrum, studentområde
- Studentstaden/Kantorsgatan: Väster om centrum
- Luthagen: Öster om centrum
- Gottsunda: Söder om centrum
- Valsätra: Söder om centrum
- Sävja: Öster om centrum
- Boländerna: Norr om centrum
- Librobäck: Nordväst om centrum

**Sjukhus och viktiga institutioner:**
- Akademiska sjukhuset: Södra delen av Uppsala

När användaren frågar om närhet till en specifik plats:
1. Identifiera platsen från listan ovan
2. Titta på adresserna och stadsdelarna i de relevanta skyddsrummen från kontexten
3. Rekommendera de skyddsrum som ligger i samma område eller närliggande områden
4. Förklara varför dessa är närmast baserat på geografisk kunskap
5. Nämn att användaren kan klicka på Google Maps-länken för exakta vägbeskrivningar

Din uppgift är att:
1. Ge tydlig och korrekt information baserat på den kontext som ges
2. Svara alltid på svenska om inte användaren specifikt ber om ett annat språk
3. När användaren frågar om närhet till en plats (t.ex. centralstationen):
   - Titta på adresserna och stadsdelarna i de relevanta skyddsrummen
   - Förklara vilka som ligger närmast baserat på adresser och områden
   - Ange att användaren kan klicka på Google Maps-länken för exakta vägbeskrivningar
4. Inkludera specifika detaljer som adress, kapacitet och tillgänglighet när det är relevant
5. Var koncis men informativ
6. Om du inte hittar relevant information i kontexten, säg det ärligt
7. När användaren frågar om antalet skyddsrum, referera till det totala antalet ({total_shelters})

Kontext från vår databas (visar de {context_count} mest relevanta skyddsrummen för denna fråga):
{context}

Tidigare konversation:
{history}

Användarens fråga: {question}

Ge ett hjälpsamt och informativt svar. Om frågan gäller närhet till en plats, analysera adresserna i kontexten och ge rekommendationer:""",
            
            "en": """You are a helpful assistant that answers questions about emergency shelters in Uppsala.

IMPORTANT INFORMATION: Our database contains a total of {total_shelters} shelters in Uppsala.

UPPSALA GEOGRAPHY AND KEY LOCATIONS:

**Central Uppsala:**
- Uppsala Central Station: Bangårdsgatan/Kungsgatan in central Uppsala (59.8586°N, 17.6389°E)
- Stora Torget: Central square in Uppsala
- Uppsala Cathedral: St Eriks torg
- Uppsala Castle: On Kasåsen above the center

**Uppsala University and Campus:**
- Ångström Laboratory: Lägerhyddsvägen, northern Uppsala (59.8395°N, 17.6470°E)
- Ekonomikum: Kyrkogårdsgatan near center
- BMC (Biomedical Center): Husargatan
- Polacksbacken: Campus east of center

**Districts and Areas:**
- Centrum: Area around Stora torget, Fyristorg, St Eriks torg
- Flogsta: West of center, student area
- Studentstaden/Kantorsgatan: West of center
- Luthagen: East of center
- Gottsunda: South of center
- Valsätra: South of center
- Sävja: East of center
- Boländerna: North of center
- Librobäck: Northwest of center

**Hospitals and Important Institutions:**
- Akademiska Hospital: Southern Uppsala

When users ask about proximity to a specific location:
1. Identify the location from the list above
2. Examine the addresses and districts of relevant shelters from the context
3. Recommend shelters in the same area or nearby areas
4. Explain why these are closest based on geographic knowledge
5. Mention that users can click the Google Maps link for exact directions

Your task is to:
1. Provide clear and accurate information based on the given context
2. Always respond in English unless specifically asked for another language
3. When users ask about proximity to a location (e.g., central station):
   - Examine the addresses and districts of relevant shelters
   - Explain which ones are closest based on addresses and areas
   - Mention that users can click the Google Maps link for exact directions
4. Include specific details like address, capacity, and accessibility when relevant
5. Be concise but informative
6. If you don't find relevant information in the context, say so honestly
7. When the user asks about the number of shelters, refer to the total count ({total_shelters})

Context from our database (showing the {context_count} most relevant shelters for this query):
{context}

Previous conversation:
{history}

User's question: {question}

Provide a helpful and informative answer. If the question is about proximity to a location, analyze the addresses in the context and provide recommendations:"""
        }
        
        # Cache for total shelter count
        self._total_shelters = None
        
        logger.info(f"RAG Engine initialized with model: {model_name}")
    
    async def get_total_shelters(self, collection_name: str = "uppsala_shelters") -> int:
        """
        Get the total number of shelters in the database.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Total number of shelters
        """
        if self._total_shelters is not None:
            return self._total_shelters
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.vectordb_url}/collections/{collection_name}/stats"
                )
                response.raise_for_status()
                data = response.json()
                self._total_shelters = data.get("stats", {}).get("count", 0)
                logger.info(f"Total shelters in database: {self._total_shelters}")
                return self._total_shelters
        except Exception as e:
            logger.error(f"Error getting total shelter count: {e}")
            return 0
    
    def enhance_location_query(self, query: str) -> str:
        """
        Enhance location-based queries with geographic context.
        
        Args:
            query: Original user query
            
        Returns:
            Enhanced query with location context
        """
        # Define location mappings with their districts/areas
        location_mappings = {
            # University and Campus
            'ångström': 'Ångström Lägerhyddsvägen Boländerna norra Uppsala',
            'ångströmlaboratoriet': 'Ångström Lägerhyddsvägen Boländerna norra Uppsala',
            'angstrom': 'Ångström Lägerhyddsvägen Boländerna norra Uppsala',
            'ekonomikum': 'Ekonomikum Kyrkogårdsgatan centrum Uppsala',
            'bmc': 'BMC Biomedicinskt centrum Husargatan Uppsala',
            'polacksbacken': 'Polacksbacken östra Uppsala Luthagen',
            
            # Central locations
            'centralstation': 'Centralstation Bangårdsgatan Kungsgatan centrum Uppsala',
            'central station': 'Centralstation Bangårdsgatan Kungsgatan centrum Uppsala',
            'centralstationen': 'Centralstation Bangårdsgatan Kungsgatan centrum Uppsala',
            'stora torget': 'Stora torget centrum Uppsala',
            'domkyrka': 'Domkyrka St Eriks torg centrum Uppsala',
            'slott': 'Uppsala slott Kasåsen centrum',
            
            # Districts
            'flogsta': 'Flogsta västra Uppsala Librobäck',
            'studentstaden': 'Studentstaden Kantorsgatan västra Uppsala',
            'kantorsgatan': 'Kantorsgatan Studentstaden västra Uppsala',
            'luthagen': 'Luthagen östra Uppsala',
            'gottsunda': 'Gottsunda södra Uppsala Valsätra',
            'valsätra': 'Valsätra södra Uppsala Gottsunda',
            'sävja': 'Sävja östra Uppsala',
            'boländerna': 'Boländerna norra Uppsala',
            'librobäck': 'Librobäck västra Uppsala Flogsta',
            
            # Institutions
            'akademiska': 'Akademiska sjukhuset södra Uppsala',
            'sjukhus': 'Akademiska sjukhuset södra Uppsala',
        }
        
        query_lower = query.lower()
        enhanced_query = query
        
        # Check if query contains any known locations
        for location, context in location_mappings.items():
            if location in query_lower:
                enhanced_query = f"{query} {context}"
                logger.info(f"Enhanced location query: '{query}' -> '{enhanced_query}'")
                break
        
        return enhanced_query
    
    
    async def retrieve_context(
        self,
        query: str,
        max_docs: int = 5,
        collection_name: str = "uppsala_shelters"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from vector database.
        
        Args:
            query: User's query
            max_docs: Maximum number of documents to retrieve
            collection_name: Name of the collection to query
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            # Generate embedding for the query using Gemini
            logger.info(f"Generating embedding for query: {query}")
            embedding_result = genai.embed_content(
                model="models/text-embedding-004",
                content=query,
                task_type="retrieval_query"
            )
            query_embedding = embedding_result['embedding']
            logger.info(f"Generated embedding with {len(query_embedding)} dimensions")
            
            # Query vector database with embeddings
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Query to get relevant document IDs
                response = await client.post(
                    f"{self.vectordb_url}/query",
                    json={
                        "collection_name": collection_name,
                        "query_embeddings": [query_embedding],  # Use embeddings instead of texts
                        "n_results": max_docs,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract IDs and distances from query results
                results = data.get("results", {})
                ids = results.get("ids", [[]])[0] if results.get("ids") else []
                distances = results.get("distances", [[]])[0] if results.get("distances") else []
                
                if not ids:
                    logger.warning("No documents found in query results")
                    return []
                
                logger.info(f"Query returned {len(ids)} document IDs")
                
                # Step 2: Get complete documents with full metadata using IDs
                # Use the new endpoint that fetches documents by specific IDs
                get_response = await client.post(
                    f"{self.vectordb_url}/collections/{collection_name}/documents/by_ids",
                    json=ids
                )
                get_response.raise_for_status()
                get_data = get_response.json()
                
                fetched_docs = get_data.get("documents", [])
                
                # Create a dict for quick lookup by ID
                docs_by_id = {doc["id"]: doc for doc in fetched_docs}
                
                # Combine into list of dicts, maintaining query order
                context_docs = []
                for i, doc_id in enumerate(ids):
                    if doc_id in docs_by_id:
                        doc_data = docs_by_id[doc_id]
                        context_docs.append({
                            "document": doc_data["document"],
                            "metadata": doc_data["metadata"],
                            "distance": distances[i] if i < len(distances) else 0.0
                        })
                
                logger.info(f"Retrieved {len(context_docs)} context documents")
                return context_docs
                
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return []
    
    def format_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Format context documents for the prompt.
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            Formatted context string
        """
        if not documents:
            return "Ingen relevant information hittades i databasen."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            metadata = doc.get("metadata", {})
            content = doc.get("document", "")
            
            context_parts.append(f"[Källa {i}]")
            context_parts.append(content)
            
            # Add key metadata
            if metadata.get("name"):
                context_parts.append(f"Namn: {metadata['name']}")
            if metadata.get("address"):
                context_parts.append(f"Adress: {metadata['address']}")
            if metadata.get("capacity"):
                context_parts.append(f"Kapacitet: {metadata['capacity']} personer")
            if metadata.get("district"):
                context_parts.append(f"Stadsdel: {metadata['district']}")
            
            context_parts.append("")  # Empty line between sources
        
        return "\n".join(context_parts)
    
    def format_history(self, messages: List[Any]) -> str:
        """
        Format conversation history for the prompt.
        
        Args:
            messages: List of chat messages
            
        Returns:
            Formatted history string
        """
        if not messages:
            return "Ingen tidigare konversation."
        
        history_parts = []
        for msg in messages[-6:]:  # Last 6 messages (3 turns)
            role = msg.role if hasattr(msg, 'role') else msg.get('role', 'unknown')
            content = msg.content if hasattr(msg, 'content') else msg.get('content', '')
            
            if role == "user":
                history_parts.append(f"Användare: {content}")
            elif role == "assistant":
                history_parts.append(f"Assistent: {content}")
        
        return "\n".join(history_parts)
    
    async def generate_response_stream(
        self,
        query: str,
        conversation_history: Optional[List[Any]] = None,
        language: str = "sv",
        max_context_docs: int = 5,
        user_location: Optional[Dict[str, float]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate streaming response using RAG.
        
        Args:
            query: User's query
            conversation_history: Previous conversation messages
            language: Response language (sv/en)
            max_context_docs: Maximum context documents to retrieve
            user_location: Optional dict with latitude and longitude
            
        Yields:
            Dict with 'type' ('context', 'chunk', 'sources', 'error') and relevant data
        """
        try:
            # Get total shelter count
            total_shelters = await self.get_total_shelters()
            
            # Enhance query with location context if it's a location-based query
            enhanced_query = self.enhance_location_query(query)
            
            # Retrieve relevant context using enhanced query
            context_docs = await self.retrieve_context(enhanced_query, max_context_docs)
            
            # Yield context info first
            yield {
                "type": "context",
                "count": len(context_docs),
                "message": f"Found {len(context_docs)} relevant shelters"
            }
            
            # Format context and history
            context = self.format_context(context_docs)
            history = self.format_history(conversation_history or [])
            
            # Get system prompt for language
            system_prompt = self.system_prompts.get(language, self.system_prompts["sv"])
            
            # Add location context to the prompt if available
            location_context = ""
            if user_location and user_location.get("latitude") and user_location.get("longitude"):
                lat = user_location["latitude"]
                lng = user_location["longitude"]
                location_context = f"\n\nAnvändarens nuvarande plats: {lat:.4f}° N, {lng:.4f}° E (latitud, longitud)" if language == "sv" else f"\n\nUser's current location: {lat:.4f}° N, {lng:.4f}° E (latitude, longitude)"
            
            # Create full prompt with total count and context count
            prompt = system_prompt.format(
                total_shelters=total_shelters,
                context_count=len(context_docs),
                context=context,
                history=history,
                question=query
            ) + location_context
            
            logger.info(f"Generating streaming response with {len(context_docs)} context documents out of {total_shelters} total shelters")
            
            # Generate streaming response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                ),
                stream=True  # Enable streaming
            )
            
            # Stream chunks
            for chunk in response:
                if chunk.text:
                    yield {
                        "type": "chunk",
                        "text": chunk.text
                    }
            
            # Yield sources at the end
            sources = []
            for doc in context_docs:
                metadata = doc.get("metadata", {})
                sources.append({
                    "id": metadata.get("id", "unknown"),
                    "name": metadata.get("name", "Unknown"),
                    "address": metadata.get("address", ""),
                    "capacity": metadata.get("capacity"),
                    "district": metadata.get("district", ""),
                    "coordinates_lat": metadata.get("coordinates_lat"),
                    "coordinates_lng": metadata.get("coordinates_lng"),
                    "map_url": metadata.get("map_url", ""),  # Include map URL for dynamic map
                    "score": doc.get("distance", 0.0),
                    "snippet": doc.get("document", "")[:200]  # First 200 chars
                })
            
            yield {
                "type": "sources",
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error generating streaming response: {e}")
            error_message = {
                "sv": f"Ursäkta, jag kunde inte generera ett svar just nu. Fel: {str(e)}",
                "en": f"Sorry, I couldn't generate a response right now. Error: {str(e)}"
            }
            yield {
                "type": "error",
                "message": error_message.get(language, error_message["sv"])
            }
    
    async def generate_response(
        self,
        query: str,
        conversation_history: Optional[List[Any]] = None,
        language: str = "sv",
        max_context_docs: int = 5
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate response using RAG (non-streaming).
        
        Args:
            query: User's query
            conversation_history: Previous conversation messages
            language: Response language (sv/en)
            max_context_docs: Maximum context documents to retrieve
            
        Returns:
            Tuple of (response_text, source_documents)
        """
        try:
            # Retrieve relevant context
            context_docs = await self.retrieve_context(query, max_context_docs)
            
            # Format context and history
            context = self.format_context(context_docs)
            history = self.format_history(conversation_history or [])
            
            # Get system prompt for language
            system_prompt = self.system_prompts.get(language, self.system_prompts["sv"])
            
            # Create full prompt
            prompt = system_prompt.format(
                context=context,
                history=history,
                question=query
            )
            
            logger.info(f"Generating response with {len(context_docs)} context documents")
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                )
            )
            
            response_text = response.text
            
            # Prepare source information
            sources = []
            for doc in context_docs:
                metadata = doc.get("metadata", {})
                sources.append({
                    "id": metadata.get("id", "unknown"),
                    "name": metadata.get("name", "Unknown"),
                    "address": metadata.get("address", ""),
                    "capacity": metadata.get("capacity"),
                    "district": metadata.get("district", ""),
                    "coordinates_lat": metadata.get("coordinates_lat"),
                    "coordinates_lng": metadata.get("coordinates_lng"),
                    "map_url": metadata.get("map_url", ""),
                    "score": doc.get("distance", 0.0),
                    "snippet": doc.get("document", "")[:200]  # First 200 chars
                })
            
            return response_text, sources
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            error_message = {
                "sv": f"Ursäkta, jag kunde inte generera ett svar just nu. Fel: {str(e)}",
                "en": f"Sorry, I couldn't generate a response right now. Error: {str(e)}"
            }
            return error_message.get(language, error_message["sv"]), []
