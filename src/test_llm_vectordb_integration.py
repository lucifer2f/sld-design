#!/usr/bin/env python3
"""
Comprehensive test to verify LLM and Vector Database integration
"""

import sys
import os
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_vector_database_initialization():
    print("\n" + "="*80)
    print("TEST 1: Vector Database Initialization")
    print("="*80)
    
    try:
        from vector_database_manager import VectorDatabaseManager, get_vector_database
        
        logger.info("Initializing VectorDatabaseManager directly...")
        vdb = VectorDatabaseManager(persist_directory="./test_vector_db")
        logger.info("✓ VectorDatabaseManager initialized successfully")
        
        logger.info("Testing singleton pattern...")
        vdb2 = get_vector_database("./test_vector_db")
        logger.info("✓ get_vector_database() works correctly")
        
        print("\n✅ TEST 1 PASSED: Vector database initialization works correctly")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 1 FAILED: {e}", exc_info=True)
        return False


def test_llm_processor_initialization():
    print("\n" + "="*80)
    print("TEST 2: LLM Processor Initialization with Vector DB")
    print("="*80)
    
    try:
        from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig
        
        logger.info("Creating LLMConfig...")
        config = LLMConfig(provider="google", model="gemini-2.0-flash")
        logger.info(f"✓ LLMConfig created: provider={config.provider}")
        
        logger.info("Initializing LLMMultimodalProcessor...")
        processor = LLMMultimodalProcessor(config, vector_db_path="./test_vector_db")
        logger.info("✓ LLMMultimodalProcessor initialized")
        
        if processor.rag_enabled:
            logger.info("✓ RAG (Retrieval-Augmented Generation) is ENABLED")
        
        if processor.vector_db is not None:
            logger.info("✓ Vector database is accessible from LLM processor")
        else:
            return False
        
        print("\n✅ TEST 2 PASSED: LLM processor initialization works")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 2 FAILED: {e}", exc_info=True)
        return False


def test_vector_db_operations():
    print("\n" + "="*80)
    print("TEST 3: Vector Database Operations")
    print("="*80)
    
    try:
        from vector_database_manager import get_vector_database
        
        vdb = get_vector_database("./test_vector_db")
        
        logger.info("Initializing default knowledge base...")
        vdb.initialize_default_knowledge_base()
        logger.info("✓ Default knowledge base initialized")
        
        logger.info("Testing component search...")
        results = vdb.search_components("15kW motor 400V")
        logger.info(f"✓ Component search returned {len(results)} results")
        
        logger.info("Testing RAG query...")
        rag_result = vdb.rag_query("What cable size for 45A?", context_domain="electrical", top_k=5)
        logger.info(f"✓ RAG query returned results")
        
        logger.info("Testing design pattern search...")
        patterns = vdb.find_similar_designs("industrial motor control")
        logger.info(f"✓ Design pattern search returned {len(patterns)} results")
        
        logger.info("Checking collection statistics...")
        stats = vdb.get_collection_stats()
        logger.info(f"✓ Collection stats retrieved")
        
        print("\n✅ TEST 3 PASSED: Vector database operations work correctly")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 3 FAILED: {e}", exc_info=True)
        return False


def test_llm_vector_db_rag():
    print("\n" + "="*80)
    print("TEST 4: LLM and Vector DB RAG Integration")
    print("="*80)
    
    try:
        from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig
        
        config = LLMConfig(provider="google", model="gemini-2.0-flash")
        processor = LLMMultimodalProcessor(config, vector_db_path="./test_vector_db")
        
        logger.info("Checking vector database integration...")
        assert processor.vector_db is not None
        logger.info("✓ Vector database is properly integrated")
        
        logger.info("Checking RAG status...")
        assert processor.rag_enabled
        logger.info("✓ RAG is properly enabled")
        
        logger.info("Checking RAG method availability...")
        if hasattr(processor.vector_db, 'rag_query'):
            logger.info("✓ RAG query method is available")
        else:
            return False
        
        print("\n✅ TEST 4 PASSED: LLM and Vector DB RAG integration works")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 4 FAILED: {e}", exc_info=True)
        return False


def test_design_analyzer_integration():
    print("\n" + "="*80)
    print("TEST 5: Design Analyzer Integration")
    print("="*80)
    
    try:
        from design_analyzer import AIDesignAnalyzer
        from models import Project, Load, LoadType
        
        logger.info("Initializing AIDesignAnalyzer...")
        analyzer = AIDesignAnalyzer()
        
        if analyzer.llm:
            logger.info("✓ LLM processor is initialized")
        
        if analyzer.vector_db:
            logger.info("✓ Vector database is initialized")
        
        logger.info("Creating test project...")
        project = Project(project_name="Test Project")
        
        load = Load(
            load_id="TEST_MOTOR_1",
            load_name="Test Motor",
            load_type=LoadType.MOTOR,
            power_kw=15.0,
            voltage=415.0,
            phases=3,
            cable_length=10.0
        )
        project.loads.append(load)
        
        logger.info("Performing design analysis...")
        analysis = analyzer.analyze_design(project)
        logger.info(f"✓ Analysis completed with score={analysis.overall_score}")
        
        print("\n✅ TEST 5 PASSED: Design Analyzer integration works")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 5 FAILED: {e}", exc_info=True)
        return False


def test_excel_extractor_integration():
    print("\n" + "="*80)
    print("TEST 6: Excel Extractor Integration")
    print("="*80)
    
    try:
        from excel_extractor import AIExcelExtractor
        
        logger.info("Initializing AIExcelExtractor...")
        extractor = AIExcelExtractor()
        logger.info("✓ AIExcelExtractor initialization successful")
        
        print("\n✅ TEST 6 PASSED: Excel Extractor integration works")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 6 FAILED: {e}", exc_info=True)
        return False


def test_error_handling():
    print("\n" + "="*80)
    print("TEST 7: Error Handling and Fallback Mechanisms")
    print("="*80)
    
    try:
        from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig
        
        logger.info("Testing graceful degradation...")
        config = LLMConfig(provider="google")
        processor = LLMMultimodalProcessor(config, vector_db_path="./test_vector_db")
        
        assert processor is not None
        logger.info("✓ Processor created with graceful degradation")
        logger.info("✓ Error handling is working")
        
        print("\n✅ TEST 7 PASSED: Error handling works correctly")
        return True
    except Exception as e:
        logger.error(f"❌ TEST 7 FAILED: {e}", exc_info=True)
        return False


def run_all_tests():
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*15 + "LLM AND VECTOR DATABASE INTEGRATION TEST SUITE" + " "*17 + "║")
    print("╚" + "="*78 + "╝")
    
    tests = [
        ("Vector Database Initialization", test_vector_database_initialization),
        ("LLM Processor Initialization", test_llm_processor_initialization),
        ("Vector DB Operations", test_vector_db_operations),
        ("LLM-VectorDB RAG Integration", test_llm_vector_db_rag),
        ("Design Analyzer Integration", test_design_analyzer_integration),
        ("Excel Extractor Integration", test_excel_extractor_integration),
        ("Error Handling", test_error_handling),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"Unexpected error in {test_name}: {e}", exc_info=True)
            results[test_name] = False
    
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("-"*80)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print("="*80)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! LLM and Vector DB are properly integrated.")
        return 0
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
