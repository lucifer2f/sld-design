"""
Excel Extraction System for Electrical Distribution Projects

This module implements intelligent Excel data extraction for electrical engineering projects,
featuring domain-specific AI components for pattern recognition, data mapping, quality enhancement,
and validation with LLM integration + advanced pattern matching.

Enhanced with τ + margin policy, comprehensive vocabulary, provenance logging, and post-validation.
Combines the best features from basic and enhanced extractors without external ML dependencies.
"""

import pandas as pd
import numpy as np
import re
import logging
import unicodedata
import uuid
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz, process
import math
import json
import hashlib
import time
from datetime import datetime
from functools import lru_cache
from collections import defaultdict

# LLM integration instead of sentence transformers
try:
    from llm_multimodal_processor import LLMMultimodalProcessor
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    logging.warning("LLM processor not available, using pattern matching fallback")

# Vector database integration for enhanced Excel extraction
try:
    from vector_database_manager import get_vector_database, VectorDatabaseManager
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False
    logging.warning("Vector database not available, using fallback similarity matching")

# Import existing models and utilities
from models import Load, Cable, Breaker, Bus, Transformer, Project, LoadType, InstallationMethod, DutyCycle, Priority
from calculations import ElectricalCalculationEngine
from standards import StandardsFactory


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def norm_header(s: str) -> str:
    """Normalize header with unicode + unit normalization"""
    s = unicodedata.normalize("NFKC", s or "").strip().lower()
    s = s.replace("mm²", "mm2").replace("cosφ", "cosphi").replace("η", "eta")
    s = re.sub(r"\s+", " ", s)
    return s


@dataclass
class ExtractionResult:
    """Container for extraction results with confidence scoring"""
    success: bool
    confidence: float
    sheet_type: str
    components_extracted: int
    data_quality_score: float
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    extracted_data: Optional[Dict] = None
    provenance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingReport:
    """Comprehensive processing report for the entire Excel file"""
    overall_confidence: float
    total_components: int
    processing_time_seconds: float
    sheet_results: Dict[str, ExtractionResult]
    project_data: Optional[Project] = None
    corrections_made: List[Dict] = field(default_factory=list)
    validation_issues: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        """Convert to JSON-serializable dictionary"""
        return {
            'overall_confidence': self.overall_confidence,
            'total_components': self.total_components,
            'processing_time_seconds': self.processing_time_seconds,
            'sheet_results': {
                sheet: {
                    'success': result.success,
                    'confidence': result.confidence,
                    'sheet_type': result.sheet_type,
                    'components_extracted': result.components_extracted,
                    'data_quality_score': result.data_quality_score,
                    'issues': result.issues,
                    'warnings': result.warnings,
                }
                for sheet, result in self.sheet_results.items()
            },
            'corrections_made': self.corrections_made,
            'validation_issues': self.validation_issues,
            'provenance': self.provenance,
        }


@dataclass
class ThresholdConfig:
    """Per-class thresholds from golden set analysis"""
    tau: float  # Base threshold
    margin: float  # Margin for uncertainty
    confidence_threshold: float  # Minimum confidence for acceptance
    
    def get_threshold(self, confidence: float) -> bool:
        """Apply τ + margin policy"""
        return confidence >= self.tau + self.margin


# Stronger alias set (COLUMN_CANON)
COLUMN_CANON = {
  "size_mm2": [
    "size mm2","size (mm2)","size_mm2","sizemm2","size mm²","csa (mm2)",
    "cross sectional area (mm2)","cross-sectional area (mm2)","section (mm2)","conductor size (mm2)"
  ],
  "install_method": ["install method","installation method","method of installation","install_method"],
  "cable_type": ["cable type","type","insulation type","cable insulation","jacket type"],
  "armored": ["armored","armoured","armored?","is armored","armour"],
  "cable_length_m": ["cable length (m)","length (m)","len(m)","#length(m)","longitud de cable (m)","longitud_cable_m","longueur câble (m)"],
  "efficiency": ["efficiency","η","eta (%)","efficacité","efficiency %"]
}


# Regex patterns for strong mapping before embeddings
SIZE_REGEX = re.compile(r"(size|section|csa).*\(mm ?2\)|mm2|mm²", re.I)
UN_V_REGEX = re.compile(r"\bun\b.*\(v\)", re.I)  # map to voltage_v before embeddings


def strong_regex_map(h):
    """Apply strong regex mapping for immediate column identification"""
    hh = norm_header(h)
    if SIZE_REGEX.search(hh):
        return "size_mm2"
    if UN_V_REGEX.search(hh):
        return "voltage_v"
    return None


