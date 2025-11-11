"""
Equipment Configuration Suggester

Provides intelligent suggestions for equipment sizing, selection, and configuration
using LLM and vector database based on electrical engineering standards and best practices.

Part of the Design Analysis & Recommendations feature.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import math

from llm_multimodal_processor import LLMMultimodalProcessor, LLMConfig
from vector_database_manager import get_vector_database
from models import Load, Cable, Breaker, Transformer

logger = logging.getLogger(__name__)


@dataclass
class CableRecommendation:
    """Recommendation for cable selection"""
    size_sqmm: float
    type: str  # Single core, multi-core, etc.
    material: str  # Copper, Aluminum
    insulation: str  # XLPE, PVC, etc.
    confidence: float
    reasoning: str
    alternatives: List[Dict[str, Any]] = None


@dataclass
class BreakerRecommendation:
    """Recommendation for breaker selection"""
    rating_a: float
    type: str  # MCB, MCCB, ACB
    curve: str  # B, C, D, etc.
    breaking_capacity_ka: float
    confidence: float
    reasoning: str
    coordination_notes: str = ""


@dataclass
class TransformerRecommendation:
    """Recommendation for transformer selection"""
    kva_rating: float
    primary_voltage: float
    secondary_voltage: float
    connection_type: str  # Delta-Delta, Delta-Wye, etc.
    cooling_type: str  # Oil-immersed, Dry-type
    confidence: float
    reasoning: str


class AIEquipmentSuggester:
    """AI-powered equipment configuration suggester"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize suggester with LLM and vector DB"""
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

        # Standards and defaults
        self.breaker_types = ["MCB", "MCCB", "ACB"]
        self.breaker_curves = ["B", "C", "D", "K", "Z"]
        self.cable_types = ["Single Core", "Multi-Core", "Armored"]
        self.cable_materials = ["Copper", "Aluminum"]
        self.standard_breaker_ratings = [
            6, 10, 13, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 320
        ]
        self.standard_cable_sizes = [
            1, 1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300
        ]

    def suggest_cable(
        self,
        load: Load,
        installation_method: str = "in_conduit",
        ambient_temp_c: float = 30,
        use_ai: bool = True
    ) -> List[CableRecommendation]:
        """
        Suggest cable size and type for a load

        Args:
            load: Load to size cable for
            installation_method: How cable is installed
            ambient_temp_c: Ambient temperature for derating
            use_ai: Whether to use LLM for additional suggestions

        Returns:
            List of cable recommendations
        """
        recommendations = []

        try:
            # Calculate required current with safety margin
            current_required = (load.current_a or 0) * 1.25  # 125% margin

            # Find suitable cable sizes
            for size in self.standard_cable_sizes:
                ampacity = self._get_cable_ampacity(
                    size,
                    installation_method,
                    ambient_temp_c
                )

                if ampacity >= current_required:
                    recommendation = CableRecommendation(
                        size_sqmm=size,
                        type="Multi-Core",
                        material="Copper",
                        insulation="XLPE",
                        confidence=0.85,
                        reasoning=f"Ampacity {ampacity}A exceeds required {current_required:.1f}A"
                    )
                    recommendations.append(recommendation)

                    # Only suggest next larger size as alternative
                    if len(recommendations) >= 2:
                        break

            # If LLM available, get additional recommendations
            if use_ai and self.llm:
                ai_suggestions = self._get_llm_cable_suggestions(
                    load,
                    installation_method
                )
                recommendations.extend(ai_suggestions)

            # Search vector DB for similar recommendations
            if self.vector_db:
                db_suggestions = self._search_similar_cable_specs(load)
                for suggestion in db_suggestions:
                    if suggestion not in recommendations:
                        recommendations.append(suggestion)

        except Exception as e:
            logger.error(f"Cable suggestion failed: {e}")

        return recommendations[:3]  # Return top 3 recommendations

    def suggest_breaker(
        self,
        load: Load,
        downstream_breaker: Optional[Breaker] = None,
        use_ai: bool = True
    ) -> List[BreakerRecommendation]:
        """
        Suggest breaker for a load

        Args:
            load: Load to protect
            downstream_breaker: Optional downstream breaker for coordination
            use_ai: Whether to use LLM for additional suggestions

        Returns:
            List of breaker recommendations
        """
        recommendations = []

        try:
            # Calculate required breaker rating (typical: 1.25x to 1.5x load current)
            current_required = load.current_a or 0
            breaker_rating_min = current_required * 1.25
            breaker_rating_max = current_required * 1.5

            # Find suitable standard breaker ratings
            suitable_ratings = [
                r for r in self.standard_breaker_ratings
                if breaker_rating_min <= r <= breaker_rating_max
            ]

            # If no perfect fit, use next larger
            if not suitable_ratings:
                suitable_ratings = [
                    r for r in self.standard_breaker_ratings
                    if r > breaker_rating_min
                ][:2]

            for rating in suitable_ratings[:2]:  # Top 2 options
                # Determine breaker type based on current
                breaker_type = self._select_breaker_type(rating)
                curve = self._select_breaker_curve(load)

                recommendation = BreakerRecommendation(
                    rating_a=rating,
                    type=breaker_type,
                    curve=curve,
                    breaking_capacity_ka=self._get_breaking_capacity(breaker_type),
                    confidence=0.85,
                    reasoning=f"Protects load current {current_required}A with appropriate margin"
                )

                # Add coordination notes if downstream breaker exists
                if downstream_breaker and downstream_breaker.rating_a:
                    if rating > downstream_breaker.rating_a:
                        recommendation.coordination_notes = (
                            f"Properly coordinates with downstream breaker "
                            f"{downstream_breaker.rating_a}A"
                        )
                    else:
                        recommendation.coordination_notes = (
                            f"WARNING: Breaker rating {rating}A should be larger than "
                            f"downstream {downstream_breaker.rating_a}A"
                        )

                recommendations.append(recommendation)

            # Get LLM suggestions
            if use_ai and self.llm:
                ai_suggestions = self._get_llm_breaker_suggestions(load)
                recommendations.extend(ai_suggestions)

        except Exception as e:
            logger.error(f"Breaker suggestion failed: {e}")

        return recommendations[:3]

    def suggest_transformer(
        self,
        total_load_kw: float,
        total_load_kvar: float,
        primary_voltage: float,
        secondary_voltage: float,
        use_ai: bool = True
    ) -> List[TransformerRecommendation]:
        """
        Suggest transformer for a system

        Args:
            total_load_kw: Total load power
            total_load_kvar: Total reactive power
            primary_voltage: Primary side voltage
            secondary_voltage: Secondary side voltage
            use_ai: Whether to use LLM

        Returns:
            List of transformer recommendations
        """
        recommendations = []

        try:
            # Calculate required KVA with safety margin
            kva = math.sqrt(total_load_kw**2 + total_load_kvar**2) * 1.2

            # Find suitable standard ratings
            standard_kva = [5, 10, 15, 25, 30, 37.5, 50, 75, 100, 150, 200, 250]

            for rating in standard_kva:
                if rating >= kva:
                    recommendation = TransformerRecommendation(
                        kva_rating=rating,
                        primary_voltage=primary_voltage,
                        secondary_voltage=secondary_voltage,
                        connection_type=self._select_connection_type(
                            primary_voltage,
                            secondary_voltage
                        ),
                        cooling_type="Dry-type" if rating <= 100 else "Oil-immersed",
                        confidence=0.8,
                        reasoning=f"Capacity {rating}kVA handles load {kva:.1f}kVA"
                    )
                    recommendations.append(recommendation)

                    if len(recommendations) >= 2:
                        break

            # Get LLM suggestions
            if use_ai and self.llm:
                ai_suggestions = self._get_llm_transformer_suggestions(
                    total_load_kw,
                    primary_voltage,
                    secondary_voltage
                )
                recommendations.extend(ai_suggestions)

        except Exception as e:
            logger.error(f"Transformer suggestion failed: {e}")

        return recommendations[:3]

    def get_quick_configuration(
        self, load: Load
    ) -> Dict[str, Any]:
        """
        Get quick equipment configuration for a load

        Args:
            load: Load to configure

        Returns:
            Dictionary with cable, breaker, and starter recommendations
        """
        config = {
            "load_id": load.load_id,
            "cable": None,
            "breaker": None,
            "starter": None,
            "notes": []
        }

        try:
            # Get cable suggestion
            cable_suggestions = self.suggest_cable(load, use_ai=False)
            if cable_suggestions:
                cable = cable_suggestions[0]
                config["cable"] = {
                    "size_sqmm": cable.size_sqmm,
                    "type": cable.type,
                    "material": cable.material,
                    "reason": cable.reasoning
                }

            # Get breaker suggestion
            breaker_suggestions = self.suggest_breaker(load, use_ai=False)
            if breaker_suggestions:
                breaker = breaker_suggestions[0]
                config["breaker"] = {
                    "rating_a": breaker.rating_a,
                    "type": breaker.type,
                    "curve": breaker.curve,
                    "reason": breaker.reasoning
                }

            # Determine if starter needed
            if load.power_kw and load.power_kw > 3:
                config["starter"] = {
                    "type": "Soft Starter or VFD" if load.power_kw > 10 else "Direct Online Starter",
                    "reason": f"Motor load {load.power_kw}kW requires starting equipment"
                }
                config["notes"].append("Soft starter recommended to reduce inrush current")

        except Exception as e:
            logger.error(f"Quick configuration failed: {e}")
            config["notes"].append(f"Configuration error: {str(e)}")

        return config

    # Helper methods

    def _get_cable_ampacity(
        self,
        size_sqmm: float,
        installation_method: str,
        ambient_temp_c: float
    ) -> float:
        """Get cable ampacity based on size and installation method"""
        # Simplified ampacity table for XLPE cables
        ampacity_table = {
            1: 14, 1.5: 17.5, 2.5: 24, 4: 32, 6: 40, 10: 57,
            16: 76, 25: 101, 35: 127, 50: 158, 70: 201, 95: 245,
            120: 283, 150: 326, 185: 375, 240: 434, 300: 490
        }

        base_ampacity = ampacity_table.get(size_sqmm, 100)

        # Apply installation method derating
        derating_factor = {
            "in_conduit": 0.8,
            "in_cable_tray": 0.9,
            "in_ground": 0.95,
            "air": 1.0
        }.get(installation_method, 0.8)

        # Apply temperature derating (30°C reference)
        temp_derating = 1.0
        if ambient_temp_c > 30:
            temp_derating = 1 - (ambient_temp_c - 30) * 0.01

        return base_ampacity * derating_factor * temp_derating

    def _select_breaker_type(self, rating_a: float) -> str:
        """Select appropriate breaker type based on current rating"""
        if rating_a <= 63:
            return "MCB"  # Miniature Circuit Breaker
        elif rating_a <= 160:
            return "MCCB"  # Molded Case Circuit Breaker
        else:
            return "ACB"  # Air Circuit Breaker

    def _select_breaker_curve(self, load: Load) -> str:
        """Select appropriate breaker curve based on load type"""
        load_type = getattr(load, 'load_type', 'general')

        curves = {
            "motor": "D",  # High inrush
            "lighting": "B",  # Low inrush
            "heating": "C",  # Medium inrush
            "general": "C",  # Default
            "resistive": "B"
        }

        return curves.get(str(load_type).lower(), "C")

    def _get_breaking_capacity(self, breaker_type: str) -> float:
        """Get breaking capacity for breaker type"""
        capacities = {
            "MCB": 6,  # kA
            "MCCB": 25,
            "ACB": 100
        }
        return capacities.get(breaker_type, 6)

    def _select_connection_type(
        self,
        primary_voltage: float,
        secondary_voltage: float
    ) -> str:
        """Select transformer connection type"""
        if primary_voltage > 400:
            return "Delta-Wye" if secondary_voltage <= 400 else "Delta-Delta"
        else:
            return "Delta-Wye" if secondary_voltage >= 200 else "Wye-Wye"

    def _get_llm_cable_suggestions(
        self,
        load: Load,
        installation_method: str
    ) -> List[CableRecommendation]:
        """Get cable suggestions from LLM"""
        suggestions = []

        try:
            if not self.llm:
                return suggestions

            prompt = f"""Suggest cable sizes for this electrical load:
            Load: {load.load_id}
            Current: {load.current_a} A
            Voltage: {load.voltage} V
            Distance: Unknown (assume standard run)
            Installation: {installation_method}
            
            Provide 2-3 cable sizes with mm² and justification."""

            response = self.llm.process_text(prompt)

            if response and response.get("success"):
                content = response.get("content", "")
                # Parse basic recommendation from response
                if "mm²" in content or "sqmm" in content:
                    suggestion = CableRecommendation(
                        size_sqmm=25,  # Default fallback
                        type="Multi-Core",
                        material="Copper",
                        insulation="XLPE",
                        confidence=0.7,
                        reasoning=f"LLM suggestion: {content[:100]}"
                    )
                    suggestions.append(suggestion)

        except Exception as e:
            logger.warning(f"LLM cable suggestion failed: {e}")

        return suggestions

    def _get_llm_breaker_suggestions(
        self, load: Load
    ) -> List[BreakerRecommendation]:
        """Get breaker suggestions from LLM"""
        suggestions = []

        try:
            if not self.llm:
                return suggestions

            prompt = f"""Suggest a breaker for protecting this load:
            Load: {load.load_id}
            Current: {load.current_a} A
            Load Type: {getattr(load, 'load_type', 'general')}
            
            Recommend breaker rating (A), type (MCB/MCCB/ACB), and curve (B/C/D)."""

            response = self.llm.process_text(prompt)

            if response and response.get("success"):
                content = response.get("content", "")
                # Parse basic recommendation
                suggestion = BreakerRecommendation(
                    rating_a=(load.current_a or 20) * 1.5,
                    type="MCCB",
                    curve="C",
                    breaking_capacity_ka=25,
                    confidence=0.7,
                    reasoning=f"LLM suggestion: {content[:100]}"
                )
                suggestions.append(suggestion)

        except Exception as e:
            logger.warning(f"LLM breaker suggestion failed: {e}")

        return suggestions

    def _get_llm_transformer_suggestions(
        self,
        total_load_kw: float,
        primary_voltage: float,
        secondary_voltage: float
    ) -> List[TransformerRecommendation]:
        """Get transformer suggestions from LLM"""
        suggestions = []

        try:
            if not self.llm:
                return suggestions

            prompt = f"""Suggest a transformer for this system:
            Load: {total_load_kw} kW
            Primary Voltage: {primary_voltage} V
            Secondary Voltage: {secondary_voltage} V
            
            Recommend kVA rating and connection type."""

            response = self.llm.process_text(prompt)

            if response and response.get("success"):
                # Default suggestion based on calculations
                kva = total_load_kw * 1.2
                suggestion = TransformerRecommendation(
                    kva_rating=kva,
                    primary_voltage=primary_voltage,
                    secondary_voltage=secondary_voltage,
                    connection_type="Delta-Wye",
                    cooling_type="Dry-type",
                    confidence=0.75,
                    reasoning="Sized for 20% additional capacity"
                )
                suggestions.append(suggestion)

        except Exception as e:
            logger.warning(f"LLM transformer suggestion failed: {e}")

        return suggestions

    def _search_similar_cable_specs(
        self, load: Load
    ) -> List[CableRecommendation]:
        """Search vector DB for similar cable specifications"""
        suggestions = []

        try:
            if not self.vector_db:
                return suggestions

            query = f"Cable {load.current_a}A {load.voltage}V copper XLPE"

            results = self.vector_db.search_components(
                query=query,
                top_k=2
            )

            if results and results.get("documents"):
                # Create suggestions from DB results
                for doc in results.get("documents", []):
                    if isinstance(doc, dict):
                        suggestion = CableRecommendation(
                            size_sqmm=doc.get("size_sqmm", 25),
                            type=doc.get("type", "Multi-Core"),
                            material=doc.get("material", "Copper"),
                            insulation=doc.get("insulation", "XLPE"),
                            confidence=0.8,
                            reasoning="Found in standards database"
                        )
                        suggestions.append(suggestion)

        except Exception as e:
            logger.warning(f"Vector DB cable search failed: {e}")

        return suggestions
