import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Search, MapPin, Compass, Layers, CheckCircle, AlertTriangle, Sparkles } from 'lucide-react';
import { BoundingBox, PresetLocation } from '../types';
import { PRESET_LOCATIONS } from '../data/presets';
import { calculateAoiStats } from '../services/analysisEngine';

interface MapPickerProps {
  bbox: BoundingBox;
  setBbox: (box: BoundingBox) => void;
  onSelectPreset: (preset: PresetLocation) => void;
  selectedPresetId?: string;
}

export const MapPicker: React.FC<MapPickerProps> = ({
  bbox,
  setBbox,
  onSelectPreset,
  selectedPresetId,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const rectLayerRef = useRef<L.Rectangle | null>(null);
  const baseLayersRef = useRef<{ osm: L.TileLayer; satellite: L.TileLayer } | null>(null);

  const [basemap, setBasemap] = useState<'satellite' | 'osm'>('satellite');
  const [presetFilter, setPresetFilter] = useState<'all' | 'india' | 'global'>('india');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [manualInputs, setManualInputs] = useState({
    west: bbox.west.toFixed(4),
    south: bbox.south.toFixed(4),
    east: bbox.east.toFixed(4),
    north: bbox.north.toFixed(4),
  });

  const aoiStats = calculateAoiStats(bbox);

  // Initialize Leaflet map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const latMid = (bbox.south + bbox.north) / 2;
    const lonMid = (bbox.west + bbox.east) / 2;

    const map = L.map(mapContainerRef.current, {
      center: [latMid, lonMid],
      zoom: 12,
      zoomControl: true,
      attributionControl: false,
    });

    // Basemaps
    const satelliteLayer = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 18 }
    );

    const osmLayer = L.tileLayer(
      'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      { maxZoom: 19 }
    );

    satelliteLayer.addTo(map);

    baseLayersRef.current = { osm: osmLayer, satellite: satelliteLayer };
    mapInstanceRef.current = map;

    // Draw initial AOI rectangle
    const bounds: L.LatLngBoundsExpression = [
      [bbox.south, bbox.west],
      [bbox.north, bbox.east],
    ];

    const rect = L.rectangle(bounds, {
      color: '#67e8f9',
      weight: 2,
      fillColor: '#38bdf8',
      fillOpacity: 0.15,
      dashArray: '4, 4',
    }).addTo(map);

    rectLayerRef.current = rect;

    // Allow user to click to re-center the AOI box
    map.on('click', (e: L.LeafletMouseEvent) => {
      const dLat = (bbox.north - bbox.south) / 2;
      const dLon = (bbox.east - bbox.west) / 2;
      const newBbox: BoundingBox = {
        west: e.latlng.lng - dLon,
        south: e.latlng.lat - dLat,
        east: e.latlng.lng + dLon,
        north: e.latlng.lat + dLat,
      };
      setBbox(newBbox);
    });

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Sync rectangle with bbox changes and flyTo if new location
  useEffect(() => {
    if (!mapInstanceRef.current || !rectLayerRef.current) return;

    const bounds: L.LatLngBoundsExpression = [
      [bbox.south, bbox.west],
      [bbox.north, bbox.east],
    ];

    rectLayerRef.current.setBounds(bounds);

    const latMid = (bbox.south + bbox.north) / 2;
    const lonMid = (bbox.west + bbox.east) / 2;
    const currentCenter = mapInstanceRef.current.getCenter();
    const distance = Math.hypot(currentCenter.lat - latMid, currentCenter.lng - lonMid);

    // If map center is significantly different from the new AOI center, smoothly fly to it
    if (distance > 0.03) {
      mapInstanceRef.current.flyTo([latMid, lonMid], 13, { duration: 1.2 });
    }

    setManualInputs({
      west: bbox.west.toFixed(4),
      south: bbox.south.toFixed(4),
      east: bbox.east.toFixed(4),
      north: bbox.north.toFixed(4),
    });
  }, [bbox]);

  // Basemap switch
  useEffect(() => {
    if (!mapInstanceRef.current || !baseLayersRef.current) return;
    const { osm, satellite } = baseLayersRef.current;
    if (basemap === 'satellite') {
      if (mapInstanceRef.current.hasLayer(osm)) mapInstanceRef.current.removeLayer(osm);
      if (!mapInstanceRef.current.hasLayer(satellite)) mapInstanceRef.current.addLayer(satellite);
    } else {
      if (mapInstanceRef.current.hasLayer(satellite)) mapInstanceRef.current.removeLayer(satellite);
      if (!mapInstanceRef.current.hasLayer(osm)) mapInstanceRef.current.addLayer(osm);
    }
  }, [basemap]);

  // Place Search (Nominatim)
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          searchQuery
        )}&limit=4`
      );
      const data = await res.json();
      setSearchResults(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectSearchResult = (item: any) => {
    const lat = parseFloat(item.lat);
    const lon = parseFloat(item.lon);

    // Default 5x5 km box around found location
    const dLat = 0.025;
    const dLon = 0.035;

    const newBbox: BoundingBox = {
      west: lon - dLon,
      south: lat - dLat,
      east: lon + dLon,
      north: lat + dLat,
    };

    setBbox(newBbox);
    setSearchResults([]);
    setSearchQuery(item.display_name.split(',')[0]);

    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([lat, lon], 12);
    }
  };

  const centerAoiOnCurrentView = () => {
    if (!mapInstanceRef.current) return;
    const center = mapInstanceRef.current.getCenter();
    const dLat = Math.abs(bbox.north - bbox.south) / 2;
    const dLon = Math.abs(bbox.east - bbox.west) / 2;

    const newBbox: BoundingBox = {
      west: center.lng - dLon,
      south: center.lat - dLat,
      east: center.lng + dLon,
      north: center.lat + dLat,
    };
    setBbox(newBbox);
  };

  const applyManualCoordinates = () => {
    const w = parseFloat(manualInputs.west);
    const s = parseFloat(manualInputs.south);
    const e = parseFloat(manualInputs.east);
    const n = parseFloat(manualInputs.north);

    if (isNaN(w) || isNaN(s) || isNaN(e) || isNaN(n) || w >= e || s >= n) {
      alert('Please enter valid coordinates where West < East and South < North');
      return;
    }

    const newBbox: BoundingBox = { west: w, south: s, east: e, north: n };
    setBbox(newBbox);

    if (mapInstanceRef.current) {
      mapInstanceRef.current.fitBounds([
        [s, w],
        [n, e],
      ]);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Quick Curated Hotspots Bar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 backdrop-blur-sm">
        <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-cyan-400">
              <Sparkles className="h-3.5 w-3.5" />
              Real-Time Change Presets
            </span>
            <span className="text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full font-mono">
              12 Benchmarks
            </span>
          </div>

          {/* Regional Filter Tabs */}
          <div className="flex items-center rounded-lg border border-slate-800 bg-slate-950 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setPresetFilter('india')}
              className={`rounded-md px-2.5 py-1 font-semibold transition-all ${
                presetFilter === 'india'
                  ? 'bg-gradient-to-r from-orange-500/20 to-emerald-500/20 text-white border border-emerald-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              🇮🇳 India Corridors (9)
            </button>
            <button
              type="button"
              onClick={() => setPresetFilter('global')}
              className={`rounded-md px-2.5 py-1 font-semibold transition-all ${
                presetFilter === 'global'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              🌍 Global (3)
            </button>
            <button
              type="button"
              onClick={() => setPresetFilter('all')}
              className={`rounded-md px-2.5 py-1 font-semibold transition-all ${
                presetFilter === 'all'
                  ? 'bg-slate-700 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              All (12)
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-3 max-h-[220px] overflow-y-auto pr-1">
          {PRESET_LOCATIONS.filter((p) => {
            if (presetFilter === 'india') return !p.tag.startsWith('Global');
            if (presetFilter === 'global') return p.tag.startsWith('Global');
            return true;
          }).map((preset) => {
            const isSelected = selectedPresetId === preset.id;
            return (
              <button
                key={preset.id}
                onClick={() => {
                  onSelectPreset(preset);
                  if (mapInstanceRef.current) {
                    const latMid = (preset.bbox.south + preset.bbox.north) / 2;
                    const lonMid = (preset.bbox.west + preset.bbox.east) / 2;
                    mapInstanceRef.current.flyTo([latMid, lonMid], 12, { duration: 1.2 });
                  }
                }}
                className={`flex flex-col items-start rounded-lg p-2 text-left transition-all ${
                  isSelected
                    ? 'border border-cyan-500 bg-cyan-950/50 text-cyan-200 shadow-[0_0_12px_rgba(103,232,249,0.2)]'
                    : 'border border-slate-800 bg-slate-800/40 text-slate-300 hover:border-slate-700 hover:bg-slate-800/80'
                }`}
              >
                <div className="flex items-center justify-between w-full">
                  <span className="text-[10px] font-semibold text-cyan-400">{preset.tag}</span>
                  {isSelected && <CheckCircle className="h-3 w-3 text-cyan-400" />}
                </div>
                <span className="text-xs font-semibold text-white line-clamp-1 mt-0.5">
                  {preset.name.split(',')[0]}
                </span>
                <span className="text-[10px] text-slate-400 line-clamp-1">{preset.name.split(',')[1] || preset.subtitle}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Map Control Bar & Place Search */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <form onSubmit={handleSearch} className="relative flex-1 min-w-[260px]">
          <div className="flex items-center rounded-lg border border-slate-700 bg-slate-900/90 px-3 py-1.5 focus-within:border-cyan-500 focus-within:ring-1 focus-within:ring-cyan-500">
            <Search className="h-4 w-4 text-slate-400 mr-2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search place, city, or coordinates..."
              className="w-full bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none"
            />
            {isSearching && (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
            )}
          </div>

          {searchResults.length > 0 && (
            <div className="absolute left-0 right-0 top-full z-[1000] mt-1 overflow-hidden rounded-lg border border-slate-700 bg-slate-900 shadow-xl">
              {searchResults.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectSearchResult(item)}
                  className="w-full px-3 py-2 text-left text-xs text-slate-200 hover:bg-slate-800 flex items-center gap-2 border-b border-slate-800 last:border-none"
                >
                  <MapPin className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                  <span className="line-clamp-1">{item.display_name}</span>
                </button>
              ))}
            </div>
          )}
        </form>

        <div className="flex items-center gap-2">
          {/* Basemap Switcher */}
          <div className="flex items-center rounded-lg border border-slate-700 bg-slate-900 p-0.5 text-xs">
            <button
              type="button"
              onClick={() => setBasemap('satellite')}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                basemap === 'satellite'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Satellite
            </button>
            <button
              type="button"
              onClick={() => setBasemap('osm')}
              className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
                basemap === 'osm'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Street Map
            </button>
          </div>

          <button
            type="button"
            onClick={centerAoiOnCurrentView}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 hover:border-slate-600 hover:text-white transition-colors"
          >
            <Compass className="h-3.5 w-3.5 text-cyan-400" />
            Center AOI Here
          </button>
        </div>
      </div>

      {/* Map Shell */}
      <div className="relative h-[360px] w-full overflow-hidden rounded-xl border border-slate-800 shadow-2xl">
        <div ref={mapContainerRef} className="h-full w-full" />

        {/* Live AOI Dimension Indicator Overlay */}
        <div className="absolute bottom-3 left-3 z-[900] flex flex-wrap items-center gap-2 rounded-lg border border-slate-800/80 bg-slate-950/85 px-3 py-2 text-xs backdrop-blur-md">
          <div>
            <span className="text-[10px] uppercase text-slate-400 block font-semibold">AOI Footprint</span>
            <span className="font-semibold text-white">
              {aoiStats.widthKm.toFixed(1)} km × {aoiStats.heightKm.toFixed(1)} km
            </span>
          </div>
          <div className="h-6 w-px bg-slate-800 mx-1" />
          <div>
            <span className="text-[10px] uppercase text-slate-400 block font-semibold">Area</span>
            <span className="font-semibold text-cyan-300">
              {aoiStats.areaKm2.toFixed(1)} km² ({Math.round(aoiStats.areaHa).toLocaleString()} ha)
            </span>
          </div>
          <div className="h-6 w-px bg-slate-800 mx-1" />
          <div className="flex items-center gap-1">
            {aoiStats.isWithinLimit ? (
              <span className="inline-flex items-center gap-1 rounded bg-emerald-950/80 px-2 py-0.5 text-[10px] font-medium text-emerald-300 border border-emerald-800/50">
                <CheckCircle className="h-3 w-3" /> Sentinel-2 10m Ready
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded bg-amber-950/80 px-2 py-0.5 text-[10px] font-medium text-amber-300 border border-amber-800/50">
                <AlertTriangle className="h-3 w-3" /> Large Area (&gt;15km)
              </span>
            )}
          </div>
        </div>

        {/* Hint to click map */}
        <div className="absolute top-3 left-3 z-[900] rounded-md bg-slate-950/70 px-2 py-1 text-[11px] text-slate-400 backdrop-blur-sm pointer-events-none">
          Click anywhere on the map to relocate the monitoring box
        </div>
      </div>

      {/* Manual Coordinate Collapsible */}
      <details className="group rounded-xl border border-slate-800/80 bg-slate-900/40 p-3 text-xs">
        <summary className="cursor-pointer font-medium text-slate-400 hover:text-white flex items-center justify-between">
          <span>Manual Bounding Box Coordinates (WGS 84)</span>
          <span className="text-[10px] text-cyan-400 group-open:rotate-180 transition-transform">▼</span>
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <div>
            <label className="text-[10px] text-slate-400">West (Min Lon)</label>
            <input
              type="text"
              value={manualInputs.west}
              onChange={(e) => setManualInputs({ ...manualInputs, west: e.target.value })}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400">South (Min Lat)</label>
            <input
              type="text"
              value={manualInputs.south}
              onChange={(e) => setManualInputs({ ...manualInputs, south: e.target.value })}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400">East (Max Lon)</label>
            <input
              type="text"
              value={manualInputs.east}
              onChange={(e) => setManualInputs({ ...manualInputs, east: e.target.value })}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400">North (Max Lat)</label>
            <input
              type="text"
              value={manualInputs.north}
              onChange={(e) => setManualInputs({ ...manualInputs, north: e.target.value })}
              className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200"
            />
          </div>
        </div>
        <button
          type="button"
          onClick={applyManualCoordinates}
          className="mt-2.5 rounded bg-slate-800 px-3 py-1 font-medium text-cyan-300 hover:bg-slate-700"
        >
          Apply Custom Coordinates
        </button>
      </details>
    </div>
  );
};
