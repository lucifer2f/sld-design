# AI Equipment Configuration Suggester

## Overview

The AI Equipment Configuration Suggester is an intelligent system that analyzes electrical projects and provides AI-powered recommendations for equipment sizing and configuration. It integrates LLM capabilities with vector database knowledge for comprehensive design optimization.

### Key Features

- **Project Analysis**: Deep AI analysis of entire electrical systems
- **Smart Suggestions**: Intelligent recommendations for cables, breakers, starters
- **Confidence Scoring**: All suggestions include confidence metrics
- **Vector DB Integration**: Learns from historical designs and standards
- **Interactive Workflow**: Accept, reject, or modify suggestions
- **Auto-Update**: Automatically applies accepted configurations to project
- **Knowledge Base**: Saves decisions for future reference

## Architecture

### Components

```
AIEquipmentConfigSuggester (Main Engine)
├── AIEquipmentSuggester (Equipment sizing calculations)
├── AIDesignAnalyzer (Project-level analysis)
├── LLMMultimodalProcessor (AI engine - Claude/GPT)
└── VectorDatabaseManager (Knowledge base - ChromaDB)
```

### Data Flow

```
Project Input
    ↓
[Load Analysis] → Extract parameters, identify patterns
    ↓
[AI Analysis] → Design analysis, safety checks, standards compliance
    ↓
[Vector DB Search] → Find similar projects and components
    ↓
[LLM Processing] → Generate detailed recommendations
    ↓
[Suggestion Generation] → Cable, breaker, starter suggestions
    ↓
[User Review] → Accept/reject with confidence scoring
    ↓
[Apply Changes] → Update project configuration
    ↓
[Store Learning] → Save to vector DB for future use
```

## Usage

### Basic Usage

```python
from models import Project, Load
from ai_equipment_suggester import AIEquipmentConfigSuggester

# 1. Create or load your project
project = Project(project_name="My Electrical Design")
# ... add loads, buses, etc ...

# 2. Initialize suggester
suggester = AIEquipmentConfigSuggester(api_key="your-api-key")

# 3. Analyze and get suggestions
suggestion_set = suggester.analyze_and_suggest(project)

# 4. Review insights and suggestions
print(f"Optimization potential: {suggestion_set.overall_optimization_potential}%")
for insight in suggestion_set.insights:
    print(f"- {insight.title}: {insight.description}")

# 5. Accept or reject suggestions
suggester.accept_suggestion(suggestion_set, load_id="LOAD_01")
suggester.reject_suggestion(suggestion_set, load_id="LOAD_02", reason="Custom requirement")

# 6. Apply to project
changes = suggester.apply_accepted_suggestions(project, suggestion_set)

# 7. Save for future reference
suggester.save_suggestions_to_vector_db(suggestion_set)
```

### Streamlit UI Usage

The project includes a Streamlit web interface:

```bash
streamlit run src/equipment_suggestion_ui.py
```

**Workflow:**
1. **Load Project Tab**: Upload or create a project
2. **Analysis Tab**: Review AI insights and optimization potential
3. **Review Tab**: Accept or reject individual suggestions
4. **Apply Tab**: Apply changes and export results

## Suggestion Types

### 1. Equipment Suggestions (Per Load)

Each load receives recommendations for:

- **Cable**: Size (mm²), type (single/multi-core), material (copper/aluminum), insulation (XLPE/PVC)
- **Breaker**: Rating (A), type (MCB/MCCB/ACB), curve (B/C/D/K), breaking capacity
- **Starter**: Type (direct online, soft starter, VFD) with justification

### 2. Project Insights

Generated insights include:

- **Optimization**: Load balancing, efficiency improvements, cost reduction
- **Risk**: Safety concerns, compliance violations, design issues
- **Pattern**: Similar projects found in knowledge base
- **Efficiency**: Power factor correction, losses reduction opportunities

### 3. Bus Configuration Suggestions

For each bus/panel:

- Recommended short circuit rating
- Main breaker sizing
- Utilization analysis
- Headroom calculation

### 4. Transformer Suggestions

- KVA rating based on total load
- Primary/secondary voltage selection
- Connection type (Delta-Wye, etc.)
- Cooling type (oil-immersed, dry-type)

## Suggestion Set Structure

```python
@dataclass
class SuggestionSet:
    project_id: str
    analysis_timestamp: str
    total_loads: int
    
    # Results
    insights: List[ProjectInsight]
    load_suggestions: Dict[str, List[EquipmentConfigSuggestion]]
    bus_suggestions: Dict[str, BusConfigSuggestion]
    transformer_suggestions: List[TransformerConfigSuggestion]
    
    # Tracking
    accepted_suggestions: Dict[str, bool]
    rejection_reasons: Dict[str, str]
    overall_optimization_potential: float
```

### Suggestion Status Workflow

```
pending  →  (user decides)  →  accepted/rejected
           
accepted  →  (apply_accepted_suggestions)  →  applied
rejected  →  (store reason)  →  archived
```

## Confidence Scores

Confidence ranges from 0.0 to 1.0:

- **0.90-1.00**: High confidence, based on standards and multiple sources
- **0.75-0.89**: Good confidence, multiple criteria met
- **0.60-0.74**: Moderate confidence, some uncertainty
- **Below 0.60**: Lower confidence, needs review

Sources affecting confidence:
- Standards compliance checks
- Vector DB similarity matches
- Equipment ampacity calculations
- LLM analysis agreement
- Historical project similarity

## Vector Database Integration

### What Gets Stored

When you accept suggestions, they are saved as design history:

```
Design History Entry:
├── Load configuration
├── Equipment specifications
├── Reasoning and confidence
├── Project context
└── Success rating
```

