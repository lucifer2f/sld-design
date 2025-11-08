# AI Equipment Suggester - Quick Start Guide

## 30-Second Overview

Get intelligent equipment suggestions (cable, breaker, starter) for electrical loads using AI + vector database knowledge.

## Installation

Already integrated into your SLD Design system. Just use:

```python
from ai_equipment_suggester import AIEquipmentConfigSuggester
```

## Minimal Example

```python
from models import Project, Load, LoadType
from ai_equipment_suggester import AIEquipmentConfigSuggester

# 1. Create a project
project = Project(project_name="My Design")

# 2. Add a load
load = Load("MOTOR_01", "My Motor", 15.0, 400, 3, LoadType.MOTOR, current_a=25.0)
project.add_load(load)

# 3. Get suggestions
suggester = AIEquipmentConfigSuggester()
suggestion_set = suggester.analyze_and_suggest(project)

# 4. View suggestions
for load_id, suggestions in suggestion_set.load_suggestions.items():
    for suggestion in suggestions:
        print(f"Load {load_id}:")
        if suggestion.cable_suggestions:
            cable = suggestion.cable_suggestions[0]
            print(f"  Cable: {cable.size_sqmm}mm² {cable.material}")
        if suggestion.breaker_suggestions:
            breaker = suggestion.breaker_suggestions[0]
            print(f"  Breaker: {breaker.rating_a}A {breaker.type}")

# 5. Accept suggestion
suggester.accept_suggestion(suggestion_set, "MOTOR_01")

# 6. Apply to project
suggester.apply_accepted_suggestions(project, suggestion_set)
```

## Web UI (Recommended for Users)

```bash
streamlit run src/equipment_suggestion_ui.py
```

Then:
1. Upload your project (JSON/Excel)
2. Click "Analyze Project"
3. Review suggestions
4. Accept or reject with one click
5. Download updated configuration

## What You Get

### Per Load:
- ✅ Cable size (mm²) with material & insulation
- ✅ Breaker rating (A) with type & curve  
- ✅ Starter type (if needed)
- ✅ Confidence score (0-100%)
- ✅ Alternative options
- ✅ Full reasoning

### For Project:
- ✅ AI insights (optimization, risk, patterns)
- ✅ Bus/panel sizing
- ✅ Transformer recommendations
- ✅ Overall optimization potential %

## Workflow

```
┌─────────────────┐
│  Load Project   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ AI Analysis             │
│ • Design check          │
│ • Safety analysis       │
│ • Pattern matching      │
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Generate Suggestions     │
│ • Cable options          │
│ • Breaker options        │
│ • Starter recommendations│
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ User Review              │
│ ✅ Accept               │
│ ❌ Reject               │
│ 📝 Edit                 │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Apply Changes            │
│ Update project config    │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Save Learning            │
│ Add to knowledge base    │
│ Improve future suggestions
└──────────────────────────┘
```

## Common Tasks

### Get Cable Suggestion for One Load
```python
load = project.get_load_by_id("MOTOR_01")
cables = suggester.equipment_suggester.suggest_cable(load)
print(f"Recommended: {cables[0].size_sqmm}mm² {cables[0].material}")
```

### Get Breaker Suggestion
```python
breakers = suggester.equipment_suggester.suggest_breaker(load)
print(f"Recommended: {breakers[0].rating_a}A {breakers[0].type}")
```

### Get Bus Configuration
```python
buses = project.buses
for bus in buses:
    bus_suggestion = suggester._suggest_bus_configuration(bus, project)
    print(f"{bus.bus_id}: {bus_suggestion.recommended_short_circuit_rating_ka}kA")
```

### Accept All High-Confidence Suggestions
```python
for load_id, suggestions in suggestion_set.load_suggestions.items():
    if suggestions[0].confidence > 0.95:
        suggester.accept_suggestion(suggestion_set, load_id)
```

### Export as JSON
```python
export_data = {
    "project_id": suggestion_set.project_id,
    "suggestions": {}
}
for load_id, suggestions in suggestion_set.load_suggestions.items():
    export_data["suggestions"][load_id] = {
        "cable": suggestions[0].cable_suggestions[0].__dict__,
        "breaker": suggestions[0].breaker_suggestions[0].__dict__,
    }

import json
with open("export.json", "w") as f:
    json.dump(export_data, f, indent=2)
```

## Key Parameters

### Cable Sizing
```
Design Current = Load Current × 1.25 (safety margin)
Cable Size = First standard size with sufficient ampacity
```

**Standard sizes (mm²):** 1, 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300

### Breaker Sizing
```
Breaker Rating = Load Current × 1.25 (minimum)
Selected Rating = Next standard rating that fits
```

**Standard ratings (A):** 6, 10, 13, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 320