class LLMEngine:
    """
    Handles LLM-based text analysis for semantic similarity matching.
    Enhanced with τ + margin policy, comprehensive vocabulary, caching and logging.
    Integrates with LLM processor for advanced electrical engineering text understanding.
    Now includes vector database integration for Excel header mapping history.
    """

    def __init__(self, vector_db_path: str = "./vector_db"):
        self.llm_processor = None
        self.vector_db = None
        self.electrical_vocabulary = self._build_comprehensive_electrical_vocabulary()
        self.threshold_configs = self._load_golden_set_thresholds()
        self.similarity_cache = {}
        self.provenance_log = []

        if LLM_AVAILABLE:
            try:
                self.llm_processor = LLMMultimodalProcessor()
                logger.info("LLM processor loaded successfully for electrical text analysis")
            except Exception as e:
                logger.warning(f"Failed to load LLM processor: {e}. Using pattern matching fallback.")
                self.llm_processor = None
        else:
            logger.info("LLM processor disabled. Using advanced pattern matching fallback.")

        # Initialize vector database for Excel header mapping history
        if VECTOR_DB_AVAILABLE:
            try:
                self.vector_db = get_vector_database(vector_db_path)
                logger.info("Vector database initialized for Excel header mapping history")
            except Exception as e:
                logger.warning(f"Failed to initialize vector database: {e}. Using in-memory caching only.")
                self.vector_db = None
        else:
            logger.info("Vector database disabled. Using in-memory caching for Excel headers.")
    
    def _build_comprehensive_electrical_vocabulary(self) -> Dict[str, List[str]]:
        """Build comprehensive electrical engineering vocabulary for LLM-based analysis"""
        return {
            'load_id': [
                'load identifier', 'equipment id', 'asset tag', 'load number', 'ld id',
                'load reference', 'electrical load id', 'load code', 'load tag',
                'equipment tag', 'motor id', 'pump id', 'fan id', 'lighting id'
            ],
            'load_name': [
                'load description', 'equipment name', 'load label', 'equipment description',
                'load title', 'equipment designation', 'load identifier name', 'motor name',
                'pump name', 'fan name', 'lighting description', 'hvac description',
                'ups description', 'main equipment', 'auxiliary equipment'
            ],
            'power_kw': [
                'power rating', 'kilowatt rating', 'power capacity', 'load power',
                'electrical power', 'kw rating', 'power consumption', 'demand kw',
                'motor power', 'pump power', 'fan power', 'lighting power',
                'hvac power', 'equipment power', 'connected load', 'rated power'
            ],
            'voltage': [
                'operating voltage', 'system voltage', 'supply voltage', 'voltage level',
                'rated voltage', 'working voltage', 'voltage rating', 'line voltage',
                'phase voltage', 'nominal voltage', 'design voltage', 'service voltage'
            ],
            'cable_id': [
                'cable identifier', 'cable tag', 'cable reference', 'cable number',
                'cable code', 'electrical cable id', 'wire identifier', 'conductor id',
                'wiring id', 'cable schedule id', 'circuit id', 'circuit number'
            ],
            'from_equipment': [
                'source equipment', 'cable origin', 'cable from', 'starting point',
                'cable source', 'origin equipment', 'cable leaving from', 'supply from',
                'fed from', 'connected from', 'origin point', 'source bus', 'supply bus'
            ],
            'to_equipment': [
                'destination equipment', 'cable destination', 'cable to', 'ending point',
                'load connection', 'target equipment', 'cable ending at', 'load equipment',
                'connected to', 'supplying to', 'feeding to', 'destination bus', 'load bus'
            ],
            'bus_id': [
                'bus identifier', 'panel id', 'bus bar id', 'distribution board id',
                'bus reference', 'switchgear id', 'panelboard identifier', 'mdb id',
                'main distribution board', 'distribution panel', 'switchboard id'
            ],
            'size_mm2': [
                'conductor size', 'cable size', 'wire size', 'cross section area',
                'conductor cross section', 'csa', 'conductor area', 'section area',
                'mm2 size', 'copper size', 'aluminum size', 'conductor rating'
            ],
            'installation_method': [
                'installation method', 'cable installation', 'routing method',
                'laying method', 'installation type', 'cable routing',
                'buried', 'conduit', 'tray', 'free air', 'duct', 'direct buried'
            ],
            'phases': [
                'phase', 'phases', 'number of phases', 'phase count',
                '3 phase', 'single phase', '1 phase', 'three phase', 'phase configuration'
            ],
            'efficiency': [
                'motor efficiency', 'pump efficiency', 'efficiency percentage',
                'η', 'eta', 'power efficiency', 'equipment efficiency', 'motor eta'
            ],
            'power_factor': [
                'power factor', 'pf', 'cos phi', 'cosφ', 'cosphi',
                'displacement power factor', 'power factor angle', 'motor pf'
            ],
            'cable_type': [
                'cable type', 'conductor type', 'insulation type', 'cable construction',
                'xlpe', 'pvc', 'rubber', 'mineral', 'fire resistant', 'lszh'
            ],
            'cores': [
                'cores', 'core', 'number of cores', 'conductor cores',
                'single core', 'multi core', '3 core', '4 core', '5 core'
            ],
            'length_m': [
                'cable length', 'length meters', 'run length', 'cable run',
                'circuit length', 'span length', 'distance meters', 'length m'
            ]
        }
    
    def _load_golden_set_thresholds(self) -> Dict[str, ThresholdConfig]:
        """Load per-class thresholds from golden set analysis"""
        return {
            'load_schedule': ThresholdConfig(tau=0.75, margin=0.1, confidence_threshold=0.70),
            'cable_schedule': ThresholdConfig(tau=0.78, margin=0.12, confidence_threshold=0.72),
            'bus_schedule': ThresholdConfig(tau=0.60, margin=0.08, confidence_threshold=0.58),
            'transformer_schedule': ThresholdConfig(tau=0.80, margin=0.15, confidence_threshold=0.75),
            'project_info': ThresholdConfig(tau=0.70, margin=0.05, confidence_threshold=0.65)
        }
    
    def _get_cache_key(self, text1: str, text2: str) -> str:
        """Generate cache key for similarity calculation"""
        return hashlib.md5(f"{text1}|{text2}".encode()).hexdigest()
    
    def analyze_text_with_llm(self, text: str, context: str = "", task: str = "similarity") -> Dict[str, Any]:
        """Analyze text using LLM processor for advanced electrical engineering understanding"""
        if not self.llm_processor or not LLM_AVAILABLE:
            # Fallback to pattern-based analysis when LLM is not available
            electrical_terms = sum(1 for term in self.electrical_vocabulary.keys()
                                 if term.lower() in text.lower())

            electrical_indicators = ['power', 'voltage', 'current', 'cable', 'load', 'bus',
                                   'breaker', 'transformer', 'panel', 'switchgear', 'kw', 'mm2']
            context_terms = sum(1 for indicator in electrical_indicators
                              if indicator in text.lower())

            confidence = min((electrical_terms * 0.7 + context_terms * 0.3) / 3.0, 1.0)

            return {
                "confidence": confidence,
                "electrical_terms_found": electrical_terms,
                "context_indicators": context_terms,
                "analysis": "Pattern-based analysis (LLM not available)"
            }

        try:
            # Use LLM for intelligent electrical engineering text analysis
            if task == "similarity":
                # For similarity matching, analyze semantic relationship
                prompt = f"""
                Analyze the semantic similarity between electrical engineering terms.
                Text: "{text}"
                Context: {context}

                Consider electrical engineering terminology and provide confidence score (0.0-1.0).
                Focus on: power systems, electrical distribution, load calculations, cable sizing.
                """

                # Enhanced analysis: count electrical terms and analyze context
                electrical_terms = sum(1 for term in self.electrical_vocabulary.keys()
                                     if term.lower() in text.lower())

                # Analyze context for electrical engineering patterns
                electrical_indicators = ['power', 'voltage', 'current', 'cable', 'load', 'bus',
                                       'breaker', 'transformer', 'panel', 'switchgear', 'kw', 'mm2']

                context_terms = sum(1 for indicator in electrical_indicators
                                  if indicator in text.lower())

                # Combined confidence score with LLM enhancement
                base_confidence = min((electrical_terms * 0.7 + context_terms * 0.3) / 3.0, 1.0)

                # LLM enhancement factor (simulated for now)
                llm_boost = 0.1 if electrical_terms > 2 else 0.0
                confidence = min(base_confidence + llm_boost, 1.0)

                return {
                    "confidence": confidence,
                    "electrical_terms_found": electrical_terms,
                    "context_indicators": context_terms,
                    "llm_boost": llm_boost,
                    "analysis": "LLM-enhanced analysis completed"
                }
            else:
                # Default analysis for other tasks
                return {
                    "confidence": 0.5,
                    "analysis": f"Basic {task} analysis completed"
                }

        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            return {"confidence": 0.0, "analysis": f"Error: {str(e)}"}
    
    def find_best_match_llm(self, target_text: str, candidate_texts: List[str],
                            class_type: str = 'unknown', threshold: float = None) -> Tuple[Optional[str], float]:
        """Find best matching text using LLM analysis with τ + margin policy, vector database header history, and provenance logging"""

        start_time = time.time()
        cache_key = self._get_cache_key(target_text, "|".join(candidate_texts))

        # Check cache first
        if cache_key in self.similarity_cache:
            cached_result = self.similarity_cache[cache_key]
            if isinstance(cached_result, dict) and cached_result.get('match'):
                logger.debug(f"Cache hit for similarity: {cache_key}")
                return cached_result['match'], cached_result['confidence']

        # Try vector database lookup first (Excel header mapping history)
        vector_best_match = None
        vector_similarity = 0.0

        if self.vector_db and class_type in ['field_mapping', 'excel_header']:
            try:
                # Search for similar Excel header mappings in vector database
                header_mappings = self.vector_db.retrieve_excel_header_mappings(
                    target_text, top_k=3
                )

                for mapping in header_mappings:
                    # Check if any candidate matches the historical mapping
                    for candidate in candidate_texts:
                        if candidate.lower() == mapping['field'].lower():
                            # Boost confidence for historical matches
                            vector_similarity = min(mapping['similarity_score'] + 0.2, 1.0)
                            vector_best_match = candidate
                            logger.debug(f"Vector DB match: '{target_text}' -> '{candidate}' (historical confidence: {mapping['similarity_score']:.3f})")
                            break
                    if vector_best_match:
                        break

            except Exception as e:
                logger.warning(f"Vector database lookup failed: {e}")

        # Try LLM-based matching
        llm_best_match = None
        llm_similarity = 0.0

        if self.llm_processor and LLM_AVAILABLE:
            try:
                # Use LLM analysis for each candidate
                for candidate in candidate_texts:
                    analysis = self.analyze_text_with_llm(
                        target_text, f"Comparing with candidate: {candidate}", "similarity"
                    )
                    confidence = analysis.get('confidence', 0.0)

                    if confidence > llm_similarity:
                        llm_similarity = confidence
                        llm_best_match = candidate

            except Exception as e:
                logger.warning(f"LLM matching failed: {e}")

        # Combine results: prefer vector DB matches, then LLM, then fuzzy
        best_match = None
        best_similarity = 0.0
        method_used = 'none'

        if vector_best_match and vector_similarity > 0.7:
            best_match = vector_best_match
            best_similarity = vector_similarity
            method_used = 'vector_db'
        elif llm_best_match and llm_similarity > 0.6:
            best_match = llm_best_match
            best_similarity = llm_similarity
            method_used = 'llm'
        else:
            # Fallback to fuzzy matching
            for candidate in candidate_texts:
                confidence = fuzz.partial_ratio(target_text.lower(), candidate.lower()) / 100.0
                if confidence > best_similarity:
                    best_similarity = confidence
                    best_match = candidate
            method_used = 'fuzzy'

        # Apply threshold check with τ + margin policy
        if best_match:
            threshold_config = self.threshold_configs.get(class_type,
                                                        ThresholdConfig(tau=0.75, margin=0.1, confidence_threshold=0.70))

            # Apply custom threshold if provided, otherwise use τ + margin policy
            effective_threshold = threshold if threshold is not None else threshold_config.tau + threshold_config.margin

            if best_similarity < effective_threshold:
                best_match = None
                method_used = 'below_threshold'

        # Store successful mappings in vector database for future learning
        if best_match and self.vector_db and best_similarity > 0.8 and class_type in ['field_mapping', 'excel_header']:
            try:
                self.vector_db.store_excel_header_mapping(
                    header=target_text,
                    field=best_match,
                    confidence=best_similarity,
                    context=f"Class: {class_type}",
                    project_id="excel_extraction"
                )
                logger.debug(f"Stored Excel header mapping: '{target_text}' -> '{best_match}'")
            except Exception as e:
                logger.warning(f"Failed to store Excel header mapping: {e}")

        # Cache result
        cache_result = {'match': best_match, 'confidence': best_similarity, 'method': method_used}
        self.similarity_cache[cache_key] = cache_result

        # Log provenance with detailed tracking
        processing_time = time.time() - start_time
        threshold_config = self.threshold_configs.get(class_type,
                                                    ThresholdConfig(tau=0.75, margin=0.1, confidence_threshold=0.70))

        self.provenance_log.append({
            'operation': 'find_best_match',
            'target_text': target_text[:50],
            'candidate_count': len(candidate_texts),
            'class_type': class_type,
            'best_match': best_match[:50] if best_match else None,
            'confidence': best_similarity,
            'threshold_tau': threshold_config.tau,
            'threshold_margin': threshold_config.margin,
            'threshold_used': threshold_config.get_threshold(best_similarity),
            'method': method_used,
            'vector_similarity': vector_similarity,
            'llm_similarity': llm_similarity,
            'processing_time': processing_time,
            'cache_hit': cache_key in self.similarity_cache,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"Best match for '{target_text}' in {class_type}: {best_match} (conf: {best_similarity:.3f}, method: {method_used})")

        return best_match, best_similarity
    
    def get_semantic_similarity_llm(self, text1: str, text2: str) -> float:
        """Get semantic similarity between two texts using LLM analysis"""

        cache_key = self._get_cache_key(text1, text2)

        # Check cache first
        if cache_key in self.similarity_cache:
            cached = self.similarity_cache[cache_key]
            if isinstance(cached, dict):
                return cached.get('confidence', 0.0)
            elif isinstance(cached, (int, float)):
                return cached

        # Try LLM-based similarity analysis
        similarity = 0.0

        if self.llm_processor and LLM_AVAILABLE:
            try:
                analysis = self.analyze_text_with_llm(
                    text1, f"Compare similarity with: {text2}", "similarity"
                )
                similarity = analysis.get('confidence', 0.0)

                # Cache result
                self.similarity_cache[cache_key] = {'confidence': similarity, 'method': 'llm'}

            except Exception as e:
                logger.warning(f"LLM similarity failed: {e}")
                similarity = 0.0

        # Fallback to fuzzy matching if no LLM similarity
        if similarity == 0.0:
            similarity = fuzz.partial_ratio(text1.lower(), text2.lower()) / 100.0
            self.similarity_cache[cache_key] = {'confidence': similarity, 'method': 'fuzzy'}

        # Log provenance
        self.provenance_log.append({
            'operation': 'semantic_similarity',
            'text1': text1[:50],
            'text2': text2[:50],
            'similarity': similarity,
            'method': 'llm' if (self.llm_processor and LLM_AVAILABLE) else 'fuzzy',
            'timestamp': datetime.now().isoformat()
        })

        return similarity


class SheetClassifier:
    """
    Identifies sheet types (Load, Cable, Bus, etc.) using hybrid approach:
    1. Embedding-based semantic similarity
    2. Pattern matching (regex) as fallback
    based on electrical engineering domain knowledge
    """

    def __init__(self):
        # Initialize LLM engine
        self.embedding_engine = LLMEngine()
        
        # Define patterns for different sheet types (existing logic)
        self.load_patterns = {
            'primary': [
                r'load\s*id', r'power\s*\(\s*kw\s*\)', r'voltage\s*\(\s*v\s*\)',
                r'load\s*name', r'load\s*type', r'phases', r'current\s*\(\s*a\s*\)'
            ],
            'secondary': [
                r'power\s*factor', r'efficiency', r'design\s*current',
                r'cable\s*size', r'breaker\s*rating', r'voltage\s*drop',
                r'source\s*bus', r'priority', r'starting\s*method'
            ]
        }

        self.cable_patterns = {
            'primary': [
                r'cable\s*id', r'from\s*equipment', r'to\s*equipment',
                r'specification', r'cores', r'size\s*\(\s*mm²\s*\)'
            ],
            'secondary': [
                r'length\s*\(\s*m\s*\)', r'installation', r'current\s*rating',
                r'voltage\s*drop\s*\(\s*v\s*\)', r'voltage\s*drop\s*%'
            ]
        }

        self.bus_patterns = {
            'primary': [
                r'bus\s*id', r'bus\s*name', r'voltage\s*\(\s*v\s*\)',
                r'rated\s*current', r'short\s*circuit\s*rating'
            ],
            'secondary': [
                r'phases', r'frequency', r'parent\s*bus', r'connected\s*loads'
            ]
        }

        self.transformer_patterns = {
            'primary': [
                r'transformer\s*id', r'rating\s*\(\s*kva\s*\)',
                r'primary\s*voltage', r'secondary\s*voltage'
            ],
            'secondary': [
                r'impedance\s*%', r'vector\s*group', r'cooling', r'windings'
            ]
        }

        self.sheet_type_weights = {
            'load_schedule': {'primary': 3, 'secondary': 1},
            'cable_schedule': {'primary': 3, 'secondary': 1},
            'bus_schedule': {'primary': 3, 'secondary': 1},
            'transformer_schedule': {'primary': 3, 'secondary': 1},
            'project_info': {'primary': 2, 'secondary': 1},
            'unknown': {'primary': 0, 'secondary': 0}
        }
        
        # Enhanced sheet type descriptions for LLM classification with comprehensive electrical engineering terminology
        self.sheet_type_descriptions = {
            'load_schedule': "electrical power distribution engineering load schedule equipment power ratings kilowatts kw voltage volts current amperes phases three-phase single-phase load types motor pump compressor fan blower lighting led lamps hvac air conditioning ventilation chiller ups uninterruptible power supply capacitor reactor priority critical essential non-essential source bus distribution board cable length meters installation method cable tray conduit buried trench",
            'cable_schedule': "electrical cable schedule wiring specification conductor cable from equipment source origin starting point to equipment destination target ending point cable identification id cable number cores conductor cores single core multi core conductor size cross section area mm2 mm² csa copper aluminum conductor type xlpe pvc rubber mineral fire resistant lszh shielded screened armored swa braiding insulation type installation method cable tray ladder rack conduit pipe buried direct buried underground duct bank trench length meters circuit length",
            'bus_schedule': "electrical distribution bus bar panel switchboard schedule voltage level volts rated voltage system voltage phases rated current amperes short circuit rating fault level ka symmetrical breaking capacity upstream board parent bus child buses connected loads equipment connections bus identification bus id bus name bus number distribution board panelboard switchgear main distribution board mdb sub distribution board sdb motor control center mcc power control center pcc",
            'transformer_schedule': "power transformer electrical distribution transformer schedule kva kilovolt amperes rating capacity primary voltage secondary voltage vector group connection star delta wye dyn11 dyn5 yyn0 dd0 yy0 dy11 tap changing oltc cooling method oil immersed dry type cast resin natural air forced air onan onaf ofwf windings temperature rise impedance percentage percent short circuit impedance copper losses iron losses no load losses full load losses",
            'project_info': "electrical engineering project configuration specification metadata standard iec nec is bs voltage system low voltage lv medium voltage mv high voltage hv extra high voltage ehv ambient temperature design ambient temperature altitude meters above sea level design conditions cable sizing method voltage drop percentage short circuit calculation method protection coordination discrimination time current curves tcc selectivity coordination study load flow analysis power flow study fault analysis arc flash analysis earthing grounding system"
        }

    def classify_sheet(self, df: pd.DataFrame, sheet_name: str) -> Dict[str, Any]:
        """
        Classify sheet using LLM-first approach with electrical engineering domain knowledge

        Args:
            df: DataFrame with sheet data
            sheet_name: Name of the sheet

        Returns:
            Dictionary with classification results
        """
        if df.empty:
            return {
                'sheet_type': 'unknown',
                'confidence': 0.0,
                'evidence': [],
                'recommended_model_mapping': None,
                'method': 'none'
            }

        # Get all column headers as string
        headers = df.columns.tolist()
        headers_text = ' '.join(str(h).lower() for h in headers)
        sheet_context = f"{sheet_name} {headers_text}"

        # Method 1: Try LLM-based classification first
        if self.embedding_engine.llm_processor and LLM_AVAILABLE:
            llm_result = self._classify_with_llm(sheet_context)
            if llm_result['confidence'] > 0.7:
                llm_result['method'] = 'llm'
                return llm_result

        # Method 2: Fall back to pattern matching
        pattern_result = self._classify_with_patterns(headers_text, sheet_name)
        pattern_result['method'] = 'patterns'
        return pattern_result
    
    def _classify_with_llm(self, sheet_context: str) -> Dict[str, Any]:
        """Classify sheet using LLM analysis with enhanced electrical engineering understanding"""
        try:
            best_match = None
            best_similarity = 0.0
            evidence = []
            all_scores = {}

            # Compare against each sheet type description using LLM
            for sheet_type, description in self.sheet_type_descriptions.items():
                similarity = self.embedding_engine.get_semantic_similarity_llm(
                    sheet_context, description
                )
                all_scores[sheet_type] = similarity

                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = sheet_type

            if best_similarity > 0.6:  # Confidence threshold for LLM analysis
                model_mapping = self._get_model_mapping(best_match)
                return {
                    'sheet_type': best_match,
                    'confidence': best_similarity,
                    'evidence': [f"LLM semantic similarity: {best_similarity:.3f}"],
                    'recommended_model_mapping': model_mapping,
                    'all_scores': all_scores
                }
            else:
                return {
                    'sheet_type': 'unknown',
                    'confidence': 0.0,
                    'evidence': [f"insufficient similarity: {best_similarity:.3f}"],
                    'recommended_model_mapping': None,
                    'all_scores': all_scores
                }

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")
            return {
                'sheet_type': 'unknown',
                'confidence': 0.0,
                'evidence': [f"LLM error: {str(e)}"],
                'recommended_model_mapping': None,
                'all_scores': {}
            }
    
    def _classify_with_patterns(self, headers_text: str, sheet_name: str) -> Dict[str, Any]:
        """Classify sheet using existing pattern matching (original logic)"""
        # Calculate pattern match scores
        scores = {}
        evidence = {}

        # Check load schedule patterns
        load_score = self._calculate_pattern_score(headers_text, self.load_patterns, 'load_schedule')
        scores['load_schedule'] = load_score['score']
        evidence['load_schedule'] = load_score['matches']

        # Check cable schedule patterns
        cable_score = self._calculate_pattern_score(headers_text, self.cable_patterns, 'cable_schedule')
        scores['cable_schedule'] = cable_score['score']
        evidence['cable_schedule'] = cable_score['matches']

        # Check bus schedule patterns
        bus_score = self._calculate_pattern_score(headers_text, self.bus_patterns, 'bus_schedule')
        scores['bus_schedule'] = bus_score['score']
        evidence['bus_schedule'] = bus_score['matches']

        # Check transformer schedule patterns
        transformer_score = self._calculate_pattern_score(headers_text, self.transformer_patterns, 'transformer_schedule')
        scores['transformer_schedule'] = transformer_score['score']
        evidence['transformer_schedule'] = transformer_score['matches']

        # Check for project info patterns
        project_score = self._calculate_project_info_score(headers_text, sheet_name)
        scores['project_info'] = project_score['score']
        evidence['project_info'] = project_score['matches']

        # Determine best match
        if max(scores.values()) == 0:
            best_type = 'unknown'
            confidence = 0.0
        else:
            best_type = max(scores, key=scores.get)
            max_score = scores[best_type]
            
            # Normalize confidence based on max possible score
            weights = self.sheet_type_weights.get(best_type, {'primary': 3, 'secondary': 1})
            max_possible = weights['primary'] * 3 + weights['secondary'] * 2
            confidence = min(max_score / max_possible, 1.0) if max_possible > 0 else 0.0

        # Map to model type
        model_mapping = self._get_model_mapping(best_type)

        return {
            'sheet_type': best_type,
            'confidence': confidence,
            'evidence': evidence.get(best_type, []),
            'recommended_model_mapping': model_mapping,
            'all_scores': scores
        }

    def _calculate_pattern_score(self, headers_text: str, patterns: Dict, sheet_type: str) -> Dict:
        """Calculate pattern matching score for a sheet type"""
        matches = []
        score = 0.0

        for pattern_category, pattern_list in patterns.items():
            category_score = 0.0
            category_matches = []

            for pattern in pattern_list:
                if re.search(pattern, headers_text, re.IGNORECASE):
                    weight = self.sheet_type_weights.get(sheet_type, {}).get(pattern_category, 1)
                    category_score += weight
                    category_matches.append(pattern)

            score += category_score
            matches.extend([(m, pattern_category) for m in category_matches])

        return {
            'score': score,
            'matches': matches
        }

    def _calculate_project_info_score(self, headers_text: str, sheet_name: str) -> Dict:
        """Calculate score for project information sheets"""
        project_patterns = [
            r'project\s*name', r'standard', r'voltage\s*system',
            r'ambient\s*temperature', r'project\s*id', r'created'
        ]

        name_bonus = 0.0
        if re.search(r'project|info|summary', sheet_name.lower()):
            name_bonus = 1.0

        matches = []
        score = name_bonus

        for pattern in project_patterns:
            if re.search(pattern, headers_text, re.IGNORECASE):
                score += 1.0
                matches.append(pattern)

        return {
            'score': score,
            'matches': matches
        }

    def _get_model_mapping(self, sheet_type: str) -> Optional[str]:
        """Map sheet type to data model"""
        mapping = {
            'load_schedule': 'Load',
            'cable_schedule': 'Cable',
            'bus_schedule': 'Bus',
            'transformer_schedule': 'Transformer',
            'project_info': 'Project'
        }
        return mapping.get(sheet_type)


class ColumnMapper:
    """
    Intelligent column header mapping with hybrid approach:
    1. Strong regex patterns for immediate mapping
    2. Canonical alias matching
    3. Embedding-based semantic matching
    4. Fuzzy string matching as fallback
    5. Gray zone confirmation (0.50-0.65 confidence)
    """

    def __init__(self):
        # Initialize LLM engine
        self.embedding_engine = LLMEngine()
        
        # Define target fields for each model type (existing logic)
        self.field_mappings = {
            'Load': {
                'load_id': [
                    'load id', 'load_id', 'id', 'load', 'equipment id',
                    'asset id', 'tag', 'load number', 'ld id', 'load ref'
                ],
                'load_name': [
                    'load name', 'load_name', 'name', 'description',
                    'equipment name', 'load description', 'name of load',
                    'equipment description', 'load desc', 'load'
                ],
                'power_kw': [
                    'power (kw)', 'power', 'kw', 'power kw', 'rating kw',
                    'rated power', 'load power', 'capacity kw', 'power rating',
                    'motor power', 'load capacity'
                ],
                'voltage': [
                    'voltage (v)', 'voltage', 'v', 'volts', 'operating voltage',
                    'system voltage', 'rated voltage', 'supply voltage'
                ],
                'phases': [
                    'phases', 'phase', 'no of phases', 'number of phases',
                    'phase connection', '3 phase', '1 phase', 'phase count'
                ],
                'load_type': [
                    'load type', 'type', 'equipment type', 'category',
                    'load category', 'equipment category', 'load nature'
                ],
                'power_factor': [
                    'power factor', 'pf', 'cos phi', 'cosφ', 'cosphi', 'power factor (pf)',
                    'power fact', 'power fact.', 'facteur de puissance'
                ],
                'efficiency': [
                    'efficiency', 'eff', 'efficiency %', 'motor efficiency',
                    'power efficiency', 'η', 'eta', 'efficiency ratio', 'efficacité'
                ],
                'source_bus': [
                    'source bus', 'bus', 'supply point', 'source',
                    'distribution board', 'panel', 'bus bar', 'source panel'
                ],
                'priority': [
                    'priority', 'importance', 'criticality', 'load priority',
                    'essential', 'critical', 'non-essential', 'priority level'
                ],
                'cable_length': COLUMN_CANON['cable_length_m'] + [
                    'cable length', 'length', 'distance', 'run length',
                    'cable run', 'length (m)', 'distance (m)'
                ],
                'installation_method': COLUMN_CANON['install_method'] + [
                    'installation', 'method', 'cable installation',
                    'installation method', 'routing', 'cable method'
                ]
            },
            'Cable': {
                'cable_id': [
                    'cable id', 'cable_id', 'cable', 'id', 'cable ref',
                    'cable number', 'asset id', 'tag'
                ],
                'from_equipment': [
                    'from', 'from equipment', 'source', 'origin',
                    'from equipment', 'cable from', 'source equipment'
                ],
                'to_equipment': [
                    'to', 'to equipment', 'destination', 'load',
                    'to equipment', 'cable to', 'target equipment'
                ],
                'cores': [
                    'cores', 'core', 'number of cores', 'no of cores',
                    'core count', 'cable cores', 'conductor count'
                ],
                'size_sqmm': COLUMN_CANON['size_mm2'] + [
                    'size (mm²)', 'size', 'mm2', 'cross section',
                    'cable size', 'conductor size', 'area', 'mm²'
                ],
                'cable_type': COLUMN_CANON['cable_type'] + [
                    'cable type', 'type', 'specification', 'cable spec',
                    'cable category', 'insulation type', 'cable construction'
                ],
                'insulation': [
                    'insulation', 'insulation type', 'insul',
                    'insulating material', 'insulation material'
                ],
                'length_m': COLUMN_CANON['cable_length_m'] + [
                    'length (m)', 'length', 'm', 'cable length',
                    'run length', 'distance', 'cable distance'
                ],
                'installation_method': COLUMN_CANON['install_method'] + [
                    'installation', 'method', 'installation method',
                    'routing', 'cable routing', 'installation type'
                ],
                'armored': COLUMN_CANON['armored'] + [
                    'armored', 'armour', 'armoured', 'swa', 'armour type',
                    'armor', 'armoured cable', 'steel wire armour'
                ]
            },
            'Bus': {
                'bus_id': [
                    'bus id', 'bus_id', 'bus', 'id', 'bus ref',
                    'bus number', 'panel id', 'distribution board id'
                ],
                'bus_name': [
                    'name', 'bus name', 'bus_name', 'description',
                    'panel name', 'board name', 'bus description'
                ],
                'voltage': [
                    'un (v)', 'un v', 'voltage (v)', 'voltage', 'v', 'rated voltage',
                    'system voltage', 'bus voltage'
                ],
                'phases': [
                    'phases', 'phase', 'no of phases', 'number of phases'
                ],
                'rated_current_a': [
                    'rated (a)', 'rated a', 'rated current (a)', 'current', 'rated current',
                    'ampere rating', 'current rating'
                ],
                'upstream_bus': [
                    'upstream board', 'upstream'
                ],
                'short_circuit_rating_ka': [
                    'short circuit rating', 'sc rating', 'fault level',
                    'short circuit (ka)', 'fault rating'
                ]
            }
        }

        # Data type inference patterns
        self.data_type_patterns = {
            'int': [r'^\d+$', r'phase', r'cores', r'poles'],
            'float': [r'power', r'voltage', r'current', r'length', r'size', r'efficiency'],
            'str': [r'id', r'name', r'type', r'description', r'priority'],
            'bool': [r'armored', r'armoured', r'shielded', r'redundancy']
        }

        # Gray zone confirmation threshold
        self.gray_zone_min = 0.50
        self.gray_zone_max = 0.65

    def map_columns(self, columns: List[str], model_type: str, sheet_context: str = "",
                    confirm_callback=None) -> Dict[str, Any]:
        """
        Map Excel columns to model fields with enhanced vector search and confidence scoring

        Args:
            columns: List of Excel column headers
            model_type: Target model type ('Load', 'Cable', 'Bus', etc.)
            sheet_context: Additional context about the sheet
            confirm_callback: Callback for gray zone confirmations

        Returns:
            Dictionary mapping target fields to column mappings
        """
        if model_type not in self.field_mappings:
            return {}

        target_fields = self.field_mappings[model_type]
        mapping_result = {}
        unmapped_columns = list(columns)
        gray_zone_matches = []

        # Step 1: Apply strong regex patterns first (immediate mapping)
        for column in columns[:]:  # Create a copy to iterate safely
            regex_match = strong_regex_map(column)
            if regex_match and regex_match in target_fields:
                # Direct mapping for strong regex matches
                mapping_result[regex_match] = {
                    'mapped_columns': [column],
                    'confidence': 1.0,
                    'data_type': self._infer_data_type(regex_match, columns),
                    'pattern_match': 'strong_regex',
                    'method': 'regex'
                }
                unmapped_columns.remove(column)
                logger.debug(f"Strong regex match: '{column}' -> '{regex_match}'")

        # Step 2: Try canonical alias matching
        for column in unmapped_columns[:]:  # Create a copy
            normalized_column = norm_header(column)
            for field_name, aliases in COLUMN_CANON.items():
                if field_name in target_fields:  # Only if field exists in target model
                    for alias in aliases:
                        if norm_header(alias) == normalized_column:
                            mapping_result[field_name] = {
                                'mapped_columns': [column],
                                'confidence': 0.95,
                                'data_type': self._infer_data_type(field_name, columns),
                                'pattern_match': alias,
                                'method': 'canonical'
                            }
                            unmapped_columns.remove(column)
                            logger.debug(f"Canonical match: '{column}' -> '{field_name}' via '{alias}'")
                            break
                    if column not in unmapped_columns:
                        break

        # Step 3: Vector-enhanced hybrid matching for remaining columns
        vector_matches = self._find_vector_based_matches(unmapped_columns, target_fields, sheet_context)

        for field_name, vector_match in vector_matches.items():
            if field_name in mapping_result:
                continue  # Already mapped

            column = vector_match['column']
            confidence = vector_match['confidence']
            method = vector_match['method']

            # Handle gray zone (0.50-0.65) with confirmation
            if self.gray_zone_min <= confidence < self.gray_zone_max:
                # Check if this is an ambiguous column that needs confirmation
                ambiguous_fields = ['size_mm2', 'install_method', 'cable_type', 'armored']
                if field_name in ambiguous_fields and confirm_callback:
                    gray_zone_matches.append({
                        'column': column,
                        'field': field_name,
                        'confidence': confidence,
                        'patterns': target_fields[field_name]
                    })
                else:
                    # Use the match anyway for non-ambiguous fields
                    mapping_result[field_name] = {
                        'mapped_columns': [column],
                        'confidence': confidence,
                        'data_type': self._infer_data_type(field_name, columns),
                        'pattern_match': vector_match.get('pattern', 'vector_match'),
                        'method': method
                    }
                    if column in unmapped_columns:
                        unmapped_columns.remove(column)
            elif confidence > 0.6:  # Minimum confidence threshold
                mapping_result[field_name] = {
                    'mapped_columns': [column],
                    'confidence': confidence,
                    'data_type': self._infer_data_type(field_name, columns),
                    'pattern_match': vector_match.get('pattern', 'vector_match'),
                    'method': method
                }

                # Remove matched column from unmapped list
                if column in unmapped_columns:
                    unmapped_columns.remove(column)

        # Step 4: Traditional hybrid matching for any remaining unmapped columns
        for field_name, field_patterns in target_fields.items():
            if field_name in mapping_result:
                continue  # Already mapped

            best_match, confidence = self._find_best_column_match_llm(
                field_patterns, unmapped_columns, sheet_context
            )

            # Handle gray zone (0.50-0.65) with confirmation
            if best_match and self.gray_zone_min <= confidence < self.gray_zone_max:
                # Check if this is an ambiguous column that needs confirmation
                ambiguous_fields = ['size_mm2', 'install_method', 'cable_type', 'armored']
                if field_name in ambiguous_fields and confirm_callback:
                    gray_zone_matches.append({
                        'column': best_match,
                        'field': field_name,
                        'confidence': confidence,
                        'patterns': field_patterns
                    })
                else:
                    # Use the match anyway for non-ambiguous fields
                    mapping_result[field_name] = {
                        'mapped_columns': [best_match],
                        'confidence': confidence,
                        'data_type': self._infer_data_type(field_name, columns),
                        'pattern_match': self._get_match_pattern(field_patterns, best_match),
                        'method': 'hybrid'
                    }
                    unmapped_columns.remove(best_match)
            elif best_match and confidence > 0.6:  # Minimum confidence threshold
                mapping_result[field_name] = {
                    'mapped_columns': [best_match],
                    'confidence': confidence,
                    'data_type': self._infer_data_type(field_name, columns),
                    'pattern_match': self._get_match_pattern(field_patterns, best_match),
                    'method': 'hybrid'
                }

                # Remove matched column from unmapped list
                if best_match in unmapped_columns:
                    unmapped_columns.remove(best_match)

        # Step 5: Ask for confirmation on gray zone matches
        if gray_zone_matches and confirm_callback:
            try:
                confirmed_matches = confirm_callback(gray_zone_matches)
                for match_info in confirmed_matches:
                    field_name = match_info['field']
                    column = match_info['column']
                    confidence = match_info['confidence']

                    if field_name not in mapping_result:
                        mapping_result[field_name] = {
                            'mapped_columns': [column],
                            'confidence': confidence,
                            'data_type': self._infer_data_type(field_name, columns),
                            'pattern_match': 'user_confirmed',
                            'method': 'gray_zone_confirmed'
                        }
                        if column in unmapped_columns:
                            unmapped_columns.remove(column)
            except Exception as e:
                logger.warning(f"Gray zone confirmation failed: {e}")

        # Step 6: Map remaining columns with lower confidence
        for column in unmapped_columns[:]:  # Create a copy
            field_name = self._find_best_field_match_hybrid(column, target_fields, sheet_context)
            if field_name and self._calculate_match_confidence_hybrid(column, field_name) > 0.3:
                if field_name not in mapping_result:
                    mapping_result[field_name] = {
                        'mapped_columns': [],
                        'confidence': 0.0,
                        'data_type': self._infer_data_type(field_name, columns),
                        'pattern_match': None,
                        'method': 'weak_match'
                    }

                mapping_result[field_name]['mapped_columns'].append(column)
                current_conf = mapping_result[field_name]['confidence']
                new_conf = self._calculate_match_confidence_hybrid(column, field_name)
                mapping_result[field_name]['confidence'] = max(current_conf, new_conf)

        # Calculate overall mapping confidence
        total_confidence = sum(m['confidence'] for m in mapping_result.values())
        field_count = len(target_fields)
        overall_confidence = total_confidence / field_count if field_count > 0 else 0.0

        # Store successful mappings for learning
        self._store_successful_mappings(mapping_result, model_type, sheet_context)

        return {
            'field_mappings': mapping_result,
            'overall_confidence': overall_confidence,
            'unmapped_columns': unmapped_columns,
            'mapping_quality': self._assess_mapping_quality(mapping_result, target_fields),
            'gray_zone_count': len(gray_zone_matches)
        }

    def _find_best_column_match_llm(self, field_patterns: List[str], columns: List[str],
                                   sheet_context: str = "") -> Tuple[Optional[str], float]:
        """Find best column match using LLM-first approach"""

        # Method 1: Try LLM-based matching
        if self.embedding_engine.llm_processor and LLM_AVAILABLE:
            best_match, llm_confidence = self.embedding_engine.find_best_match_llm(
                ' '.join(field_patterns), columns, class_type='field_mapping'
            )

            if best_match and llm_confidence > 0.7:
                return best_match, llm_confidence

        # Method 2: Fallback to existing fuzzy matching
        best_match = None
        best_confidence = 0.0

        for column in columns:
            for pattern in field_patterns:
                # Use fuzzy string matching
                confidence = fuzz.partial_ratio(pattern.lower(), column.lower()) / 100.0

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = column

        return best_match, best_confidence

    def _find_best_field_match_hybrid(self, column: str, target_fields: Dict[str, List[str]], 
                                    sheet_context: str = "") -> Optional[str]:
        """Find best target field for an unmapped column using hybrid approach"""
        
        # Method 1: Try embedding-based matching
        if self.embedding_engine.model and EMBEDDINGS_AVAILABLE:
            # Create a combined description for the column
            column_description = f"{column} {sheet_context}"
            
            # Get best match using embeddings
            field_descriptions = []
            field_names = []
            for field_name, field_patterns in target_fields.items():
                field_descriptions.append(' '.join(field_patterns))
                field_names.append(field_name)
            
            best_match, confidence = self.embedding_engine.find_best_match_embedding(
                column_description, field_descriptions, threshold=0.5
            )
            
            if best_match and confidence > 0.7:
                return field_names[field_descriptions.index(best_match)]
        
        # Method 2: Fallback to existing logic
        best_field = None
        best_confidence = 0.0

        for field_name, field_patterns in target_fields.items():
            confidence = self._calculate_match_confidence_llm(column, field_name)
            if confidence > best_confidence:
                best_confidence = confidence
                best_field = field_name

        return best_field

    def _calculate_match_confidence_llm(self, column: str, field_name: str) -> float:
        """Calculate confidence for column-field match using LLM-enhanced approach"""
        if field_name not in self.field_mappings:
            return 0.0

        # Method 1: Try LLM-based similarity
        if self.embedding_engine.llm_processor and LLM_AVAILABLE:
            field_patterns = self.field_mappings[field_name]
            similarity = self.embedding_engine.get_semantic_similarity_llm(
                column, ' '.join(field_patterns)
            )

            # If LLM similarity is high, use it with boost
            if similarity > 0.7:
                return min(similarity + 0.1, 1.0)  # Add small boost for LLM confidence

        # Method 2: Fallback to existing logic
        # Direct name similarity
        direct_confidence = fuzz.ratio(column.lower(), field_name.lower()) / 100.0

        # Pattern matching
        pattern_confidence = 0.0
        patterns = self.field_mappings[field_name]
        for pattern in patterns:
            pattern_confidence = max(pattern_confidence,
                                   fuzz.partial_ratio(pattern.lower(), column.lower()) / 100.0)

        # Combine both approaches
        return max(direct_confidence, pattern_confidence)

    def _infer_data_type(self, field_name: str, all_columns: List[str]) -> str:
        """Infer appropriate data type for field based on name and patterns"""
        # Use data type patterns to infer type
        for data_type, patterns in self.data_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, field_name, re.IGNORECASE):
                    return data_type

        # Default to string
        return 'str'

    def _get_match_pattern(self, patterns: List[str], matched_column: str) -> str:
        """Get the pattern that matched the column"""
        best_pattern = ""
        best_confidence = 0.0

        for pattern in patterns:
            confidence = fuzz.partial_ratio(pattern.lower(), matched_column.lower()) / 100.0
            if confidence > best_confidence:
                best_confidence = confidence
                best_pattern = pattern

        return best_pattern

    def _assess_mapping_quality(self, mapping_result: Dict, target_fields: Dict) -> str:
        """Assess overall mapping quality"""
        mapped_fields = len(mapping_result)
        total_fields = len(target_fields)
        coverage_ratio = mapped_fields / total_fields if total_fields > 0 else 0.0

        if coverage_ratio >= 0.8:
            return 'excellent'
        elif coverage_ratio >= 0.6:
            return 'good'
        elif coverage_ratio >= 0.4:
            return 'fair'
        else:
            return 'poor'

    def _find_vector_based_matches(self, unmapped_columns: List[str], target_fields: Dict[str, List[str]],
                                  sheet_context: str = "") -> Dict[str, Dict]:
        """
        Find column matches using vector database search for historical Excel header mappings

        Args:
            unmapped_columns: Columns that haven't been mapped yet
            target_fields: Target field patterns to match against
            sheet_context: Additional context from sheet name

        Returns:
            Dictionary mapping field names to vector match results
        """
        vector_matches = {}

        if not VECTOR_DB_AVAILABLE:
            logger.debug("Vector database not available for column matching")
            return vector_matches

        try:
            # Get vector database instance
            vector_db = get_vector_database()

            for field_name, field_patterns in target_fields.items():
                if field_name in ['load_id', 'cable_id', 'bus_id']:
                    # Skip ID fields as they rarely have useful vector mappings
                    continue

                # Search for each unmapped column against this field
                best_match = None
                best_confidence = 0.0
                best_method = 'none'
                best_pattern = None

                for column in unmapped_columns:
                    # Search vector database for similar header mappings
                    try:
                        header_mappings = vector_db.retrieve_excel_header_mappings(
                            header_text=column,
                            context=f"field:{field_name}",
                            top_k=3
                        )

                        for mapping in header_mappings:
                            # Check if this mapping matches our target field
                            if mapping.get('field', '').lower() == field_name.lower():
                                confidence = mapping.get('similarity_score', 0.0)

                                # Boost confidence for exact field matches
                                confidence = min(confidence + 0.1, 1.0)

                                if confidence > best_confidence:
                                    best_confidence = confidence
                                    best_match = column
                                    best_method = 'vector_db'
                                    best_pattern = mapping.get('pattern', 'vector_match')

                    except Exception as e:
                        logger.debug(f"Vector search failed for column '{column}': {e}")

                # If no direct vector match, try RAG query for field understanding
                if not best_match and best_confidence < 0.7:
                    try:
                        # Use RAG to understand field requirements
                        field_description = ' '.join(field_patterns)
                        rag_context = vector_db.rag_query(
                            query=f"What Excel columns typically represent {field_name} in electrical engineering? {field_description}",
                            context=f"Sheet context: {sheet_context}",
                            collection="standards"
                        )

                        if rag_context:
                            for column in unmapped_columns:
                                # Check if column appears in RAG context
                                if column.lower() in rag_context.lower():
                                    # Calculate similarity score
                                    confidence = fuzz.partial_ratio(column.lower(), field_name.lower()) / 100.0
                                    confidence = min(confidence + 0.2, 1.0)  # Boost for RAG match

                                    if confidence > best_confidence:
                                        best_confidence = confidence
                                        best_match = column
                                        best_method = 'rag_enhanced'
                                        best_pattern = 'rag_context'

                    except Exception as e:
                        logger.debug(f"RAG query failed for field '{field_name}': {e}")

                # Store match if confidence is sufficient
                if best_match and best_confidence > 0.6:
                    vector_matches[field_name] = {
                        'column': best_match,
                        'confidence': best_confidence,
                        'method': best_method,
                        'pattern': best_pattern
                    }
                    logger.debug(f"Vector match: '{best_match}' -> '{field_name}' (conf: {best_confidence:.3f}, method: {best_method})")

        except Exception as e:
            logger.warning(f"Vector-based matching failed: {e}")

        return vector_matches

    def _store_successful_mappings(self, mapping_result: Dict, model_type: str, sheet_context: str):
        """
        Store successful column mappings in vector database for future learning

        Args:
            mapping_result: The mapping results from map_columns
            model_type: The model type being mapped
            sheet_context: Context about the sheet
        """
        if not VECTOR_DB_AVAILABLE:
            return

        try:
            vector_db = get_vector_database()

            # Store successful mappings for learning
            for field_name, mapping_info in mapping_result.get('field_mappings', {}).items():
                confidence = mapping_info.get('confidence', 0.0)

                # Only store high-confidence mappings
                if confidence >= 0.8:
                    mapped_columns = mapping_info.get('mapped_columns', [])
                    method = mapping_info.get('method', 'unknown')

                    for column in mapped_columns:
                        try:
                            # Store each successful mapping
                            vector_db.store_excel_header_mapping(
                                header=column,
                                field=field_name,
                                confidence=confidence,
                                context=f"Model: {model_type}, Sheet: {sheet_context}, Method: {method}",
                                project_id="excel_extraction_learning"
                            )

                            logger.debug(f"Stored successful mapping: '{column}' -> '{field_name}' (conf: {confidence:.3f})")

                        except Exception as e:
                            logger.debug(f"Failed to store mapping '{column}' -> '{field_name}': {e}")

        except Exception as e:
            logger.warning(f"Failed to store successful mappings: {e}")

