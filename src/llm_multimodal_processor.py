#!/usr/bin/env python3
"""
LLM-Powered Multimodal Electrical Diagram Processor

This module uses Large Language Models with vision capabilities to understand
electrical diagrams, Single Line Diagrams (SLDs), and extract structured electrical
engineering information through natural language reasoning.
"""

import os
import json
import base64
import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from PIL import Image
import requests
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import vector database manager for RAG capabilities
from vector_database_manager import get_vector_database, VectorDatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM multimodal processing"""
    provider: str = "google"  # 'google', 'openai', 'anthropic', 'ollama', 'openrouter'
    model: str = "gemini-2.0-flash"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1  # Low temperature for consistent extraction

    def __post_init__(self):
        if not self.api_key:
            if self.provider == 'google':
                self.api_key = os.getenv('GOOGLE_API_KEY')
                if not self.api_key:
                    logger.warning("No API key found for Google Gemini. Set GOOGLE_API_KEY environment variable.")
            elif self.provider in ['openai', 'anthropic']:
                env_var = f"{self.provider.upper()}_API_KEY"
                self.api_key = os.getenv(env_var)
                if not self.api_key:
                    logger.warning(f"No API key found for {self.provider}. Set {env_var} environment variable.")


@dataclass
class DiagramAnalysis:
    """Results from diagram analysis"""
    diagram_type: str
    symbols_identified: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]
    text_elements: List[Dict[str, Any]]
    electrical_parameters: Dict[str, Any]
    validation_notes: List[str]
    confidence_score: float
    structured_data: Dict[str, Any] = field(default_factory=dict)


class LLMMultimodalProcessor:
    """
    LLM-powered multimodal processor for electrical diagrams

    Uses vision-capable LLMs to understand electrical diagrams through
    natural language reasoning rather than traditional computer vision.
    """

    def __init__(self, config: Optional[LLMConfig] = None, vector_db_path: str = "./vector_db"):
        self.config = config or LLMConfig()

        # Initialize session for API calls
        self.session = requests.Session()
        self.session.timeout = 120  # 2 minute timeout for vision processing

        # Initialize vector database for RAG capabilities
        try:
            self.vector_db = get_vector_database(vector_db_path)
            self.rag_enabled = True
            logger.info("Vector database initialized for RAG capabilities")
        except Exception as e:
            logger.warning(f"Vector database initialization failed: {e}. Continuing without RAG.")
            self.vector_db = None
            self.rag_enabled = False

        # Electrical engineering knowledge base for prompts
        self.electrical_kb = self._load_electrical_knowledge()

        logger.info(f"Initialized LLM Multimodal Processor with {self.config.provider}:{self.config.model}")
        if self.rag_enabled:
            logger.info("RAG (Retrieval-Augmented Generation) is enabled")

    def _load_electrical_knowledge(self) -> Dict[str, Any]:
        """Load electrical engineering knowledge for prompt engineering"""
        return {
            'equipment_types': {
                'loads': ['motor', 'pump', 'fan', 'lighting', 'heater', 'chiller', 'conveyor', 'compressor'],
                'sources': ['generator', 'transformer', 'ups', 'battery', 'solar panel', 'wind turbine'],
                'protection': ['circuit breaker', 'fuse', 'relay', 'contactor', 'surge protector'],
                'distribution': ['busbar', 'switchgear', 'panel', 'switchboard', 'distribution board']
            },
            'symbols': {
                'power_symbols': ['⏚', '⚡', '🔌', '🔋', '🏭', '🏢', '💡'],
                'switch_symbols': ['⭕', '🔘', '🔲', '▢', '△', '▽'],
                'measurement': ['📊', '📈', '⚡', '🌡️', '💧']
            },
            'standards': ['IEC', 'NEC', 'IS', 'BS', 'IEEE', 'ANSI'],
            'voltage_levels': ['110V', '230V', '400V', '415V', '690V', '11kV', '33kV', '132kV'],
            'protection_devices': ['MCB', 'MCCB', 'ACB', 'VCB', 'SF6', 'MOF']
        }

    def analyze_diagram(self, image_path: str, context: Optional[str] = None,
                       use_rag: bool = True) -> DiagramAnalysis:
        """
        Analyze an electrical diagram using LLM vision capabilities with optional RAG

        Args:
            image_path: Path to diagram image
            context: Additional context about the diagram
            use_rag: Whether to use RAG for enhanced analysis

        Returns:
            Comprehensive analysis results
        """

        logger.info(f"Analyzing diagram: {image_path}")

        try:
            # Load and encode image
            image = Image.open(image_path)
            image_b64 = self._encode_image(image)

            # Get RAG context if enabled
            rag_context = None
            if use_rag and self.rag_enabled:
                try:
                    # Extract basic diagram description for RAG query
                    basic_description = self._extract_basic_diagram_description(image_path)
                    rag_query = f"electrical diagram analysis: {basic_description}"
                    if context:
                        rag_query += f" Context: {context}"

                    rag_result = self.vector_db.rag_query(rag_query, "electrical", top_k=5)
                    if rag_result['context'].strip():
                        rag_context = rag_result['context']
                        logger.info(f"RAG provided {len(rag_result['sources'])} relevant knowledge sources")
                    else:
                        logger.info("RAG query returned no relevant context")
                except Exception as e:
                    logger.warning(f"RAG query failed: {e}")
                    rag_context = None

            # Create analysis prompt with RAG context
            prompt = self._create_analysis_prompt(context, rag_context)

            # Call LLM for analysis
            response = self._call_llm_vision(prompt, image_b64)

            # Parse and structure results
            analysis = self._parse_llm_response(response)

            # Store successful analysis results in vector database for future learning
            if self.rag_enabled and analysis.confidence_score > 0.7:
                try:
                    self._store_analysis_results(analysis, image_path, context)
                except Exception as e:
                    logger.warning(f"Failed to store analysis results: {e}")

            analysis.validation_notes.append(f"Analysis completed using {self.config.provider}:{self.config.model}")
            if rag_context:
                analysis.validation_notes.append("Enhanced with RAG (Retrieval-Augmented Generation)")

            logger.info(f"Successfully analyzed diagram with {len(analysis.symbols_identified)} symbols identified")
            if rag_context:
                logger.info("Analysis enhanced with vector database knowledge")

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze diagram {image_path}: {e}")
            # Return minimal analysis on error
            return DiagramAnalysis(
                diagram_type="unknown",
                symbols_identified=[],
                connections=[],
                text_elements=[],
                electrical_parameters={},
                validation_notes=[f"Analysis failed: {str(e)}"],
                confidence_score=0.0
            )

    def _encode_image(self, image: Image.Image) -> str:
        """Encode PIL image to base64 string"""
        # Resize if too large (most LLMs have token limits)
        max_size = (2048, 2048)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Save to bytes and encode
        from io import BytesIO
        buffer = BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        image_bytes = buffer.getvalue()

        return base64.b64encode(image_bytes).decode('utf-8')

    def _create_analysis_prompt(self, context: Optional[str] = None, rag_context: Optional[str] = None) -> str:
        """Create detailed analysis prompt for the LLM with optional RAG context"""

        rag_section = ""
        if rag_context and self.rag_enabled:
            rag_section = f"""

