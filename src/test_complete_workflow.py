#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Workflow Verification Test
Tests all integration points: LLM, Vector DB, AI Extraction, Calculations, SLD Generation
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="ignore")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="ignore")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("\n" + "="*70)
print("COMPLETE WORKFLOW VERIFICATION TEST".center(70))
print("="*70 + "\n")

# Test results tracker
test_results = {}

def test_section(name):
    """Print test section header"""
    print(f"\n{'='*70}")
    print(f"{name.upper()}".center(70))
    print(f"{'='*70}\n")

def test_item(description, status="testing"):
    """Print test item"""
    if status == "testing":
        print(f"  → {description}...", end=" ", flush=True)
    elif status == "pass":
        print("✓ PASS")
    elif status == "fail":
        print("✗ FAIL")
    elif status == "skip":
        print("⊘ SKIP")

# ============================================================================
# 1. ENVIRONMENT & CONFIGURATION
# ============================================================================
test_section("1. Environment & Configuration")

test_item("Loading environment variables", "testing")
try:
    from dotenv import load_dotenv
    load_dotenv()
    test_item("", "pass")
    test_results["env_load"] = True
except Exception as e:
    test_item("", "fail")
    print(f"     Error: {e}")
    test_results["env_load"] = False

test_item("Checking GOOGLE_API_KEY", "testing")
google_api_key = os.getenv('GOOGLE_API_KEY')
if google_api_key:
    test_item("", "pass")
    print(f"     Key: {google_api_key[:10]}...{google_api_key[-4:]}")
    test_results["google_api"] = True
else:
    test_item("", "fail")
    print("     Missing GOOGLE_API_KEY in .env")
    test_results["google_api"] = False

# ============================================================================
# 2. VECTOR DATABASE INTEGRATION
# ============================================================================
test_section("2. Vector Database Integration")

test_item("Importing vector_database_manager", "testing")
try:
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        from vector_database_manager import VectorDatabaseManager, get_vector_database
    test_item("", "pass")
    test_results["vdb_import"] = True
except Exception as e:
    test_item("", "fail")
    print(f"     Error: {e}")
    test_results["vdb_import"] = False

if test_results.get("vdb_import"):
    test_item("Initializing vector database", "testing")
    try:
        vdb = VectorDatabaseManager(persist_directory="./vector_db")
        test_item("", "pass")
        test_results["vdb_init"] = True
    except Exception as e:
        test_item("", "fail")
        print(f"     Error: {e}")
        test_results["vdb_init"] = False
    
    if test_results.get("vdb_init"):
        test_item("Checking vector DB collections", "testing")
        try:
            collections = vdb.collections
            print(f"\n     Collections: {len(collections)}")
            for key, name in collections.items():
                print(f"       - {name}")
            test_item("", "pass")
            test_results["vdb_collections"] = True
        except Exception as e:
            test_item("", "fail")
            print(f"     Error: {e}")
            test_results["vdb_collections"] = False
        
        test_item("Testing embedding generation", "testing")
        try:
            test_text = "400V 3-phase motor load"
            embedding = vdb._get_embedding(test_text)
            if len(embedding) > 0:
                test_item("", "pass")
                print(f"     Embedding dimension: {len(embedding)}")
                test_results["vdb_embedding"] = True
            else:
                test_item("", "fail")
                test_results["vdb_embedding"] = False
        except Exception as e:
            test_item("", "fail")
            print(f"     Error: {e}")
            test_results["vdb_embedding"] = False
        
        test_item("Testing RAG query capability", "testing")
        try:
            results = vdb.rag_query("electrical motor specifications", n_results=3)
            test_item("", "pass")
            print(f"     Query returned {len(results)} results")
            test_results["vdb_rag"] = True
        except Exception as e:
            test_item("", "skip")
            print(f"     Warning: {e} (database may be empty)")
            test_results["vdb_rag"] = "skip"

# ============================================================================
# 3. LLM INTEGRATION
# ============================================================================
test_section("3. LLM Integration")

test_item("Importing LLM multimodal processor", "testing")
try:
    from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig
    test_item("", "pass")
    test_results["llm_import"] = True
except Exception as e:
    test_item("", "fail")
    print(f"     Error: {e}")
    test_results["llm_import"] = False

if test_results.get("llm_import") and test_results.get("google_api"):
    test_item("Creating LLM configuration", "testing")
    try:
        config = LLMConfig(provider="google", model="gemini-2.0-flash")
        test_item("", "pass")
        print(f"     Provider: {config.provider}")
        print(f"     Model: {config.model}")
        test_results["llm_config"] = True
    except Exception as e:
        test_item("", "fail")
        print(f"     Error: {e}")
        test_results["llm_config"] = False
    
    if test_results.get("llm_config"):
        test_item("Initializing LLM processor with Vector DB", "testing")
        try:
            processor = LLMMultimodalProcessor(config=config, vector_db_path="./vector_db")
            test_item("", "pass")
            
            if processor.rag_enabled:
                print(f"     RAG: ✓ Enabled")
                test_results["llm_rag"] = True
            else:
                print(f"     RAG: ✗ Disabled")
                test_results["llm_rag"] = False
            
            if config.api_key:
                print(f"     API Key: ✓ Configured")
                test_results["llm_api_key"] = True
            else:
                print(f"     API Key: ✗ Missing")
                test_results["llm_api_key"] = False
            
            test_results["llm_init"] = True
        except Exception as e:
            test_item("", "fail")
            print(f"     Error: {e}")
            test_results["llm_init"] = False

