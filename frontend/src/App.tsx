import React, { useState, useCallback } from 'react';
import {
  Droplet, Calculator, Download, AlertTriangle, CheckCircle,
  Plus, Trash2, Upload, FileJson, Play, RotateCcw
} from 'lucide-react';
import {
  Node, Edge, NetworkInput, CalculationResult, FluidProperties,
  DEFAULT_FLUID, createEmptyNode, createEmptyEdge, K_FACTOR_REFERENCE
} from './types';
import { calculateNetwork, getDemoNetwork, exportSegmentsCSV, exportNodesCSV, downloadBlob } from './api';
import { PressureChart } from './components/PressureChart';

function App() {
  // Network state
  const [nodes, setNodes] = useState<Node[]>([
    { node_id: 'S', type: 'source', elevation_m: 0, demand_lpm: 0, is_active: true }
  ]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [sourcePressure, setSourcePressure] = useState(8.0);
  const [fluid, setFluid] = useState<FluidProperties>(DEFAULT_FLUID);
  const [includeElevation, setIncludeElevation] = useState(true);

  // Result state
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [activeTab, setActiveTab] = useState<'input' | 'results'>('input');

  // Node handlers
  const addNode = useCallback((type: 'junction' | 'hydrant') => {
    const prefix = type === 'junction' ? 'J' : 'H';
    const count = nodes.filter(n => n.type === type).length + 1;
    const newNode = createEmptyNode(`${prefix}${count}`, type);
    setNodes([...nodes, newNode]);
  }, [nodes]);

  const updateNode = useCallback((index: number, field: keyof Node, value: Node[keyof Node]) => {
    const updated = [...nodes];
    updated[index] = { ...updated[index], [field]: value };
    setNodes(updated);
  }, [nodes]);

  const removeNode = useCallback((index: number) => {
    const nodeId = nodes[index].node_id;
    // Don't remove source
    if (nodes[index].type === 'source') return;
    // Remove related edges
    setEdges(edges.filter(e => e.from_node !== nodeId && e.to_node !== nodeId));
    setNodes(nodes.filter((_, i) => i !== index));
  }, [nodes, edges]);

  // Edge handlers
  const addEdge = useCallback(() => {
    const count = edges.length + 1;
    const fromOptions = nodes.map(n => n.node_id);
    const newEdge = createEmptyEdge(
      `P${count}`,
      fromOptions[0] || '',
      fromOptions[1] || ''
    );
    setEdges([...edges, newEdge]);
  }, [edges, nodes]);

  const updateEdge = useCallback((index: number, field: keyof Edge, value: Edge[keyof Edge]) => {
    const updated = [...edges];
    updated[index] = { ...updated[index], [field]: value };
    setEdges(updated);
  }, [edges]);

  const removeEdge = useCallback((index: number) => {
    setEdges(edges.filter((_, i) => i !== index));
  }, [edges]);

  // Load demo network
  const loadDemo = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const demo = await getDemoNetwork();
      setNodes(demo.nodes);
      setEdges(demo.edges);
      setSourcePressure(demo.source_pressure_bar);
      setFluid(demo.fluid);
      setIncludeElevation(demo.include_elevation);
      setResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load demo');
    } finally {
      setLoading(false);
    }
  }, []);

  // Reset network
  const resetNetwork = useCallback(() => {
    setNodes([{ node_id: 'S', type: 'source', elevation_m: 0, demand_lpm: 0, is_active: true }]);
    setEdges([]);
    setSourcePressure(8.0);
    setFluid(DEFAULT_FLUID);
    setIncludeElevation(true);
    setResult(null);
    setError(null);
  }, []);

  // Run calculation
  const runCalculation = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const network: NetworkInput = {
        nodes,
        edges,
        source_pressure_bar: sourcePressure,
        fluid,
        include_elevation: includeElevation,
        pressure_unit: 'bar'
      };

      const calcResult = await calculateNetwork(network);
      setResult(calcResult);
      setActiveTab('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Calculation failed');
    } finally {
      setLoading(false);
    }
  }, [nodes, edges, sourcePressure, fluid, includeElevation]);

  // Export handlers
  const handleExportSegments = useCallback(async () => {
    if (!result) return;
    try {
      const blob = await exportSegmentsCSV(result);
      downloadBlob(blob, 'segments.csv');
    } catch (err) {
      setError('Failed to export segments CSV');
    }
  }, [result]);

  const handleExportNodes = useCallback(async () => {
    if (!result) return;
    try {
      const blob = await exportNodesCSV(result);
      downloadBlob(blob, 'nodes.csv');
    } catch (err) {
      setError('Failed to export nodes CSV');
    }
  }, [result]);

  // Import JSON
  const handleImportJSON = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (data.nodes) setNodes(data.nodes);
        if (data.edges) setEdges(data.edges);
        if (data.source_pressure_bar) setSourcePressure(data.source_pressure_bar);
        if (data.fluid) setFluid(data.fluid);
        if (data.include_elevation !== undefined) setIncludeElevation(data.include_elevation);
        setResult(null);
        setError(null);
      } catch {
        setError('Invalid JSON file');
      }
    };
    reader.readAsText(file);
  }, []);

  // Export current network as JSON
  const handleExportJSON = useCallback(() => {
    const network: NetworkInput = {
      nodes,
      edges,
      source_pressure_bar: sourcePressure,
      fluid,
      include_elevation: includeElevation,
      pressure_unit: 'bar'
    };
    const blob = new Blob([JSON.stringify(network, null, 2)], { type: 'application/json' });
    downloadBlob(blob, 'hydrant_network.json');
  }, [nodes, edges, sourcePressure, fluid, includeElevation]);

  return (
    <div className="min-h-screen p-4 md:p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Droplet className="w-8 h-8 text-indigo-600" />
          <h1 className="text-2xl font-bold text-slate-800">Hydrant Network Calculator</h1>
        </div>
        <p className="text-slate-600">
          Hitung pressure drop dan distribusi flow pada jaringan pipa hydrant bercabang (tree network)
        </p>
      </div>

      {/* Error display */}
      {error && (
        <div className="max-w-7xl mx-auto mb-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-red-800 text-sm whitespace-pre-wrap">{error}</div>
            <button onClick={() => setError(null)} className="ml-auto text-red-600 hover:text-red-800">
              &times;
            </button>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="max-w-7xl mx-auto">
        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('input')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'input'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-slate-600 hover:bg-slate-100'
            }`}
          >
            Input Network
          </button>
          <button
            onClick={() => setActiveTab('results')}
            className={`px-4 py-2 rounded-lg font-medium transition ${
              activeTab === 'results'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-slate-600 hover:bg-slate-100'
            }`}
            disabled={!result}
          >
            Hasil Perhitungan
          </button>
        </div>

        {/* Input Tab */}
        {activeTab === 'input' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Network Input */}
            <div className="space-y-6">
              {/* Actions */}
              <div className="card">
                <div className="flex flex-wrap gap-2">
                  <button onClick={loadDemo} className="btn btn-secondary flex items-center gap-2" disabled={loading}>
                    <Play className="w-4 h-4" /> Load Demo
                  </button>
                  <label className="btn btn-secondary flex items-center gap-2 cursor-pointer">
                    <Upload className="w-4 h-4" /> Import JSON
                    <input type="file" accept=".json" onChange={handleImportJSON} className="hidden" />
                  </label>
                  <button onClick={handleExportJSON} className="btn btn-secondary flex items-center gap-2">
                    <FileJson className="w-4 h-4" /> Export JSON
                  </button>
                  <button onClick={resetNetwork} className="btn btn-secondary flex items-center gap-2">
                    <RotateCcw className="w-4 h-4" /> Reset
                  </button>
                </div>
              </div>

              {/* Boundary Conditions */}
              <div className="card">
                <h3 className="font-semibold text-slate-800 mb-4">Boundary Conditions</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="input-group">
                    <label>Source Pressure (bar)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={sourcePressure}
                      onChange={(e) => setSourcePressure(parseFloat(e.target.value) || 0)}
                    />
                  </div>
                  <div className="input-group">
                    <label>Include Elevation</label>
                    <select
                      value={includeElevation ? 'yes' : 'no'}
                      onChange={(e) => setIncludeElevation(e.target.value === 'yes')}
                    >
                      <option value="yes">Yes</option>
                      <option value="no">No</option>
                    </select>
                  </div>
                  <div className="input-group">
                    <label>Density (kg/m&sup3;)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={fluid.density_kg_m3}
                      onChange={(e) => setFluid({ ...fluid, density_kg_m3: parseFloat(e.target.value) || 998 })}
                    />
                  </div>
                  <div className="input-group">
                    <label>Viscosity (Pa.s)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={fluid.viscosity_pa_s}
                      onChange={(e) => setFluid({ ...fluid, viscosity_pa_s: parseFloat(e.target.value) || 0.001 })}
                    />
                  </div>
                </div>
              </div>

              {/* Nodes */}
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-slate-800">Nodes ({nodes.length})</h3>
                  <div className="flex gap-2">
                    <button onClick={() => addNode('junction')} className="btn btn-sm btn-secondary flex items-center gap-1">
                      <Plus className="w-4 h-4" /> Junction
                    </button>
                    <button onClick={() => addNode('hydrant')} className="btn btn-sm btn-primary flex items-center gap-1">
                      <Plus className="w-4 h-4" /> Hydrant
                    </button>
                  </div>
                </div>

                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {nodes.map((node, idx) => (
                    <div key={node.node_id} className="bg-slate-50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={`badge badge-${node.type}`}>{node.type}</span>
                        <input
                          type="text"
                          value={node.node_id}
                          onChange={(e) => updateNode(idx, 'node_id', e.target.value)}
                          className="flex-1 px-2 py-1 border rounded text-sm"
                          placeholder="Node ID"
                        />
                        {node.type !== 'source' && (
                          <button onClick={() => removeNode(idx)} className="text-red-500 hover:text-red-700">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-sm">
                        <div>
                          <label className="text-slate-500 text-xs">Elevation (m)</label>
                          <input
                            type="number"
                            step="0.1"
                            value={node.elevation_m}
                            onChange={(e) => updateNode(idx, 'elevation_m', parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 border rounded"
                          />
                        </div>
                        {node.type === 'hydrant' && (
                          <>
                            <div>
                              <label className="text-slate-500 text-xs">Demand (L/min)</label>
                              <input
                                type="number"
                                step="10"
                                value={node.demand_lpm}
                                onChange={(e) => updateNode(idx, 'demand_lpm', parseFloat(e.target.value) || 0)}
                                className="w-full px-2 py-1 border rounded"
                              />
                            </div>
                            <div>
                              <label className="text-slate-500 text-xs">Active</label>
                              <select
                                value={node.is_active ? 'yes' : 'no'}
                                onChange={(e) => updateNode(idx, 'is_active', e.target.value === 'yes')}
                                className="w-full px-2 py-1 border rounded"
                              >
                                <option value="yes">Yes</option>
                                <option value="no">No</option>
                              </select>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Right: Edges */}
            <div className="space-y-6">
              {/* Edges */}
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-slate-800">Pipes ({edges.length})</h3>
                  <button onClick={addEdge} className="btn btn-sm btn-primary flex items-center gap-1">
                    <Plus className="w-4 h-4" /> Add Pipe
                  </button>
                </div>

                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {edges.map((edge, idx) => (
                    <div key={edge.edge_id} className="bg-slate-50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-2">
                        <input
                          type="text"
                          value={edge.edge_id}
                          onChange={(e) => updateEdge(idx, 'edge_id', e.target.value)}
                          className="w-20 px-2 py-1 border rounded text-sm"
                          placeholder="ID"
                        />
                        <select
                          value={edge.from_node}
                          onChange={(e) => updateEdge(idx, 'from_node', e.target.value)}
                          className="flex-1 px-2 py-1 border rounded text-sm"
                        >
                          <option value="">From...</option>
                          {nodes.map(n => (
                            <option key={n.node_id} value={n.node_id}>{n.node_id}</option>
                          ))}
                        </select>
                        <span className="text-slate-400">&rarr;</span>
                        <select
                          value={edge.to_node}
                          onChange={(e) => updateEdge(idx, 'to_node', e.target.value)}
                          className="flex-1 px-2 py-1 border rounded text-sm"
                        >
                          <option value="">To...</option>
                          {nodes.map(n => (
                            <option key={n.node_id} value={n.node_id}>{n.node_id}</option>
                          ))}
                        </select>
                        <button onClick={() => removeEdge(idx)} className="text-red-500 hover:text-red-700">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="grid grid-cols-4 gap-2 text-sm">
                        <div>
                          <label className="text-slate-500 text-xs">Length (m)</label>
                          <input
                            type="number"
                            step="1"
                            value={edge.length_m}
                            onChange={(e) => updateEdge(idx, 'length_m', parseFloat(e.target.value) || 1)}
                            className="w-full px-2 py-1 border rounded"
                          />
                        </div>
                        <div>
                          <label className="text-slate-500 text-xs">Diameter (mm)</label>
                          <input
                            type="number"
                            step="1"
                            value={edge.diameter_mm}
                            onChange={(e) => updateEdge(idx, 'diameter_mm', parseFloat(e.target.value) || 1)}
                            className="w-full px-2 py-1 border rounded"
                          />
                        </div>
                        <div>
                          <label className="text-slate-500 text-xs">Roughness (mm)</label>
                          <input
                            type="number"
                            step="0.001"
                            value={edge.roughness_mm}
                            onChange={(e) => updateEdge(idx, 'roughness_mm', parseFloat(e.target.value) || 0.045)}
                            className="w-full px-2 py-1 border rounded"
                          />
                        </div>
                        <div>
                          <label className="text-slate-500 text-xs">Minor K</label>
                          <input
                            type="number"
                            step="0.1"
                            value={edge.minor_K}
                            onChange={(e) => updateEdge(idx, 'minor_K', parseFloat(e.target.value) || 0)}
                            className="w-full px-2 py-1 border rounded"
                          />
                        </div>
                      </div>
                    </div>
                  ))}

                  {edges.length === 0 && (
                    <div className="text-center text-slate-400 py-8">
                      No pipes added. Click "Add Pipe" to start.
                    </div>
                  )}
                </div>
              </div>

              {/* K-factor reference */}
              <div className="card">
                <h3 className="font-semibold text-slate-800 mb-3">Minor Loss K Reference</h3>
                <div className="grid grid-cols-2 gap-1 text-xs max-h-48 overflow-y-auto">
                  {Object.entries(K_FACTOR_REFERENCE).map(([name, k]) => (
                    <div key={name} className="flex justify-between py-1 px-2 hover:bg-slate-50 rounded">
                      <span className="text-slate-600">{name.replace(/_/g, ' ')}</span>
                      <span className="font-mono text-slate-800">{k}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Calculate button */}
              <button
                onClick={runCalculation}
                disabled={loading || nodes.length < 2 || edges.length === 0}
                className="w-full btn btn-primary py-4 flex items-center justify-center gap-2 text-lg"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white" />
                    Calculating...
                  </>
                ) : (
                  <>
                    <Calculator className="w-5 h-5" />
                    Run Calculation
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Results Tab */}
        {activeTab === 'results' && result && (
          <div className="space-y-6">
            {/* Summary cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Status card */}
              <div className={`card-dark ${result.success ? 'bg-emerald-900' : 'bg-red-900'}`}>
                <div className="flex items-center gap-3 mb-2">
                  {result.success ? (
                    <CheckCircle className="w-6 h-6 text-emerald-400" />
                  ) : (
                    <AlertTriangle className="w-6 h-6 text-red-400" />
                  )}
                  <span className="text-slate-300 text-sm uppercase tracking-wide">Status</span>
                </div>
                <div className="text-2xl font-bold">{result.success ? 'Success' : 'Failed'}</div>
                <div className="text-slate-400 text-sm mt-1">{result.message}</div>
              </div>

              {/* Total demand */}
              <div className="card-dark">
                <div className="text-slate-400 text-sm uppercase tracking-wide mb-2">Total Demand</div>
                <div className="text-3xl font-bold text-cyan-400">{result.total_demand_lpm.toFixed(0)}</div>
                <div className="text-slate-400 text-sm">L/min</div>
              </div>

              {/* Critical pressure */}
              {result.critical_path && (
                <div className="card-dark">
                  <div className="text-slate-400 text-sm uppercase tracking-wide mb-2">
                    Critical Hydrant: {result.critical_path.critical_hydrant}
                  </div>
                  <div className={`text-3xl font-bold ${
                    result.critical_path.critical_pressure_bar < 2 ? 'text-red-400' : 'text-emerald-400'
                  }`}>
                    {result.critical_path.critical_pressure_bar.toFixed(2)}
                  </div>
                  <div className="text-slate-400 text-sm">bar (min pressure)</div>
                </div>
              )}
            </div>

            {/* Warnings */}
            {result.warnings.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-medium text-yellow-800 mb-1">Warnings</div>
                    <ul className="list-disc list-inside text-yellow-700 text-sm">
                      {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Critical path */}
            {result.critical_path && (
              <div className="card">
                <h3 className="font-semibold text-slate-800 mb-3">Critical Path (Lowest Pressure)</h3>
                <div className="flex items-center gap-2 flex-wrap">
                  {result.critical_path.path_nodes.map((nodeId, i) => (
                    <React.Fragment key={nodeId}>
                      <span className={`badge ${
                        nodeId === result.critical_path!.critical_hydrant ? 'badge-danger' : 'badge-success'
                      }`}>
                        {nodeId}
                      </span>
                      {i < result.critical_path!.path_nodes.length - 1 && (
                        <span className="text-slate-400">&rarr;</span>
                      )}
                    </React.Fragment>
                  ))}
                </div>
                <div className="text-sm text-slate-600 mt-2">
                  Total length: {result.critical_path.total_length_m.toFixed(1)} m
                </div>
              </div>
            )}

            {/* Pressure chart */}
            {result.critical_path && (
              <div className="card">
                <h3 className="font-semibold text-slate-800 mb-4">Pressure Profile (Critical Path)</h3>
                <PressureChart result={result} />
              </div>
            )}

            {/* Segments table */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-800">Segment Results</h3>
                <button onClick={handleExportSegments} className="btn btn-sm btn-secondary flex items-center gap-1">
                  <Download className="w-4 h-4" /> Export CSV
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Edge</th>
                      <th>From → To</th>
                      <th>Q (L/min)</th>
                      <th>v (m/s)</th>
                      <th>Re</th>
                      <th>f</th>
                      <th>ΔP major (bar)</th>
                      <th>ΔP minor (bar)</th>
                      <th>ΔP total (bar)</th>
                      <th>Regime</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.segments.map(seg => (
                      <tr key={seg.edge_id}>
                        <td className="font-medium">{seg.edge_id}</td>
                        <td className="text-slate-600">{seg.from_node} → {seg.to_node}</td>
                        <td className="font-mono">{seg.flow_lpm.toFixed(1)}</td>
                        <td className="font-mono">{seg.velocity_ms.toFixed(3)}</td>
                        <td className="font-mono">{seg.reynolds.toFixed(0)}</td>
                        <td className="font-mono">{seg.friction_factor.toFixed(5)}</td>
                        <td className="font-mono">{seg.delta_p_major_bar.toFixed(4)}</td>
                        <td className="font-mono">{seg.delta_p_minor_bar.toFixed(4)}</td>
                        <td className="font-mono font-medium">{seg.delta_p_total_bar.toFixed(4)}</td>
                        <td>
                          <span className={`badge ${seg.flow_regime === 'turbulent' ? 'badge-warning' : 'badge-success'}`}>
                            {seg.flow_regime}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Nodes table */}
            <div className="card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-800">Node Results</h3>
                <button onClick={handleExportNodes} className="btn btn-sm btn-secondary flex items-center gap-1">
                  <Download className="w-4 h-4" /> Export CSV
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Node</th>
                      <th>Type</th>
                      <th>Elevation (m)</th>
                      <th>Demand (L/min)</th>
                      <th>Pressure (bar)</th>
                      <th>Distance (m)</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.nodes.map(node => (
                      <tr key={node.node_id} className={node.pressure_bar < 0 ? 'bg-red-50' : ''}>
                        <td className="font-medium">{node.node_id}</td>
                        <td>
                          <span className={`badge badge-${node.type}`}>{node.type}</span>
                        </td>
                        <td className="font-mono">{node.elevation_m.toFixed(1)}</td>
                        <td className="font-mono">{node.demand_lpm.toFixed(0)}</td>
                        <td className={`font-mono font-medium ${
                          node.pressure_bar < 2 ? 'text-red-600' : 'text-emerald-600'
                        }`}>
                          {node.pressure_bar.toFixed(3)}
                        </td>
                        <td className="font-mono">{node.distance_from_source_m.toFixed(1)}</td>
                        <td>
                          {node.pressure_bar < 0 ? (
                            <span className="badge badge-danger">Negative!</span>
                          ) : node.pressure_bar < 2 ? (
                            <span className="badge badge-warning">Low</span>
                          ) : (
                            <span className="badge badge-success">OK</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
