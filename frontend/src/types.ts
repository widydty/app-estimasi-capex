/**
 * TypeScript types for Hydrant Network Calculator
 * Mirrors the backend Pydantic models
 */

export type NodeType = 'source' | 'junction' | 'hydrant';
export type PressureUnit = 'bar' | 'kPa' | 'MPa';

export interface MinorLossComponent {
  name: string;
  K: number;
}

export interface Node {
  node_id: string;
  type: NodeType;
  elevation_m: number;
  demand_lpm: number;
  is_active: boolean;
}

export interface Edge {
  edge_id: string;
  from_node: string;
  to_node: string;
  length_m: number;
  diameter_mm: number;
  roughness_mm: number;
  minor_K: number;
  minor_components?: MinorLossComponent[];
}

export interface FluidProperties {
  density_kg_m3: number;
  viscosity_pa_s: number;
}

export interface NetworkInput {
  nodes: Node[];
  edges: Edge[];
  source_pressure_bar: number;
  fluid: FluidProperties;
  include_elevation: boolean;
  pressure_unit: PressureUnit;
}

// Result types
export interface SegmentResult {
  edge_id: string;
  from_node: string;
  to_node: string;
  flow_lpm: number;
  flow_m3s: number;
  velocity_ms: number;
  reynolds: number;
  friction_factor: number;
  delta_p_major_bar: number;
  delta_p_minor_bar: number;
  delta_p_total_bar: number;
  flow_regime: string;
}

export interface NodeResult {
  node_id: string;
  type: string;
  elevation_m: number;
  demand_lpm: number;
  pressure_bar: number;
  is_active: boolean;
  distance_from_source_m: number;
}

export interface CriticalPath {
  path_nodes: string[];
  path_edges: string[];
  total_length_m: number;
  critical_hydrant: string;
  critical_pressure_bar: number;
}

export interface CalculationResult {
  success: boolean;
  message: string;
  segments: SegmentResult[];
  nodes: NodeResult[];
  critical_path: CriticalPath | null;
  total_demand_lpm: number;
  warnings: string[];
}

export interface ValidationResponse {
  is_valid: boolean;
  errors: string[];
}

// Default values
export const DEFAULT_FLUID: FluidProperties = {
  density_kg_m3: 998.0,
  viscosity_pa_s: 0.001002
};

export const createEmptyNode = (id: string, type: NodeType = 'junction'): Node => ({
  node_id: id,
  type,
  elevation_m: 0,
  demand_lpm: type === 'hydrant' ? 500 : 0,
  is_active: true
});

export const createEmptyEdge = (id: string, from: string, to: string): Edge => ({
  edge_id: id,
  from_node: from,
  to_node: to,
  length_m: 10,
  diameter_mm: 100,
  roughness_mm: 0.045,
  minor_K: 0,
  minor_components: []
});

// K-factor reference for UI
export const K_FACTOR_REFERENCE: Record<string, number> = {
  'gate_valve_open': 0.2,
  'gate_valve_half': 5.6,
  'globe_valve_open': 10.0,
  'ball_valve_open': 0.05,
  'check_valve_swing': 2.5,
  'butterfly_valve_open': 0.3,
  'elbow_90_standard': 0.9,
  'elbow_90_long_radius': 0.6,
  'elbow_45': 0.4,
  'tee_run': 0.3,
  'tee_branch': 1.0,
  'reducer_sudden': 0.5,
  'expander_sudden': 1.0,
  'entrance_sharp': 0.5,
  'entrance_rounded': 0.25,
  'exit': 1.0,
  'hydrant_outlet': 2.5
};
