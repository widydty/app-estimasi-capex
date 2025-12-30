/**
 * API client for Hydrant Network Calculator backend
 */

import { NetworkInput, CalculationResult, ValidationResponse } from './types';

const API_BASE = '/api';

export async function calculateNetwork(network: NetworkInput): Promise<CalculationResult> {
  const response = await fetch(`${API_BASE}/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(network)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.message || error.detail || 'Calculation failed');
  }

  return response.json();
}

export async function validateNetwork(network: NetworkInput): Promise<ValidationResponse> {
  const response = await fetch(`${API_BASE}/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(network)
  });

  if (!response.ok) {
    throw new Error('Validation request failed');
  }

  return response.json();
}

export async function getDemoNetwork(): Promise<NetworkInput> {
  const response = await fetch(`${API_BASE}/demo`);

  if (!response.ok) {
    throw new Error('Failed to fetch demo network');
  }

  return response.json();
}

export async function getKFactors(): Promise<Record<string, number>> {
  const response = await fetch(`${API_BASE}/k-factors`);

  if (!response.ok) {
    throw new Error('Failed to fetch K-factors');
  }

  return response.json();
}

export async function exportSegmentsCSV(result: CalculationResult): Promise<Blob> {
  const response = await fetch(`${API_BASE}/export/segments-csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result, pressure_unit: 'bar' })
  });

  if (!response.ok) {
    throw new Error('Failed to export segments CSV');
  }

  return response.blob();
}

export async function exportNodesCSV(result: CalculationResult): Promise<Blob> {
  const response = await fetch(`${API_BASE}/export/nodes-csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result, pressure_unit: 'bar' })
  });

  if (!response.ok) {
    throw new Error('Failed to export nodes CSV');
  }

  return response.blob();
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
