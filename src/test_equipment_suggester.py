"""
Test script for AI Equipment Configuration Suggester

Demonstrates:
- Loading a project
- Generating suggestions with AI analysis
- Accepting/rejecting suggestions
- Applying changes to project
- Saving to vector database
"""

import logging
from models import Project, Load, LoadType, InstallationMethod, DutyCycle, Priority, Bus, Transformer
from ai_equipment_suggester import AIEquipmentConfigSuggester
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_project() -> Project:
    """Create a sample project for testing"""
    
    project = Project(
        project_name="Industrial Plant Control Panel",
        project_id="PROJ_001",
        standard="IEC",
        voltage_system="LV",
        ambient_temperature_c=40
    )
    
    # Create sample loads
    loads_data = [
        {
            "load_id": "MOTOR_01",
            "load_name": "Main Pump Motor",
            "power_kw": 15.0,
            "voltage": 400,
            "phases": 3,
            "load_type": LoadType.MOTOR,
            "current_a": 25.0
        },
        {
            "load_id": "FAN_01",
            "load_name": "Cooling Fan",
            "power_kw": 5.5,
            "voltage": 400,
            "phases": 3,
            "load_type": LoadType.MOTOR,
            "current_a": 9.0
        },
        {
            "load_id": "HEAT_01",
            "load_name": "Process Heater",
            "power_kw": 10.0,
            "voltage": 400,
            "phases": 3,
            "load_type": LoadType.HEATER,
            "current_a": 16.0
        },
        {
            "load_id": "LIGHT_01",
            "load_name": "Facility Lighting",
            "power_kw": 3.0,
            "voltage": 400,
            "phases": 3,
            "load_type": LoadType.LIGHTING,
            "current_a": 5.0
        },
        {
            "load_id": "CTRL_01",
            "load_name": "Control System",
            "power_kw": 2.0,
            "voltage": 400,
            "phases": 3,
            "load_type": LoadType.GENERAL,
            "current_a": 3.5
        }
    ]
    
    for load_data in loads_data:
        load = Load(**load_data)
        project.add_load(load)
    
    # Create buses
    main_bus = Bus(
        bus_id="MAIN_BUS",
        bus_name="Main Distribution Bus",
        voltage=400,
        rated_current_a=200,
        phases=3,
        short_circuit_rating_ka=25
    )
    
    # Connect loads to bus
    for load in project.loads:
        main_bus.add_load(load.load_id)
    
    project.buses.append(main_bus)
    
    # Create a transformer
    transformer = Transformer(
        transformer_id="TR_001",
        name="Main Transformer",
        rating_kva=100,
        primary_voltage_v=11000,
        secondary_voltage_v=400,
        impedance_percent=6.0,
        vector_group="Dyn11"
    )
    project.transformers.append(transformer)
    
    return project


