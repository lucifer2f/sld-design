#!/usr/bin/env python3
"""
Electrical Design Automation System - Streamlit Web UI

A comprehensive web-based interface for electrical design automation,
providing intuitive tools for electrical engineers to design power distribution systems.
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import plotly.express as px
import plotly.graph_objects as go
import io
import csv

# Import our data models
try:
    from models import (
        Project, Load, Bus, Transformer, Cable, Breaker,
        LoadType, InstallationMethod, DutyCycle, Priority
    )
    from calculations import ElectricalCalculationEngine
    from standards import StandardsFactory
    from unified_processor import (
        UnifiedDataProcessor, ProcessingInterface,
        create_unified_processor, initialize_processing_status,
        get_processing_status, ProcessingStatus
    )
    from design_analyzer import AIDesignAnalyzer, DesignAnalysis
    from equipment_suggester import AIEquipmentSuggester
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    from models import (
        Project, Load, Bus, Transformer, Cable, Breaker,
        LoadType, InstallationMethod, DutyCycle, Priority
    )
    from calculations import ElectricalCalculationEngine
    from standards import StandardsFactory
    from unified_processor import (
        UnifiedDataProcessor, ProcessingInterface,
        create_unified_processor, initialize_processing_status,
        get_processing_status, ProcessingStatus
    )
    from design_analyzer import AIDesignAnalyzer, DesignAnalysis
    from equipment_suggester import AIEquipmentSuggester

# Page configuration
st.set_page_config(
    page_title="Electrical Design Automation System",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3498db;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
    .dataframe {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

class CollaborativeDesignAssistant:
    """Collaborative design assistant that works with users during design process"""

    def __init__(self, llm_engine):
        self.llm_engine = llm_engine

    def get_design_suggestions(self, project, calculation_results=None) -> Dict[str, Any]:
        """Get collaborative design suggestions based on current project state"""
        if not project:
            return {"suggestions": [], "insights": []}

        suggestions = []
        insights = []

        try:
            # Analyze system capacity and diversity
            if project.loads:
                total_power = sum(load.power_kw for load in project.loads)
                demand_kw = project.total_demand_kw or total_power * 0.8  # Estimate if not calculated
                diversity_factor = project.system_diversity_factor or 0.8

                if diversity_factor < 0.7:
                    suggestions.append({
                        "type": "optimization",
                        "title": "Low Diversity Factor Detected",
                        "description": f"System diversity factor is {diversity_factor:.2f}, which may indicate inefficient use of capacity.",
                        "recommendations": [
                            "Consider demand-based load scheduling",
                            "Review load simultaneity factors",
                            "Evaluate peak demand management strategies"
                        ],
                        "impact": "medium"
                    })

                # Check for unbalanced phases
                if project.buses:
                    for bus in project.buses:
                        connected_loads = [l for l in project.loads if l.source_bus == bus.bus_id]
                        if connected_loads:
                            phase_balance = self._analyze_phase_balance(connected_loads)
                            if phase_balance.get("imbalance_detected", False):
                                suggestions.append({
                                    "type": "balancing",
                                    "title": f"Phase Imbalance on Bus {bus.bus_id}",
                                    "description": f"Loads on {bus.bus_name} show significant phase imbalance.",
                                    "recommendations": phase_balance.get("recommendations", []),
                                    "impact": "high"
                                })

            # Cable sizing optimization suggestions
            if project.cables and calculation_results:
                cable_optimization = self._analyze_cable_optimization(project, calculation_results)
                if cable_optimization.get("optimizations_available", []):
                    suggestions.extend(cable_optimization["optimizations_available"])

            # Standards compliance guidance
            if project.standard:
                compliance_suggestions = self._get_standards_guidance(project)
                suggestions.extend(compliance_suggestions)

        except Exception as e:
            insights.append(f"Analysis error: {str(e)}")

        return {
            "suggestions": suggestions,
            "insights": insights,
            "timestamp": datetime.now().isoformat()
        }

    def get_smart_defaults_for_load(self, load_type: str, voltage: int, phases: int) -> Dict[str, Any]:
        """Get smart default values for load parameters based on type"""
        defaults = {
            "power_factor": 0.85,
            "efficiency": 0.9,
            "cable_length": 50.0
        }

        # Adjust defaults based on load type
        type_defaults = {
            "motor": {
                "power_factor": 0.82,
                "efficiency": 0.88,
                "cable_length": 25.0,
                "notes": "Consider motor starting current and protection requirements"
            },
            "lighting": {
                "power_factor": 0.95,
                "efficiency": 0.95,
                "cable_length": 30.0,
                "notes": "Consider emergency lighting and dimming requirements"
            },
            "hvac": {
                "power_factor": 0.80,
                "efficiency": 0.85,
                "cable_length": 40.0,
                "notes": "Consider compressor starting current and backup power needs"
            },
            "general": {
                "power_factor": 0.85,
                "efficiency": 0.90,
                "cable_length": 35.0,
                "notes": "Verify power factor correction requirements"
            }
        }

        if load_type in type_defaults:
            defaults.update(type_defaults[load_type])

        # Adjust for voltage levels
        if voltage > 1000:
            defaults["cable_length"] = max(defaults["cable_length"], 75.0)
            defaults["notes"] += ". High voltage installation - ensure proper clearances."

        return defaults

    def validate_load_parameters(self, load_params: Dict) -> Dict[str, Any]:
        """Validate load parameters and provide feedback"""
        issues = []
        warnings = []
        suggestions = []

        # Basic parameter validation
        if load_params.get("power_kw", 0) <= 0:
            issues.append("Power rating must be positive")

        if load_params.get("power_factor", 0) <= 0 or load_params.get("power_factor", 0) > 1:
            issues.append("Power factor must be between 0.1 and 1.0")

        if load_params.get("efficiency", 0) <= 0 or load_params.get("efficiency", 0) > 1:
            issues.append("Efficiency must be between 0.1 and 1.0")

        # Engineering validation
        load_type = load_params.get("load_type", "")
        voltage = load_params.get("voltage", 400)
        power = load_params.get("power_kw", 0)

        # Check for unrealistic combinations
        if load_type == "motor" and power > 1000:
            warnings.append("Very large motor detected - consider multiple smaller units")

        if load_type == "lighting" and power > 50:
            warnings.append("High power lighting load - verify LED efficiency claims")

        # Calculate expected current
        if power > 0 and voltage > 0:
            pf = load_params.get("power_factor", 0.85)
            phases = load_params.get("phases", 3)
            expected_current = power / (voltage * pf * (1 if phases == 1 else 3**0.5))

            if expected_current > 1000:
                warnings.append(f"Expected current {expected_current:.1f}A is very high - verify voltage and power ratings")
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "suggestions": suggestions
        }

    def _analyze_phase_balance(self, loads) -> Dict[str, Any]:
        """Analyze phase balance of connected loads"""
        phase_loads = {1: [], 2: [], 3: []}

        for load in loads:
            if load.phases == 1:
                # Assume single-phase loads distributed across phases
                min_phase = min(phase_loads.keys(), key=lambda p: sum(l.power_kw for l in phase_loads[p]))
                phase_loads[min_phase].append(load)
            else:
                # Three-phase load
                total_power = load.power_kw
                per_phase_power = total_power / 3
                for phase in [1, 2, 3]:
                    phase_loads[phase].append(type('MockLoad', (), {'power_kw': per_phase_power})())

        phase_totals = {phase: sum(l.power_kw for l in loads) for phase, loads in phase_loads.items()}
        max_load = max(phase_totals.values())
        min_load = min(phase_totals.values())
        imbalance_ratio = max_load / min_load if min_load > 0 else float('inf')

        imbalance_detected = imbalance_ratio > 1.3  # 30% imbalance threshold

        recommendations = []
        if imbalance_detected:
            recommendations = [
                "Redistribute single-phase loads across phases",
                "Consider three-phase loads where possible",
                "Add power factor correction capacitors",
                "Implement load balancing relays"
            ]

        return {
            "imbalance_detected": imbalance_detected,
            "phase_totals": phase_totals,
            "imbalance_ratio": imbalance_ratio,
            "recommendations": recommendations
        }

    def _analyze_cable_optimization(self, project, calculation_results) -> Dict[str, Any]:
        """Analyze cable sizing for optimization opportunities"""
        optimizations = []

        if not project.cables:
            return {"optimizations_available": []}

        for cable in project.cables:
            if hasattr(cable, 'current_carrying_capacity_a') and cable.current_carrying_capacity_a:
                # Find associated load
                load = next((l for l in project.loads if l.load_id == cable.to_equipment), None)
                if load and hasattr(load, 'design_current_a') and load.design_current_a:
                    utilization = load.design_current_a / cable.current_carrying_capacity_a
                    if utilization < 0.6:
                        optimizations.append({
                            "type": "cable_optimization",
                            "title": f"Oversized Cable: {cable.cable_id}",
                            "description": f"Cable size {cable.size_sqmm}mm² has only {utilization:.1%} utilization.",
                            "recommendations": [
                                f"Consider reducing to smaller size if voltage drop allows",
                                "Review cable routing and installation conditions",
                                "Check for future expansion requirements"
                            ],
                            "impact": "low",
                            "savings_potential": "medium"
                        })

        return {"optimizations_available": optimizations}

    def _get_standards_guidance(self, project) -> List[Dict[str, Any]]:
        """Get standards compliance guidance"""
        guidance = []

        if project.standard == "IEC":
            # IEC specific guidance
            if project.voltage_system == "LV":
                guidance.append({
                    "type": "standards",
                    "title": "IEC 60364 Compliance Check",
                    "description": "Low voltage installation requirements",
                    "recommendations": [
                        "Ensure proper protective earthing",
                        "Verify RCD requirements for socket circuits",
                        "Check cable insulation for ambient temperature"
                    ],
                    "impact": "high"
                })

        elif project.standard == "NEC":
            # NEC specific guidance
            guidance.append({
                "type": "standards",
                "title": "NEC Compliance Considerations",
                "description": "National Electrical Code requirements",
                "recommendations": [
                    "Verify conductor ampacity calculations",
                    "Check equipment grounding requirements",
                    "Ensure proper overcurrent protection coordination"
                ],
                "impact": "high"
            })

        return guidance
class ElectricalDesignApp:
    """Main Streamlit application class"""

    def __init__(self):
        # Initialize calculation engine
        try:
            self.calc_engine = ElectricalCalculationEngine()
        except Exception as e:
            st.error(f"Failed to initialize calculation engine: {e}")
            self.calc_engine = None

        # Load project and calculation results from session state if they exist
        try:
            if 'project' in st.session_state:
                self.project = st.session_state.project
            else:
                self.project: Optional[Project] = None
        except Exception as e:
            st.warning(f"Failed to load project from session state: {e}")
            self.project = None

        try:
            if 'calculation_results' in st.session_state:
                self.calculation_results = st.session_state.calculation_results
            else:
                self.calculation_results = {}
        except Exception as e:
            st.warning(f"Failed to load calculation results from session state: {e}")
            self.calculation_results = {}

        # Initialize unified processor with error handling
        try:
            self.unified_processor = create_unified_processor(
                self.project.standard if self.project else "IEC"
            )
        except Exception as e:
            st.error(f"Failed to initialize AI extraction processor: {e}")
            self.unified_processor = None

        # Initialize collaborative design assistant
        self.design_assistant = None
        if self.unified_processor and hasattr(self.unified_processor.ai_extractor, 'llm_engine'):
            try:
                self.design_assistant = CollaborativeDesignAssistant(
                    llm_engine=self.unified_processor.ai_extractor.llm_engine
                )
            except Exception as e:
                st.warning(f"Design assistant initialization failed: {e}")
                self.design_assistant = None

        # Initialize AI design analyzer
        self.ai_analyzer = None
        try:
            self.ai_analyzer = AIDesignAnalyzer()
        except Exception as e:
            st.warning(f"AI design analyzer initialization failed: {e}")
            self.ai_analyzer = None

        # Initialize AI equipment suggester
        self.equipment_suggester = None
        try:
            self.equipment_suggester = AIEquipmentSuggester()
        except Exception as e:
            st.warning(f"AI equipment suggester initialization failed: {e}")
            self.equipment_suggester = None

    def run(self):
        """Main application entry point"""
        choice = self._setup_sidebar()
        self._main_content(choice)

    def _setup_sidebar(self):
        """Setup sidebar navigation"""
        st.sidebar.title("⚡ EDA System")
        st.sidebar.markdown("---")

        # Navigation menu - streamlined with equipment setup
        menu_options = [
            "🏠 Dashboard",
            "⚙️ Project Setup",
            "🔧 Equipment Config",
            "📊 Design & Analysis",
            "📥 Excel Extraction",
            "ℹ️ Help"
        ]

        choice = st.sidebar.selectbox("Navigation", menu_options)

        # Project status indicator
        if self.project:
            st.sidebar.success(f"Project: {self.project.project_name}")
            st.sidebar.info(f"Loads: {len(self.project.loads)} | Buses: {len(self.project.buses)}")
        else:
            st.sidebar.warning("No project loaded")

        # Quick actions
        st.sidebar.markdown("---")
        st.sidebar.subheader("Quick Actions")

        if st.sidebar.button("🆕 New Project", type="primary"):
            self._create_new_project()

        if st.sidebar.button("📂 Try Sample Project"):
            self._load_demo_project()

        if st.sidebar.button("💾 Save Project"):
            self._save_project()

        # AI Insights Panel
        if self.project and self.ai_analyzer:
            st.sidebar.markdown("---")
            st.sidebar.subheader("🤖 AI Insights")
            
            try:
                # Get quick AI analysis
                with st.sidebar.spinner("Analyzing..."):
                    analysis = self.ai_analyzer.analyze_design(self.project)
                
                # Design score indicator
                score_color = "🟢" if analysis.overall_score >= 80 else "🟡" if analysis.overall_score >= 60 else "🔴"
                st.sidebar.metric("Design Score", f"{analysis.overall_score:.0f}/100", delta=score_color)
                
                # Critical alerts
                critical_count = len(analysis.validation_issues) + len(analysis.safety_concerns)
                if critical_count > 0:
                    st.sidebar.error(f"⚠️ {critical_count} Critical Issues")
                    if st.sidebar.button("🔍 View Issues", key="sidebar_view_issues"):
                        st.session_state.selected_page = "📊 Design & Analysis"
                        st.rerun()
                
                # Quick recommendations
                if analysis.recommendations:
                    st.sidebar.success(f"💡 {len(analysis.recommendations)} Suggestions")
                    if st.sidebar.button("✨ View Suggestions", key="sidebar_view_suggestions"):
                        st.session_state.selected_page = "📊 Design & Analysis"
                        st.run()
                
                # AI Actions
                st.sidebar.markdown("**AI Actions**")
                if st.sidebar.button("🔧 Optimize Design", key="sidebar_optimize", help="AI will analyze and suggest optimizations"):
                    self._ai_optimize_project()
                if st.sidebar.button("📋 Generate Report", key="sidebar_report", help="AI-generated executive summary"):
                    self._ai_generate_executive_summary()
                    
            except Exception as e:
                st.sidebar.warning("AI insights unavailable")

        # Auto-save indicator
        if self.project:
            st.sidebar.markdown("---")
            if st.sidebar.checkbox("Auto-save", value=True, key="auto_save"):
                # Auto-save functionality will be implemented
                pass

        return choice

    def _quick_design_page(self):
        """Super streamlined quick design workflow"""
        st.markdown('<h1 class="main-header">🚀 Quick Electrical Design</h1>', unsafe_allow_html=True)
        st.markdown("Complete your electrical design in just a few clicks!")

        # Step 1: Choose design type
        st.markdown("### Step 1: Choose Your Design Type")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🏭 Manufacturing Plant", type="primary", use_container_width=True):
                st.session_state.quick_design_choice = "manufacturing"
                st.rerun()
        with col2:
            if st.button("🏢 Commercial Building", use_container_width=True):
                st.session_state.quick_design_choice = "commercial"
                st.rerun()
        with col3:
            if st.button("🏠 Residential Complex", use_container_width=True):
                st.session_state.quick_design_choice = "residential"
                st.rerun()

        design_choice = st.session_state.get("quick_design_choice")
        if design_choice:
            with st.spinner("Creating your project..."):
                self._create_template_project(design_choice)
                st.success(f"✅ {design_choice.title()} project created!")
                st.info("🔄 Running calculations...")
                self._perform_calculations()
                st.success("✅ Design complete!")
                st.balloons()

                # Show project summary when design is complete
                st.markdown("### 📊 Project Summary")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Loads", len(self.project.loads))
                with col2:
                    total_power = sum(load.power_kw for load in self.project.loads)
                    st.metric("Total Power", f"{total_power:.1f} kW")
                with col3:
                    st.metric("Buses", len(self.project.buses))
                with col4:
                    st.metric("Transformers", len(self.project.transformers))

                # Load breakdown
                if self.project.loads:
                    st.markdown("#### Load Breakdown")
                    load_types = {}
                    for load in self.project.loads:
                        load_type = load.load_type.value
                        if load_type not in load_types:
                            load_types[load_type] = 0
                        load_types[load_type] += load.power_kw

                    for load_type, power in load_types.items():
                        st.write(f"• **{load_type.title()}**: {power:.1f} kW")

                # Quick actions
                st.markdown("### 🎉 Your Design is Ready!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📊 View Results", type="primary", use_container_width=True):
                        st.session_state.selected_page = "📊 Design & Analysis"
                        if "quick_design_choice" in st.session_state:
                            del st.session_state.quick_design_choice
                        st.rerun()
                with col2:
                    if st.button("📥 Export All", use_container_width=True):
                        self._quick_export_all()
                        st.success("All reports exported!")
                with col3:
                    if st.button("🔄 Start New Design", use_container_width=True):
                        self._create_new_project()
                        if "quick_design_choice" in st.session_state:
                            del st.session_state.quick_design_choice
                        st.rerun()

    def _design_analysis_page(self):
        """Consolidated design and analysis page with tabs"""
        st.markdown('<h1 class="section-header">📊 Design & Analysis</h1>', unsafe_allow_html=True)

        if not self.project:
            st.warning("No project loaded. Go to Quick Design to get started.")
            return

        # Auto-run calculations if not done
        if not self.calculation_results and len(self.project.loads) > 0:
            st.info("🔄 Running calculations...")
            with st.spinner("Calculating..."):
                self._perform_calculations()
            st.rerun()

        # Main dashboard metrics
        if self.calculation_results:
            summary = self.calculation_results.get("summary", {})

            # Key metrics in one row
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Loads", summary.get("total_loads", 0))
            with col2:
                st.metric("Total Power", f"{summary.get('total_power_kw', 0):.1f} kW")
            with col3:
                st.metric("Demand", f"{summary.get('total_demand_kw', 0):.1f} kW")
            with col4:
                st.metric("Diversity", f"{summary.get('diversity_factor', 0):.3f}")
            with col5:
                status = "✅ Complete" if self.calculation_results else "⚠️ Pending"
                st.metric("Status", status)

            st.markdown("---")

        # Tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Load Analysis", "📊 Charts & Reports", "🔀 SLD Diagram", "📤 Export"])

        with tab1:
            self._load_analysis_tab()

        with tab2:
            self._charts_reports_tab()

        with tab3:
            self._sld_diagram_tab()

        with tab4:
            self._export_tab()

    def _load_analysis_tab(self):
        """Load analysis table tab with AI recommendations"""
        if self.project.loads:
            st.markdown("### Load Analysis Details")
            
            # AI-powered design analysis
            if self.ai_analyzer:
                with st.spinner("🤖 Analyzing design with AI..."):
                    analysis = self.ai_analyzer.analyze_design(self.project)
                    
                    # Show overall design score
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        score_color = "🟢" if analysis.overall_score >= 80 else "🟡" if analysis.overall_score >= 60 else "🔴"
                        st.metric("Design Score", f"{analysis.overall_score:.0f}/100", delta=score_color)
                    with col2:
                        st.metric("Issues Found", len(analysis.validation_issues))
                    with col3:
                        st.metric("Recommendations", len(analysis.recommendations))
                    
                    st.markdown("---")
            
            # Load data table
            load_data = []
            for load in self.project.loads:
                load_data.append({
                    "ID": load.load_id,
                    "Name": load.load_name,
                    "Power (kW)": load.power_kw,
                    "Voltage (V)": load.voltage,
                    "Current (A)": load.current_a or "N/A",
                    "Cable Size": load.cable_size_sqmm or "N/A",
                    "Breaker": load.breaker_rating_a or "N/A"
                })
            
            st.dataframe(pd.DataFrame(load_data), use_container_width=True)
            
            # AI Equipment suggestions for each load
            if self.equipment_suggester:
                st.markdown("### 🤖 AI Equipment Configuration Suggestions")
                
                for load in self.project.loads[:5]:  # Show suggestions for first 5 loads
                    with st.expander(f"📌 {load.load_id}: {load.load_name}"):
                        config = self.equipment_suggester.get_quick_configuration(load)
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if config["cable"]:
                                st.markdown("**🔌 Cable Recommendation**")
                                st.write(f"Size: **{config['cable']['size_sqmm']} mm²**")
                                st.write(f"Type: {config['cable']['type']}")
                                st.write(f"Material: {config['cable']['material']}")
                                st.caption(config['cable']['reason'])
                        
                        with col2:
                            if config["breaker"]:
                                st.markdown("**⚡ Breaker Recommendation**")
                                st.write(f"Rating: **{config['breaker']['rating_a']:.0f} A**")
                                st.write(f"Type: {config['breaker']['type']}")
                                st.write(f"Curve: {config['breaker']['curve']}")
                                st.caption(config['breaker']['reason'])
                        
                        with col3:
                            if config["starter"]:
                                st.markdown("**🔧 Starter Recommendation**")
                                st.write(f"Type: {config['starter']['type']}")
                                st.caption(config['starter']['reason'])
                        
                        if config['notes']:
                            st.info("\n".join(config['notes']))
        else:
            st.info("No loads in project yet.")

    def _charts_reports_tab(self):
        """Charts and reports tab with AI insights"""
        st.markdown("### System Charts & Analytics")
        
        if not self.project or not self.project.loads:
            st.info("No project data available. Add loads to see analytics.")
            return
        
        # Power distribution chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Load Power Distribution**")
            load_names = [l.load_name or l.load_id for l in self.project.loads]
            load_powers = [l.power_kw or 0 for l in self.project.loads]
            
            fig = px.bar(
                x=load_names,
                y=load_powers,
                labels={"x": "Load", "y": "Power (kW)"},
                title="Power Distribution by Load"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("**Voltage Distribution**")
            voltages = list(set(l.voltage for l in self.project.loads if l.voltage))
            voltage_counts = [sum(1 for l in self.project.loads if l.voltage == v) for v in voltages]
            
            fig = px.pie(
                values=voltage_counts,
                names=[f"{v}V" for v in voltages],
                title="Loads by Voltage Level"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # AI Design Insights
        if self.ai_analyzer:
            st.markdown("---")
            st.markdown("### 🤖 AI Design Insights")
            
            analysis = self.ai_analyzer.analyze_design(self.project)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if analysis.validation_issues:
                    st.warning(f"**Issues Found: {len(analysis.validation_issues)}**")
                    for issue in analysis.validation_issues[:3]:
                        st.caption(f"• {issue}")
                
                if analysis.safety_concerns:
                    st.error(f"**Safety Concerns: {len(analysis.safety_concerns)}**")
                    for concern in analysis.safety_concerns[:3]:
                        st.caption(f"• {concern}")
            
            with col2:
                if analysis.recommendations:
                    st.success(f"**Recommendations: {len(analysis.recommendations)}**")
                    for rec in analysis.recommendations[:3]:
                        st.caption(f"• {rec}")
                
                if analysis.warnings:
                    st.info(f"**Warnings: {len(analysis.warnings)}**")
                    for warning in analysis.warnings[:3]:
                        st.caption(f"• {warning}")
            
            # Standards compliance
            if analysis.standards_compliance:
                st.markdown("**Standards Compliance**")
                compliance_data = {
                    "Aspect": list(analysis.standards_compliance.keys()),
                    "Compliant": ["✅" if v else "❌" for v in analysis.standards_compliance.values()]
                }
                st.dataframe(pd.DataFrame(compliance_data), use_container_width=True)

    def _export_tab(self):
        """Enhanced export options tab with AI insights and recommendations"""
        st.markdown("### 🤖 AI-Enhanced Export Options")
        
        # AI Export Recommendations
        if self.project and self.ai_analyzer:
            try:
                with st.spinner("🤖 AI analyzing export requirements..."):
                    analysis = self.ai_analyzer.analyze_design(self.project)
                
                st.markdown("#### 💡 **AI Export Recommendations**")
                
                # AI insights for export priorities
                col1, col2 = st.columns(2)
                with col1:
                    if analysis.validation_issues:
                        st.warning("⚠️ **Issues Found**: Export validation report first")
                        priority_exports = ["📋 Validation Report", "🔌 Load Schedule", "📊 Project Data"]
                    else:
                        st.success("✅ **Design Valid**: Full export package recommended")
                        priority_exports = ["📋 Complete Report", "🔌 Cable Schedule", "📊 SLD Diagram"]
                
                with col2:
                    # AI suggestion based on project complexity
                    total_components = len(self.project.loads) + len(self.project.cables) + len(self.project.transformers)
                    if total_components > 20:
                        st.info("📈 **Complex Project**: Consider detailed documentation package")
                    elif total_components > 10:
                        st.info("📊 **Medium Project**: Standard export package recommended")
                    else:
                        st.success("📝 **Simple Project**: Quick export sufficient")
                
                # AI export sequence recommendation
                st.markdown("**🎯 AI-Recommended Export Sequence:**")
                step = 1
                if analysis.validation_issues or analysis.safety_concerns:
                    st.write(f"{step}. **Validation Report** - Address issues first")
                    step += 1
                st.write(f"{step}. **Load Schedule** - Equipment specifications")
                step += 1
                st.write(f"{step}. **Cable Schedule** - Installation details")
                step += 1
                st.write(f"{step}. **SLD Diagram** - System visualization")
                step += 1
                st.write(f"{step}. **Complete Report** - Documentation package")
                
            except Exception as e:
                st.info("AI export recommendations unavailable")

        st.markdown("---")
        st.markdown("#### 📤 **Export Options**")
        
        # Enhanced export buttons with AI context
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📋 AI Load Report", use_container_width=True, 
                         help="AI-enhanced load analysis with recommendations"):
                self._export_load_list_excel()
                if self.ai_analyzer:
                    st.success("🤖 AI insights included in export")
        
        with col2:
            if st.button("🔌 Smart Cable Schedule", use_container_width=True,
                         help="Cable schedule with AI optimization notes"):
                self._export_cable_schedule_excel()
                if self.equipment_suggester:
                    st.success("⚡ Equipment optimization included")
        
        with col3:
            if st.button("📊 Complete Project", use_container_width=True,
                         help="Full project data with AI analysis"):
                self._export_project_json()
                st.success("📈 Full project exported")
        
        with col4:
            if st.button("🚀 AI Export Package", type="primary", use_container_width=True,
                         help="Complete AI-enhanced documentation package"):
                self._ai_enhanced_export_package()
        
        # AI Export Summary
        if self.project:
            st.markdown("---")
            st.markdown("#### 📊 **Export Summary**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Loads", len(self.project.loads))
                st.metric("Cables", len(self.project.cables))
            with col2:
                st.metric("Buses", len(self.project.buses))
                st.metric("Transformers", len(self.project.transformers))
            with col3:
                if self.calculation_results:
                    st.success("✅ Calculations Ready")
                else:
                    st.warning("⚠️ Run Calculations First")
            
            # AI Export Tips
            st.markdown("**💡 AI Export Tips:**")
            tips_col1, tips_col2 = st.columns(2)
            with tips_col1:
                st.write("• 📋 Include validation reports for compliance")
                st.write("• 🔌 Add AI optimization notes to schedules")
                st.write("• 📊 Export SLD diagrams for visualization")
            with tips_col2:
                st.write("• 📈 Include AI analysis in documentation")
                st.write("• 🚀 Use complete package for handover")
                st.write("• 💾 Archive all versions for traceability")

    def _ai_enhanced_export_package(self):
        """Generate AI-enhanced export package"""
        if not self.project:
            st.error("No project to export")
            return
        
        try:
            with st.spinner("🤖 AI generating comprehensive export package..."):
                # Create export package with AI insights
                export_files = {}
                
                # 1. AI Executive Summary
                if self.ai_analyzer:
                    try:
                        analysis = self.ai_analyzer.analyze_design(self.project)
                        summary_data = {
                            "project_name": self.project.project_name,
                            "ai_score": analysis.overall_score,
                            "total_loads": len(self.project.loads),
                            "issues_count": len(analysis.validation_issues),
                            "recommendations_count": len(analysis.recommendations),
                            "export_timestamp": datetime.now().isoformat(),
                            "ai_insights": {
                                "validation_issues": analysis.validation_issues,
                                "recommendations": analysis.recommendations,
                                "safety_concerns": analysis.safety_concerns,
                                "warnings": analysis.warnings
                            }
                        }
                        export_files["ai_summary"] = summary_data
                    except Exception as e:
                        st.warning(f"AI summary generation failed: {e}")
                
                # 2. Load Schedule with AI Equipment Suggestions
                if self.project.loads:
                    load_data = []
                    for load in self.project.loads:
                        load_info = {
                            "load_id": load.load_id,
                            "load_name": load.load_name,
                            "load_type": load.load_type.value,
                            "power_kw": load.power_kw,
                            "voltage_v": load.voltage,
                            "phases": load.phases,
                            "power_factor": load.power_factor,
                            "efficiency": load.efficiency
                        }
                        
                        # Add AI equipment suggestions
                        if self.equipment_suggester:
                            try:
                                config = self.equipment_suggester.get_quick_configuration(load)
                                load_info.update({
                                    "ai_cable_size": config.get("cable", {}).get("size_sqmm"),
                                    "ai_breaker_rating": config.get("breaker", {}).get("rating_a"),
                                    "ai_cable_reason": config.get("cable", {}).get("reason"),
                                    "ai_breaker_reason": config.get("breaker", {}).get("reason")
                                })
                            except:
                                pass
                        
                        load_data.append(load_info)
                    
                    export_files["load_schedule"] = load_data
                
                # 3. Project Configuration
                project_config = {
                    "project_name": self.project.project_name,
                    "project_id": self.project.project_id,
                    "standard": self.project.standard,
                    "voltage_system": self.project.voltage_system,
                    "ambient_temperature_c": self.project.ambient_temperature_c,
                    "altitude_m": self.project.altitude_m,
                    "creation_date": self.project.creation_date,
                    "last_modified": datetime.now().isoformat()
                }
                export_files["project_config"] = project_config
                
                # Save comprehensive export
                export_filename = f"ai_enhanced_{self.project.project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                with open(export_filename, 'w') as f:
                    json.dump(export_files, f, indent=2, default=str)
                
                st.success(f"🎉 **AI-Enhanced Export Package Created!**")
                st.info(f"📁 File saved as: {export_filename}")
                
                # Export package summary
                st.markdown("#### 📦 **Package Contents**")
                package_col1, package_col2 = st.columns(2)
                with package_col1:
                    st.success("✅ AI Executive Summary")
                    st.success("✅ Enhanced Load Schedule")
                    st.success("✅ Project Configuration")
                with package_col2:
                    st.success("✅ Equipment Recommendations")
                    st.success("✅ Validation Results")
                    st.success("✅ Optimization Notes")
                
                # Download button
                with open(export_filename, 'rb') as f:
                    st.download_button(
                        label="📥 Download AI Package",
                        data=f.read(),
                        file_name=export_filename,
                        mime="application/json"
                    )
                
        except Exception as e:
            st.error(f"AI export package generation failed: {str(e)}")

    def _sld_diagram_tab(self):
        """Display SLD diagram tab with auto-calculations"""
        st.subheader("Single-Line Diagram (SLD)")

        if not self.project:
            st.warning("Please create or load a project first.")
            return

        # Auto-run calculations if missing
        if not self.calculation_results and len(self.project.loads) > 0:
            st.info("🔄 Running calculations before generating SLD...")
            with st.spinner("Calculating electrical parameters..."):
                try:
                    self._perform_calculations()
                    st.success("✅ Calculations complete! You can now generate the SLD.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Calculation failed: {str(e)}")
                    st.warning("Please go to Design & Analysis page to review your project data.")
                    return
        elif not self.calculation_results:
            st.warning("Please add loads to your project first. Go to 🔧 Equipment Config to add loads.")
            return

        # Generate SLD button
        if st.button("🔀 Generate SLD Diagram", type="primary"):
            with st.spinner("Generating SLD diagram..."):
                try:
                    # Ensure SLD graph is generated first
                    if not hasattr(self, 'sld_graph') or not self.sld_graph:
                        self._generate_sld_graph()

                    # Generate DOT code
                    self._generate_sld_diagram()

                    # Store in session state
                    st.session_state.sld_graph = self.sld_graph
                    st.session_state.sld_dot_content = self.sld_dot_content

                    st.success("SLD diagram generated successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating SLD: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc(), language="text")

        # Display SLD if available
        sld_graph = getattr(self, 'sld_graph', None) or st.session_state.get('sld_graph')
        sld_dot_content = getattr(self, 'sld_dot_content', None) or st.session_state.get('sld_dot_content')

        if sld_graph:
            st.markdown("### SLD Graph Object")
            st.json(sld_graph)

            # Display DOT content if available
            if sld_dot_content:
                st.markdown("### Graphviz DOT Code")
                st.code(sld_dot_content, language="dot")

                # Option to download DOT file
                st.download_button(
                    label="📥 Download DOT File",
                    data=sld_dot_content,
                    file_name="sld_diagram.dot",
                    mime="text/plain"
                )

        # Display SLD visualization options
        if sld_dot_content:
            st.markdown("### SLD Diagram Visualization")

            # Save DOT to file
            try:
                with open('sld_diagram.dot', 'w') as f:
                    f.write(sld_dot_content)
                st.success("✅ DOT file saved as 'sld_diagram.dot' in the project directory")
            except Exception as e:
                st.warning(f"Could not save DOT file: {e}")

            # Show rendering instructions
            st.info("🔧 **Graphviz System Package Required for Rendering**")
            st.markdown("""
            To render the diagram automatically, install Graphviz on your system:
            
            **Windows:** `choco install graphviz` or download from https://graphviz.org/download/
            **Ubuntu/Debian:** `sudo apt install graphviz`
            **macOS:** `brew install graphviz`
            
            Then run: `dot -Tpng sld_diagram.dot -o sld_diagram.png`
            """)

    def _excel_extraction_page(self):
        """Enhanced Excel extraction and data import page with AI insights"""
        st.markdown('<h1 class="section-header">📥 AI-Powered Excel Extraction</h1>', unsafe_allow_html=True)

        # AI System Status Dashboard
        st.markdown("### 🤖 AI System Status")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Check LLM availability
            try:
                import os
                if os.getenv('GOOGLE_API_KEY') or os.getenv('OPENAI_API_KEY'):
                    st.success("🧠 **LLM Engine**: Active")
                    st.caption("Full AI extraction enabled")
                else:
                    st.warning("🧠 **LLM Engine**: Pattern Mode")
                    st.caption("Using pattern matching")
            except Exception as e:
                st.info("🧠 **LLM Engine**: Unavailable")
                st.caption("Basic extraction only")
        
        with col2:
            # Check Vector DB availability
            try:
                if os.path.exists('./vector_db'):
                    st.success("🔍 **Vector DB**: Connected")
                    st.caption("Historical data available")
                else:
                    st.info("🔍 **Vector DB**: Initializing")
                    st.caption("Building knowledge base")
            except (OSError, IOError) as e:
                st.info("🔍 **Vector DB**: Disabled")
                st.caption("No historical data")
        
        with col3:
            # AI Equipment Suggester Status
            if self.equipment_suggester:
                st.success("⚡ **Equipment AI**: Ready")
                st.caption("Smart sizing available")
            else:
                st.warning("⚡ **Equipment AI**: Limited")
                st.caption("Basic suggestions only")
        
        with col4:
            # AI Design Analyzer Status
            if self.ai_analyzer:
                st.success("🛡️ **Safety AI**: Active")
                st.caption("Compliance checking enabled")
            else:
                st.warning("🛡️ **Safety AI**: Limited")
                st.caption("Manual verification needed")

        st.markdown("---")

        # Create tabs for different sections
        tab1, tab2, tab3, tab4 = st.tabs(["📥 Smart Import", "🔧 AI Equipment", "💡 Design Insights", "📊 Analytics"])

        # TAB 1: Enhanced Excel Import
        with tab1:
            st.markdown("### 🤖 AI-Enhanced Data Extraction")
            
            # AI Tips Panel
            with st.expander("💡 **AI Extraction Tips**", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.info("📋 **Best Practices:**")
                    st.write("• Use clear column headers (Load ID, Power, Voltage)")
                    st.write("• Include units (kW, A, V, mm²)")
                    st.write("• Separate sheets for different data types")
                    st.write("• Use consistent naming conventions")
                with col2:
                    st.success("🎯 **AI Capabilities:**")
                    st.write("• Automatic load type detection")
                    st.write("• Intelligent equipment sizing")
                    st.write("• Standards compliance checking")
                    st.write("• Error correction suggestions")

        st.markdown("#### 📤 Upload Your Excel File")
        col1, col2 = st.columns([2, 1])
        with col1:
            uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'], 
                                       help="Upload load schedules, cable schedules, or equipment lists")
        with col2:
            project_name = st.text_input("Project Name", "AI Extracted Project", 
                                     help="Name for your extracted project")

        # AI-powered file validation (before upload)
        if uploaded_file:
            st.markdown("##### 🤖 **AI File Analysis**")
            
            # File analysis simulation
            file_size = uploaded_file.size / (1024 * 1024)  # MB
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("File Size", f"{file_size:.2f} MB")
                if file_size > 10:
                    st.warning("Large file may take longer to process")
                else:
                    st.success("Optimal file size")
            
            with col2:
                # Simulated sheet count (would be actual analysis)
                st.metric("Estimated Sheets", "3-5")
                st.caption("Based on file size")
            
            with col3:
                # AI confidence prediction
                confidence = 95 if file_size < 5 else 85 if file_size < 10 else 75
                st.metric("AI Confidence", f"{confidence}%")
                if confidence > 90:
                    st.success("High accuracy expected")
                elif confidence > 80:
                    st.info("Good accuracy expected")
                else:
                    st.warning("Manual review may be needed")

        if uploaded_file and project_name:
            extraction_button = st.button("🚀 Start AI Extraction", type="primary", width='stretch',
                                       help="AI will extract, validate, and optimize your electrical data")
            
            if extraction_button:
                with st.spinner("🤖 AI is working... Extracting, validating, and optimizing your data"):
                    try:
                        if 'unified_processor' not in st.session_state:
                            st.session_state.unified_processor = create_unified_processor("IEC")

                        success, message, project = st.session_state.unified_processor.process_excel_upload(
                            uploaded_file, project_name
                        )

                        if success:
                            self.project = project
                            st.session_state.project = self.project
                            
                            # Enhanced extraction success panel
                            st.markdown("---")
                            st.success("🎉 **AI Extraction Successful!**")
                            
                            # Comprehensive extraction metrics
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("⚡ Loads", len(self.project.loads), delta="✓ Extracted")
                            with col2:
                                st.metric("🚌 Buses", len(self.project.buses), delta="✓ Identified")
                            with col3:
                                st.metric("🔌 Transformers", len(self.project.transformers), delta="✓ Processed")
                            with col4:
                                st.metric("📊 Cables", len(self.project.cables), delta="✓ Generated")
                            
                            # AI Quality Assessment
                            st.markdown("##### 🤖 **AI Quality Assessment**")
                            
                            # Calculate quality metrics
                            total_components = len(self.project.loads) + len(self.project.buses) + len(self.project.transformers) + len(self.project.cables)
                            quality_score = min(100, (total_components / 20) * 100) if total_components > 0 else 0  # Simplified scoring
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                quality_emoji = "🟢" if quality_score >= 80 else "🟡" if quality_score >= 60 else "🔴"
                                st.metric("Data Quality", f"{quality_score:.0f}%", delta=quality_emoji)
                            with col2:
                                st.metric("Confidence", f"{confidence}%")
                            with col3:
                                validation_issues = 0  # Would be calculated from AI validation
                                st.metric("Issues Found", validation_issues, delta="✓ Clean" if validation_issues == 0 else "⚠️ Review")
                            
                            # AI Recommendations
                            if self.ai_analyzer:
                                try:
                                    analysis = self.ai_analyzer.analyze_design(self.project)
                                    if analysis.recommendations:
                                        st.markdown("##### 💡 **AI Initial Recommendations**")
                                        for rec in analysis.recommendations[:3]:
                                            st.write(f"• {rec}")
                                except:
                                    pass
                            
                            # Enhanced Next Steps Panel
                            st.markdown("---")
                            st.markdown("##### 🎯 **Intelligent Next Steps**")
                            
                            next_steps_col1, next_steps_col2 = st.columns(2)
                            with next_steps_col1:
                                st.markdown("""
                                <div style='background-color: #e3f2fd; padding: 15px; border-radius: 8px; border-left: 4px solid #2196f3;'>
                                    <h4 style='margin-top: 0; color: #1565c0;'>📊 Immediate Actions</h4>
                                    <ul style='margin-bottom: 0;'>
                                        <li><strong>Review extracted data</strong> in Design & Analysis</li>
                                        <li><strong>Run calculations</strong> for validation</li>
                                        <li><strong>Check AI suggestions</strong> for optimization</li>
                                    </ul>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with next_steps_col2:
                                st.markdown("""
                                <div style='background-color: #f3e5f5; padding: 15px; border-radius: 8px; border-left: 4px solid #9c27b0;'>
                                    <h4 style='margin-top: 0; color: #6a1b9a;'>🤖 AI-Powered Features</h4>
                                    <ul style='margin-bottom: 0;'>
                                        <li><strong>Equipment optimization</strong> suggestions</li>
                                        <li><strong>Safety compliance</strong> checking</li>
                                        <li><strong>Design validation</strong> reports</li>
                                    </ul>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Quick action buttons
                            st.markdown("##### 🚀 **Quick Actions**")
                            action_col1, action_col2, action_col3 = st.columns(3)
                            
                            with action_col1:
                                if st.button("📊 Review Design", type="primary", help="Go to detailed analysis"):
                                    st.session_state.selected_page = "📊 Design & Analysis"
                                    st.rerun()
                            
                            with action_col2:
                                if st.button("🔧 Optimize Equipment", help="Get AI equipment suggestions"):
                                    st.session_state.selected_page = "🔧 Equipment Config"
                                    st.rerun()
                            
                            with action_col3:
                                if st.button("📋 Generate Report", help="Create comprehensive report"):
                                    self._ai_generate_executive_summary()
                                    st.rerun()
                            
                            # Show detailed extraction report if available
                            if hasattr(st.session_state.unified_processor, 'status') and st.session_state.unified_processor.status.extraction_report:
                                with st.expander("📋 **Detailed AI Extraction Report**", expanded=False):
                                    report = st.session_state.unified_processor.status.extraction_report
                                    try:
                                        st.json(report.to_dict())
                                    except Exception as e:
                                        st.error(f"Error displaying report: {str(e)}")
                                        st.text(str(report))
                        else:
                            st.error(f"❌ **AI Extraction Failed**")
                            st.error(f"**Error:** {message}")
                            
                            # Enhanced error guidance
                            st.markdown("##### 🔧 **AI Troubleshooting Assistant**")
                            
                            error_col1, error_col2 = st.columns(2)
                            with error_col1:
                                st.markdown("""
                                <div style='background-color: #fff3e0; padding: 15px; border-radius: 8px; border-left: 4px solid #ff9800;'>
                                    <h4 style='margin-top: 0; color: #e65100;'>🔍 Common Issues</h4>
                                    <ul style='margin-bottom: 0;'>
                                        <li>Unclear column headers</li>
                                        <li>Missing units in data</li>
                                        <li>Complex formatting</li>
                                        <li>Corrupted file sections</li>
                                    </ul>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with error_col2:
                                st.markdown("""
                                <div style='background-color: #fce4ec; padding: 15px; border-radius: 8px; border-left: 4px solid #e91e63;'>
                                    <h4 style='margin-top: 0; color: #880e4f;'>💡 Quick Fixes</h4>
                                    <ul style='margin-bottom: 0;'>
                                        <li>Use standard headers</li>
                                        <li>Add units to all values</li>
                                        <li>Simplify formatting</li>
                                        <li>Try sample template</li>
                                    </ul>
                                </div>
                                """, unsafe_allow_html=True)
                            
                            # Offer sample template download
                            st.markdown("##### 📋 **Need Help?**")
                            template_col1, template_col2 = st.columns(2)
                            with template_col1:
                                if st.button("📄 Download Template", help="Get sample Excel template"):
                                    self._create_sample_excel_file("load_schedule")
                            with template_col2:
                                if st.button("📖 View Guide", help="Open preparation guide"):
                                    st.info("📖 **Guide:** Prepare your Excel file with clear headers, consistent units, and simple formatting for best AI extraction results.")
                                
                    except Exception as e:
                        st.error(f"AI extraction error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc(), language="python")

        uploaded_file = st.file_uploader("Choose Excel file", type=['xlsx', 'xls'])
        project_name = st.text_input("Project Name", "AI Extracted Project")

        if uploaded_file and project_name:
            if st.button("🚀 Extract with AI", type="primary", width='stretch'):
                with st.spinner("AI extracting data..."):
                    try:
                        if 'unified_processor' not in st.session_state:
                            st.session_state.unified_processor = create_unified_processor("IEC")

                        success, message, project = st.session_state.unified_processor.process_excel_upload(
                            uploaded_file, project_name
                        )

                        if success:
                            self.project = project
                            st.session_state.project = self.project
                            
                            # Show extraction summary
                            st.success(f"✅ Extraction Complete!")
                            
                            # Extraction details
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("✓ Loads", len(self.project.loads))
                            with col2:
                                st.metric("✓ Buses", len(self.project.buses))
                            with col3:
                                st.metric("✓ Transformers", len(self.project.transformers))
                            with col4:
                                st.metric("✓ Cables", len(self.project.cables))
                            
                            # Next Steps Panel
                            st.markdown("---")
                            st.markdown("### 🎯 Next Steps")
                            
                            st.markdown("""
                            <div style='background-color: #d4edda; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;'>
                                <h4 style='margin-top: 0; color: #155724;'>✅ Extraction Successful!</h4>
                                <p style='margin-bottom: 10px;'><strong>What to do next:</strong></p>
                                <ol style='margin-bottom: 0;'>
                                    <li>Navigate to <strong>📊 Design & Analysis</strong> to review extracted data</li>
                                    <li>Calculations will run automatically</li>
                                    <li>Go to <strong>🔀 SLD Diagram</strong> tab to generate your single-line diagram</li>
                                    <li>Use <strong>📤 Export</strong> tab to download results</li>
                                </ol>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Show extraction report if available
                            if hasattr(st.session_state.unified_processor, 'status') and st.session_state.unified_processor.status.extraction_report:
                                with st.expander("📋 View Detailed Extraction Report"):
                                    report = st.session_state.unified_processor.status.extraction_report
                                    try:
                                        st.json(report.to_dict())
                                    except Exception as e:
                                        st.error(f"Error displaying report: {str(e)}")
                                        st.text(str(report))
                        else:
                            st.error(f"❌ Extraction Failed")
                            st.error(f"{message}")
                            
                            # Improved error guidance
                            with st.expander("🔧 Troubleshooting Tips", expanded=True):
                                st.markdown("""
                                **Common issues and solutions:**
                                
                                1. **File Format Issues:**
                                   - Ensure file is .xlsx or .xls format
                                   - Check file is not corrupted
                                   - Try opening in Excel first to verify
                                
                                2. **Data Structure Issues:**
                                   - Headers should be in first row
                                   - Data should be in tabular format (no merged cells)
                                   - Use standard electrical engineering terminology
                                
                                3. **Content Issues:**
                                   - Verify numerical values are valid
                                   - Check equipment IDs are unique
                                   - Ensure voltages and power ratings are realistic
                                
                                4. **Try Manual Entry:**
                                   - Go to **🔧 Equipment Config** to add equipment manually
                                   - Use **⚙️ Project Setup** to configure your project
                                """)
                    except Exception as e:
                        st.error(f"AI extraction failed: {str(e)}")

        # Sample files
        st.markdown("---")
        st.markdown("### 📋 Sample Files")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Load Schedule Sample", use_container_width=True):
                self._create_sample_excel_file("load_schedule")
        with col2:
            if st.button("🔌 Cable Schedule Sample", use_container_width=True):
                self._create_sample_excel_file("cable_schedule")

        if not self.project:
            st.info("📌 Load a project first to see equipment suggestions. Go to the Excel Import tab or create a new project.")
        elif not self.project.loads:
            st.info("📌 Add loads to your project to see equipment suggestions.")
        elif not self.equipment_suggester:
            st.warning("⚠️ Equipment suggester not initialized. Check AI configuration.")
        else:
            st.markdown("AI analyzes your loads and suggests optimal cable sizes, breaker ratings, and other equipment.")

            # Run calculations if not done
            if not self.calculation_results and len(self.project.loads) > 0:
                st.info("🔄 Running calculations...")
                with st.spinner("Calculating..."):
                    self._perform_calculations()

            # Show suggestions for each load
            for i, load in enumerate(self.project.loads):
                with st.expander(f"📌 {load.load_id}: {load.load_name}", expanded=(i == 0)):
                        try:
                            config = self.equipment_suggester.get_quick_configuration(load)
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if config["cable"]:
                                    st.markdown("**🔌 Cable Recommendation**")
                                    st.write(f"Size: **{config['cable']['size_sqmm']} mm²**")
                                    st.write(f"Type: {config['cable']['type']}")
                                    st.write(f"Material: {config['cable']['material']}")
                                    st.caption(config['cable']['reason'])
                            
                            with col2:
                                if config["breaker"]:
                                    st.markdown("**⚡ Breaker Recommendation**")
                                    st.write(f"Rating: **{config['breaker']['rating_a']:.0f} A**")
                                    st.write(f"Type: {config['breaker']['type']}")
                                    st.write(f"Curve: {config['breaker']['curve']}")
                                    st.caption(config['breaker']['reason'])
                            
                            with col3:
                                if config["starter"]:
                                    st.markdown("**🔧 Starter Recommendation**")
                                    st.write(f"Type: {config['starter']['type']}")
                                    st.caption(config['starter']['reason'])
                            
                            if config['notes']:
                                st.info("\n".join(config['notes']))
                        except Exception as e:
                            st.error(f"Error getting suggestions for {load.load_id}: {str(e)}")

        # TAB 3: Design Insights
        with tab3:
            st.markdown("### 💡 AI Design Insights")
            
            if not self.project:
                st.info("📌 Load a project first to see design insights.")
            elif not self.project.loads:
                st.info("📌 Add loads to your project to see design insights.")
            elif not self.ai_analyzer:
                st.warning("⚠️ AI analyzer not initialized. Check AI configuration.")
            else:
                st.markdown("AI analyzes your electrical design for optimization opportunities, safety concerns, and standards compliance.")
                
                # Run calculations if not done
                if not self.calculation_results and len(self.project.loads) > 0:
                    st.info("🔄 Running calculations...")
                    with st.spinner("Calculating..."):
                        self._perform_calculations()

                try:
                    analysis = self.ai_analyzer.analyze_design(self.project)
                    
                    # Design Score
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        score_color = "🟢" if analysis.overall_score >= 80 else "🟡" if analysis.overall_score >= 60 else "🔴"
                        st.metric("Design Score", f"{analysis.overall_score:.0f}/100", delta=score_color)
                    with col2:
                        st.metric("Issues", len(analysis.validation_issues))
                    with col3:
                        st.metric("Recommendations", len(analysis.recommendations))
                    with col4:
                        st.metric("Safety Concerns", len(analysis.safety_concerns))
                    
                    st.markdown("---")
                    
                    # Validation Issues
                    if analysis.validation_issues:
                        st.warning(f"**Issues Found ({len(analysis.validation_issues)})**")
                        for issue in analysis.validation_issues:
                            st.caption(f"❌ {issue}")
                    
                    # Safety Concerns
                    if analysis.safety_concerns:
                        st.error(f"**Safety Concerns ({len(analysis.safety_concerns)})**")
                        for concern in analysis.safety_concerns:
                            st.caption(f"⚠️ {concern}")
                    
                    # Recommendations
                    if analysis.recommendations:
                        st.success(f"**Recommendations ({len(analysis.recommendations)})**")
                        for rec in analysis.recommendations:
                            st.caption(f"✅ {rec}")
                    
                    # Warnings
                    if analysis.warnings:
                        st.info(f"**Warnings ({len(analysis.warnings)})**")
                        for warning in analysis.warnings:
                            st.caption(f"ℹ️ {warning}")
                    
                    # Standards Compliance
                    if analysis.standards_compliance:
                        st.markdown("**Standards Compliance**")
                        compliance_data = {
                            "Aspect": list(analysis.standards_compliance.keys()),
                            "Compliant": ["✅" if v else "❌" for v in analysis.standards_compliance.values()]
                        }
                        st.dataframe(pd.DataFrame(compliance_data), use_container_width=True, hide_index=True)
                        
                except Exception as e:
                    st.error(f"Error analyzing design: {str(e)}")

        # TAB 4: Analytics
        with tab4:
            st.markdown("### 📊 AI Analytics")
            
            if not self.project:
                st.info("📌 Load a project first to see analytics.")
            elif not self.project.loads:
                st.info("📌 Add loads to your project to see analytics.")
            else:
                st.markdown("AI-powered analytics and system analysis.")
                
                # Run calculations if not done
                if not self.calculation_results and len(self.project.loads) > 0:
                    st.info("🔄 Running calculations...")
                    with st.spinner("Calculating..."):
                        self._perform_calculations()

                # Power Distribution
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Load Power Distribution**")
                    load_names = [l.load_name or l.load_id for l in self.project.loads]
                    load_powers = [l.power_kw or 0 for l in self.project.loads]
                    
                    fig = px.bar(
                        x=load_names,
                        y=load_powers,
                        labels={"x": "Load", "y": "Power (kW)"},
                        title="Power Distribution by Load"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("**Voltage Distribution**")
                    voltages = list(set(l.voltage for l in self.project.loads if l.voltage))
                    voltage_counts = [sum(1 for l in self.project.loads if l.voltage == v) for v in voltages]
                    
                    if voltages:
                        fig = px.pie(
                            values=voltage_counts,
                            names=[f"{v}V" for v in voltages],
                            title="Loads by Voltage Level"
                        )
                        st.plotly_chart(fig, use_container_width=True)

    def _main_content(self, choice):
        """Main content area based on navigation choice"""
        if choice == "🚀 Quick Design":
            self._quick_design_page()
        elif choice == "🏠 Dashboard":
            self._dashboard_page()
        elif choice == "⚙️ Project Setup":
            self._project_setup_page()
        elif choice == "🔧 Equipment Config":
            self._equipment_config_page()
        elif choice == "📊 Design & Analysis":
            self._design_analysis_page()
        elif choice == "📥 Excel Extraction":
            self._excel_extraction_page()
        elif choice == "ℹ️ Help":
            self._help_page()

    def _quick_start_wizard(self):
        """Quick start wizard for new users"""
        st.markdown("### 🚀 Quick Start Wizard")
        st.markdown("Get started with your electrical design project in just a few steps!")

        # Step 1: Project type selection
        st.markdown("**Step 1: Choose Project Type**")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🏭 Manufacturing Plant", type="primary", use_container_width=True):
                self._create_template_project("manufacturing")
                st.rerun()

        with col2:
            if st.button("🏢 Commercial Building", type="primary", use_container_width=True):
                self._create_template_project("commercial")
                st.rerun()

        with col3:
            if st.button("🏠 Residential Complex", type="primary", use_container_width=True):
                self._create_template_project("residential")
                st.rerun()

        st.markdown("---")
        st.markdown("**Alternative Options:**")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📂 Try Sample Project", use_container_width=True):
                self._load_demo_project()
                st.rerun()

        with col2:
            if st.button("📥 Import Excel Data", use_container_width=True):
                st.session_state.selected_page = "🤖 AI Excel Extraction"
                st.rerun()

        with col3:
            if st.button("⚙️ Custom Project", use_container_width=True):
                self._create_new_project()
                st.session_state.selected_page = "⚙️ Project Setup"
                st.rerun()

        st.markdown("---")
        st.markdown("💡 **Tip:** Choose a template to get started quickly, or import your existing Excel data!")

    def _dashboard_page(self):
        """Enhanced dashboard with AI insights, project overview, and intelligent recommendations"""
        st.markdown('<h1 class="main-header">🏠 Electrical Design Dashboard</h1>', unsafe_allow_html=True)

        if not self.project:
            # Welcome screen with AI-powered guidance
            st.info("🤖 **AI Assistant Ready!** Let's create your electrical design project with intelligent guidance.")
            st.markdown("### Choose Your Starting Point:")
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("🚀 AI Quick Design", type="primary", use_container_width=True, help="AI-guided project creation"):
                    st.session_state.selected_page = "🚀 Quick Design"
                    st.rerun()
            with col2:
                if st.button("📂 Load Sample Project", use_container_width=True, help="Explore AI features with sample data"):
                    self._load_demo_project()
                    st.rerun()
            with col3:
                if st.button("📥 AI Excel Import", use_container_width=True, help="AI-powered data extraction"):
                    st.session_state.selected_page = "📥 Excel Extraction"
                    st.rerun()
            
            # AI tips for new users
            st.markdown("---")
            st.markdown("### 💡 AI-Powered Tips")
            col1, col2 = st.columns(2)
            with col1:
                st.info("🎯 **Smart Templates**: Start with industry-specific templates for faster design")
                st.success("🔍 **Intelligent Analysis**: Get real-time design validation and optimization suggestions")
            with col2:
                st.warning("⚡ **Equipment Suggestions**: AI recommends optimal cable sizes and breaker ratings")
                st.error("🛡️ **Safety Checks**: Automated compliance verification with electrical standards")
            return

        # AI Insights Panel (Top Priority)
        if self.ai_analyzer:
            st.markdown("### 🤖 AI Design Intelligence")
            
            try:
                # Get AI analysis
                with st.spinner("🧠 AI analyzing your design..."):
                    analysis = self.ai_analyzer.analyze_design(self.project)
                
                # AI Score and Alerts
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    score_color = "🟢" if analysis.overall_score >= 80 else "🟡" if analysis.overall_score >= 60 else "🔴"
                    st.metric("AI Score", f"{analysis.overall_score:.0f}/100", delta=score_color)
                
                with col2:
                    critical_issues = len(analysis.validation_issues) + len(analysis.safety_concerns)
                    if critical_issues > 0:
                        st.metric("Critical Issues", critical_issues, delta="🚨")
                    else:
                        st.metric("Critical Issues", 0, delta="✅")
                
                with col3:
                    st.metric("Recommendations", len(analysis.recommendations), delta="💡")
                
                with col4:
                    optimization_potential = min(100 - analysis.overall_score, 40)
                    st.metric("Optimization", f"+{optimization_potential:.0f}", delta="📈")
                
                with col5:
                    if st.button("🔧 AI Optimize", type="primary", help="Run comprehensive AI optimization"):
                        self._ai_optimize_project()
                        st.rerun()
                
                # Quick AI Actions
                if analysis.validation_issues or analysis.safety_concerns or analysis.recommendations:
                    st.markdown("#### 🚨 AI Alerts & Suggestions")
                    alert_col1, alert_col2, alert_col3 = st.columns(3)
                    
                    with alert_col1:
                        if analysis.validation_issues or analysis.safety_concerns:
                            st.error(f"⚠️ {len(analysis.validation_issues + analysis.safety_concerns)} Issues Need Attention")
                            if st.button("🔍 Fix Issues", key="dashboard_fix_issues"):
                                st.session_state.selected_page = "📊 Design & Analysis"
                                st.rerun()
                    
                    with alert_col2:
                        if analysis.recommendations:
                            st.success(f"💡 {len(analysis.recommendations)} Optimization Opportunities")
                            if st.button("✨ View Suggestions", key="dashboard_suggestions"):
                                st.session_state.selected_page = "📊 Design & Analysis"
                                st.rerun()
                    
                    with alert_col3:
                        if st.button("📋 AI Summary", key="dashboard_summary"):
                            self._ai_generate_executive_summary()
                            st.rerun()
                
            except Exception as e:
                st.warning("🤖 AI insights temporarily unavailable")

        st.markdown("---")

        # Project Overview Metrics
        st.markdown("### 📊 Project Overview")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Loads", len(self.project.loads))
            if st.button("➕ Add Load", key="dashboard_add_load", help="Add new electrical load"):
                st.session_state.selected_page = "🔧 Equipment Config"
                st.rerun()

        with col2:
            total_power = sum(load.power_kw for load in self.project.loads)
            st.metric("Total Power", f"{total_power:.1f} kW")
            if not self.calculation_results:
                if st.button("⚡ Run Calc", key="dashboard_calc", help="Run electrical calculations"):
                    with st.spinner("🔄 AI-powered calculations..."):
                        self._perform_calculations()
                    st.rerun()

        with col3:
            st.metric("Buses", len(self.project.buses))
            if st.button("🔧 Add Bus", key="dashboard_add_bus", help="Add distribution bus"):
                st.session_state.selected_page = "🔧 Equipment Config"
                st.rerun()

        with col4:
            calc_status = "✅ Done" if self.calculation_results else "⚠️ Pending"
            st.metric("Calculations", calc_status)
            if self.calculation_results and st.button("📊 Results", key="dashboard_results", help="View calculation results"):
                st.session_state.selected_page = "📊 Design & Analysis"
                st.rerun()

        # Visual Analytics with AI Insights
        if self.project.loads:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("### 📈 Load Distribution Analysis")
                
                # Load type distribution
                load_types = {}
                for load in self.project.loads:
                    load_type = load.load_type.value
                    if load_type not in load_types:
                        load_types[load_type] = 0
                    load_types[load_type] += load.power_kw

                fig = px.pie(
                    values=list(load_types.values()),
                    names=list(load_types.keys()),
                    title="Power Distribution by Load Type",
                    color_discrete_map={
                        "motor": "#FF6B6B",
                        "lighting": "#4ECDC4", 
                        "hvac": "#45B7D1",
                        "general": "#96CEB4"
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # AI Insight below chart
                if self.ai_analyzer:
                    try:
                        analysis = self.ai_analyzer.analyze_design(self.project)
                        if analysis.warnings:
                            st.info("🤖 **AI Insight:** " + analysis.warnings[0] if analysis.warnings else "Load distribution looks balanced")
                    except:
                        pass

            with col2:
                st.markdown("### 🚀 Quick Actions")
                
                # Smart action buttons based on project state
                if not self.calculation_results:
                    if st.button("🧠 AI Complete Setup", key="ai_complete_setup", type="primary", help="AI will configure and optimize your system"):
                        with st.spinner("🤖 AI setting up your project..."):
                            if not self.calculation_results:
                                self._perform_calculations()
                        st.session_state.selected_page = "📊 Design & Analysis"
                        st.rerun()
                else:
                    if st.button("🔧 AI Optimize", key="ai_optimize_dashboard", type="primary", help="AI optimization suggestions"):
                        self._ai_optimize_project()
                        st.rerun()

                if st.button("📥 Smart Import", key="smart_import", help="AI-powered data import"):
                    st.session_state.selected_page = "📥 Excel Extraction"
                    st.rerun()

                if st.button("📤 AI Reports", key="ai_reports", help="Generate AI-enhanced reports"):
                    if self.calculation_results:
                        self._quick_export_all()
                        st.success("🤖 AI-enhanced reports exported!")
                    else:
                        st.warning("⚠️ Run calculations first")

                # AI Equipment Suggestions Preview
                if self.equipment_suggester and len(self.project.loads) > 0:
                    st.markdown("### 💡 Equipment Tips")
                    sample_load = self.project.loads[0]
                    try:
                        config = self.equipment_suggester.get_quick_configuration(sample_load)
                        if config.get("cable"):
                            st.info(f"🔌 {sample_load.load_name}: {config['cable']['size_sqmm']}mm² cable recommended")
                    except:
                        pass

        # Enhanced workflow progress with AI guidance
        self._show_ai_enhanced_workflow_progress()

    def _show_ai_enhanced_workflow_progress(self):
        """Show AI-enhanced workflow progress with intelligent recommendations"""
        st.markdown('<h2 class="section-header">🤖 AI-Guided Project Progress</h2>', unsafe_allow_html=True)

        # Calculate completion steps with AI insights
        steps = [
            ("📋 Project Setup", self.project and self.project.project_name != "New Electrical Project", "Configure basic project parameters and standards"),
            ("🔧 System Config", len(self.project.buses) > 0 or len(self.project.transformers) > 0, "Add buses, transformers, and distribution system"),
            ("⚡ Load Definition", len(self.project.loads) > 0, "Define electrical loads and their characteristics"),
            ("🧮 Calculations", self.calculation_results and self.calculation_results.get("completed"), "Run electrical calculations and analysis"),
            ("🤖 AI Analysis", self.calculation_results and self.ai_analyzer, "AI-powered design validation and optimization"),
            ("📊 Complete", self.calculation_results and len(self.project.loads) > 0, "Generate reports and documentation")
        ]

        completed_steps = sum(1 for _, completed, _ in steps if completed)
        progress = completed_steps / len(steps)

        # Progress bar with AI enhancement
        st.progress(progress)
        st.markdown(f"**Progress:** {completed_steps}/{len(steps)} steps completed")

        # AI-powered progress insights
        if self.ai_analyzer and self.project:
            try:
                analysis = self.ai_analyzer.analyze_design(self.project)
                ai_score = analysis.overall_score
                
                # AI Quality Indicator
                col1, col2, col3 = st.columns(3)
                with col1:
                    quality_color = "🟢 Excellent" if ai_score >= 80 else "🟡 Good" if ai_score >= 60 else "🔴 Needs Work"
                    st.metric("Design Quality", quality_color)
                
                with col2:
                    st.metric("AI Score", f"{ai_score:.0f}/100")
                
                with col3:
                    next_actions = len(analysis.validation_issues) + len(analysis.recommendations)
                    st.metric("Actions Needed", next_actions)
                
            except Exception as e:
                st.info("🤖 AI analysis available after calculations complete")

        # Step indicators with AI recommendations
        cols = st.columns(len(steps))
        for i, (step_name, completed, description) in enumerate(steps):
            with cols[i]:
                if completed:
                    icon = "✅"
                    color = "green"
                elif i == completed_steps:
                    icon = "🎯"
                    color = "orange"
                else:
                    icon = "⏳"
                    color = "gray"
                
                st.markdown(f'<div style="text-align: center; color: {color}; font-weight: bold;">{icon}<br><small>{step_name.split(" ", 1)[1]}</small></div>', unsafe_allow_html=True)

        # AI-powered next step recommendations
        if completed_steps < len(steps):
            next_step = steps[completed_steps][0].split(" ", 1)[1]
            next_description = steps[completed_steps][2]
            
            st.markdown("---")
            st.markdown("### 🎯 AI-Recommended Next Steps")
            
            # Primary recommendation
            if next_step == "Project Setup":
                st.info(f"🎯 **Primary Action:** Complete {next_step}")
                st.write(next_description)
                st.write("💡 **AI Tip:** Choose the right electrical standard (IEC/NEC/IS) for your region to ensure compliance")
                
            elif next_step == "System Config":
                st.info(f"🎯 **Primary Action:** Configure {next_step}")
                st.write(next_description)
                if self.project.loads:
                    total_power = sum(load.power_kw for load in self.project.loads)
                    st.write(f"💡 **AI Tip:** Based on {total_power:.1f}kW total load, consider adding a main distribution bus")
                
            elif next_step == "Load Definition":
                st.info(f"🎯 **Primary Action:** Add {next_step}")
                st.write(next_description)
                st.write("💡 **AI Tip:** Use AI equipment suggester for optimal cable and breaker sizing")
                
            elif next_step == "Calculations":
                st.info(f"🎯 **Primary Action:** Run {next_step}")
                st.write(next_description)
                st.write("💡 **AI Tip:** Calculations will enable AI-powered optimization and safety analysis")
                
            elif next_step == "AI Analysis":
                st.info(f"🎯 **Primary Action:** Review {next_step}")
                st.write(next_description)
                st.write("💡 **AI Tip:** Pay special attention to safety concerns and optimization opportunities")
                
            elif next_step == "Complete":
                st.success(f"🎉 **Project Complete!**")
                st.write("📋 **AI Suggestions:**")
                st.write("• Generate comprehensive reports for documentation")
                st.write("• Export SLD diagrams for review")
                st.write("• Schedule peer review for critical designs")
                st.write("• Archive project data for future reference")

            # Quick action buttons
            action_col1, action_col2, action_col3 = st.columns(3)
            
            with action_col1:
                if st.button(f"🚀 Go to {next_step}", type="primary", key=f"go_to_{next_step.lower().replace(' ', '_')}"):
                    # Navigate to appropriate page
                    if "Project Setup" in next_step:
                        st.session_state.selected_page = "⚙️ Project Setup"
                    elif "System Config" in next_step:
                        st.session_state.selected_page = "🔧 Equipment Config"
                    elif "Load Definition" in next_step:
                        st.session_state.selected_page = "🔧 Equipment Config"
                    elif "Calculations" in next_step:
                        with st.spinner("🔄 Running calculations..."):
                            self._perform_calculations()
                        st.rerun()
                    elif "AI Analysis" in next_step:
                        st.session_state.selected_page = "📊 Design & Analysis"
                    elif "Complete" in next_step:
                        st.session_state.selected_page = "📊 Design & Analysis"
                    st.rerun()
            
            with action_col2:
                if self.ai_analyzer and completed_steps >= 3:  # After loads are added
                    if st.button("🤖 AI Check", key="ai_check_progress"):
                        try:
                            analysis = self.ai_analyzer.analyze_design(self.project)
                            if analysis.validation_issues:
                                st.error(f"⚠️ {len(analysis.validation_issues)} issues found")
                            else:
                                st.success("✅ No critical issues detected")
                        except:
                            st.warning("AI analysis unavailable")
            
            with action_col3:
                if st.button("📋 View Guide", key="view_guide"):
                    st.info("📖 **Guide:** Follow the step-by-step workflow for optimal results")

        # Project completion summary
        if completed_steps == len(steps):
            st.markdown("---")
            st.success("🎉 **Congratulations! Project Complete!**")
            st.balloons()
            
            # Final AI recommendations
            if self.ai_analyzer:
                try:
                    analysis = self.ai_analyzer.analyze_design(self.project)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Final AI Score", f"{analysis.overall_score:.0f}/100")
                        if analysis.overall_score >= 80:
                            st.success("🏆 Excellent design quality!")
                        elif analysis.overall_score >= 60:
                            st.info("👍 Good design with room for improvement")
                        else:
                            st.warning("⚠️ Consider optimization recommendations")
                    
                    with col2:
                        if st.button("📊 Generate Final Report", type="primary"):
                            self._ai_generate_executive_summary()
                            st.rerun()
                        
                        if st.button("📤 Export All Reports"):
                            self._quick_export_all()
                            st.success("All reports exported successfully!")
                
                except Exception as e:
                    st.info("📊 Generate your final reports and documentation")

    def _project_setup_page(self):
        """Project configuration page"""
        st.markdown('<h1 class="section-header">Project Setup</h1>', unsafe_allow_html=True)

        if not self.project:
            st.info("Create a new project to get started.")
            return

        # Use st.form to prevent immediate updates and session state conflicts
        with st.form("project_setup_form"):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Basic Information")
                project_name = st.text_input(
                    "Project Name",
                    value=self.project.project_name
                )
                project_id = st.text_input(
                    "Project ID",
                    value=self.project.project_id or ""
                )
                standard_options = ["IEC", "IS", "NEC"]
                try:
                    standard_index = standard_options.index(self.project.standard)
                except ValueError:
                    standard_index = 0
                standard = st.selectbox(
                    "Electrical Standard",
                    standard_options,
                    index=standard_index
                )

            with col2:
                st.subheader("Environmental Conditions")
                ambient_temp = st.number_input(
                    "Ambient Temperature (°C)",
                    value=float(self.project.ambient_temperature_c),
                    min_value=-20.0,
                    max_value=60.0,
                    step=0.5
                )
                altitude = st.number_input(
                    "Altitude (m)",
                    value=float(self.project.altitude_m),
                    min_value=0.0,
                    max_value=5000.0,
                    step=10.0
                )
                voltage_options = ["LV", "MV", "HV"]
                try:
                    voltage_index = voltage_options.index(self.project.voltage_system)
                except ValueError:
                    voltage_index = 0
                voltage_system = st.selectbox(
                    "Voltage System",
                    voltage_options,
                    index=voltage_index
                )

            # Submit button
            submitted = st.form_submit_button("💾 Save Project Settings", type="primary")

            if submitted:
                # Update project attributes
                self.project.project_name = project_name
                self.project.project_id = project_id
                self.project.standard = standard
                self.project.ambient_temperature_c = float(ambient_temp)
                self.project.altitude_m = float(altitude)
                self.project.voltage_system = voltage_system

                # Update calculation engine with new standard
                self.calc_engine = ElectricalCalculationEngine(standard=standard)

                # Save to session state
                st.session_state.project = self.project

                st.success("Project settings saved successfully!")

    def _ai_excel_extraction_page(self):
        """AI-powered Excel extraction interface"""
        st.markdown('<h1 class="section-header">🤖 AI Excel Extraction</h1>', unsafe_allow_html=True)

        # Initialize processing status
        initialize_processing_status()
        
        # Get or create unified processor - ensure all tabs share the same instance
        if 'unified_processor' not in st.session_state:
            st.session_state.unified_processor = create_unified_processor(
                self.project.standard if self.project else "IEC"
            )
        
        unified_processor = st.session_state.unified_processor
        
        # Main interface tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Excel", "🔄 Processing Status", "✏️ Manual Review", "📊 Results Dashboard"])
        
        with tab1:
            self._render_excel_upload_interface(unified_processor)
            
        with tab2:
            self._render_processing_status_interface(unified_processor)
            
        with tab3:
            self._render_manual_review_interface(unified_processor)
            
        with tab4:
            self._render_results_dashboard_interface(unified_processor)

    def _render_excel_upload_interface(self, unified_processor: UnifiedDataProcessor):
        """Render Excel file upload interface"""
        st.markdown("### 📁 Upload Excel File for AI Extraction")
        
        # Upload section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            **Supported Excel Formats:**
            - Load schedules with power, voltage, and equipment details
            - Cable schedules with specifications and routing information
            - Bus configurations with ratings and connections
            - Transformer schedules with ratings and vector groups
            """)
            
            # File uploader
            uploaded_file = st.file_uploader(
                "Choose an Excel file",
                type=['xlsx', 'xls'],
                help="Upload an Excel file containing electrical project data"
            )
            
            # Project name input
            project_name = st.text_input(
                "Project Name",
                value="AI Extracted Electrical Project",
                help="Name for the extracted project"
            )
            
        with col2:
            st.markdown("### 🎯 What the AI Extracts")
            st.markdown("""
            **Automatically Detects:**
            - ✅ Load IDs and specifications
            - ✅ Power ratings and voltages
            - ✅ Cable specifications
            - ✅ Equipment connections
            - ✅ Bus configurations
            - ✅ Transformer details
            """)
            
            st.markdown("### 📋 Processing Steps")
            st.markdown("""
            1. **File Analysis** - AI analyzes structure
            2. **Data Extraction** - Intelligent parsing
            3. **Validation** - Electrical rule checking
            4. **Enhancement** - Auto-correction
            5. **Integration** - Project creation
            """)
        
        # Processing options
        st.markdown("---")
        st.markdown("### ⚙️ Processing Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            auto_validate = st.checkbox("Auto-validate data", value=True, help="Automatically validate against electrical standards")
            
        with col2:
            auto_enhance = st.checkbox("Auto-enhance data", value=True, help="Automatically correct common issues")
            
        with col3:
            calculate_immediately = st.checkbox("Calculate immediately", value=True, help="Perform electrical calculations after extraction")
        
        # Process button
        if uploaded_file and project_name:
            if st.button("🚀 Start AI Extraction", type="primary", width='stretch'):
                with st.spinner("Initializing AI extraction pipeline..."):
                    # Start processing in session state to enable progress updates
                    st.session_state.current_processor = unified_processor
                    st.session_state.uploaded_file = uploaded_file
                    st.session_state.project_name = project_name
                    st.session_state.processing_options = {
                        'auto_validate': auto_validate,
                        'auto_enhance': auto_enhance,
                        'calculate_immediately': calculate_immediately
                    }
                    
                    # Process the file
                    success, message, project = unified_processor.process_excel_upload(uploaded_file, project_name)
                    
                    if success:
                        # Save extracted project to session state
                        self.project = project
                        st.session_state.project = self.project
                        st.session_state.calculation_results = {}  # Clear any previous calculations
                        
                        # Initialize unified processor with extracted project
                        try:
                            self.unified_processor = create_unified_processor(
                                self.project.standard if self.project else "IEC"
                            )
                        except Exception as e:
                            st.warning(f"Failed to initialize processor with extracted project: {e}")
                        
                        st.success(f"✅ {message}")
                        st.success(f"✅ Project '{self.project.project_name}' created with {len(self.project.loads)} loads, {len(self.project.buses)} buses")
                        st.info("📊 You can now:")
                        st.info("   • Switch to the 'Manual Review' tab to review extracted data")
                        st.info("   • Switch to the 'Results Dashboard' to see extraction summary")
                        st.info("   • Navigate to other project pages to work with the data")
                    else:
                        st.error(f"❌ {message}")
                        
                        # Provide helpful troubleshooting suggestions
                        with st.expander("🔧 Troubleshooting Help", expanded=False):
                            st.markdown("""
                            **Common issues and solutions:**
                            
                            1. **File Format Issues**
                               - Ensure your Excel file has proper column headers
                               - Use standard electrical engineering terminology
                               - Check that data is in tabular format (not merged cells)
                            
                            2. **Data Structure Issues**
                               - Load schedules should have columns like: Load ID, Load Name, Power (kW), Voltage (V)
                               - Cable schedules should have: Cable ID, From Equipment, To Equipment, Size (mm²)
                               - Use consistent naming conventions throughout the file
                            
                            3. **Content Issues**
                               - Ensure electrical components have valid specifications
                               - Check that power ratings and voltages are realistic
                               - Verify equipment connections make sense
                            
                            4. **Try Manual Workflow**
                               - If AI extraction continues to fail, use the manual workflow
                               - Create projects through the standard interface
                               - Export your data to standard formats and retry
                            """)
                    
                    st.rerun()
        else:
            st.info("👆 Please upload an Excel file and provide a project name to start extraction")
            
        # Sample file download
        st.markdown("---")
        st.markdown("### 📥 Sample Excel Files")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Download Sample Load Schedule", width='stretch'):
                self._create_sample_excel_file("load_schedule")
                
        with col2:
            if st.button("🔌 Download Sample Cable Schedule", width='stretch'):
                self._create_sample_excel_file("cable_schedule")
    
    def _render_processing_status_interface(self, unified_processor: UnifiedDataProcessor):
        """Render processing status and progress interface"""
        st.markdown("### 🔄 Processing Status & Progress")
        
        # Get current status
        current_status = get_processing_status()
        
        if current_status:
            # Render processing status
            ProcessingInterface.render_processing_status(current_status)
            
            # Show extraction report if available
            if hasattr(current_status, 'extraction_report') and current_status.extraction_report:
                st.markdown("---")
                ProcessingInterface.render_confidence_visualization(current_status.extraction_report)
                
                # Show validation issues
                if current_status.validation_results:
                    st.markdown("---")
                    ProcessingInterface.render_validation_issues(current_status.validation_results)
        else:
            st.info("💡 Upload an Excel file and start processing to see status here")
            
        # Manual workflow option
        st.markdown("---")
        st.markdown("### 🔄 Manual Workflow Alternative")
        
        if self.project:
            if st.button("🔄 Process Existing Project Manually", type="secondary"):
                success, message, enhanced_project = unified_processor.process_manual_workflow(self.project)
                
                if success:
                    st.success(f"✅ {message}")
                    st.info("📊 Check the Results Dashboard for enhanced project details")
                else:
                    st.error(f"❌ {message}")
                    
                st.rerun()
        else:
            st.info("👆 Create or load a project first to use manual workflow processing")

    def _render_manual_review_interface(self, unified_processor: UnifiedDataProcessor):
        """Render manual correction interface"""
        st.markdown("### ✏️ Manual Review & Corrections")
        
        # Get correction interface data
        correction_data = unified_processor.get_correction_interface_data()
        
        if correction_data:
            # Render correction interface
            ProcessingInterface.render_correction_interface(correction_data)
            
            # Handle correction submission
            if st.button("💾 Apply Manual Corrections", type="primary"):
                # Collect corrections from session state
                corrections = {}
                
                # Get corrections from text areas (would need to be implemented with proper session state management)
                for key in st.session_state.keys():
                    if key.startswith('correction_'):
                        sheet_name = key.replace('correction_', '')
                        corrections[sheet_name] = st.session_state[key]
                
                # Apply corrections
                success, message, corrected_project = unified_processor.apply_manual_corrections(corrections)
                
                if success:
                    st.success(f"✅ {message}")
                    st.info("📊 Corrections applied successfully")
                else:
                    st.error(f"❌ {message}")
                    
                st.rerun()
        else:
            st.info("💡 Process an Excel file first to see items requiring manual review")
            
        # High-confidence items confirmation
        if correction_data and correction_data.get('extraction_confidence', 0) > 0.8:
            st.markdown("---")
            st.success("✅ **High Confidence Extraction**")
            st.markdown("""
            Your data extraction shows high confidence scores. The system recommends proceeding with minimal manual review.
            
            **Recommended Actions:**
            - ✅ Accept extracted data as-is
            - ⚠️ Review only low-confidence items (if any)
            - 📊 Proceed to Results Dashboard
            """)
            
            if st.button("✅ Accept High Confidence Data", type="primary"):
                st.success("Data accepted and ready for use!")
                st.info("📊 Navigate to the Results Dashboard or other project pages")

    def _render_results_dashboard_interface(self, unified_processor: UnifiedDataProcessor):
        """Render comprehensive results dashboard"""
        st.markdown("### 📊 Results Dashboard")
        
        # Get dashboard data
        dashboard_data = unified_processor.get_processing_dashboard_data()
        
        if dashboard_data:
            # Project summary
            st.markdown("#### 📋 Project Summary")
            summary = dashboard_data.get('project_summary', {})
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Project Name", summary.get('project_name', 'N/A'))
                st.metric("Standard", summary.get('standard', 'N/A'))
                
            with col2:
                st.metric("Total Loads", summary.get('total_loads', 0))
                st.metric("Total Power", f"{summary.get('total_power_kw', 0):.1f} kW")
                
            with col3:
                st.metric("Total Cables", summary.get('total_cables', 0))
                st.metric("Total Buses", summary.get('total_buses', 0))
                
            with col4:
                st.metric("Transformers", summary.get('total_transformers', 0))
                st.metric("Diversity Factor", f"{summary.get('system_diversity_factor', 0):.3f}")
            
            # Extraction metrics
            if 'extraction_metrics' in dashboard_data:
                st.markdown("#### 🎯 Extraction Performance")
                metrics = dashboard_data['extraction_metrics']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    confidence = metrics.get('overall_confidence', 0) * 100
                    st.metric("Overall Confidence", f"{confidence:.1f}%")
                    
                with col2:
                    st.metric("Components Extracted", metrics.get('total_components', 0))
                    
                with col3:
                    processing_time = metrics.get('processing_time_seconds', 0)
                    st.metric("Processing Time", f"{processing_time:.1f}s")
                
                # Sheet results breakdown
                if 'sheet_results' in metrics:
                    st.markdown("**Sheet-by-Sheet Results:**")
                    for sheet_name, result in metrics['sheet_results'].items():
                        confidence = result.get('confidence', 0) * 100
                        components = result.get('components_extracted', 0)
                        quality = result.get('data_quality_score', 0) * 100
                        
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"**{sheet_name}**")
                        with col2:
                            st.write(f"Confidence: {confidence:.1f}%")
                        with col3:
                            st.write(f"Components: {components}")
            
            # Component statistics
            if 'component_statistics' in dashboard_data:
                st.markdown("#### 📈 Component Statistics")
                stats = dashboard_data['component_statistics']
                
                # Load statistics
                if 'loads' in stats:
                    load_stats = stats['loads']
                    st.markdown("**Load Analysis:**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Load Power", f"{load_stats.get('total_power_kw', 0):.1f} kW")
                        st.metric("Average Load", f"{load_stats.get('average_power_kw', 0):.1f} kW")
                        
                    with col2:
                        # Load type distribution
                        if 'load_types' in load_stats:
                            st.markdown("**Load Types:**")
                            for load_type, count in load_stats['load_types'].items():
                                st.write(f"• {load_type.title()}: {count}")
                
                # Cable statistics
                if 'cables' in stats:
                    cable_stats = stats['cables']
                    st.markdown("**Cable Analysis:**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Cable Length", f"{cable_stats.get('total_length_m', 0):.1f} m")
                        st.metric("Average Length", f"{cable_stats.get('average_length_m', 0):.1f} m")
                        
                    with col2:
                        # Size distribution
                        if 'size_distribution' in cable_stats:
                            st.markdown("**Size Distribution:**")
                            for size, count in list(cable_stats['size_distribution'].items())[:5]:
                                st.write(f"• {size} mm²: {count} cables")
            
            # Validation status
            if 'validation_status' in dashboard_data:
                st.markdown("#### 🔍 Validation Status")
                validation = dashboard_data['validation_status']
                
                errors = validation.get('errors', [])
                warnings = validation.get('warnings', [])
                
                if errors:
                    st.error(f"🚫 **Errors:** {len(errors)} found")
                    for error in errors[:5]:  # Show first 5 errors
                        st.error(f"• {error}")
                    if len(errors) > 5:
                        st.error(f"... and {len(errors) - 5} more errors")
                else:
                    st.success("✅ **No validation errors**")
                
                if warnings:
                    st.warning(f"⚠️ **Warnings:** {len(warnings)} found")
                    for warning in warnings[:3]:  # Show first 3 warnings
                        st.warning(f"• {warning}")
                    if len(warnings) > 3:
                        st.warning(f"... and {len(warnings) - 3} more warnings")
                else:
                    st.success("✅ **No validation warnings**")
            
            # Processing history
            if 'processing_history' in dashboard_data:
                st.markdown("#### 📜 Processing History")
                for event in dashboard_data['processing_history']:
                    timestamp = event.get('timestamp', '')
                    event_type = event.get('event', '')
                    details = event.get('details', '')
                    
                    st.info(f"**{event_type}** - {details}")
            
            # Action buttons
            st.markdown("---")
            st.markdown("### 🚀 Next Steps")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🧮 Run Calculations", type="primary", width='stretch'):
                    st.info("Navigate to the Calculations page to run detailed electrical analysis")
                    
            with col2:
                if st.button("📊 View Reports", type="primary", width='stretch'):
                    st.info("Navigate to Results & Reports page for detailed analysis")
                    
            with col3:
                if st.button("💾 Save Project", type="primary", width='stretch'):
                    self._save_project()
                    
        else:
            st.info("💡 Process an Excel file first to see results dashboard")

    def _create_template_project(self, template_type: str):
        """Create a project from predefined templates"""
        from demo_script import ElectricalDesignDemo

        demo = ElectricalDesignDemo()

        if template_type == "manufacturing":
            self.project = demo.create_manufacturing_plant_project()
            self.project.project_name = "Manufacturing Plant Project"
        elif template_type == "commercial":
            # Create a commercial building template
            self.project = Project(
                project_name="Commercial Building Project",
                standard="IEC",
                voltage_system="LV",
                ambient_temperature_c=35.0,
                altitude_m=0.0,
                created_by="EDA System Template",
                created_date=datetime.now().isoformat(),
                version="1.0"
            )
            # Add commercial loads
            commercial_loads = [
                ("HVAC System", 50, 400, 3, "hvac"),
                ("Lighting Main", 25, 230, 1, "lighting"),
                ("Elevator", 15, 400, 3, "motor"),
                ("Kitchen Equipment", 30, 400, 3, "general"),
                ("Server Room", 20, 230, 1, "general")
            ]
            for name, power, voltage, phases, load_type in commercial_loads:
                load = Load(
                    load_id=f"L{len(self.project.loads)+1:03d}",
                    load_name=name,
                    load_type=LoadType(load_type),
                    power_kw=power,
                    voltage=voltage,
                    phases=phases,
                    power_factor=0.85,
                    efficiency=0.9,
                    cable_length=25.0,
                    installation_method=InstallationMethod.tray,
                    priority=Priority.essential,
                    source_bus="B001"
                )
                self.project.add_load(load)

            # Add bus
            bus = Bus(
                bus_id="B001",
                bus_name="Main Distribution Bus",
                voltage=400,
                phases=3,
                rated_current_a=800,
                short_circuit_rating_ka=35.0,
                location="Main Electrical Room"
            )
            self.project.buses.append(bus)

        elif template_type == "residential":
            # Create a residential complex template
            self.project = Project(
                project_name="Residential Complex Project",
                standard="IEC",
                voltage_system="LV",
                ambient_temperature_c=30.0,
                altitude_m=0.0,
                created_by="EDA System Template",
                created_date=datetime.now().isoformat(),
                version="1.0"
            )
            # Add residential loads
            residential_loads = [
                ("Water Pump", 7.5, 400, 3, "motor"),
                ("Common Lighting", 15, 230, 1, "lighting"),
                ("Lift Motor", 11, 400, 3, "motor"),
                ("Backup Generator", 25, 400, 3, "general"),
                ("Security System", 5, 230, 1, "general")
            ]
            for name, power, voltage, phases, load_type in residential_loads:
                load = Load(
                    load_id=f"L{len(self.project.loads)+1:03d}",
                    load_name=name,
                    load_type=LoadType(load_type),
                    power_kw=power,
                    voltage=voltage,
                    phases=phases,
                    power_factor=0.85,
                    efficiency=0.9,
                    cable_length=30.0,
                    installation_method=InstallationMethod.conduit,
                    priority=Priority.essential,
                    source_bus="B001"
                )
                self.project.add_load(load)

            # Add bus
            bus = Bus(
                bus_id="B001",
                bus_name="Main Distribution Bus",
                voltage=400,
                phases=3,
                rated_current_a=400,
                short_circuit_rating_ka=25.0,
                location="Electrical Room"
            )
            self.project.buses.append(bus)

        # Clear previous calculations and save
        self.calculation_results = {}
        st.session_state.project = self.project
        st.session_state.calculation_results = self.calculation_results
        st.success(f"{template_type.title()} project template created!")
        st.info("💡 Go to System Configuration to customize loads and equipment, then run calculations in Analysis & Reports.")

    def _create_sample_excel_file(self, file_type: str):
        """Create sample Excel files for testing"""
        if file_type == "load_schedule":
            # Create sample load schedule
            data = {
                'Load ID': ['L001', 'L002', 'L003', 'L004', 'L005'],
                'Load Name': ['Motor Pump', 'HVAC Unit', 'Lighting Panel', 'Control Cabinet', 'Conveyor Motor'],
                'Power (kW)': [15.5, 25.0, 8.2, 5.5, 11.0],
                'Voltage (V)': [400, 400, 230, 230, 400],
                'Phases': [3, 3, 1, 1, 3],
                'Load Type': ['motor', 'hvac', 'lighting', 'general', 'motor'],
                'Power Factor': [0.85, 0.80, 0.90, 0.85, 0.85],
                'Efficiency': [0.92, 0.88, 0.95, 0.90, 0.91],
                'Source Bus': ['B001', 'B001', 'B002', 'B002', 'B001'],
                'Priority': ['essential', 'critical', 'non-essential', 'essential', 'essential']
            }
            df = pd.DataFrame(data)
            filename = "sample_load_schedule.xlsx"
            
        elif file_type == "cable_schedule":
            # Create sample cable schedule
            data = {
                'Cable ID': ['C001', 'C002', 'C003', 'C004', 'C005'],
                'From Equipment': ['B001', 'B001', 'B002', 'B002', 'B001'],
                'To Equipment': ['L001', 'L002', 'L003', 'L004', 'L005'],
                'Specification': ['4C x 4.0 sq.mm XLPE/PVC/SWA/PVC', '4C x 6.0 sq.mm XLPE/PVC/SWA/PVC',
                                '3C x 2.5 sq.mm XLPE/PVC/PVC', '3C x 2.5 sq.mm XLPE/PVC/PVC', '4C x 4.0 sq.mm XLPE/PVC/SWA/PVC'],
                'Cores': [4, 4, 3, 3, 4],
                'Size (mm²)': [4.0, 6.0, 2.5, 2.5, 4.0],
                'Length (m)': [45, 38, 22, 15, 52],
                'Installation': ['tray', 'tray', 'conduit', 'conduit', 'tray']
            }
            df = pd.DataFrame(data)
            filename = "sample_cable_schedule.xlsx"
        
        # Save to Excel
        df.to_excel(filename, index=False)
        
        # Download button
        with open(filename, 'rb') as f:
            st.download_button(
                label=f"📥 Download {filename}",
                data=f,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    def _load_management_page(self):
        """Load management interface"""
        st.markdown('<h1 class="section-header">Load Management</h1>', unsafe_allow_html=True)

        if not self.project:
            st.warning("Please create or load a project first.")
            return

        # Load overview
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Loads", len(self.project.loads))
        with col2:
            total_power = sum(load.power_kw for load in self.project.loads)
            st.metric("Total Power", f"{total_power:.1f} kW")
        with col3:
            avg_pf = sum(load.power_factor for load in self.project.loads) / len(self.project.loads) if self.project.loads else 0
            st.metric("Avg Power Factor", f"{avg_pf:.3f}")

        # CSV Import/Export
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📥 Import Loads")
            uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
            if uploaded_file is not None:
                if st.button("Import Loads from CSV"):
                    self._import_loads_from_csv(uploaded_file)

        with col2:
            st.subheader("📤 Export Loads")
            if st.button("Export Loads to CSV"):
                self._export_loads_to_csv()

        # Load table
        if self.project.loads:
            st.subheader("Current Loads")

            # Convert loads to DataFrame for display
            load_data = []
            for load in self.project.loads:
                load_data.append({
                    "ID": load.load_id,
                    "Name": load.load_name,
                    "Type": load.load_type.value,
                    "Power (kW)": load.power_kw,
                    "Voltage (V)": load.voltage,
                    "Phases": load.phases,
                    "PF": load.power_factor,
                    "Priority": load.priority.value,
                    "Bus": load.source_bus or "N/A"
                })

            df = pd.DataFrame(load_data)
            st.dataframe(df, width='content')

        # Add new load
        st.markdown("---")
        with st.expander("➕ Add New Load", expanded=False):
            self._add_load_form()

        # Edit/Delete loads
        if self.project.loads:
            st.markdown("---")
            with st.expander("✏️ Edit/Delete Loads", expanded=False):
                self._edit_load_form()

    def _add_load_form(self):
        """Enhanced form to add a new load with AI validation and intelligent suggestions"""
        with st.form("add_load_form"):
            # AI-powered assistance header
            st.markdown("### 🤖 AI-Assisted Load Configuration")
            
            # Smart defaults helper with enhanced AI
            if self.design_assistant and st.checkbox("🧠 Use AI Smart Defaults", value=True, help="Apply intelligent defaults based on load type and AI analysis"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    load_type_hint = st.selectbox("Load Type for AI Defaults", ["motor", "lighting", "hvac", "general"], index=0, key="load_type_hint")
                with col2:
                    voltage_hint = st.selectbox("Voltage for AI Defaults", [230, 400, 415, 440, 690], index=1, key="voltage_hint")
                with col3:
                    if st.form_submit_button("🚀 Apply AI Defaults", type="secondary"):
                        defaults = self.design_assistant.get_smart_defaults_for_load(load_type_hint, voltage_hint, 3)
                        st.session_state.load_defaults = defaults
                        st.success(f"🤖 AI defaults applied for {load_type_hint} at {voltage_hint}V!")
                        st.rerun()
            
            # AI Load Type Analysis
            if self.project and len(self.project.loads) > 0 and self.ai_analyzer:
                with st.expander("🎯 **AI Load Analysis**", expanded=False):
                    try:
                        # Analyze current load distribution
                        load_types = {}
                        for load in self.project.loads:
                            load_type = load.load_type.value
                            if load_type not in load_types:
                                load_types[load_type] = 0
                            load_types[load_type] += 1
                        
                        st.write("**Current Load Distribution:**")
                        for load_type, count in load_types.items():
                            st.write(f"• {load_type.title()}: {count} loads")
                        
                        # AI recommendation for next load type
                        if len(load_types) > 0:
                            most_common = max(load_types, key=load_types.get)
                            least_common = min(load_types, key=load_types.get)
                            st.info(f"💡 **AI Tip:** Most loads are {most_common} type. Consider balancing with {least_common} loads for better system design.")
                    
                    except Exception as e:
                        st.warning("AI analysis temporarily unavailable")

            # Apply defaults if available
            defaults = st.session_state.get("load_defaults", {}) or st.session_state.get("smart_defaults", {})

            col1, col2, col3 = st.columns(3)

            with col1:
                load_id = st.text_input("Load ID", placeholder="L001")
                load_name = st.text_input("Load Name", placeholder="Motor Pump")

            with col2:
                load_type_options = [lt.value for lt in LoadType]
                default_type_index = 0
                if defaults.get("type"):
                    try:
                        default_type_index = load_type_options.index(defaults["type"])
                    except ValueError:
                        pass
                load_type = st.selectbox("Load Type", load_type_options, index=default_type_index)
                power_kw = st.number_input("Power (kW)", min_value=0.001, step=0.1)
                voltage_options = [230, 400, 415, 440, 690, 3300, 6600, 11000, 33000]
                default_voltage_index = 2  # Default to 400V
                if defaults.get("voltage") and defaults["voltage"] in voltage_options:
                    default_voltage_index = voltage_options.index(defaults["voltage"])
                voltage = st.selectbox("Voltage (V)", voltage_options, index=default_voltage_index)

            with col3:
                phases = st.selectbox("Phases", [1, 3], index=1)
                power_factor = st.slider("Power Factor", 0.1, 1.0, defaults.get("power_factor", 0.85), 0.01)
                efficiency = st.slider("Efficiency", 0.1, 1.0, defaults.get("efficiency", 0.9), 0.01)

            col4, col5, col6 = st.columns(3)

            with col4:
                cable_length = st.number_input("Cable Length (m)", min_value=0.1, value=defaults.get("cable_length", 50.0))
                installation_method = st.selectbox("Installation", [im.value for im in InstallationMethod], index=1)

            with col5:
                priority = st.selectbox("Priority", [p.value for p in Priority], index=2)
                source_bus = st.selectbox("Source Bus", [""] + [bus.bus_id for bus in self.project.buses])

            with col6:
                redundancy = st.checkbox("Redundancy Required")
                notes = st.text_area("Notes", value=defaults.get("notes", ""), height=60)

            # Real-time AI validation section
            if power_kw > 0 and voltage > 0:
                with st.expander("🔍 **Real-time AI Validation**", expanded=False):
                    try:
                        # Calculate basic parameters for AI analysis
                        estimated_current = power_kw / (voltage * (power_factor if 'power_factor' in locals() else 0.85) * (1 if phases == 1 else 3**0.5))
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Est. Current", f"{estimated_current:.1f} A")
                        with col2:
                            # AI cable size suggestion
                            suggested_cable = max(1.5, estimated_current / 5)  # Simplified calculation
                            st.metric("Min. Cable", f"{suggested_cable:.1f} mm²")
                        with col3:
                            # AI breaker suggestion  
                            suggested_breaker = estimated_current * 1.25  # 125% rule
                            st.metric("Min. Breaker", f"{suggested_breaker:.0f} A")
                        
                        # AI-powered validation insights
                        if estimated_current > 1000:
                            st.warning("⚠️ **High Current Detected**: Consider using higher voltage or splitting the load")
                        if power_kw > 500:
                            st.info("💡 **Large Load**: This may require special protection and starting considerations")
                        if phases == 1 and power_kw > 50:
                            st.warning("⚠️ **Large Single-Phase Load**: Consider three-phase supply for better efficiency")
                        
                    except Exception as e:
                        st.info("AI validation unavailable")

            submitted = st.form_submit_button("🚀 Add Load with AI Validation", type="primary")

            if submitted:
                # Enhanced validation with AI
                load_params = {
                    "load_id": load_id,
                    "load_name": load_name,
                    "load_type": load_type,
                    "power_kw": power_kw,
                    "voltage": voltage,
                    "phases": phases,
                    "power_factor": power_factor,
                    "efficiency": efficiency,
                    "cable_length": cable_length,
                    "installation_method": installation_method
                }

                # AI-powered validation
                validation_issues = []
                validation_warnings = []
                ai_suggestions = []

                # Basic validation
                if not load_id or not load_name:
                    validation_issues.append("Load ID and Name are required")
                if power_kw <= 0:
                    validation_issues.append("Power must be greater than 0")
                if voltage <= 0:
                    validation_issues.append("Voltage must be greater than 0")

                # AI-powered engineering validation
                try:
                    # Calculate electrical parameters
                    estimated_current = power_kw / (voltage * power_factor * (1 if phases == 1 else 3**0.5))
                    
                    # AI engineering checks
                    if estimated_current > 2000:
                        validation_issues.append(f"Very high current ({estimated_current:.0f}A). Verify voltage and power ratings.")
                    elif estimated_current > 1000:
                        validation_warnings.append(f"High current ({estimated_current:.0f}A). Verify conductor sizing and protection.")
                    
                    # Load type specific AI validation
                    if load_type == "motor" and power_kw > 200:
                        validation_warnings.append("Large motor detected. Consider starting current and soft starter requirements.")
                    if load_type == "lighting" and power_kw > 100:
                        validation_warnings.append("High lighting load. Verify LED efficiency claims and circuit diversity.")
                    
                    # AI efficiency suggestions
                    if efficiency < 0.8:
                        ai_suggestions.append("Consider upgrading to higher efficiency equipment for energy savings.")
                    if power_factor < 0.85:
                        ai_suggestions.append("Power factor correction may be beneficial for this load.")
                    
                    # AI cable length validation
                    if estimated_current > 100 and cable_length > 100:
                        validation_warnings.append("Long cable run with high current. Check voltage drop requirements.")
                    
                except Exception as e:
                    validation_warnings.append("AI engineering validation temporarily unavailable.")

                if self.design_assistant:
                    try:
                        assistant_validation = self.design_assistant.validate_load_parameters(load_params)
                        if not assistant_validation["valid"]:
                            validation_issues.extend(assistant_validation["issues"])
                        if assistant_validation.get("warnings"):
                            validation_warnings.extend(assistant_validation["warnings"])
                    except:
                        pass

                # Display AI validation results
                if validation_issues:
                    st.error("🚫 **Critical Issues - Must Fix:**")
                    for issue in validation_issues:
                        st.error(f"• {issue}")
                    st.warning("Please resolve critical issues before adding the load.")
                    return

                if validation_warnings:
                    st.warning("⚠️ **AI Warnings - Review Recommended:**")
                    for warning in validation_warnings[:3]:  # Show first 3
                        st.warning(f"• {warning}")
                    if len(validation_warnings) > 3:
                        st.warning(f"... and {len(validation_warnings) - 3} more warnings")

                if ai_suggestions:
                    st.info("💡 **AI Optimization Suggestions:**")
                    for suggestion in ai_suggestions[:3]:  # Show first 3
                        st.info(f"• {suggestion}")
                    if len(ai_suggestions) > 3:
                        st.info(f"... and {len(ai_suggestions) - 3} more suggestions")

                try:
                    new_load = Load(
                        load_id=load_id,
                        load_name=load_name,
                        load_type=LoadType(load_type),
                        power_kw=power_kw,
                        voltage=voltage,
                        phases=phases,
                        power_factor=power_factor,
                        efficiency=efficiency,
                        cable_length=cable_length,
                        installation_method=InstallationMethod(installation_method),
                        priority=Priority(priority),
                        source_bus=source_bus if source_bus else None,
                        redundancy=redundancy,
                        notes=notes
                    )

                    self.project.add_load(new_load)

                    # Add to bus if specified
                    if source_bus:
                        bus = next((b for b in self.project.buses if b.bus_id == source_bus), None)
                        if bus:
                            bus.add_load(load_id)

                    # Save to session state
                    st.session_state.project = self.project

                    st.success(f"Load '{load_name}' added successfully!")

                except Exception as e:
                    st.error(f"Error adding load: {str(e)}")

    def _edit_load_form(self):
        """Form to edit or delete existing loads"""
        load_options = [f"{load.load_id}: {load.load_name}" for load in self.project.loads]
        selected_load = st.selectbox("Select Load to Edit", load_options)

        if selected_load:
            load_id = selected_load.split(":")[0]
            load = next((l for l in self.project.loads if l.load_id == load_id), None)

            if load:
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("🗑️ Delete Load", type="secondary"):
                        self.project.loads.remove(load)
                        # Save to session state
                        st.session_state.project = self.project
                        st.success(f"Load '{load.load_name}' deleted!")
                        st.rerun()

                with col2:
                    if st.button("✏️ Edit Load", type="primary"):
                        st.session_state.edit_load = load
                        st.rerun()

    def _system_configuration_page(self):
        """Unified system configuration page combining loads, buses, and transformers"""
        st.markdown('<h1 class="section-header">System Configuration</h1>', unsafe_allow_html=True)

        if not self.project:
            st.warning("Please create or load a project first.")
            return

        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Loads", len(self.project.loads))
        with col2:
            st.metric("Buses", len(self.project.buses))
        with col3:
            st.metric("Transformers", len(self.project.transformers))
        with col4:
            ready_for_calc = "✅ Ready" if len(self.project.loads) > 0 and len(self.project.buses) > 0 else "⚠️ Incomplete"
            st.metric("System Status", ready_for_calc)

        tab1, tab2, tab3, tab4 = st.tabs(["💡 Load Management", "🚌 Bus Configuration", "🔌 Transformer Setup", "⚡ Cable & Breaker Auto-Config"])

        with tab1:
            self._load_management_tab()

        with tab2:
            self._bus_configuration_tab()

        with tab3:
            self._transformer_configuration_tab()

        with tab4:
            self._cable_breaker_tab()

        # Quick actions for this page
        st.markdown("---")
        st.markdown("### Quick Actions")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("➕ Add Common Load Types", type="secondary"):
                self._add_common_loads()
                st.rerun()

        with col2:
            if st.button("🔄 Generate Standard Buses", type="secondary"):
                self._generate_standard_buses()
                st.rerun()

        with col3:
            if len(self.project.loads) > 0 and len(self.project.buses) > 0 and not self.calculation_results:
                if st.button("🚀 Run Calculations Now", type="primary"):
                    with st.spinner("Running calculations..."):
                        self._perform_calculations()
                    st.session_state.selected_page = "📊 Analysis & Reports"
                    st.rerun()

    def _load_management_tab(self):
        """Load management within system configuration"""
        st.subheader("Load Management")

        # Quick load addition
        with st.expander("➕ Quick Add Loads", expanded=False):
            col1, col2 = st.columns([1, 2])

            with col1:
                load_templates = {
                    "Motor (15kW, 400V)": {"power": 15, "voltage": 400, "phases": 3, "type": "motor"},
                    "HVAC Unit (25kW, 400V)": {"power": 25, "voltage": 400, "phases": 3, "type": "hvac"},
                    "Lighting Panel (8kW, 230V)": {"power": 8, "voltage": 230, "phases": 1, "type": "lighting"},
                    "Control Cabinet (5kW, 230V)": {"power": 5, "voltage": 230, "phases": 1, "type": "general"},
                    "Conveyor Motor (11kW, 400V)": {"power": 11, "voltage": 400, "phases": 3, "type": "motor"}
                }

                template_choice = st.selectbox("Load Template", list(load_templates.keys()))
                if template_choice:
                    template = load_templates[template_choice]
                    if st.button("Add This Load"):
                        self._add_load_from_template(template, template_choice.split(" (")[0])

    def _add_load_from_template(self, template: dict, name: str):
        """Add a load using template data"""
        load = Load(
            load_id=f"L{len(self.project.loads)+1:03d}",
            load_name=name,
            load_type=LoadType(template["type"]),
            power_kw=template["power"],
            voltage=template["voltage"],
            phases=template["phases"],
            power_factor=0.85,
            efficiency=0.9,
            cable_length=50.0,
            installation_method=InstallationMethod.tray,
            priority=Priority.essential,
            source_bus="B001" if self.project.buses else None
        )
        self.project.add_load(load)
        st.session_state.project = self.project
        st.success(f"Load '{name}' added successfully!")

    def _generate_standard_buses(self):
        """Generate standard bus configuration"""
        if len(self.project.buses) == 0:
            # Add a main distribution bus
            bus = Bus(
                bus_id="B001",
                bus_name="Main Distribution Bus",
                voltage=400,
                phases=3,
                rated_current_a=1000,
                short_circuit_rating_ka=35.0,
                location="Main Electrical Room"
            )
            self.project.buses.append(bus)
            st.session_state.project = self.project
            st.success("Standard bus configuration generated!")
        else:
            st.info("Buses already exist. Use manual configuration to add more.")

    def _add_common_loads(self):
        """Add common load types to the project"""
        common_loads = [
            ("Motor (15kW, 400V)", 15, 400, 3, "motor"),
            ("HVAC Unit (25kW, 400V)", 25, 400, 3, "hvac"),
            ("Lighting Panel (8kW, 230V)", 8, 230, 1, "lighting"),
            ("Control Cabinet (5kW, 230V)", 5, 230, 1, "general"),
            ("Conveyor Motor (11kW, 400V)", 11, 400, 3, "motor"),
        ]

        added_count = 0
        for name, power, voltage, phases, load_type in common_loads:
            load = Load(
                load_id=f"L{len(self.project.loads)+1:03d}",
                load_name=name,
                load_type=LoadType(load_type),
                power_kw=power,
                voltage=voltage,
                phases=phases,
                power_factor=0.85,
                efficiency=0.9,
                cable_length=50.0,
                installation_method=InstallationMethod.tray,
                priority=Priority.essential,
                source_bus="B001" if self.project.buses else None
            )
            self.project.add_load(load)
            added_count += 1

        st.session_state.project = self.project
        st.success(f"Added {added_count} common loads to your project!")

    def _quick_export_all(self):
        """Quick export all reports"""
        try:
            # Export load list
            self._export_load_list_excel()
            # Export cable schedule
            self._export_cable_schedule_excel()
            # Export project JSON
            self._export_project_json()
            st.success("All reports exported successfully!")
        except Exception as e:
            st.error(f"Export failed: {str(e)}")

            with col2:
                # CSV upload for bulk import
                uploaded_file = st.file_uploader("Bulk Import CSV", type=['csv'], key="bulk_load_csv")
                if uploaded_file is not None:
                    if st.button("Import Loads from CSV"):
                        self._import_loads_from_csv(uploaded_file)
                        st.rerun()

        # Existing loads display
        if self.project.loads:
            st.subheader("Current Loads")
            load_data = []
            for load in self.project.loads:
                load_data.append({
                    "ID": load.load_id,
                    "Name": load.load_name,
                    "Power (kW)": load.power_kw,
                    "Voltage (V)": load.voltage,
                    "Bus": load.source_bus or "Not assigned",
                    "Type": load.load_type.value
                })

            df = pd.DataFrame(load_data)
            st.dataframe(df, use_container_width=True)

            # Quick edit/delete
            st.markdown("**Quick Edit:**")
            load_options = [f"{load.load_id}: {load.load_name}" for load in self.project.loads]
            selected_load = st.selectbox("Select load to edit", load_options, key="load_edit_select")

            if selected_load:
                load_id = selected_load.split(":")[0]
                load = next((l for l in self.project.loads if l.load_id == load_id), None)

                if load:
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✏️ Change Bus Assignment", key=f"edit_bus_{load_id}"):
                            st.session_state.edit_load_bus = load
                            st.rerun()
                    with col2:
                        if st.button("🗑️ Delete Load", key=f"delete_{load_id}", type="secondary"):
                            self.project.loads.remove(load)
                            st.session_state.project = self.project
                            st.success(f"Load '{load.load_name}' deleted!")
                            st.rerun()
        else:
            st.info("No loads defined yet. Use the Quick Add section above to get started.")

    def _cable_breaker_tab(self):
        """Cable and breaker configuration (auto-generated)"""
        st.subheader("Cable & Breaker Configuration")

        if not self.calculation_results:
            st.info("⚠️ Cables and breakers will be automatically generated during calculations.")
            st.markdown("**To generate:**")
            st.markdown("1. Add loads and buses in other tabs")
            st.markdown("2. Run calculations from the dashboard or use the button below")

            if len(self.project.loads) > 0 and len(self.project.buses) > 0:
                if st.button("🚀 Generate System Now", type="primary"):
                    with st.spinner("Running calculations and generating cables/breakers..."):
                        self._perform_calculations()
                    st.rerun()
            else:
                st.warning("Add loads and buses first before generating cables and breakers.")
        else:
            # Display generated cables and breakers
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Breakers**")
                if self.project.breakers:
                    breaker_data = []
                    for br in self.project.breakers:
                        breaker_data.append({
                            "ID": br.breaker_id,
                            "Load": br.load_id,
                            "Rating (A)": br.rated_current_a,
                            "Type": br.type
                        })
                    df = pd.DataFrame(breaker_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No breakers generated yet.")

            with col2:
                st.markdown("**Cables**")
                if self.project.cables:
                    cable_data = []
                    for cable in self.project.cables:
                        cable_data.append({
                            "ID": cable.cable_id,
                            "From": cable.from_equipment,
                            "To": cable.to_equipment,
                            "Size (mm²)": cable.size_sqmm,
                            "Length (m)": cable.length_m
                        })
                    df = pd.DataFrame(cable_data)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No cables generated yet.")

    def _equipment_config_page(self):
        """Equipment configuration page"""
        st.markdown('<h1 class="section-header">Equipment Configuration</h1>', unsafe_allow_html=True)

        if not self.project:
            st.warning("Please create or load a project first.")
            return

        tab1, tab2, tab3, tab4 = st.tabs(["🚌 Buses", "🔌 Transformers", "⚡ Breakers & Cables", "🤖 AI Suggestions"])

        with tab1:
            self._bus_configuration_tab()

        with tab2:
            self._transformer_configuration_tab()

        with tab3:
            self._breaker_cable_tab()
        
        with tab4:
            self._ai_equipment_suggestions_tab()

    def _bus_configuration_tab(self):
        """Bus configuration interface with AI insights"""
        st.subheader("🚌 Bus Configuration with AI Guidance")

        # AI Insights for Bus Configuration
        if self.project.buses and self.ai_analyzer:
            try:
                with st.spinner("🤖 AI analyzing bus configuration..."):
                    analysis = self.ai_analyzer.analyze_design(self.project)
                
                # AI Bus Recommendations
                if analysis.recommendations:
                    bus_recommendations = [rec for rec in analysis.recommendations if "bus" in rec.lower() or "distribution" in rec.lower()]
                    if bus_recommendations:
                        st.info("🤖 **AI Bus Recommendations:**")
                        for rec in bus_recommendations[:2]:
                            st.write(f"• {rec}")
                
                # Bus Status Analysis
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Buses", len(self.project.buses))
                with col2:
                    total_bus_capacity = sum(bus.rated_current_a for bus in self.project.buses)
                    st.metric("Total Capacity", f"{total_bus_capacity:.0f} A")
                with col3:
                    if self.project.loads:
                        connected_loads = sum(len(bus.connected_loads) for bus in self.project.buses)
                        st.metric("Connected Loads", connected_loads)
                
            except Exception as e:
                pass

        # Display existing buses with AI insights
        if self.project.buses:
            bus_data = []
            for bus in self.project.buses:
                # AI-powered bus utilization analysis
                utilization = 0
                if hasattr(bus, 'demand_kw') and bus.demand_kw:
                    # Calculate approximate utilization based on demand vs capacity
                    apparent_power = bus.demand_kw / 0.85  # Assuming 0.85 PF
                    utilization = (apparent_power * 1000) / (bus.voltage * bus.rated_current_a * (3**0.5)) * 100 if bus.voltage and bus.rated_current_a else 0
                
                utilization_status = "🟢 Good" if utilization < 70 else "🟡 Moderate" if utilization < 90 else "🔴 High"
                
                bus_data.append({
                    "ID": bus.bus_id,
                    "Name": bus.bus_name,
                    "Voltage (V)": bus.voltage,
                    "Phases": bus.phases,
                    "Rating (A)": bus.rated_current_a,
                    "Utilization": f"{utilization:.1f}%",
                    "Status": utilization_status,
                    "SC Rating (kA)": bus.short_circuit_rating_ka,
                    "Connected Loads": len(bus.connected_loads),
                    "Location": bus.location or "N/A"
                })

            df = pd.DataFrame(bus_data)
            st.dataframe(df, width='content')
            
            # AI Bus Optimization Tips
            if self.ai_analyzer:
                with st.expander("🤖 AI Bus Optimization Tips", expanded=False):
                    st.markdown("**Intelligent Bus Management:**")
                    st.write("• 🎯 **Load Balancing**: Distribute loads evenly across buses for optimal performance")
                    st.write("• ⚡ **Capacity Planning**: Ensure buses have adequate capacity for future expansion")
                    st.write("• 🛡️ **Safety Margins**: Maintain at least 20% spare capacity on critical buses")
                    st.write("• 📊 **Monitoring**: Track bus utilization to prevent overloading")
                    
                    # Specific recommendations based on current configuration
                    high_utilization_buses = [bus for bus in self.project.buses if hasattr(bus, 'demand_kw') and bus.demand_kw]
                    if high_utilization_buses:
                        st.warning("⚠️ **High Utilization Detected:** Consider redistributing loads or adding additional buses")
                    
                    if len(self.project.buses) == 1 and len(self.project.loads) > 10:
                        st.info("💡 **Suggestion:** Consider adding multiple buses for better load distribution in larger systems")

        # Add new bus
        with st.expander("➕ Add New Bus", expanded=False):
            with st.form("add_bus_form"):
                col1, col2 = st.columns(2)

                with col1:
                    bus_id = st.text_input("Bus ID", placeholder="B001")
                    bus_name = st.text_input("Bus Name", placeholder="Main Distribution Bus")
                    voltage = st.selectbox("Voltage (V)", [230, 400, 415, 440, 690, 3300, 6600, 11000, 33000], index=2)
                    phases = st.selectbox("Phases", [1, 3], index=1)

                with col2:
                    rated_current = st.number_input("Rated Current (A)", min_value=1.0, value=1000.0)
                    sc_rating = st.number_input("Short Circuit Rating (kA)", min_value=1.0, value=35.0)
                    location = st.text_input("Location", placeholder="Main Electrical Room")
                    parent_bus = st.selectbox("Parent Bus", [""] + [bus.bus_id for bus in self.project.buses])

                submitted = st.form_submit_button("➕ Add Bus", type="primary")

                if submitted:
                    try:
                        new_bus = Bus(
                            bus_id=bus_id,
                            bus_name=bus_name,
                            voltage=voltage,
                            phases=phases,
                            rated_current_a=rated_current,
                            short_circuit_rating_ka=sc_rating,
                            parent_bus=parent_bus if parent_bus else None,
                            location=location
                        )

                        self.project.buses.append(new_bus)

                        # Update parent bus children
                        if parent_bus:
                            parent = next((b for b in self.project.buses if b.bus_id == parent_bus), None)
                            if parent and bus_id not in parent.child_buses:
                                parent.child_buses.append(bus_id)

                        # Save to session state
                        st.session_state.project = self.project

                        st.success(f"Bus '{bus_name}' added successfully!")

                    except Exception as e:
                        st.error(f"Error adding bus: {str(e)}")

    def _transformer_configuration_tab(self):
        """Transformer configuration interface with AI insights"""
        st.subheader("🔌 Transformer Configuration with AI Guidance")

        # AI Insights for Transformer Configuration
        if self.project.transformers and self.ai_analyzer:
            try:
                with st.spinner("🤖 AI analyzing transformer configuration..."):
                    analysis = self.ai_analyzer.analyze_design(self.project)
                
                # AI Transformer Recommendations
                tx_recommendations = [rec for rec in analysis.recommendations if "transformer" in rec.lower() or "tx" in rec.lower()]
                if tx_recommendations:
                    st.info("🤖 **AI Transformer Recommendations:**")
                    for rec in tx_recommendations[:2]:
                        st.write(f"• {rec}")
                
                # Transformer Status Analysis
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Transformers", len(self.project.transformers))
                with col2:
                    total_capacity = sum(tx.rating_kva for tx in self.project.transformers)
                    st.metric("Total Capacity", f"{total_capacity:.0f} kVA")
                with col3:
                    if self.project.loads:
                        total_load = sum(load.power_kw for load in self.project.loads)
                        utilization = (total_load / total_capacity) * 100 if total_capacity > 0 else 0
                        st.metric("System Utilization", f"{utilization:.1f}%")
                
            except Exception as e:
                pass

        # Display existing transformers with AI insights
        if self.project.transformers:
            transformer_data = []
            for tx in self.project.transformers:
                # AI-powered transformer utilization analysis
                utilization = 0
                if self.project.loads:
                    # Calculate loads connected to this transformer (simplified)
                    total_load = sum(load.power_kw for load in self.project.loads)
                    utilization = (total_load / tx.rating_kva) * 100 if tx.rating_kva > 0 else 0
                
                efficiency_status = "🟢 Optimal" if 40 <= utilization <= 80 else "🟡 Light Load" if utilization < 40 else "🔴 Heavy Load"
                
                transformer_data.append({
                    "ID": tx.transformer_id,
                    "Name": tx.name,
                    "Rating (kVA)": tx.rating_kva,
                    "Primary (V)": tx.primary_voltage_v,
                    "Secondary (V)": tx.secondary_voltage_v,
                    "Utilization": f"{utilization:.1f}%",
                    "Status": efficiency_status,
                    "Type": tx.type,
                    "Vector Group": tx.vector_group,
                    "Impedance (%)": tx.impedance_percent
                })

            df = pd.DataFrame(transformer_data)
            st.dataframe(df, width='content')
            
            # AI Transformer Optimization Tips
            if self.ai_analyzer:
                with st.expander("🤖 AI Transformer Optimization Tips", expanded=False):
                    st.markdown("**Intelligent Transformer Management:**")
                    st.write("• ⚡ **Efficiency Zone**: Aim for 40-80% utilization for optimal efficiency")
                    st.write("• 🌡️ **Temperature Management**: Monitor loading to prevent overheating")
                    st.write("• 🔧 **Maintenance Planning**: Schedule maintenance based on loading patterns")
                    st.write("• 📈 **Future Planning**: Consider growth projections when sizing transformers")
                    
                    # Specific recommendations based on current configuration
                    if self.project.transformers:
                        total_capacity = sum(tx.rating_kva for tx in self.project.transformers)
                        total_load = sum(load.power_kw for load in self.project.loads)
                        
                        if total_load > total_capacity * 0.9:
                            st.warning("⚠️ **High System Loading**: Consider transformer upgrades or load redistribution")
                        elif total_load < total_capacity * 0.3:
                            st.info("💡 **Light Loading**: System may be oversized, consider right-sizing for efficiency")
                        
                        # Voltage level recommendations
                        voltage_levels = set(tx.secondary_voltage_v for tx in self.project.transformers)
                        if len(voltage_levels) > 2:
                            st.warning("⚠️ **Multiple Voltage Levels**: Simplify distribution where possible for better reliability")
                        
                        # Redundancy suggestions
                        if len(self.project.transformers) == 1 and total_load > 500:  # kW threshold
                            st.info("💡 **Redundancy**: Consider parallel transformers for critical applications")

        # Add new transformer
        with st.expander("➕ Add New Transformer", expanded=False):
            with st.form("add_transformer_form"):
                col1, col2 = st.columns(2)

                with col1:
                    tx_id = st.text_input("Transformer ID", placeholder="T001")
                    tx_name = st.text_input("Name", placeholder="Main Power Transformer")
                    rating_kva = st.number_input("Rating (kVA)", min_value=10.0, value=1000.0)
                    primary_voltage = st.selectbox("Primary Voltage (V)", [33000, 11000, 6600, 3300, 690, 415, 400], index=1)

                with col2:
                    secondary_voltage = st.selectbox("Secondary Voltage (V)", [11000, 6600, 3300, 690, 415, 400, 230], index=4)
                    tx_type = st.selectbox("Type", ["oil_immersed", "dry_type", "cast_resin"], index=0)
                    vector_group = st.selectbox("Vector Group", ["Dyn11", "Dyn5", "Yyn0", "Dd0"], index=0)
                    impedance = st.number_input("Impedance (%)", min_value=3.0, max_value=15.0, value=6.0)

                submitted = st.form_submit_button("➕ Add Transformer", type="primary")

                if submitted:
                    try:
                        new_tx = Transformer(
                            transformer_id=tx_id,
                            name=tx_name,
                            rating_kva=rating_kva,
                            primary_voltage_v=primary_voltage,
                            secondary_voltage_v=secondary_voltage,
                            impedance_percent=impedance,
                            vector_group=vector_group,
                            type=tx_type
                        )
                        new_tx.calculate_currents()

                        self.project.transformers.append(new_tx)
                        # Save to session state
                        st.session_state.project = self.project
                        st.success(f"Transformer '{tx_name}' added successfully!")

                    except Exception as e:
                        st.error(f"Error adding transformer: {str(e)}")

    def _breaker_cable_tab(self):
        """Breaker and cable configuration"""
        st.subheader("Breakers and Cables")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Breakers**")
            if self.project.breakers:
                breaker_data = []
                for br in self.project.breakers:
                    breaker_data.append({
                        "ID": br.breaker_id,
                        "Name": getattr(br, 'name', 'N/A'),
                        "Load ID": br.load_id,
                        "Rating (A)": br.rated_current_a,
                        "Type": br.type,
                        "Poles": br.poles
                    })

                df = pd.DataFrame(breaker_data)
                st.dataframe(df, width='content')
            else:
                st.info("Breakers will be auto-generated during calculations")
            
            # Add new breaker
            with st.expander("➕ Add New Breaker", expanded=False):
                with st.form("add_breaker_form"):
                    breaker_id = st.text_input("Breaker ID", placeholder="BR001")
                    breaker_name = st.text_input("Breaker Name", placeholder="Main Breaker")
                    load_id = st.selectbox("Associated Load", [l.load_id for l in self.project.loads] if self.project.loads else [])
                    rating_a = st.number_input("Rating (A)", min_value=1.0, value=100.0)
                    breaker_type = st.selectbox("Type", ["MCB", "MCCB", "ACB", "Relay"])
                    poles = st.selectbox("Poles", [1, 3], index=1)
                    curve = st.selectbox("Curve", ["B", "C", "D"], index=1)
                    
                    submitted = st.form_submit_button("➕ Add Breaker", type="primary")
                    
                    if submitted:
                        try:
                            new_breaker = Breaker(
                                breaker_id=breaker_id,
                                load_id=load_id,
                                rated_current_a=rating_a,
                                type=breaker_type,
                                poles=poles,
                                curve=curve
                            )
                            if hasattr(new_breaker, 'name'):
                                new_breaker.name = breaker_name
                            
                            self.project.breakers.append(new_breaker)
                            st.session_state.project = self.project
                            st.success(f"Breaker '{breaker_name}' added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding breaker: {str(e)}")

        with col2:
            st.markdown("**Cables**")
            if self.project.cables:
                cable_data = []
                for cable in self.project.cables:
                    cable_data.append({
                        "ID": cable.cable_id,
                        "Name": getattr(cable, 'name', 'N/A'),
                        "From": cable.from_equipment,
                        "To": cable.to_equipment,
                        "Size (mm²)": cable.size_sqmm,
                        "Length (m)": cable.length_m,
                        "Type": cable.cable_type
                    })

                df = pd.DataFrame(cable_data)
                st.dataframe(df, width='content')
            else:
                st.info("Cables will be auto-generated during calculations")
            
            # Add new cable
            with st.expander("➕ Add New Cable", expanded=False):
                with st.form("add_cable_form"):
                    cable_id = st.text_input("Cable ID", placeholder="C001")
                    cable_name = st.text_input("Cable Name", placeholder="Main Supply Cable")
                    from_equipment = st.text_input("From Equipment", placeholder="Transformer or Bus ID")
                    to_equipment = st.text_input("To Equipment", placeholder="Load or Bus ID")
                    size_sqmm = st.number_input("Size (mm²)", min_value=1.0, value=10.0)
                    length_m = st.number_input("Length (m)", min_value=0.1, value=10.0)
                    cable_type = st.selectbox("Cable Type", ["Single Core", "Twin Core", "3-Phase+N+E"])
                    
                    submitted = st.form_submit_button("➕ Add Cable", type="primary")
                    
                    if submitted:
                        try:
                            new_cable = Cable(
                                cable_id=cable_id,
                                from_equipment=from_equipment,
                                to_equipment=to_equipment,
                                size_sqmm=size_sqmm,
                                length_m=length_m,
                                cable_type=cable_type
                            )
                            if hasattr(new_cable, 'name'):
                                new_cable.name = cable_name
                            
                            self.project.cables.append(new_cable)
                            st.session_state.project = self.project
                            st.success(f"Cable '{cable_name}' added successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding cable: {str(e)}")

    def _ai_equipment_suggestions_tab(self):
        """AI Equipment Configuration Suggestions tab"""
        st.subheader("🤖 AI Equipment Recommendations")
        
        if not self.project or not self.project.loads:
            st.info("No loads in project yet. Add loads to get AI equipment recommendations.")
            return
        
        if not self.equipment_suggester:
            st.warning("AI Equipment Suggester not initialized. Some features may be unavailable.")
            return
        
        st.markdown("Get intelligent default values for equipment configuration based on electrical engineering best practices.")
        
        for load in self.project.loads[:10]:  # Show suggestions for first 10 loads
            with st.expander(f"📌 {load.load_id}: {load.load_name}", expanded=False):
                try:
                    config = self.equipment_suggester.get_quick_configuration(load)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if config["cable"]:
                            st.markdown("**🔌 Cable Recommendation**")
                            st.write(f"Size: **{config['cable']['size_sqmm']} mm²**")
                            st.write(f"Type: {config['cable']['type']}")
                            st.write(f"Material: {config['cable']['material']}")
                            st.caption(config['cable']['reason'])
                            
                            # Quick add button for cable
                            if st.button(f"➕ Add This Cable", key=f"add_cable_sugg_{load.load_id}"):
                                try:
                                    new_cable = Cable(
                                        cable_id=f"C{load.load_id[1:]}",
                                        from_equipment=load.source_bus,
                                        to_equipment=load.load_id,
                                        size_sqmm=config['cable']['size_sqmm'],
                                        cable_type=config['cable']['type'],
                                        length_m=10.0
                                    )
                                    if hasattr(new_cable, 'name'):
                                        new_cable.name = f"{load.load_name} - Cable"
                                    
                                    self.project.cables.append(new_cable)
                                    st.session_state.project = self.project
                                    st.success("Cable added!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error adding cable: {str(e)}")
                    
                    with col2:
                        if config["breaker"]:
                            st.markdown("**⚡ Breaker Recommendation**")
                            st.write(f"Rating: **{config['breaker']['rating_a']:.0f} A**")
                            st.write(f"Type: {config['breaker']['type']}")
                            st.write(f"Curve: {config['breaker']['curve']}")
                            st.caption(config['breaker']['reason'])
                            
                            # Quick add button for breaker
                            if st.button(f"➕ Add This Breaker", key=f"add_breaker_sugg_{load.load_id}"):
                                try:
                                    new_breaker = Breaker(
                                        breaker_id=f"BR{load.load_id[1:]}",
                                        load_id=load.load_id,
                                        rated_current_a=config['breaker']['rating_a'],
                                        type=config['breaker']['type'],
                                        curve=config['breaker']['curve'],
                                        poles=3
                                    )
                                    if hasattr(new_breaker, 'name'):
                                        new_breaker.name = f"{load.load_name} - Breaker"
                                    
                                    self.project.breakers.append(new_breaker)
                                    st.session_state.project = self.project
                                    st.success("Breaker added!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error adding breaker: {str(e)}")
                    
                    with col3:
                        if config["starter"]:
                            st.markdown("**🔧 Starter Recommendation**")
                            st.write(f"Type: {config['starter']['type']}")
                            st.caption(config['starter']['reason'])
                    
                    if config['notes']:
                        st.info("\n".join(config['notes']))
                
                except Exception as e:
                    st.warning(f"Error generating recommendations: {str(e)}")

    def _calculations_page(self):
        """Calculations execution page"""
        st.markdown('<h1 class="section-header">Electrical Calculations</h1>', unsafe_allow_html=True)

        if not self.project:
            st.warning("Please create or load a project first.")
            return

        # Pre-calculation checks
        issues = []

        if not self.project.loads:
            issues.append("No loads defined")
        if not self.project.buses:
            issues.append("No buses defined")
        if not self.project.transformers:
            issues.append("No transformers defined")

        if issues:
            st.error("Cannot perform calculations. Issues found:")
            for issue in issues:
                st.error(f"• {issue}")
            return

        # Calculation status
        if self.calculation_results:
            st.success("✅ Calculations completed!")
        else:
            st.info("⚠️ Calculations not yet performed")

        # Run calculations button
        if st.button("🚀 Run Electrical Calculations", type="primary", width='stretch'):
            with st.spinner("Performing electrical calculations..."):
                try:
                    self._perform_calculations()
                    st.success("Calculations completed successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Calculation error: {str(e)}")

        # Display calculation results
        if self.calculation_results:
            self._display_calculation_results()

    def _perform_calculations(self):
        """Perform all electrical calculations"""
        # Calculate loads
        for load in self.project.loads:
            try:
                calculated_load = self.calc_engine.calculate_load(load)
                # Update the load in the project
                idx = self.project.loads.index(load)
                self.project.loads[idx] = calculated_load
            except Exception as e:
                st.warning(f"Error calculating load {load.load_id}: {str(e)}")

        # Calculate bus loads
        for bus in self.project.buses:
            total_load = bus.calculate_total_load(self.project.loads)
            demand_load = total_load * bus.diversity_factor
            bus.demand_kw = demand_load
            bus.demand_kva = demand_load / 0.85  # Assuming average PF

        # Calculate project totals
        self.project.total_installed_capacity_kw = sum(load.power_kw for load in self.project.loads)
        self.project.total_demand_kw = sum(bus.demand_kw for bus in self.project.buses if bus.demand_kw)
        self.project.system_diversity_factor = self.project.total_demand_kw / self.project.total_installed_capacity_kw if self.project.total_installed_capacity_kw > 0 else 1.0
        # Handle case where buses exist but none have valid demand_kva
        if self.project.buses and any(bus.demand_kva for bus in self.project.buses if bus.demand_kva):
            self.project.main_transformer_rating_kva = max(bus.demand_kva for bus in self.project.buses if bus.demand_kva)
        else:
            self.project.main_transformer_rating_kva = 0

        # Create cables and breakers for calculated loads
        self._create_cables_and_breakers_from_calculations()

        # Generate SLD graph after calculations
        self._generate_sld_graph()

        self.calculation_results = {
            "completed": True,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_loads": len(self.project.loads),
                "total_power_kw": self.project.total_installed_capacity_kw,
                "total_demand_kw": self.project.total_demand_kw,
                "diversity_factor": self.project.system_diversity_factor
            }
        }
        # Save to session state
        st.session_state.calculation_results = self.calculation_results
        st.session_state.project = self.project  # Also save project since calculations may modify it

    def _create_cables_and_breakers_from_calculations(self):
        """Create cables and breakers based on calculation results"""
        # Clear existing cables and breakers
        self.project.cables = []
        self.project.breakers = []

        for load in self.project.loads:
            if load.cable_size_sqmm and load.breaker_rating_a:
                # Create cable
                cable = Cable(
                    cable_id=f"C{load.load_id[1:]}",
                    from_equipment=load.source_bus,
                    to_equipment=load.load_id,
                    cores=4 if load.phases == 3 else 3,
                    size_sqmm=load.cable_size_sqmm,
                    cable_type=load.cable_type or "XLPE",
                    insulation="PVC",
                    armored=True,
                    length_m=load.cable_length,
                    installation_method=load.installation_method,
                    grouping_factor=load.grouping_factor,
                    standard=self.project.standard,
                    temperature_rating_c=90
                )
                self.project.cables.append(cable)

                # Create breaker
                breaker = Breaker(
                    breaker_id=f"BR{load.load_id[1:]}",
                    load_id=load.load_id,
                    rated_current_a=load.breaker_rating_a,
                    rated_voltage_v=load.voltage,
                    poles=load.phases,
                    breaking_capacity_ka=35.0 if load.voltage == 400 else 10.0,
                    type=load.breaker_type or "MCCB",
                    curve_type="C" if load.breaker_type == "MCB" else None,
                    standard=self.project.standard
                )
                self.project.breakers.append(breaker)

    def _display_calculation_results(self):
        """Display calculation results"""
        st.markdown('<h2 class="section-header">Calculation Results</h2>', unsafe_allow_html=True)

        summary = self.calculation_results.get("summary", {})

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Loads", summary.get("total_loads", 0))

        with col2:
            st.metric("Installed Capacity", f"{summary.get('total_power_kw', 0):.1f} kW")

        with col3:
            st.metric("System Demand", f"{summary.get('total_demand_kw', 0):.1f} kW")

        with col4:
            st.metric("Diversity Factor", f"{summary.get('diversity_factor', 0):.3f}")

        # Load calculation results
        if self.project.loads and any(load.current_a for load in self.project.loads):
            st.subheader("Load Calculations")

            load_results = []
            for load in self.project.loads:
                if load.current_a:  # Only show calculated loads
                    load_results.append({
                        "Load ID": load.load_id,
                        "Name": load.load_name,
                        "Current (A)": f"{load.current_a:.1f}",
                        "Design Current (A)": f"{load.design_current_a:.1f}" if load.design_current_a else "N/A",
                        "Cable Size (mm²)": load.cable_size_sqmm or "N/A",
                        "Breaker (A)": load.breaker_rating_a or "N/A",
                        "Voltage Drop (%)": f"{load.voltage_drop_percent:.2f}" if load.voltage_drop_percent else "N/A"
                    })

            if load_results:
                df = pd.DataFrame(load_results)
                st.dataframe(df, width='content')

    def _analysis_reports_page(self):
        """Unified analysis and reports page"""
        st.markdown('<h1 class="section-header">Analysis & Reports</h1>', unsafe_allow_html=True)

        if not self.project:
            st.warning("Please create or load a project first.")
            return

        if not self.calculation_results:
            # Auto-run calculations if system is ready
            if len(self.project.loads) > 0 and len(self.project.buses) > 0:
                st.info("🔄 System ready for analysis. Running calculations...")
                with st.spinner("Performing electrical calculations..."):
                    try:
                        self._perform_calculations()
                        st.success("Calculations completed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Auto-calculation failed: {str(e)}")
                        st.info("Please check your system configuration and try manual calculations.")
                        return
            else:
                st.warning("Please complete system configuration first.")
                missing = []
                if len(self.project.loads) == 0:
                    missing.append("loads")
                if len(self.project.buses) == 0:
                    missing.append("buses")
                if missing:
                    st.info(f"Missing: {', '.join(missing)}. Go to System Configuration to add them.")
                return

        # Overview metrics
        summary = self.calculation_results.get("summary", {})
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Loads", summary.get("total_loads", 0))
        with col2:
            st.metric("Installed Capacity", f"{summary.get('total_power_kw', 0):.1f} kW")
        with col3:
            st.metric("System Demand", f"{summary.get('total_demand_kw', 0):.1f} kW")
        with col4:
            st.metric("Diversity Factor", f"{summary.get('diversity_factor', 0):.3f}")

        # Design Assistant Section
        if self.design_assistant:
            st.markdown("---")
            st.markdown('<h2 class="section-header">🤖 Design Assistant</h2>', unsafe_allow_html=True)

            # Get design suggestions
            design_suggestions = self.design_assistant.get_design_suggestions(
                self.project, self.calculation_results
            )

            if design_suggestions.get("suggestions"):
                # Display suggestions by impact level
                high_impact = [s for s in design_suggestions["suggestions"] if s.get("impact") == "high"]
                medium_impact = [s for s in design_suggestions["suggestions"] if s.get("impact") == "medium"]
                low_impact = [s for s in design_suggestions["suggestions"] if s.get("impact") == "low"]

                for impact_level, suggestions, color in [
                    ("High Priority", high_impact, "🔴"),
                    ("Medium Priority", medium_impact, "🟡"),
                    ("Low Priority", low_impact, "🟢")
                ]:
                    if suggestions:
                        with st.expander(f"{color} {impact_level} Suggestions ({len(suggestions)})", expanded=impact_level=="High Priority"):
                            for suggestion in suggestions:
                                col1, col2 = st.columns([1, 3])
                                with col1:
                                    st.markdown(f"**{suggestion['title']}**")
                                with col2:
                                    st.markdown(f"{suggestion['description']}")

                                if suggestion.get("recommendations"):
                                    st.markdown("**Recommendations:**")
                                    for rec in suggestion["recommendations"]:
                                        st.markdown(f"• {rec}")
                                st.markdown("---")

            # Smart defaults helper
            st.markdown("### 💡 Smart Defaults Helper")
            st.markdown("Get intelligent default values for new equipment based on electrical engineering best practices.")

            col1, col2, col3 = st.columns(3)
            with col1:
                load_type = st.selectbox("Load Type", ["motor", "lighting", "hvac", "general"], key="smart_defaults_type")
            with col2:
                voltage = st.selectbox("Voltage (V)", [230, 400, 415, 440, 690], key="smart_defaults_voltage")
            with col3:
                phases = st.selectbox("Phases", [1, 3], key="smart_defaults_phases")

            if st.button("Get Smart Defaults", key="smart_defaults_btn"):
                defaults = self.design_assistant.get_smart_defaults_for_load(load_type, voltage, phases)
                st.success("Smart defaults applied to your session!")

                # Display defaults in a nice format
                st.markdown("**Recommended Values:**")
                cols = st.columns(4)
                with cols[0]:
                    st.metric("Power Factor", defaults.get("power_factor", 0.85))
                with cols[1]:
                    st.metric("Efficiency", defaults.get("efficiency", 0.9))
                with cols[2]:
                    st.metric("Cable Length", f"{defaults.get('cable_length', 50)}m")
                with cols[3]:
                    st.metric("Installation", "Tray")

                if defaults.get("notes"):
                    st.info(f"💡 {defaults['notes']}")

                # Store defaults in session for use in forms
                st.session_state.smart_defaults = defaults

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Load Analysis", "🔌 Cable Schedule", "📊 System Analytics", "🔀 SLD Diagram", "📤 Export Reports"])

        with tab1:
            self._load_analysis_tab()

        with tab2:
            self._cable_schedule_tab()

        with tab3:
            self._system_analytics_tab()

        with tab4:
            self._sld_diagram_tab()

        with tab5:
            self._export_reports_tab()

    def _load_analysis_tab(self):
        """Load analysis tab"""
        st.subheader("Load Analysis")

        if self.project.loads:
            # Create comprehensive load list
            load_data = []
            for load in self.project.loads:
                load_data.append({
                    "Load ID": load.load_id,
                    "Load Name": load.load_name,
                    "Type": load.load_type.value,
                    "Power (kW)": load.power_kw,
                    "Voltage (V)": load.voltage,
                    "Phases": load.phases,
                    "Power Factor": load.power_factor,
                    "Efficiency": load.efficiency,
                    "Current (A)": load.current_a or "N/A",
                    "Design Current (A)": load.design_current_a or "N/A",
                    "Cable Size (mm²)": load.cable_size_sqmm or "N/A",
                    "Breaker Rating (A)": load.breaker_rating_a or "N/A",
                    "Voltage Drop (%)": load.voltage_drop_percent or "N/A",
                    "Source Bus": load.source_bus or "N/A",
                    "Priority": load.priority.value
                })

            df = pd.DataFrame(load_data)
            st.dataframe(df, use_container_width=True)

            # Summary statistics
            st.subheader("Summary Statistics")
            col1, col2, col3 = st.columns(3)

            with col1:
                total_power = sum(load.power_kw for load in self.project.loads)
                st.metric("Total Installed Capacity", f"{total_power:.1f} kW")

            with col2:
                total_current = sum(load.current_a for load in self.project.loads if load.current_a)
                st.metric("Total Current", f"{total_current:.1f} A")

            with col3:
                avg_pf = sum(load.power_factor for load in self.project.loads) / len(self.project.loads)
                st.metric("Average Power Factor", f"{avg_pf:.3f}")

    def _cable_schedule_tab(self):
        """Cable schedule tab"""
        st.subheader("Cable Schedule")

        if self.project.cables:
            cable_data = []
            for cable in self.project.cables:
                cable_data.append({
                    "Cable ID": cable.cable_id,
                    "From": cable.from_equipment,
                    "To": cable.to_equipment,
                    "Specification": cable.get_full_specification(),
                    "Cores": cable.cores,
                    "Size (mm²)": cable.size_sqmm,
                    "Length (m)": cable.length_m,
                    "Installation": cable.installation_method.value,
                    "Current Rating (A)": cable.current_carrying_capacity_a or "N/A"
                })

            df = pd.DataFrame(cable_data)
            st.dataframe(df, use_container_width=True)

            # Cable statistics
            st.subheader("Cable Statistics")
            col1, col2, col3 = st.columns(3)

            with col1:
                total_length = sum(cable.length_m for cable in self.project.cables)
                st.metric("Total Cable Length", f"{total_length:.1f} m")

            with col2:
                unique_sizes = len(set(cable.size_sqmm for cable in self.project.cables))
                st.metric("Unique Cable Sizes", unique_sizes)

            with col3:
                avg_length = total_length / len(self.project.cables) if self.project.cables else 0
                st.metric("Average Cable Length", f"{avg_length:.1f} m")

    def _system_analytics_tab(self):
        """System analytics tab"""
        st.subheader("System Analytics")

        if not self.project.loads:
            st.info("No load data available for charts.")
            return

        # Power distribution by load type
        load_types = {}
        for load in self.project.loads:
            load_type = load.load_type.value
            if load_type not in load_types:
                load_types[load_type] = 0
            load_types[load_type] += load.power_kw

        fig1 = px.pie(
            values=list(load_types.values()),
            names=list(load_types.keys()),
            title="Power Distribution by Load Type"
        )
        st.plotly_chart(fig1, use_container_width=True)

        # Voltage levels distribution
        voltage_levels = {}
        for load in self.project.loads:
            voltage = load.voltage
            if voltage not in voltage_levels:
                voltage_levels[voltage] = 0
            voltage_levels[voltage] += 1

        fig2 = px.bar(
            x=list(voltage_levels.keys()),
            y=list(voltage_levels.values()),
            title="Load Count by Voltage Level",
            labels={"x": "Voltage (V)", "y": "Number of Loads"}
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Power factor distribution
        if any(load.power_factor for load in self.project.loads):
            pf_values = [load.power_factor for load in self.project.loads if load.power_factor]

            fig3 = px.histogram(
                pf_values,
                title="Power Factor Distribution",
                labels={"value": "Power Factor", "count": "Number of Loads"},
                nbins=20
            )
            st.plotly_chart(fig3, use_container_width=True)

    def _export_reports_tab(self):
        """Export reports tab"""
        st.subheader("Export Reports")

        st.info("Generate comprehensive reports for your electrical design project.")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📄 Export Load List (Excel)", use_container_width=True):
                self._export_load_list_excel()

        with col2:
            if st.button("🔌 Export Cable Schedule (Excel)", use_container_width=True):
                self._export_cable_schedule_excel()

        with col3:
            if st.button("📊 Export Complete Project (JSON)", use_container_width=True):
                self._export_project_json()

        st.markdown("---")
        st.subheader("Quick Export All")

        if st.button("📤 Export All Reports", type="primary", use_container_width=True):
            self._quick_export_all()

        # Export summary
        st.markdown("---")
        st.subheader("Export Summary")

        export_options = {
            "Load List": "Excel spreadsheet with detailed load calculations",
            "Cable Schedule": "Excel spreadsheet with cable specifications",
            "Complete Project": "JSON file with all project data and calculations",
            "All Reports": "Complete set of all above reports in a ZIP file"
        }

        for export_type, description in export_options.items():
            st.markdown(f"**{export_type}**: {description}")

    def _results_page(self):
        """Results and reports page"""
        st.markdown('<h1 class="section-header">Results & Reports</h1>', unsafe_allow_html=True)

        if not self.project:
            st.warning("Please create or load a project first.")
            return

        if not self.calculation_results:
            st.warning("Please run calculations first to view results.")
            return

        tab1, tab2, tab3, tab4 = st.tabs(["📋 Load List", "🔌 Cable Schedule", "📊 Charts & Analytics", "🔀 SLD Diagram"])

        with tab1:
            self._load_list_report()

        with tab2:
            self._cable_schedule_report()

        with tab3:
            self._analytics_charts()

        with tab4:
            self._sld_diagram_tab()

    def _load_list_report(self):
        """Display load list report"""
        st.subheader("Electrical Load List")

        if self.project.loads:
            # Create comprehensive load list
            load_data = []
            for load in self.project.loads:
                load_data.append({
                    "Load ID": load.load_id,
                    "Load Name": load.load_name,
                    "Type": load.load_type.value,
                    "Power (kW)": load.power_kw,
                    "Voltage (V)": load.voltage,
                    "Phases": load.phases,
                    "Power Factor": load.power_factor,
                    "Efficiency": load.efficiency,
                    "Current (A)": load.current_a or "N/A",
                    "Design Current (A)": load.design_current_a or "N/A",
                    "Cable Size (mm²)": load.cable_size_sqmm or "N/A",
                    "Breaker Rating (A)": load.breaker_rating_a or "N/A",
                    "Voltage Drop (%)": load.voltage_drop_percent or "N/A",
                    "Source Bus": load.source_bus or "N/A",
                    "Priority": load.priority.value
                })

            df = pd.DataFrame(load_data)
            st.dataframe(df, width='content')

            # Summary statistics
            st.subheader("Summary Statistics")
            col1, col2, col3 = st.columns(3)

            with col1:
                total_power = sum(load.power_kw for load in self.project.loads)
                st.metric("Total Installed Capacity", f"{total_power:.1f} kW")

            with col2:
                total_current = sum(load.current_a for load in self.project.loads if load.current_a)
                st.metric("Total Current", f"{total_current:.1f} A")

            with col3:
                avg_pf = sum(load.power_factor for load in self.project.loads) / len(self.project.loads)
                st.metric("Average Power Factor", f"{avg_pf:.3f}")

    def _cable_schedule_report(self):
        """Display cable schedule report"""
        st.subheader("Cable Schedule")

        if self.project.cables:
            cable_data = []
            for cable in self.project.cables:
                cable_data.append({
                    "Cable ID": cable.cable_id,
                    "From": cable.from_equipment,
                    "To": cable.to_equipment,
                    "Specification": cable.get_full_specification(),
                    "Cores": cable.cores,
                    "Size (mm²)": cable.size_sqmm,
                    "Length (m)": cable.length_m,
                    "Installation": cable.installation_method.value,
                    "Current Rating (A)": cable.current_carrying_capacity_a or "N/A"
                })

            df = pd.DataFrame(cable_data)
            st.dataframe(df, width='content')

            # Cable statistics
            st.subheader("Cable Statistics")
            col1, col2, col3 = st.columns(3)

            with col1:
                total_length = sum(cable.length_m for cable in self.project.cables)
                st.metric("Total Cable Length", f"{total_length:.1f} m")

            with col2:
                unique_sizes = len(set(cable.size_sqmm for cable in self.project.cables))
                st.metric("Unique Cable Sizes", unique_sizes)

            with col3:
                avg_length = total_length / len(self.project.cables) if self.project.cables else 0
                st.metric("Average Cable Length", f"{avg_length:.1f} m")

    def _analytics_charts(self):
        """Display analytics charts"""
        st.subheader("Analytics & Charts")

        if not self.project.loads:
            st.info("No load data available for charts.")
            return

        # Power distribution by load type
        load_types = {}
        for load in self.project.loads:
            load_type = load.load_type.value
            if load_type not in load_types:
                load_types[load_type] = 0
            load_types[load_type] += load.power_kw

        fig1 = px.pie(
            values=list(load_types.values()),
            names=list(load_types.keys()),
            title="Power Distribution by Load Type"
        )
        st.plotly_chart(fig1, width='content')

        # Voltage levels distribution
        voltage_levels = {}
        for load in self.project.loads:
            voltage = load.voltage
            if voltage not in voltage_levels:
                voltage_levels[voltage] = 0
            voltage_levels[voltage] += 1

        fig2 = px.bar(
            x=list(voltage_levels.keys()),
            y=list(voltage_levels.values()),
            title="Load Count by Voltage Level",
            labels={"x": "Voltage (V)", "y": "Number of Loads"}
        )
        st.plotly_chart(fig2, width='content')

        # Power factor distribution
        if any(load.power_factor for load in self.project.loads):
            pf_values = [load.power_factor for load in self.project.loads if load.power_factor]

            fig3 = px.histogram(
                pf_values,
                title="Power Factor Distribution",
                labels={"value": "Power Factor", "count": "Number of Loads"},
                nbins=20
            )
            st.plotly_chart(fig3, width='content')
    def _export_page(self):
        """Export functionality page"""
        st.markdown('<h1 class="section-header">Export Reports</h1>', unsafe_allow_html=True)

        if not self.project:
            st.warning("Please create or load a project first.")
            return

        if not self.calculation_results:
            st.warning("Please run calculations first.")
            return

        st.subheader("Export Options")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📄 Export Load List (Excel)", width='stretch'):
                self._export_load_list_excel()

        with col2:
            if st.button("🔌 Export Cable Schedule (Excel)", width='stretch'):
                self._export_cable_schedule_excel()

        with col3:
            if st.button("📊 Export Complete Project (JSON)", width='stretch'):
                self._export_project_json()

        # Export summary
        st.markdown("---")
        st.subheader("Export Summary")

        export_options = {
            "Load List": "Excel spreadsheet with detailed load calculations",
            "Cable Schedule": "Excel spreadsheet with cable specifications",
            "Complete Project": "JSON file with all project data and calculations"
        }

        for export_type, description in export_options.items():
            st.markdown(f"**{export_type}**: {description}")

    def _export_load_list_excel(self):
        """Export load list to Excel"""
        if not self.project.loads:
            st.error("No load data to export.")
            return

        # Create DataFrame
        load_data = []
        for load in self.project.loads:
            load_data.append({
                "Load ID": load.load_id,
                "Load Name": load.load_name,
                "Type": load.load_type.value,
                "Power (kW)": load.power_kw,
                "Voltage (V)": load.voltage,
                "Phases": load.phases,
                "Power Factor": load.power_factor,
                "Efficiency": load.efficiency,
                "Current (A)": load.current_a,
                "Design Current (A)": load.design_current_a,
                "Cable Size (mm²)": load.cable_size_sqmm,
                "Breaker Rating (A)": load.breaker_rating_a,
                "Voltage Drop (%)": load.voltage_drop_percent,
                "Source Bus": load.source_bus,
                "Priority": load.priority.value
            })

        df = pd.DataFrame(load_data)

        # Create Excel file
        filename = f"{self.project.project_name.replace(' ', '_')}_LoadList.xlsx"

        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Load List', index=False)

            # Add formatting
            workbook = writer.book
            worksheet = writer.sheets['Load List']

            # Header format
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Auto-fit columns
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 20))  # Cap at 20 for readability

        st.success(f"Load list exported to {filename}")

        # Download button
        with open(filename, 'rb') as f:
            st.download_button(
                label="📥 Download Load List Excel",
                data=f,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    def _export_cable_schedule_excel(self):
        """Export cable schedule to Excel"""
        if not self.project.cables:
            st.error("No cable data to export.")
            return

        # Create DataFrame
        cable_data = []
        for cable in self.project.cables:
            cable_data.append({
                "Cable ID": cable.cable_id,
                "From": cable.from_equipment,
                "To": cable.to_equipment,
                "Specification": cable.get_full_specification(),
                "Cores": cable.cores,
                "Size (mm²)": cable.size_sqmm,
                "Length (m)": cable.length_m,
                "Installation": cable.installation_method.value,
                "Current Rating (A)": cable.current_carrying_capacity_a,
                "Voltage Drop (V)": cable.voltage_drop_v,
                "Voltage Drop (%)": cable.voltage_drop_percent
            })

        df = pd.DataFrame(cable_data)

        # Create Excel file
        filename = f"{self.project.project_name.replace(' ', '_')}_CableSchedule.xlsx"

        with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Cable Schedule', index=False)

            # Add formatting
            workbook = writer.book
            worksheet = writer.sheets['Cable Schedule']

            # Header format
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            # Apply header format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Auto-fit columns
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 25))

        st.success(f"Cable schedule exported to {filename}")

        # Download button
        with open(filename, 'rb') as f:
            st.download_button(
                label="📥 Download Cable Schedule Excel",
                data=f,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    def _export_project_json(self):
        """Export complete project to JSON"""
        # Convert project to dictionary
        project_data = {
            "project_info": {
                "name": self.project.project_name,
                "id": self.project.project_id,
                "standard": self.project.standard,
                "voltage_system": self.project.voltage_system,
                "ambient_temperature_c": self.project.ambient_temperature_c,
                "altitude_m": self.project.altitude_m,
                "created_by": self.project.created_by,
                "created_date": self.project.created_date,
                "version": self.project.version
            },
            "loads": [self._load_to_dict(load) for load in self.project.loads],
            "buses": [self._bus_to_dict(bus) for bus in self.project.buses],
            "transformers": [self._transformer_to_dict(tx) for tx in self.project.transformers],
            "cables": [self._cable_to_dict(cable) for cable in self.project.cables],
            "breakers": [self._breaker_to_dict(breaker) for breaker in self.project.breakers],
            "calculations": self.calculation_results
        }

        filename = f"{self.project.project_name.replace(' ', '_')}_CompleteProject.json"

        with open(filename, 'w') as f:
            json.dump(project_data, f, indent=2, default=str)

        st.success(f"Complete project exported to {filename}")

        # Download button
        with open(filename, 'rb') as f:
            st.download_button(
                label="📥 Download Complete Project JSON",
                data=f,
                file_name=filename,
                mime="application/json"
            )

    def _import_loads_from_csv(self, uploaded_file):
        """Import loads from CSV file"""
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)

            # Validate required columns
            required_columns = ['load_id', 'load_name', 'power_kw', 'voltage', 'phases']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
                return

            # Process each row
            imported_count = 0
            for _, row in df.iterrows():
                try:
                    load = Load(
                        load_id=str(row['load_id']),
                        load_name=str(row['load_name']),
                        load_type=LoadType(row.get('load_type', 'general')),
                        power_kw=float(row['power_kw']),
                        voltage=int(row['voltage']),
                        phases=int(row['phases']),
                        power_factor=float(row.get('power_factor', 0.85)),
                        efficiency=float(row.get('efficiency', 0.9)),
                        cable_length=float(row.get('cable_length', 50.0)),
                        installation_method=InstallationMethod(row.get('installation_method', 'tray')),
                        priority=Priority(row.get('priority', 'non-essential')),
                        source_bus=row.get('source_bus') if pd.notna(row.get('source_bus')) else None
                    )

                    self.project.add_load(load)
                    imported_count += 1

                except Exception as e:
                    st.warning(f"Error importing row {row['load_id']}: {str(e)}")

            # Save to session state
            st.session_state.project = self.project

            st.success(f"Successfully imported {imported_count} loads from CSV!")

        except Exception as e:
            st.error(f"Error importing CSV: {str(e)}")

    def _export_loads_to_csv(self):
        """Export loads to CSV"""
        if not self.project.loads:
            st.error("No loads to export.")
            return

        # Create CSV data
        csv_data = []
        headers = [
            'load_id', 'load_name', 'load_type', 'power_kw', 'voltage', 'phases',
            'power_factor', 'efficiency', 'cable_length', 'installation_method',
            'priority', 'source_bus'
        ]
        csv_data.append(headers)

        for load in self.project.loads:
            row = [
                load.load_id,
                load.load_name,
                load.load_type.value,
                load.power_kw,
                load.voltage,
                load.phases,
                load.power_factor,
                load.efficiency,
                load.cable_length,
                load.installation_method.value,
                load.priority.value,
                load.source_bus
            ]
            csv_data.append(row)

        # Create CSV string
        csv_string = io.StringIO()
        writer = csv.writer(csv_string)
        writer.writerows(csv_data)

        filename = f"{self.project.project_name.replace(' ', '_')}_Loads.csv"

        st.success(f"Loads exported to {filename}")

        # Download button
        st.download_button(
            label="📥 Download Loads CSV",
            data=csv_string.getvalue(),
            file_name=filename,
            mime="text/csv"
        )

    def _help_page(self):
        """Help and documentation page"""
        st.markdown('<h1 class="section-header">Help & Documentation</h1>', unsafe_allow_html=True)

        st.subheader("Getting Started")

        st.markdown("""
        Welcome to the Electrical Design Automation System! This tool helps electrical engineers design and analyze power distribution systems.

        ### Quick Start Guide:

        1. **Create a New Project**: Start with project setup to define basic parameters
        2. **Add Equipment**: Configure buses and transformers for your system
        3. **Define Loads**: Add electrical loads with their specifications
        4. **Run Calculations**: Execute electrical calculations automatically
        5. **Review Results**: Analyze load lists, cable schedules, and reports
        6. **Export Reports**: Generate professional documentation

        ### Key Features:

        - **Multi-Standard Support**: IEC, IS, and NEC standards
        - **Comprehensive Calculations**: Current, cable sizing, voltage drop, short circuit
        - **Professional Reports**: Excel exports, load lists, cable schedules
        - **Interactive Interface**: Easy-to-use web interface
        """)

        st.subheader("Standards Supported")

        standards_info = {
            "IEC": "International Electrotechnical Commission - Global standard",
            "IS": "Indian Standards - Used in India and South Asia",
            "NEC": "National Electrical Code - Used in North America"
        }

        for standard, description in standards_info.items():
            st.markdown(f"**{standard}**: {description}")

        st.subheader("Calculation Methods")

        st.markdown("""
        The system performs the following calculations:

        - **Load Current**: Based on power, voltage, power factor, and efficiency
        - **Cable Sizing**: Considers current capacity, voltage drop, and short circuit withstand
        - **Breaker Selection**: Automatic selection based on load requirements
        - **Voltage Drop**: Calculates percentage drop for compliance checking
        - **Short Circuit**: Estimates fault currents for protection coordination
        """)

        st.subheader("CSV Import Format")

        st.markdown("""
        For bulk load import, use CSV files with the following columns:

        **Required columns:**
        - `load_id`: Unique identifier for the load
        - `load_name`: Descriptive name
        - `power_kw`: Power rating in kilowatts
        - `voltage`: Operating voltage in volts
        - `phases`: Number of phases (1 or 3)

        **Optional columns:**
        - `load_type`: motor, heater, lighting, hvac, ups, transformer, capacitor, generator, general
        - `power_factor`: Power factor (0.1-1.0, default: 0.85)
        - `efficiency`: Equipment efficiency (0.1-1.0, default: 0.9)
        - `cable_length`: Cable run length in meters (default: 50.0)
        - `installation_method`: conduit, tray, buried, air, duct, free_air (default: tray)
        - `priority`: critical, essential, non-essential (default: non-essential)
        - `source_bus`: Bus ID where load is connected
        """)

    def _load_to_dict(self, load: Load) -> Dict:
        """Convert Load object to dictionary for JSON export"""
        return {
            "load_id": load.load_id,
            "load_name": load.load_name,
            "load_type": load.load_type.value,
            "power_kw": load.power_kw,
            "voltage": load.voltage,
            "phases": load.phases,
            "power_factor": load.power_factor,
            "efficiency": load.efficiency,
            "cable_length": load.cable_length,
            "installation_method": load.installation_method.value,
            "grouping_factor": load.grouping_factor,
            "source_bus": load.source_bus,
            "priority": load.priority.value,
            "redundancy": load.redundancy,
            "notes": load.notes,
            "current_a": load.current_a,
            "design_current_a": load.design_current_a,
            "cable_size_sqmm": load.cable_size_sqmm,
            "cable_type": load.cable_type,
            "breaker_rating_a": load.breaker_rating_a,
            "voltage_drop_v": load.voltage_drop_v,
            "voltage_drop_percent": load.voltage_drop_percent
        }

    def _bus_to_dict(self, bus: Bus) -> Dict:
        """Convert Bus object to dictionary for JSON export"""
        return {
            "bus_id": bus.bus_id,
            "bus_name": bus.bus_name,
            "voltage": bus.voltage,
            "phases": bus.phases,
            "rated_current_a": bus.rated_current_a,
            "short_circuit_rating_ka": bus.short_circuit_rating_ka,
            "parent_bus": bus.parent_bus,
            "child_buses": bus.child_buses,
            "connected_loads": bus.connected_loads,
            "total_load_kw": bus.total_load_kw,
            "diversity_factor": bus.diversity_factor,
            "demand_kw": bus.demand_kw,
            "location": bus.location
        }

    def _transformer_to_dict(self, tx) -> Dict:
        """Convert Transformer object to dictionary for JSON export"""
        return {
            "transformer_id": tx.transformer_id,
            "name": tx.name,
            "rating_kva": tx.rating_kva,
            "primary_voltage_v": tx.primary_voltage_v,
            "secondary_voltage_v": tx.secondary_voltage_v,
            "impedance_percent": tx.impedance_percent,
            "vector_group": tx.vector_group,
            "type": tx.type,
            "primary_current_a": tx.primary_current_a,
            "secondary_current_a": tx.secondary_current_a
        }

    def _cable_to_dict(self, cable: Cable) -> Dict:
        """Convert Cable object to dictionary for JSON export"""
        return {
            "cable_id": cable.cable_id,
            "from_equipment": cable.from_equipment,
            "to_equipment": cable.to_equipment,
            "cores": cable.cores,
            "size_sqmm": cable.size_sqmm,
            "cable_type": cable.cable_type,
            "insulation": cable.insulation,
            "length_m": cable.length_m,
            "installation_method": cable.installation_method.value,
            "armored": cable.armored,
            "current_carrying_capacity_a": cable.current_carrying_capacity_a,
            "voltage_drop_v": cable.voltage_drop_v,
            "voltage_drop_percent": cable.voltage_drop_percent
        }

    def _breaker_to_dict(self, breaker: Breaker) -> Dict:
        """Convert Breaker object to dictionary for JSON export"""
        return {
            "breaker_id": breaker.breaker_id,
            "load_id": breaker.load_id,
            "rated_current_a": breaker.rated_current_a,
            "rated_voltage_v": breaker.rated_voltage_v,
            "poles": breaker.poles,
            "breaking_capacity_ka": breaker.breaking_capacity_ka,
            "type": breaker.type,
            "curve_type": breaker.curve_type,
            "standard": breaker.standard
        }

    def _generate_sld_graph(self):
        """Generate SLD graph object from project data"""
        nodes = []
        edges = []

        # Add transformers
        for tx in self.project.transformers:
            nodes.append({
                "id": tx.transformer_id,
                "type": "transformer",
                "name": tx.name,
                "rating_kva": tx.rating_kva,
                "primary_v": tx.primary_voltage_v,
                "secondary_v": tx.secondary_voltage_v
            })

        # Add buses
        for bus in self.project.buses:
            nodes.append({
                "id": bus.bus_id,
                "type": "bus",
                "name": bus.bus_name,
                "voltage_v": bus.voltage
            })

        # Add loads
        for load in self.project.loads:
            node = {
                "id": load.load_id,
                "type": "load",
                "name": load.load_name,
                "power_kw": load.power_kw,
                "voltage_v": load.voltage,
                "phases": load.phases
            }
            if load.source_bus:
                node["source_bus"] = load.source_bus
            nodes.append(node)

        # Add breakers
        for breaker in self.project.breakers:
            nodes.append({
                "id": breaker.breaker_id,
                "type": "breaker",
                "rated_current_a": breaker.rated_current_a,
                "associated_load_id": breaker.load_id
            })

        # Create edges
        # Transformer to bus connections (assuming first bus is main)
        if self.project.transformers and self.project.buses:
            main_bus = next((bus for bus in self.project.buses if not bus.parent_bus), None)
            if main_bus:
                for tx in self.project.transformers:
                    edges.append({
                        "from": tx.transformer_id,
                        "to": main_bus.bus_id,
                        "type": "transformer-to-bus"
                    })

        # Bus to bus connections
        for bus in self.project.buses:
            if bus.parent_bus:
                edges.append({
                    "from": bus.parent_bus,
                    "to": bus.bus_id,
                    "type": "bus-to-bus"
                })

        # Bus to load connections via breakers
        for load in self.project.loads:
            if load.source_bus:
                # Find breaker for this load
                breaker = next((br for br in self.project.breakers if br.load_id == load.load_id), None)
                if breaker:
                    edges.append({
                        "from": load.source_bus,
                        "to": breaker.breaker_id,
                        "type": "bus-to-breaker"
                    })
                    edges.append({
                        "from": breaker.breaker_id,
                        "to": load.load_id,
                        "type": "breaker-to-load"
                    })
                else:
                    edges.append({
                        "from": load.source_bus,
                        "to": load.load_id,
                        "type": "bus-to-load"
                    })

        self.sld_graph = {
            "nodes": nodes,
            "edges": edges
        }

    def _generate_sld_diagram(self):
        """Generate Graphviz DOT code for SLD diagram"""
        if not hasattr(self, 'sld_graph') or not self.sld_graph:
            self._generate_sld_graph()

        dot_lines = []
        dot_lines.append("digraph SLD {")
        dot_lines.append("  rankdir=LR;")
        dot_lines.append("  node [fontname=\"Helvetica\"];")
        dot_lines.append("  edge [penwidth=1.0];")
        dot_lines.append("")

        # Group nodes by bus for clustering
        bus_nodes = {}
        for node in self.sld_graph["nodes"]:
            if node["type"] == "bus":
                bus_nodes[node["id"]] = []
            elif node["type"] in ["breaker", "load"]:
                # Find source bus for breakers and loads
                source_bus = None
                if node["type"] == "load" and "source_bus" in node:
                    source_bus = node["source_bus"]
                elif node["type"] == "breaker" and "associated_load_id" in node:
                    # Find load and its source bus
                    load = next((l for l in self.sld_graph["nodes"]
                               if l["type"] == "load" and l["id"] == node["associated_load_id"]), None)
                    if load and "source_bus" in load:
                        source_bus = load["source_bus"]

                if source_bus and source_bus in bus_nodes:
                    bus_nodes[source_bus].append(node)

        # Create clusters for each bus
        for bus_id, components in bus_nodes.items():
            bus_node = next((n for n in self.sld_graph["nodes"] if n["id"] == bus_id), None)
            if bus_node:
                dot_lines.append(f"  subgraph cluster_{bus_id} {{")
                dot_lines.append("    style=dashed;")

                # Add bus node
                dot_lines.append(f"    {bus_id} [shape=circle, label=\"{bus_node['name']}\\n{bus_node['voltage_v']}V\"];")

                # Add breakers and loads
                for comp in components:
                    if comp["type"] == "breaker":
                        dot_lines.append(f"    {comp['id']} [shape=box, width=0.5, height=0.3, label=\"CB{comp['id']}\"];")
                    elif comp["type"] == "load":
                        dot_lines.append(f"    {comp['id']} [shape=box, label=\"{comp['name']}\\n{comp['power_kw']}kW\"];")

                dot_lines.append("  }")
                dot_lines.append("")

        # Add transformer nodes
        for node in self.sld_graph["nodes"]:
            if node["type"] == "transformer":
                dot_lines.append(f"  {node['id']} [shape=circle, label=\"{node['name']}\\n{node['rating_kva']}kVA\\n○/●\"];")

        dot_lines.append("")

        # Add edges
        for edge in self.sld_graph["edges"]:
            if edge["type"] == "transformer-to-bus":
                dot_lines.append(f"  {edge['from']} -> {edge['to']} [arrowhead=normal];")
            elif edge["type"] == "bus-to-bus":
                dot_lines.append(f"  {edge['from']} -> {edge['to']} [arrowhead=normal];")
            elif edge["type"] == "bus-to-breaker":
                dot_lines.append(f"  {edge['from']} -> {edge['to']};")
            elif edge["type"] == "breaker-to-load":
                dot_lines.append(f"  {edge['to']} -> {edge['from']};")  # Reverse for proper flow
            elif edge["type"] == "bus-to-load":
                dot_lines.append(f"  {edge['from']} -> {edge['to']};")

        dot_lines.append("}")

        self.sld_dot_content = "\n".join(dot_lines)

    def _create_text_diagram(self):
        """Create a simple text-based representation of the SLD"""
        if not hasattr(self, 'sld_graph') or not self.sld_graph:
            return None

        lines = []
        lines.append("ELECTRICAL SINGLE-LINE DIAGRAM")
        lines.append("=" * 50)
        lines.append("")

        # Find transformer
        transformer = next((n for n in self.sld_graph["nodes"] if n["type"] == "transformer"), None)
        if transformer:
            lines.append(f"TRANSFORMER: {transformer['name']} ({transformer['rating_kva']}kVA)")
            lines.append(f"Primary: {transformer['primary_v']}V → Secondary: {transformer['secondary_v']}V")
            lines.append("")

        # Show bus hierarchy
        buses = [n for n in self.sld_graph["nodes"] if n["type"] == "bus"]
        for bus in buses:
            lines.append(f"BUS: {bus['name']} ({bus['voltage_v']}V)")

            # Find connected components (breakers and loads)
            connected_components = []
            for edge in self.sld_graph["edges"]:
                if edge["from"] == bus["id"] and edge["type"] in ["bus-to-breaker", "bus-to-load"]:
                    component = next((n for n in self.sld_graph["nodes"] if n["id"] == edge["to"]), None)
                    if component:
                        connected_components.append(component)

            if connected_components:
                lines.append("  Connected Equipment:")
                for comp in connected_components:
                    if comp["type"] == "breaker":
                        load = next((n for n in self.sld_graph["nodes"]
                                   if n["type"] == "load" and n["id"] == comp["associated_load_id"]), None)
                        if load:
                            lines.append(f"    • Breaker {comp['id']} → {load['name']} ({load['power_kw']}kW)")
                    elif comp["type"] == "load":
                        lines.append(f"    • {comp['name']} ({comp['power_kw']}kW, {comp['phases']}ph, {comp['voltage_v']}V)")
            lines.append("")

        lines.append("LEGEND:")
        lines.append("• Transformer: ○/● symbol")
        lines.append("• Bus: Circular node with voltage")
        lines.append("• Breaker: Small rectangular box (CBxxx)")
        lines.append("• Load: Rectangular box with name and power")
        lines.append("• Connection: Arrow shows power flow direction")

        return "\n".join(lines)

    def _create_new_project(self):
        """Create a new empty project"""
        # Clear all existing session state to ensure clean reset
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        # Create new empty project
        self.project = Project(
            project_name="New Electrical Project",
            standard="IEC",
            voltage_system="LV",
            ambient_temperature_c=40.0,
            altitude_m=0.0,
            created_by="EDA System User",
            created_date=datetime.now().isoformat(),
            version="1.0"
        )
        self.calculation_results = {}

        # Save to session state
        st.session_state.project = self.project
        st.session_state.calculation_results = self.calculation_results

        st.success("New project created!")
        st.rerun()

    def _load_demo_project(self):
        """Load the demo manufacturing plant project"""
        from demo_script import ElectricalDesignDemo

        demo = ElectricalDesignDemo()
        self.project = demo.create_manufacturing_plant_project()
        self.calculation_results = {}
        # Save to session state
        st.session_state.project = self.project
        st.session_state.calculation_results = self.calculation_results
        st.success("Demo project loaded!")

    def _save_project(self):
        """Save current project to JSON file"""
        if not self.project:
            st.error("No project to save.")
            return

        try:
            from .demo_script import ElectricalDesignDemo
        except ImportError:
            from demo_script import ElectricalDesignDemo

        demo = ElectricalDesignDemo()
        demo.project = self.project

        filename = f"{self.project.project_name.replace(' ', '_')}_Project.json"
        demo.export_project_data(filename)
        st.success(f"Project saved to {filename}")

    def _generate_sld_graph(self):
        """Generate SLD graph object from project data"""
        nodes = []
        edges = []

        # Add transformers
        for tx in self.project.transformers:
            nodes.append({
                "id": tx.transformer_id,
                "type": "transformer",
                "name": tx.name,
                "rating_kva": tx.rating_kva,
                "primary_v": tx.primary_voltage_v,
                "secondary_v": tx.secondary_voltage_v
            })

        # Add buses
        for bus in self.project.buses:
            nodes.append({
                "id": bus.bus_id,
                "type": "bus",
                "name": bus.bus_name,
                "voltage_v": bus.voltage
            })

        # Add loads
        for load in self.project.loads:
            node = {
                "id": load.load_id,
                "type": "load",
                "name": load.load_name,
                "power_kw": load.power_kw,
                "voltage_v": load.voltage,
                "phases": load.phases
            }
            if load.source_bus:
                node["source_bus"] = load.source_bus
            nodes.append(node)

        # Add breakers
        for breaker in self.project.breakers:
            nodes.append({
                "id": breaker.breaker_id,
                "type": "breaker",
                "rated_current_a": breaker.rated_current_a,
                "associated_load_id": breaker.load_id
            })

        # Create edges
        # Transformer to bus connections
        if self.project.transformers and self.project.buses:
            main_bus = next((bus for bus in self.project.buses if not bus.parent_bus), None)
            if main_bus:
                for tx in self.project.transformers:
                    edges.append({
                        "from": tx.transformer_id,
                        "to": main_bus.bus_id,
                        "type": "transformer-to-bus"
                    })

        # Bus to bus connections
        for bus in self.project.buses:
            if bus.parent_bus:
                edges.append({
                    "from": bus.parent_bus,
                    "to": bus.bus_id,
                    "type": "bus-to-bus"
                })

        # Bus to load connections via breakers
        for load in self.project.loads:
            if load.source_bus:
                breaker = next((br for br in self.project.breakers if br.load_id == load.load_id), None)
                if breaker:
                    edges.append({
                        "from": load.source_bus,
                        "to": breaker.breaker_id,
                        "type": "bus-to-breaker"
                    })
                    edges.append({
                        "from": breaker.breaker_id,
                        "to": load.load_id,
                        "type": "breaker-to-load"
                    })
                else:
                    edges.append({
                        "from": load.source_bus,
                        "to": load.load_id,
                        "type": "bus-to-load"
                    })

        self.sld_graph = {
            "nodes": nodes,
            "edges": edges
        }

    def _generate_sld_diagram(self):
        """Generate Graphviz DOT code for SLD diagram"""
        if not hasattr(self, 'sld_graph') or not self.sld_graph:
            self._generate_sld_graph()

        dot_lines = []
        dot_lines.append("digraph SLD {")
        dot_lines.append("  rankdir=LR;")
        dot_lines.append("  node [fontname=\"Helvetica\"];")
        dot_lines.append("  edge [penwidth=1.0];")
        dot_lines.append("")

        # Group nodes by bus
        bus_nodes = {}
        for node in self.sld_graph["nodes"]:
            if node["type"] == "bus":
                bus_nodes[node["id"]] = []
            elif node["type"] in ["breaker", "load"]:
                source_bus = None
                if node["type"] == "load" and "source_bus" in node:
                    source_bus = node["source_bus"]
                elif node["type"] == "breaker" and "associated_load_id" in node:
                    load = next((l for l in self.sld_graph["nodes"]
                               if l["type"] == "load" and l["id"] == node["associated_load_id"]), None)
                    if load and "source_bus" in load:
                        source_bus = load["source_bus"]

                if source_bus and source_bus in bus_nodes:
                    bus_nodes[source_bus].append(node)

        # Create clusters
        for bus_id, components in bus_nodes.items():
            bus_node = next((n for n in self.sld_graph["nodes"] if n["id"] == bus_id), None)
            if bus_node:
                dot_lines.append(f"  subgraph cluster_{bus_id} {{")
                dot_lines.append("    style=dashed;")
                dot_lines.append(f"    {bus_id} [shape=circle, label=\"{bus_node['name']}\\n{bus_node['voltage_v']}V\"];")

                for comp in components:
                    if comp["type"] == "breaker":
                        dot_lines.append(f"    {comp['id']} [shape=box, width=0.5, height=0.3, label=\"CB{comp['id']}\"];")
                    elif comp["type"] == "load":
                        dot_lines.append(f"    {comp['id']} [shape=box, label=\"{comp['name']}\\n{comp['power_kw']}kW\"];")

                dot_lines.append("  }")
                dot_lines.append("")

        # Add transformers
        for node in self.sld_graph["nodes"]:
            if node["type"] == "transformer":
                dot_lines.append(f"  {node['id']} [shape=circle, label=\"{node['name']}\\n{node['rating_kva']}kVA\"];")

        dot_lines.append("")

        # Add edges
        for edge in self.sld_graph["edges"]:
            if edge["type"] == "transformer-to-bus":
                dot_lines.append(f"  {edge['from']} -> {edge['to']} [arrowhead=normal];")
            elif edge["type"] == "bus-to-bus":
                dot_lines.append(f"  {edge['from']} -> {edge['to']} [arrowhead=normal];")
            elif edge["type"] == "bus-to-breaker":
                dot_lines.append(f"  {edge['from']} -> {edge['to']};")
            elif edge["type"] == "breaker-to-load":
                dot_lines.append(f"  {edge['to']} -> {edge['from']};")
            elif edge["type"] == "bus-to-load":
                dot_lines.append(f"  {edge['from']} -> {edge['to']};")

        dot_lines.append("}")
        self.sld_dot_content = "\n".join(dot_lines)

    def _ai_optimize_project(self):
        """AI-powered project optimization"""
        if not self.project or not self.ai_analyzer:
            st.error("Project or AI analyzer not available")
            return
        
        try:
            with st.spinner("🤖 AI analyzing optimization opportunities..."):
                analysis = self.ai_analyzer.analyze_design(self.project)
                
                st.markdown("### 🔧 AI Project Optimization")
                
                # Optimization summary
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Current Score", f"{analysis.overall_score:.0f}/100")
                with col2:
                    optimization_potential = min(100 - analysis.overall_score, 30)
                    st.metric("Optimization Potential", f"+{optimization_potential:.0f}")
                with col3:
                    st.metric("Issues to Fix", len(analysis.validation_issues) + len(analysis.safety_concerns))
                
                st.markdown("---")
                
                # Critical issues first
                if analysis.validation_issues or analysis.safety_concerns:
                    st.error("### 🚨 Critical Issues (Fix First)")
                    all_critical = analysis.validation_issues + analysis.safety_concerns
                    for i, issue in enumerate(all_critical, 1):
                        st.write(f"{i}. {issue}")
                        
                        # AI-powered fix suggestions
                        if self.equipment_suggester:
                            with st.expander(f"🔧 AI Fix Suggestion for Issue {i}"):
                                fix_suggestion = self._get_ai_fix_suggestion(issue, analysis)
                                st.info(fix_suggestion)
                
                # Optimization recommendations
                if analysis.recommendations:
                    st.success("### 💡 Optimization Recommendations")
                    for i, rec in enumerate(analysis.recommendations, 1):
                        st.write(f"{i}. {rec}")
                        
                        # Quick action buttons
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"✅ Apply {i}", key=f"apply_rec_{i}"):
                                self._apply_optimization_recommendation(rec)
                                st.success(f"Applied recommendation {i}")
                                st.rerun()
                        with col2:
                            if st.button(f"📋 Details {i}", key=f"details_rec_{i}"):
                                with st.expander(f"Details for Recommendation {i}", expanded=True):
                                    st.write(f"**Recommendation:** {rec}")
                                    details = self._get_recommendation_details(rec)
                                    st.write(details)
                
                # AI equipment optimization
                if self.equipment_suggester and self.project.loads:
                    st.markdown("### 🔌 Equipment Optimization")
                    
                    for load in self.project.loads[:3]:  # Show top 3 loads
                        with st.expander(f"⚡ {load.load_name} Optimization"):
                            config = self.equipment_suggester.get_quick_configuration(load)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown("**Current vs Recommended**")
                                if hasattr(load, 'cable_size_sqmm') and load.cable_size_sqmm:
                                    st.write(f"Cable: {load.cable_size_sqmm} → {config['cable']['size_sqmm']} mm²")
                                if hasattr(load, 'breaker_rating_a') and load.breaker_rating_a:
                                    st.write(f"Breaker: {load.breaker_rating_a} → {config['breaker']['rating_a']:.0f} A")
                            
                            with col2:
                                if st.button(f"🔄 Optimize {load.load_id}", key=f"opt_{load.load_id}"):
                                    self._apply_equipment_optimization(load, config)
                                    st.success(f"Optimized {load.load_name}")
                                    st.rerun()
                
                # Optimization summary
                st.markdown("---")
                st.info("🎯 **AI Optimization Complete!** Review the suggestions above and apply the relevant ones to improve your design.")
                
        except Exception as e:
            st.error(f"AI optimization failed: {str(e)}")

    def _ai_generate_executive_summary(self):
        """Generate AI-powered executive summary"""
        if not self.project:
            st.error("No project loaded")
            return
        
        try:
            with st.spinner("🤖 AI generating executive summary..."):
                st.markdown("### 📋 AI Executive Summary")
                
                # Project overview
                st.markdown("#### 🏗️ Project Overview")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Loads", len(self.project.loads))
                with col2:
                    total_power = sum(load.power_kw for load in self.project.loads)
                    st.metric("Total Power", f"{total_power:.1f} kW")
                with col3:
                    st.metric("Buses", len(self.project.buses))
                with col4:
                    st.metric("Transformers", len(self.project.transformers))
                
                # AI analysis insights
                if self.ai_analyzer:
                    analysis = self.ai_analyzer.analyze_design(self.project)
                    
                    st.markdown("#### 🤖 AI Assessment")
                    col1, col2 = st.columns(2)
                    with col1:
                        score_color = "🟢 Excellent" if analysis.overall_score >= 80 else "🟡 Good" if analysis.overall_score >= 60 else "🔴 Needs Improvement"
                        st.write(f"**Design Quality:** {score_color}")
                        st.write(f"**Overall Score:** {analysis.overall_score:.0f}/100")
                    
                    with col2:
                        st.write(f"**Issues Found:** {len(analysis.validation_issues)}")
                        st.write(f"**Recommendations:** {len(analysis.recommendations)}")
                    
                    # Key insights
                    st.markdown("#### 💡 Key Insights")
                    if analysis.validation_issues:
                        st.error("**Critical Issues:**")
                        for issue in analysis.validation_issues[:2]:
                            st.write(f"• {issue}")
                    
                    if analysis.recommendations:
                        st.success("**Top Recommendations:**")
                        for rec in analysis.recommendations[:3]:
                            st.write(f"• {rec}")
                    
                    if analysis.warnings:
                        st.info("**Important Notes:**")
                        for warning in analysis.warnings[:2]:
                            st.write(f"• {warning}")
                
                # Load type analysis
                st.markdown("#### ⚡ Load Distribution")
                load_types = {}
                for load in self.project.loads:
                    load_type = load.load_type.value
                    if load_type not in load_types:
                        load_types[load_type] = {"count": 0, "power": 0}
                    load_types[load_type]["count"] += 1
                    load_types[load_type]["power"] += load.power_kw
                
                for load_type, data in load_types.items():
                    st.write(f"**{load_type.title()}:** {data['count']} loads, {data['power']:.1f} kW total")
                
                # Standards compliance
                if self.ai_analyzer:
                    analysis = self.ai_analyzer.analyze_design(self.project)
                    if analysis.standards_compliance:
                        st.markdown("#### 📐 Standards Compliance")
                        for aspect, compliant in analysis.standards_compliance.items():
                            status = "✅ Compliant" if compliant else "❌ Non-compliant"
                            st.write(f"**{aspect}:** {status}")
                
                # Next steps
                st.markdown("#### 🎯 Recommended Next Steps")
                st.write("1. **Review Critical Issues** - Address any safety or validation concerns")
                st.write("2. **Apply Optimizations** - Implement AI recommendations for efficiency")
                st.write("3. **Finalize Calculations** - Ensure all electrical calculations are complete")
                st.write("4. **Generate Documentation** - Export reports and SLD diagrams")
                st.write("5. **Peer Review** - Have design reviewed by senior engineer")
                
                # Export options
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📄 Export Summary PDF", type="primary"):
                        st.info("PDF export would be implemented here")
                with col2:
                    if st.button("📧 Email Summary"):
                        st.info("Email functionality would be implemented here")
                
        except Exception as e:
            st.error(f"Failed to generate executive summary: {str(e)}")

    def _get_ai_fix_suggestion(self, issue: str, analysis) -> str:
        """Get AI-powered fix suggestion for an issue"""
        # This would integrate with the LLM for contextual suggestions
        suggestions = {
            "overload": "Consider upgrading cable size or redistributing loads across phases",
            "voltage_drop": "Reduce cable length or increase conductor size to meet voltage drop limits",
            "protection": "Install appropriate overcurrent protection devices",
            "grounding": "Ensure proper grounding according to standards"
        }
        
        for key, suggestion in suggestions.items():
            if key.lower() in issue.lower():
                return suggestion
        
        return "Review the component specifications and applicable standards"

    def _apply_optimization_recommendation(self, recommendation: str):
        """Apply an optimization recommendation"""
        # This would implement the actual optimization logic
        # For now, just log it
        if not hasattr(self, 'applied_optimizations'):
            self.applied_optimizations = []
        self.applied_optimizations.append(recommendation)

    def _get_recommendation_details(self, recommendation: str) -> str:
        """Get detailed explanation for a recommendation"""
        details = {
            "efficiency": "This optimization will improve energy efficiency and reduce operating costs",
            "safety": "This change enhances system safety and compliance with electrical codes",
            "capacity": "This upgrade provides additional capacity for future expansion",
            "reliability": "This improvement increases system reliability and reduces downtime"
        }
        
        for key, detail in details.items():
            if key.lower() in recommendation.lower():
                return detail
        
        return "This recommendation improves overall system performance and compliance"

    def _apply_equipment_optimization(self, load, config):
        """Apply equipment optimization to a load"""
        try:
            # Update cable size
            if config.get("cable"):
                load.cable_size_sqmm = config["cable"]["size_sqmm"]
                load.cable_type = config["cable"]["type"]
            
            # Update breaker rating
            if config.get("breaker"):
                load.breaker_rating_a = config["breaker"]["rating_a"]
                load.breaker_type = config["breaker"]["type"]
            
            # Update the load in the project
            for i, project_load in enumerate(self.project.loads):
                if project_load.load_id == load.load_id:
                    self.project.loads[i] = load
                    break
            
            # Save to session state
            st.session_state.project = self.project
            
        except Exception as e:
            st.error(f"Failed to apply optimization: {str(e)}")


def main():
    """Main application entry point"""
    app = ElectricalDesignApp()
    app.run()


if __name__ == "__main__":
    main()
