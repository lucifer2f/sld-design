# Feature Organization Guide

## Core Features

### 1. Excel Extraction Feature
**Module**: `src/excel_extractor.py`

**Purpose**: Intelligent extraction of electrical design data from Excel spreadsheets

**Key Classes**:
- `AIExcelExtractor` - Main orchestrator for Excel processing
- `SheetClassifier` - Classifies Excel sheets by type
- `ColumnMapper` - Maps Excel columns to data model fields
- `DataExtractor` - Extracts structured data from sheets
- `DataEnhancer` - Enhances and normalizes extracted data
- `ValidationEngine` - Validates extracted data quality
- `LLMEngine` - Handles LLM-based semantic analysis
- `ExtractionResult` - Result container with confidence scoring
- `ProcessingReport` - Comprehensive extraction report

**Key Methods**:
- `process_excel_file()` - Main entry point
- `extract_loads()` - Extract load schedule data
- `extract_cables()` - Extract cable schedule data
- `extract_buses()` - Extract bus schedule data

**Used By**:
- `src/app.py` - Web UI Excel upload feature
- `src/integration_layer.py` - System integration
- `src/unified_processor.py` - Data processing pipeline

**Example Usage**:
```python
from excel_extractor import AIExcelExtractor

extractor = AIExcelExtractor(standard="IEC")
report = extractor.process_excel_file("project.xlsx")

print(f"Extracted {report.total_components} components")
print(f"Confidence: {report.overall_confidence:.2%}")
```

---

### 2. Design Analysis & Recommendations Feature
**Modules**: `src/design_analyzer.py`, `src/equipment_suggester.py`

**Purpose**: Provide intelligent design validation, analysis, and equipment recommendations

#### 2.1 Design Analyzer (`design_analyzer.py`)

**Purpose**: Comprehensive design validation and analysis

**Key Classes**:
- `AIDesignAnalyzer` - Main design analysis engine
- `DesignAnalysis` - Analysis results container
- `EquipmentSuggestion` - Equipment recommendation

**Key Methods**:
- `analyze_design()` - Full design analysis
- `validate_cable_selection()` - Cable validation
- `validate_breaker_coordination()` - Breaker coordination check
- `suggest_equipment()` - Get equipment suggestions

**Features**:
- Load validation
- Standards compliance checking
- Design pattern matching
- Safety concern identification
- Optimization recommendations
- Cable selection validation
- Breaker coordination analysis

**Example Usage**:
```python
from design_analyzer import AIDesignAnalyzer

analyzer = AIDesignAnalyzer()
analysis = analyzer.analyze_design(project)

print(f"Design Score: {analysis.overall_score}/100")
print(f"Issues: {len(analysis.validation_issues)}")
print(f"Safety Concerns: {len(analysis.safety_concerns)}")
```

#### 2.2 Equipment Suggester (`equipment_suggester.py`)

**Purpose**: Intelligent equipment sizing and configuration recommendations

**Key Classes**:
- `AIEquipmentSuggester` - Main equipment suggestion engine
- `CableRecommendation` - Cable sizing recommendation
- `BreakerRecommendation` - Breaker selection recommendation
- `TransformerRecommendation` - Transformer sizing recommendation

**Key Methods**:
- `suggest_cable()` - Get cable size recommendations
- `suggest_breaker()` - Get breaker recommendations
- `suggest_transformer()` - Get transformer recommendations
- `get_quick_configuration()` - Quick equipment configuration

**Features**:
- Cable ampacity calculation
- Cable type and material selection
- Breaker type and curve selection
- Breaker coordination notes
- Transformer kVA rating calculation
- Connection type selection
- LLM-enhanced suggestions
- Vector database lookup

**Example Usage**:
```python
from equipment_suggester import AIEquipmentSuggester

suggester = AIEquipmentSuggester()

# Cable recommendations
cables = suggester.suggest_cable(load, use_ai=True)
for cable in cables:
    print(f"Cable: {cable.size_sqmm}mm² {cable.material}")

# Quick configuration
config = suggester.get_quick_configuration(load)
print(f"Cable: {config['cable']}")
print(f"Breaker: {config['breaker']}")
```

---

## Feature Integration Points

### Data Flow

