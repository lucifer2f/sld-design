#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Integration Tests for SLD Design Electrical Automation
Tests all components to verify proper integration and functionality
"""

import os
import sys
import importlib
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="ignore")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="ignore")

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_test(text, status="running"):
    if status == "running":
        print(f"{Colors.YELLOW}[TESTING]{Colors.RESET} {text}...", end=" ")
    elif status == "pass":
        print(f"{Colors.GREEN}✓ PASS{Colors.RESET}")
    elif status == "fail":
        print(f"{Colors.RED}✗ FAIL{Colors.RESET}")
    elif status == "warn":
        print(f"{Colors.YELLOW}⚠ WARNING{Colors.RESET}")
    elif status == "skip":
        print(f"{Colors.YELLOW}⊘ SKIPPED{Colors.RESET}")

def test_imports():
    """Test all critical imports"""
    print_header("Testing Python Imports")
    
    tests = {
        "Core Dependencies": [
            ("pandas", "pandas"),
            ("numpy", "numpy"),
            ("streamlit", "streamlit"),
            ("plotly", "plotly.express"),
        ],
        "AI/ML Components": [
            ("chromadb", "chromadb"),
            ("sentence-transformers", "sentence_transformers"),
            ("PIL (Pillow)", "PIL"),
            ("requests", "requests"),
        ],
        "Data Processing": [
            ("openpyxl", "openpyxl"),
            ("fuzzywuzzy", "fuzzywuzzy"),
            ("python-dotenv", "dotenv"),
        ],
        "Application Modules": [
            ("models", "models"),
            ("calculations", "calculations"),
            ("standards", "standards"),
            ("vector_database_manager", "vector_database_manager"),
            ("llm_multimodal_processor", "llm_multimodal_processor"),
            ("excel_extractor", "excel_extractor"),
            ("unified_processor", "unified_processor"),
        ]
    }
    
    all_passed = True
    for category, imports in tests.items():
        print(f"\n{Colors.BOLD}{category}:{Colors.RESET}")
        for name, module in imports:
            print_test(f"Importing {name}", "running")
            try:
                importlib.import_module(module)
                print_test("", "pass")
            except ImportError as e:
                print_test("", "fail")
                print(f"  Error: {e}")
                all_passed = False
            except Exception as e:
                print_test("", "warn")
                print(f"  Warning: {e}")
    
    return all_passed

def test_env_configuration():
    """Test environment configuration"""
    print_header("Testing Environment Configuration")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = {
        "GOOGLE_API_KEY": "Google Gemini API",
        "OPENAI_API_KEY": "OpenAI API (Optional)",
        "ANTHROPIC_API_KEY": "Anthropic API (Optional)",
    }
    
    has_at_least_one = False
    for var, description in env_vars.items():
        print_test(f"Checking {description}", "running")
        value = os.getenv(var)
        if value:
            if var == "GOOGLE_API_KEY":
                has_at_least_one = True
            print_test("", "pass")
            print(f"  Configured: {value[:10]}...{value[-4:] if len(value) > 14 else ''}")
        else:
            if var == "GOOGLE_API_KEY":
                print_test("", "fail")
                print(f"  Please set {var} in .env file")
            else:
                print_test("", "skip")
                print(f"  Optional - not configured")
    
    return has_at_least_one

def test_vector_database():
    """Test vector database initialization"""
    print_header("Testing Vector Database")
    
    try:
        print_test("Initializing vector database manager", "running")
        from vector_database_manager import VectorDatabaseManager
        print_test("", "pass")
        
        print_test("Creating vector database instance", "running")
        vdb = VectorDatabaseManager(persist_directory="./vector_db")
        print_test("", "pass")
        
        print_test("Checking collections", "running")
        collections = vdb.collections
        print_test("", "pass")
        print(f"  Found {len(collections)} collections: {', '.join(collections.keys())}")
        
        print_test("Testing embedding generation", "running")
        test_text = "Test electrical component: 400V motor"
        embedding = vdb._get_embedding(test_text)
        if len(embedding) > 0:
            print_test("", "pass")
            print(f"  Embedding dimension: {len(embedding)}")
        else:
            print_test("", "fail")
            return False
        
        print_test("Testing RAG query", "running")
        try:
            results = vdb.rag_query("electrical motor specifications", n_results=3)
            print_test("", "pass")
            print(f"  Query successful (returned {len(results)} results)")
        except Exception as e:
            print_test("", "warn")
            print(f"  Warning: {e} (database may be empty)")
        
        return True
        
    except Exception as e:
        print_test("", "fail")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_processor():
    """Test LLM multimodal processor"""
    print_header("Testing LLM Processor")
    
    try:
        print_test("Importing LLM processor", "running")
        from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig
        print_test("", "pass")
        
        print_test("Creating LLM configuration", "running")
        config = LLMConfig(provider="google", model="gemini-2.0-flash")
        print_test("", "pass")
        print(f"  Provider: {config.provider}, Model: {config.model}")
        
        print_test("Initializing LLM processor", "running")
        processor = LLMMultimodalProcessor(config=config)
        print_test("", "pass")
        
        if processor.rag_enabled:
            print(f"  RAG: {Colors.GREEN}Enabled{Colors.RESET}")
        else:
            print(f"  RAG: {Colors.YELLOW}Disabled{Colors.RESET}")
        
        if config.api_key:
            print(f"  API Key: {Colors.GREEN}Configured{Colors.RESET}")
        else:
            print(f"  API Key: {Colors.RED}Missing{Colors.RESET}")
            return False
        
        return True
        
    except Exception as e:
        print_test("", "fail")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_extractor():
    """Test AI Excel extractor"""
    print_header("Testing AI Excel Extractor")
    
    try:
        print_test("Importing AI extractor", "running")
        from ai_excel_extractor import AIExcelExtractor
        print_test("", "pass")
        
        print_test("Initializing AI extractor", "running")
        extractor = AIExcelExtractor(standard="IEC")
        print_test("", "pass")
        
        print_test("Checking LLM engine integration", "running")
        if hasattr(extractor, 'llm_engine') and extractor.llm_engine:
            print_test("", "pass")
            print(f"  LLM Engine: {Colors.GREEN}Available{Colors.RESET}")
        else:
            print_test("", "warn")
            print(f"  LLM Engine: {Colors.YELLOW}Not available (using fallback){Colors.RESET}")
        
        print_test("Checking vector database integration", "running")
        if hasattr(extractor, 'vector_db') and extractor.vector_db:
            print_test("", "pass")
            print(f"  Vector DB: {Colors.GREEN}Connected{Colors.RESET}")
        else:
            print_test("", "warn")
            print(f"  Vector DB: {Colors.YELLOW}Not connected (using fallback){Colors.RESET}")
        
        return True
        
    except Exception as e:
        print_test("", "fail")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_unified_processor():
    """Test unified processor integration"""
    print_header("Testing Unified Processor")
    
    try:
        print_test("Importing unified processor", "running")
        from unified_processor import UnifiedDataProcessor, create_unified_processor
        print_test("", "pass")
        
        print_test("Creating unified processor", "running")
        processor = create_unified_processor(standard="IEC")
        print_test("", "pass")
        
        print_test("Checking AI extractor integration", "running")
        if hasattr(processor, 'ai_extractor') and processor.ai_extractor:
            print_test("", "pass")
        else:
            print_test("", "fail")
            return False
        
        print_test("Checking calculation engine integration", "running")
        if hasattr(processor, 'calc_engine') and processor.calc_engine:
            print_test("", "pass")
        else:
            print_test("", "fail")
            return False
        
        print_test("Checking standards framework integration", "running")
        if hasattr(processor, 'standards') and processor.standards:
            print_test("", "pass")
            print(f"  Standard: {processor.standards.__class__.__name__}")
        else:
            print_test("", "fail")
            return False
        
        return True
        
    except Exception as e:
        print_test("", "fail")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_calculation_engines():
    """Test calculation engines"""
    print_header("Testing Calculation Engines")
    
    try:
        print_test("Importing calculation engines", "running")
        from calculations import (
            ElectricalCalculationEngine,
            CurrentCalculator,
            VoltageDropCalculator,
            CableSizingEngine,
            BreakerSelectionEngine
        )
        print_test("", "pass")
        
        print_test("Initializing calculation engine", "running")
        calc_engine = ElectricalCalculationEngine(standard="IEC")
        print_test("", "pass")
        
        print_test("Testing current calculator", "running")
        current_calc = CurrentCalculator(calc_engine.standard)
        print_test("", "pass")
        
        print_test("Testing voltage drop calculator", "running")
        vd_calc = VoltageDropCalculator(calc_engine.standard)
        print_test("", "pass")
        
        print_test("Testing cable sizing engine", "running")
        cable_engine = CableSizingEngine(calc_engine.standard)
        print_test("", "pass")
        
        print_test("Testing breaker selection engine", "running")
        breaker_engine = BreakerSelectionEngine(calc_engine.standard)
        print_test("", "pass")
        
        return True
        
    except Exception as e:
        print_test("", "fail")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_models():
    """Test data models"""
    print_header("Testing Data Models")
    
    try:
        print_test("Importing data models", "running")
        from models import (
            Project, Load, Bus, Transformer, Cable, Breaker,
            LoadType, InstallationMethod, DutyCycle, Priority
        )
        print_test("", "pass")
        
        print_test("Creating test project", "running")
        project = Project(
            project_name="Test Project",
            project_id="TEST-001",
            standard="IEC"
        )
        print_test("", "pass")
        
        print_test("Creating test load", "running")
        load = Load(
            load_id="L001",
            load_name="Test Motor",
            load_type=LoadType.MOTOR,
            power_kw=15.0,
            voltage=400,
            phases=3,
            power_factor=0.85
        )
        print_test("", "pass")
        
        print_test("Adding load to project", "running")
        project.add_load(load)
        if len(project.loads) == 1:
            print_test("", "pass")
        else:
            print_test("", "fail")
            return False
        
        return True
        
    except Exception as e:
        print_test("", "fail")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def print_summary(results):
    """Print test summary"""
    print_header("Test Summary")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
    print(f"Success Rate: {(passed/total*100):.1f}%\n")
    
    if failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED{Colors.RESET}")
        print(f"{Colors.GREEN}System is fully integrated and ready to use!{Colors.RESET}\n")
        return True
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.RESET}")
        print(f"{Colors.YELLOW}Please review the errors above and fix any issues.{Colors.RESET}\n")
        return False

def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}SLD Design - System Integration Tests{Colors.RESET}")
    print(f"Testing all components for proper integration...\n")
    
    results = {}
    
    # Run all tests
    results["Python Imports"] = test_imports()
    results["Environment Configuration"] = test_env_configuration()
    results["Vector Database"] = test_vector_database()
    results["LLM Processor"] = test_llm_processor()
    results["AI Excel Extractor"] = test_ai_extractor()
    results["Unified Processor"] = test_unified_processor()
    results["Calculation Engines"] = test_calculation_engines()
    results["Data Models"] = test_data_models()
    
    # Print summary
    success = print_summary(results)
    
    # Return exit code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
