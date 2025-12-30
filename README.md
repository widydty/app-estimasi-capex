# Hydrant Network Calculator

Aplikasi untuk menghitung pressure drop dan distribusi flow pada jaringan pipa hydrant bercabang (tree network).

## Fitur Utama

- Memodelkan jaringan pipa bercabang berbasis node-edge
- Menghitung debit (Q), kecepatan (v), Reynolds number, friction factor
- Menghitung pressure drop: major loss (Darcy-Weisbach) + minor losses (K)
- Menentukan hydrant paling kritis (tekanan terendah)
- Mendukung berbagai skenario demand hydrant
- Export hasil ke CSV
- Visualisasi pressure profile

## Teknologi

- **Backend**: Python FastAPI
- **Frontend**: React + TypeScript + Tailwind CSS
- **Charts**: Recharts

## Cara Menjalankan

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm atau yarn

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run backend server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend akan berjalan di http://localhost:8000

API Documentation: http://localhost:8000/docs

### Frontend

```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev
```

Frontend akan berjalan di http://localhost:3000

## Format Input

### Node

| Field | Type | Description |
|-------|------|-------------|
| node_id | string | ID unik node |
| type | string | `source`, `junction`, atau `hydrant` |
| elevation_m | number | Elevasi node (meter) |
| demand_lpm | number | Demand air (L/min), untuk hydrant |
| is_active | boolean | Apakah hydrant aktif |

### Edge (Pipe Segment)

| Field | Type | Description |
|-------|------|-------------|
| edge_id | string | ID unik pipa |
| from_node | string | Node asal (upstream) |
| to_node | string | Node tujuan (downstream) |
| length_m | number | Panjang pipa (meter) |
| diameter_mm | number | Diameter dalam pipa (mm) |
| roughness_mm | number | Kekasaran pipa (mm), default 0.045 |
| minor_K | number | Total K-factor minor loss |
| minor_components | array | Daftar komponen minor loss (opsional) |

### Contoh JSON Input

```json
{
  "nodes": [
    {"node_id": "S", "type": "source", "elevation_m": 0, "demand_lpm": 0, "is_active": true},
    {"node_id": "J1", "type": "junction", "elevation_m": 0, "demand_lpm": 0, "is_active": true},
    {"node_id": "H1", "type": "hydrant", "elevation_m": 0, "demand_lpm": 500, "is_active": true}
  ],
  "edges": [
    {
      "edge_id": "P1",
      "from_node": "S",
      "to_node": "J1",
      "length_m": 50,
      "diameter_mm": 150,
      "roughness_mm": 0.045,
      "minor_K": 0.5
    },
    {
      "edge_id": "P2",
      "from_node": "J1",
      "to_node": "H1",
      "length_m": 20,
      "diameter_mm": 65,
      "roughness_mm": 0.045,
      "minor_K": 3.5
    }
  ],
  "source_pressure_bar": 8.0,
  "fluid": {
    "density_kg_m3": 998.0,
    "viscosity_pa_s": 0.001002
  },
  "include_elevation": true,
  "pressure_unit": "bar"
}
```

## Metodologi Perhitungan

### Friction Factor

- **Laminar (Re < 2300)**: `f = 64/Re`
- **Turbulent**: Swamee-Jain equation
  ```
  f = 0.25 / [log10(ε/(3.7D) + 5.74/Re^0.9)]²
  ```

### Pressure Drop

**Major Loss (Darcy-Weisbach):**
```
ΔP_major = f × (L/D) × (ρv²/2)
```

**Minor Loss:**
```
ΔP_minor = K × (ρv²/2)
```

**Elevation Head:**
```
ΔP_static = ρ × g × Δz
```

### Flow Distribution (Tree Network)

Flow di setiap segmen = jumlah demand downstream dari segmen tersebut.

## K-Factor Reference

| Component | K |
|-----------|---|
| Gate valve (open) | 0.2 |
| Globe valve (open) | 10.0 |
| Ball valve (open) | 0.05 |
| Check valve (swing) | 2.5 |
| Elbow 90° (standard) | 0.9 |
| Elbow 90° (long radius) | 0.6 |
| Elbow 45° | 0.4 |
| Tee (run) | 0.3 |
| Tee (branch) | 1.0 |
| Entrance (sharp) | 0.5 |
| Exit | 1.0 |
| Hydrant outlet | 2.5 |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/calculate | Jalankan perhitungan |
| POST | /api/validate | Validasi struktur network |
| GET | /api/demo | Dapatkan demo network |
| GET | /api/k-factors | Dapatkan referensi K-factor |
| POST | /api/export/segments-csv | Export hasil segmen ke CSV |
| POST | /api/export/nodes-csv | Export hasil node ke CSV |

## Validasi

Aplikasi melakukan validasi:

1. ✅ Node ID dan Edge ID harus unik
2. ✅ Edge harus referensi ke node yang ada
3. ✅ Hanya boleh ada satu source node
4. ✅ Diameter dan panjang pipa > 0
5. ✅ Demand tidak boleh negatif
6. ✅ Network harus tree (tidak ada loop)
7. ✅ Semua node harus terhubung dari source
8. ✅ Minimal satu hydrant aktif dengan demand > 0

## Testing

```bash
# Run unit tests
cd backend
pytest tests/ -v
```

## Struktur Proyek

```
app-estimasi-capex/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── models.py        # Pydantic data models
│   ├── calculator.py    # Core calculation engine
│   ├── validation.py    # Network validation
│   └── tests/
│       ├── __init__.py
│       └── test_calculator.py
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── types.ts
│       ├── api.ts
│       ├── index.css
│       └── components/
│           └── PressureChart.tsx
├── data/
│   └── demo_network.json
├── requirements.txt
└── README.md
```

## Default Fluid Properties

- **Fluid**: Water at 20°C
- **Density**: 998 kg/m³
- **Viscosity**: 1.002×10⁻³ Pa·s

## License

MIT