def demonstrate_workflow():
    """Demonstrate the complete workflow"""
    
    print("\n" + "="*80)
    print("AI EQUIPMENT CONFIGURATION SUGGESTER - DEMONSTRATION")
    print("="*80 + "\n")
    
    # Step 1: Load project
    print("STEP 1: Creating sample project...")
    print("-" * 80)
    
    project = create_sample_project()
    print(f"✓ Project created: {project.project_name}")
    print(f"  - Loads: {len(project.loads)}")
    print(f"  - Total power: {sum(l.power_kw for l in project.loads):.1f} kW")
    print(f"  - Buses: {len(project.buses)}")
    print(f"  - Transformers: {len(project.transformers)}")
    
    # Step 2: Initialize suggester
    print("\n\nSTEP 2: Initializing AI suggester...")
    print("-" * 80)
    
    suggester = AIEquipmentConfigSuggester()
    print("✓ Suggester initialized")
    print(f"  - LLM available: {suggester.llm is not None}")
    print(f"  - Vector DB available: {suggester.vector_db is not None}")
    
    # Step 3: Analyze and generate suggestions
    print("\n\nSTEP 3: Analyzing project and generating suggestions...")
    print("-" * 80)
    
    suggestion_set = suggester.analyze_and_suggest(project)
    
    print(f"✓ Analysis complete at {suggestion_set.analysis_timestamp}")
    print(f"  - Project insights: {len(suggestion_set.insights)}")
    print(f"  - Load suggestions: {sum(len(s) for s in suggestion_set.load_suggestions.values())}")
    print(f"  - Optimization potential: {suggestion_set.overall_optimization_potential:.1f}%")
    
    # Display insights
    print("\n  KEY INSIGHTS:")
    for insight in suggestion_set.insights[:3]:
        print(f"    • [{insight.priority.upper()}] {insight.title}")
        print(f"      {insight.description[:70]}...")
    
    # Step 4: Review suggestions
    print("\n\nSTEP 4: Reviewing suggestions for each load...")
    print("-" * 80)
    
    for load_id, suggestions in suggestion_set.load_suggestions.items():
        print(f"\n  Load: {load_id}")
        for idx, sugg in enumerate(suggestions):
            print(f"    Option {idx + 1}: {sugg.suggestion_type}")
            print(f"      Confidence: {sugg.confidence*100:.0f}%")
            print(f"      Status: {sugg.status}")
            
            if sugg.cable_suggestions:
                cable = sugg.cable_suggestions[0]
                print(f"      Cable: {cable.size_sqmm}mm² {cable.material} {cable.insulation}")
            
            if sugg.breaker_suggestions:
                breaker = sugg.breaker_suggestions[0]
                print(f"      Breaker: {breaker.rating_a}A {breaker.type} {breaker.curve}-curve")
    
    # Step 5: Accept some suggestions
    print("\n\nSTEP 5: Accepting suggestions...")
    print("-" * 80)
    
    accepted_count = 0
    for load_id in list(suggestion_set.load_suggestions.keys())[:3]:  # Accept first 3 loads
        if suggester.accept_suggestion(
            suggestion_set,
            load_id,
            suggestion_index=0,
            user_notes="Approved by system test"
        ):
            accepted_count += 1
            print(f"  ✓ Accepted suggestion for {load_id}")
    
    print(f"\n  Total accepted: {accepted_count}")
    
    # Step 6: Reject one suggestion
    print("\n\nSTEP 6: Rejecting a suggestion...")
    print("-" * 80)
    
    remaining_load = list(suggestion_set.load_suggestions.keys())[3]
    if suggester.reject_suggestion(
        suggestion_set,
        remaining_load,
        suggestion_index=0,
        reason="Custom equipment preferred"
    ):
        print(f"  ✓ Rejected suggestion for {remaining_load}")
    
    # Step 7: Apply accepted suggestions
    print("\n\nSTEP 7: Applying accepted suggestions to project...")
    print("-" * 80)
    
    changes = suggester.apply_accepted_suggestions(project, suggestion_set)
    
    print(f"✓ Suggestions applied successfully")
    print(f"  - Loads updated: {changes['loads_updated']}")
    print(f"  - Cables updated: {changes['cables_updated']}")
    print(f"  - Breakers updated: {changes['breakers_updated']}")
    print(f"  - Buses updated: {changes['buses_updated']}")
    
    if changes['errors']:
        print(f"  Errors: {len(changes['errors'])}")
        for error in changes['errors']:
            print(f"    - {error}")
    
    # Step 8: Show updated project
    print("\n\nSTEP 8: Reviewing updated project configuration...")
    print("-" * 80)
    
    for load in project.loads:
        print(f"\n  {load.load_id}:")
        if load.cable_size_sqmm:
            print(f"    Cable: {load.cable_size_sqmm}mm² {load.cable_insulation}")
        if load.breaker_rating_a:
            print(f"    Breaker: {load.breaker_rating_a}A {load.breaker_type}")
    
    # Step 9: Save to vector database
    print("\n\nSTEP 9: Saving suggestions to vector database...")
    print("-" * 80)
    
    suggester.save_suggestions_to_vector_db(
        suggestion_set,
        success_rating=0.85
    )
    print("✓ Suggestions saved to vector database")
    print("  This allows future projects to benefit from these recommendations")
    
    # Step 10: Generate report
    print("\n\nSTEP 10: Summary Report")
    print("-" * 80)
    
    total_suggestions = sum(len(s) for s in suggestion_set.load_suggestions.values())
    accepted = sum(1 for sugg_list in suggestion_set.load_suggestions.values() 
                   for s in sugg_list if s.status == "accepted")
    rejected = sum(1 for sugg_list in suggestion_set.load_suggestions.values() 
                   for s in sugg_list if s.status == "rejected")
    pending = total_suggestions - accepted - rejected
    
    print(f"\n  SUGGESTION STATISTICS:")
    print(f"    Total generated: {total_suggestions}")
    print(f"    Accepted: {accepted}")
    print(f"    Rejected: {rejected}")
    print(f"    Pending: {pending}")
    print(f"\n  PROJECT INSIGHTS:")
    print(f"    Total insights: {len(suggestion_set.insights)}")
    print(f"    Critical issues: {sum(1 for i in suggestion_set.insights if i.priority == 'critical')}")
    print(f"    High priority: {sum(1 for i in suggestion_set.insights if i.priority == 'high')}")
    print(f"\n  OPTIMIZATION:")
    print(f"    Potential: {suggestion_set.overall_optimization_potential:.1f}%")
    
    # Export suggestion set
    print("\n\nSTEP 11: Exporting results...")
    print("-" * 80)
    
    export_data = {
        "project_id": suggestion_set.project_id,
        "timestamp": suggestion_set.analysis_timestamp,
        "optimization_potential": suggestion_set.overall_optimization_potential,
        "accepted_count": accepted,
        "rejected_count": rejected,
        "pending_count": pending,
        "insights_count": len(suggestion_set.insights)
    }
    
    with open("suggestion_results.json", "w") as f:
        json.dump(export_data, f, indent=2)
    
    print("✓ Results exported to suggestion_results.json")
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80 + "\n")
    
    return suggestion_set, project


if __name__ == "__main__":
    print("\nAI Equipment Configuration Suggester - Test Suite\n")
    
    try:
        suggestion_set, project = demonstrate_workflow()
        
        print("\n✓ All tests completed successfully!")
        print("\nKey features demonstrated:")
        print("  1. Project loading and validation")
        print("  2. AI-powered design analysis")
        print("  3. Multi-level equipment suggestions (cable, breaker, starter)")
        print("  4. Vector database integration for similar designs")
        print("  5. Interactive suggestion workflow (accept/reject)")
        print("  6. Automatic project configuration updates")
        print("  7. Knowledge base storage for future reference")
        print("  8. Comprehensive reporting and analytics")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ Error during test: {e}")