```
Excel File
    ↓
[Excel Extraction Feature]
    ├─ Sheet Classification
    ├─ Column Mapping
    ├─ Data Extraction
    └─ Validation
    ↓
Project Data Model
    ↓
[Design Analysis & Recommendations]
    ├─ Design Analyzer
    │   ├─ Load Validation
    │   ├─ Standards Compliance
    │   ├─ Safety Analysis
    │   └─ Design Patterns
    │
    └─ Equipment Suggester
        ├─ Cable Recommendations
        ├─ Breaker Selection
        └─ Transformer Sizing
    ↓
Web UI / Reports
```

### Web UI Integration (`src/app.py`)

**Excel Extraction Feature**:
- Upload Excel files
- View extraction results
- See confidence metrics
- Review extracted components
- Validate data quality

**Design Analysis Feature**:
- Analyze imported projects
- Get design recommendations
- View standards compliance
- Check safety concerns
- Get equipment suggestions

---

## Module Dependencies

### Excel Extractor Dependencies
```
excel_extractor.py
├── models.py (Load, Cable, Bus, Transformer, Project)
├── calculations.py (ElectricalCalculationEngine)
├── standards.py (StandardsFactory)
├── llm_multimodal_processor.py (LLM analysis)
├── vector_database_manager.py (Similarity search)
└── pandas, numpy (Data processing)
```

### Design Analyzer Dependencies
```
design_analyzer.py
├── models.py (Project, Load, Cable, Breaker, Transformer)
├── llm_multimodal_processor.py (LLM analysis)
├── vector_database_manager.py (Pattern lookup)
└── logging
```

### Equipment Suggester Dependencies
```
equipment_suggester.py
├── models.py (Load, Cable, Breaker, Transformer)
├── llm_multimodal_processor.py (LLM suggestions)
├── vector_database_manager.py (Spec lookup)
└── math
```

---

## Configuration

### Excel Extractor
```python
# Standard selection
extractor = AIExcelExtractor(standard="IEC")  # or "NFPA", "BS", etc.

# Sheet classification threshold
sheet_classifier = SheetClassifier(confidence_threshold=0.7)

# Column mapping
column_mapper = ColumnMapper(use_llm=True, use_vector_db=True)
```

### Design Analyzer
```python
# With API key
analyzer = AIDesignAnalyzer(api_key="your-key")

# Without API (fallback mode)
analyzer = AIDesignAnalyzer()
```

### Equipment Suggester
```python
# With API key
suggester = AIEquipmentSuggester(api_key="your-key")

# With vector database
# Automatically loads if available
```

---

## Testing

### Unit Tests
- `src/test_ai_extraction.py` - Excel extractor tests
- `src/test_models.py` - Data model tests
- `src/test_calculations.py` - Calculation tests

### Integration Tests
- `src/test_integration_workflow.py` - Full workflow
- `test_app_imports.py` - Import verification
- `run_system_tests.py` - System-level tests

---

## Future Enhancements

### Recommended Structure for Scaling
```
features/
├── excel_extraction/
│   ├── __init__.py
│   ├── extractor.py
│   ├── classifiers.py
│   ├── mappers.py
│   └── validators.py
│
├── design_analysis/
│   ├── __init__.py
│   ├── analyzer.py
│   ├── equipment_suggester.py
│   ├── validators.py
│   └── pattern_matcher.py
│
├── sld_generation/
│   ├── __init__.py
│   ├── generator.py
│   └── layout_engine.py
│
└── utilities/
    ├── models.py
    ├── calculations.py
    ├── standards.py
    └── vector_database_manager.py
```

---

## Quick Start

### 1. Extract from Excel
```python
from excel_extractor import AIExcelExtractor

extractor = AIExcelExtractor()
report = extractor.process_excel_file("electrical_project.xlsx")
project = report.project_data
```

### 2. Analyze Design
```python
from design_analyzer import AIDesignAnalyzer

analyzer = AIDesignAnalyzer()
analysis = analyzer.analyze_design(project)
```

### 3. Get Recommendations
```python
from equipment_suggester import AIEquipmentSuggester

suggester = AIEquipmentSuggester()
cable_recommendations = suggester.suggest_cable(load)
breaker_recommendations = suggester.suggest_breaker(load)
```

---

## Support & Troubleshooting

### Common Issues

**1. Import Errors**
- Ensure all files are in `src/` directory
- Check Python path includes `src/`
- Verify renamed files (excel_extractor, design_analyzer, equipment_suggester)

**2. LLM Not Available**
- Most features work in fallback mode
- Install LLM dependencies: `pip install -r requirements.txt`
- Set API keys in environment variables

**3. Vector Database Issues**
- Optional feature, system works without it
- Check vector_database_manager initialization
- Use in-memory fallback if needed

---

