#!/usr/bin/env python3
"""
Test script for Vector Database Integration

Tests all vector database features including:
- RAG with LLM processor
- Excel header mapping storage and retrieval
- Component specification knowledge base
- Design pattern recognition
- Standards compliance storage
"""

import os
import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from vector_database_manager import get_vector_database, VectorDatabaseManager
from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_basic_vector_operations():
    """Test basic vector database operations"""
    print("\nTesting Basic Vector Database Operations")
    print("=" * 60)

    try:
        # Initialize vector database
        db = get_vector_database("./test_vector_db")

        # Test component storage and search
        print("Testing component storage and search...")

        # Store a test component
        component_data = {
            "type": "induction_motor",
            "power_kw": 22.0,
            "voltage": 400,
            "phases": 3,
            "power_factor": 0.85,
            "efficiency": 0.92,
            "starting_method": "DOL",
            "speed_rpm": 1470
        }

        db.store_component_specification("test_motor_22kw", component_data, "motor")

        # Search for similar components
        results = db.search_components("22kW induction motor 400V", top_k=3)
        print(f"✅ Found {len(results)} matching components")
        for result in results:
            print(f"   - {result['component_id']}: {result['type']} {result['power_kw']}kW")

        # Test design pattern storage
        print("Testing design pattern storage...")

        pattern_data = {
            "description": "Standard motor control center with VFD drives",
            "components": ["motor", "vfd", "circuit_breaker", "control_cable"],
            "standards": ["IEC 60947", "IEC 60204"],
            "industry": "industrial",
            "efficiency_rating": 0.88,
            "complexity": "high"
        }

        db.store_design_pattern("vfd_motor_control", pattern_data, "motor_control")

        # Find similar patterns
        patterns = db.find_similar_designs("motor control with variable frequency drives", top_k=2)
        print(f"✅ Found {len(patterns)} similar design patterns")
        for pattern in patterns:
            print(f"   - {pattern['pattern_id']}: {pattern['description']}")

        # Test standards storage
        print("Testing standards compliance storage...")

        rule_data = {
            "title": "Motor Protection Requirements",
            "description": "Motors above 0.37kW shall have overload protection",
            "requirements": "Thermal overload relay or electronic protection",
            "category": "motor_protection",
            "applies_to": ["motors", "protection_devices"],
            "severity": "high",
            "reference": "IEC 60947-4-1"
        }

        db.store_standards_rule("iec_motor_protection", rule_data, "IEC")

        # Search standards
        standards = db.search_standards("motor overload protection", top_k=2)
        print(f"✅ Found {len(standards)} relevant standards")
        for std in standards:
            print(f"   - {std['title']}: {std['description']}")

        # Test Excel header mappings
        print("Testing Excel header mappings...")

        db.store_excel_header_mapping("Power (kW)", "power_kw", 0.95, "Load schedule")
        db.store_excel_header_mapping("Voltage (V)", "voltage", 0.98, "Load schedule")
        db.store_excel_header_mapping("Motor Name", "load_name", 0.92, "Load schedule")

        # Retrieve header mappings
        mappings = db.retrieve_excel_header_mappings("Power", top_k=3)
        print(f"✅ Found {len(mappings)} similar header mappings")
        for mapping in mappings:
            print(f"   - '{mapping['header']}' → '{mapping['field']}' (conf: {mapping['confidence']:.2f})")

        # Test collection stats
        print("Testing collection statistics...")
        stats = db.get_collection_stats()
        for collection_type, info in stats.items():
            count = info.get('count', 0)
            print(f"   - {collection_type}: {count} items")

        print("Basic vector operations test passed!")
        return True

    except Exception as e:
        print(f"Basic vector operations test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_integration():
    """Test RAG integration with LLM processor"""
    print("\nTesting RAG Integration with LLM Processor")
    print("=" * 60)

    try:
        # Initialize vector database
        db = get_vector_database("./test_vector_db")

        # Initialize LLM processor with vector DB
        llm_config = LLMConfig(
            provider="openai",  # Will fallback gracefully
            model="gpt-4-vision-preview"
        )

        processor = LLMMultimodalProcessor(config=llm_config)

        # Test RAG query
        print("Testing RAG query...")

        rag_result = db.rag_query(
            "What protection is required for motors above 0.37kW?",
            "electrical",
            top_k=3
        )

        print(f"✅ RAG query returned {len(rag_result['sources'])} sources")
        print(f"   Context length: {rag_result['context_length']} characters")
        print(f"   Query: {rag_result['query'][:50]}...")

        if rag_result['sources']:
            print("   Top sources:")
            for i, source in enumerate(rag_result['sources'][:2]):
                print(f"     {i+1}. {source['type']}: {source.get('id', 'unknown')}")

        print("RAG integration test passed!")
        return True

    except Exception as e:
        print(f"RAG integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_excel_header_integration():
    """Test Excel header mapping integration"""
    print("\nTesting Excel Header Mapping Integration")
    print("=" * 60)

    try:
        # Initialize vector database
        db = get_vector_database("./test_vector_db")

        # Add more comprehensive header mappings
        headers_to_add = [
            ("load id", "load_id", 0.95),
            ("equipment id", "load_id", 0.90),
            ("motor id", "load_id", 0.88),
            ("load name", "load_name", 0.95),
            ("equipment name", "load_name", 0.92),
            ("description", "load_name", 0.85),
            ("power (kw)", "power_kw", 0.98),
            ("kw", "power_kw", 0.90),
            ("rated power", "power_kw", 0.85),
            ("voltage (v)", "voltage", 0.98),
            ("volts", "voltage", 0.90),
            ("system voltage", "voltage", 0.85),
            ("phases", "phases", 0.95),
            ("phase", "phases", 0.85),
            ("number of phases", "phases", 0.90),
            ("power factor", "power_factor", 0.95),
            ("pf", "power_factor", 0.85),
            ("cos phi", "power_factor", 0.90),
            ("cosφ", "power_factor", 0.88),
            ("efficiency", "efficiency", 0.95),
            ("eta", "efficiency", 0.85),
            ("η", "efficiency", 0.80),
            ("source bus", "source_bus", 0.90),
            ("bus", "source_bus", 0.80),
            ("panel", "source_bus", 0.75),
            ("priority", "priority", 0.90),
            ("importance", "priority", 0.85),
            ("cable length", "cable_length", 0.95),
            ("length (m)", "cable_length", 0.90),
            ("installation method", "installation_method", 0.95),
            ("install method", "installation_method", 0.90),
            ("cable id", "cable_id", 0.95),
            ("cable tag", "cable_id", 0.85),
            ("from equipment", "from_equipment", 0.95),
            ("from", "from_equipment", 0.80),
            ("source", "from_equipment", 0.85),
            ("to equipment", "to_equipment", 0.95),
            ("to", "to_equipment", 0.80),
            ("destination", "to_equipment", 0.85),
            ("cores", "cores", 0.95),
            ("core", "cores", 0.85),
            ("size (mm2)", "size_sqmm", 0.95),
            ("size mm2", "size_sqmm", 0.90),
            ("csa", "size_sqmm", 0.80),
            ("cable type", "cable_type", 0.95),
            ("type", "cable_type", 0.75),
            ("length (m)", "length_m", 0.95),
            ("length m", "length_m", 0.90),
            ("cable length", "length_m", 0.85),
            ("armored", "armored", 0.95),
            ("armoured", "armored", 0.90),
            ("bus id", "bus_id", 0.95),
            ("panel id", "bus_id", 0.85),
            ("bus name", "bus_name", 0.95),
            ("panel name", "bus_name", 0.85),
            ("un (v)", "voltage", 0.90),
            ("rated voltage", "voltage", 0.95),
            ("phases", "phases", 0.95),
            ("rated current (a)", "rated_current_a", 0.95),
            ("current", "rated_current_a", 0.80),
            ("upstream bus", "upstream_bus", 0.90),
            ("upstream", "upstream_bus", 0.80),
            ("short circuit rating (ka)", "short_circuit_rating_ka", 0.95),
            ("sc rating", "short_circuit_rating_ka", 0.85),
            ("fault level", "short_circuit_rating_ka", 0.80)
        ]

        print(f"Adding {len(headers_to_add)} Excel header mappings...")
        for header, field, confidence in headers_to_add:
            db.store_excel_header_mapping(header, field, confidence, "Comprehensive mapping")

        # Test retrieval with various queries
        test_queries = [
            "power",
            "voltage",
            "cable size",
            "motor name",
            "bus id",
            "installation"
        ]

        print("Testing header mapping retrieval...")
        for query in test_queries:
            mappings = db.retrieve_excel_header_mappings(query, top_k=2)
            if mappings:
                top_match = mappings[0]
                print(f"   '{query}' → '{top_match['header']}' → '{top_match['field']}' (conf: {top_match['similarity_score']:.2f})")
            else:
                print(f"   '{query}' → No matches found")

        print("Excel header integration test passed!")
        return True

    except Exception as e:
        print(f"Excel header integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_knowledge_base_initialization():
    """Test knowledge base initialization"""
    print("\nTesting Knowledge Base Initialization")
    print("=" * 60)

    try:
        # Initialize vector database
        db = get_vector_database("./test_vector_db")

        # Initialize default knowledge base
        print("Initializing default knowledge base...")
        db.initialize_default_knowledge_base()

        # Check collections after initialization
        stats = db.get_collection_stats()

        print("Knowledge base statistics:")
        total_items = 0
        for collection_type, info in stats.items():
            count = info.get('count', 0)
            total_items += count
            print(f"   - {collection_type}: {count} items")

        print(f"Knowledge base initialized with {total_items} total items!")

        # Test a few queries to verify knowledge is accessible
        print("Testing knowledge retrieval...")

        # Test component search
        motors = db.search_components("induction motor", top_k=3)
        print(f"   Motors found: {len(motors)}")

        # Test pattern search
        patterns = db.find_similar_designs("motor control", top_k=2)
        print(f"   Design patterns found: {len(patterns)}")

        # Test standards search
        standards = db.search_standards("cable sizing", top_k=2)
        print(f"   Standards rules found: {len(standards)}")

        # Test header mappings
        headers = db.retrieve_excel_header_mappings("power", top_k=3)
        print(f"   Header mappings found: {len(headers)}")

        print("Knowledge base initialization test passed!")
        return True

    except Exception as e:
        print(f"Knowledge base initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_database():
    """Clean up test database"""
    import shutil

    try:
        if os.path.exists("./test_vector_db"):
            shutil.rmtree("./test_vector_db")
            print("Cleaned up test database")
    except Exception as e:
        print(f"Failed to clean up test database: {e}")


def main():
    """Run all vector database tests"""
    print("Vector Database Integration Test Suite")
    print("=" * 60)
    print(f"Test database location: {os.path.abspath('./test_vector_db')}")

    # Clean up any existing test database
    cleanup_test_database()

    # Run tests
    tests = [
        ("Basic Vector Operations", test_basic_vector_operations),
        ("RAG Integration", test_rag_integration),
        ("Excel Header Integration", test_excel_header_integration),
        ("Knowledge Base Initialization", test_knowledge_base_initialization)
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\nTest Results Summary")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("All tests passed! Vector database integration is working correctly.")
    else:
        print(f"{total - passed} test(s) failed. Please check the implementation.")

    # Clean up
    cleanup_test_database()

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)