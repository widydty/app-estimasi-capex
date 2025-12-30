"""
Hydrant Network Calculator - Core Calculation Engine

Implements:
- Darcy-Weisbach equation for pressure drop
- Swamee-Jain equation for friction factor (turbulent)
- Laminar friction factor (Re < 2300)
- Tree network flow distribution
- Pressure profile calculation
"""

import math
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

try:
    from .models import (
        Node, Edge, NodeType, FluidProperties, NetworkInput,
        SegmentResult, NodeResult, CriticalPath, CalculationResult
    )
except ImportError:
    from models import (
        Node, Edge, NodeType, FluidProperties, NetworkInput,
        SegmentResult, NodeResult, CriticalPath, CalculationResult
    )


# Physical constants
GRAVITY = 9.81  # m/s²


def lpm_to_m3s(lpm: float) -> float:
    """Convert L/min to m³/s"""
    return lpm / 60000.0


def m3s_to_lpm(m3s: float) -> float:
    """Convert m³/s to L/min"""
    return m3s * 60000.0


def mm_to_m(mm: float) -> float:
    """Convert mm to m"""
    return mm / 1000.0


def pa_to_bar(pa: float) -> float:
    """Convert Pascal to bar"""
    return pa / 100000.0


def bar_to_pa(bar: float) -> float:
    """Convert bar to Pascal"""
    return bar * 100000.0


def calculate_reynolds(velocity: float, diameter_m: float,
                       density: float, viscosity: float) -> float:
    """
    Calculate Reynolds number

    Args:
        velocity: Flow velocity in m/s
        diameter_m: Pipe diameter in m
        density: Fluid density in kg/m³
        viscosity: Dynamic viscosity in Pa·s

    Returns:
        Reynolds number (dimensionless)
    """
    if velocity == 0 or diameter_m == 0:
        return 0.0
    return (density * velocity * diameter_m) / viscosity


def calculate_friction_factor_laminar(reynolds: float) -> float:
    """
    Laminar flow friction factor: f = 64/Re

    Args:
        reynolds: Reynolds number

    Returns:
        Darcy friction factor
    """
    if reynolds <= 0:
        return 0.0
    return 64.0 / reynolds


def calculate_friction_factor_swamee_jain(reynolds: float,
                                          roughness_m: float,
                                          diameter_m: float) -> float:
    """
    Swamee-Jain equation for turbulent flow friction factor

    f = 0.25 / [log10(ε/(3.7D) + 5.74/Re^0.9)]²

    Valid for: 5000 ≤ Re ≤ 10^8 and 10^-6 ≤ ε/D ≤ 10^-2

    Args:
        reynolds: Reynolds number
        roughness_m: Pipe roughness (epsilon) in m
        diameter_m: Pipe diameter in m

    Returns:
        Darcy friction factor
    """
    if reynolds <= 0 or diameter_m <= 0:
        return 0.0

    relative_roughness = roughness_m / diameter_m

    # Swamee-Jain equation
    term1 = relative_roughness / 3.7
    term2 = 5.74 / (reynolds ** 0.9)

    log_term = math.log10(term1 + term2)

    f = 0.25 / (log_term ** 2)

    return f


def calculate_friction_factor_colebrook(reynolds: float,
                                        roughness_m: float,
                                        diameter_m: float,
                                        tolerance: float = 1e-6,
                                        max_iterations: int = 50) -> float:
    """
    Colebrook-White equation (iterative) for friction factor

    1/√f = -2 log10(ε/(3.7D) + 2.51/(Re√f))

    Uses Newton-Raphson iteration starting from Swamee-Jain estimate.

    Args:
        reynolds: Reynolds number
        roughness_m: Pipe roughness in m
        diameter_m: Pipe diameter in m
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations

    Returns:
        Darcy friction factor
    """
    if reynolds <= 0 or diameter_m <= 0:
        return 0.0

    relative_roughness = roughness_m / diameter_m

    # Initial guess from Swamee-Jain
    f = calculate_friction_factor_swamee_jain(reynolds, roughness_m, diameter_m)

    for _ in range(max_iterations):
        sqrt_f = math.sqrt(f)

        # Colebrook equation: F(f) = 1/√f + 2log10(ε/(3.7D) + 2.51/(Re√f)) = 0
        term = relative_roughness / 3.7 + 2.51 / (reynolds * sqrt_f)
        F = 1.0 / sqrt_f + 2.0 * math.log10(term)

        # Derivative dF/df
        dF = -0.5 / (f * sqrt_f) - 2.51 / (reynolds * f * sqrt_f * term * math.log(10))

        # Newton-Raphson update
        f_new = f - F / dF

        if abs(f_new - f) < tolerance:
            return f_new

        f = f_new

    return f