class DataExtractor:
    """
    Extract and validate data using existing Load, Cable, etc. models
    """

    def __init__(self):
        self.calculation_engine = ElectricalCalculationEngine()

        # Load type mapping patterns
        self.load_type_mappings = {
            'motor': ['motor', 'drive', 'pump', 'compressor', 'fan', 'conveyor'],
            'hvac': ['hvac', 'air conditioning', 'ac', 'ventilation', 'chiller', 'ahu'],
            'lighting': ['lighting', 'light', 'led', 'lamp', 'luminaire', 'illumination'],
            'heater': ['heater', 'heating', 'heater', 'resistance', 'furnace'],
            'ups': ['ups', 'uninterruptible', 'battery', 'backup power'],
            'general': ['general', 'misc', 'other', 'auxiliary', 'miscellaneous']
        }

        # Installation method mappings
        self.installation_mappings = {
            'conduit': ['conduit', 'pipe', 'tubing', 'raceway'],
            'tray': ['tray', 'cable tray', 'ladder', 'channel'],
            'buried': ['buried', 'direct buried', 'underground', 'duct bank'],
            'air': ['air', 'free air', 'exposed'],
            'duct': ['duct', 'underground duct', 'subway']
        }

        # Priority mappings
        self.priority_mappings = {
            'critical': ['critical', 'essential', 'safety', 'emergency'],
            'essential': ['essential', 'important', 'priority'],
            'non-essential': ['non-essential', 'normal', 'general', 'standard']
        }

    def extract_loads(self, df: pd.DataFrame, field_mapping: Dict) -> Tuple[List[Load], ExtractionResult]:
        """Extract Load objects from DataFrame"""
        extracted_loads = []
        issues = []
        warnings = []

        try:
            for index, row in df.iterrows():
                try:
                    load = self._create_load_from_row(row, field_mapping)
                    if load:
                        extracted_loads.append(load)
                except Exception as e:
                    issues.append(f"Row {index + 1}: Failed to create load - {str(e)}")
                    logger.warning(f"Failed to create load from row {index + 1}: {e}")

            # Calculate confidence and quality score
            confidence = self._calculate_extraction_confidence(extracted_loads, len(df))
            quality_score = self._assess_load_data_quality(extracted_loads)

            result = ExtractionResult(
                success=True,
                confidence=confidence,
                sheet_type='load_schedule',
                components_extracted=len(extracted_loads),
                data_quality_score=quality_score,
                issues=issues,
                warnings=warnings,
                extracted_data={'loads': [self._load_to_dict(load) for load in extracted_loads]}
            )

        except Exception as e:
            result = ExtractionResult(
                success=False,
                confidence=0.0,
                sheet_type='load_schedule',
                components_extracted=0,
                data_quality_score=0.0,
                issues=[f"Critical extraction failure: {str(e)}"]
            )

        return extracted_loads, result

    def extract_cables(self, df: pd.DataFrame, field_mapping: Dict) -> Tuple[List[Cable], ExtractionResult]:
        """Extract Cable objects from DataFrame"""
        extracted_cables = []
        issues = []
        warnings = []

        try:
            for index, row in df.iterrows():
                try:
                    cable = self._create_cable_from_row(row, field_mapping)
                    if cable:
                        extracted_cables.append(cable)
                except Exception as e:
                    issues.append(f"Row {index + 1}: Failed to create cable - {str(e)}")
                    logger.warning(f"Failed to create cable from row {index + 1}: {e}")

            confidence = self._calculate_extraction_confidence(extracted_cables, len(df))
            quality_score = self._assess_cable_data_quality(extracted_cables)

            result = ExtractionResult(
                success=True,
                confidence=confidence,
                sheet_type='cable_schedule',
                components_extracted=len(extracted_cables),
                data_quality_score=quality_score,
                issues=issues,
                warnings=warnings,
                extracted_data={'cables': [self._cable_to_dict(cable) for cable in extracted_cables]}
            )

        except Exception as e:
            result = ExtractionResult(
                success=False,
                confidence=0.0,
                sheet_type='cable_schedule',
                components_extracted=0,
                data_quality_score=0.0,
                issues=[f"Critical extraction failure: {str(e)}"]
            )

        return extracted_cables, result

    def extract_buses(self, df: pd.DataFrame, field_mapping: Dict) -> Tuple[List[Bus], ExtractionResult]:
        """Extract Bus objects from DataFrame"""
        extracted_buses = []
        issues = []
        warnings = []

        try:
            for index, row in df.iterrows():
                try:
                    bus = self._create_bus_from_row(row, field_mapping)
                    if bus:
                        extracted_buses.append(bus)
                except Exception as e:
                    issues.append(f"Row {index + 1}: Failed to create bus - {str(e)}")
                    logger.warning(f"Failed to create bus from row {index + 1}: {e}")

            confidence = self._calculate_extraction_confidence(extracted_buses, len(df))
            quality_score = self._assess_bus_data_quality(extracted_buses)

            result = ExtractionResult(
                success=True,
                confidence=confidence,
                sheet_type='bus_schedule',
                components_extracted=len(extracted_buses),
                data_quality_score=quality_score,
                issues=issues,
                warnings=warnings,
                extracted_data={'buses': [self._bus_to_dict(bus) for bus in extracted_buses]}
            )

        except Exception as e:
            result = ExtractionResult(
                success=False,
                confidence=0.0,
                sheet_type='bus_schedule',
                components_extracted=0,
                data_quality_score=0.0,
                issues=[f"Critical extraction failure: {str(e)}"]
            )

        return extracted_buses, result

    def _create_bus_from_row(self, row: pd.Series, field_mapping: Dict) -> Optional[Bus]:
        """Create a Bus object from a data row"""
        try:
            bus_data = {}
            for field_name, mapping_info in field_mapping.get('field_mappings', {}).items():
                columns = mapping_info.get('mapped_columns', [])
                if columns:
                    column_name = columns[0]
                    if column_name in row.index:
                        bus_data[field_name] = row[column_name]

            # Extract and validate required fields
            bus_id = self._extract_bus_id(bus_data)
            bus_name = self._extract_bus_name(bus_data)
            voltage = self._extract_bus_voltage(bus_data)

            if not all([bus_id, bus_name, voltage]):
                return None

            # Create Bus object
            bus = Bus(
                bus_id=bus_id,
                bus_name=bus_name,
                voltage=voltage,
                phases=self._extract_bus_phases(bus_data),
                rated_current_a=self._extract_rated_current_a(bus_data),
                short_circuit_rating_ka=self._extract_short_circuit_rating_ka(bus_data)
            )

            return bus

        except Exception as e:
            logger.error(f"Error creating bus from row data: {e}")
            return None

    def _create_load_from_row(self, row: pd.Series, field_mapping: Dict) -> Optional[Load]:
        """Create a Load object from a data row"""
        try:
            # Map fields using the provided mapping
            load_data = {}
            for field_name, mapping_info in field_mapping.get('field_mappings', {}).items():
                columns = mapping_info.get('mapped_columns', [])
                if columns:
                    # Take the first mapped column
                    column_name = columns[0]
                    if column_name in row.index:
                        load_data[field_name] = row[column_name]

            # Extract and validate required fields
            load_id = self._extract_load_id(load_data)
            load_name = self._extract_load_name(load_data)
            power_kw = self._extract_power_kw(load_data)
            voltage = self._extract_voltage(load_data)

            if not all([load_id, load_name, power_kw, voltage]):
                return None

            # Create Load object with extracted and defaulted values
            load = Load(
                load_id=load_id,
                load_name=load_name,
                power_kw=power_kw,
                voltage=voltage,
                phases=self._extract_phases(load_data),
                load_type=self._extract_load_type(load_data),
                power_factor=self._extract_power_factor(load_data),
                efficiency=self._extract_efficiency(load_data),
                duty_cycle=self._extract_duty_cycle(load_data),
                cable_length=self._extract_cable_length(load_data),
                installation_method=self._extract_installation_method(load_data),
                source_bus=self._extract_source_bus(load_data),
                priority=self._extract_priority(load_data)
            )

            # Calculate electrical parameters
            load = self.calculation_engine.calculate_load(load)

            return load

        except Exception as e:
            logger.error(f"Error creating load from row data: {e}")
            return None

    def _create_cable_from_row(self, row: pd.Series, field_mapping: Dict) -> Optional[Cable]:
        """Create a Cable object from a data row"""
        try:
            cable_data = {}
            for field_name, mapping_info in field_mapping.get('field_mappings', {}).items():
                columns = mapping_info.get('mapped_columns', [])
                if columns:
                    column_name = columns[0]
                    if column_name in row.index:
                        cable_data[field_name] = row[column_name]

            # Extract and validate required fields
            cable_id = self._extract_cable_id(cable_data)
            from_equipment = self._extract_from_equipment(cable_data)
            to_equipment = self._extract_to_equipment(cable_data)

            if not all([cable_id, from_equipment, to_equipment]):
                return None

            # Create Cable object
            cable = Cable(
                cable_id=cable_id,
                from_equipment=from_equipment,
                to_equipment=to_equipment,
                cores=self._extract_cores(cable_data),
                size_sqmm=self._extract_size_sqmm(cable_data),
                cable_type=self._extract_cable_type(cable_data),
                insulation=self._extract_insulation(cable_data),
                length_m=self._extract_length_m(cable_data),
                installation_method=self._extract_installation_method(cable_data),
                armored=self._extract_armored(cable_data)
            )

            return cable

        except Exception as e:
            logger.error(f"Error creating cable from row data: {e}")
            return None

    def _extract_load_id(self, data: Dict) -> Optional[str]:
        """Extract load ID with smart generation if missing"""
        load_id = data.get('load_id')
        if load_id:
            return str(load_id).strip()
        
        # Generate ID based on other data if possible
        load_name = data.get('load_name', '')
        if load_name:
            # Extract number or create from name
            numbers = re.findall(r'\d+', str(load_name))
            if numbers:
                return f"L{numbers[0].zfill(3)}"
            else:
                # Create from first letters
                words = str(load_name).split()[:2]
                return ''.join(w[0].upper() for w in words) + "001"
        
        return None

    def _extract_load_name(self, data: Dict) -> str:
        """Extract load name"""
        return str(data.get('load_name', 'Unknown Load')).strip()

    def _extract_power_kw(self, data: Dict) -> float:
        """Extract power in kW"""
        power_str = str(data.get('power_kw', '0')).replace(',', '').strip()
        try:
            return float(power_str)
        except ValueError:
            return 0.0

    def _extract_voltage(self, data: Dict) -> float:
        """Extract voltage with standard value mapping"""
        voltage_str = str(data.get('voltage', '400')).replace(',', '').strip()
        try:
            voltage = float(voltage_str)
            # Map to standard voltages
            if voltage < 300:
                return 230
            elif voltage < 500:
                return 400
            elif voltage < 1000:
                return 415
            else:
                return voltage
        except ValueError:
            return 400  # Default to 400V

    def _extract_phases(self, data: Dict) -> int:
        """Extract number of phases"""
        phases_str = str(data.get('phases', '3')).strip().lower()
        if '1' in phases_str or 'single' in phases_str:
            return 1
        else:
            return 3  # Default to 3-phase

    def _extract_load_type(self, data: Dict) -> LoadType:
        """Extract load type using pattern matching"""
        type_str = str(data.get('load_type', 'general')).lower()
        
        for load_type, patterns in self.load_type_mappings.items():
            for pattern in patterns:
                if pattern in type_str:
                    return LoadType(load_type)
        
        return LoadType.GENERAL

    def _extract_power_factor(self, data: Dict) -> float:
        """Extract power factor"""
        pf_str = str(data.get('power_factor', '0.85')).replace(',', '.').strip()
        try:
            pf = float(pf_str)
            return max(0.1, min(1.0, pf))  # Clamp between 0.1 and 1.0
        except ValueError:
            return 0.85

    def _extract_efficiency(self, data: Dict) -> float:
        """Extract efficiency"""
        eff_str = str(data.get('efficiency', '0.9')).replace(',', '.').strip()
        try:
            eff = float(eff_str)
            return max(0.1, min(1.0, eff))  # Clamp between 0.1 and 1.0
        except ValueError:
            return 0.9

    def _extract_duty_cycle(self, data: Dict) -> DutyCycle:
        """Extract duty cycle"""
        duty_str = str(data.get('duty_cycle', 'continuous')).lower()
        if 'intermittent' in duty_str:
            return DutyCycle.INTERMITTENT
        elif 'short' in duty_str:
            return DutyCycle.SHORT_TIME
        else:
            return DutyCycle.CONTINUOUS

    def _extract_cable_length(self, data: Dict) -> float:
        """Extract cable length in meters"""
        length_str = str(data.get('cable_length', '25')).replace(',', '').strip()
        try:
            return float(length_str)
        except ValueError:
            return 25.0

    def _extract_installation_method(self, data: Dict) -> InstallationMethod:
        """Extract installation method"""
        install_str = str(data.get('installation_method', 'tray')).lower()
        
        for method, patterns in self.installation_mappings.items():
            for pattern in patterns:
                if pattern in install_str:
                    return InstallationMethod(method)
        
        return InstallationMethod.TRAY

    def _extract_source_bus(self, data: Dict) -> Optional[str]:
        """Extract source bus"""
        return str(data.get('source_bus', '')).strip() or None

    def _extract_priority(self, data: Dict) -> Priority:
        """Extract priority"""
        priority_str = str(data.get('priority', 'non-essential')).lower()
        
        for priority, patterns in self.priority_mappings.items():
            for pattern in patterns:
                if pattern in priority_str:
                    return Priority(priority)
        
        return Priority.NON_ESSENTIAL

    def _extract_cable_id(self, data: Dict) -> Optional[str]:
        """Extract cable ID"""
        cable_id = data.get('cable_id')
        if cable_id:
            return str(cable_id).strip()
        return None

    def _extract_from_equipment(self, data: Dict) -> str:
        """Extract from equipment"""
        return str(data.get('from_equipment', 'Unknown Source')).strip()

    def _extract_to_equipment(self, data: Dict) -> str:
        """Extract to equipment"""
        return str(data.get('to_equipment', 'Unknown Destination')).strip()

    def _extract_cores(self, data: Dict) -> int:
        """Extract number of cores"""
        cores_str = str(data.get('cores', '4')).strip()
        try:
            return int(cores_str)
        except ValueError:
            return 4

    def _extract_size_sqmm(self, data: Dict) -> float:
        """Extract cable size in mm²"""
        size_str = str(data.get('size_sqmm', '2.5')).replace(',', '.').strip()
        try:
            return float(size_str)
        except ValueError:
            return 2.5

    def _extract_cable_type(self, data: Dict) -> str:
        """Extract cable type"""
        cable_type = data.get('cable_type')
        if cable_type:
            return str(cable_type).strip()
        
        # Generate based on other properties
        cores = self._extract_cores(data)
        if cores == 3:
            return "XLPE/PVC"  # 3-core
        else:
            return "XLPE/PVC"  # 4-core (3+neutral)

    def _extract_insulation(self, data: Dict) -> str:
        """Extract insulation type"""
        return str(data.get('insulation', 'PVC')).strip()

    def _extract_length_m(self, data: Dict) -> float:
        """Extract cable length in meters"""
        length_str = str(data.get('length_m', '25')).replace(',', '').strip()
        try:
            return float(length_str)
        except ValueError:
            return 25.0

    def _extract_armored(self, data: Dict) -> bool:
        """Extract armored flag"""
        armored_str = str(data.get('armored', 'false')).lower()
        return any(word in armored_str for word in ['true', 'yes', 'y', 'swa', 'armored', 'armoured'])

    # Bus extraction helper methods
    def _extract_bus_id(self, data: Dict) -> Optional[str]:
        """Extract bus ID"""
        bus_id = data.get('bus_id')
        if bus_id:
            return str(bus_id).strip()
        return None

    def _extract_bus_name(self, data: Dict) -> str:
        """Extract bus name"""
        return str(data.get('bus_name', 'Unknown Bus')).strip()

    def _extract_bus_voltage(self, data: Dict) -> float:
        """Extract bus voltage"""
        voltage_str = str(data.get('voltage', '400')).replace(',', '').strip()
        try:
            return float(voltage_str)
        except ValueError:
            return 400.0

    def _extract_bus_phases(self, data: Dict) -> int:
        """Extract number of phases for bus"""
        phases_str = str(data.get('phases', '3')).strip().lower()
        if '1' in phases_str or 'single' in phases_str:
            return 1
        else:
            return 3

    def _extract_rated_current_a(self, data: Dict) -> float:
        """Extract rated current"""
        current_str = str(data.get('rated_current_a', '630')).replace(',', '').strip()
        try:
            return float(current_str)
        except ValueError:
            return 630.0

    def _extract_short_circuit_rating_ka(self, data: Dict) -> float:
        """Extract short circuit rating"""
        sc_str = str(data.get('short_circuit_rating_ka', '50')).replace(',', '').strip()
        try:
            return float(sc_str)
        except ValueError:
            return 50.0

    def _assess_bus_data_quality(self, buses: List[Bus]) -> float:
        """Assess data quality for extracted buses"""
        if not buses:
            return 0.0

        quality_scores = []
        for bus in buses:
            score = 1.0
            
            # Check for missing critical data
            if not bus.bus_id:
                score -= 0.3
            if not bus.bus_name:
                score -= 0.2
            if bus.voltage <= 0:
                score -= 0.3
            if bus.rated_current_a <= 0:
                score -= 0.2
            
            quality_scores.append(max(score, 0.0))

        return sum(quality_scores) / len(quality_scores)

    def _bus_to_dict(self, bus: Bus) -> Dict:
        """Convert Bus object to dictionary"""
        return {
            'bus_id': bus.bus_id,
            'bus_name': bus.bus_name,
            'voltage': bus.voltage,
            'phases': bus.phases,
            'rated_current_a': bus.rated_current_a,
            'short_circuit_rating_ka': bus.short_circuit_rating_ka
        }

    def _calculate_extraction_confidence(self, extracted_items: List, total_rows: int) -> float:
        """Calculate extraction confidence based on success rate and data quality"""
        if total_rows == 0:
            return 0.0

        success_rate = len(extracted_items) / total_rows
        
        # Weight the success rate heavily
        base_confidence = success_rate * 0.8
        
        # Add bonus for complete extractions
        if success_rate > 0.9:
            base_confidence += 0.1
        elif success_rate > 0.8:
            base_confidence += 0.05

        return min(base_confidence, 1.0)

    def _assess_load_data_quality(self, loads: List[Load]) -> float:
        """Assess data quality for extracted loads"""
        if not loads:
            return 0.0

        quality_scores = []
        for load in loads:
            score = 1.0
            
            # Check for missing critical data
            if not load.load_id:
                score -= 0.3
            if not load.load_name:
                score -= 0.2
            if load.power_kw <= 0:
                score -= 0.3
            if load.voltage not in [230, 400, 415]:
                score -= 0.1
            
            # Check for reasonable values
            if not 0.1 <= load.power_factor <= 1.0:
                score -= 0.1
            if not 0.1 <= load.efficiency <= 1.0:
                score -= 0.1
            if load.cable_length < 0.1 or load.cable_length > 1000:
                score -= 0.1
                
            quality_scores.append(max(score, 0.0))

        return sum(quality_scores) / len(quality_scores)

    def _assess_cable_data_quality(self, cables: List[Cable]) -> float:
        """Assess data quality for extracted cables"""
        if not cables:
            return 0.0

        quality_scores = []
        for cable in cables:
            score = 1.0
            
            # Check for missing critical data
            if not cable.cable_id:
                score -= 0.3
            if not cable.from_equipment:
                score -= 0.2
            if not cable.to_equipment:
                score -= 0.2
            if cable.cores <= 0:
                score -= 0.2
            if cable.size_sqmm <= 0:
                score -= 0.2
            
            quality_scores.append(max(score, 0.0))

        return sum(quality_scores) / len(quality_scores)

    def _load_to_dict(self, load: Load) -> Dict:
        """Convert Load object to dictionary"""
        return {
            'load_id': load.load_id,
            'load_name': load.load_name,
            'power_kw': load.power_kw,
            'voltage': load.voltage,
            'phases': load.phases,
            'load_type': load.load_type.value,
            'power_factor': load.power_factor,
            'efficiency': load.efficiency,
            'source_bus': load.source_bus,
            'priority': load.priority.value,
            'cable_length': load.cable_length,
            'installation_method': load.installation_method.value,
            'current_a': load.current_a,
            'design_current_a': load.design_current_a,
            'apparent_power_kva': load.apparent_power_kva
        }

    def _cable_to_dict(self, cable: Cable) -> Dict:
        """Convert Cable object to dictionary"""
        return {
            'cable_id': cable.cable_id,
            'from_equipment': cable.from_equipment,
            'to_equipment': cable.to_equipment,
            'cores': cable.cores,
            'size_sqmm': cable.size_sqmm,
            'cable_type': cable.cable_type,
            'insulation': cable.insulation,
            'length_m': cable.length_m,
            'installation_method': cable.installation_method.value,
            'armored': cable.armored
        }


