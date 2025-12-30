"""
Data models for Hydrant Network Calculator
Pydantic models for nodes, edges, and network configuration
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Literal
from enum import Enum


class NodeType(str, Enum):
    SOURCE = "source"
    JUNCTION = "junction"
    HYDRANT = "hydrant"


class Node(BaseModel):
    """
    Represents a node in the hydrant network.
    Can be a source (pump/reservoir), junction, or hydrant (demand point).
    """
    node_id: str = Field(..., description="Unique identifier for the node")
    type: NodeType = Field(..., description="Type of node: source, junction, or hydrant")
    elevation_m: float = Field(default=0.0, description="Node elevation in meters")
    demand_lpm: float = Field(default=0.0, ge=0, description="Water demand in L/min (for hydrants)")
    is_active: bool = Field(default=True, description="Whether the hydrant is active (for demand scenarios)")

    @field_validator('demand_lpm')
    @classmethod
    def validate_demand(cls, v, info):
        if v < 0:
            raise ValueError("Demand cannot be negative")
        return v


class MinorLossComponent(BaseModel):
    """Individual minor loss component (valve, elbow, tee, etc.)"""
    name: str = Field(..., description="Component name (e.g., 'gate_valve', 'elbow_90')")
    K: float = Field(..., ge=0, description="K factor for the component")


class Edge(BaseModel):
    """
    Represents a pipe segment connecting two nodes.
    Contains pipe properties and minor loss coefficients.
    """
    edge_id: str = Field(..., description="Unique identifier for the edge")
    from_node: str = Field(..., description="ID of upstream node")
    to_node: str = Field(..., description="ID of downstream node")
    length_m: float = Field(..., gt=0, description="Pipe length in meters")
    diameter_mm: float = Field(..., gt=0, description="Pipe internal diameter in mm")
    roughness_mm: float = Field(default=0.045, ge=0, description="Pipe roughness (epsilon) in mm")
    minor_K: float = Field(default=0.0, ge=0, description="Total minor loss coefficient K")
    minor_components: Optional[List[MinorLossComponent]] = Field(
        default=None,
        description="List of minor loss components (alternative to minor_K)"
    )

    def get_total_K(self) -> float:
        """Calculate total K factor from components or use direct value"""
        if self.minor_components:
            return sum(comp.K for comp in self.minor_components)
        return self.minor_K


class FluidProperties(BaseModel):
    """Fluid properties (default: water at 20°C)"""
    density_kg_m3: float = Field(default=998.0, gt=0, description="Fluid density in kg/m³")
    viscosity_pa_s: float = Field(default=1.002e-3, gt=0, description="Dynamic viscosity in Pa·s")


class PressureUnit(str, Enum):
    BAR = "bar"
    KPA = "kPa"
    MPA = "MPa"


class NetworkInput(BaseModel):
    """
    Complete network configuration input for calculation.
    """
    nodes: List[Node] = Field(..., min_length=1, description="List of network nodes")
    edges: List[Edge] = Field(..., min_length=1, description="List of pipe segments")
    source_pressure_bar: float = Field(..., gt=0, description="Pressure at source node in bar")
    fluid: FluidProperties = Field(default_factory=FluidProperties, description="Fluid properties")
    include_elevation: bool = Field(default=True, description="Include elevation head in calculations")
    pressure_unit: PressureUnit = Field(default=PressureUnit.BAR, description="Output pressure unit")


# ===== Output Models =====

class SegmentResult(BaseModel):
    """Calculation results for a single pipe segment"""
    edge_id: str
    from_node: str
    to_node: str
    flow_lpm: float = Field(description="Flow rate in L/min")
    flow_m3s: float = Field(description="Flow rate in m³/s")
    velocity_ms: float = Field(description="Flow velocity in m/s")
    reynolds: float = Field(description="Reynolds number")
    friction_factor: float = Field(description="Darcy friction factor")
    delta_p_major_bar: float = Field(description="Major loss (friction) in bar")
    delta_p_minor_bar: float = Field(description="Minor losses in bar")
    delta_p_total_bar: float = Field(description="Total pressure drop in bar")
    flow_regime: str = Field(description="'laminar' or 'turbulent'")


class NodeResult(BaseModel):
    """Calculation results for a node"""
    node_id: str
    type: str
    elevation_m: float
    demand_lpm: float
    pressure_bar: float = Field(description="Pressure at node in bar")
    is_active: bool
    distance_from_source_m: float = Field(default=0.0, description="Cumulative distance from source")


class CriticalPath(BaseModel):
    """Information about the critical (most unfavorable) path"""
    path_nodes: List[str] = Field(description="Node IDs from source to critical hydrant")
    path_edges: List[str] = Field(description="Edge IDs along the critical path")
    total_length_m: float = Field(description="Total path length in meters")
    critical_hydrant: str = Field(description="Node ID of hydrant with lowest pressure")
    critical_pressure_bar: float = Field(description="Pressure at critical hydrant")


class CalculationResult(BaseModel):
    """Complete calculation results"""
    success: bool = Field(description="Whether calculation succeeded")
    message: str = Field(default="", description="Status or error message")
    segments: List[SegmentResult] = Field(default_factory=list, description="Results per pipe segment")
    nodes: List[NodeResult] = Field(default_factory=list, description="Results per node")
    critical_path: Optional[CriticalPath] = Field(default=None, description="Critical path information")
    total_demand_lpm: float = Field(default=0.0, description="Total system demand in L/min")
    warnings: List[str] = Field(default_factory=list, description="Calculation warnings")


# ===== Minor Loss K-factor Reference =====

MINOR_LOSS_K_FACTORS: Dict[str, float] = {
    # Valves
    "gate_valve_open": 0.2,
    "gate_valve_half": 5.6,
    "globe_valve_open": 10.0,
    "ball_valve_open": 0.05,
    "check_valve_swing": 2.5,
    "butterfly_valve_open": 0.3,

    # Elbows
    "elbow_90_standard": 0.9,
    "elbow_90_long_radius": 0.6,
    "elbow_45": 0.4,

    # Tees
    "tee_run": 0.3,
    "tee_branch": 1.0,

    # Reducers/Expanders
    "reducer_sudden": 0.5,
    "expander_sudden": 1.0,

    # Entries/Exits
    "entrance_sharp": 0.5,
    "entrance_rounded": 0.25,
    "exit": 1.0,

    # Hydrant
    "hydrant_outlet": 2.5,
}