### Starter
- **Not required**: < 3 kW
- **Direct Online**: 3-10 kW
- **Soft Starter or VFD**: > 10 kW

## Confidence Interpretation

| Score | Meaning |
|-------|---------|
| 90-100% | High confidence - based on standards & multiple sources |
| 75-89% | Good confidence - meets main criteria |
| 60-74% | Moderate - some uncertainty, needs review |
| <60% | Lower confidence - needs careful consideration |

## What Can Go Wrong (& Fixes)

| Issue | Cause | Fix |
|-------|-------|-----|
| No suggestions | LLM API key invalid | Check API key in LLMConfig |
| Low confidence | Unusual load parameters | Review load specs |
| Vector DB empty | First time usage | Run a few projects to build knowledge |
| Slow analysis | API latency | Can parallelize across loads |
| Import errors | Missing dependencies | Check requirements.txt |

## Integration Checklist

- [ ] Import suggester: `from ai_equipment_suggester import ...`
- [ ] Initialize: `suggester = AIEquipmentConfigSuggester()`
- [ ] Load project with loads (must have current_a, voltage, power_kw)
- [ ] Call analyze: `suggestion_set = suggester.analyze_and_suggest(project)`
- [ ] Review results (insights + suggestions)
- [ ] Make decisions (accept/reject)
- [ ] Apply: `suggester.apply_accepted_suggestions(project, suggestion_set)`
- [ ] Save: `suggester.save_suggestions_to_vector_db(suggestion_set)`
- [ ] Export if needed (JSON/CSV)

## Running Tests

```bash
# Full workflow test
python src/test_equipment_suggester.py

# Integration examples
python src/equipment_suggester_example.py

# Web UI demo
streamlit run src/equipment_suggestion_ui.py
```

## Key Methods Reference

```python
# Main entry point
suggestion_set = suggester.analyze_and_suggest(project)

# Decisions
suggester.accept_suggestion(suggestion_set, load_id, suggestion_index, user_notes)
suggester.reject_suggestion(suggestion_set, load_id, suggestion_index, reason)

# Apply changes
changes = suggester.apply_accepted_suggestions(project, suggestion_set)

# Save learning
suggester.save_suggestions_to_vector_db(suggestion_set, success_rating)

# Individual equipment (no full analysis)
cables = suggester.equipment_suggester.suggest_cable(load)
breakers = suggester.equipment_suggester.suggest_breaker(load)
transformers = suggester.equipment_suggester.suggest_transformer(kw, kvar, v1, v2)
```

## Output Format

### SuggestionSet Structure
```python
{
    "project_id": "string",
    "analysis_timestamp": "ISO timestamp",
    "total_loads": int,
    "overall_optimization_potential": 0-100,
    "insights": [
        {
            "insight_type": "optimization|risk|pattern|efficiency",
            "title": "string",
            "description": "string",
            "priority": "critical|high|medium|low",
            "confidence": 0.0-1.0,
            "affected_items": ["load_id", ...]
        }
    ],
    "load_suggestions": {
        "load_id": [
            {
                "suggestion_type": "cable|breaker|starter|combination",
                "cable_suggestions": [...],
                "breaker_suggestions": [...],
                "starter_suggestion": {...},
                "confidence": 0.0-1.0,
                "status": "pending|accepted|rejected",
                "reasoning": "string"
            }
        ]
    }
}
```

## API Key Setup

```python
import os

# Option 1: Environment variable
os.environ['CLAUDE_API_KEY'] = 'your-key-here'
suggester = AIEquipmentConfigSuggester()

# Option 2: Direct parameter
suggester = AIEquipmentConfigSuggester(api_key='your-key-here')

# Option 3: .env file
# Create .env file with: CLAUDE_API_KEY=your-key-here
from dotenv import load_dotenv
load_dotenv()
suggester = AIEquipmentConfigSuggester()
```

## Performance Tips

1. **Batch processing**: Process multiple projects together
2. **Selective AI**: Only use LLM for complex cases
3. **Caching**: Vector DB caches recent queries
4. **Parallel**: Can parallelize across loads
5. **Export**: Save results for reuse

## Next Level

- **Custom Rules**: Add your specific standards
- **Multi-User**: Deploy with Streamlit sharing
- **API**: Wrap in FastAPI for system integration
- **Analytics**: Track acceptance rates and confidence over time
- **Compliance**: Tie to certification workflows

## Support

- **Full Docs**: `EQUIPMENT_SUGGESTER_GUIDE.md`
- **Examples**: `equipment_suggester_example.py`
- **Test Suite**: `test_equipment_suggester.py`
- **Web UI**: `equipment_suggestion_ui.py`

---

**That's it!** You now have AI-powered equipment suggestions. Start with the web UI or examples above. 🚀