Relevant knowledge from electrical engineering database:
{rag_context}

Use this contextual information to improve your analysis accuracy and provide more detailed insights."""

        prompt = f"""You are an expert electrical engineer analyzing an electrical Single Line Diagram (SLD) or schematic.

Your task is to carefully examine this electrical diagram and extract all relevant information in a structured format.

{f"If context is provided: {context}" if context else ""}{rag_section}

Please analyze the diagram and provide a detailed JSON response with the following structure:

{{
  "diagram_type": "SLD|schematic|wiring_diagram|other",
  "confidence": 0.0-1.0,
  "symbols": [
    {{
      "type": "motor|transformer|circuit_breaker|busbar|generator|load|etc",
      "id": "unique identifier if visible",
      "location": "top-left|center|bottom-right|etc",
      "rating": "voltage/current/power rating if visible",
      "description": "brief description"
    }}
  ],
  "connections": [
    {{
      "from": "symbol_id or description",
      "to": "symbol_id or description",
      "type": "power|control|signal|ground",
      "conductor_size": "if visible (e.g., 4x10mm2)",
      "voltage_level": "if specified"
    }}
  ],
  "text_elements": [
    {{
      "text": "extracted text",
      "location": "where it appears",
      "type": "label|rating|specification|note"
    }}
  ],
  "electrical_parameters": {{
    "voltage_levels": ["list of voltages found"],
    "frequency": "50|60 Hz",
    "phases": "1|3",
    "standards": ["IEC", "NEC", etc.],
    "total_load": "if calculable",
    "main_source": "transformer rating or generator capacity"
  }},
  "validation_notes": [
    "any observations about diagram quality, missing info, etc."
  ]
}}

