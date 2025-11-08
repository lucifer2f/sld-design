"""
Embedding Generation Pipeline for Vector Database

This module implements a comprehensive pipeline for generating and managing embeddings
for electrical engineering knowledge base, including batch processing, incremental updates,
and performance optimization features.
"""

import pandas as pd
import numpy as np
import logging
import json
import os
import time
from typing import Dict, List, Optional, Any, Tuple, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# Vector database integration
try:
    from .vector_database_manager import get_vector_database, VectorDatabaseManager
    VECTOR_DB_AVAILABLE = True
except ImportError:
    VECTOR_DB_AVAILABLE = False
    logging.warning("Vector database not available for embedding pipeline")

# Sentence transformers for embedding generation - REMOVED as not used elsewhere
# ChromaDB handles its own embeddings internally

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("Sentence transformers not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmbeddingBatch:
    """Container for batch embedding generation results"""
    texts: List[str]
    embeddings: np.ndarray
    metadata: List[Dict[str, Any]]
    batch_id: str
    generation_time: float
    model_name: str


@dataclass
class ProcessingStats:
    """Statistics for embedding generation pipeline"""
    total_texts_processed: int = 0
    total_batches: int = 0
    total_processing_time: float = 0.0
    average_batch_time: float = 0.0
    failed_batches: int = 0
    cached_embeddings_used: int = 0
    new_embeddings_generated: int = 0


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation pipeline"""
    model_name: str = "all-MiniLM-L6-v2"
    batch_size: int = 32
    max_workers: int = 4
    cache_embeddings: bool = True
    enable_incremental_updates: bool = True
    similarity_threshold: float = 0.95
    max_sequence_length: int = 512
    normalize_embeddings: bool = True


class EmbeddingCache:
    """
    LRU cache for embedding vectors with persistence
    """

    def __init__(self, cache_file: str = "./embedding_cache.json", max_size: int = 10000):
        self.cache_file = cache_file
        self.max_size = max_size
        self.cache = {}
        self.access_order = []
        self._lock = threading.Lock()

        # Load existing cache
        self._load_cache()

    def _load_cache(self):
        """Load cache from disk"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache = data.get('cache', {})
                    self.access_order = data.get('access_order', [])
                logger.info(f"Loaded {len(self.cache)} cached embeddings")
        except Exception as e:
            logger.warning(f"Failed to load embedding cache: {e}")

    def _save_cache(self):
        """Save cache to disk"""
        try:
            data = {
                'cache': self.cache,
                'access_order': self.access_order,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")

    def get(self, text: str) -> Optional[np.ndarray]:
        """Get cached embedding for text"""
        with self._lock:
            text_hash = self._get_text_hash(text)
            if text_hash in self.cache:
                # Update access order
                if text_hash in self.access_order:
                    self.access_order.remove(text_hash)
                self.access_order.append(text_hash)

                # Convert back to numpy array
                return np.array(self.cache[text_hash])
            return None

    def put(self, text: str, embedding: np.ndarray):
        """Cache embedding for text"""
        with self._lock:
            text_hash = self._get_text_hash(text)

            # Remove old entry if exists
            if text_hash in self.cache:
                self.access_order.remove(text_hash)

            # Add new entry
            self.cache[text_hash] = embedding.tolist()
            self.access_order.append(text_hash)

            # Enforce max size
            while len(self.cache) > self.max_size:
                oldest = self.access_order.pop(0)
                del self.cache[oldest]

            # Save periodically
            if len(self.cache) % 100 == 0:
                self._save_cache()

    def _get_text_hash(self, text: str) -> str:
        """Generate hash for text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def clear(self):
        """Clear cache"""
        with self._lock:
            self.cache.clear()
            self.access_order.clear()
            self._save_cache()


class EmbeddingGenerator:
    """
    Core embedding generation engine with batch processing and caching
    """

    def __init__(self, config: EmbeddingConfig = None):
        self.config = config or EmbeddingConfig()
        self.model = None
        self.cache = EmbeddingCache()
        self.stats = ProcessingStats()
        self._lock = threading.Lock()

        # Initialize model
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the sentence transformer model"""
        if not EMBEDDINGS_AVAILABLE:
            raise ImportError("Sentence transformers not available")

        try:
            logger.info(f"Loading embedding model: {self.config.model_name}")
            self.model = SentenceTransformer(self.config.model_name)

            # Configure model
            if hasattr(self.model, 'max_seq_length'):
                self.model.max_seq_length = self.config.max_sequence_length

            logger.info("Embedding model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str], metadata: List[Dict[str, Any]] = None) -> EmbeddingBatch:
        """
        Generate embeddings for a batch of texts

        Args:
            texts: List of texts to embed
            metadata: Optional metadata for each text

        Returns:
            EmbeddingBatch with results
        """
        if not self.model:
            raise RuntimeError("Model not initialized")

        start_time = time.time()
        batch_id = f"batch_{int(time.time() * 1000)}"

        # Prepare metadata
        if metadata is None:
            metadata = [{} for _ in texts]

        # Check cache for existing embeddings
        cached_embeddings = []
        new_texts = []
        new_metadata = []
        text_indices = []

        for i, (text, meta) in enumerate(zip(texts, metadata)):
            cached = self.cache.get(text) if self.config.cache_embeddings else None
            if cached is not None:
                cached_embeddings.append((i, cached))
                self.stats.cached_embeddings_used += 1
            else:
                new_texts.append(text)
                new_metadata.append(meta)
                text_indices.append(i)

        # Generate new embeddings
        new_embeddings = []
        if new_texts:
            try:
                logger.debug(f"Generating embeddings for {len(new_texts)} new texts")

                # Generate embeddings in batches
                embeddings_list = []
                for i in range(0, len(new_texts), self.config.batch_size):
                    batch_texts = new_texts[i:i + self.config.batch_size]
                    batch_embeddings = self.model.encode(
                        batch_texts,
                        normalize_embeddings=self.config.normalize_embeddings,
                        show_progress_bar=False
                    )
                    embeddings_list.append(batch_embeddings)

                new_embeddings_array = np.vstack(embeddings_list)

                # Cache new embeddings
                for text, embedding in zip(new_texts, new_embeddings_array):
                    self.cache.put(text, embedding)
                    self.stats.new_embeddings_generated += 1

                new_embeddings = list(new_embeddings_array)

            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
                raise

        # Combine cached and new embeddings
        all_embeddings = [None] * len(texts)
        for idx, embedding in cached_embeddings:
            all_embeddings[idx] = embedding

        for new_idx, embedding in enumerate(new_embeddings):
            original_idx = text_indices[new_idx]
            all_embeddings[original_idx] = embedding

        # Convert to numpy array
        embeddings_array = np.array(all_embeddings)

        generation_time = time.time() - start_time

        # Update stats
        with self._lock:
            self.stats.total_texts_processed += len(texts)
            self.stats.total_batches += 1
            self.stats.total_processing_time += generation_time
            self.stats.average_batch_time = self.stats.total_processing_time / self.stats.total_batches

        batch = EmbeddingBatch(
            texts=texts,
            embeddings=embeddings_array,
            metadata=metadata,
            batch_id=batch_id,
            generation_time=generation_time,
            model_name=self.config.model_name
        )

        logger.debug(f"Generated batch {batch_id}: {len(texts)} texts in {generation_time:.2f}s")
        return batch

    def generate_embeddings_streaming(self, text_iterator: Iterator[Tuple[str, Dict[str, Any]]],
                                    batch_size: int = None) -> Iterator[EmbeddingBatch]:
        """
        Generate embeddings for streaming text input

        Args:
            text_iterator: Iterator yielding (text, metadata) tuples
            batch_size: Override batch size

        Yields:
            EmbeddingBatch objects
        """
        batch_texts = []
        batch_metadata = []

        effective_batch_size = batch_size or self.config.batch_size

        for text, metadata in text_iterator:
            batch_texts.append(text)
            batch_metadata.append(metadata)

            if len(batch_texts) >= effective_batch_size:
                yield self.generate_embeddings_batch(batch_texts, batch_metadata)
                batch_texts = []
                batch_metadata = []

        # Yield remaining texts
        if batch_texts:
            yield self.generate_embeddings_batch(batch_texts, batch_metadata)


class ElectricalEngineeringDataLoader:
    """
    Specialized data loader for electrical engineering content
    """

    def __init__(self):
        self.data_sources = {
            'standards': self._load_standards_data,
            'components': self._load_component_data,
            'patterns': self._load_pattern_data,
            'specifications': self._load_specification_data
        }

    def load_data_source(self, source_name: str) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """
        Load data from a specific source

        Args:
            source_name: Name of data source

        Yields:
            (text, metadata) tuples for embedding generation
        """
        if source_name not in self.data_sources:
            raise ValueError(f"Unknown data source: {source_name}")

        loader_func = self.data_sources[source_name]
        yield from loader_func()

    def _load_standards_data(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """Load electrical standards and regulations"""
        standards = [
            ("IEC 60364 Low Voltage Electrical Installations", {
                "type": "standard", "code": "IEC_60364", "category": "installation",
                "description": "Low voltage electrical installations design and safety requirements"
            }),
            ("NEC National Electrical Code", {
                "type": "standard", "code": "NEC", "category": "safety",
                "description": "US National Electrical Code for electrical installations"
            }),
            ("IEEE 141 Recommended Practice for Electric Power Distribution", {
                "type": "standard", "code": "IEEE_141", "category": "distribution",
                "description": "Recommended practices for electric power distribution systems"
            }),
            ("BS 7671 Requirements for Electrical Installations", {
                "type": "standard", "code": "BS_7671", "category": "installation",
                "description": "UK electrical installation requirements and guidance"
            })
        ]

        for text, metadata in standards:
            yield text, metadata

    def _load_component_data(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """Load electrical component specifications"""
        components = [
            ("Power transformer 1000kVA 11kV to 400V", {
                "type": "component", "category": "transformer",
                "rating": "1000kVA", "voltage": "11kV/400V"
            }),
            ("Circuit breaker MCCB 630A 400V 3P", {
                "type": "component", "category": "breaker",
                "rating": "630A", "voltage": "400V", "poles": "3P"
            }),
            ("Cable XLPE 4x240mm2 copper armored", {
                "type": "component", "category": "cable",
                "type": "XLPE", "cores": "4", "size": "240mm2", "conductor": "copper"
            })
        ]

        for text, metadata in components:
            yield text, metadata

    def _load_pattern_data(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """Load design patterns and best practices"""
        patterns = [
            ("Motor starter circuit with overload protection", {
                "type": "pattern", "category": "motor_control",
                "description": "Standard motor starting and protection circuit"
            }),
            ("Distribution board radial feeder system", {
                "type": "pattern", "category": "distribution",
                "description": "Radial distribution system from main switchboard"
            })
        ]

        for text, metadata in patterns:
            yield text, metadata

    def _load_specification_data(self) -> Iterator[Tuple[str, Dict[str, Any]]]:
        """Load technical specifications"""
        specs = [
            ("Voltage drop limit 5% for lighting circuits", {
                "type": "specification", "category": "voltage_drop",
                "limit": "5%", "application": "lighting"
            }),
            ("Cable derating factor 0.8 for grouping", {
                "type": "specification", "category": "cable_rating",
                "factor": "0.8", "condition": "grouping"
            })
        ]

        for text, metadata in specs:
            yield text, metadata


class EmbeddingGenerationPipeline:
    """
    Complete pipeline for generating and managing embeddings for electrical engineering knowledge
    """

    def __init__(self, config: EmbeddingConfig = None, vector_db_path: str = "./vector_db"):
        self.config = config or EmbeddingConfig()
        self.vector_db_path = vector_db_path
        self.generator = EmbeddingGenerator(self.config)
        self.data_loader = ElectricalEngineeringDataLoader()
        self.vector_db = None

        if VECTOR_DB_AVAILABLE:
            try:
                self.vector_db = get_vector_database(vector_db_path)
                logger.info("Vector database initialized for embedding pipeline")
            except Exception as e:
                logger.warning(f"Vector database initialization failed: {e}")

        self.stats = ProcessingStats()

    def process_data_source(self, source_name: str, collection_name: str = None) -> ProcessingStats:
        """
        Process a complete data source and store embeddings

        Args:
            source_name: Name of data source to process
            collection_name: Optional collection name for vector storage

        Returns:
            Processing statistics
        """
        logger.info(f"Processing data source: {source_name}")

        # Get data iterator
        data_iterator = self.data_loader.load_data_source(source_name)

        # Process in batches
        total_processed = 0
        for batch in self.generator.generate_embeddings_streaming(data_iterator):
            total_processed += len(batch.texts)

            # Store in vector database if available
            if self.vector_db and collection_name:
                try:
                    self._store_batch_in_vector_db(batch, collection_name)
                except Exception as e:
                    logger.warning(f"Failed to store batch in vector database: {e}")

        # Update overall stats
        self.stats.total_texts_processed += self.generator.stats.total_texts_processed
        self.stats.total_batches += self.generator.stats.total_batches
        self.stats.total_processing_time += self.generator.stats.total_processing_time

        logger.info(f"Processed {total_processed} texts from {source_name}")
        return self.generator.stats

    def process_excel_headers(self, excel_files: List[str], collection_name: str = "excel_headers") -> ProcessingStats:
        """
        Process Excel column headers for learning

        Args:
            excel_files: List of Excel file paths
            collection_name: Collection name for storage

        Returns:
            Processing statistics
        """
        logger.info(f"Processing Excel headers from {len(excel_files)} files")

        headers_texts = []
        headers_metadata = []

        for file_path in excel_files:
            try:
                # Read Excel file
                excel_data = pd.read_excel(file_path, sheet_name=None, nrows=1)

                for sheet_name, df in excel_data.items():
                    for col in df.columns:
                        headers_texts.append(str(col))
                        headers_metadata.append({
                            "type": "excel_header",
                            "file": os.path.basename(file_path),
                            "sheet": sheet_name,
                            "source": "excel_extraction"
                        })

            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")

        # Generate embeddings for headers
        if headers_texts:
            batch = self.generator.generate_embeddings_batch(headers_texts, headers_metadata)

            # Store in vector database
            if self.vector_db:
                try:
                    self._store_batch_in_vector_db(batch, collection_name)
                except Exception as e:
                    logger.warning(f"Failed to store Excel headers in vector database: {e}")

        logger.info(f"Processed {len(headers_texts)} Excel headers")
        return self.generator.stats

    def incremental_update(self, new_texts: List[str], collection_name: str,
                         similarity_threshold: float = None) -> ProcessingStats:
        """
        Perform incremental update with deduplication

        Args:
            new_texts: New texts to process
            collection_name: Collection for storage
            similarity_threshold: Threshold for considering texts as duplicates

        Returns:
            Processing statistics
        """
        threshold = similarity_threshold or self.config.similarity_threshold
        logger.info(f"Performing incremental update for {len(new_texts)} texts")

        # Filter out similar existing texts (simplified - in practice would use vector similarity)
        filtered_texts = []
        filtered_metadata = []

        for text in new_texts:
            # Simple deduplication - check exact matches and cache
            if not self.generator.cache.get(text):
                filtered_texts.append(text)
                filtered_metadata.append({
                    "type": "incremental",
                    "timestamp": datetime.now().isoformat(),
                    "source": "incremental_update"
                })

        if filtered_texts:
            batch = self.generator.generate_embeddings_batch(filtered_texts, filtered_metadata)

            if self.vector_db:
                try:
                    self._store_batch_in_vector_db(batch, collection_name)
                except Exception as e:
                    logger.warning(f"Failed to store incremental update: {e}")

        logger.info(f"Incremental update: {len(filtered_texts)} new texts processed")
        return self.generator.stats

    def _store_batch_in_vector_db(self, batch: EmbeddingBatch, collection_name: str):
        """
        Store embedding batch in vector database

        Args:
            batch: Embedding batch to store
            collection_name: Target collection name
        """
        if not self.vector_db:
            return

        # Convert batch to vector database format
        for text, embedding, metadata in zip(batch.texts, batch.embeddings, batch.metadata):
            try:
                # Store based on collection type
                if collection_name == "standards":
                    self.vector_db.store_standards_rule(
                        rule_text=text,
                        rule_type=metadata.get("category", "general"),
                        standard_code=metadata.get("code", "unknown"),
                        metadata=metadata
                    )
                elif collection_name == "components":
                    self.vector_db.store_component_spec(
                        component_text=text,
                        component_type=metadata.get("category", "general"),
                        specifications=metadata
                    )
                elif collection_name == "patterns":
                    self.vector_db.store_design_pattern(
                        pattern_text=text,
                        pattern_type=metadata.get("category", "general"),
                        metadata=metadata
                    )
                elif collection_name == "excel_headers":
                    # Store as general knowledge for now
                    self.vector_db.store_component_spec(
                        component_text=text,
                        component_type="excel_header",
                        specifications=metadata
                    )
                else:
                    # Default storage
                    self.vector_db.store_component_spec(
                        component_text=text,
                        component_type="general",
                        specifications=metadata
                    )

            except Exception as e:
                logger.debug(f"Failed to store individual item in vector DB: {e}")

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        return {
            "generator_stats": {
                "total_texts_processed": self.generator.stats.total_texts_processed,
                "total_batches": self.generator.stats.total_batches,
                "total_processing_time": self.generator.stats.total_processing_time,
                "average_batch_time": self.generator.stats.average_batch_time,
                "cached_embeddings_used": self.generator.stats.cached_embeddings_used,
                "new_embeddings_generated": self.generator.stats.new_embeddings_generated,
                "failed_batches": self.generator.stats.failed_batches
            },
            "pipeline_config": {
                "model_name": self.config.model_name,
                "batch_size": self.config.batch_size,
                "max_workers": self.config.max_workers,
                "cache_embeddings": self.config.cache_embeddings,
                "normalize_embeddings": self.config.normalize_embeddings
            },
            "vector_db_available": self.vector_db is not None,
            "embeddings_available": EMBEDDINGS_AVAILABLE
        }


def run_embedding_pipeline_demo():
    """
    Demo function showing how to use the embedding generation pipeline
    """
    if not EMBEDDINGS_AVAILABLE:
        print("Sentence transformers not available. Cannot run embedding pipeline demo.")
        return

    print("Initializing Embedding Generation Pipeline...")

    # Create pipeline
    config = EmbeddingConfig(
        model_name="all-MiniLM-L6-v2",
        batch_size=16,
        cache_embeddings=True
    )

    pipeline = EmbeddingGenerationPipeline(config)

    print("Processing electrical standards...")
    stats1 = pipeline.process_data_source("standards", "standards")

    print("Processing component data...")
    stats2 = pipeline.process_data_source("components", "components")

    print("Processing design patterns...")
    stats3 = pipeline.process_data_source("patterns", "patterns")

    # Get final statistics
    final_stats = pipeline.get_pipeline_stats()

    print("\n=== Pipeline Results ===")
    print(f"Total texts processed: {final_stats['generator_stats']['total_texts_processed']}")
    print(".2f")
    print(f"Cached embeddings used: {final_stats['generator_stats']['cached_embeddings_used']}")
    print(f"New embeddings generated: {final_stats['generator_stats']['new_embeddings_generated']}")

    print("\n=== Configuration ===")
    print(f"Model: {final_stats['pipeline_config']['model_name']}")
    print(f"Batch size: {final_stats['pipeline_config']['batch_size']}")
    print(f"Vector DB available: {final_stats['vector_db_available']}")


if __name__ == "__main__":
    run_embedding_pipeline_demo()