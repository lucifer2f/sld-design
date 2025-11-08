"""
Design Analysis Module

Provides intelligent design validation, recommendations, and standards checking
using LLM and vector database capabilities for electrical system designs.

Part of the Design Analysis & Recommendations feature.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json

from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig
from vector_database_manager import VectorDatabaseManager, get_vector_database
from models import Project, Load, Cable, Breaker, Transformer

logger = logging.getLogger(__name__)


@dataclass
class DesignAnalysis:
    """Results from AI design analysis"""
    overall_score: float  # 0-100
    validation_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    standards_compliance: Dict[str, bool] = field(default_factory=dict)
    design_patterns_matched: List[str] = field(default_factory=list)
    safety_concerns: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)


@dataclass
class EquipmentSuggestion:
    """AI-generated equipment suggestion"""
    equipment_type: str
    suggested_values: Dict[str, Any]
    confidence: float  # 0-1
    reasoning: str
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


class AIDesignAnalyzer:
    """AI-powered design analysis using LLM and vector database"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize analyzer with LLM and vector DB"""
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

    def analyze_design(self, project: Project) -> DesignAnalysis:
        """
        Comprehensive AI analysis of electrical design

        Args:
            project: Project to analyze

        Returns:
            DesignAnalysis with findings and recommendations
        """
        if not isinstance(project, Project):
            raise TypeError("Input must be a Project instance")
        
        analysis = DesignAnalysis(overall_score=75.0)

        try:
            # Validate loads
            analysis.validation_issues.extend(self._validate_loads(project.loads))

            # Check standards compliance
            analysis.standards_compliance = self._check_standards_compliance(
                project
            )

            # Get design pattern recommendations
            if self.vector_db:
                analysis.design_patterns_matched = (
                    self._find_design_patterns(project)
                )

            # Identify safety concerns
            analysis.safety_concerns = self._identify_safety_concerns(project)

            # Get optimization suggestions
            if self.llm:
                analysis.recommendations = self._get_ai_recommendations(project)

            # Calculate overall score
            analysis.overall_score = self._calculate_design_score(analysis)

        except Exception as e:
            logger.error(f"Design analysis failed: {e}")
            analysis.warnings.append(f"Analysis error: {str(e)}")

        return analysis

    def suggest_equipment(
        self, load: Load, context: Optional[Project] = None
    ) -> List[EquipmentSuggestion]:
        """
        Get AI suggestions for equipment sizing

        Args:
            load: Load to get suggestions for
            context: Optional project context

        Returns:
            List of equipment suggestions
        """
        suggestions = []

        try:
            # Search vector DB for similar loads
            if self.vector_db:
                similar_specs = self._find_similar_component_specs(load)
                for spec in similar_specs:
                    suggestion = self._create_suggestion_from_spec(
                        load, spec
                    )
                    if suggestion:
                        suggestions.append(suggestion)

            # If LLM available, get additional recommendations
            if self.llm:
                llm_suggestions = self._get_llm_equipment_suggestions(load)
                suggestions.extend(llm_suggestions)

        except Exception as e:
            logger.error(f"Equipment suggestion failed: {e}")

        return suggestions

    def validate_cable_selection(self, cable: Cable, load: Load) -> Dict[str, Any]:
        """
        Validate cable selection using standards and LLM

        Args:
            cable: Cable to validate
            load: Load the cable serves

        Returns:
            Validation results
        """
        result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "recommendations": []
        }

        try:
            # Check ampacity
            if cable.ampacity_a and load.current_a:
                if cable.ampacity_a < load.current_a * 1.25:  # 125% safety margin
                    result["issues"].append(
                        f"Cable ampacity ({cable.ampacity_a}A) insufficient for load current "
                        f"({load.current_a}A with margin)"
                    )
                    result["is_valid"] = False

            # Check voltage drop
            if cable.resistance_ohm_per_km and load.current_a:
                voltage_drop_pct = (
                    (cable.resistance_ohm_per_km * load.current_a * 2)
                    / (load.voltage * 10)
                )
                if voltage_drop_pct > 3:
                    result["warnings"].append(
                        f"Voltage drop ({voltage_drop_pct:.1f}%) exceeds 3% limit"
                    )

            # Use vector DB for standards compliance
            if self.vector_db:
                compliance = self._check_cable_standards(cable)
                result.update(compliance)

            # Use LLM for detailed analysis
            if self.llm:
                llm_analysis = self._get_llm_cable_analysis(cable, load)
                if llm_analysis:
                    result["recommendations"].extend(
                        llm_analysis.get("recommendations", [])
                    )

        except Exception as e:
            logger.error(f"Cable validation failed: {e}")
            result["warnings"].append(f"Validation error: {str(e)}")

        return result

    def validate_breaker_coordination(self, project: Project) -> Dict[str, Any]:
        """
        Validate breaker coordination using standards

        Args:
            project: Project with breakers to validate

        Returns:
            Coordination validation results
        """
        result = {
            "is_coordinated": True,
            "issues": [],
            "warnings": [],
            "recommendations": []
        }

        try:
            if not project.breakers:
                return result

            # Check cascade coordination
            sorted_breakers = sorted(
                project.breakers,
                key=lambda b: b.rating_a or 0,
                reverse=True
            )

            for i, upstream_breaker in enumerate(sorted_breakers):
                for downstream_breaker in sorted_breakers[i + 1:]:
                    if (
                        upstream_breaker.rating_a
                        and downstream_breaker.rating_a
                        and upstream_breaker.rating_a <= downstream_breaker.rating_a
                    ):
                        result["issues"].append(
                            f"Breaker coordination issue: "
                            f"{upstream_breaker.breaker_id} "
                            f"({upstream_breaker.rating_a}A) should be larger "
                            f"than {downstream_breaker.breaker_id}"
                        )
                        result["is_coordinated"] = False

            # Use LLM for selective coordination analysis
            if self.llm:
                coordination = self._get_llm_coordination_analysis(project)
                if coordination:
                    result["recommendations"].extend(
                        coordination.get("recommendations", [])
                    )

        except Exception as e:
            logger.error(f"Breaker coordination validation failed: {e}")
            result["warnings"].append(f"Validation error: {str(e)}")

        return result

    # Helper methods

    def _validate_loads(self, loads: List[Load]) -> List[str]:
        """Validate load parameters"""
        issues = []
        for load in loads:
            if load.power_kw and load.power_kw <= 0:
                issues.append(f"Load {load.load_id}: Power must be positive")
            if load.voltage and load.voltage <= 0:
                issues.append(f"Load {load.load_id}: Voltage must be positive")
            if load.power_factor and (load.power_factor < 0.6 or load.power_factor > 1):
                issues.append(
                    f"Load {load.load_id}: Power factor must be between 0.6 and 1"
                )
        return issues

    def _check_standards_compliance(self, project: Project) -> Dict[str, bool]:
        """Check compliance with electrical standards"""
        compliance = {
            "voltage_ratings": True,
            "cable_sizing": True,
            "breaker_selection": True,
            "grounding": True,
            "protection": True
        }

        try:
            if self.vector_db:
                # Search for standards in vector DB
                standards_results = self.vector_db.search(
                    collection_name="standards",
                    query="electrical design standards voltage breaker cable",
                    n_results=5
                )

                # Perform basic checks
                for load in project.loads:
                    if load.voltage not in [120, 208, 240, 277, 347, 480, 600]:
                        compliance["voltage_ratings"] = False

        except Exception as e:
            logger.warning(f"Standards check failed: {e}")

        return compliance

    def _find_design_patterns(self, project: Project) -> List[str]:
        """Find matching design patterns in vector DB"""
        patterns = []

        try:
            if not self.vector_db:
                return patterns

            project_summary = f"Project with {len(project.loads)} loads, voltage {project.loads[0].voltage if project.loads else 'unknown'}V"

            results = self.vector_db.search(
                collection_name="design_patterns",
                query=project_summary,
                n_results=3
            )

            if results and results.get("documents"):
                patterns = results["documents"][0] if results["documents"] else []

        except Exception as e:
            logger.warning(f"Design pattern search failed: {e}")

        return patterns

    def _identify_safety_concerns(self, project: Project) -> List[str]:
        """Identify safety concerns in design"""
        concerns = []

        # Check for ground faults
        if project.loads:
            for load in project.loads:
                if not load.breaker_rating_a:
                    concerns.append(f"Load {load.load_id}: No breaker configured")

        # Check for overcurrent protection
        for breaker in project.breakers:
            if not breaker.rating_a:
                concerns.append(f"Breaker {breaker.breaker_id}: No rating specified")

        return concerns

    def _get_ai_recommendations(self, project: Project) -> List[str]:
        """Get AI recommendations using LLM"""
        recommendations = []

        try:
            if not self.llm:
                return recommendations

            prompt = self._build_design_analysis_prompt(project)
            
            # Get LLM analysis
            response = self.llm.process_text(prompt)
            
            if response and response.get("success"):
                content = response.get("content", "")
                recommendations = self._parse_recommendations(content)

        except Exception as e:
            logger.warning(f"AI recommendations failed: {e}")

        return recommendations

    def _get_llm_equipment_suggestions(
        self, load: Load
    ) -> List[EquipmentSuggestion]:
        """Get equipment suggestions from LLM"""
        suggestions = []

        try:
            if not self.llm:
                return suggestions

            prompt = f"""Based on this electrical load, suggest appropriate equipment:
            Load ID: {load.load_id}
            Power: {load.power_kw} kW
            Voltage: {load.voltage} V
            Current: {load.current_a} A
            Duty Cycle: {load.duty_cycle if hasattr(load, 'duty_cycle') else 'Unknown'}
            
            Provide suggestions for:
            1. Cable size (mm²)
            2. Breaker rating (A)
            3. Starter type if applicable
            
            Format as JSON."""

            response = self.llm.process_text(prompt)

            if response and response.get("success"):
                content = response.get("content", "")
                try:
                    suggestions_data = json.loads(content)
                    for item in suggestions_data:
                        suggestion = EquipmentSuggestion(
                            equipment_type=item.get("type", "unknown"),
                            suggested_values=item.get("values", {}),
                            confidence=item.get("confidence", 0.7),
                            reasoning=item.get("reasoning", "")
                        )
                        suggestions.append(suggestion)
                except json.JSONDecodeError:
                    logger.warning("Could not parse LLM equipment suggestions")

        except Exception as e:
            logger.warning(f"LLM equipment suggestions failed: {e}")

        return suggestions

    def _get_llm_cable_analysis(
        self, cable: Cable, load: Load
    ) -> Optional[Dict[str, Any]]:
        """Get detailed cable analysis from LLM"""
        try:
            if not self.llm:
                return None

            prompt = f"""Analyze this cable selection for compatibility:
            Cable: {cable.cable_id}
            Size: {cable.size_sqmm} mm²
            Type: {cable.type}
            Ampacity: {cable.ampacity_a} A
            
            Load: {load.load_id}
            Current Required: {load.current_a} A
            Voltage: {load.voltage} V
            
            Provide analysis including any concerns and recommendations."""

            response = self.llm.process_text(prompt)

            if response and response.get("success"):
                # Parse response into structured format
                return {"recommendations": [response.get("content", "")]}

        except Exception as e:
            logger.warning(f"Cable analysis failed: {e}")

        return None

    def _get_llm_coordination_analysis(
        self, project: Project
    ) -> Optional[Dict[str, Any]]:
        """Get breaker coordination analysis from LLM"""
        try:
            if not self.llm:
                return None

            breaker_info = [
                f"{b.breaker_id}: {b.rating_a}A" for b in project.breakers
            ]

            prompt = f"""Analyze breaker coordination for this system:
            Breakers: {', '.join(breaker_info)}
            
            Check for:
            1. Proper cascade coordination
            2. Selective coordination
            3. Adequate time-current coordination
            
            Provide recommendations."""

            response = self.llm.process_text(prompt)

            if response and response.get("success"):
                return {"recommendations": [response.get("content", "")]}

        except Exception as e:
            logger.warning(f"Coordination analysis failed: {e}")

        return None

    def _find_similar_component_specs(self, load: Load) -> List[Dict[str, Any]]:
        """Find similar component specifications in vector DB"""
        specs = []

        try:
            if not self.vector_db:
                return specs

            query = f"Load {load.power_kw}kW {load.voltage}V {load.load_type if hasattr(load, 'load_type') else 'general'}"

            results = self.vector_db.search(
                collection_name="component_specs",
                query=query,
                n_results=3
            )

            if results and results.get("documents"):
                specs = results["documents"][0] if results["documents"] else []

        except Exception as e:
            logger.warning(f"Component spec search failed: {e}")

        return specs

    def _create_suggestion_from_spec(
        self, load: Load, spec: Dict[str, Any]
    ) -> Optional[EquipmentSuggestion]:
        """Create suggestion from vector DB spec"""
        try:
            return EquipmentSuggestion(
                equipment_type=spec.get("type", "component"),
                suggested_values=spec.get("values", {}),
                confidence=0.8,
                reasoning=spec.get("description", "Based on similar loads")
            )
        except Exception as e:
            logger.warning(f"Could not create suggestion: {e}")
            return None

    def _check_cable_standards(self, cable: Cable) -> Dict[str, Any]:
        """Check cable against standards using vector DB"""
        result = {"standards_compliant": True, "warnings": []}

        try:
            if not self.vector_db:
                return result

            query = f"Cable {cable.type} {cable.size_sqmm}mm² {cable.voltage_rating}V"

            results = self.vector_db.search(
                collection_name="standards",
                query=query,
                n_results=1
            )

            # If no matches found, flag for review
            if not results or not results.get("documents"):
                result["warnings"].append("Cable type not found in standards database")

        except Exception as e:
            logger.warning(f"Cable standards check failed: {e}")

        return result

    def _build_design_analysis_prompt(self, project: Project) -> str:
        """Build LLM prompt for design analysis"""
        loads_summary = "\n".join(
            [
                f"- {l.load_id}: {l.power_kw}kW at {l.voltage}V, PF={l.power_factor}"
                for l in project.loads[:5]
            ]
        )

        return f"""Analyze this electrical design and provide recommendations:

Project: {project.project_id}
Total Loads: {len(project.loads)}

Loads:
{loads_summary}

Transformers: {len(project.transformers)}
Cables: {len(project.cables)}
Breakers: {len(project.breakers)}

Provide analysis for:
1. Load distribution balance
2. Potential bottlenecks
3. Cost optimization opportunities
4. Reliability improvements
5. Standards compliance

Format as a structured report."""

    def _parse_recommendations(self, content: str) -> List[str]:
        """Parse recommendations from LLM response"""
        recommendations = []
        
        try:
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Filter out short lines
                    recommendations.append(line)
        except Exception:
            if content:
                recommendations.append(content)
        
        return recommendations[:5]  # Limit to 5 recommendations

    def _calculate_design_score(self, analysis: DesignAnalysis) -> float:
        """Calculate overall design score"""
        score = 100.0

        # Deduct points for issues
        score -= len(analysis.validation_issues) * 10
        score -= len(analysis.safety_concerns) * 15
        score -= len(analysis.warnings) * 3

        # Add points for pattern matches and compliance
        score += len(analysis.design_patterns_matched) * 5

        # Count compliance failures
        compliance_failures = sum(
            1 for v in analysis.standards_compliance.values() if not v
        )
        score -= compliance_failures * 10

        return max(0, min(100, score))