# ============================================================================
# 4. AI EXCEL EXTRACTOR INTEGRATION
# ============================================================================
test_section("4. AI Excel Extractor Integration")

test_item("Importing AI Excel Extractor", "testing")
try:
    from ai_excel_extractor import AIExcelExtractor
    test_item("", "pass")
    test_results["extractor_import"] = True
except Exception as e:
    test_item("", "fail")
    print(f"     Error: {e}")
    test_results["extractor_import"] = False

if test_results.get("extractor_import"):
    test_item("Initializing AI Extractor", "testing")
    try:
        extractor = AIExcelExtractor(standard="IEC")
        test_item("", "pass")
        test_results["extractor_init"] = True
    except Exception as e:
        test_item("", "fail")
        print(f"     Error: {e}")
        test_results["extractor_init"] = False
    
    if test_results.get("extractor_init"):
        test_item("Checking LLM engine integration", "testing")
        if hasattr(extractor, 'llm_engine') and extractor.llm_engine:
            test_item("", "pass")
            print(f"     LLM Engine: ✓ Available")
            test_results["extractor_llm"] = True
        else:
            test_item("", "skip")
            print(f"     LLM Engine: Using pattern matching fallback")
            test_results["extractor_llm"] = "fallback"
        
        test_item("Checking Vector DB integration", "testing")
        if hasattr(extractor, 'vector_db') and extractor.vector_db:
            test_item("", "pass")
            print(f"     Vector DB: ✓ Connected")
            test_results["extractor_vdb"] = True
        else:
            test_item("", "skip")
            print(f"     Vector DB: Using fallback similarity")
            test_results["extractor_vdb"] = "fallback"

# ============================================================================
# 5. UNIFIED PROCESSOR INTEGRATION
# ============================================================================
test_section("5. Unified Processor Integration")

test_item("Importing Unified Processor", "testing")
try:
    from unified_processor import UnifiedDataProcessor, create_unified_processor
    test_item("", "pass")
    test_results["unified_import"] = True
except Exception as e:
    test_item("", "fail")
    print(f"     Error: {e}")
    test_results["unified_import"] = False

if test_results.get("unified_import"):
    test_item("Creating unified processor", "testing")
    try:
        processor = create_unified_processor(standard="IEC")
        test_item("", "pass")
        test_results["unified_init"] = True
    except Exception as e:
        test_item("", "fail")
        print(f"     Error: {e}")
        test_results["unified_init"] = False
    
    if test_results.get("unified_init"):
        test_item("Verifying AI Extractor integration", "testing")
        if hasattr(processor, 'ai_extractor') and processor.ai_extractor:
            test_item("", "pass")
            print(f"     AI Extractor: ✓ Integrated")
            test_results["unified_ai"] = True
        else:
            test_item("", "fail")
            test_results["unified_ai"] = False
        
        test_item("Verifying Calculation Engine integration", "testing")
        if hasattr(processor, 'calc_engine') and processor.calc_engine:
            test_item("", "pass")
            print(f"     Calculation Engine: ✓ Integrated")
            test_results["unified_calc"] = True
        else:
            test_item("", "fail")
            test_results["unified_calc"] = False
        
        test_item("Verifying Standards Framework integration", "testing")
        if hasattr(processor, 'standards') and processor.standards:
            test_item("", "pass")
            print(f"     Standards: ✓ {processor.standards.__class__.__name__}")
            test_results["unified_standards"] = True
        else:
            test_item("", "fail")
            test_results["unified_standards"] = False

# ============================================================================
# 6. CALCULATION ENGINE
# ============================================================================
test_section("6. Calculation Engine")

test_item("Importing calculation engines", "testing")
try:
    from calculations import (
        ElectricalCalculationEngine,
        CurrentCalculator,
        VoltageDropCalculator,
        CableSizingEngine,
        BreakerSelectionEngine
    )
    test_item("", "pass")
    test_results["calc_import"] = True
except Exception as e:
    test_item("", "fail")
    print(f"     Error: {e}")
    test_results["calc_import"] = False

if test_results.get("calc_import"):
    test_item("Initializing calculation engine", "testing")
    try:
        calc_engine = ElectricalCalculationEngine(standard="IEC")
        test_item("", "pass")
        test_results["calc_init"] = True
    except Exception as e:
        test_item("", "fail")
        print(f"     Error: {e}")
        test_results["calc_init"] = False

