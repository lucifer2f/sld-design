"""
Vector Database Manager for Electrical Design Automation System

This module provides comprehensive vector database functionality for:
- RAG (Retrieval-Augmented Generation) with LLMs
- Component specification storage and retrieval
- Design pattern recognition
- Standards compliance knowledge base
- Excel column header mapping history

Integrates ChromaDB with sentence transformers for semantic search capabilities.
"""

import os
import logging
import numpy as np
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
import json
import hashlib
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import tempfile
import shutil

logger = logging.getLogger(__name__)


class VectorDatabaseManager:
    """
    Comprehensive vector database manager for electrical engineering applications.

    Provides RAG capabilities, component knowledge bases, design patterns,
    and intelligent search across electrical engineering domains.
    """

    def __init__(self, persist_directory: str = "./vector_db", model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the vector database manager.

        Args:
            persist_directory: Directory to persist vector database
            model_name: Sentence transformer model for embeddings
        """
        self.persist_directory = persist_directory
        self.model_name = model_name

        # Initialize sentence transformer model
        try:
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded sentence transformer model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load {model_name}, falling back to default: {e}")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Enhanced caching system
        self.query_cache = {}  # Query result cache
        self.embedding_cache = {}  # Embedding cache
        self.cache_max_size = 2000
        self.cache_ttl = 3600  # 1 hour TTL for cache entries
        self.cache_timestamps = {}

        # Persistence settings
        self.auto_save_interval = 300  # Auto-save every 5 minutes
        self.last_save_time = time.time()
        self.persistence_enabled = True

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Collection names for different knowledge domains
        self.collections = {
            'excel_headers': 'electrical_excel_headers',
            'component_specs': 'electrical_components',
            'design_patterns': 'electrical_design_patterns',
            'standards': 'electrical_standards',
            'component_recommendations': 'component_recommendations',
            'design_history': 'design_history'
        }

        # Initialize collections
        self._initialize_collections()

        # Load cache from disk
        self._load_cache_from_disk()

        logger.info("VectorDatabaseManager initialized successfully")

    def _initialize_collections(self):
        """Initialize all required collections"""
        for collection_name in self.collections.values():
            try:
                self.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"description": f"Collection for {collection_name}"}
                )
                logger.debug(f"Initialized collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize collection {collection_name}: {e}")

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            if isinstance(text, str):
                return self.embedding_model.encode(text).tolist()
            elif isinstance(text, list):
                # Handle list of texts
                combined_text = " ".join(text)
                return self.embedding_model.encode(combined_text).tolist()
            else:
                return self.embedding_model.encode(str(text)).tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * 384  # Default dimension for MiniLM

    def add_component_to_recommendations(self, component_id: str, component_data: Dict,
                                       usage_context: str = "", confidence: float = 0.8):
        """
        Add a component to the recommendations collection for future reference.

        Args:
            component_id: Unique component identifier
            component_data: Component specification data
            usage_context: Context in which this component was successfully used
            confidence: Confidence in the recommendation
        """
        try:
            collection = self._get_collection('component_recommendations')

            # Create searchable document
            document_parts = [
                f"Component: {component_id}",
                f"Type: {component_data.get('type', '')}",
                f"Rating: {component_data.get('power_kw', component_data.get('rating', ''))}",
                f"Voltage: {component_data.get('voltage', '')}V",
                f"Context: {usage_context}",
            ]

            document = " | ".join(document_parts)

            # Prepare metadata
            metadata = {
                "component_id": component_id,
                "component_type": component_data.get('type', ''),
                "power_rating": component_data.get('power_kw', 0),
                "voltage": component_data.get('voltage', 0),
                "usage_context": usage_context,
                "confidence": confidence,
                "recommendation_score": confidence,
                "timestamp": datetime.now().isoformat(),
                "component_data_json": json.dumps(component_data)
            }

            # Store in vector database
            collection.add(
                embeddings=[self._get_embedding(document)],
                documents=[document],
                metadatas=[metadata],
                ids=[f"rec_{component_id}_{int(datetime.now().timestamp())}"]
            )

            logger.debug(f"Added component recommendation: {component_id}")

        except Exception as e:
            logger.error(f"Failed to add component recommendation: {e}")

    def add_design_to_history(self, design_id: str, design_data: Dict,
                            project_context: str = "", success_rating: float = 0.8):
        """
        Add a successful design to the design history collection.

        Args:
            design_id: Unique design identifier
            design_data: Design specification data
            project_context: Project context where design was used
            success_rating: Success rating of the design
        """
        try:
            collection = self._get_collection('design_history')

            # Create searchable document
            components_str = ', '.join(design_data.get('components', []))
            standards_str = ', '.join(design_data.get('standards', []))

            document_parts = [
                f"Design: {design_id}",
                f"Description: {design_data.get('description', '')}",
                f"Components: {components_str}",
                f"Standards: {standards_str}",
                f"Industry: {design_data.get('industry', '')}",
                f"Project Context: {project_context}",
            ]

            document = " | ".join(document_parts)

            # Prepare metadata
            metadata = {
                "design_id": design_id,
                "description": design_data.get('description', ''),
                "components_str": components_str,
                "standards_str": standards_str,
                "industry": design_data.get('industry', ''),
                "project_context": project_context,
                "success_rating": success_rating,
                "efficiency_rating": design_data.get('efficiency_rating', 0.0),
                "complexity": design_data.get('complexity', 'medium'),
                "components_count": len(design_data.get('components', [])),
                "standards_count": len(design_data.get('standards', [])),
                "timestamp": datetime.now().isoformat(),
                "design_data_json": json.dumps(design_data)
            }

            # Store in vector database
            collection.add(
                embeddings=[self._get_embedding(document)],
                documents=[document],
                metadatas=[metadata],
                ids=[f"hist_{design_id}_{int(datetime.now().timestamp())}"]
            )

            logger.debug(f"Added design to history: {design_id}")

        except Exception as e:
            logger.error(f"Failed to add design to history: {e}")

    def get_component_recommendations(self, query: str, component_type: str = None, top_k: int = 5) -> List[Dict]:
        """
        Get component recommendations based on query and context.

        Args:
            query: Search query describing desired component characteristics
            component_type: Optional component type filter
            top_k: Number of recommendations to return

        Returns:
            List of recommended components with usage context
        """
        try:
            collection = self._get_collection('component_recommendations')

            # Build search query
            search_query = query
            if component_type:
                search_query = f"{query} type:{component_type}"

            # Add type filter if specified
            where_clause = None
            if component_type:
                where_clause = {"component_type": component_type}

            results = collection.query(
                query_embeddings=[self._get_embedding(search_query)],
                n_results=top_k,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            recommendations = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    # Parse component data from JSON string
                    component_data = {}
                    try:
                        component_data = json.loads(metadata.get("component_data_json", "{}"))
                    except:
                        pass

                    recommendations.append({
                        "component_id": metadata.get("component_id", ""),
                        "component_type": metadata.get("component_type", ""),
                        "power_rating": metadata.get("power_rating", 0),
                        "voltage": metadata.get("voltage", 0),
                        "usage_context": metadata.get("usage_context", ""),
                        "confidence": metadata.get("confidence", 0.0),
                        "recommendation_score": metadata.get("recommendation_score", 0.0),
                        "similarity_score": 1.0 - distance,
                        "component_data": component_data
                    })

            return recommendations

        except Exception as e:
            logger.error(f"Failed to get component recommendations: {e}")
            return []

    def search_design_history(self, query: str, industry: str = None, top_k: int = 5) -> List[Dict]:
        """
        Search successful design history for similar patterns.

        Args:
            query: Description of design requirements
            industry: Industry filter
            top_k: Number of results to return

        Returns:
            List of similar successful designs
        """
        try:
            collection = self._get_collection('design_history')

            # Build search query
            search_query = query
            if industry:
                search_query = f"{query} industry:{industry}"

            # Add industry filter if specified
            where_clause = None
            if industry:
                where_clause = {"industry": industry}

            results = collection.query(
                query_embeddings=[self._get_embedding(search_query)],
                n_results=top_k,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            designs = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    # Parse design data from JSON string
                    design_data = {}
                    try:
                        design_data = json.loads(metadata.get("design_data_json", "{}"))
                    except:
                        pass

                    designs.append({
                        "design_id": metadata.get("design_id", ""),
                        "description": metadata.get("description", ""),
                        "components": design_data.get("components", []),  # Get from parsed JSON
                        "standards": design_data.get("standards", []),    # Get from parsed JSON
                        "industry": metadata.get("industry", ""),
                        "project_context": metadata.get("project_context", ""),
                        "success_rating": metadata.get("success_rating", 0.0),
                        "efficiency_rating": metadata.get("efficiency_rating", 0.0),
                        "complexity": metadata.get("complexity", ""),
                        "components_count": metadata.get("components_count", 0),
                        "standards_count": metadata.get("standards_count", 0),
                        "similarity_score": 1.0 - distance,
                        "design_data": design_data
                    })

            return designs

        except Exception as e:
            logger.error(f"Failed to search design history: {e}")
            return []

    def _get_collection(self, collection_type: str):
        """Get collection by type"""
        collection_name = self.collections.get(collection_type)
        if not collection_name:
            raise ValueError(f"Unknown collection type: {collection_type}")

        return self.client.get_collection(collection_name)

    def store_component_specification(self, component_id: str, component_data: Dict,
                                     category: str = "general"):
        """
        Store component specification in vector database.

        Args:
            component_id: Unique component identifier
            component_data: Component specification data
            category: Component category (motor, cable, transformer, etc.)
        """
        try:
            collection = self._get_collection('component_specs')

            # Create searchable document
            document_parts = [
                f"Component ID: {component_id}",
                f"Category: {category}",
                f"Type: {component_data.get('type', 'unknown')}",
                f"Rating: {component_data.get('rating', 'unknown')}",
                f"Voltage: {component_data.get('voltage', 'unknown')}",
                f"Current: {component_data.get('current', 'unknown')}",
            ]

            # Add specific attributes based on component type
            if category == "motor":
                document_parts.extend([
                    f"Power: {component_data.get('power_kw', 'unknown')} kW",
                    f"Speed: {component_data.get('speed_rpm', 'unknown')} RPM",
                    f"Starting Method: {component_data.get('starting_method', 'unknown')}",
                ])
            elif category == "cable":
                document_parts.extend([
                    f"Size: {component_data.get('size_mm2', 'unknown')} mm²",
                    f"Material: {component_data.get('material', 'unknown')}",
                    f"Insulation: {component_data.get('insulation', 'unknown')}",
                ])
            elif category == "transformer":
                document_parts.extend([
                    f"Rating: {component_data.get('rating_kva', 'unknown')} kVA",
                    f"Vector Group: {component_data.get('vector_group', 'unknown')}",
                    f"Impedance: {component_data.get('impedance_percent', 'unknown')}%",
                ])

            document = " | ".join(document_parts)

            # Prepare metadata
            metadata = {
                "component_id": component_id,
                "category": category,
                "type": component_data.get('type', 'unknown'),
                "rating": component_data.get('rating', 'unknown'),
                "voltage": component_data.get('voltage', 'unknown'),
                "current": component_data.get('current', 'unknown'),
                "timestamp": datetime.now().isoformat(),
                "component_data": json.dumps(component_data)
            }

            # Store in vector database
            collection.add(
                embeddings=[self._get_embedding(document)],
                documents=[document],
                metadatas=[metadata],
                ids=[component_id]
            )

            logger.debug(f"Stored component specification: {component_id}")

        except Exception as e:
            logger.error(f"Failed to store component specification: {e}")

    def search_components(self, query: str, category: str = None, top_k: int = 10) -> List[Dict]:
        """
        Search for components matching query criteria.

        Args:
            query: Search query (e.g., "15kW motor 400V 3-phase")
            category: Optional category filter
            top_k: Number of results to return

        Returns:
            List of matching components with metadata
        """
        try:
            collection = self._get_collection('component_specs')

            # Build search query with filters
            search_query = query
            if category:
                search_query = f"{query} category:{category}"

            # Add category filter if specified
            where_clause = None
            if category:
                where_clause = {"category": category}

            results = collection.query(
                query_embeddings=[self._get_embedding(search_query)],
                n_results=top_k,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            components = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    # Parse component data
                    component_data = {}
                    try:
                        component_data = json.loads(metadata.get("component_data", "{}"))
                    except:
                        pass

                    components.append({
                        "component_id": metadata.get("component_id", ""),
                        "category": metadata.get("category", ""),
                        "type": metadata.get("type", ""),
                        "rating": metadata.get("rating", ""),
                        "voltage": metadata.get("voltage", ""),
                        "current": metadata.get("current", ""),
                        "similarity_score": 1.0 - distance,
                        "component_data": component_data
                    })

            return components

        except Exception as e:
            logger.error(f"Failed to search components: {e}")
            return []

    def store_design_pattern(self, pattern_id: str, pattern_data: Dict,
                            pattern_type: str = "general"):
        """
        Store design pattern for future recognition.

        Args:
            pattern_id: Unique pattern identifier
            pattern_data: Pattern description and characteristics
            pattern_type: Type of design pattern
        """
        try:
            collection = self._get_collection('design_patterns')

            # Create searchable document
            components_str = ', '.join(pattern_data.get('components', []))
            standards_str = ', '.join(pattern_data.get('standards', []))

            document_parts = [
                f"Pattern: {pattern_id}",
                f"Type: {pattern_type}",
                f"Description: {pattern_data.get('description', '')}",
                f"Components: {components_str}",
                f"Standards: {standards_str}",
                f"Industry: {pattern_data.get('industry', 'general')}",
            ]

            document = " | ".join(document_parts)

            # Prepare metadata (ChromaDB only accepts str, int, float, bool - no lists)
            metadata = {
                "pattern_id": pattern_id,
                "pattern_type": pattern_type,
                "description": pattern_data.get('description', ''),
                "components_str": components_str,  # Convert list to string
                "standards_str": standards_str,    # Convert list to string
                "industry": pattern_data.get('industry', 'general'),
                "efficiency_rating": float(pattern_data.get('efficiency_rating', 0.0)),
                "complexity": pattern_data.get('complexity', 'medium'),
                "components_count": len(pattern_data.get('components', [])),
                "standards_count": len(pattern_data.get('standards', [])),
                "timestamp": datetime.now().isoformat(),
                "pattern_data_json": json.dumps(pattern_data)  # Store as JSON string
            }

            # Store in vector database
            collection.add(
                embeddings=[self._get_embedding(document)],
                documents=[document],
                metadatas=[metadata],
                ids=[pattern_id]
            )

            logger.debug(f"Stored design pattern: {pattern_id}")

        except Exception as e:
            logger.error(f"Failed to store design pattern: {e}")

    def find_similar_designs(self, query: str, industry: str = None, top_k: int = 5) -> List[Dict]:
        """
        Find similar design patterns.

        Args:
            query: Description of desired design pattern
            industry: Industry filter
            top_k: Number of results to return

        Returns:
            List of similar design patterns
        """
        try:
            collection = self._get_collection('design_patterns')

            # Build search query
            search_query = query
            if industry:
                search_query = f"{query} industry:{industry}"

            # Add industry filter if specified
            where_clause = None
            if industry:
                where_clause = {"industry": industry}

            results = collection.query(
                query_embeddings=[self._get_embedding(search_query)],
                n_results=top_k,
                where=where_clause,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            patterns = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    # Parse pattern data from JSON string
                    pattern_data = {}
                    try:
                        pattern_data = json.loads(metadata.get("pattern_data_json", "{}"))
                    except:
                        pass

                    patterns.append({
                        "pattern_id": metadata.get("pattern_id", ""),
                        "pattern_type": metadata.get("pattern_type", ""),
                        "description": metadata.get("description", ""),
                        "components": pattern_data.get("components", []),  # Get from parsed JSON
                        "standards": pattern_data.get("standards", []),    # Get from parsed JSON
                        "industry": metadata.get("industry", ""),
                        "efficiency_rating": metadata.get("efficiency_rating", 0.0),
                        "complexity": metadata.get("complexity", ""),
                        "components_count": metadata.get("components_count", 0),
                        "standards_count": metadata.get("standards_count", 0),
                        "similarity_score": 1.0 - distance,
                        "pattern_data": pattern_data
                    })

            return patterns

        except Exception as e:
            logger.error(f"Failed to find similar designs: {e}")
            return []

    def store_standards_rule(self, rule_id: str, rule_data: Dict, standard: str = "IEC"):
        """
        Store standards compliance rule.

        Args:
            rule_id: Unique rule identifier
            rule_data: Rule description and requirements
            standard: Electrical standard (IEC, NEC, IS, etc.)
        """
        try:
            collection = self._get_collection('standards')

            # Create searchable document
            applies_to_str = ', '.join(rule_data.get('applies_to', []))

            document_parts = [
                f"Rule: {rule_id}",
                f"Standard: {standard}",
                f"Title: {rule_data.get('title', '')}",
                f"Description: {rule_data.get('description', '')}",
                f"Requirements: {rule_data.get('requirements', '')}",
                f"Category: {rule_data.get('category', '')}",
                f"Applies to: {applies_to_str}",
            ]

            document = " | ".join(document_parts)

            # Prepare metadata (ChromaDB only accepts str, int, float, bool - no lists)
            metadata = {
                "rule_id": rule_id,
                "standard": standard,
                "title": rule_data.get('title', ''),
                "description": rule_data.get('description', ''),
                "requirements": rule_data.get('requirements', ''),
                "category": rule_data.get('category', ''),
                "applies_to_str": applies_to_str,  # Convert list to string
                "severity": rule_data.get('severity', 'medium'),
                "reference": rule_data.get('reference', ''),
                "applies_to_count": len(rule_data.get('applies_to', [])),
                "timestamp": datetime.now().isoformat(),
                "rule_data_json": json.dumps(rule_data)  # Store as JSON string
            }

            # Store in vector database
            collection.add(
                embeddings=[self._get_embedding(document)],
                documents=[document],
                metadatas=[metadata],
                ids=[rule_id]
            )

            logger.debug(f"Stored standards rule: {rule_id}")

        except Exception as e:
            logger.error(f"Failed to store standards rule: {e}")

    def search_standards(self, query: str, standard: str = None, category: str = None,
                        top_k: int = 5) -> List[Dict]:
        """
        Search for relevant standards and compliance rules.

        Args:
            query: Search query (e.g., "cable sizing motor circuits")
            standard: Standard filter (IEC, NEC, etc.)
            category: Category filter
            top_k: Number of results to return

        Returns:
            List of relevant standards and rules
        """
        try:
            collection = self._get_collection('standards')

            # Build search query
            search_query = query
            if standard:
                search_query = f"{query} standard:{standard}"
            if category:
                search_query = f"{search_query} category:{category}"

            # Build where clause for filters
            where_clause = {}
            if standard:
                where_clause["standard"] = standard
            if category:
                where_clause["category"] = category

            results = collection.query(
                query_embeddings=[self._get_embedding(search_query)],
                n_results=top_k,
                where=where_clause if where_clause else None,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            standards = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    # Parse rule data from JSON string
                    rule_data = {}
                    try:
                        rule_data = json.loads(metadata.get("rule_data_json", "{}"))
                    except:
                        pass

                    standards.append({
                        "rule_id": metadata.get("rule_id", ""),
                        "standard": metadata.get("standard", ""),
                        "title": metadata.get("title", ""),
                        "description": metadata.get("description", ""),
                        "requirements": metadata.get("requirements", ""),
                        "category": metadata.get("category", ""),
                        "applies_to": rule_data.get("applies_to", []),  # Get from parsed JSON
                        "severity": metadata.get("severity", ""),
                        "reference": metadata.get("reference", ""),
                        "applies_to_count": metadata.get("applies_to_count", 0),
                        "similarity_score": 1.0 - distance,
                        "rule_data": rule_data
                    })

            return standards

        except Exception as e:
            logger.error(f"Failed to search standards: {e}")
            return []

    def rag_query(self, query: str, context_domain: str = "electrical",
                  top_k: int = 3, include_sources: bool = True) -> Dict[str, Any]:
        """
        Perform Retrieval-Augmented Generation query across all knowledge domains.

        Args:
            query: User query
            context_domain: Domain to search (electrical, components, standards, etc.)
            top_k: Number of results per domain
            include_sources: Whether to include source information

        Returns:
            Dictionary with retrieved context and sources
        """
        try:
            context_parts = []
            sources = []

            # Search across relevant collections based on domain
            if context_domain in ["electrical", "all"]:
                # Search component specifications
                components = self.search_components(query, top_k=top_k)
                for comp in components[:top_k]:
                    power_info = f" {comp['power_kw']}kW" if comp.get('power_kw') and comp['power_kw'] != 'N/A' else ""
                    context_parts.append(f"Component: {comp['component_id']} - {comp['type']}{power_info}")
                    if include_sources:
                        sources.append({
                            "type": "component",
                            "id": comp['component_id'],
                            "score": comp['similarity_score'],
                            "data": comp
                        })

                # Search design patterns
                patterns = self.find_similar_designs(query, top_k=top_k)
                for pattern in patterns[:top_k]:
                    context_parts.append(f"Design Pattern: {pattern['description']} - Components: {', '.join(pattern['components'])}")
                    if include_sources:
                        sources.append({
                            "type": "design_pattern",
                            "id": pattern['pattern_id'],
                            "score": pattern['similarity_score'],
                            "data": pattern
                        })

                # Search standards
                standards = self.search_standards(query, top_k=top_k)
                for std in standards[:top_k]:
                    context_parts.append(f"Standard: {std['title']} - {std['description']}")
                    if include_sources:
                        sources.append({
                            "type": "standard",
                            "id": std['rule_id'],
                            "score": std['similarity_score'],
                            "data": std
                        })

                # Search Excel header mappings
                headers = self.retrieve_excel_header_mappings(query, top_k=top_k)
                for header in headers[:top_k]:
                    context_parts.append(f"Header Mapping: '{header['header']}' → '{header['field']}' (confidence: {header['confidence']:.2f})")
                    if include_sources:
                        sources.append({
                            "type": "excel_header",
                            "header": header['header'],
                            "field": header['field'],
                            "score": header['similarity_score'],
                            "data": header
                        })

            # Combine context
            combined_context = "\n".join(context_parts)

            return {
                "query": query,
                "context": combined_context,
                "sources": sources if include_sources else [],
                "context_length": len(combined_context),
                "num_sources": len(sources) if include_sources else 0,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to perform RAG query: {e}")
            return {
                "query": query,
                "context": "",
                "sources": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def initialize_default_knowledge_base(self):
        """Initialize the vector database with default electrical engineering knowledge"""
        try:
            logger.info("Initializing default knowledge base...")

            # Initialize common component specifications
            self._initialize_common_components()

            # Initialize common design patterns
            self._initialize_common_design_patterns()

            # Initialize standards compliance rules
            self._initialize_standards_rules()

            # Initialize Excel header mappings for common variations
            self._initialize_excel_header_mappings()

            logger.info("Default knowledge base initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize default knowledge base: {e}")

    def _initialize_excel_header_mappings(self):
        """Initialize vector database with common Excel header mappings"""
        try:
            logger.info("Initializing Excel header mappings...")

            # Common Excel header variations and their mappings
            header_mappings = [
                # Load schedule headers
                ("load id", "load_id", 0.95),
                ("load_id", "load_id", 1.0),
                ("equipment id", "load_id", 0.85),
                ("asset tag", "load_id", 0.80),
                ("load name", "load_name", 0.95),
                ("load_name", "load_name", 1.0),
                ("equipment name", "load_name", 0.90),
                ("description", "load_name", 0.75),
                ("power (kw)", "power_kw", 1.0),
                ("power kw", "power_kw", 0.95),
                ("kw", "power_kw", 0.85),
                ("power rating", "power_kw", 0.90),
                ("voltage (v)", "voltage", 1.0),
                ("voltage v", "voltage", 0.95),
                ("volts", "voltage", 0.90),
                ("operating voltage", "voltage", 0.85),
                ("phases", "phases", 1.0),
                ("phase", "phases", 0.90),
                ("number of phases", "phases", 0.85),
                ("load type", "load_type", 0.95),
                ("equipment type", "load_type", 0.90),
                ("power factor", "power_factor", 0.95),
                ("pf", "power_factor", 0.85),
                ("cos phi", "power_factor", 0.90),
                ("efficiency", "efficiency", 0.95),
                ("eta", "efficiency", 0.85),
                ("η", "efficiency", 0.80),
                ("source bus", "source_bus", 0.95),
                ("bus", "source_bus", 0.80),
                ("distribution board", "source_bus", 0.85),
                ("priority", "priority", 0.95),
                ("importance", "priority", 0.85),
                ("cable length", "cable_length", 0.95),
                ("length (m)", "cable_length", 0.90),
                ("installation method", "installation_method", 0.95),
                ("install method", "installation_method", 0.90),
                ("routing", "installation_method", 0.80),

                # Cable schedule headers
                ("cable id", "cable_id", 0.95),
                ("cable_id", "cable_id", 1.0),
                ("cable tag", "cable_id", 0.85),
                ("from equipment", "from_equipment", 0.95),
                ("from", "from_equipment", 0.85),
                ("source", "from_equipment", 0.80),
                ("origin", "from_equipment", 0.85),
                ("to equipment", "to_equipment", 0.95),
                ("to", "to_equipment", 0.85),
                ("destination", "to_equipment", 0.80),
                ("target", "to_equipment", 0.85),
                ("cores", "cores", 1.0),
                ("core", "cores", 0.90),
                ("number of cores", "cores", 0.95),
                ("size (mm2)", "size_sqmm", 0.95),
                ("size mm2", "size_sqmm", 0.90),
                ("csa", "size_sqmm", 0.80),
                ("cross section", "size_sqmm", 0.85),
                ("conductor size", "size_sqmm", 0.90),
                ("cable type", "cable_type", 0.95),
                ("type", "cable_type", 0.75),
                ("insulation", "cable_type", 0.80),
                ("length (m)", "length_m", 0.95),
                ("length m", "length_m", 0.90),
                ("cable length", "length_m", 0.85),
                ("run length", "length_m", 0.80),
                ("install method", "installation_method", 0.90),
                ("installation", "installation_method", 0.85),
                ("armored", "armored", 1.0),
                ("armoured", "armored", 0.95),
                ("swa", "armored", 0.85),

                # Bus schedule headers
                ("bus id", "bus_id", 0.95),
                ("bus_id", "bus_id", 1.0),
                ("panel id", "bus_id", 0.85),
                ("bus name", "bus_name", 0.95),
                ("bus_name", "bus_name", 1.0),
                ("panel name", "bus_name", 0.85),
                ("description", "bus_name", 0.70),
                ("un (v)", "voltage", 0.90),
                ("rated voltage", "voltage", 0.95),
                ("system voltage", "voltage", 0.90),
                ("phases", "phases", 1.0),
                ("phase", "phases", 0.90),
                ("rated current (a)", "rated_current_a", 0.95),
                ("rated current a", "rated_current_a", 0.90),
                ("current", "rated_current_a", 0.80),
                ("ampere rating", "rated_current_a", 0.85),
                ("upstream bus", "upstream_bus", 0.95),
                ("upstream", "upstream_bus", 0.85),
                ("parent bus", "upstream_bus", 0.90),
                ("short circuit rating (ka)", "short_circuit_rating_ka", 0.95),
                ("sc rating", "short_circuit_rating_ka", 0.85),
                ("fault level", "short_circuit_rating_ka", 0.80)
            ]

            for header, field, confidence in header_mappings:
                self.store_excel_header_mapping(
                    header=header,
                    field=field,
                    confidence=confidence,
                    context=f"Default mapping for {field}",
                    project_id="default_knowledge_base"
                )

            logger.info(f"Initialized {len(header_mappings)} Excel header mappings")

        except Exception as e:
            logger.error(f"Failed to initialize Excel header mappings: {e}")

    def _initialize_common_components(self):
        """Initialize database with common electrical components"""
        common_components = [
            # Motors
            {
                "id": "motor_15kw_400v_3ph",
                "data": {
                    "type": "induction_motor",
                    "power_kw": 15.0,
                    "voltage": 400,
                    "phases": 3,
                    "power_factor": 0.82,
                    "efficiency": 0.88,
                    "starting_method": "DOL",
                    "speed_rpm": 1450,
                    "full_load_current_a": 27.5,
                    "starting_current_ratio": 6.0,
                    "insulation_class": "F",
                    "ip_rating": "IP55",
                    "duty_cycle": "S1",
                    "mounting": "B3"
                },
                "category": "motor"
            },
            {
                "id": "motor_37kw_400v_3ph",
                "data": {
                    "type": "induction_motor",
                    "power_kw": 37.0,
                    "voltage": 400,
                    "phases": 3,
                    "power_factor": 0.84,
                    "efficiency": 0.91,
                    "starting_method": "Star-Delta",
                    "speed_rpm": 1480,
                    "full_load_current_a": 65.0,
                    "starting_current_ratio": 4.5,
                    "insulation_class": "F",
                    "ip_rating": "IP55",
                    "duty_cycle": "S1",
                    "mounting": "B3"
                },
                "category": "motor"
            },
            {
                "id": "motor_75kw_400v_3ph",
                "data": {
                    "type": "induction_motor",
                    "power_kw": 75.0,
                    "voltage": 400,
                    "phases": 3,
                    "power_factor": 0.86,
                    "efficiency": 0.93,
                    "starting_method": "Star-Delta",
                    "speed_rpm": 1485,
                    "full_load_current_a": 130.0,
                    "starting_current_ratio": 4.0,
                    "insulation_class": "F",
                    "ip_rating": "IP55",
                    "duty_cycle": "S1",
                    "mounting": "B3"
                },
                "category": "motor"
            },

            # Cables
            {
                "id": "cable_cu_xlpe_4mm2_4c",
                "data": {
                    "type": "XLPE_cable",
                    "size_mm2": 4.0,
                    "cores": 4,
                    "material": "copper",
                    "insulation": "XLPE",
                    "voltage_rating": 1000,
                    "current_rating": 37,
                    "resistance_ohm_per_km": 4.61,
                    "reactance_ohm_per_km": 0.07,
                    "cable_weight_kg_per_km": 240,
                    "outer_diameter_mm": 15.2,
                    "bending_radius_mm": 76,
                    "max_operating_temp_c": 90,
                    "short_circuit_rating_ka_1s": 2.1
                },
                "category": "cable"
            },
            {
                "id": "cable_cu_xlpe_10mm2_4c",
                "data": {
                    "type": "XLPE_cable",
                    "size_mm2": 10.0,
                    "cores": 4,
                    "material": "copper",
                    "insulation": "XLPE",
                    "voltage_rating": 1000,
                    "current_rating": 52,
                    "resistance_ohm_per_km": 1.83,
                    "reactance_ohm_per_km": 0.065,
                    "cable_weight_kg_per_km": 350,
                    "outer_diameter_mm": 18.5,
                    "bending_radius_mm": 92,
                    "max_operating_temp_c": 90,
                    "short_circuit_rating_ka_1s": 3.8
                },
                "category": "cable"
            },
            {
                "id": "cable_cu_xlpe_25mm2_4c",
                "data": {
                    "type": "XLPE_cable",
                    "size_mm2": 25.0,
                    "cores": 4,
                    "material": "copper",
                    "insulation": "XLPE",
                    "voltage_rating": 1000,
                    "current_rating": 76,
                    "resistance_ohm_per_km": 0.727,
                    "reactance_ohm_per_km": 0.058,
                    "cable_weight_kg_per_km": 580,
                    "outer_diameter_mm": 23.8,
                    "bending_radius_mm": 119,
                    "max_operating_temp_c": 90,
                    "short_circuit_rating_ka_1s": 7.2
                },
                "category": "cable"
            },
            {
                "id": "cable_al_pvc_50mm2_4c",
                "data": {
                    "type": "PVC_cable",
                    "size_mm2": 50.0,
                    "cores": 4,
                    "material": "aluminum",
                    "insulation": "PVC",
                    "voltage_rating": 1000,
                    "current_rating": 105,
                    "resistance_ohm_per_km": 0.641,
                    "reactance_ohm_per_km": 0.052,
                    "cable_weight_kg_per_km": 720,
                    "outer_diameter_mm": 30.2,
                    "bending_radius_mm": 151,
                    "max_operating_temp_c": 70,
                    "short_circuit_rating_ka_1s": 9.8
                },
                "category": "cable"
            },

            # Transformers
            {
                "id": "transformer_315kva_11kv_400v",
                "data": {
                    "type": "oil_immersed",
                    "rating_kva": 315,
                    "primary_voltage": 11000,
                    "secondary_voltage": 400,
                    "vector_group": "Dyn11",
                    "impedance_percent": 4.5,
                    "no_load_loss_kw": 1.8,
                    "full_load_loss_kw": 6.2,
                    "cooling_method": "ONAN",
                    "insulation_class": "A",
                    "temperature_rise_c": 55,
                    "total_weight_kg": 1850,
                    "oil_weight_kg": 280,
                    "efficiency_percent": 97.2
                },
                "category": "transformer"
            },
            {
                "id": "transformer_630kva_11kv_400v",
                "data": {
                    "type": "oil_immersed",
                    "rating_kva": 630,
                    "primary_voltage": 11000,
                    "secondary_voltage": 400,
                    "vector_group": "Dyn11",
                    "impedance_percent": 5.0,
                    "no_load_loss_kw": 2.8,
                    "full_load_loss_kw": 10.5,
                    "cooling_method": "ONAN",
                    "insulation_class": "A",
                    "temperature_rise_c": 55,
                    "total_weight_kg": 2450,
                    "oil_weight_kg": 380,
                    "efficiency_percent": 97.5
                },
                "category": "transformer"
            },
            {
                "id": "transformer_1000kva_11kv_400v",
                "data": {
                    "type": "oil_immersed",
                    "rating_kva": 1000,
                    "primary_voltage": 11000,
                    "secondary_voltage": 400,
                    "vector_group": "Dyn11",
                    "impedance_percent": 6.5,
                    "no_load_loss_kw": 4.2,
                    "full_load_loss_kw": 15.8,
                    "cooling_method": "ONAN",
                    "insulation_class": "A",
                    "temperature_rise_c": 55,
                    "total_weight_kg": 3200,
                    "oil_weight_kg": 520,
                    "efficiency_percent": 97.8
                },
                "category": "transformer"
            },

            # Circuit Breakers
            {
                "id": "mccb_125a_3p_25ka",
                "data": {
                    "type": "MCCB",
                    "rated_current_a": 125,
                    "poles": 3,
                    "breaking_capacity_ka": 25,
                    "voltage_rating": 690,
                    "tripping_characteristic": "C",
                    "magnetic_setting": "5-10In",
                    "thermal_setting": "0.8-1.0In",
                    "dimensions_mm": "150x110x90",
                    "weight_kg": 1.8,
                    "ip_rating": "IP40"
                },
                "category": "circuit_breaker"
            },
            {
                "id": "mccb_250a_3p_36ka",
                "data": {
                    "type": "MCCB",
                    "rated_current_a": 250,
                    "poles": 3,
                    "breaking_capacity_ka": 36,
                    "voltage_rating": 690,
                    "tripping_characteristic": "C",
                    "magnetic_setting": "5-10In",
                    "thermal_setting": "0.8-1.0In",
                    "dimensions_mm": "210x140x110",
                    "weight_kg": 3.2,
                    "ip_rating": "IP40"
                },
                "category": "circuit_breaker"
            },

            # Generators
            {
                "id": "generator_100kva_400v",
                "data": {
                    "type": "diesel_generator",
                    "rating_kva": 100,
                    "voltage": 400,
                    "phases": 3,
                    "power_factor": 0.8,
                    "frequency_hz": 50,
                    "speed_rpm": 1500,
                    "efficiency_percent": 85,
                    "fuel_consumption_l_per_h": 22,
                    "noise_level_db": 75,
                    "dimensions_mm": "2200x900x1400",
                    "weight_kg": 1250
                },
                "category": "generator"
            }
        ]

        for comp in common_components:
            self.store_component_specification(
                comp["id"],
                comp["data"],
                comp["category"]
            )

    def _initialize_common_design_patterns(self):
        """Initialize database with common design patterns"""
        design_patterns = [
            {
                "id": "industrial_motor_control",
                "data": {
                    "description": "Standard industrial motor control center with DOL starters",
                    "components": ["motors", "contactors", "circuit_breakers", "control_cables"],
                    "standards": ["IEC 60947", "IEC 60204"],
                    "industry": "industrial",
                    "efficiency_rating": 0.85,
                    "complexity": "medium"
                },
                "type": "power_distribution"
            },
            {
                "id": "commercial_lighting_system",
                "data": {
                    "description": "Commercial building lighting system with emergency backup",
                    "components": ["lighting_panels", "emergency_generators", "lighting_controls"],
                    "standards": ["IEC 60364", "BS 5266"],
                    "industry": "commercial",
                    "efficiency_rating": 0.90,
                    "complexity": "low"
                },
                "type": "lighting_system"
            },
            {
                "id": "vfd_motor_control_system",
                "data": {
                    "description": "Variable frequency drive system for motor speed control and energy efficiency",
                    "components": ["motors", "vfds", "harmonic_filters", "control_panels", "braking_resistors"],
                    "standards": ["IEC 61800", "IEC 61000"],
                    "industry": "industrial",
                    "efficiency_rating": 0.92,
                    "complexity": "high"
                },
                "type": "motor_control"
            },
            {
                "id": "emergency_power_system",
                "data": {
                    "description": "Emergency power system with automatic transfer switches and generator backup",
                    "components": ["generators", "ats", "emergency_panels", "battery_backup"],
                    "standards": ["IEC 60364", "NFPA 110"],
                    "industry": "commercial",
                    "efficiency_rating": 0.88,
                    "complexity": "high"
                },
                "type": "emergency_power"
            },
            {
                "id": "data_center_power",
                "data": {
                    "description": "Redundant power system for data centers with dual feeds and UPS systems",
                    "components": ["transformers", "ups", "switchgear", "redundant_feeders"],
                    "standards": ["IEC 60364", "EN 50173"],
                    "industry": "data_center",
                    "efficiency_rating": 0.95,
                    "complexity": "very_high"
                },
                "type": "critical_power"
            },
            {
                "id": "solar_pv_system",
                "data": {
                    "description": "Grid-tied solar photovoltaic system with inverters and monitoring",
                    "components": ["solar_panels", "inverters", "monitoring_system", "grid_connection"],
                    "standards": ["IEC 61215", "IEC 61727"],
                    "industry": "renewable_energy",
                    "efficiency_rating": 0.85,
                    "complexity": "medium"
                },
                "type": "renewable_energy"
            },
            {
                "id": "process_control_system",
                "data": {
                    "description": "Industrial process control system with PLC and instrumentation",
                    "components": ["plc", "sensors", "actuators", "control_panels", "instrumentation"],
                    "standards": ["IEC 61131", "IEC 60654"],
                    "industry": "process_industry",
                    "efficiency_rating": 0.90,
                    "complexity": "high"
                },
                "type": "process_control"
            },
            {
                "id": "building_automation",
                "data": {
                    "description": "Building automation system integrating HVAC, lighting, and security",
                    "components": ["hvac_controls", "lighting_controls", "security_system", "building_management"],
                    "standards": ["BACnet", "IEC 61850"],
                    "industry": "building_automation",
                    "efficiency_rating": 0.88,
                    "complexity": "medium"
                },
                "type": "automation"
            }
        ]

        for pattern in design_patterns:
            self.store_design_pattern(
                pattern["id"],
                pattern["data"],
                pattern["type"]
            )

    def _initialize_standards_rules(self):
        """Initialize database with common standards compliance rules"""
        standards_rules = [
            {
                "id": "iec_60364_cable_sizing",
                "data": {
                    "title": "Cable Sizing Requirements",
                    "description": "Cable sizing shall consider current carrying capacity, voltage drop, and short circuit withstand",
                    "requirements": "Current rating ≥ design current, Voltage drop ≤ 5%, Short circuit rating adequate",
                    "category": "cable_sizing",
                    "applies_to": ["cables", "conductors"],
                    "severity": "high",
                    "reference": "IEC 60364-5-52"
                },
                "standard": "IEC"
            },
            {
                "id": "iec_60364_earthing",
                "data": {
                    "title": "Protective Earthing Requirements",
                    "description": "All exposed conductive parts shall be connected to protective earth",
                    "requirements": "RCD protection ≤ 32A circuits, Earth resistance ≤ 1 ohm, Equipotential bonding",
                    "category": "earthing",
                    "applies_to": ["earthing", "bonding"],
                    "severity": "critical",
                    "reference": "IEC 60364-4-41"
                },
                "standard": "IEC"
            },
            {
                "id": "iec_60947_motor_protection",
                "data": {
                    "title": "Motor Protection Requirements",
                    "description": "Motors above 0.37kW shall have overload protection and short-circuit protection",
                    "requirements": "Thermal overload relay or electronic protection, Short-circuit protection within 5 cycles",
                    "category": "motor_protection",
                    "applies_to": ["motors", "protection_devices"],
                    "severity": "high",
                    "reference": "IEC 60947-4-1"
                },
                "standard": "IEC"
            },
            {
                "id": "iec_60204_emergency_stop",
                "data": {
                    "title": "Emergency Stop Requirements",
                    "description": "Emergency stop devices shall be available at all operator stations",
                    "requirements": "Red mushroom head pushbutton, Direct opening contacts, Unlatchable from stop position",
                    "category": "safety",
                    "applies_to": ["emergency_stops", "safety_devices"],
                    "severity": "critical",
                    "reference": "IEC 60204-1"
                },
                "standard": "IEC"
            },
            {
                "id": "iec_60364_voltage_drop",
                "data": {
                    "title": "Voltage Drop Limits",
                    "description": "Voltage drop in final circuits shall not exceed 5%",
                    "requirements": "Lighting circuits: ≤3%, Other circuits: ≤5%, Total from origin: ≤8%",
                    "category": "voltage_drop",
                    "applies_to": ["cables", "circuits"],
                    "severity": "medium",
                    "reference": "IEC 60364-5-52"
                },
                "standard": "IEC"
            },
            {
                "id": "iec_61439_switchgear",
                "data": {
                    "title": "Switchgear and Controlgear Requirements",
                    "description": "Assemblies shall be designed for intended use and normal service conditions",
                    "requirements": "Temperature rise limits, Short-circuit withstand, IP rating maintenance",
                    "category": "switchgear",
                    "applies_to": ["switchgear", "panels", "controlgear"],
                    "severity": "high",
                    "reference": "IEC 61439-1"
                },
                "standard": "IEC"
            },
            {
                "id": "iec_61000_emc",
                "data": {
                    "title": "Electromagnetic Compatibility",
                    "description": "Equipment shall not generate electromagnetic disturbances exceeding defined levels",
                    "requirements": "Emission limits, Immunity requirements, Harmonics compliance",
                    "category": "emc",
                    "applies_to": ["electronic_equipment", "variable_speed_drives"],
                    "severity": "medium",
                    "reference": "IEC 61000-6-2"
                },
                "standard": "IEC"
            },
            {
                "id": "nec_250_grounding",
                "data": {
                    "title": "Grounding Electrode System",
                    "description": "Building shall be grounded using approved grounding electrodes",
                    "requirements": "Ground rod minimum 8ft, Multiple electrodes connected, Ground resistance ≤25 ohms",
                    "category": "grounding",
                    "applies_to": ["grounding", "earthing"],
                    "severity": "critical",
                    "reference": "NEC 250.53"
                },
                "standard": "NEC"
            },
            {
                "id": "nec_430_motor_calculations",
                "data": {
                    "title": "Motor Circuit Calculations",
                    "description": "Branch circuit conductors shall have ampacity not less than motor FLC × 125%",
                    "requirements": "Feeder conductors: motor FLC × 125%, Short-circuit protection: motor FLC × 250%",
                    "category": "motor_circuits",
                    "applies_to": ["motors", "cables", "protection"],
                    "severity": "high",
                    "reference": "NEC 430.22"
                },
                "standard": "NEC"
            }
        ]

        for rule in standards_rules:
            self.store_standards_rule(
                rule["id"],
                rule["data"],
                rule["standard"]
            )

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about all collections"""
        stats = {}
        try:
            for collection_type, collection_name in self.collections.items():
                try:
                    collection = self.client.get_collection(collection_name)
                    count = collection.count()
                    stats[collection_type] = {
                        "count": count,
                        "collection_name": collection_name
                    }
                except Exception as e:
                    stats[collection_type] = {
                        "error": str(e),
                        "collection_name": collection_name
                    }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")

        return stats

    def clear_collection(self, collection_type: str):
        """Clear all data from a collection"""
        try:
            collection = self._get_collection(collection_type)
            # ChromaDB doesn't have a direct clear method, recreate collection
            self.client.delete_collection(collection.name)
            self.client.get_or_create_collection(
                name=collection.name,
                metadata={"description": f"Collection for {collection.name}"}
            )
            logger.info(f"Cleared collection: {collection_type}")
        except Exception as e:
            logger.error(f"Failed to clear collection {collection_type}: {e}")

    def backup_database(self, backup_path: str):
        """Backup the vector database to a compressed archive"""
        try:
            if os.path.exists(self.persist_directory):
                # Create backup archive
                shutil.make_archive(backup_path, 'zip', self.persist_directory)
                logger.info(f"Database backed up to: {backup_path}.zip")
                return True
            else:
                logger.warning(f"No database found at: {self.persist_directory}")
                return False
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            return False

    def restore_database(self, backup_path: str):
        """Restore the vector database from a backup archive"""
        try:
            if os.path.exists(f"{backup_path}.zip"):
                # Clear current database
                if os.path.exists(self.persist_directory):
                    shutil.rmtree(self.persist_directory)

                # Extract backup
                shutil.unpack_archive(f"{backup_path}.zip", self.persist_directory)
                logger.info(f"Database restored from: {backup_path}.zip")

                # Reinitialize client connection
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )

                return True
            else:
                logger.error(f"Backup file not found: {backup_path}.zip")
                return False
        except Exception as e:
            logger.error(f"Failed to restore database: {e}")
            return False

    def _load_cache_from_disk(self):
        """Load caches from disk persistence"""
        try:
            cache_file = os.path.join(self.persist_directory, "cache_data.json")
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                self.query_cache = cache_data.get('query_cache', {})
                self.embedding_cache = cache_data.get('embedding_cache', {})
                self.cache_timestamps = cache_data.get('cache_timestamps', {})

                # Clean expired cache entries
                current_time = time.time()
                expired_keys = [
                    key for key, timestamp in self.cache_timestamps.items()
                    if current_time - timestamp > self.cache_ttl
                ]

                for key in expired_keys:
                    self.query_cache.pop(key, None)
                    self.embedding_cache.pop(key, None)
                    self.cache_timestamps.pop(key, None)

                logger.info(f"Loaded cache with {len(self.query_cache)} query entries and {len(self.embedding_cache)} embedding entries")
        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")

    def _save_cache_to_disk(self):
        """Persist caches to disk"""
        if not self.persistence_enabled:
            return

        try:
            cache_file = os.path.join(self.persist_directory, "cache_data.json")
            cache_data = {
                'query_cache': self.query_cache,
                'embedding_cache': self.embedding_cache,
                'cache_timestamps': self.cache_timestamps,
                'timestamp': datetime.now().isoformat()
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)

            logger.debug("Cache persisted to disk")
        except Exception as e:
            logger.warning(f"Failed to save cache to disk: {e}")

    def _auto_save_cache(self):
        """Auto-save cache if interval has passed"""
        current_time = time.time()
        if current_time - self.last_save_time > self.auto_save_interval:
            self._save_cache_to_disk()
            self.last_save_time = current_time

    def _get_cache_key(self, query: str, params: Dict = None) -> str:
        """Generate cache key for query with parameters"""
        key_parts = [query]
        if params:
            # Sort parameters for consistent key generation
            sorted_params = sorted(params.items())
            key_parts.extend([f"{k}:{v}" for k, v in sorted_params])

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()

    def _get_cached_query_result(self, cache_key: str) -> Optional[Any]:
        """Get cached query result if valid"""
        if cache_key in self.query_cache:
            timestamp = self.cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.cache_ttl:
                return self.query_cache[cache_key]
            else:
                # Remove expired entry
                self.query_cache.pop(cache_key, None)
                self.cache_timestamps.pop(cache_key, None)
        return None

    def _cache_query_result(self, cache_key: str, result: Any):
        """Cache query result"""
        current_time = time.time()

        self.query_cache[cache_key] = result
        self.cache_timestamps[cache_key] = current_time

        # Enforce cache size limits
        if len(self.query_cache) > self.cache_max_size:
            # Remove oldest entries
            sorted_entries = sorted(self.cache_timestamps.items(), key=lambda x: x[1])
            entries_to_remove = sorted_entries[:len(sorted_entries) - self.cache_max_size]

            for key, _ in entries_to_remove:
                self.query_cache.pop(key, None)
                self.cache_timestamps.pop(key, None)

        self._auto_save_cache()

    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding if available"""
        cache_key = self._get_cache_key(text)
        if cache_key in self.embedding_cache:
            timestamp = self.cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.cache_ttl:
                return self.embedding_cache[cache_key]
            else:
                # Remove expired entry
                self.embedding_cache.pop(cache_key, None)
                self.cache_timestamps.pop(cache_key, None)
        return None

    def _cache_embedding(self, text: str, embedding: List[float]):
        """Cache embedding"""
        cache_key = self._get_cache_key(text)
        current_time = time.time()

        self.embedding_cache[cache_key] = embedding
        self.cache_timestamps[cache_key] = current_time

        # Enforce cache size limits
        if len(self.embedding_cache) > self.cache_max_size:
            # Remove oldest entries
            sorted_entries = sorted(self.cache_timestamps.items(), key=lambda x: x[1])
            entries_to_remove = sorted_entries[:len(sorted_entries) - self.cache_max_size]

            for key, _ in entries_to_remove:
                self.embedding_cache.pop(key, None)
                self.cache_timestamps.pop(key, None)

        self._auto_save_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        current_time = time.time()
        valid_query_entries = sum(1 for ts in self.cache_timestamps.values()
                                 if current_time - ts < self.cache_ttl)

        return {
            "query_cache_size": len(self.query_cache),
            "embedding_cache_size": len(self.embedding_cache),
            "valid_cache_entries": valid_query_entries,
            "cache_max_size": self.cache_max_size,
            "cache_ttl_seconds": self.cache_ttl,
            "auto_save_interval": self.auto_save_interval,
            "persistence_enabled": self.persistence_enabled
        }

    def clear_cache(self, cache_type: str = "all"):
        """Clear specified cache"""
        if cache_type in ["all", "query"]:
            self.query_cache.clear()
        if cache_type in ["all", "embedding"]:
            self.embedding_cache.clear()

        # Clear timestamps for cleared caches
        if cache_type == "all":
            self.cache_timestamps.clear()
        else:
            # Remove timestamps for cleared cache type
            keys_to_remove = [k for k in self.cache_timestamps.keys()
                            if (cache_type == "query" and k in self.query_cache) or
                               (cache_type == "embedding" and k in self.embedding_cache)]
            for key in keys_to_remove:
                self.cache_timestamps.pop(key, None)

        self._save_cache_to_disk()
        logger.info(f"Cleared {cache_type} cache")

    def store_excel_header_mapping(self, header: str, field: str, confidence: float,
                                  context: str = "", project_id: str = ""):
        """
        Store Excel header to field mapping for future reference.

        Args:
            header: Excel column header text
            field: Mapped data model field name
            confidence: Confidence score for the mapping
            context: Additional context about the mapping
            project_id: Project identifier
        """
        try:
            collection = self._get_collection('excel_headers')

            # Create searchable document
            document_parts = [
                f"Header: {header}",
                f"Field: {field}",
                f"Context: {context}",
                f"Project: {project_id}"
            ]

            document = " | ".join(document_parts)

            # Prepare metadata
            metadata = {
                "header": header,
                "field": field,
                "confidence": confidence,
                "similarity_score": confidence,  # For compatibility
                "context": context,
                "project_id": project_id,
                "timestamp": datetime.now().isoformat()
            }

            # Store in vector database
            collection.add(
                embeddings=[self._get_embedding(document)],
                documents=[document],
                metadatas=[metadata],
                ids=[f"header_{header.lower().replace(' ', '_')}_{int(datetime.now().timestamp())}"]
            )

            logger.debug(f"Stored Excel header mapping: '{header}' -> '{field}'")

        except Exception as e:
            logger.error(f"Failed to store Excel header mapping: {e}")

    def retrieve_excel_header_mappings(self, header_text: str, context: str = "",
                                      top_k: int = 5) -> List[Dict]:
        """
        Retrieve similar Excel header mappings.

        Args:
            header_text: Header text to search for
            context: Additional context
            top_k: Number of results to return

        Returns:
            List of similar header mappings
        """
        try:
            collection = self._get_collection('excel_headers')

            # Create search query
            search_query = f"{header_text} {context}"

            results = collection.query(
                query_embeddings=[self._get_embedding(search_query)],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )

            # Format results
            mappings = []
            if results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i]

                    mappings.append({
                        "header": metadata.get("header", ""),
                        "field": metadata.get("field", ""),
                        "confidence": metadata.get("confidence", 0.0),
                        "similarity_score": 1.0 - distance,
                        "context": metadata.get("context", ""),
                        "project_id": metadata.get("project_id", ""),
                        "timestamp": metadata.get("timestamp", "")
                    })

            return mappings

        except Exception as e:
            logger.error(f"Failed to retrieve Excel header mappings: {e}")
            return []

    def optimize_cache(self):
        """Optimize cache by removing expired entries and compacting"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if current_time - timestamp > self.cache_ttl
        ]

        for key in expired_keys:
            self.query_cache.pop(key, None)
            self.embedding_cache.pop(key, None)
            self.cache_timestamps.pop(key, None)

        # Force save after optimization
        self._save_cache_to_disk()

        logger.info(f"Cache optimized: removed {len(expired_keys)} expired entries")

    def enable_persistence(self, enabled: bool = True):
        """Enable or disable cache persistence"""
        self.persistence_enabled = enabled
        if enabled:
            self._save_cache_to_disk()
        logger.info(f"Cache persistence {'enabled' if enabled else 'disabled'}")

    def set_cache_ttl(self, ttl_seconds: int):
        """Set cache TTL in seconds"""
        self.cache_ttl = ttl_seconds
        logger.info(f"Cache TTL set to {ttl_seconds} seconds")

    def set_cache_size(self, max_size: int):
        """Set maximum cache size"""
        self.cache_max_size = max_size
        logger.info(f"Cache max size set to {max_size}")

    def warmup_cache(self, common_queries: List[str] = None):
        """Warm up cache with common queries"""
        if common_queries is None:
            common_queries = [
                "motor", "cable", "transformer", "bus", "breaker",
                "voltage drop", "current rating", "power factor",
                "cable sizing", "motor protection", "earthing"
            ]

        logger.info("Warming up cache with common queries...")

        for query in common_queries:
            try:
                # Pre-compute embeddings for common terms
                embedding = self._get_embedding(query)
                if embedding:
                    self._cache_embedding(query, embedding)

                # Pre-run common searches
                self.search_components(query, top_k=1)
                self.find_similar_designs(query, top_k=1)
                self.search_standards(query, top_k=1)

            except Exception as e:
                logger.debug(f"Failed to warmup cache for query '{query}': {e}")

        logger.info("Cache warmup completed")


# Global instance for application use
_vector_db_instance = None

def get_vector_database(persist_directory: str = "./vector_db") -> VectorDatabaseManager:
    """Get global vector database instance (singleton pattern)"""
    global _vector_db_instance
    if _vector_db_instance is None:
        _vector_db_instance = VectorDatabaseManager(persist_directory)
    return _vector_db_instance


if __name__ == "__main__":
    # Example usage
    db = VectorDatabaseManager()

    # Initialize with default knowledge
    db.initialize_default_knowledge_base()

    # Test component search
    results = db.search_components("15kW induction motor 400V")
    print(f"Found {len(results)} matching components")

    # Test design pattern search
    patterns = db.find_similar_designs("industrial motor control system")
    print(f"Found {len(patterns)} similar design patterns")

    # Test RAG query
    rag_result = db.rag_query("What cable size for 45A motor circuit?")
    print(f"RAG context length: {rag_result['context_length']}")
    print(f"Number of sources: {rag_result['num_sources']}")

    # Show stats
    stats = db.get_collection_stats()
    for collection_type, info in stats.items():
        print(f"{collection_type}: {info.get('count', 0)} items")