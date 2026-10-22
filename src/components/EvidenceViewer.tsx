import React, { useState } from 'react';
import { Layers, Download, Info } from 'lucide-react';

interface EvidenceViewerProps {
  overlayImage: string;
  maskImage: string;
  heatmapImage: string;
  percentChanged: number;
  profileLabel: string;
}

export const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  overlayImage,
  maskImage,
  heatmapImage,
  percentChanged,
  profileLabel,
}) => {
  const [activeLayer, setActiveLayer] = useState<'overlay' | 'mask' | 'heatmap'>('overlay');

  const getImageSrc = () => {
    switch (activeLayer) {
      case 'overlay':
        return overlayImage;
      case 'mask':
        return maskImage;
      case 'heatmap':
        return heatmapImage;
    }
  };

  const getCaption = () => {
    switch (activeLayer) {
      case 'overlay':
        return `Red semi-transparent highlighting identifies pixels where spectral criteria were exceeded (${percentChanged}% of AOI).`;
      case 'mask':
        return 'Discrete binary decision mask filtered with minimum mapping unit (MMU) connected component removal.';
      case 'heatmap':
        return 'Continuous spectral-rule evidence on a colour-blind-safe Viridis scale: dark purple is near 0.0 delta, yellow indicates maximum spectral perturbation (e.g. high NDVI loss or NDBI gain).';
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Layer selector tabs */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-900/80 p-1 text-xs">
          <button
            onClick={() => setActiveLayer('overlay')}
            className={`rounded-md px-3 py-1 font-medium transition-colors ${
              activeLayer === 'overlay'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Change Overlay
          </button>
          <button
            onClick={() => setActiveLayer('mask')}
            className={`rounded-md px-3 py-1 font-medium transition-colors ${
              activeLayer === 'mask'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Binary Mask
          </button>
          <button
            onClick={() => setActiveLayer('heatmap')}
            className={`rounded-md px-3 py-1 font-medium transition-colors ${
              activeLayer === 'heatmap'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Rule Evidence Heatmap
          </button>
        </div>

        <a
          href={getImageSrc()}
          download={`change-evidence-${activeLayer}.png`}
          className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
        >
          <Download className="h-3.5 w-3.5 text-cyan-400" />
          Export Layer
        </a>
      </div>

      {/* Layer Preview */}
      <div className="relative aspect-square w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-2xl">
        <img
          src={getImageSrc()}
          alt={activeLayer}
          className="h-full w-full object-cover"
        />

        <div className="absolute top-3 left-3 rounded-md bg-slate-950/80 px-2.5 py-1 text-xs font-semibold text-slate-200 border border-slate-800 backdrop-blur-md flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5 text-cyan-400" />
          <span>Layer: {activeLayer.toUpperCase()}</span>
        </div>
      </div>

      {/* Viridis Legend (when Heatmap is selected) */}
      {activeLayer === 'heatmap' && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-2.5 text-xs">
          <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
            <span>Low Evidence (0.0)</span>
            <span className="font-semibold text-cyan-300">Viridis Continuous Spectral Scale</span>
            <span>High Evidence (1.0)</span>
          </div>
          <div
            className="h-3.5 w-full rounded-md shadow-inner"
            style={{
              background: 'linear-gradient(to right, #440154, #3b528b, #21918c, #5ec962, #fde725)',
            }}
          />
        </div>
      )}

      {/* Caption */}
      <div className="flex items-start gap-2 text-xs text-slate-400 bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/60">
        <Info className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
        <span>{getCaption()}</span>
      </div>
    </div>
  );
};