def calculate_friction_factor(reynolds: float,
                              roughness_m: float,
                              diameter_m: float,
                              use_colebrook: bool = False) -> Tuple[float, str]:
    """
    Calculate Darcy friction factor based on flow regime

    Args:
        reynolds: Reynolds number
        roughness_m: Pipe roughness in m
        diameter_m: Pipe diameter in m
        use_colebrook: Use Colebrook instead of Swamee-Jain

    Returns:
        Tuple of (friction_factor, flow_regime)
    """
    if reynolds < 2300:
        # Laminar flow
        return calculate_friction_factor_laminar(reynolds), "laminar"
    else:
        # Turbulent flow
        if use_colebrook:
            f = calculate_friction_factor_colebrook(reynolds, roughness_m, diameter_m)
        else:
            f = calculate_friction_factor_swamee_jain(reynolds, roughness_m, diameter_m)
        return f, "turbulent"


def calculate_velocity(flow_m3s: float, diameter_m: float) -> float:
    """
    Calculate flow velocity from volumetric flow rate

    Args:
        flow_m3s: Flow rate in m³/s
        diameter_m: Pipe diameter in m

    Returns:
        Velocity in m/s
    """
    if diameter_m <= 0:
        return 0.0
    area = math.pi * (diameter_m / 2) ** 2
    return flow_m3s / area if area > 0 else 0.0


def calculate_major_loss(friction_factor: float,
                         length_m: float,
                         diameter_m: float,
                         velocity: float,
                         density: float) -> float:
    """
    Calculate major (friction) pressure loss using Darcy-Weisbach

    ΔP = f * (L/D) * (ρv²/2)

    Args:
        friction_factor: Darcy friction factor
        length_m: Pipe length in m
        diameter_m: Pipe diameter in m
        velocity: Flow velocity in m/s
        density: Fluid density in kg/m³

    Returns:
        Pressure drop in Pascal
    """
    if diameter_m <= 0:
        return 0.0

    dynamic_pressure = 0.5 * density * velocity ** 2
    delta_p = friction_factor * (length_m / diameter_m) * dynamic_pressure

    return delta_p


def calculate_minor_loss(K_total: float, velocity: float, density: float) -> float:
    """
    Calculate minor losses from fittings

    ΔP = K * (ρv²/2)

    Args:
        K_total: Sum of all K factors
        velocity: Flow velocity in m/s
        density: Fluid density in kg/m³

    Returns:
        Pressure drop in Pascal
    """
    dynamic_pressure = 0.5 * density * velocity ** 2
    return K_total * dynamic_pressure


def calculate_elevation_head(delta_elevation_m: float, density: float) -> float:
    """
    Calculate static pressure difference due to elevation change

    ΔP = ρgh

    Args:
        delta_elevation_m: Elevation difference (downstream - upstream) in m
        density: Fluid density in kg/m³

    Returns:
        Pressure change in Pascal (positive if downstream is lower)
    """
    return density * GRAVITY * delta_elevation_m


