"""
Hydrant Network Calculator - FastAPI Backend

API Endpoints:
- POST /api/calculate - Run network calculation
- POST /api/validate - Validate network structure
- GET /api/demo - Get demo network data
- GET /api/k-factors - Get minor loss K-factor reference
- POST /api/export/csv - Export results to CSV
"""

import io
import csv
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

try:
    from .models import (
        NetworkInput, CalculationResult, Node, Edge, NodeType,
        FluidProperties, MinorLossComponent, MINOR_LOSS_K_FACTORS, PressureUnit
    )
    from .calculator import run_calculation
    from .validation import validate_network
except ImportError:
    from models import (
        NetworkInput, CalculationResult, Node, Edge, NodeType,
        FluidProperties, MinorLossComponent, MINOR_LOSS_K_FACTORS, PressureUnit
    )
    from calculator import run_calculation
    from validation import validate_network


# Create FastAPI app
app = FastAPI(
    title="Hydrant Network Calculator",
    description="Calculate pressure drop and flow distribution in tree-topology hydrant networks",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===

class ValidationResponse(BaseModel):
    is_valid: bool
    errors: list[str]


class ExportRequest(BaseModel):
    result: CalculationResult
    pressure_unit: PressureUnit = PressureUnit.BAR


# === API Endpoints ===

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Hydrant Network Calculator",
        "version": "1.0.0"
    }


@app.post("/api/calculate", response_model=CalculationResult)
async def calculate(network: NetworkInput):
    """
    Calculate pressure drop and flow distribution for the network.

    The network must be a valid tree topology with:
    - Exactly one source node
    - No loops
    - All nodes reachable from source
    - At least one active hydrant with demand > 0
    """
    # Validate first
    is_valid, errors = validate_network(network)

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Network validation failed",
                "errors": errors
            }
        )

    # Run calculation
    result = run_calculation(network)

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail={
                "message": result.message,
                "warnings": result.warnings
            }
        )

    return result


@app.post("/api/validate", response_model=ValidationResponse)
async def validate(network: NetworkInput):
    """
    Validate network structure without running calculations.

    Checks:
    - Unique node and edge IDs
    - Valid edge references
    - Single source node
    - Positive pipe dimensions
    - No loops (tree structure)
    - All nodes connected to source
    - Active hydrants with demand
    """
    is_valid, errors = validate_network(network)

    return ValidationResponse(
        is_valid=is_valid,
        errors=errors
    )


