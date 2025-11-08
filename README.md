# SLD Design - Electrical Automation System

AI-powered electrical design automation system with LLM integration, vector database knowledge management, and comprehensive calculation engines.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure API key (copy .env.example to .env and add your key)
cp .env.example .env
# Edit .env and add GOOGLE_API_KEY

# Run the application
streamlit run src/app.py
```

**Or use the quick start script:**
- Windows: Double-click `START_APP.bat`
- Linux/Mac: `./start_app.sh`

## ✨ Features

### AI-Powered Capabilities
- **Intelligent Excel Extraction** - Automatically extract electrical data from Excel files
- **LLM Integration** - Google Gemini, OpenAI, Anthropic Claude support
- **RAG (Retrieval-Augmented Generation)** - Context-aware knowledge retrieval
- **Vector Database** - ChromaDB with semantic search
- **Pattern Recognition** - Automatic detection of electrical patterns
- **Smart Validation** - AI-powered data quality checks

### Electrical Calculations
- **Current Calculations** - Load current, design current, starting current
- **Voltage Drop Analysis** - Per IEC, NEC, IS, BS standards
- **Cable Sizing** - Automatic cable selection based on load requirements
- **Breaker Selection** - MCB, MCCB, ACB selection
- **Standards Compliance** - Multi-standard support (IEC, NEC, IS, BS)

### Manual Workflows
- **Project Management** - Create and manage electrical projects
- **Equipment Configuration** - Loads, buses, transformers, cables, breakers
- **SLD Generation** - Automatic Single Line Diagram creation (Graphviz DOT format)
- **Data Import/Export** - Excel and JSON support
- **Reports** - Comprehensive calculation reports
- **SLD Export** - Download diagrams for rendering with Graphviz

## 📋 Requirements

- Python 3.8+
- Windows, Linux, or macOS
- At least one LLM API key (Google Gemini recommended)

## 📦 Installation

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API key:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

4. **Run the application:**
   ```bash
   streamlit run src/app.py
   ```

## 🎯 Usage

### AI Excel Extraction

1. Navigate to **🤖 AI Tools** in the sidebar
2. Upload an Excel file with electrical data
3. Review the AI-extracted data
4. Make manual corrections if needed
5. Integrate with calculations

### Manual Data Entry

1. Go to **⚙️ Project Setup** to create a project
2. Use **🔧 Equipment Config** to add:
   - Loads (motors, lighting, HVAC, etc.)
   - Buses (distribution points)
   - Transformers
   - Cables
   - Breakers
3. Navigate to **📊 Design & Analysis** to run calculations
4. Generate reports and export results

### Vector Knowledge Search

1. Open **🤖 AI Tools**
2. Use the search interface to query electrical knowledge
3. Get context-aware recommendations
4. Save useful patterns for future use

## 📁 Project Structure

```
d:/SLD Design/
├── src/                          # Source code
│   ├── app.py                    # Main Streamlit application
│   ├── models.py                 # Data models
│   ├── calculations.py           # Electrical calculations
│   ├── standards.py              # Standards framework
│   ├── vector_database_manager.py # Vector DB integration
│   ├── llm_multimodal_processor.py # LLM processor
│   ├── ai_excel_extractor.py     # AI extraction
│   └── unified_processor.py      # Unified pipeline
├── data/                         # Input data
├── output/                       # Generated files
├── vector_db/                    # ChromaDB storage
├── docs/                         # Documentation
├── .env                          # API keys (create from .env.example)
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── START_APP.bat                 # Windows quick start
└── README.md                     # This file
```

## 🔧 Configuration

### API Keys

Get your API key from:
- **Google Gemini:** https://makersuite.google.com/app/apikey
- **OpenAI:** https://platform.openai.com/api-keys
- **Anthropic:** https://console.anthropic.com/

Add to `.env`:
```bash
GOOGLE_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here  # Optional
ANTHROPIC_API_KEY=your_key_here  # Optional
```

### Vector Database

The system automatically creates and manages a ChromaDB vector database in `./vector_db/`.

**Collections:**
- `electrical_excel_headers` - Excel column mapping history
- `electrical_components` - Component specifications
- `electrical_design_patterns` - Design patterns
- `electrical_standards` - Standards knowledge
- `component_recommendations` - Component recommendations
- `design_history` - Design history

## 📚 Documentation

- [SYSTEM_AUDIT_REPORT.md](SYSTEM_AUDIT_REPORT.md) - Complete system audit
- [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md) - Integration architecture
- [VERIFICATION_COMPLETE.md](VERIFICATION_COMPLETE.md) - Verification results
- `docs/` - Additional documentation

## 🧪 Testing

Run integration tests:
```bash
python test_quick_integration.py
```

## 🐛 Troubleshooting

### LLM Features Not Working
- Check that `GOOGLE_API_KEY` is set in `.env`
- Verify API key is valid
- Check internet connection

### Import Errors
```bash
pip install -r requirements.txt
```

### Vector Database Errors
- Delete `vector_db/` directory and restart the app
- The database will be recreated automatically

### Application Won't Start
- Verify Python 3.8+ is installed: `python --version`
- Check all dependencies are installed
- Try reinstalling: `pip install -r requirements.txt --force-reinstall`

## 📊 System Status

✅ **All systems operational**
- LLM Integration: Working
- Vector Database: Working
- AI Excel Extraction: Working
- Calculations: Working
- Manual Workflows: Working
- All Pages: Working

## 🔄 Updates

To update dependencies:
```bash
pip install -r requirements.txt --upgrade
```

## 📄 License

[Your License Here]

## 🤝 Contributing

[Your Contributing Guidelines Here]

## 📧 Support

[Your Support Contact Here]

---

**Last Updated:** 2025-11-08  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
"# sld-design" 
