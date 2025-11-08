"""
Electrical Design Automation System - Source Package

This package contains the core modules for the Electrical Design Automation System.
"""

from models import Project, Load, Bus, Transformer, Cable, Breaker, LoadType, InstallationMethod, DutyCycle, Priority
from calculations import ElectricalCalculationEngine
from standards import StandardsFactory
from unified_processor import UnifiedDataProcessor, ProcessingInterface, create_unified_processor, initialize_processing_status, get_processing_status, ProcessingStatus
from ai_design_analyzer import AIDesignAnalyzer, DesignAnalysis
from ai_equipment_suggester import AIEquipmentSuggester

__version__ = "1.0.0"
__author__ = "EDA System Team"