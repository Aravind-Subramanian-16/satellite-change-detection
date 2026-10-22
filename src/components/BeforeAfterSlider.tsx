import React, { useState, useRef, useEffect } from 'react';
import {
  Columns,
  SplitSquareVertical,
  Eye,
  MapPin,
  Building,
  Trees,
  Navigation,
  Store,
  Droplets,
  X,
  Search,
  Maximize2,
  Minimize2,
  Sparkles,
} from 'lucide-react';
import { DetectedFeature } from '../types';

interface BeforeAfterSliderProps {
  imageBefore: string;
  imageAfter: string;
  dateBefore: string;
  dateAfter: string;
  detectedFeatures?: DetectedFeature[];
  sourceBefore?: string;
  sourceAfter?: string;
}

export const BeforeAfterSlider: React.FC<BeforeAfterSliderProps> = ({
  imageBefore,
  imageAfter,
  dateBefore,
  dateAfter,
  detectedFeatures = [],
  sourceBefore,
  sourceAfter,
}) => {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [viewMode, setViewMode] = useState<'split' | 'side' | 'flicker'>('split');
  const [flickerState, setFlickerState] = useState<'before' | 'after'>('before');
  const [isFlickering, setIsFlickering] = useState(false);
  const [showPins, setShowPins] = useState(true);
  const [activePin, setActivePin] = useState<DetectedFeature | null>(null);

  // HD Magnifier (Loupe) state
  const [isMagnifierActive, setIsMagnifierActive] = useState(false);
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  // Flicker animation loop
  useEffect(() => {
    let interval: any = null;
    if (viewMode === 'flicker' && isFlickering) {
      interval = setInterval(() => {
        setFlickerState((prev) => (prev === 'before' ? 'after' : 'before'));
      }, 550);
    }
    return () => clearInterval(interval);
  }, [viewMode, isFlickering]);

  const handlePointerDown = (e: React.PointerEvent) => {
    if (isMagnifierActive) return;
    if ((e.target as HTMLElement).closest('.pin-badge') || (e.target as HTMLElement).closest('.pin-card')) {
      return;
    }
    isDragging.current = true;
  };

  const handlePointerUp = () => {
    isDragging.current = false;
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height));

    if (isMagnifierActive) {
      setMousePos({ x, y });
    }

    if (isDragging.current) {
      const percent = Math.round((x / rect.width) * 100);
      setSliderPosition(percent);
    }
  };

  const handlePointerLeave = () => {
    if (isMagnifierActive) {
      setMousePos(null);
    }
    isDragging.current = false;
  };

  const getPinIcon = (cat: DetectedFeature['category']) => {
    switch (cat) {
      case 'building':
        return <Building className="h-3 w-3 text-amber-300" />;
      case 'commercial':
        return <Store className="h-3 w-3 text-rose-300" />;
      case 'cleared_trees':
        return <Trees className="h-3 w-3 text-emerald-300" />;
      case 'road':
        return <Navigation className="h-3 w-3 text-purple-300" />;
      case 'water_loss':
        return <Droplets className="h-3 w-3 text-cyan-300" />;
      default:
        return <MapPin className="h-3 w-3 text-cyan-300" />;
    }
  };

  const getPinBg = (cat: DetectedFeature['category']) => {
    switch (cat) {
      case 'building':
        return 'bg-amber-950/90 border-amber-500/80 text-amber-200';
      case 'commercial':
        return 'bg-rose-950/90 border-rose-500/80 text-rose-200';
      case 'cleared_trees':
        return 'bg-emerald-950/90 border-emerald-500/80 text-emerald-200';
      case 'road':
        return 'bg-purple-950/90 border-purple-500/80 text-purple-200';
      case 'water_loss':
        return 'bg-cyan-950/90 border-cyan-500/80 text-cyan-200';
      default:
        return 'bg-blue-950/90 border-blue-500/80 text-blue-200';
    }
  };

  return (
    <div className={`flex flex-col gap-3 ${isFullscreen ? 'fixed inset-0 z-50 bg-slate-950/95 p-6 backdrop-blur-xl overflow-y-auto' : ''}`}>
      {/* Controls & Mode Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/80 p-1 text-xs">
          <button
            onClick={() => {
              setViewMode('split');
              setIsFlickering(false);
            }}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 font-medium transition-colors ${
              viewMode === 'split' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            <SplitSquareVertical className="h-3.5 w-3.5" />
            Swipe Slider
          </button>

          <button
            onClick={() => {
              setViewMode('side');
              setIsFlickering(false);
            }}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 font-medium transition-colors ${
              viewMode === 'side' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Columns className="h-3.5 w-3.5" />
            Side-by-Side
          </button>

          <button
            onClick={() => {
              setViewMode('flicker');
              setIsFlickering(true);
            }}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 font-medium transition-colors ${
              viewMode === 'flicker' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Eye className="h-3.5 w-3.5" />
            Blink Comparator
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* HD Magnifier Loupe Toggle */}
          <button
            onClick={() => setIsMagnifierActive(!isMagnifierActive)}
            title="Toggle 2.5x HD Magnifier to inspect individual buildings and roads in crisp resolution"
            className={`flex items-center gap-1.5 rounded-xl px-3 py-1 text-xs font-semibold border transition-all ${
              isMagnifierActive
                ? 'bg-amber-950/80 border-amber-500 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.25)]'
                : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-white'
            }`}
          >
            <Search className="h-3.5 w-3.5 text-amber-400" />
            <span>HD Loupe (2.5x Zoom)</span>
          </button>

          {detectedFeatures.length > 0 && (
            <button
              onClick={() => setShowPins(!showPins)}
              className={`flex items-center gap-1.5 rounded-xl px-3 py-1 text-xs font-semibold border transition-all ${
                showPins
                  ? 'bg-cyan-950/60 border-cyan-500/60 text-cyan-300 shadow-[0_0_10px_rgba(103,232,249,0.2)]'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:text-white'
              }`}
            >
              <MapPin className="h-3.5 w-3.5" />
              <span>Pinpoint Objects ({detectedFeatures.length})</span>
            </button>
          )}

          {/* Fullscreen Expand */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Exit Fullscreen' : 'View High-Resolution Satellite in Fullscreen'}
            className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/80 p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
        </div>

        {viewMode === 'split' && !isMagnifierActive && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Swipe:</span>
            <input
              type="range"
              min="0"
              max="100"
              value={sliderPosition}
              onChange={(e) => setSliderPosition(Number(e.target.value))}
              className="h-1.5 w-24 accent-blue-500 bg-slate-800 rounded-lg cursor-pointer"
            />
            <span className="font-mono text-[11px] text-cyan-400">{sliderPosition}%</span>
          </div>
        )}
      </div>

      {/* Split Swipe View */}
      {viewMode === 'split' && (
        <div
          ref={containerRef}
          onPointerDown={handlePointerDown}
          onPointerUp={handlePointerUp}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          className={`relative aspect-square w-full select-none overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-2xl ${
            isMagnifierActive ? 'cursor-crosshair' : 'cursor-ew-resize'
          }`}
        >
          {/* Base Layer: AFTER Image (Underneath) */}
          <img
            src={imageAfter}
            alt="Current After State"
            className="pointer-events-none absolute inset-0 h-full w-full object-cover"
          />

          {/* Top Layer: BEFORE Image (Clipped by sliderPosition) */}
          <div
            className="absolute inset-0 h-full w-full overflow-hidden"
            style={{ width: `${sliderPosition}%` }}
          >
            <img
              src={imageBefore}
              alt="Historical Before State"
              style={{
                width: containerRef.current ? `${containerRef.current.clientWidth}px` : '100%',
                maxWidth: 'none',
              }}
              className="pointer-events-none h-full object-cover"
            />
          </div>

          {/* Slider Divider Bar */}
          {!isMagnifierActive && (
            <div
              className="absolute top-0 bottom-0 z-20 w-1 bg-white shadow-[0_0_12px_rgba(255,255,255,0.8)]"
              style={{ left: `${sliderPosition}%` }}
            >
              <div className="absolute top-1/2 -left-3.5 -translate-y-1/2 flex h-8 w-8 items-center justify-center rounded-full bg-white shadow-xl text-slate-900 border-2 border-slate-900">
                <SplitSquareVertical className="h-4 w-4" />
              </div>
            </div>
          )}

          {/* HD Magnifier Lens (Loupe) */}
          {isMagnifierActive && mousePos && containerRef.current && (
            <div
              className="pointer-events-none absolute z-40 h-44 w-44 rounded-full border-4 border-amber-400 bg-slate-950 shadow-[0_0_30px_rgba(245,158,11,0.5)] overflow-hidden"
              style={{
                left: `${mousePos.x - 88}px`,
                top: `${mousePos.y - 88}px`,
              }}
            >
              <img
                src={mousePos.x / (containerRef.current.clientWidth || 1) * 100 > sliderPosition ? imageAfter : imageBefore}
                alt="Magnified View"
                style={{
                  position: 'absolute',
                  width: `${(containerRef.current.clientWidth || 512) * 2.5}px`,
                  height: `${(containerRef.current.clientHeight || 512) * 2.5}px`,
                  left: `${-mousePos.x * 2.5 + 88}px`,
                  top: `${-mousePos.y * 2.5 + 88}px`,
                  maxWidth: 'none',
                }}
              />
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-slate-950/90 px-2 py-0.5 text-[10px] font-bold text-amber-300 border border-amber-500/60 shadow">
                2.5x HD
              </div>
            </div>
          )}

          {/* Interactive Feature Pins Overlay */}
          {showPins && detectedFeatures.map((feat) => {
            const isSelected = activePin?.id === feat.id;
            return (
              <div
                key={feat.id}
                onClick={(e) => {
                  e.stopPropagation();
                  setActivePin(feat);
                }}
                className={`pin-badge absolute z-30 -translate-x-1/2 -translate-y-1/2 cursor-pointer transition-all duration-200 ${
                  isSelected ? 'scale-125 z-40' : 'hover:scale-115'
                }`}
                style={{
                  left: `${feat.pixelLocation.x}%`,
                  top: `${feat.pixelLocation.y}%`,
                }}
              >
                <div
                  className={`flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-bold shadow-xl border backdrop-blur-md ${getPinBg(feat.category)}`}
                >
                  {getPinIcon(feat.category)}
                  <span className="hidden sm:inline">{feat.name}</span>
                </div>
              </div>
            );
          })}

          {/* Pin Details Drawer Card */}
          {activePin && (
            <div className="pin-card absolute bottom-4 left-4 right-4 z-40 rounded-xl border border-cyan-500/50 bg-slate-950/95 p-4 shadow-2xl backdrop-blur-md animate-fadeIn">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                    {getPinIcon(activePin.category)}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                      <span>{activePin.name}</span>
                      <span className="rounded bg-slate-800 px-1.5 py-0.2 text-[10px] font-normal text-cyan-300">
                        {activePin.metric}
                      </span>
                    </h4>
                    <p className="text-[11px] text-cyan-300 font-semibold">{activePin.story}</p>
                  </div>
                </div>

                <button
                  onClick={() => setActivePin(null)}
                  className="rounded-lg p-1 text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-2.5 grid grid-cols-2 gap-2 text-[10px] pt-2 border-t border-slate-800/80">
                <div className="bg-slate-900/60 p-2 rounded-lg">
                  <span className="text-slate-400 font-bold block mb-0.5">Before ({dateBefore}):</span>
                  <span className="text-slate-200">{activePin.beforeState}</span>
                </div>
                <div className="bg-slate-900/60 p-2 rounded-lg border border-cyan-900/40">
                  <span className="text-cyan-400 font-bold block mb-0.5">After ({dateAfter}):</span>
                  <span className="text-slate-200">{activePin.afterState}</span>
                </div>
              </div>
            </div>
          )}

          {/* Badges */}
          <div className="absolute top-3 left-3 rounded-md bg-slate-950/85 px-2.5 py-1 text-xs font-semibold text-slate-200 border border-slate-800 backdrop-blur-md">
            <div>Before: {dateBefore}</div>
            {sourceBefore && <div className="text-[10px] font-normal text-slate-400">{sourceBefore}</div>}
          </div>
          <div className="absolute top-3 right-3 rounded-md bg-cyan-950/85 px-2.5 py-1 text-xs font-semibold text-cyan-300 border border-cyan-800/80 backdrop-blur-md text-right">
            <div>After: {dateAfter}</div>
            {sourceAfter && <div className="text-[10px] font-normal text-cyan-400">{sourceAfter}</div>}
          </div>
        </div>
      )}

      {/* Side-by-Side View */}
      {viewMode === 'side' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="relative aspect-square overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-lg">
            <img src={imageBefore} alt="Before date" className="h-full w-full object-cover" />
            <div className="absolute top-3 left-3 rounded-md bg-slate-950/85 px-2.5 py-1 text-xs font-semibold text-slate-200 border border-slate-800 backdrop-blur-md">
              <div>Before ({dateBefore})</div>
              {sourceBefore && <div className="text-[10px] font-normal text-slate-400">{sourceBefore}</div>}
            </div>
          </div>

          <div className="relative aspect-square overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-lg">
            <img src={imageAfter} alt="After date" className="h-full w-full object-cover" />
            <div className="absolute top-3 left-3 rounded-md bg-cyan-950/85 px-2.5 py-1 text-xs font-semibold text-cyan-300 border border-cyan-800 backdrop-blur-md">
              <div>After ({dateAfter})</div>
              {sourceAfter && <div className="text-[10px] font-normal text-cyan-400">{sourceAfter}</div>}
            </div>
          </div>
        </div>
      )}

      {/* Flicker View */}
      {viewMode === 'flicker' && (
        <div className="relative aspect-square w-full select-none overflow-hidden rounded-xl border border-slate-800 bg-slate-950 shadow-2xl">
          <img
            src={flickerState === 'before' ? imageBefore : imageAfter}
            alt="Flicker frame"
            className="h-full w-full object-cover"
          />
          <div className="absolute top-3 left-3 rounded-md bg-slate-950/85 px-3 py-1.5 text-xs font-bold border border-slate-700 backdrop-blur-md">
            {flickerState === 'before' ? (
              <div>
                <span className="text-slate-200">Frame 1: Before ({dateBefore})</span>
                {sourceBefore && <div className="text-[10px] font-normal text-slate-400">{sourceBefore}</div>}
              </div>
            ) : (
              <div>
                <span className="text-cyan-400">Frame 2: After ({dateAfter})</span>
                {sourceAfter && <div className="text-[10px] font-normal text-cyan-300">{sourceAfter}</div>}
              </div>
            )}
          </div>
          <div className="absolute bottom-3 left-3 rounded-md bg-slate-950/80 px-2.5 py-1 text-[11px] text-slate-400 backdrop-blur-sm">
            Astronomical blink comparator toggling frames to highlight shifting pixels
          </div>
        </div>
      )}
    </div>
  );
};