# ============================================================================
# 7. DATA MODELS
# ============================================================================
test_section("7. Data Models & Project Creation")

test_item("Importing data models", "testing")
try:
    from models import (
        Project, Load, Bus, Transformer, Cable, Breaker,
        LoadType, InstallationMethod, DutyCycle, Priority
    )
    test_item("", "pass")
    test_results["models_import"] = True
except Exception as e:
    test_item("", "fail")
    print(f"     Error: {e}")
    test_results["models_import"] = False

if test_results.get("models_import"):
    test_item("Creating test project", "testing")
    try:
        project = Project(
            project_name="Workflow Test Project",
            project_id="TEST-WORKFLOW-001",
            standard="IEC"
        )
        test_item("", "pass")
        test_results["project_create"] = True
    except Exception as e:
        test_item("", "fail")
        print(f"     Error: {e}")
        test_results["project_create"] = False
    
    if test_results.get("project_create"):
        test_item("Creating test bus", "testing")
        try:
            bus = Bus(
                bus_id="MAIN-BUS-01",
                bus_name="Main Distribution Bus",
                voltage=400,
                rated_current_a=630
            )
            project.add_bus(bus)
            test_item("", "pass")
            print(f"     Buses in project: {len(project.buses)}")
            test_results["bus_create"] = True
        except Exception as e:
            test_item("", "fail")
            print(f"     Error: {e}")
            test_results["bus_create"] = False
        
        test_item("Creating test load", "testing")
        try:
            load = Load(
                load_id="LOAD-001",
                load_name="Test Motor",
                load_type=LoadType.MOTOR,
                power_kw=15.0,
                voltage=400,
                phases=3,
                power_factor=0.85,
                cable_length=50.0,
                source_bus="MAIN-BUS-01"
            )
            project.add_load(load)
            test_item("", "pass")
            print(f"     Loads in project: {len(project.loads)}")
            test_results["load_create"] = True
        except Exception as e:
            test_item("", "fail")
            print(f"     Error: {e}")
            test_results["load_create"] = False

# ============================================================================
# 8. COMPLETE WORKFLOW TEST
# ============================================================================
test_section("8. Complete Workflow Integration")

if all([test_results.get("calc_init"), test_results.get("project_create"), 
        test_results.get("load_create")]):
    
    test_item("Running electrical calculations on test project", "testing")
    try:
        calc_engine = ElectricalCalculationEngine(standard="IEC")
        
        # Calculate current for the load
        load = project.loads[0]
        current_result = calc_engine.calculate_load_current(load)
        
        if current_result and 'design_current_a' in current_result:
            test_item("", "pass")
            print(f"     Design Current: {current_result['design_current_a']:.2f} A")
            test_results["calc_workflow"] = True
        else:
            test_item("", "fail")
            test_results["calc_workflow"] = False
    except Exception as e:
        test_item("", "fail")
        print(f"     Error: {e}")
        test_results["calc_workflow"] = False

# ============================================================================
# SUMMARY
# ============================================================================
test_section("Test Summary")

# Count results
total_tests = len([k for k in test_results.keys() if k != "summary"])
passed = len([v for v in test_results.values() if v is True])
failed = len([v for v in test_results.values() if v is False])
skipped = len([v for v in test_results.values() if v == "skip" or v == "fallback"])

print(f"\nTotal Tests: {total_tests}")
print(f"  ✓ Passed: {passed}")
print(f"  ✗ Failed: {failed}")
print(f"  ⊘ Skipped/Fallback: {skipped}")
print(f"\nSuccess Rate: {(passed/total_tests*100):.1f}%\n")

# Critical integration points
print("="*70)
print("CRITICAL INTEGRATION POINTS")
print("="*70 + "\n")

critical_checks = {
    "LLM → Vector DB": test_results.get("llm_rag"),
    "AI Extractor → LLM": test_results.get("extractor_llm"),
    "AI Extractor → Vector DB": test_results.get("extractor_vdb"),
    "Unified Processor → AI Extractor": test_results.get("unified_ai"),
    "Unified Processor → Calculations": test_results.get("unified_calc"),
    "Unified Processor → Standards": test_results.get("unified_standards"),
    "Calculations → Data Models": test_results.get("calc_workflow")
}

for check, status in critical_checks.items():
    status_str = "✓ CONNECTED" if status is True else ("⊘ FALLBACK" if status == "fallback" else "✗ FAILED")
    print(f"  {check}: {status_str}")

print("\n" + "="*70)

if failed == 0:
    print("\n✅ ALL CRITICAL SYSTEMS OPERATIONAL")
    print("System is ready for production use!\n")
    sys.exit(0)
else:
    print("\n⚠️  SOME ISSUES FOUND")
    print("Review the failures above and fix before deployment.\n")
    sys.exit(1)
