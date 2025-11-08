"""
AI Equipment Suggester with Project Analysis & Vector DB Integration

Enhanced equipment configuration system with:
- Project-wide AI analysis and insights
- Intelligent equipment suggestions with confidence scores
- Vector database-backed recommendations from historical designs
- Interactive suggestion acceptance/rejection workflow
- Automatic configuration updates on acceptance
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig
from vector_database_manager import get_vector_database
from equipment_suggester import AIEquipmentSuggester, CableRecommendation, BreakerRecommendation, TransformerRecommendation
from design_analyzer import AIDesignAnalyzer
from models import Project, Load, Cable, Breaker, Transformer, Bus

logger = logging.getLogger(__name__)


@dataclass
class ProjectInsight:
    """AI-generated insight about project"""
    insight_type: str  # "optimization", "risk", "pattern", "efficiency"
    title: str
    description: str
    affected_items: List[str] = field(default_factory=list)
    priority: str = "medium"  # "critical", "high", "medium", "low"
    confidence: float = 0.8


@dataclass
class SuggestionSet:
    """Collection of equipment suggestions for project loads"""
    project_id: str
    analysis_timestamp: str
    total_loads: int
    insights: List[ProjectInsight] = field(default_factory=list)
    load_suggestions: Dict[str, List[EquipmentConfigSuggestion]] = field(default_factory=dict)
    bus_suggestions: Dict[str, BusConfigSuggestion] = field(default_factory=dict)
    transformer_suggestions: List[TransformerConfigSuggestion] = field(default_factory=list)
    accepted_suggestions: Dict[str, bool] = field(default_factory=dict)
    rejection_reasons: Dict[str, str] = field(default_factory=dict)
    overall_optimization_potential: float = 0.0


@dataclass
class EquipmentConfigSuggestion:
    """Suggestion for equipment configuration for a load"""
    load_id: str
    suggestion_id: str
    suggestion_type: str  # "cable", "breaker", "starter", "combination"
    
    # Configuration suggestions
    cable_suggestions: List[CableRecommendation] = field(default_factory=list)
    breaker_suggestions: List[BreakerRecommendation] = field(default_factory=list)
    starter_suggestion: Optional[Dict[str, Any]] = None
    
    # AI analysis
    reasoning: str = ""
    confidence: float = 0.85
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    vector_db_source: Optional[str] = None  # Source from similar historical designs
    
    # Workflow
    status: str = "pending"  # "pending", "accepted", "rejected", "modified"
    user_notes: str = ""
    accepted_at: Optional[str] = None
    
    def to_config(self) -> Dict[str, Any]:
        """Convert to equipment configuration dict"""
        config = {
            "load_id": self.load_id,
            "timestamp": datetime.now().isoformat(),
            "cable": None,
            "breaker": None,
            "starter": None
        }
        
        if self.cable_suggestions:
            cable = self.cable_suggestions[0]
            config["cable"] = {
                "size_sqmm": cable.size_sqmm,
                "type": cable.type,
                "material": cable.material,
                "insulation": cable.insulation,
                "confidence": cable.confidence
            }
        
        if self.breaker_suggestions:
            breaker = self.breaker_suggestions[0]
            config["breaker"] = {
                "rating_a": breaker.rating_a,
                "type": breaker.type,
                "curve": breaker.curve,
                "breaking_capacity_ka": breaker.breaking_capacity_ka,
                "confidence": breaker.confidence
            }
        
        if self.starter_suggestion:
            config["starter"] = self.starter_suggestion
        
        return config


@dataclass
class BusConfigSuggestion:
    """Suggestion for bus/panel configuration"""
    bus_id: str
    suggestion_id: str
    
    # Configuration suggestions
    recommended_short_circuit_rating_ka: float
    recommended_main_breaker_rating_a: float
    recommendations: List[str] = field(default_factory=list)
    
    # Analysis
    current_utilization_percent: float = 0.0
    projected_utilization_percent: float = 0.0
    headroom_percentage: float = 0.0
    
    confidence: float = 0.85
    status: str = "pending"


@dataclass
class TransformerConfigSuggestion:
    """Suggestion for transformer configuration"""
    transformer_id: Optional[str] = None
    suggestion_id: str = ""
    
    kva_rating: float = 0.0
    primary_voltage: float = 0.0
    secondary_voltage: float = 0.0
    connection_type: str = ""
    cooling_type: str = ""
    
    reasoning: str = ""
    confidence: float = 0.85
    utilization_percent: float = 0.0
    headroom_percent: float = 0.0
    
    status: str = "pending"


class AIEquipmentConfigSuggester:
    """
    AI-powered equipment configuration suggester with project analysis
    
    Provides:
    - Comprehensive project analysis with AI insights
    - Equipment suggestions for all loads
    - Vector DB-backed recommendations from similar projects
    - Interactive acceptance/rejection workflow
    - Automatic configuration updates
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with LLM and vector DB"""
        try:
            self.llm_config = LLMConfig(api_key=api_key)
            self.llm = LLMMultimodalProcessor(self.llm_config)
        except Exception as e:
            logger.warning(f"LLM initialization failed: {e}")
            self.llm = None
        
        try:
            self.vector_db = get_vector_database()
        except Exception as e:
            logger.warning(f"Vector database initialization failed: {e}")
            self.vector_db = None
        
        self.equipment_suggester = AIEquipmentSuggester(api_key=api_key)
        self.design_analyzer = AIDesignAnalyzer(api_key=api_key)
    
    def analyze_and_suggest(self, project: Project) -> SuggestionSet:
        """
        Load project and provide comprehensive AI analysis with equipment suggestions
        
        Args:
            project: Project to analyze
        
        Returns:
            SuggestionSet with all suggestions and insights
        """
        suggestion_set = SuggestionSet(
            project_id=project.project_id or "unknown",
            analysis_timestamp=datetime.now().isoformat(),
            total_loads=len(project.loads)
        )
        
        try:
            # Step 1: Analyze overall project design
            logger.info(f"Analyzing project: {project.project_name}")
            design_analysis = self.design_analyzer.analyze_design(project)
            
            # Step 2: Extract project-level insights
            suggestion_set.insights = self._extract_project_insights(
                project, design_analysis
            )
            
            # Step 3: Generate equipment suggestions for each load
            for load in project.loads:
                load_suggestions = self._suggest_load_equipment(load, project)
                suggestion_set.load_suggestions[load.load_id] = load_suggestions
            
            # Step 4: Suggest bus/panel configurations
            for bus in project.buses:
                bus_suggestion = self._suggest_bus_configuration(bus, project)
                if bus_suggestion:
                    suggestion_set.bus_suggestions[bus.bus_id] = bus_suggestion
            
            # Step 5: Suggest transformer configurations
            if project.transformers:
                transformer_suggestions = self._suggest_transformer_configurations(project)
                suggestion_set.transformer_suggestions = transformer_suggestions
            
            # Step 6: Calculate optimization potential
            suggestion_set.overall_optimization_potential = self._calculate_optimization_potential(
                suggestion_set
            )
            
            logger.info(f"Analysis complete: {len(suggestion_set.insights)} insights, "
                       f"{sum(len(s) for s in suggestion_set.load_suggestions.values())} load suggestions")
        
        except Exception as e:
            logger.error(f"Project analysis failed: {e}")
        
        return suggestion_set
    
    def accept_suggestion(self, suggestion_set: SuggestionSet, 
                         load_id: str, suggestion_index: int = 0,
                         user_notes: str = "") -> bool:
        """
        Accept equipment suggestion for a load
        
        Args:
            suggestion_set: The suggestion set being processed
            load_id: Load ID to accept suggestion for
            suggestion_index: Index of suggestion to accept (0 = top)
            user_notes: Optional user notes
        
        Returns:
            True if accepted successfully
        """
        try:
            if load_id not in suggestion_set.load_suggestions:
                logger.error(f"Load {load_id} not found in suggestions")
                return False
            
            suggestions = suggestion_set.load_suggestions[load_id]
            if suggestion_index >= len(suggestions):
                logger.error(f"Invalid suggestion index {suggestion_index}")
                return False
            
            suggestion = suggestions[suggestion_index]
            suggestion.status = "accepted"
            suggestion.user_notes = user_notes
            suggestion.accepted_at = datetime.now().isoformat()
            
            # Mark as accepted in tracking dict
            suggestion_set.accepted_suggestions[suggestion.suggestion_id] = True
            
            logger.info(f"Accepted suggestion {suggestion.suggestion_id} for load {load_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to accept suggestion: {e}")
            return False
    
    def reject_suggestion(self, suggestion_set: SuggestionSet,
                         load_id: str, suggestion_index: int = 0,
                         reason: str = "") -> bool:
        """
        Reject equipment suggestion
        
        Args:
            suggestion_set: The suggestion set being processed
            load_id: Load ID
            suggestion_index: Index of suggestion to reject
            reason: Reason for rejection
        
        Returns:
            True if rejected successfully
        """
        try:
            if load_id not in suggestion_set.load_suggestions:
                return False
            
            suggestions = suggestion_set.load_suggestions[load_id]
            if suggestion_index >= len(suggestions):
                return False
            
            suggestion = suggestions[suggestion_index]
            suggestion.status = "rejected"
            suggestion_set.rejection_reasons[suggestion.suggestion_id] = reason
            
            logger.info(f"Rejected suggestion {suggestion.suggestion_id} for load {load_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to reject suggestion: {e}")
            return False
    
    def apply_accepted_suggestions(self, project: Project, 
                                   suggestion_set: SuggestionSet) -> Dict[str, Any]:
        """
        Apply all accepted suggestions to project
        
        Updates loads, cables, breakers with accepted configurations
        
        Args:
            project: Project to update
            suggestion_set: Accepted suggestions
        
        Returns:
            Summary of applied changes
        """
        changes = {
            "cables_updated": 0,
            "breakers_updated": 0,
            "loads_updated": 0,
            "buses_updated": 0,
            "transformers_updated": 0,
            "errors": []
        }
        
        try:
            # Apply load equipment suggestions
            for load_id, suggestions in suggestion_set.load_suggestions.items():
                for suggestion in suggestions:
                    if suggestion.status == "accepted":
                        config = suggestion.to_config()
                        load = project.get_load_by_id(load_id)
                        
                        if load:
                            # Update load with suggested equipment specs
                            if config.get("cable"):
                                load.cable_size_sqmm = config["cable"]["size_sqmm"]
                                load.cable_type = config["cable"]["type"]
                                load.cable_insulation = config["cable"]["insulation"]
                                changes["loads_updated"] += 1
                            
                            if config.get("breaker"):
                                load.breaker_rating_a = config["breaker"]["rating_a"]
                                load.breaker_type = config["breaker"]["type"]
                                load.breaker_curve = config["breaker"]["curve"]
                                changes["loads_updated"] += 1
            
            # Apply bus suggestions
            for bus_id, bus_suggestion in suggestion_set.bus_suggestions.items():
                if bus_suggestion.status == "accepted":
                    bus = next((b for b in project.buses if b.bus_id == bus_id), None)
                    if bus:
                        bus.short_circuit_rating_ka = bus_suggestion.recommended_short_circuit_rating_ka
                        changes["buses_updated"] += 1
            
            # Apply transformer suggestions
            for transformer_suggestion in suggestion_set.transformer_suggestions:
                if transformer_suggestion.status == "accepted":
                    if transformer_suggestion.transformer_id:
                        transformer = next(
                            (t for t in project.transformers 
                             if t.transformer_id == transformer_suggestion.transformer_id),
                            None
                        )
                        if transformer:
                            transformer.rating_kva = transformer_suggestion.kva_rating
                            transformer.cooling = transformer_suggestion.cooling_type
                            changes["transformers_updated"] += 1
            
            logger.info(f"Applied {changes['loads_updated']} load configurations from suggestions")
        
        except Exception as e:
            logger.error(f"Failed to apply suggestions: {e}")
            changes["errors"].append(str(e))
        
        return changes
    
    def save_suggestions_to_vector_db(self, suggestion_set: SuggestionSet,
                                      success_rating: float = 0.8):
        """
        Save accepted suggestions to vector DB for future reference
        
        Args:
            suggestion_set: Suggestions to save
            success_rating: Rating of how well suggestions performed
        """
        try:
            if not self.vector_db:
                return
            
            for load_id, suggestions in suggestion_set.load_suggestions.items():
                for suggestion in suggestions:
                    if suggestion.status == "accepted":
                        # Create design record
                        design_data = {
                            "load_id": load_id,
                            "suggestion_type": suggestion.suggestion_type,
                            "cable": suggestion.cable_suggestions[0].__dict__ if suggestion.cable_suggestions else None,
                            "breaker": suggestion.breaker_suggestions[0].__dict__ if suggestion.breaker_suggestions else None,
                            "reasoning": suggestion.reasoning,
                            "confidence": suggestion.confidence
                        }
                        
                        # Store in design history
                        self.vector_db.add_design_to_history(
                            design_id=suggestion.suggestion_id,
                            design_data=design_data,
                            project_context=f"Project {suggestion_set.project_id}, Load {load_id}",
                            success_rating=success_rating
                        )
            
            logger.info(f"Saved {len([s for sugg_list in suggestion_set.load_suggestions.values() for s in sugg_list if s.status == 'accepted'])} suggestions to vector DB")
        
        except Exception as e:
            logger.warning(f"Failed to save suggestions to vector DB: {e}")
    
    # Helper methods
    
    def _extract_project_insights(self, project: Project, 
                                  design_analysis) -> List[ProjectInsight]:
        """Extract high-level insights about project"""
        insights = []
        
        try:
            # Load balance analysis
            if project.loads:
                kw_values = [l.power_kw for l in project.loads if l.power_kw]
                if kw_values:
                    avg_load = sum(kw_values) / len(kw_values)
                    variance = sum((x - avg_load)**2 for x in kw_values) / len(kw_values)
                    if variance**0.5 > avg_load * 0.5:  # High variance
                        insights.append(ProjectInsight(
                            insight_type="optimization",
                            title="Unbalanced Load Distribution",
                            description="Loads vary significantly in power rating. Consider load balancing or phased approach.",
                            affected_items=[l.load_id for l in project.loads],
                            priority="high",
                            confidence=0.85
                        ))
            
            # Safety concerns from design analysis
            for concern in design_analysis.safety_concerns:
                insights.append(ProjectInsight(
                    insight_type="risk",
                    title="Safety Concern Identified",
                    description=concern,
                    priority="critical",
                    confidence=0.9
                ))
            
            # Optimization opportunities from LLM
            if self.llm:
                insights.extend(self._get_llm_insights(project))
            
            # Pattern matching from vector DB
            if self.vector_db:
                patterns = self._find_similar_project_patterns(project)
                for pattern in patterns:
                    insights.append(ProjectInsight(
                        insight_type="pattern",
                        title=f"Similar Pattern Found: {pattern.get('name', 'Unknown')}",
                        description=pattern.get('description', ''),
                        priority="medium",
                        confidence=pattern.get('confidence', 0.7)
                    ))
        
        except Exception as e:
            logger.warning(f"Failed to extract insights: {e}")
        
        return insights
    
    def _suggest_load_equipment(self, load: Load, project: Project) -> List[EquipmentConfigSuggestion]:
        """Generate equipment suggestions for a load"""
        suggestions = []
        
        try:
            suggestion_id = f"sugg_{load.load_id}_{datetime.now().timestamp()}"
            
            # Get cable suggestions
            cable_suggestions = self.equipment_suggester.suggest_cable(load, use_ai=True)
            
            # Get breaker suggestions
            breaker_suggestions = self.equipment_suggester.suggest_breaker(load, use_ai=True)
            
            # Determine if starter needed
            starter_suggestion = None
            if load.power_kw and load.power_kw > 3:
                starter_suggestion = {
                    "type": "Soft Starter or VFD" if load.power_kw > 10 else "Direct Online Starter",
                    "reason": f"Motor load {load.power_kw}kW requires starting equipment"
                }
            
            # Check vector DB for similar loads
            vector_db_source = None
            if self.vector_db:
                similar = self.vector_db.get_component_recommendations(
                    f"Cable breaker {load.current_a}A {load.voltage}V {getattr(load, 'load_type', 'general')}"
                )
                if similar:
                    vector_db_source = similar[0].get('component_id', 'vector_db')
            
            # Build reasoning
            reasoning = self._build_suggestion_reasoning(load, cable_suggestions, breaker_suggestions)
            
            suggestion = EquipmentConfigSuggestion(
                load_id=load.load_id,
                suggestion_id=suggestion_id,
                suggestion_type="combination",
                cable_suggestions=cable_suggestions,
                breaker_suggestions=breaker_suggestions,
                starter_suggestion=starter_suggestion,
                reasoning=reasoning,
                confidence=0.85,
                vector_db_source=vector_db_source
            )
            
            suggestions.append(suggestion)
            
            # Add alternatives if available
            if len(cable_suggestions) > 1 or len(breaker_suggestions) > 1:
                alt_suggestion = EquipmentConfigSuggestion(
                    load_id=load.load_id,
                    suggestion_id=f"alt_{suggestion_id}",
                    suggestion_type="combination",
                    cable_suggestions=cable_suggestions[1:2],
                    breaker_suggestions=breaker_suggestions[1:2] if len(breaker_suggestions) > 1 else breaker_suggestions,
                    starter_suggestion=starter_suggestion,
                    reasoning="Alternative configuration with different specifications",
                    confidence=0.75
                )
                suggestions.append(alt_suggestion)
        
        except Exception as e:
            logger.error(f"Failed to suggest equipment for load {load.load_id}: {e}")
        
        return suggestions
    
    def _suggest_bus_configuration(self, bus: Bus, project: Project) -> Optional[BusConfigSuggestion]:
        """Generate bus/panel configuration suggestion"""
        try:
            # Calculate current loading
            bus.calculate_total_load(project.loads)
            total_load_kw = bus.total_load_kw or 0
            
            if total_load_kw <= 0:
                return None
            
            # Get connected load currents (simplified)
            total_current_a = 0
            for load_id in bus.connected_loads:
                load = project.get_load_by_id(load_id)
                if load and load.current_a:
                    total_current_a += load.current_a
            
            current_util = (total_current_a / bus.rated_current_a * 100) if bus.rated_current_a else 0
            
            # Recommend short circuit rating
            recommended_sc_ka = bus.short_circuit_rating_ka or 25
            if current_util > 80:
                recommended_sc_ka = 50
            
            # Recommend main breaker
            recommended_breaker = total_current_a * 1.5
            
            recommendations = []
            if current_util > 80:
                recommendations.append(f"Bus is {current_util:.0f}% utilized. Consider upgrading capacity.")
            if current_util < 30:
                recommendations.append(f"Bus is underutilized at {current_util:.0f}%. May be oversized for current needs.")
            
            return BusConfigSuggestion(
                bus_id=bus.bus_id,
                suggestion_id=f"bus_{bus.bus_id}_{datetime.now().timestamp()}",
                recommended_short_circuit_rating_ka=recommended_sc_ka,
                recommended_main_breaker_rating_a=recommended_breaker,
                recommendations=recommendations,
                current_utilization_percent=current_util,
                projected_utilization_percent=current_util,
                headroom_percentage=100 - current_util,
                confidence=0.8
            )
        
        except Exception as e:
            logger.error(f"Failed to suggest bus configuration: {e}")
            return None
    
    def _suggest_transformer_configurations(self, project: Project) -> List[TransformerConfigSuggestion]:
        """Generate transformer configuration suggestions"""
        suggestions = []
        
        try:
            # Calculate total system load
            total_kw = sum(l.power_kw for l in project.loads if l.power_kw)
            total_kvar = total_kw * 0.5  # Assume 0.9 PF = 0.5 kvar per kw
            
            if total_kw > 0:
                # Get transformer suggestions
                transformer_suggestions = self.equipment_suggester.suggest_transformer(
                    total_kw, total_kvar,
                    primary_voltage=next((l.voltage for l in project.loads), 400),
                    secondary_voltage=next((l.voltage for l in project.loads), 400),
                    use_ai=True
                )
                
                for idx, ts in enumerate(transformer_suggestions):
                    suggestion = TransformerConfigSuggestion(
                        transformer_id=project.transformers[idx].transformer_id if idx < len(project.transformers) else None,
                        suggestion_id=f"transformer_{idx}_{datetime.now().timestamp()}",
                        kva_rating=ts.kva_rating,
                        primary_voltage=ts.primary_voltage,
                        secondary_voltage=ts.secondary_voltage,
                        connection_type=ts.connection_type,
                        cooling_type=ts.cooling_type,
                        reasoning=ts.reasoning,
                        confidence=ts.confidence,
                        utilization_percent=(total_kw / ts.kva_rating * 100) if ts.kva_rating else 0
                    )
                    suggestions.append(suggestion)
        
        except Exception as e:
            logger.warning(f"Failed to suggest transformer configurations: {e}")
        
        return suggestions
    
    def _calculate_optimization_potential(self, suggestion_set: SuggestionSet) -> float:
        """Calculate overall optimization potential percentage"""
        try:
            # Count suggestions available
            total_suggestions = sum(len(s) for s in suggestion_set.load_suggestions.values())
            total_insights = len(suggestion_set.insights)
            
            # Weight by confidence and priority
            potential = 0.0
            for insight in suggestion_set.insights:
                weight = {"critical": 0.3, "high": 0.2, "medium": 0.1, "low": 0.05}
                potential += weight.get(insight.priority, 0.1) * insight.confidence
            
            for suggestions_list in suggestion_set.load_suggestions.values():
                for sugg in suggestions_list:
                    potential += sugg.confidence * 0.1
            
            return min(potential * 10, 100.0)
        
        except Exception:
            return 0.0
    
    def _build_suggestion_reasoning(self, load: Load, cable_sugg, breaker_sugg) -> str:
        """Build reasoning string for suggestion"""
        reasons = []
        
        if load.current_a:
            reasons.append(f"Load current: {load.current_a:.1f}A")
        
        if cable_sugg:
            reasons.append(f"Cable: {cable_sugg[0].size_sqmm}mm² {cable_sugg[0].material}")
        
        if breaker_sugg:
            reasons.append(f"Breaker: {breaker_sugg[0].rating_a}A {breaker_sugg[0].type}")
        
        if load.power_kw and load.power_kw > 3:
            reasons.append("Motor starter recommended for inrush protection")
        
        return " | ".join(reasons)
    
    def _get_llm_insights(self, project: Project) -> List[ProjectInsight]:
        """Get AI insights from LLM"""
        insights = []
        
        try:
            if not self.llm:
                return insights
            
            prompt = f"""Analyze this electrical project and provide key insights:
            Project: {project.project_name}
            Loads: {len(project.loads)}
            Total Power: {sum(l.power_kw for l in project.loads if l.power_kw):.1f}kW
            Buses: {len(project.buses)}
            Transformers: {len(project.transformers)}
            
            Provide 2-3 key insights for optimization, efficiency, or safety concerns."""
            
            response = self.llm.process_text(prompt)
            if response and response.get("success"):
                # Parse response into insights (simplified)
                insights.append(ProjectInsight(
                    insight_type="optimization",
                    title="AI Analysis Complete",
                    description=response.get("content", "")[:200],
                    priority="medium",
                    confidence=0.7
                ))
        
        except Exception as e:
            logger.warning(f"Failed to get LLM insights: {e}")
        
        return insights
    
    def _find_similar_project_patterns(self, project: Project) -> List[Dict[str, Any]]:
        """Find similar project patterns in vector DB"""
        patterns = []
        
        try:
            if not self.vector_db:
                return patterns
            
            query = f"Project {len(project.loads)} loads {sum(l.power_kw for l in project.loads if l.power_kw):.0f}kW"
            similar_designs = self.vector_db.search_design_history(query, top_k=2)
            
            for design in similar_designs:
                patterns.append({
                    "name": design.get("design_id", "unknown"),
                    "description": f"Similar project with {design.get('components_count', 0)} components",
                    "confidence": design.get("similarity_score", 0.7)
                })
        
        except Exception as e:
            logger.warning(f"Failed to find patterns: {e}")
        
        return patterns
