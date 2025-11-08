"""
Equipment Suggestion UI Component

Streamlit interface for:
- Project loading and AI analysis
- Interactive suggestion review and acceptance
- Real-time project updates
- Suggestion history and analytics
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any
import logging
from datetime import datetime
import json

from models import Project
from ai_equipment_suggester import AIEquipmentConfigSuggester, SuggestionSet

logger = logging.getLogger(__name__)


class EquipmentSuggestionUI:
    """Streamlit UI for equipment suggestions"""
    
    def __init__(self):
        """Initialize UI component"""
        self.suggester = AIEquipmentConfigSuggester()
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state"""
        if 'suggestion_set' not in st.session_state:
            st.session_state.suggestion_set = None
        if 'current_project' not in st.session_state:
            st.session_state.current_project = None
        if 'analysis_complete' not in st.session_state:
            st.session_state.analysis_complete = False
        if 'suggestion_decisions' not in st.session_state:
            st.session_state.suggestion_decisions = {}
    
    def render(self):
        """Render main UI"""
        st.set_page_config(page_title="Equipment Configuration Suggester", layout="wide")
        
        st.title("🤖 AI Equipment Configuration Suggester")
        st.markdown("Intelligent equipment suggestions powered by AI and vector database analysis")
        
        # Create tabs for workflow
        tab1, tab2, tab3, tab4 = st.tabs([
            "📂 Load Project",
            "🔍 Analysis & Insights",
            "✅ Review Suggestions",
            "📊 Apply & Summary"
        ])
        
        with tab1:
            self._render_project_loader()
        
        with tab2:
            self._render_analysis_insights()
        
        with tab3:
            self._render_suggestion_review()
        
        with tab4:
            self._render_apply_summary()
    
    def _render_project_loader(self):
        """Render project loading interface"""
        st.subheader("Load Electrical Project")
        
        col1, col2 = st.columns(2)
        
        with col1:
            project_source = st.radio(
                "Load project from:",
                ["Upload File", "Create Sample", "Recent Projects"]
            )
        
        if project_source == "Upload File":
            uploaded_file = st.file_uploader(
                "Upload project JSON",
                type=["json"]
            )
            
            if uploaded_file:
                try:
                    project_data = json.load(uploaded_file)
                    # Parse into Project object (simplified)
                    project = self._parse_project_json(project_data)
                    st.session_state.current_project = project
                    st.success(f"✓ Loaded project: {project.project_name}")
                    st.info(f"Loads: {len(project.loads)} | Cables: {len(project.cables)} | Breakers: {len(project.breakers)}")
                except Exception as e:
                    st.error(f"Failed to load project: {e}")
        
        elif project_source == "Create Sample":
            st.info("Sample project loaded for demonstration")
            # Could load sample project here
        
        # Show project summary if loaded
        if st.session_state.current_project:
            st.divider()
            st.subheader("Project Summary")
            
            project = st.session_state.current_project
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Loads", len(project.loads))
            with col2:
                total_power = sum(l.power_kw for l in project.loads if l.power_kw)
                st.metric("Total Power", f"{total_power:.1f} kW")
            with col3:
                st.metric("Buses", len(project.buses))
            with col4:
                st.metric("Transformers", len(project.transformers))
            
            # Load list
            with st.expander("View Loads", expanded=False):
                load_data = []
                for load in project.loads:
                    load_data.append({
                        "Load ID": load.load_id,
                        "Name": load.load_name,
                        "Power (kW)": load.power_kw,
                        "Voltage (V)": load.voltage,
                        "Current (A)": load.current_a or "N/A",
                        "Type": str(load.load_type)
                    })
                st.dataframe(pd.DataFrame(load_data), use_container_width=True)
            
            # Analyze button
            if st.button("🚀 Analyze Project & Generate Suggestions", use_container_width=True):
                with st.spinner("Analyzing project..."):
                    suggestion_set = self.suggester.analyze_and_suggest(project)
                    st.session_state.suggestion_set = suggestion_set
                    st.session_state.analysis_complete = True
                    st.success("Analysis complete!")
                    st.rerun()
    
    def _render_analysis_insights(self):
        """Render analysis results and insights"""
        if not st.session_state.analysis_complete or not st.session_state.suggestion_set:
            st.info("👈 Load a project and run analysis in the 'Load Project' tab")
            return
        
        suggestion_set = st.session_state.suggestion_set
        
        st.subheader("🔍 Project Analysis Results")
        
        # Overall optimization potential
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Optimization Potential",
                f"{suggestion_set.overall_optimization_potential:.1f}%"
            )
        with col2:
            st.metric("Total Insights", len(suggestion_set.insights))
        with col3:
            st.metric("Total Suggestions", 
                     sum(len(s) for s in suggestion_set.load_suggestions.values()))
        
        # Insights section
        if suggestion_set.insights:
            st.subheader("💡 Key Insights")
            
            for insight in suggestion_set.insights:
                # Color code by priority
                colors = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }
                
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {colors.get(insight.priority, '●')} {insight.title}")
                        st.write(insight.description)
                        if insight.affected_items:
                            st.caption(f"Affects: {', '.join(insight.affected_items[:5])}")
                    with col2:
                        st.metric("Confidence", f"{insight.confidence*100:.0f}%")
        else:
            st.info("No insights generated for this project")
        
        # Load distribution analysis
        if st.session_state.current_project:
            st.subheader("📊 Load Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Power distribution
                loads = st.session_state.current_project.loads
                power_data = {
                    "Load ID": [l.load_id for l in loads],
                    "Power (kW)": [l.power_kw for l in loads],
                    "Current (A)": [l.current_a or 0 for l in loads]
                }
                
                st.bar_chart(
                    pd.DataFrame(power_data).set_index("Load ID")["Power (kW)"],
                    use_container_width=True
                )
                st.caption("Power Distribution by Load")
            
            with col2:
                # Load types
                load_types = {}
                for load in loads:
                    lt = str(load.load_type)
                    load_types[lt] = load_types.get(lt, 0) + 1
                
                st.bar_chart(pd.Series(load_types), use_container_width=True)
                st.caption("Loads by Type")
    
    def _render_suggestion_review(self):
        """Render suggestion review interface"""
        if not st.session_state.suggestion_set:
            st.info("👈 Complete analysis first")
            return
        
        suggestion_set = st.session_state.suggestion_set
        
        st.subheader("✅ Review & Accept Suggestions")
        
        if not suggestion_set.load_suggestions:
            st.warning("No load suggestions generated")
            return
        
        # Load selector
        load_ids = list(suggestion_set.load_suggestions.keys())
        selected_load = st.selectbox("Select load to review:", load_ids)
        
        if selected_load:
            suggestions = suggestion_set.load_suggestions[selected_load]
            
            st.subheader(f"Suggestions for {selected_load}")
            
            for idx, suggestion in enumerate(suggestions):
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"### Option {idx + 1}")
                        st.write(suggestion.reasoning)
                    
                    with col2:
                        st.metric("Confidence", f"{suggestion.confidence*100:.0f}%")
                        st.metric("Status", suggestion.status)
                    
                    # Equipment details
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.subheader("Cable")
                        if suggestion.cable_suggestions:
                            cable = suggestion.cable_suggestions[0]
                            st.write(f"**Size:** {cable.size_sqmm} mm²")
                            st.write(f"**Type:** {cable.type}")
                            st.write(f"**Material:** {cable.material}")
                            st.write(f"**Insulation:** {cable.insulation}")
                    
                    with col2:
                        st.subheader("Breaker")
                        if suggestion.breaker_suggestions:
                            breaker = suggestion.breaker_suggestions[0]
                            st.write(f"**Rating:** {breaker.rating_a} A")
                            st.write(f"**Type:** {breaker.type}")
                            st.write(f"**Curve:** {breaker.curve}")
                            st.write(f"**Breaking Cap:** {breaker.breaking_capacity_ka} kA")
                    
                    with col3:
                        st.subheader("Starter")
                        if suggestion.starter_suggestion:
                            st.write(f"**Type:** {suggestion.starter_suggestion.get('type', 'N/A')}")
                            st.write(f"**Reason:** {suggestion.starter_suggestion.get('reason', '')}")
                        else:
                            st.write("Not required")
                    
                    # User interaction
                    st.divider()
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(
                            "✅ Accept",
                            key=f"accept_{suggestion.suggestion_id}",
                            use_container_width=True
                        ):
                            self.suggester.accept_suggestion(
                                suggestion_set,
                                selected_load,
                                idx
                            )
                            st.success("Suggestion accepted!")
                            st.session_state.suggestion_decisions[suggestion.suggestion_id] = "accepted"
                    
                    with col2:
                        if st.button(
                            "❌ Reject",
                            key=f"reject_{suggestion.suggestion_id}",
                            use_container_width=True
                        ):
                            reason = st.text_input("Reason for rejection:", key=f"reason_{idx}")
                            self.suggester.reject_suggestion(
                                suggestion_set,
                                selected_load,
                                idx,
                                reason
                            )
                            st.info("Suggestion rejected")
                            st.session_state.suggestion_decisions[suggestion.suggestion_id] = "rejected"
                    
                    with col3:
                        if st.button(
                            "📝 Edit",
                            key=f"edit_{suggestion.suggestion_id}",
                            use_container_width=True
                        ):
                            st.info("Edit mode not yet implemented")
    
    def _render_apply_summary(self):
        """Render apply suggestions and summary"""
        if not st.session_state.suggestion_set or not st.session_state.current_project:
            st.info("👈 Complete analysis and review suggestions first")
            return
        
        st.subheader("📊 Apply Suggestions & Summary")
        
        suggestion_set = st.session_state.suggestion_set
        project = st.session_state.current_project
        
        # Summary of decisions
        col1, col2, col3 = st.columns(3)
        
        accepted = sum(1 for sugg_list in suggestion_set.load_suggestions.values() 
                      for s in sugg_list if s.status == "accepted")
        rejected = sum(1 for sugg_list in suggestion_set.load_suggestions.values() 
                      for s in sugg_list if s.status == "rejected")
        pending = sum(1 for sugg_list in suggestion_set.load_suggestions.values() 
                     for s in sugg_list if s.status == "pending")
        
        with col1:
            st.metric("✅ Accepted", accepted)
        with col2:
            st.metric("❌ Rejected", rejected)
        with col3:
            st.metric("⏳ Pending", pending)
        
        # Apply button
        if accepted > 0:
            if st.button("🚀 Apply All Accepted Suggestions", use_container_width=True):
                with st.spinner("Applying suggestions to project..."):
                    changes = self.suggester.apply_accepted_suggestions(
                        project,
                        suggestion_set
                    )
                    
                    st.success("Suggestions applied successfully!")
                    
                    # Show changes summary
                    st.subheader("Changes Applied")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Loads Updated", changes.get("loads_updated", 0))
                    with col2:
                        st.metric("Cables Updated", changes.get("cables_updated", 0))
                    with col3:
                        st.metric("Breakers Updated", changes.get("breakers_updated", 0))
                    with col4:
                        st.metric("Buses Updated", changes.get("buses_updated", 0))
                    
                    if changes.get("errors"):
                        st.warning("Some errors occurred during application:")
                        for error in changes["errors"]:
                            st.error(error)
        
        # Save to vector DB
        st.divider()
        st.subheader("💾 Save for Future Reference")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            success_rating = st.slider(
                "Rate the quality of these suggestions:",
                0.0, 1.0, 0.8
            )
        with col2:
            if st.button("Save to Knowledge Base", use_container_width=True):
                self.suggester.save_suggestions_to_vector_db(
                    suggestion_set,
                    success_rating=success_rating
                )
                st.success("Suggestions saved to vector database!")
        
        # Export
        st.divider()
        st.subheader("📤 Export")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Export as JSON", use_container_width=True):
                export_data = {
                    "project_id": suggestion_set.project_id,
                    "timestamp": suggestion_set.analysis_timestamp,
                    "suggestions": {
                        load_id: [
                            {
                                "id": s.suggestion_id,
                                "status": s.status,
                                "confidence": s.confidence,
                                "reasoning": s.reasoning
                            }
                            for s in suggestions
                        ]
                        for load_id, suggestions in suggestion_set.load_suggestions.items()
                    }
                }
                
                st.download_button(
                    "Download JSON",
                    json.dumps(export_data, indent=2),
                    f"suggestions_{suggestion_set.project_id}.json",
                    "application/json"
                )
        
        with col2:
            if st.button("Export as CSV Report", use_container_width=True):
                # Create CSV export
                rows = []
                for load_id, suggestions in suggestion_set.load_suggestions.items():
                    for sugg in suggestions:
                        rows.append({
                            "Load ID": load_id,
                            "Suggestion ID": sugg.suggestion_id,
                            "Type": sugg.suggestion_type,
                            "Status": sugg.status,
                            "Confidence": f"{sugg.confidence*100:.1f}%",
                            "Reasoning": sugg.reasoning[:100]
                        })
                
                df = pd.DataFrame(rows)
                csv = df.to_csv(index=False)
                
                st.download_button(
                    "Download CSV",
                    csv,
                    f"suggestions_{suggestion_set.project_id}.csv",
                    "text/csv"
                )
    
    def _parse_project_json(self, data: Dict[str, Any]) -> Project:
        """Parse JSON into Project object (simplified)"""
        from models import Load, LoadType, InstallationMethod, DutyCycle, Priority
        
        project = Project(
            project_name=data.get("project_name", "Imported Project"),
            project_id=data.get("project_id")
        )
        
        # Parse loads
        for load_data in data.get("loads", []):
            load = Load(
                load_id=load_data.get("load_id", ""),
                load_name=load_data.get("load_name", ""),
                power_kw=load_data.get("power_kw", 1.0),
                voltage=load_data.get("voltage", 400),
                phases=load_data.get("phases", 3),
                power_factor=load_data.get("power_factor", 0.85),
                load_type=LoadType.GENERAL,
                current_a=load_data.get("current_a")
            )
            project.add_load(load)
        
        return project


def main():
    """Main entry point"""
    ui = EquipmentSuggestionUI()
    ui.render()


if __name__ == "__main__":
    main()
