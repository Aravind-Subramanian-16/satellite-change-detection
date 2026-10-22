# Satellite Change Detection & Land Audit Platform

An interactive React + TypeScript prototype for comparing provider imagery and screening visible RGB pixel differences. It is not a multi-spectral land-cover classifier or validated environmental monitoring product. Provider images may be composites; when a complete image pair is unavailable, the app clearly labels generated demonstration imagery instead of presenting it as a real observation.

## Key Features

- **Interactive Global Map & AOI Selector**:
  - Interactive Leaflet map with OpenStreetMap and High-Resolution Satellite basemaps.
  - One-click quick-start presets for major global land-change hotspots (Palm Jumeirah Dubai, Aral Sea desiccation, Amazon deforestation, California wildfire burn scars, Imperial Valley agriculture, Madrid expansion).
  - OpenStreetMap Nominatim place search with instant auto-complete and flying camera.
  - Bounding-box dimension estimates from selected coordinates; these do not validate imagery ground resolution.
  - Manual WGS 84 coordinate input support.

- **RGB Difference Screening**:
  - Date/profile inputs provide search context only; available imagery may not match requested acquisition dates.
  - Visible RGB pixel differences are a screening signal only. No semantic classification, physical-area estimate, object count, or accuracy score is produced.
  - The app does not apply image registration, cloud/shadow masking, atmospheric correction, or multispectral-index calculations.

- **Visual Comparison & Evidence Layers**:
  - **Interactive Swipe Slider**: Smooth dual-image split slider with draggable handle and range controls.
  - **Synchronized Zoom & Pan**: Inspect both dates at up to 5× zoom with matching pan in swipe, side-by-side, and blink views; wheel zoom and drag pan are supported.
  - **Side-by-Side Dual View**: Simultaneous synchronized comparison that preserves the full image frame.
  - **Astronomical Blink Comparator**: Alternating flicker mode for spotting subtle micro-shifts.
  - RGB difference overlay, threshold mask, and Viridis display layer for visual inspection; these are not calibrated confidence or spectral-index maps.

- **Detailed Analysis & Audit Report**:
  - Pixel-count and threshold summaries with limitations shown beside results.
  - PDF/CSV screening evidence exports. GeoJSON is unavailable where validated georeferenced regions are not produced.

- **Dual-Image Pair Upload**:
  - Compare custom RGB imagery and delineate a focused region on the Before image; the matching normalized crop is applied to both dates and can be refined and reanalyzed.
  - Pixel-difference screening uses the lower-resolution crop, capped at 2,048 px per dimension. Results explicitly warn that registration, geospatial scale, semantic classes, and accuracy are not inferred.

- **Local Audit History**:
  - Stored in browser `localStorage` for immediate recall, re-inspection, and comparative auditing.

## Tech Stack

- **Frontend**: React 18, TypeScript, Tailwind CSS, Vite
- **Mapping**: Leaflet, OpenStreetMap, Esri World Imagery
- **Reporting & Export**: jsPDF and CSV; GeoJSON for georeferenced outputs only
- **Icons**: Lucide React
