"""
Quick integration examples for Equipment Suggester

Shows how to integrate the suggester into your existing workflows.
"""

import logging
from models import Project, Load, LoadType, Bus, Transformer
from ai_equipment_suggester import AIEquipmentConfigSuggester
from datetime import datetime
import json

logger = logging.getLogger(__name__)


# =============================================================================
# EXAMPLE 1: Simple Single-Load Suggestion
# =============================================================================

def example_single_load():
    """Get suggestions for a single load"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Single Load Equipment Suggestion")
    print("="*80)
    
    # Create a simple load
    load = Load(
        load_id="PUMP_01",
        load_name="Main Circulation Pump",
        power_kw=11.0,
        voltage=400,
        phases=3,
        load_type=LoadType.MOTOR,
        power_factor=0.85
    )
    load.current_a = 20.0
    
    # Initialize suggester
    suggester = AIEquipmentConfigSuggester()
    
    # Get suggestions for this load
    suggestions = suggester.equipment_suggester.suggest_cable(load)
    print(f"\nCable Suggestions for {load.load_id}:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n  Option {i}:")
        print(f"    Size: {suggestion.size_sqmm}mm²")
        print(f"    Material: {suggestion.material}")
        print(f"    Type: {suggestion.type}")
        print(f"    Confidence: {suggestion.confidence*100:.0f}%")
        print(f"    Reason: {suggestion.reasoning}")
    
    # Get breaker suggestions
    breaker_suggestions = suggester.equipment_suggester.suggest_breaker(load)
    print(f"\nBreaker Suggestions for {load.load_id}:")
    for i, suggestion in enumerate(breaker_suggestions, 1):
        print(f"\n  Option {i}:")
        print(f"    Rating: {suggestion.rating_a}A")
        print(f"    Type: {suggestion.type}")
        print(f"    Curve: {suggestion.curve}")
        print(f"    Confidence: {suggestion.confidence*100:.0f}%")


# =============================================================================
# EXAMPLE 2: Project Analysis Workflow
# =============================================================================

def example_project_analysis():
    """Complete project analysis workflow"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Complete Project Analysis")
    print("="*80)
    
    # Create project
    project = Project(
        project_name="Factory Extension",
        project_id="FACTORY_EXT_2024"
    )
    
    # Add loads
    loads = [
        Load("MOTOR_1", "Main Motor", 30, 400, 3, LoadType.MOTOR, current_a=50),
        Load("MOTOR_2", "Backup Motor", 15, 400, 3, LoadType.MOTOR, current_a=25),
        Load("HEATER_1", "Process Heater", 20, 400, 3, LoadType.HEATER, current_a=35),
        Load("LIGHT_1", "Factory Lighting", 5, 400, 3, LoadType.LIGHTING, current_a=10),
    ]
    
    for load in loads:
        project.add_load(load)
    
    # Create main bus
    bus = Bus(
        bus_id="MAIN_BUS",
        bus_name="Main Distribution",
        voltage=400,
        rated_current_a=250,
        phases=3
    )
    for load in loads:
        bus.add_load(load.load_id)
    project.buses.append(bus)
    
    # Initialize suggester
    suggester = AIEquipmentConfigSuggester()
    
    # Analyze project
    print("\nAnalyzing project...")
    suggestion_set = suggester.analyze_and_suggest(project)
    
    # Display results
    print(f"\n✓ Analysis complete!")
    print(f"\n  Optimization Potential: {suggestion_set.overall_optimization_potential:.1f}%")
    
    print(f"\n  Key Insights ({len(suggestion_set.insights)}):")
    for insight in suggestion_set.insights[:3]:
        priority_icon = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }.get(insight.priority, "●")
        
        print(f"    {priority_icon} {insight.title}")
        print(f"       {insight.description[:60]}...")
    
    print(f"\n  Load Suggestions Generated: {sum(len(s) for s in suggestion_set.load_suggestions.values())}")
    
    return suggestion_set, project


# =============================================================================
# EXAMPLE 3: Accept/Reject Workflow
# =============================================================================

def example_accept_reject_workflow():
    """Show how to accept/reject suggestions"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Accept/Reject Suggestion Workflow")
    print("="*80)
    
    # Get project and suggestions
    suggestion_set, project = example_project_analysis()
    
    suggester = AIEquipmentConfigSuggester()
    
    # Accept first two
    loads = list(suggestion_set.load_suggestions.keys())
    
    print(f"\nAccepting suggestions...")
    for load_id in loads[:2]:
        if suggester.accept_suggestion(
            suggestion_set,
            load_id,
            user_notes="Approved - meets requirements"
        ):
            print(f"  ✓ {load_id}: Accepted")
    
    # Reject one
    if len(loads) > 2:
        if suggester.reject_suggestion(
            suggestion_set,
            loads[2],
            reason="Custom equipment required"
        ):
            print(f"  ✗ {loads[2]}: Rejected - {suggestion_set.rejection_reasons.get(loads[2])}")
    
    # Summary
    accepted = sum(1 for s in suggestion_set.load_suggestions.values() 
                  for ss in s if ss.status == "accepted")
    rejected = sum(1 for s in suggestion_set.load_suggestions.values() 
                  for ss in s if ss.status == "rejected")
    
    print(f"\n  Summary:")
    print(f"    Accepted: {accepted}")
    print(f"    Rejected: {rejected}")
    
    return suggestion_set, project


# =============================================================================
# EXAMPLE 4: Apply Changes to Project
# =============================================================================

def example_apply_changes():
    """Show how to apply suggestions to project"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Apply Suggestions to Project")
    print("="*80)
    
    # Get project and suggestions with decisions
    suggestion_set, project = example_accept_reject_workflow()
    
    suggester = AIEquipmentConfigSuggester()
    
    # Apply all accepted suggestions
    print(f"\nApplying {sum(1 for s in suggestion_set.load_suggestions.values() for ss in s if ss.status == 'accepted')} suggestions...")
    
    changes = suggester.apply_accepted_suggestions(project, suggestion_set)
    
    print(f"\n✓ Changes Applied:")
    print(f"  Loads updated: {changes['loads_updated']}")
    print(f"  Cables updated: {changes['cables_updated']}")
    print(f"  Breakers updated: {changes['breakers_updated']}")
    
    # Show updated configurations
    print(f"\nUpdated Load Configurations:")
    for load in project.loads:
        if load.cable_size_sqmm or load.breaker_rating_a:
            print(f"\n  {load.load_id}:")
            if load.cable_size_sqmm:
                print(f"    Cable: {load.cable_size_sqmm}mm² {load.cable_type}")
            if load.breaker_rating_a:
                print(f"    Breaker: {load.breaker_rating_a}A {load.breaker_type}")
    
    return suggestion_set, project


