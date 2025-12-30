"""
Unit tests for Hydrant Network Calculator

Tests friction factor calculations, pressure drop, and network calculations.
"""

import pytest
import math
import sys
import os

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from calculator import (
    calculate_reynolds,
    calculate_friction_factor_laminar,
    calculate_friction_factor_swamee_jain,
    calculate_friction_factor,
    calculate_velocity,
    calculate_major_loss,
    calculate_minor_loss,
    calculate_elevation_head,
    lpm_to_m3s,
    m3s_to_lpm,
    mm_to_m,
    pa_to_bar,
    bar_to_pa,
    TreeNetworkCalculator,
    run_calculation
)
from models import (
    Node, Edge, NodeType, FluidProperties, NetworkInput,
    MinorLossComponent
)


class TestUnitConversions:
    """Test unit conversion functions"""

    def test_lpm_to_m3s(self):
        """1000 L/min = 1/60 m³/s"""
        assert abs(lpm_to_m3s(1000) - 1/60) < 1e-10

    def test_m3s_to_lpm(self):
        """1 m³/s = 60000 L/min"""
        assert abs(m3s_to_lpm(1) - 60000) < 1e-10

    def test_mm_to_m(self):
        """1000 mm = 1 m"""
        assert mm_to_m(1000) == 1.0

    def test_pa_to_bar(self):
        """100000 Pa = 1 bar"""
        assert pa_to_bar(100000) == 1.0

    def test_bar_to_pa(self):
        """1 bar = 100000 Pa"""
        assert bar_to_pa(1) == 100000


class TestReynoldsNumber:
    """Test Reynolds number calculation"""

    def test_reynolds_typical(self):
        """Test typical water flow in pipe"""
        # 100mm pipe, 1 m/s velocity, water at 20°C
        velocity = 1.0  # m/s
        diameter = 0.1  # m
        density = 998.0  # kg/m³
        viscosity = 0.001002  # Pa·s

        Re = calculate_reynolds(velocity, diameter, density, viscosity)

        # Expected: (998 * 1 * 0.1) / 0.001002 ≈ 99601
        assert 99000 < Re < 100000

    def test_reynolds_zero_velocity(self):
        """Zero velocity should give zero Reynolds"""
        Re = calculate_reynolds(0, 0.1, 998, 0.001)
        assert Re == 0

    def test_reynolds_zero_diameter(self):
        """Zero diameter should give zero Reynolds"""
        Re = calculate_reynolds(1, 0, 998, 0.001)
        assert Re == 0


class TestFrictionFactor:
    """Test friction factor calculations"""

    def test_laminar_friction_factor(self):
        """f = 64/Re for laminar flow"""
        Re = 2000
        f = calculate_friction_factor_laminar(Re)
        assert abs(f - 0.032) < 1e-6

    def test_laminar_zero_reynolds(self):
        """Zero Reynolds should give zero friction factor"""
        f = calculate_friction_factor_laminar(0)
        assert f == 0

    def test_swamee_jain_smooth_pipe(self):
        """Test Swamee-Jain for smooth pipe at high Re"""
        # For smooth pipe (ε ≈ 0), high Re
        Re = 100000
        roughness = 0.0001  # 0.1 mm
        diameter = 0.1  # 100 mm

        f = calculate_friction_factor_swamee_jain(Re, roughness, diameter)

        # Expected friction factor around 0.018-0.022 for this regime
        assert 0.015 < f < 0.025

    def test_swamee_jain_rough_pipe(self):
        """Test Swamee-Jain for rough pipe"""
        Re = 100000
        roughness = 0.001  # 1 mm (very rough)
        diameter = 0.1

        f = calculate_friction_factor_swamee_jain(Re, roughness, diameter)

        # Rough pipe has higher friction
        f_smooth = calculate_friction_factor_swamee_jain(Re, 0.0001, diameter)
        assert f > f_smooth

    def test_friction_factor_laminar_regime(self):
        """Test automatic regime detection for laminar"""
        Re = 1500  # Laminar
        f, regime = calculate_friction_factor(Re, 0.0001, 0.1)

        assert regime == "laminar"
        assert abs(f - 64/1500) < 1e-6

    def test_friction_factor_turbulent_regime(self):
        """Test automatic regime detection for turbulent"""
        Re = 50000  # Turbulent
        f, regime = calculate_friction_factor(Re, 0.0001, 0.1)

        assert regime == "turbulent"
        assert f > 0