@app.get("/api/demo")
async def get_demo_network() -> Dict[str, Any]:
    """
    Get a demo network configuration for testing.

    Demo network:
    - Source S at 8 bar
    - Junctions J1, J2
    - Hydrants H1 (500 L/min), H2 (500 L/min)
    - Pipes with varying diameters and lengths
    """
    demo_network = {
        "nodes": [
            {
                "node_id": "S",
                "type": "source",
                "elevation_m": 0.0,
                "demand_lpm": 0.0,
                "is_active": True
            },
            {
                "node_id": "J1",
                "type": "junction",
                "elevation_m": 0.0,
                "demand_lpm": 0.0,
                "is_active": True
            },
            {
                "node_id": "J2",
                "type": "junction",
                "elevation_m": 2.0,
                "demand_lpm": 0.0,
                "is_active": True
            },
            {
                "node_id": "H1",
                "type": "hydrant",
                "elevation_m": 0.0,
                "demand_lpm": 500.0,
                "is_active": True
            },
            {
                "node_id": "H2",
                "type": "hydrant",
                "elevation_m": 3.0,
                "demand_lpm": 500.0,
                "is_active": True
            }
        ],
        "edges": [
            {
                "edge_id": "P1",
                "from_node": "S",
                "to_node": "J1",
                "length_m": 50.0,
                "diameter_mm": 150.0,
                "roughness_mm": 0.045,
                "minor_K": 0.5,
                "minor_components": [
                    {"name": "gate_valve_open", "K": 0.2},
                    {"name": "tee_run", "K": 0.3}
                ]
            },
            {
                "edge_id": "P2",
                "from_node": "J1",
                "to_node": "J2",
                "length_m": 30.0,
                "diameter_mm": 100.0,
                "roughness_mm": 0.045,
                "minor_K": 1.3,
                "minor_components": [
                    {"name": "elbow_90_standard", "K": 0.9},
                    {"name": "tee_run", "K": 0.3},
                    {"name": "gate_valve_open", "K": 0.2}
                ]
            },
            {
                "edge_id": "P3",
                "from_node": "J1",
                "to_node": "H1",
                "length_m": 20.0,
                "diameter_mm": 65.0,
                "roughness_mm": 0.045,
                "minor_K": 3.4,
                "minor_components": [
                    {"name": "tee_branch", "K": 1.0},
                    {"name": "elbow_90_standard", "K": 0.9},
                    {"name": "hydrant_outlet", "K": 2.5}
                ]
            },
            {
                "edge_id": "P4",
                "from_node": "J2",
                "to_node": "H2",
                "length_m": 25.0,
                "diameter_mm": 65.0,
                "roughness_mm": 0.045,
                "minor_K": 4.4,
                "minor_components": [
                    {"name": "tee_branch", "K": 1.0},
                    {"name": "elbow_90_standard", "K": 0.9},
                    {"name": "hydrant_outlet", "K": 2.5}
                ]
            }
        ],
        "source_pressure_bar": 8.0,
        "fluid": {
            "density_kg_m3": 998.0,
            "viscosity_pa_s": 0.001002
        },
        "include_elevation": True,
        "pressure_unit": "bar"
    }

    return demo_network


@app.get("/api/k-factors")
async def get_k_factors() -> Dict[str, float]:
    """
    Get reference K-factors for common fittings and components.
    """
    return MINOR_LOSS_K_FACTORS


@app.post("/api/export/segments-csv")
async def export_segments_csv(request: ExportRequest):
    """
    Export segment results to CSV.
    """
    result = request.result

    if not result.segments:
        raise HTTPException(status_code=400, detail="No segment data to export")

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Edge ID",
        "From Node",
        "To Node",
        "Flow (L/min)",
        "Flow (m3/s)",
        "Velocity (m/s)",
        "Reynolds",
        "Friction Factor",
        "Major Loss (bar)",
        "Minor Loss (bar)",
        "Total Loss (bar)",
        "Flow Regime"
    ])

    # Data
    for seg in result.segments:
        writer.writerow([
            seg.edge_id,
            seg.from_node,
            seg.to_node,
            f"{seg.flow_lpm:.2f}",
            f"{seg.flow_m3s:.6f}",
            f"{seg.velocity_ms:.3f}",
            f"{seg.reynolds:.0f}",
            f"{seg.friction_factor:.6f}",
            f"{seg.delta_p_major_bar:.4f}",
            f"{seg.delta_p_minor_bar:.4f}",
            f"{seg.delta_p_total_bar:.4f}",
            seg.flow_regime
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=segments.csv"}
    )


@app.post("/api/export/nodes-csv")
async def export_nodes_csv(request: ExportRequest):
    """
    Export node results to CSV.
    """
    result = request.result

    if not result.nodes:
        raise HTTPException(status_code=400, detail="No node data to export")

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Node ID",
        "Type",
        "Elevation (m)",
        "Demand (L/min)",
        "Pressure (bar)",
        "Active",
        "Distance from Source (m)"
    ])

    # Data
    for node in result.nodes:
        writer.writerow([
            node.node_id,
            node.type,
            f"{node.elevation_m:.2f}",
            f"{node.demand_lpm:.2f}",
            f"{node.pressure_bar:.4f}",
            "Yes" if node.is_active else "No",
            f"{node.distance_from_source_m:.2f}"
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nodes.csv"}
    )


# === Run with uvicorn ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