class TreeNetworkCalculator:
    """
    Calculator for tree-topology hydrant networks.
    Handles flow distribution, pressure drop, and result generation.
    """

    def __init__(self, network: NetworkInput):
        self.network = network
        self.nodes: Dict[str, Node] = {n.node_id: n for n in network.nodes}
        self.edges: Dict[str, Edge] = {e.edge_id: e for e in network.edges}

        # Build adjacency lists
        self.children: Dict[str, List[str]] = defaultdict(list)  # node -> child edges
        self.parent_edge: Dict[str, str] = {}  # node -> parent edge
        self.edge_to: Dict[str, str] = {}  # edge -> downstream node
        self.edge_from: Dict[str, str] = {}  # edge -> upstream node

        for edge in network.edges:
            self.children[edge.from_node].append(edge.edge_id)
            self.parent_edge[edge.to_node] = edge.edge_id
            self.edge_to[edge.edge_id] = edge.to_node
            self.edge_from[edge.edge_id] = edge.from_node

        # Results storage
        self.segment_results: Dict[str, SegmentResult] = {}
        self.node_results: Dict[str, NodeResult] = {}
        self.edge_flows: Dict[str, float] = {}  # edge_id -> flow in L/min
        self.warnings: List[str] = []

        # Find source node
        self.source_node: Optional[str] = None
        for node in network.nodes:
            if node.type == NodeType.SOURCE:
                self.source_node = node.node_id
                break

    def calculate_downstream_demand(self, node_id: str) -> float:
        """
        Recursively calculate total downstream demand from a node.
        For a tree network, flow in each segment = sum of demands downstream.

        Args:
            node_id: Starting node ID

        Returns:
            Total demand in L/min
        """
        node = self.nodes[node_id]

        # Base demand at this node
        total = 0.0
        if node.type == NodeType.HYDRANT and node.is_active:
            total = node.demand_lpm

        # Add demands from all downstream nodes
        for edge_id in self.children[node_id]:
            downstream_node = self.edge_to[edge_id]
            total += self.calculate_downstream_demand(downstream_node)

        return total

    def calculate_edge_flows(self):
        """Calculate flow in each edge based on downstream demands"""
        for edge_id, edge in self.edges.items():
            # Flow in edge = total demand downstream of this edge
            downstream_node = edge.to_node
            self.edge_flows[edge_id] = self.calculate_downstream_demand(downstream_node)

    def calculate_segment(self, edge_id: str) -> SegmentResult:
        """
        Calculate all hydraulic parameters for a pipe segment.

        Args:
            edge_id: Edge identifier

        Returns:
            SegmentResult with all calculated parameters
        """
        edge = self.edges[edge_id]
        flow_lpm = self.edge_flows.get(edge_id, 0.0)
        flow_m3s = lpm_to_m3s(flow_lpm)

        diameter_m = mm_to_m(edge.diameter_mm)
        roughness_m = mm_to_m(edge.roughness_mm)

        density = self.network.fluid.density_kg_m3
        viscosity = self.network.fluid.viscosity_pa_s

        # Calculate velocity
        velocity = calculate_velocity(flow_m3s, diameter_m)

        # Calculate Reynolds number
        reynolds = calculate_reynolds(velocity, diameter_m, density, viscosity)

        # Calculate friction factor
        friction_factor, flow_regime = calculate_friction_factor(
            reynolds, roughness_m, diameter_m
        )

        # Calculate pressure losses
        if flow_lpm > 0:
            delta_p_major_pa = calculate_major_loss(
                friction_factor, edge.length_m, diameter_m, velocity, density
            )
            delta_p_minor_pa = calculate_minor_loss(
                edge.get_total_K(), velocity, density
            )
        else:
            delta_p_major_pa = 0.0
            delta_p_minor_pa = 0.0

        delta_p_total_pa = delta_p_major_pa + delta_p_minor_pa

        return SegmentResult(
            edge_id=edge_id,
            from_node=edge.from_node,
            to_node=edge.to_node,
            flow_lpm=flow_lpm,
            flow_m3s=flow_m3s,
            velocity_ms=velocity,
            reynolds=reynolds,
            friction_factor=friction_factor,
            delta_p_major_bar=pa_to_bar(delta_p_major_pa),
            delta_p_minor_bar=pa_to_bar(delta_p_minor_pa),
            delta_p_total_bar=pa_to_bar(delta_p_total_pa),
            flow_regime=flow_regime
        )

    def calculate_node_pressures(self):
        """
        Calculate pressure at each node using BFS from source.
        P_downstream = P_upstream - ΔP_pipe - ΔP_elevation
        """
        if not self.source_node:
            return

        # Source node pressure
        source_node = self.nodes[self.source_node]
        source_pressure_bar = self.network.source_pressure_bar

        # BFS traversal
        visited: Set[str] = set()
        queue: List[Tuple[str, float, float]] = [
            (self.source_node, source_pressure_bar, 0.0)
        ]  # (node_id, pressure, cumulative_distance)

        while queue:
            node_id, pressure_bar, distance_m = queue.pop(0)

            if node_id in visited:
                continue
            visited.add(node_id)

            node = self.nodes[node_id]

            # Store node result
            self.node_results[node_id] = NodeResult(
                node_id=node_id,
                type=node.type.value,
                elevation_m=node.elevation_m,
                demand_lpm=node.demand_lpm if node.is_active else 0.0,
                pressure_bar=pressure_bar,
                is_active=node.is_active,
                distance_from_source_m=distance_m
            )

            # Check for negative pressure
            if pressure_bar < 0:
                self.warnings.append(
                    f"Warning: Negative gauge pressure at node {node_id} "
                    f"({pressure_bar:.2f} bar)"
                )

            # Process child edges
            for edge_id in self.children[node_id]:
                edge = self.edges[edge_id]
                downstream_node_id = edge.to_node
                downstream_node = self.nodes[downstream_node_id]

                if downstream_node_id in visited:
                    continue

                # Get segment result
                seg_result = self.segment_results.get(edge_id)
                if not seg_result:
                    seg_result = self.calculate_segment(edge_id)
                    self.segment_results[edge_id] = seg_result

                # Calculate pressure at downstream node
                delta_p_pipe = seg_result.delta_p_total_bar

                # Elevation head
                delta_p_elevation = 0.0
                if self.network.include_elevation:
                    delta_z = downstream_node.elevation_m - node.elevation_m
                    delta_p_elevation_pa = calculate_elevation_head(
                        delta_z, self.network.fluid.density_kg_m3
                    )
                    delta_p_elevation = pa_to_bar(delta_p_elevation_pa)

                # Downstream pressure = upstream - pipe loss - elevation head
                downstream_pressure = pressure_bar - delta_p_pipe - delta_p_elevation

                new_distance = distance_m + edge.length_m

                queue.append((downstream_node_id, downstream_pressure, new_distance))

    def find_critical_path(self) -> Optional[CriticalPath]:
        """
        Find the critical (lowest pressure) hydrant and trace path from source.

        Returns:
            CriticalPath object or None if no hydrants
        """
        # Find hydrant with lowest pressure
        critical_hydrant: Optional[str] = None
        min_pressure = float('inf')

        for node_id, result in self.node_results.items():
            node = self.nodes[node_id]
            if node.type == NodeType.HYDRANT and node.is_active:
                if result.pressure_bar < min_pressure:
                    min_pressure = result.pressure_bar
                    critical_hydrant = node_id

        if not critical_hydrant:
            return None

        # Trace path from critical hydrant back to source
        path_nodes: List[str] = [critical_hydrant]
        path_edges: List[str] = []
        total_length = 0.0

        current = critical_hydrant
        while current in self.parent_edge:
            edge_id = self.parent_edge[current]
            edge = self.edges[edge_id]
            path_edges.insert(0, edge_id)
            path_nodes.insert(0, edge.from_node)
            total_length += edge.length_m
            current = edge.from_node

        return CriticalPath(
            path_nodes=path_nodes,
            path_edges=path_edges,
            total_length_m=total_length,
            critical_hydrant=critical_hydrant,
            critical_pressure_bar=min_pressure
        )

    def calculate(self) -> CalculationResult:
        """
        Run complete network calculation.

        Returns:
            CalculationResult with all calculated data
        """
        try:
            # Step 1: Calculate flow in each edge
            self.calculate_edge_flows()

            # Step 2: Calculate segment results
            for edge_id in self.edges:
                self.segment_results[edge_id] = self.calculate_segment(edge_id)

            # Step 3: Calculate node pressures
            self.calculate_node_pressures()

            # Step 4: Find critical path
            critical_path = self.find_critical_path()

            # Step 5: Calculate total demand
            total_demand = sum(
                node.demand_lpm
                for node in self.network.nodes
                if node.type == NodeType.HYDRANT and node.is_active
            )

            return CalculationResult(
                success=True,
                message="Calculation completed successfully",
                segments=list(self.segment_results.values()),
                nodes=list(self.node_results.values()),
                critical_path=critical_path,
                total_demand_lpm=total_demand,
                warnings=self.warnings
            )

        except Exception as e:
            return CalculationResult(
                success=False,
                message=f"Calculation error: {str(e)}",
                warnings=self.warnings
            )


def run_calculation(network: NetworkInput) -> CalculationResult:
    """
    Main entry point for network calculation.

    Args:
        network: Complete network input configuration

    Returns:
        CalculationResult with all calculated data
    """
    calculator = TreeNetworkCalculator(network)
    return calculator.calculate()