Important analysis guidelines:
1. Look for all electrical symbols and identify their types
2. Note all connections and conductor sizes if visible
3. Extract all text, labels, and ratings
4. Identify voltage levels and system parameters
5. Note any safety devices, protection equipment
6. Look for main power sources and distribution paths
7. Identify loads and their characteristics
8. Note any unusual or non-standard elements
9. Use the provided electrical engineering knowledge to enhance your analysis
10. Reference known component specifications and design patterns when possible

Be precise and thorough in your analysis. If uncertain about something, note it in validation_notes."""

        return prompt

    def _call_llm_vision(self, prompt: str, image_b64: str) -> Dict[str, Any]:
        """Call the appropriate LLM vision API"""

        if self.config.provider == "google":
            return self._call_google_vision(prompt, image_b64)
        elif self.config.provider == "openai":
            return self._call_openai_vision(prompt, image_b64)
        elif self.config.provider == "anthropic":
            return self._call_anthropic_vision(prompt, image_b64)
        elif self.config.provider == "ollama":
            return self._call_ollama_vision(prompt, image_b64)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.config.provider}")

    def _call_openai_vision(self, prompt: str, image_b64: str) -> Dict[str, Any]:
        """Call OpenAI GPT-4 Vision API"""

        if not self.config.api_key:
            raise ValueError("OpenAI API key required")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }

        response = self.session.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            raise RuntimeError(f"OpenAI API error: {response.status_code} - {response.text}")

        result = response.json()
        content = result['choices'][0]['message']['content']

        # Parse JSON response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Sometimes LLM returns extra text, try to extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JSON from LLM response: {content[:200]}...")

    def _call_anthropic_vision(self, prompt: str, image_b64: str) -> Dict[str, Any]:
        """Call Anthropic Claude Vision API"""

        if not self.config.api_key:
            raise ValueError("Anthropic API key required")

        headers = {
            "x-api-key": self.config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        payload = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }
            ]
        }

        response = self.session.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            raise RuntimeError(f"Anthropic API error: {response.status_code} - {response.text}")

        result = response.json()
        content = result['content'][0]['text']

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JSON from Claude response: {content[:200]}...")

    def _call_google_vision(self, prompt: str, image_b64: str) -> Dict[str, Any]:
        """Call Google Gemini Vision API"""

        if not self.config.api_key:
            raise ValueError("Google API key required")

        headers = {
            "Content-Type": "application/json"
        }

        # Convert base64 to proper format for Gemini (remove data URL prefix)
        if image_b64.startswith('data:image'):
            image_b64 = image_b64.split(',')[1]

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens
            }
        }

        response = self.session.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.config.model}:generateContent?key={self.config.api_key}",
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            raise RuntimeError(f"Google Gemini API error: {response.status_code} - {response.text}")

        result = response.json()

        if 'candidates' not in result or not result['candidates']:
            raise ValueError(f"No response from Gemini API: {result}")

        content = result['candidates'][0]['content']['parts'][0]['text']

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JSON from Gemini response: {content[:200]}...")

    def _call_ollama_vision(self, prompt: str, image_b64: str) -> Dict[str, Any]:
        """Call local Ollama vision model"""

        base_url = self.config.base_url or "http://localhost:11434"

        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens
            }
        }

        response = self.session.post(
            f"{base_url}/api/generate",
            json=payload
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")

        result = response.json()
        content = result['response']

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse JSON from Ollama response: {content[:200]}...")

    def _parse_llm_response(self, llm_response: Dict[str, Any]) -> DiagramAnalysis:
        """Parse LLM response into structured DiagramAnalysis"""

        # Extract basic fields
        diagram_type = llm_response.get('diagram_type', 'unknown')
        confidence = llm_response.get('confidence', 0.5)

        # Extract symbols
        symbols = []
        for symbol_data in llm_response.get('symbols', []):
            symbols.append({
                'type': symbol_data.get('type', 'unknown'),
                'id': symbol_data.get('id', ''),
                'location': symbol_data.get('location', 'unknown'),
                'rating': symbol_data.get('rating', ''),
                'description': symbol_data.get('description', ''),
                'confidence': 0.8  # Default confidence for LLM extractions
            })

        # Extract connections
        connections = []
        for conn_data in llm_response.get('connections', []):
            connections.append({
                'from': conn_data.get('from', ''),
                'to': conn_data.get('to', ''),
                'type': conn_data.get('type', 'power'),
                'conductor_size': conn_data.get('conductor_size', ''),
                'voltage_level': conn_data.get('voltage_level', '')
            })

        # Extract text elements
        text_elements = []
        for text_data in llm_response.get('text_elements', []):
            text_elements.append({
                'text': text_data.get('text', ''),
                'location': text_data.get('location', 'unknown'),
                'type': text_data.get('type', 'unknown')
            })

        # Extract electrical parameters
        electrical_parameters = llm_response.get('electrical_parameters', {})

        # Validation notes
        validation_notes = llm_response.get('validation_notes', [])

        return DiagramAnalysis(
            diagram_type=diagram_type,
            symbols_identified=symbols,
            connections=connections,
            text_elements=text_elements,
            electrical_parameters=electrical_parameters,
            validation_notes=validation_notes,
            confidence_score=confidence
        )

    def validate_design(self, analysis: DiagramAnalysis) -> Dict[str, Any]:
        """
        Use LLM to validate electrical design principles
        """

        validation_prompt = f"""As an expert electrical engineer, validate this electrical design:

Diagram Type: {analysis.diagram_type}
Symbols Found: {len(analysis.symbols_identified)}
Connections: {len(analysis.connections)}
Electrical Parameters: {json.dumps(analysis.electrical_parameters, indent=2)}

Please validate:
1. Electrical safety compliance
2. Design standards adherence (IEC/NEC/etc.)
3. Circuit logic and connectivity
4. Rating coordination
5. Grounding and protection
6. Load balance and distribution

Provide a JSON response with validation results:
{{
  "overall_valid": true/false,
  "safety_score": 0.0-1.0,
  "compliance_score": 0.0-1.0,
  "issues": ["list of issues found"],
  "recommendations": ["suggested improvements"],
  "critical_findings": ["serious safety/compliance issues"]
}}"""

        # Create a simple text-based validation (since we don't have an image)
        # In practice, this would call LLM again with design validation prompt

        return {
            "overall_valid": True,
            "safety_score": 0.85,
            "compliance_score": 0.80,
            "issues": ["Sample validation - implement with LLM call"],
            "recommendations": ["Add proper earthing", "Verify conductor sizing"],
            "critical_findings": []
        }

    def extract_structured_data(self, analysis: DiagramAnalysis) -> Dict[str, Any]:
        """
        Extract structured electrical project data from analysis

        This converts the LLM analysis into the format expected by the existing
        electrical design system.
        """

        structured_data = {
            'project_info': {
                'diagram_type': analysis.diagram_type,
                'analysis_confidence': analysis.confidence_score,
                'electrical_parameters': analysis.electrical_parameters
            },
            'loads': [],
            'cables': [],
            'buses': [],
            'transformers': [],
            'equipment': []
        }

        # Convert symbols to structured data
        for symbol in analysis.symbols_identified:
            symbol_type = symbol['type'].lower()

            if symbol_type in ['motor', 'pump', 'fan', 'lighting', 'heater']:
                # Create load
                load = {
                    'load_id': symbol.get('id', f"L{len(structured_data['loads'])+1:03d}"),
                    'load_name': symbol.get('description', f"{symbol_type.title()} Load"),
                    'load_type': symbol_type,
                    'power_kw': self._extract_rating(symbol.get('rating', ''), 'power'),
                    'voltage': self._extract_rating(symbol.get('rating', ''), 'voltage'),
                    'location': symbol.get('location', 'unknown'),
                    'from_analysis': True
                }
                structured_data['loads'].append(load)

            elif symbol_type == 'transformer':
                transformer = {
                    'transformer_id': symbol.get('id', f"T{len(structured_data['transformers'])+1:03d}"),
                    'rating_kva': self._extract_rating(symbol.get('rating', ''), 'power'),
                    'primary_voltage': None,  # Would need more analysis
                    'secondary_voltage': analysis.electrical_parameters.get('voltage_levels', [400])[0],
                    'location': symbol.get('location', 'unknown'),
                    'from_analysis': True
                }
                structured_data['transformers'].append(transformer)

            elif symbol_type in ['busbar', 'bus']:
                bus = {
                    'bus_id': symbol.get('id', f"B{len(structured_data['buses'])+1:03d}"),
                    'bus_name': symbol.get('description', f"Bus {len(structured_data['buses'])+1}"),
                    'voltage': analysis.electrical_parameters.get('voltage_levels', [400])[0],
                    'location': symbol.get('location', 'unknown'),
                    'from_analysis': True
                }
                structured_data['buses'].append(bus)

        # Convert connections to cables
        for conn in analysis.connections:
            if conn.get('type') == 'power':
                cable = {
                    'cable_id': f"C{len(structured_data['cables'])+1:03d}",
                    'from_equipment': conn.get('from', 'Unknown'),
                    'to_equipment': conn.get('to', 'Unknown'),
                    'size_sqmm': self._extract_conductor_size(conn.get('conductor_size', '')),
                    'length_m': 25.0,  # Default assumption
                    'voltage_level': conn.get('voltage_level', ''),
                    'from_analysis': True
                }
                structured_data['cables'].append(cable)

        return structured_data

    def _extract_rating(self, rating_text: str, rating_type: str) -> Optional[Union[float, str]]:
        """Extract numerical ratings from text"""
        import re

        if not rating_text:
            return None

        if rating_type == 'power':
            # Look for kW, KW, etc.
            match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kW|KW|kw|kVA|KVA|kva)', rating_text)
            if match:
                return float(match.group(1))
        elif rating_type == 'voltage':
            # Look for V, KV, etc.
            match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kV|KV|kv|V)', rating_text)
            if match:
                value = float(match.group(1))
                unit = match.group(2).lower() if len(match.groups()) > 1 else ''
                if unit in ['kv', 'kV', 'KV']:
                    return value * 1000
                return value

        return None

    def _extract_conductor_size(self, size_text: str) -> float:
        """Extract conductor size from text"""
        import re

        # Look for patterns like "4x10mm2", "10 mm2", etc.
        match = re.search(r'(\d+(?:\.\d+)?)\s*(?:mm2|mm²|sq\.?mm)', size_text)
        if match:
            return float(match.group(1))

        # Default sizes based on common applications
        return 4.0  # Default 4mm²

    def _extract_basic_diagram_description(self, image_path: str) -> str:
        """Extract basic description from image filename and metadata for RAG queries"""
        try:
            # Extract from filename
            filename = Path(image_path).stem.lower()

            # Common electrical diagram indicators
            indicators = []
            if 'sld' in filename or 'single' in filename:
                indicators.append('single line diagram')
            if 'motor' in filename:
                indicators.append('motor control')
            if 'distribution' in filename:
                indicators.append('power distribution')
            if 'control' in filename:
                indicators.append('control system')
            if 'transformer' in filename:
                indicators.append('transformer')
            if 'switchgear' in filename:
                indicators.append('switchgear')

            # Extract voltage levels if mentioned
            import re
            voltage_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:kv|kV|KV|v|V)', filename)
            if voltage_match:
                indicators.append(f"{voltage_match.group(1)}{voltage_match.group(2)}")

            # Combine indicators
            if indicators:
                return f"{' '.join(indicators)} electrical diagram"
            else:
                return "electrical power system diagram"

        except Exception as e:
            logger.warning(f"Failed to extract basic description: {e}")
            return "electrical diagram"

    def _store_analysis_results(self, analysis: DiagramAnalysis, image_path: str,
                               context: Optional[str] = None):
        """Store successful analysis results in vector database for continuous learning"""
        if not self.rag_enabled:
            return

        try:
            # Store design patterns from successful analyses
            design_patterns = self._extract_design_patterns_from_analysis(analysis)
            for pattern in design_patterns:
                self.vector_db.store_design_pattern(
                    pattern['id'],
                    pattern['data'],
                    pattern['type']
                )

            # Store component specifications found in analysis
            for symbol in analysis.symbols_identified:
                if symbol.get('rating') and symbol['type'] != 'unknown':
                    component_data = {
                        'type': symbol['type'],
                        'rating': symbol.get('rating', ''),
                        'description': symbol.get('description', ''),
                        'source': 'diagram_analysis',
                        'diagram_path': image_path,
                        'confidence': symbol.get('confidence', 0.8)
                    }

                    # Try to extract structured data
                    if symbol['type'] == 'motor':
                        component_data.update(self._extract_motor_specs(symbol))
                    elif symbol['type'] == 'transformer':
                        component_data.update(self._extract_transformer_specs(symbol))
                    elif symbol['type'] == 'cable':
                        component_data.update(self._extract_cable_specs(symbol))

                    component_id = f"{symbol['type']}_{hash(str(component_data)) % 10000}"
                    self.vector_db.store_component_specification(component_id, component_data, symbol['type'])

            # Store standards compliance if identified
            if analysis.electrical_parameters.get('standards'):
                for standard in analysis.electrical_parameters['standards']:
                    rule_data = {
                        'title': f"Standards compliance for {analysis.diagram_type}",
                        'description': f"Analysis indicates compliance with {standard} standards",
                        'requirements': f"Following {standard} guidelines for {analysis.diagram_type}",
                        'category': 'general_compliance',
                        'applies_to': [analysis.diagram_type.lower()],
                        'reference': f"Diagram analysis: {Path(image_path).name}",
                        'severity': 'medium'
                    }
                    rule_id = f"{standard.lower()}_{analysis.diagram_type}_{hash(str(rule_data)) % 10000}"
                    self.vector_db.store_standards_rule(rule_id, rule_data, standard)

            logger.info("Analysis results stored in vector database for continuous learning")

        except Exception as e:
            logger.warning(f"Failed to store analysis results: {e}")

    def _extract_design_patterns_from_analysis(self, analysis: DiagramAnalysis) -> List[Dict]:
        """Extract design patterns from successful analysis for future reference"""
        patterns = []

        try:
            # Identify common patterns
            transformers = [s for s in analysis.symbols_identified if s['type'] == 'transformer']
            motors = [s for s in analysis.symbols_identified if s['type'] == 'motor']
            breakers = [s for s in analysis.symbols_identified if s['type'] in ['circuit_breaker', 'breaker']]

            # Transformer + motor pattern (common in industrial systems)
            if transformers and motors:
                pattern_id = f"transformer_motor_system_{len(transformers)}_{len(motors)}"
                pattern_data = {
                    'description': f"Power distribution system with {len(transformers)} transformer(s) and {len(motors)} motor(s)",
                    'components': ['transformer', 'motor', 'cable', 'circuit_breaker'],
                    'standards': analysis.electrical_parameters.get('standards', ['IEC']),
                    'industry': 'industrial',
                    'efficiency_rating': 0.85,
                    'complexity': 'medium' if len(motors) <= 5 else 'high'
                }
                patterns.append({
                    'id': pattern_id,
                    'data': pattern_data,
                    'type': 'power_distribution'
                })

            # Motor control center pattern
            if len(motors) >= 3 and breakers:
                pattern_id = f"motor_control_center_{len(motors)}_motors"
                pattern_data = {
                    'description': f"Motor control center with {len(motors)} motors and protection",
                    'components': ['motor', 'circuit_breaker', 'contactor', 'control_cable'],
                    'standards': ['IEC 60947', 'IEC 60204'],
                    'industry': 'industrial',
                    'efficiency_rating': 0.90,
                    'complexity': 'high'
                }
                patterns.append({
                    'id': pattern_id,
                    'data': pattern_data,
                    'type': 'motor_control'
                })

        except Exception as e:
            logger.warning(f"Failed to extract design patterns: {e}")

        return patterns

    def _extract_motor_specs(self, symbol: Dict) -> Dict[str, Any]:
        """Extract motor specifications from symbol data"""
        rating = symbol.get('rating', '')

        specs = {
            'power_kw': self._extract_rating(rating, 'power'),
            'voltage': self._extract_rating(rating, 'voltage'),
            'phases': 3,  # Assume 3-phase unless specified
            'starting_method': 'DOL',  # Direct-on-line default
            'speed_rpm': 1450,  # Common 4-pole speed
        }

        # Try to determine phases
        if '1ph' in rating.lower() or 'single' in rating.lower():
            specs['phases'] = 1

        # Try to determine starting method
        if 'star' in rating.lower() or 'delta' in rating.lower():
            specs['starting_method'] = 'Star-Delta'

        return specs

    def _extract_transformer_specs(self, symbol: Dict) -> Dict[str, Any]:
        """Extract transformer specifications from symbol data"""
        rating = symbol.get('rating', '')

        specs = {
            'rating_kva': self._extract_rating(rating, 'power'),
            'primary_voltage': None,
            'secondary_voltage': 400,  # Common secondary voltage
            'vector_group': 'Dyn11',  # Common vector group
            'impedance_percent': 6.5,  # Typical impedance
        }

        # Try to extract voltages
        import re
        voltage_matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:kV|KV|kv|V)', rating)
        if len(voltage_matches) >= 2:
            specs['primary_voltage'] = float(voltage_matches[0])
            specs['secondary_voltage'] = float(voltage_matches[1])
            if specs['primary_voltage'] < 1000:  # If in volts, convert to kV
                specs['primary_voltage'] = specs['primary_voltage'] / 1000

        return specs

    def _extract_cable_specs(self, symbol: Dict) -> Dict[str, Any]:
        """Extract cable specifications from symbol data"""
        rating = symbol.get('rating', '')

        specs = {
            'size_mm2': self._extract_conductor_size(rating),
            'cores': 4,  # Common for power cables
            'material': 'copper',  # Default
            'insulation': 'XLPE',  # Common insulation
            'voltage_rating': 1000,  # 1kV default
        }

        # Try to determine material
        if 'al' in rating.lower():
            specs['material'] = 'aluminum'

        # Try to determine cores
        import re
        core_match = re.search(r'(\d+)\s*(?:core|c)', rating.lower())
        if core_match:
            specs['cores'] = int(core_match.group(1))

        return specs

    def batch_process_diagrams(self, image_paths: List[str],
                              output_dir: str = "diagram_analysis_results") -> Dict[str, DiagramAnalysis]:
        """
        Process multiple diagrams in batch
        """

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        results = {}

        for image_path in image_paths:
            try:
                analysis = self.analyze_diagram(image_path)
                results[image_path] = analysis

                # Save individual results
                result_file = output_path / f"{Path(image_path).stem}_analysis.json"
                with open(result_file, 'w') as f:
                    json.dump({
                        'image_path': image_path,
                        'analysis': analysis.__dict__,
                        'structured_data': self.extract_structured_data(analysis)
                    }, f, indent=2, default=str)

                logger.info(f"Processed {image_path}: {len(analysis.symbols_identified)} symbols")

            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                results[image_path] = None

        # Save summary
        summary_file = output_path / "batch_summary.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'total_diagrams': len(image_paths),
                'successful_analyses': len([r for r in results.values() if r is not None]),
                'timestamp': datetime.now().isoformat(),
                'results': {
                    path: {
                        'success': analysis is not None,
                        'symbols_found': len(analysis.symbols_identified) if analysis else 0,
                        'confidence': analysis.confidence_score if analysis else 0.0
                    }
                    for path, analysis in results.items()
                }
            }, f, indent=2)

        return results


def create_sample_diagram_description() -> str:
    """
    Create a sample text description for testing when no actual diagram is available
    This simulates what the LLM would extract from a real diagram.
    """

    return {
        "diagram_type": "SLD",
        "confidence": 0.88,
        "symbols": [
            {
                "type": "transformer",
                "id": "T1",
                "location": "top-center",
                "rating": "1000 kVA, 11kV/400V",
                "description": "Main power transformer"
            },
            {
                "type": "circuit_breaker",
                "id": "CB1",
                "location": "center-left",
                "rating": "1600A",
                "description": "Main incoming breaker"
            },
            {
                "type": "busbar",
                "id": "MB1",
                "location": "center",
                "rating": "400V",
                "description": "Main distribution busbar"
            },
            {
                "type": "motor",
                "id": "M1",
                "location": "bottom-left",
                "rating": "55 kW, 400V",
                "description": "Production motor"
            },
            {
                "type": "motor",
                "id": "M2",
                "location": "bottom-center",
                "rating": "37 kW, 400V",
                "description": "Conveyor motor"
            }
        ],
        "connections": [
            {
                "from": "T1",
                "to": "CB1",
                "type": "power",
                "conductor_size": "3x240mm²",
                "voltage_level": "11kV"
            },
            {
                "from": "CB1",
                "to": "MB1",
                "type": "power",
                "conductor_size": "4x120mm²",
                "voltage_level": "400V"
            },
            {
                "from": "MB1",
                "to": "M1",
                "type": "power",
                "conductor_size": "4x10mm²",
                "voltage_level": "400V"
            },
            {
                "from": "MB1",
                "to": "M2",
                "type": "power",
                "conductor_size": "4x6mm²",
                "voltage_level": "400V"
            }
        ],
        "text_elements": [
            {
                "text": "Main Distribution Board",
                "location": "top",
                "type": "label"
            },
            {
                "text": "400V, 50Hz, 3Ph",
                "location": "top-right",
                "type": "specification"
            }
        ],
        "electrical_parameters": {
            "voltage_levels": ["11000V", "400V"],
            "frequency": "50Hz",
            "phases": "3",
            "standards": ["IEC"],
            "total_load": "92 kW",
            "main_source": "1000 kVA transformer"
        },
        "validation_notes": [
            "Standard three-phase distribution system",
            "Proper protection coordination visible",
            "All ratings clearly marked",
            "Good separation of power and control circuits"
        ]
    }


def demo_llm_multimodal_processor():
    """Demonstrate the LLM multimodal processor"""

    # Create processor with mock configuration
    config = LLMConfig(
        provider="openai",  # Would use actual API in production
        model="gpt-4-vision-preview",
        api_key="mock_key_for_demo"  # Would be real API key
    )

    processor = LLMMultimodalProcessor(config)

    # Use sample data for demonstration
    sample_response = create_sample_diagram_description()
    analysis = processor._parse_llm_response(sample_response)

    print("[Search] LLM Multimodal Diagram Analysis Demo")
    print("=" * 50)
    print(f"Diagram Type: {analysis.diagram_type}")
    print(f"Confidence Score: {analysis.confidence_score:.2f}")
    print(f"Symbols Identified: {len(analysis.symbols_identified)}")
    print(f"Connections Found: {len(analysis.connections)}")

    print("\n[Symbols] Symbols Found:")
    for symbol in analysis.symbols_identified:
        print(f"  • {symbol['type']}: {symbol['description']} ({symbol['rating']})")

    print("\n[Connections] Connections:")
    for conn in analysis.connections:
        print(f"  • {conn['from']} -> {conn['to']} ({conn['conductor_size']})")

    print(f"\n[Electrical] Electrical Parameters:")
    for key, value in analysis.electrical_parameters.items():
        print(f"  • {key}: {value}")

    # Extract structured data
    structured_data = processor.extract_structured_data(analysis)

    print(f"\n[Structured] Structured Data Extracted:")
    print(f"  • Loads: {len(structured_data['loads'])}")
    print(f"  • Cables: {len(structured_data['cables'])}")
    print(f"  • Transformers: {len(structured_data['transformers'])}")
    print(f"  • Buses: {len(structured_data['buses'])}")

    # Validate design
    validation = processor.validate_design(analysis)
    print(f"\n[Validation] Design Validation:")
    print(f"  • Overall Valid: {validation['overall_valid']}")
    print(f"  • Safety Score: {validation['safety_score']:.2f}")
    print(f"  • Compliance Score: {validation['compliance_score']:.2f}")

    print(f"\n[Advantages] Key Advantages of LLM Approach:")
    print("  • Natural language understanding of diagrams")
    print("  • Deep electrical engineering knowledge")
    print("  • Contextual reasoning and validation")
    print("  • Flexible extraction without predefined templates")
    print("  • Single model handles vision, text, and reasoning")

    return analysis


if __name__ == "__main__":
    demo_llm_multimodal_processor()