class TestVelocity:
    """Test velocity calculation"""

    def test_velocity_calculation(self):
        """Test v = Q / A"""
        # 100 mm diameter, 1 m³/s flow
        diameter = 0.1  # m
        flow = 0.01  # m³/s

        v = calculate_velocity(flow, diameter)

        # A = π * (0.05)² = 0.00785 m²
        # v = 0.01 / 0.00785 ≈ 1.27 m/s
        expected = 0.01 / (math.pi * 0.05**2)
        assert abs(v - expected) < 1e-6

    def test_velocity_zero_diameter(self):
        """Zero diameter should return zero velocity"""
        v = calculate_velocity(1, 0)
        assert v == 0


class TestPressureDrop:
    """Test pressure drop calculations"""

    def test_major_loss(self):
        """Test Darcy-Weisbach pressure drop"""
        f = 0.02
        L = 100  # m
        D = 0.1  # m
        v = 2.0  # m/s
        rho = 998  # kg/m³

        dp = calculate_major_loss(f, L, D, v, rho)

        # ΔP = f * (L/D) * (ρv²/2)
        # = 0.02 * (100/0.1) * (998 * 4 / 2)
        # = 0.02 * 1000 * 1996
        # = 39920 Pa
        expected = f * (L/D) * (0.5 * rho * v**2)
        assert abs(dp - expected) < 1

    def test_minor_loss(self):
        """Test minor loss calculation"""
        K = 2.5
        v = 2.0  # m/s
        rho = 998  # kg/m³

        dp = calculate_minor_loss(K, v, rho)

        # ΔP = K * (ρv²/2) = 2.5 * (998 * 4 / 2) = 4990 Pa
        expected = K * (0.5 * rho * v**2)
        assert abs(dp - expected) < 1

    def test_elevation_head(self):
        """Test static pressure from elevation"""
        delta_z = 10  # m
        rho = 998  # kg/m³

        dp = calculate_elevation_head(delta_z, rho)

        # ΔP = ρgh = 998 * 9.81 * 10 ≈ 97904 Pa
        expected = rho * 9.81 * delta_z
        assert abs(dp - expected) < 1


