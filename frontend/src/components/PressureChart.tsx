import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { CalculationResult } from '../types';

interface PressureChartProps {
  result: CalculationResult;
}

interface ChartDataPoint {
  distance: number;
  pressure: number;
  nodeId: string;
  type: string;
}

export const PressureChart: React.FC<PressureChartProps> = ({ result }) => {
  const chartData = useMemo(() => {
    if (!result.critical_path) return [];

    // Get nodes along critical path in order
    const data: ChartDataPoint[] = [];

    for (const nodeId of result.critical_path.path_nodes) {
      const nodeResult = result.nodes.find(n => n.node_id === nodeId);
      if (nodeResult) {
        data.push({
          distance: nodeResult.distance_from_source_m,
          pressure: nodeResult.pressure_bar,
          nodeId: nodeResult.node_id,
          type: nodeResult.type
        });
      }
    }

    return data.sort((a, b) => a.distance - b.distance);
  }, [result]);

  if (chartData.length === 0) {
    return (
      <div className="text-center text-slate-400 py-8">
        No data available for pressure chart
      </div>
    );
  }

  const minPressure = Math.min(...chartData.map(d => d.pressure));
  const maxPressure = Math.max(...chartData.map(d => d.pressure));
  const yMin = Math.floor(Math.min(0, minPressure - 0.5));
  const yMax = Math.ceil(maxPressure + 0.5);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="distance"
          label={{ value: 'Distance from Source (m)', position: 'bottom', offset: 0 }}
          stroke="#64748b"
          tick={{ fill: '#64748b', fontSize: 12 }}
        />
        <YAxis
          domain={[yMin, yMax]}
          label={{ value: 'Pressure (bar)', angle: -90, position: 'insideLeft', offset: 10 }}
          stroke="#64748b"
          tick={{ fill: '#64748b', fontSize: 12 }}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              const data = payload[0].payload as ChartDataPoint;
              return (
                <div className="bg-white shadow-lg rounded-lg p-3 border border-slate-200">
                  <div className="font-semibold text-slate-800">{data.nodeId}</div>
                  <div className="text-sm text-slate-600 capitalize">{data.type}</div>
                  <div className="mt-2 space-y-1 text-sm">
                    <div className="flex justify-between gap-4">
                      <span className="text-slate-500">Distance:</span>
                      <span className="font-mono">{data.distance.toFixed(1)} m</span>
                    </div>
                    <div className="flex justify-between gap-4">
                      <span className="text-slate-500">Pressure:</span>
                      <span className={`font-mono font-medium ${
                        data.pressure < 2 ? 'text-red-600' : 'text-emerald-600'
                      }`}>
                        {data.pressure.toFixed(3)} bar
                      </span>
                    </div>
                  </div>
                </div>
              );
            }
            return null;
          }}
        />
        <Legend />

        {/* Warning line at 2 bar */}
        <ReferenceLine
          y={2}
          stroke="#f59e0b"
          strokeDasharray="5 5"
          label={{ value: 'Min Recommended (2 bar)', fill: '#f59e0b', fontSize: 11 }}
        />

        {/* Critical line at 0 bar */}
        {minPressure < 1 && (
          <ReferenceLine
            y={0}
            stroke="#ef4444"
            strokeDasharray="5 5"
            label={{ value: 'Zero Gauge', fill: '#ef4444', fontSize: 11 }}
          />
        )}

        <Line
          type="monotone"
          dataKey="pressure"
          name="Pressure"
          stroke="#6366f1"
          strokeWidth={2}
          dot={(props) => {
            const { cx, cy, payload } = props;
            const data = payload as ChartDataPoint;

            let fill = '#6366f1';
            if (data.type === 'source') fill = '#3b82f6';
            else if (data.type === 'hydrant') fill = '#f97316';
            else fill = '#64748b';

            return (
              <circle
                cx={cx}
                cy={cy}
                r={6}
                fill={fill}
                stroke="#fff"
                strokeWidth={2}
              />
            );
          }}
          activeDot={{ r: 8, stroke: '#6366f1', strokeWidth: 2, fill: '#fff' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default PressureChart;
