# Satellite Change Detection & Land Audit Platform

An interactive React + TypeScript platform for multi-spectral satellite change detection and environmental land auditing using Copernicus Sentinel-2 L2A (10 m ground sampling resolution) imagery.

## Key Features

- **Interactive Global Map & AOI Selector**:
  - Interactive Leaflet map with OpenStreetMap and High-Resolution Satellite basemaps.
  - One-click quick-start presets for major global land-change hotspots (Palm Jumeirah Dubai, Aral Sea desiccation, Amazon deforestation, California wildfire burn scars, Imperial Valley agriculture, Madrid expansion).
  - OpenStreetMap Nominatim place search with instant auto-complete and flying camera.
  - Precise bounding box dimension calculations (width km, height km, total hectares/km²) with real-time Sentinel-2 10m validation.
  - Manual WGS 84 coordinate input support.

- **Multi-Spectral Detection Profiles**:
  - **General Change Detection**: Multi-spectral balance (NDVI drop + NDBI gain).
  - **Urban & Built-Up Expansion**: Normalized Difference Built-up Index (NDBI) and Bare Soil Index (BSI).
  - **Forest Canopy & Vegetation Loss**: Normalized Difference Vegetation Index (NDVI) and Normalized Burn Ratio (NBR).
  - **Agricultural Cropping Cycles**: Cropping dynamics, seasonal phenology, and fallow field detection.
  - **Water Bodies & Shorelines**: Modified Normalized Difference Water Index (MNDWI).
  - **Linear Infrastructure & Clearing**: Ground clearing and transport corridor encroachment.

- **Visual Comparison & Evidence Layers**:
  - **Interactive Swipe Slider**: Smooth dual-image split slider with draggable handle and range controls.
  - **Side-by-Side Dual View**: Simultaneous synchronized comparison.
  - **Astronomical Blink Comparator**: Alternating flicker mode for spotting subtle micro-shifts.
  - **Multi-Spectral Evidence Layers**:
    - Change Overlay: Translucent crimson highlight polygons atop high-res after imagery.
    - Binary Decision Mask: Clean connected-component filtered mask.
    - Continuous Viridis Heatmap: Colour-blind-safe Viridis gradient of spectral rule magnitude.

- **Detailed Analysis & Audit Report**:
  - Executive Findings Summary in plain English.
  - Quantified surface KPIs: Percent changed, net hectares modified, total area, and cloud-mask percentage.
  - Environmental Impact Analysis: Biomass loss estimation, new impervious surface calculations, and water volume shifts.
  - Categorical distribution bar chart and detected cluster inventory table.
  - Actionable recommendations for GIS analysts and field inspectors.
  - Complete scientific provenance audit trail (sensors, spectral bands, formulas, and MMU thresholds).
  - One-click exports: Downloadable PDF Report, GeoJSON Feature Collection, CSV table, and image layers.

- **Dual-Image Pair Upload**:
  - Drag-and-drop comparison of custom drone, aerial, or satellite orthophotos.
  - Perceptual color and structural differential analysis with identical detailed reporting capabilities.

- **Local Audit History**:
  - Stored in browser `localStorage` for immediate recall, re-inspection, and comparative auditing.

## Tech Stack

- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
- **Mapping**: Leaflet, OpenStreetMap, Esri World Imagery
- **Reporting & Export**: jsPDF, GeoJSON, CSV
- **Icons**: Lucide React
