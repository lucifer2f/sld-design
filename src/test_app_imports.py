#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test to verify app imports work"""

import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="ignore")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="ignore")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing imports for Streamlit app...\n")

try:
    print("1. Testing models import...", end=" ")
    from models import Project, Load, Bus
    print("✓ OK")
    
    print("2. Testing standards import...", end=" ")
    from standards import StandardsFactory
    print("✓ OK")
    
    print("3. Testing calculations import...", end=" ")
    from calculations import ElectricalCalculationEngine
    print("✓ OK")
    
    print("4. Testing vector_database_manager import...", end=" ")
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        from vector_database_manager import VectorDatabaseManager
    print("✓ OK")
    
    print("5. Testing llm_multimodal_processor import...", end=" ")
    from llm_multimodal_processor import LLMMultimodalProcessor
    print("✓ OK")
    
    print("6. Testing excel_extractor import...", end=" ")
    from excel_extractor import AIExcelExtractor
    print("✓ OK")
    
    print("7. Testing unified_processor import...", end=" ")
    from unified_processor import UnifiedDataProcessor
    print("✓ OK")
    
    print("\n✅ All imports successful!")
    print("\n✓ App should launch without import errors")
    print("\nRun: streamlit run src/app.py")
    
except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