# =============================================================================
# EXAMPLE 5: Save and Retrieve from Vector DB
# =============================================================================

def example_vector_db_integration():
    """Show vector database integration"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Vector Database Integration")
    print("="*80)
    
    # Get project and apply changes
    suggestion_set, project = example_apply_changes()
    
    suggester = AIEquipmentConfigSuggester()
    
    # Save to knowledge base
    print(f"\nSaving suggestions to vector database...")
    suggester.save_suggestions_to_vector_db(
        suggestion_set,
        success_rating=0.88
    )
    print("✓ Saved successfully")
    
    # Now when you process similar projects, they'll benefit from this knowledge
    print("\nKnowledge Base Benefits:")
    print("  - Future similar projects get better suggestions")
    print("  - Patterns from this project inform new designs")
    print("  - Success ratings improve recommendations over time")
    
    if suggester.vector_db:
        # Show what's in the vector DB
        print("\nVector Database Collections:")
        stats = suggester.vector_db.get_collection_stats()
        for collection_type, info in stats.items():
            count = info.get('count', 0)
            print(f"  - {collection_type}: {count} items")


# =============================================================================
# EXAMPLE 6: Export Results
# =============================================================================

def example_export_results():
    """Show how to export suggestion results"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Export Results")
    print("="*80)
    
    suggestion_set, project = example_project_analysis()
    
    # Build export data
    export_data = {
        "project": {
            "id": suggestion_set.project_id,
            "name": "Factory Extension",
            "analysis_timestamp": suggestion_set.analysis_timestamp,
        },
        "analysis": {
            "optimization_potential": suggestion_set.overall_optimization_potential,
            "total_insights": len(suggestion_set.insights),
            "total_suggestions": sum(len(s) for s in suggestion_set.load_suggestions.values())
        },
        "insights": [
            {
                "type": i.insight_type,
                "title": i.title,
                "priority": i.priority,
                "confidence": i.confidence
            }
            for i in suggestion_set.insights[:5]
        ],
        "suggestions_by_load": {
            load_id: {
                "count": len(suggestions),
                "primary_confidence": suggestions[0].confidence if suggestions else 0
            }
            for load_id, suggestions in suggestion_set.load_suggestions.items()
        }
    }
    
    # Save as JSON
    filename = f"suggestions_{suggestion_set.project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"\n✓ Results exported to: {filename}")
    print(f"\nExport contains:")
    print(f"  - Project metadata")
    print(f"  - Analysis summary")
    print(f"  - Top {len(export_data['insights'])} insights")
    print(f"  - Suggestions per load")


# =============================================================================
# EXAMPLE 7: Integration with Existing System
# =============================================================================

def example_system_integration():
    """Show how to integrate with your existing system"""
    print("\n" + "="*80)
    print("EXAMPLE 7: Integration Pattern")
    print("="*80)
    
    print("""
Integration Steps:
    
1. In your data loading module:
    
    from ai_equipment_suggester import AIEquipmentConfigSuggester
    
    # After loading project...
    suggester = AIEquipmentConfigSuggester()
    suggestion_set = suggester.analyze_and_suggest(project)

2. In your UI/API:
    
    # Show suggestions to user
    for insight in suggestion_set.insights:
        display_insight(insight)
    
    # Let user decide
    if user_accepts(suggestion_set, load_id):
        suggester.accept_suggestion(suggestion_set, load_id)

3. On save/commit:
    
    # Apply and save
    changes = suggester.apply_accepted_suggestions(project, suggestion_set)
    suggester.save_suggestions_to_vector_db(suggestion_set)
    save_project(project)

4. Future projects:
    
    # Automatically benefit from learned patterns
    new_suggestion_set = suggester.analyze_and_suggest(new_project)
    # Suggestions will reference similar historical designs
    """)


# =============================================================================
# Main Runner
# =============================================================================

def main():
    """Run all examples"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "  AI EQUIPMENT SUGGESTER - INTEGRATION EXAMPLES".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    try:
        # Run examples
        example_single_load()
        example_project_analysis()
        example_accept_reject_workflow()
        example_apply_changes()
        example_vector_db_integration()
        example_export_results()
        example_system_integration()
        
        print("\n" + "="*80)
        print("✓ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nNext steps:")
        print("  1. Review the EQUIPMENT_SUGGESTER_GUIDE.md for detailed docs")
        print("  2. Run test_equipment_suggester.py for comprehensive testing")
        print("  3. Integrate into your application using the patterns shown")
        print("  4. Check equipment_suggestion_ui.py for Streamlit integration")
        print("\n")
        
    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")


if __name__ == "__main__":
    main()