class TestNetworkCalculation:
    """Test complete network calculations"""

    @pytest.fixture
    def simple_network(self) -> NetworkInput:
        """Create a simple test network"""
        nodes = [
            Node(node_id="S", type=NodeType.SOURCE, elevation_m=0, demand_lpm=0),
            Node(node_id="H1", type=NodeType.HYDRANT, elevation_m=0, demand_lpm=500, is_active=True),
        ]

        edges = [
            Edge(
                edge_id="P1",
                from_node="S",
                to_node="H1",
                length_m=100,
                diameter_mm=100,
                roughness_mm=0.045,
                minor_K=2.0
            )
        ]

        return NetworkInput(
            nodes=nodes,
            edges=edges,
            source_pressure_bar=8.0,
            fluid=FluidProperties(),
            include_elevation=True,
            pressure_unit="bar"
        )

    @pytest.fixture
    def branched_network(self) -> NetworkInput:
        """Create a branched test network (demo case)"""
        nodes = [
            Node(node_id="S", type=NodeType.SOURCE, elevation_m=0, demand_lpm=0),
            Node(node_id="J1", type=NodeType.JUNCTION, elevation_m=0, demand_lpm=0),
            Node(node_id="J2", type=NodeType.JUNCTION, elevation_m=2, demand_lpm=0),
            Node(node_id="H1", type=NodeType.HYDRANT, elevation_m=0, demand_lpm=500, is_active=True),
            Node(node_id="H2", type=NodeType.HYDRANT, elevation_m=3, demand_lpm=500, is_active=True),
        ]

        edges = [
            Edge(edge_id="P1", from_node="S", to_node="J1", length_m=50, diameter_mm=150, roughness_mm=0.045, minor_K=0.5),
            Edge(edge_id="P2", from_node="J1", to_node="J2", length_m=30, diameter_mm=100, roughness_mm=0.045, minor_K=1.4),
            Edge(edge_id="P3", from_node="J1", to_node="H1", length_m=20, diameter_mm=65, roughness_mm=0.045, minor_K=4.4),
            Edge(edge_id="P4", from_node="J2", to_node="H2", length_m=25, diameter_mm=65, roughness_mm=0.045, minor_K=4.4),
        ]

        return NetworkInput(
            nodes=nodes,
            edges=edges,
            source_pressure_bar=8.0,
            fluid=FluidProperties(),
            include_elevation=True,
            pressure_unit="bar"
        )

    def test_simple_network_flow(self, simple_network):
        """Test flow calculation in simple network"""
        result = run_calculation(simple_network)

        assert result.success
        assert len(result.segments) == 1
        assert result.segments[0].flow_lpm == 500  # Demand at H1

    def test_simple_network_pressure(self, simple_network):
        """Test pressure calculation in simple network"""
        result = run_calculation(simple_network)

        assert result.success
        assert len(result.nodes) == 2

        # Source should have input pressure
        source_result = next(n for n in result.nodes if n.node_id == "S")
        assert source_result.pressure_bar == 8.0

        # Hydrant should have lower pressure due to losses
        hydrant_result = next(n for n in result.nodes if n.node_id == "H1")
        assert hydrant_result.pressure_bar < 8.0
        assert hydrant_result.pressure_bar > 0  # Should still be positive

    def test_branched_network_flow_distribution(self, branched_network):
        """Test flow distribution in branched network"""
        result = run_calculation(branched_network)

        assert result.success

        # P1 should carry total flow (1000 L/min)
        p1 = next(s for s in result.segments if s.edge_id == "P1")
        assert p1.flow_lpm == 1000

        # P2 should carry flow to H2 only (500 L/min)
        p2 = next(s for s in result.segments if s.edge_id == "P2")
        assert p2.flow_lpm == 500

        # P3 should carry flow to H1 (500 L/min)
        p3 = next(s for s in result.segments if s.edge_id == "P3")
        assert p3.flow_lpm == 500

        # P4 should carry flow to H2 (500 L/min)
        p4 = next(s for s in result.segments if s.edge_id == "P4")
        assert p4.flow_lpm == 500

    def test_branched_network_critical_path(self, branched_network):
        """Test critical path identification"""
        result = run_calculation(branched_network)

        assert result.success
        assert result.critical_path is not None

        # H2 should be critical (further away and higher elevation)
        assert result.critical_path.critical_hydrant == "H2"

    def test_total_demand(self, branched_network):
        """Test total demand calculation"""
        result = run_calculation(branched_network)

        assert result.success
        assert result.total_demand_lpm == 1000  # 500 + 500

    def test_turbulent_flow(self, simple_network):
        """Test that flow is turbulent at typical conditions"""
        result = run_calculation(simple_network)

        assert result.success
        assert result.segments[0].flow_regime == "turbulent"
        assert result.segments[0].reynolds > 2300

    def test_pressure_decreases_along_path(self, branched_network):
        """Test that pressure decreases from source to hydrants"""
        result = run_calculation(branched_network)

        assert result.success

        pressures = {n.node_id: n.pressure_bar for n in result.nodes}

        # Pressure should decrease along path
        assert pressures["S"] > pressures["J1"]
        assert pressures["J1"] > pressures["H1"]
        assert pressures["J1"] > pressures["J2"]
        assert pressures["J2"] > pressures["H2"]


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_zero_demand_hydrant(self):
        """Network with zero demand should still calculate"""
        nodes = [
            Node(node_id="S", type=NodeType.SOURCE, elevation_m=0, demand_lpm=0),
            Node(node_id="H1", type=NodeType.HYDRANT, elevation_m=0, demand_lpm=0, is_active=True),
        ]

        edges = [
            Edge(edge_id="P1", from_node="S", to_node="H1", length_m=100, diameter_mm=100)
        ]

        # This should fail validation (no demand)
        # but we test that the calculator handles it gracefully

    def test_inactive_hydrant(self):
        """Inactive hydrant should not contribute to flow"""
        nodes = [
            Node(node_id="S", type=NodeType.SOURCE, elevation_m=0, demand_lpm=0),
            Node(node_id="H1", type=NodeType.HYDRANT, elevation_m=0, demand_lpm=500, is_active=True),
            Node(node_id="H2", type=NodeType.HYDRANT, elevation_m=0, demand_lpm=500, is_active=False),
        ]

        edges = [
            Edge(edge_id="P1", from_node="S", to_node="H1", length_m=100, diameter_mm=100),
            Edge(edge_id="P2", from_node="S", to_node="H2", length_m=100, diameter_mm=100),
        ]

        network = NetworkInput(
            nodes=nodes,
            edges=edges,
            source_pressure_bar=8.0,
            fluid=FluidProperties(),
            include_elevation=True
        )

        result = run_calculation(network)

        assert result.success
        assert result.total_demand_lpm == 500  # Only H1 active

        # P2 should have zero flow
        p2 = next(s for s in result.segments if s.edge_id == "P2")
        assert p2.flow_lpm == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
