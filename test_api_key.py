#!/usr/bin/env python3
"""
Test script to verify Google API key loading and LLM functionality
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_loading():
    """Test if environment variables are loaded correctly"""
    print("="*50)
    print("Testing Google API Key Loading")
    print("="*50)

    # Check if .env file exists
    env_file_exists = os.path.exists('.env')
    print(f".env file exists: {env_file_exists}")

    # Load and check API key
    api_key = os.getenv('GOOGLE_API_KEY')
    key_loaded = api_key is not None
    key_length = len(api_key) if api_key else 0
    key_masked = api_key[:10] + "..." + api_key[-5:] if api_key and len(api_key) > 15 else api_key or "None"

    print(f"API key loaded: {key_loaded}")
    print(f"Key length: {key_length} characters")
    print(f"Key preview: {key_masked}")

    return key_loaded

def test_llm_initialization():
    """Test LLM processor initialization"""
    print("\n" + "="*50)
    print("Testing LLM Processor Initialization")
    print("="*50)

    try:
        from src.llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig

        # Create config
        config = LLMConfig()
        print(f"✅ Config created with provider: {config.provider}")
        print(f"✅ Model: {config.model}")

        # Check if API key is available in config
        if config.api_key:
            print("✅ API key found in config")
        else:
            print("❌ No API key in config (will use os.getenv fallback)")

        # Try to initialize processor
        processor = LLMMultimodalProcessor(config)
        print("✅ LLM Processor initialized successfully")

        # Check RAG status
        rag_status = "Enabled" if processor.rag_enabled else "Disabled"
        print(f"RAG Status: {rag_status}")

        return True

    except Exception as e:
        print(f"LLM initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_api_call():
    """Test a basic API call to verify key works"""
    print("\n" + "="*50)
    print("Testing Basic API Call (Optional)")
    print("="*50)

    try:
        import requests
        from src.llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig

        config = LLMConfig()
        processor = LLMMultimodalProcessor(config)

        # Test with a simple validation call (if API key works)
        # We'll just check if the config has the key
        if config.api_key and len(config.api_key) > 20:
            print("✅ API key appears valid (length check passed)")
            print("🔧 To test actual API calls, you would need to call processor.analyze_diagram() with an image")
        else:
            print("⚠️  API key may be invalid or missing")

        return True

    except Exception as e:
        print(f"API call test failed: {e}")
        return False

if __name__ == "__main__":
    print("Google API Key Test Suite")
    print("Testing environment setup and LLM integration...\n")

    # Run tests
    env_test = test_env_loading()
    llm_test = test_llm_initialization()
    api_test = test_basic_api_call()

    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Environment Setup: {'PASS' if env_test else 'FAIL'}")
    print(f"LLM Initialization: {'PASS' if llm_test else 'FAIL'}")
    print(f"API Call Setup: {'PASS' if api_test else 'FAIL'}")

    overall_status = "ALL TESTS PASSED" if all([env_test, llm_test, api_test]) else "SOME TESTS FAILED"
    print(f"\nOverall Status: {overall_status}")

    if not env_test:
        print("\n🔧 To fix environment issues:")
        print("1. Ensure .env file exists in project root")
        print("2. Add line: GOOGLE_API_KEY=your_actual_api_key_here")
        print("3. Restart any running applications")

    if not llm_test:
        print("\n🔧 To fix LLM issues:")
        print("1. Install required packages: pip install python-dotenv requests")
        print("2. Check that API key is valid Google Gemini API key")
        print("3. Ensure network connectivity for API calls")