### Retrieval for Future Projects

For similar loads, the system searches for:
- Similar power ratings
- Same voltage levels
- Matching load types (motor, heater, etc.)
- Same installation method

### Query Examples

```python
# Find similar configurations
results = vector_db.get_component_recommendations(
    query="Cable breaker 25A 400V motor",
    component_type="cable"
)

# Search design history
similar_projects = vector_db.search_design_history(
    query="Industrial plant with motors and heating"
)
```

## Configuration Parameters

### Equipment Sizing Standards

**Breaker Rating Calculation:**
```
Breaker Rating = Load Current × 1.25 (safety margin)
Selected Rating = Next standard size that fits range
```

**Cable Sizing:**
```
Design Current = Load Current × 1.25
Selected Cable = First size with ampacity ≥ Design Current
Temperature & Installation Derating Applied
```

**Standard Ratings:**

Cable Sizes (mm²): 1, 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300

Breaker Ratings (A): 6, 10, 13, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 320

## Customization

### Custom Confidence Weights

Modify confidence calculation in `_calculate_optimization_potential()`:

```python
def customize_confidence(suggestion, project_context):
    base_confidence = suggestion.confidence
    # Adjust based on project-specific factors
    if project_context.is_critical_system:
        base_confidence *= 0.95  # Increase conservatism
    return base_confidence
```

### Custom Insight Generation

Add custom insights in `_extract_project_insights()`:

```python
def add_custom_insights(project):
    # Your custom logic here
    insights.append(ProjectInsight(
        insight_type="custom",
        title="Your Insight",
        description="Your analysis"
    ))
```

## API Reference

### Main Methods

#### `analyze_and_suggest(project: Project) -> SuggestionSet`
Comprehensive project analysis and suggestion generation.

**Returns:**
- Complete SuggestionSet with insights and suggestions for all components

#### `accept_suggestion(suggestion_set, load_id, suggestion_index, user_notes) -> bool`
Accept a suggestion for implementation.

**Parameters:**
- `load_id`: ID of load to accept suggestion for
- `suggestion_index`: Index of suggestion (0 = top rated)
- `user_notes`: Optional justification

#### `reject_suggestion(suggestion_set, load_id, suggestion_index, reason) -> bool`
Reject a suggestion with reasoning.

#### `apply_accepted_suggestions(project, suggestion_set) -> Dict`
Apply all accepted suggestions to the project.

**Returns:**
- Dictionary with count of changes applied: `loads_updated`, `cables_updated`, etc.

#### `save_suggestions_to_vector_db(suggestion_set, success_rating) -> None`
Store accepted suggestions in knowledge base.

**Parameters:**
- `success_rating`: 0.0-1.0 quality rating of suggestions

## Example Scenarios

### Scenario 1: Load Balancing Optimization

```
Project: Multi-load system with unbalanced distribution
↓
AI Analysis: Identifies 60% load on one phase
↓
Suggestions: Redistribute loads to Phase B/C
↓
Impact: Better utilization, reduced cable heating
↓
Result: Smaller cables possible, cost savings
```

### Scenario 2: Safety Concern Resolution

```
Project: Motor load without proper protection
↓
AI Analysis: Missing breaker coordination
↓
Insight: Critical - upstream breaker smaller than downstream
↓
Suggestion: Upgrade upstream breaker to 100A
↓
Result: Proper protection cascade, safety compliance
```

### Scenario 3: Equipment Standardization

```
Project: New facility using mixed cable types
↓
Vector DB Search: Similar industrial projects
↓
Finding: Standard practice uses 2.5mm² PVC for <10A
↓
Suggestion: Standardize on PVC for consistency
↓
Benefit: Reduced inventory, easier maintenance
```

## Troubleshooting

### No Suggestions Generated

1. **Check vector DB**: Verify ChromaDB is initialized
2. **Verify loads**: Ensure loads have current_a calculated
3. **LLM issues**: Check API key and connectivity

### Low Confidence Scores

- Increase by finding similar historical projects
- Improve by refining project parameters
- Add more data to vector database

### Suggestions Not Applying

1. Verify suggestion status = "accepted"
2. Check project structure matches expected format
3. Review change report for errors

## Performance Considerations

### Optimization

- **Cache Results**: Vector DB caches recent queries
- **Batch Processing**: Process multiple loads together
- **Selective AI**: Use AI only for complex cases

### Scaling

- Vector DB handles 10K+ component records efficiently
- LLM calls optimized with prompt caching
- Suggestions computed in parallel

## Integration Points

### With Streamlit App

```python
# In your Streamlit app
from equipment_suggestion_ui import EquipmentSuggestionUI

ui = EquipmentSuggestionUI()
ui.render()
```

### With Design Analyzer

```python
# Leverage existing design analysis
analyzer = AIDesignAnalyzer()
design_analysis = analyzer.analyze_design(project)
# Use for insights and recommendations
```

### With Excel Importer

```python
# Process imported projects through suggester
project = parse_excel_project(excel_file)
suggestions = suggester.analyze_and_suggest(project)
```

## Future Enhancements

- [ ] Real-time collaboration on suggestion acceptance
- [ ] 3D visualization of suggested configurations
- [ ] Automated compliance certification
- [ ] Cost optimization algorithms
- [ ] Supply chain integration
- [ ] Regulatory compliance templates

## Support & Examples

See `test_equipment_suggester.py` for complete working examples:

```bash
python src/test_equipment_suggester.py
```

## License & Attribution

Part of SLD Design electrical system automation suite.
Integrates with industry standards (IEC, NEC, BS).