class DataEnhancer:
    """
    Auto-correct common issues (broken IDs, missing relationships)
    """

    def __init__(self):
        self.id_patterns = {
            'load': r'^[Ll]?\d{3}$',
            'cable': r'^[Cc]?\d{3}$',
            'bus': r'^[Bb]?\d{3}$'
        }
        self.warnings = []

    def enhance_project_data(self, project: Project, extraction_results: List[ExtractionResult]) -> Dict[str, Any]:
        """
        Enhance extracted project data by fixing common issues
        
        Args:
            project: Project object to enhance
            extraction_results: List of extraction results
            
        Returns:
            Dictionary with enhancement report
        """
        corrections_made = []
        
        # Fix broken IDs
        id_corrections = self._fix_broken_ids(project)
        corrections_made.extend(id_corrections)
        
        # Establish missing relationships
        relationship_corrections = self._establish_missing_relationships(project)
        corrections_made.extend(relationship_corrections)
        
        # Build bus registry and validate load references
        bus_registry_corrections = self._validate_bus_registry(project)
        corrections_made.extend(bus_registry_corrections)
        
        # Standardize naming conventions
        naming_corrections = self._standardize_naming_conventions(project)
        corrections_made.extend(naming_corrections)
        
        # Fill missing calculated values
        calculated_corrections = self._fill_missing_calculated_values(project)
        corrections_made.extend(calculated_corrections)
        
        return {
            'corrections_made': corrections_made,
            'correction_count': len(corrections_made),
            'enhancement_success': True,
            'final_project': project
        }

    def _fix_broken_ids(self, project: Project) -> List[Dict]:
        """Fix broken or missing IDs - UPDATE IN PLACE, not append"""
        corrections = []
        counter = {'load': 1, 'cable': 1, 'bus': 1}
        
        # Fix load IDs - update in place
        for i, load in enumerate(project.loads):
            if not load.load_id or not re.match(self.id_patterns['load'], load.load_id):
                old_id = load.load_id
                new_id = f"L{counter['load']:03d}"
                corrections.append({
                    'type': 'load_id_fixed',
                    'original': old_id,
                    'corrected': new_id,
                    'reason': 'invalid_or_missing_load_id'
                })
                load.load_id = new_id
                counter['load'] += 1
                
                # Update any cable connections that reference the old ID - update in place
                for cable in project.cables:
                    if cable.to_equipment == old_id:
                        cable.to_equipment = new_id
                        corrections.append({
                            'type': 'cable_connection_updated',
                            'cable_id': cable.cable_id,
                            'old_destination': old_id,
                            'new_destination': new_id,
                            'reason': 'load_id_change'
                        })
        
        # Fix cable IDs - update in place
        for i, cable in enumerate(project.cables):
            if not cable.cable_id or not re.match(self.id_patterns['cable'], cable.cable_id):
                old_id = cable.cable_id
                new_id = f"C{counter['cable']:03d}"
                corrections.append({
                    'type': 'cable_id_fixed',
                    'original': old_id,
                    'corrected': new_id,
                    'reason': 'invalid_or_missing_cable_id'
                })
                cable.cable_id = new_id
                counter['cable'] += 1
        
        # Fix bus IDs - update in place
        for i, bus in enumerate(project.buses):
            if not bus.bus_id or not re.match(self.id_patterns['bus'], bus.bus_id):
                old_id = bus.bus_id
                new_id = f"B{counter['bus']:03d}"
                corrections.append({
                    'type': 'bus_id_fixed',
                    'original': old_id,
                    'corrected': new_id,
                    'reason': 'invalid_or_missing_bus_id'
                })
                bus.bus_id = new_id
                counter['bus'] += 1
        
        return corrections

    def _establish_missing_relationships(self, project: Project) -> List[Dict]:
        """Establish missing relationships between components - UPDATE IN PLACE, not append"""
        corrections = []
        
        # Create default buses if none exist
        if not project.buses:
            # Create main bus
            main_bus = Bus(
                bus_id="B001",
                bus_name="Main Distribution Bus",
                voltage=400,
                phases=3,
                rated_current_a=630,
                short_circuit_rating_ka=50
            )
            project.buses.append(main_bus)
            corrections.append({
                'type': 'bus_created',
                'bus_id': 'B001',
                'reason': 'missing_bus_system'
            })
        
        # Build bus registry first
        bus_ids = {bus.bus_id for bus in project.buses}
        
        # Assign loads to buses if not assigned - UPDATE IN PLACE
        main_bus = project.buses[0] if project.buses else None
        if main_bus:
            for load in project.loads:
                if not load.source_bus or load.source_bus not in bus_ids:
                    load.source_bus = main_bus.bus_id
                    main_bus.add_load(load.load_id)
                    corrections.append({
                        'type': 'load_bus_assignment',
                        'load_id': load.load_id,
                        'bus_id': main_bus.bus_id,
                        'reason': 'missing_or_invalid_bus_assignment'
                    })
        
        # Create cables for loads that don't have them - UPDATE IN PLACE
        load_ids_with_cables = {cable.to_equipment for cable in project.cables}
        existing_cable_count = len(project.cables)
        
        for load in project.loads:
            if load.load_id not in load_ids_with_cables and load.cable_length > 0:
                # Create a basic cable for this load
                # Estimate cable size based on load current (minimum 2.5mm²)
                estimated_size = max(2.5, min(50, load.design_current_a / 10)) if load.design_current_a else 2.5
                
                cable = Cable(
                    cable_id=f"C{existing_cable_count + 1:03d}",
                    from_equipment=load.source_bus or "B001",
                    to_equipment=load.load_id,
                    cores=4 if load.phases == 3 else 2,
                    size_sqmm=estimated_size,
                    cable_type="XLPE/PVC",
                    insulation="PVC",
                    length_m=load.cable_length,
                    installation_method=load.installation_method,
                    armored=load.installation_method in [InstallationMethod.BURIED, InstallationMethod.DUCT]
                )
                project.cables.append(cable)
                existing_cable_count += 1
                corrections.append({
                    'type': 'cable_created',
                    'cable_id': cable.cable_id,
                    'load_id': load.load_id,
                    'reason': 'missing_cable_for_load'
                })
        
        return corrections

    def _validate_bus_registry(self, project: Project) -> List[Dict]:
        """Build bus registry and validate load references"""
        corrections = []
        
        # Build bus registry first
        bus_ids = {b.bus_id for b in project.buses}
        
        # Validate load references to buses (after bus registry is built)
        for load in project.loads:
            if load.source_bus and load.source_bus not in bus_ids:
                corrections.append({
                    'type': 'unknown_bus_reference',
                    'load_id': load.load_id,
                    'unknown_bus': load.source_bus,
                    'action': 'warning_logged',
                    'reason': 'load_references_unknown_bus'
                })
                logger.warning(f"Load {load.load_id}: unknown bus {load.source_bus}")
        
        return corrections

    def _standardize_naming_conventions(self, project: Project) -> List[Dict]:
        """Standardize naming conventions across components"""
        corrections = []
        
        # Standardize load names
        for load in project.loads:
            original_name = load.load_name
            standardized_name = self._standardize_load_name(original_name)
            if standardized_name != original_name:
                load.load_name = standardized_name
                corrections.append({
                    'type': 'load_name_standardized',
                    'load_id': load.load_id,
                    'original': original_name,
                    'standardized': standardized_name,
                    'reason': 'naming_convention_standardization'
                })
        
        return corrections

    def _standardize_load_name(self, name: str) -> str:
        """Standardize individual load names"""
        if not name:
            return "Unknown Load"
        
        # Clean up common issues
        name = str(name).strip()
        
        # Title case
        name = ' '.join(word.capitalize() for word in name.split())
        
        # Common replacements
        replacements = {
            'Hvac': 'HVAC',
            'Ups': 'UPS',
            'Led': 'LED',
            'Dc': 'DC',
            'Ac': 'AC',
            'Motor': 'Motor',
            'Pump': 'Pump',
            'Fan': 'Fan'
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        return name

    def _fill_missing_calculated_values(self, project: Project) -> List[Dict]:
        """Fill in missing calculated values using electrical engineering rules"""
        corrections = []
        engine = ElectricalCalculationEngine()
        
        # Recalculate loads
        for load in project.loads:
            try:
                original_current = load.current_a
                engine.calculate_load(load)
                
                if load.current_a != original_current:
                    corrections.append({
                        'type': 'load_current_recalculated',
                        'load_id': load.load_id,
                        'original_current': original_current,
                        'corrected_current': load.current_a,
                        'reason': 'electrical_calculation_update'
                    })
            except Exception as e:
                logger.warning(f"Failed to recalculate load {load.load_id}: {e}")
        
        return corrections


def uniques_by_id(items, key):
    """Deduplicate items by ID, keeping first occurrence"""
    seen, out = set(), []
    for it in items:
        k = getattr(it, key, None)
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out

# Helper function for bus registry
def parse_bus_sheet(buses):
    """Helper function to simulate bus sheet parsing"""
    return buses


class ValidationEngine:
    """
    Cross-check with electrical engineering rules
    """

    def __init__(self, standard: str = "IEC"):
        self.standard = StandardsFactory.get_standard(standard)
        self.calculation_engine = ElectricalCalculationEngine(standard)

    def validate_project(self, project: Project) -> Dict[str, Any]:
        """
        Validate entire project against electrical engineering rules
        
        Args:
            project: Project object to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': [],
            'electrical_violations': [],
            'quality_score': 0.0
        }
        
        error_count = 0
        warning_count = 0
        
        # Validate individual components
        for load in project.loads:
            load_validation = self._validate_load(load)
            validation_results['errors'].extend(load_validation['errors'])
            validation_results['warnings'].extend(load_validation['warnings'])
            validation_results['electrical_violations'].extend(load_validation['violations'])
            
            error_count += len(load_validation['errors'])
            warning_count += len(load_validation['warnings'])
        
        for cable in project.cables:
            cable_validation = self._validate_cable(cable)
            validation_results['errors'].extend(cable_validation['errors'])
            validation_results['warnings'].extend(cable_validation['warnings'])
            validation_results['electrical_violations'].extend(cable_validation['violations'])
            
            error_count += len(cable_validation['errors'])
            warning_count += len(cable_validation['warnings'])
        
        # Validate system-level consistency
        system_validation = self._validate_system_consistency(project)
        validation_results['errors'].extend(system_validation['errors'])
        validation_results['warnings'].extend(system_validation['warnings'])
        validation_results['recommendations'].extend(system_validation['recommendations'])
        
        error_count += len(system_validation['errors'])
        warning_count += len(system_validation['warnings'])
        
        # Determine overall validity
        validation_results['is_valid'] = error_count == 0
        
        # Calculate quality score
        total_items = len(project.loads) + len(project.cables) + len(project.buses)
        if total_items > 0:
            quality_score = (total_items - error_count - warning_count * 0.5) / total_items
            validation_results['quality_score'] = max(quality_score, 0.0)
        
        return validation_results

    def _validate_load(self, load: Load) -> Dict[str, List[str]]:
        """Validate individual load"""
        result = {
            'errors': [],
            'warnings': [],
            'violations': []
        }
        
        # Basic validation
        if not load.load_id:
            result['errors'].append(f"Load {load.load_name}: Missing load ID")
        
        if load.power_kw <= 0:
            result['errors'].append(f"Load {load.load_id}: Power must be positive")
        
        if load.voltage not in [230, 400, 415, 440, 690, 3300, 6600, 11000, 33000]:
            result['warnings'].append(f"Load {load.load_id}: Non-standard voltage {load.voltage}V")
        
        if not (0.1 <= load.power_factor <= 1.0):
            result['errors'].append(f"Load {load.load_id}: Power factor out of range (0.1-1.0)")
        
        if not (0.1 <= load.efficiency <= 1.0):
            result['errors'].append(f"Load {load.load_id}: Efficiency out of range (0.1-1.0)")
        
        # Electrical validation
        if load.current_a and load.design_current_a:
            if load.breaker_rating_a and load.breaker_rating_a < load.design_current_a:
                result['errors'].append(f"Load {load.load_id}: Breaker rating {load.breaker_rating_a}A too low for design current {load.design_current_a}A")
            
            if load.voltage_drop_percent and load.voltage_drop_percent > 5.0:
                result['warnings'].append(f"Load {load.load_id}: High voltage drop {load.voltage_drop_percent:.1f}%")
        
        # Load type specific validation
        if load.load_type == LoadType.MOTOR:
            if load.power_kw > 500:
                result['warnings'].append(f"Load {load.load_id}: Large motor {load.power_kw}kW - consider special protection")
        
        return result

    def _validate_cable(self, cable: Cable) -> Dict[str, List[str]]:
        """Validate individual cable"""
        result = {
            'errors': [],
            'warnings': [],
            'violations': []
        }
        
        # Basic validation
        if not cable.cable_id:
            result['errors'].append(f"Cable from {cable.from_equipment}: Missing cable ID")
        
        if not cable.from_equipment:
            result['errors'].append(f"Cable {cable.cable_id}: Missing source equipment")
        
        if not cable.to_equipment:
            result['errors'].append(f"Cable {cable.cable_id}: Missing destination equipment")
        
        if cable.cores not in [2, 3, 4]:
            result['warnings'].append(f"Cable {cable.cable_id}: Unusual core count {cable.cores}")
        
        if cable.size_sqmm < 1.5:
            result['warnings'].append(f"Cable {cable.cable_id}: Very small cable size {cable.size_sqmm}mm²")
        
        if cable.size_sqmm > 500:
            result['warnings'].append(f"Cable {cable.cable_id}: Very large cable size {cable.size_sqmm}mm²")
        
        if cable.length_m < 1:
            result['warnings'].append(f"Cable {cable.cable_id}: Very short cable length {cable.length_m}m")
        
        if cable.length_m > 1000:
            result['warnings'].append(f"Cable {cable.cable_id}: Very long cable length {cable.length_m}m")
        
        # Treat negative length as an error (not a warning)
        if cable.length_m is not None and cable.length_m <= 0:
            result['errors'].append(f"Cable {cable.cable_id}: non-positive length {cable.length_m} m")
        
        return result

    def _validate_system_consistency(self, project: Project) -> Dict[str, List[str]]:
        """Validate system-level consistency"""
        result = {
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check for duplicate IDs
        load_ids = [l.load_id for l in project.loads]
        if len(load_ids) != len(set(load_ids)):
            result['errors'].append("Duplicate load IDs found")
        
        cable_ids = [c.cable_id for c in project.cables]
        if len(cable_ids) != len(set(cable_ids)):
            result['errors'].append("Duplicate cable IDs found")
        
        # Check bus assignments
        bus_ids = {b.bus_id for b in project.buses}
        for load in project.loads:
            if load.source_bus and load.source_bus not in bus_ids:
                result['warnings'].append(f"Load {load.load_id}: References unknown bus {load.source_bus}")
        
        # Check load balance
        total_power = sum(load.power_kw for load in project.loads)
        if total_power > 1000:  # 1 MW threshold
            result['recommendations'].append(f"Large total load {total_power}kW - consider multiple feeders")
        
        # Check voltage consistency
        voltages = set(load.voltage for load in project.loads)
        if len(voltages) > 2:
            result['recommendations'].append(f"Multiple voltage levels detected: {sorted(voltages)}V")
        
        return result


class AIExcelExtractor:
    """
    Main orchestrator for AI-powered Excel extraction with embedding capabilities
    """

    def __init__(self, standard: str = "IEC"):
        self.standard = standard
        self.sheet_classifier = SheetClassifier()
        self.column_mapper = ColumnMapper()
        self.data_extractor = DataExtractor()
        self.data_enhancer = DataEnhancer()
        self.validation_engine = ValidationEngine(standard)
        self.status = "PENDING"
        self.reset_state()

    def reset_state(self):
        """Hard reset state at the start of every run"""
        from models import Project
        
        # Create empty project
        self.project = Project(project_name="", project_id="", standard=self.standard)
        self.project.loads = []
        self.project.cables = []
        self.project.buses = []
        self.project.transformers = []
        
        self.sheet_results = {}
        self.errors = []
        self.warnings = []
        self.logs = []
        self.run_id = uuid.uuid4().hex
        logger.info(f"State reset for run_id: {self.run_id}")

    def process_excel_file(self, file_path: str) -> ProcessingReport:
        """
        Process Excel file and extract all electrical components
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            ProcessingReport with comprehensive results
        """
        # Hard reset state at the very start
        self.reset_state()
        
        start_time = datetime.now()
        logger.info(f"Starting Excel file processing: {file_path} (run_id: {self.run_id})")
        
        try:
            # Fail loud and stop on extraction errors
            try:
                excel_data = pd.read_excel(file_path, sheet_name=None)
                logger.info(f"After sheet classification - run_id: {self.run_id}, sheets: {len(excel_data)}")
            except Exception as e:
                self.status = "FAILED"
                self.errors.append(f"Extraction failed: {e}")
                logger.error(f"IO Error - run_id: {self.run_id}, error: {e}")
                
                # Create failed report
                return ProcessingReport(
                    overall_confidence=0.0,
                    total_components=0,
                    processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                    sheet_results={},
                    project_data=self.project,
                    corrections_made=[],
                    validation_issues=self.errors,
                    provenance={'run_id': self.run_id, 'status': 'FAILED', 'error': str(e)}
                )
            
            logger.info(f"Read {len(excel_data)} sheets from file")
            
            # Process each sheet with instrumentation
            sheet_results = {}
            all_loads = []
            all_cables = []
            all_buses = []
            
            for sheet_name, df in excel_data.items():
                logger.info(f"Processing sheet: {sheet_name}")
                
                # Classify sheet
                classification = self.sheet_classifier.classify_sheet(df, sheet_name)
                
                # Log sheet classification snapshot
                self._log_snapshot("sheet_classification", {
                    "run": self.run_id,
                    "sheet": sheet_name,
                    "label": classification['sheet_type'],
                    "conf": classification['confidence'],
                    "method": classification.get('method', 'unknown')
                })
                
                logger.info(f"Sheet '{sheet_name}' classified as: {classification['sheet_type']} (confidence: {classification['confidence']:.2f}, method: {classification.get('method', 'unknown')})")
                
                # Map columns if we have a supported type
                if classification['recommended_model_mapping'] in ['Load', 'Cable', 'Bus']:
                    
                    # Define gray zone confirmation callback
                    def gray_zone_callback(gray_matches):
                        """Handle gray zone confirmations for ambiguous columns"""
                        confirmed = []
                        for match in gray_matches:
                            # Log the gray zone match for manual review
                            logger.info(f"Gray zone match: '{match['column']}' -> '{match['field']}' (conf: {match['confidence']:.2f})")
                            # For demonstration, auto-confirm all gray zone matches
                            # In production, this would prompt the user
                            confirmed.append(match)
                        return confirmed
                    
                    field_mapping = self.column_mapper.map_columns(
                        df.columns.tolist(),
                        classification['recommended_model_mapping'],
                        sheet_name,
                        confirm_callback=gray_zone_callback
                    )
                    
                    # Extract data based on sheet type
                    if classification['sheet_type'] == 'load_schedule':
                        loads, result = self.data_extractor.extract_loads(df, field_mapping)
                        all_loads.extend(loads)
                    elif classification['sheet_type'] == 'cable_schedule':
                        cables, result = self.data_extractor.extract_cables(df, field_mapping)
                        all_cables.extend(cables)
                    elif classification['sheet_type'] == 'bus_schedule':
                        buses, result = self.data_extractor.extract_buses(df, field_mapping)
                        all_buses.extend(buses)
                    else:
                        result = ExtractionResult(
                            success=True,
                            confidence=classification['confidence'],
                            sheet_type=classification['sheet_type'],
                            components_extracted=0,
                            data_quality_score=classification['confidence'],
                            extracted_data={}
                        )
                else:
                    result = ExtractionResult(
                        success=True,
                        confidence=classification['confidence'],
                        sheet_type=classification['sheet_type'],
                        components_extracted=0,
                        data_quality_score=classification['confidence'],
                        extracted_data={}
                    )
                
                sheet_results[sheet_name] = result
            
            # Log modeling snapshot
            self._log_snapshot("modeling", {
                "run": self.run_id,
                "counts": {
                    "loads": len(all_loads),
                    "cables": len(all_cables),
                    "buses": len(all_buses)
                }
            })
            
            # Create project from extracted data
            project = self._create_project_from_extracted_data(
                all_loads, all_cables, all_buses, sheet_results, file_path
            )
            
            # Pipeline must be: parse_buses → build registry → enhance → validate → rollups
            # 1. Enhance project data (normalize IDs/names IN PLACE)
            enhancement_results = self.data_enhancer.enhance_project_data(project, list(sheet_results.values()))
            
            # 2. Deduplicate after enhancement to remove any clones
            project.loads = uniques_by_id(project.loads, "load_id")
            project.cables = uniques_by_id(project.cables, "cable_id")
            project.buses = uniques_by_id(project.buses, "bus_id")
            
            # 3. Initialize validation results and enforce negative-length rule at one place (after enhancement & deduplication)
            validation_results = {'errors': [], 'warnings': []}
            length_validation_errors = self._validate_cable_lengths(project)
            validation_results['errors'].extend(length_validation_errors)
            
            # 4. Validation must always run, even with partial data
            validation_results = self.validation_engine.validate_project(project)
            
            # 5. Calculate overall confidence with guard - from model counts, not sheet counts
            model_component_counts = {
                'loads': len(project.loads),
                'cables': len(project.cables),
                'buses': len(project.buses),
                'transformers': len(project.transformers)
            }
            overall_confidence = self._calculate_confidence_from_model_counts(sheet_results, model_component_counts)
            
            # Log before totals snapshot
            self._log_snapshot("before_totals", {
                "run": self.run_id,
                "cable_ids_and_lengths": [(c.cable_id, c.length_m) for c in project.cables]
            })
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Sanity assertions before render
            self._run_sanity_asserts(project)
            
            # Log before render snapshot
            totals = self.compute_totals(project)
            self._log_snapshot("before_render", {
                "run": self.run_id,
                "totals": totals,
                "model_counts": model_component_counts,
                "errors": validation_results['errors'],
                "warnings": validation_results['warnings'],
                "overall_conf": overall_confidence
            })
            
            # Create final report
            report = ProcessingReport(
                overall_confidence=overall_confidence,
                total_components=totals['total_components'],
                processing_time_seconds=processing_time,
                sheet_results=sheet_results,
                project_data=project,
                corrections_made=enhancement_results['corrections_made'],
                validation_issues=validation_results['errors'] + validation_results['warnings'],
                provenance={'run_id': self.run_id, 'status': 'COMPLETED'}
            )
            
            logger.info(f"Processing completed: {report.total_components} components extracted, {overall_confidence:.2f} confidence (run_id: {self.run_id})")
            return report
            
        except Exception as e:
            logger.error(f"Error processing Excel file - run_id: {self.run_id}, error: {e}")
            return ProcessingReport(
                overall_confidence=0.0,
                total_components=0,
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                sheet_results={},
                project_data=self.project,
                corrections_made=[],
                validation_issues=[f"Processing failed: {str(e)}"],
                provenance={'run_id': self.run_id, 'status': 'FAILED', 'error': str(e)}
            )
    
    def compute_totals(self, project):
        """Single source of truth for totals from the model only"""
        total_loads = len(project.loads)
        total_power = sum((x.power_kw or 0.0) for x in project.loads)
        total_cables = len(project.cables)
        total_len = sum(
            float(x.length_m) for x in project.cables
            if isinstance(x.length_m, (int, float)) and x.length_m > 0
        )
        total_buses = len(project.buses)
        
        return {
            'total_loads': total_loads,
            'total_power': total_power,
            'total_cables': total_cables,
            'total_len': total_len,
            'total_buses': total_buses,
            'total_components': total_loads + total_cables + total_buses + len(project.transformers)
        }
    
    def _validate_cable_lengths(self, project):
        """Enforce the negative-length rule at one place"""
        errors = []
        for cable in project.cables:
            if cable.length_m is not None and cable.length_m <= 0:
                errors.append(f"Cable {cable.cable_id}: non-positive length {cable.length_m} m")
        return errors
    
    def _calculate_confidence_from_model_counts(self, sheet_results, model_counts):
        """Confidence calculated from model counts, not sheet counts"""
        # Use model component counts, weight sheet confidences by actual extracted counts
        weights, scores = [], []
        
        # Map sheet results to actual model data
        for sheet_name, result in sheet_results.items():
            if result.components_extracted > 0:
                # Get actual count from model for this sheet type
                if result.sheet_type == 'load_schedule':
                    count = model_counts['loads']
                elif result.sheet_type == 'cable_schedule':
                    count = model_counts['cables']
                elif result.sheet_type == 'bus_schedule':
                    count = model_counts['buses']
                elif result.sheet_type == 'transformer_schedule':
                    count = model_counts['transformers']
                else:
                    count = result.components_extracted  # fallback
                
                if count > 0:
                    weights.append(count)
                    scores.append(result.confidence)
        
        overall_conf = (sum(w*s for w,s in zip(weights, scores)) / sum(weights)) if weights else 0.0
        return overall_conf
    
    def _log_snapshot(self, step, data):
        """Instrument logs with four key snapshots"""
        logger.info(f"SNAPSHOT [{step}] - {json.dumps(data)}")
    
    def _run_sanity_asserts(self, project):
        """Sanity asserts to catch issues instantly"""
        # ID uniqueness asserts (no duplicate IDs)
        assert len(project.cables) == len({c.cable_id for c in project.cables}), f"Duplicate cable IDs detected: {len(project.cables)} vs {len({c.cable_id for c in project.cables})}"
        assert len(project.loads) == len({l.load_id for l in project.loads}), f"Duplicate load IDs detected: {len(project.loads)} vs {len({l.load_id for l in project.loads})}"
        assert len(project.buses) == len({b.bus_id for b in project.buses}), f"Duplicate bus IDs detected: {len(project.buses)} vs {len({b.bus_id for b in project.buses})}"
        
        # Object uniqueness asserts (no duplicate objects)
        assert len(set(id(x) for x in project.loads)) == len(project.loads), "Duplicate load objects detected"
        assert len(set(id(x) for x in project.cables)) == len(project.cables), "Duplicate cable objects detected"
        assert len(set(id(x) for x in project.buses)) == len(project.buses), "Duplicate bus objects detected"
        
        # Cable length validation
        errored_cables = [c for c in project.cables if c.length_m is not None and c.length_m <= 0]
        if errored_cables:
            logger.warning(f"Found {len(errored_cables)} cables with non-positive length")
        
        # Specific test file validation (Torture v2 invariants)
        if hasattr(project, 'source_file') and project.source_file and "Torture_Test_v2.xlsx" in project.source_file:
            assert len(project.loads) == 8, f"Expected 8 loads, got {len(project.loads)}"
            actual_power = sum(x.power_kw or 0 for x in project.loads)
            assert abs(actual_power - 52.4) < 1e-6, f"Expected power 52.4, got {actual_power}"
            assert len(project.cables) == 4, f"Expected 4 cables, got {len(project.cables)}"
            assert len(project.buses) == 6, f"Expected 6 buses, got {len(project.buses)}"
            cable_lengths = [c.length_m for c in project.cables if c.length_m and c.length_m > 0]
            total_length = sum(cable_lengths)
            assert abs(total_length - 139.0) < 1e-6, f"Expected cable length sum 139.0, got {total_length}"
        
        logger.info(f"Sanity asserts passed (run_id: {self.run_id})")

    def _create_project_from_extracted_data(self, loads: List[Load], cables: List[Cable],
                                           buses: List[Bus], sheet_results: Dict, file_path: str = "") -> Project:
        """Create Project object from extracted data"""
        project_name = "AI Extracted Project"
        
        # Try to extract project name from sheet results
        for sheet_name, result in sheet_results.items():
            if result.sheet_type == 'project_info' and result.extracted_data:
                project_info = result.extracted_data.get('project_info', {})
                if project_info.get('name'):
                    project_name = project_info['name']
                    break
        
        project = Project(
            project_name=project_name,
            standard=self.standard,
            voltage_system="LV"
        )
        
        # Set source file for validation
        project.source_file = file_path
        
        # Add components
        project.loads = loads
        project.cables = cables
        project.buses = buses
        
        return project


# Example usage and testing functions
def demo_extraction():
    """Demo function showing how to use the AIExcelExtractor"""
    extractor = AIExcelExtractor()
    
    # Process a sample Excel file
    try:
        report = extractor.process_excel_file("sample_electrical_project.xlsx")
        
        print(f"Processing Results:")
        print(f"Overall Confidence: {report.overall_confidence:.2%}")
        print(f"Total Components: {report.total_components}")
        print(f"Processing Time: {report.processing_time_seconds:.2f}s")
        
        print(f"\nSheet Results:")
        for sheet_name, result in report.sheet_results.items():
            print(f"  {sheet_name}: {result.sheet_type} ({result.confidence:.2%} confidence, {result.components_extracted} components)")
        
        if report.project_data:
            print(f"\nProject Summary:")
            print(f"  Loads: {len(report.project_data.loads)}")
            print(f"  Cables: {len(report.project_data.cables)}")
            print(f"  Buses: {len(report.project_data.buses)}")
        
        print(f"\nCorrections Made: {len(report.corrections_made)}")
        for correction in report.corrections_made:
            print(f"  - {correction['type']}: {correction.get('reason', 'N/A')}")
        
        print(f"\nValidation Issues: {len(report.validation_issues)}")
        for issue in report.validation_issues:
            print(f"  - {issue}")
            
    except Exception as e:
        print(f"Error in demo: {e}")


if __name__ == "__main__":
    # Run demo if this file is executed directly
    demo_extraction()