import React, { useEffect, useRef, useState } from 'react';
import { AlertCircle, Check, Crosshair, RotateCcw, UploadCloud } from 'lucide-react';
import { AnalysisResult, NormalizedRegion } from '../types';
import { analyzeUploadedPair } from '../services/imageAnalysisService';

interface UploadPairViewProps {
  onAnalysisComplete: (result: AnalysisResult) => void;
}

interface ImageSize {
  width: number;
  height: number;
}

interface PreviewBounds {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface RegionPreviewProps {
  label: string;
  preview: string | null;
  dimensions: ImageSize | null;
  region: NormalizedRegion;
  onDimensions: (dimensions: ImageSize) => void;
  onFileSelected?: (file: File) => void;
  onRegionChange?: (region: NormalizedRegion) => void;
}

function getPreviewBounds(frame: HTMLDivElement, dimensions: ImageSize): PreviewBounds {
  const scale = Math.min(frame.clientWidth / dimensions.width, frame.clientHeight / dimensions.height);
  const width = dimensions.width * scale;
  const height = dimensions.height * scale;
  return {
    left: (frame.clientWidth - width) / 2,
    top: (frame.clientHeight - height) / 2,
    width,
    height,
  };
}

const RegionPreview: React.FC<RegionPreviewProps> = ({
  label,
  preview,
  dimensions,
  region,
  onDimensions,
  onFileSelected,
  onRegionChange,
}) => {
  const frameRef = useRef<HTMLDivElement>(null);
  const dragStart = useRef<{ x: number; y: number; previous: NormalizedRegion } | null>(null);

  const getPoint = (event: React.PointerEvent<HTMLDivElement>) => {
    const frame = frameRef.current;
    if (!frame || !dimensions) return null;
    const bounds = getPreviewBounds(frame, dimensions);
    const rect = frame.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left - bounds.left) / bounds.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top - bounds.top) / bounds.height)),
    };
  };

  const selectionStyle = (() => {
    const frame = frameRef.current;
    if (!frame || !dimensions) return undefined;
    const bounds = getPreviewBounds(frame, dimensions);
    return {
      left: `${bounds.left + region.x * bounds.width}px`,
      top: `${bounds.top + region.y * bounds.height}px`,
      width: `${region.width * bounds.width}px`,
      height: `${region.height * bounds.height}px`,
    };
  })();

  return (
    <div className="flex min-w-0 flex-col gap-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-slate-200">{label}</span>
        {dimensions && (
          <span className="font-mono text-[10px] text-slate-400">
            {dimensions.width.toLocaleString()} × {dimensions.height.toLocaleString()} px
          </span>
        )}
      </div>
      <div
        ref={frameRef}
        onPointerDown={(event) => {
          if (!onRegionChange) return;
          const point = getPoint(event);
          if (!point) return;
          dragStart.current = { ...point, previous: region };
          event.currentTarget.setPointerCapture(event.pointerId);
          onRegionChange({ x: point.x, y: point.y, width: 0.001, height: 0.001 });
        }}
        onPointerMove={(event) => {
          if (!dragStart.current || !onRegionChange) return;
          const point = getPoint(event);
          if (!point) return;
          const start = dragStart.current;
          onRegionChange({
            x: Math.min(start.x, point.x),
            y: Math.min(start.y, point.y),
            width: Math.abs(point.x - start.x),
            height: Math.abs(point.y - start.y),
          });
        }}
        onPointerUp={(event) => {
          if (!dragStart.current || !onRegionChange) return;
          const point = getPoint(event);
          const start = dragStart.current;
          dragStart.current = null;
          if (!point || Math.abs(point.x - start.x) < 0.03 || Math.abs(point.y - start.y) < 0.03) {
            onRegionChange(start.previous);
          }
        }}
        onPointerCancel={() => {
          if (dragStart.current && onRegionChange) onRegionChange(dragStart.current.previous);
          dragStart.current = null;
        }}
        className={`relative aspect-square overflow-hidden rounded-xl border border-slate-700 bg-slate-950 ${
          onRegionChange ? 'touch-none cursor-crosshair' : ''
        }`}
      >
        {preview ? (
          <>
            <img
              src={preview}
              alt={`${label} image`}
              onLoad={(event) => onDimensions({
                width: event.currentTarget.naturalWidth,
                height: event.currentTarget.naturalHeight,
              })}
              className="h-full w-full select-none object-contain"
              draggable={false}
            />
            {selectionStyle && (
              <div
                className="pointer-events-none absolute border-2 border-amber-300 bg-amber-300/15 shadow-[0_0_0_9999px_rgba(2,6,23,0.28)]"
                style={selectionStyle}
              >
                <span className="absolute left-0 top-0 -translate-y-full rounded-t bg-amber-300 px-1.5 py-0.5 text-[9px] font-bold text-slate-950">
                  Analysis region
                </span>
              </div>
            )}
            {onFileSelected && (
              <label
                onPointerDown={(event) => event.stopPropagation()}
                className="absolute right-2 top-2 z-10 cursor-pointer rounded-lg border border-slate-700 bg-slate-950/90 px-2 py-1 text-[10px] font-semibold text-slate-200 hover:border-cyan-400"
              >
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) onFileSelected(file);
                  }}
                  className="hidden"
                />
                Change image
              </label>
            )}
          </>
        ) : (
          <label className="absolute inset-0 flex cursor-pointer flex-col items-center justify-center gap-2 text-center">
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onFileSelected?.(file);
              }}
              className="hidden"
            />
            <UploadCloud className="h-8 w-8 text-cyan-400" />
            <span className="text-xs font-semibold text-white">Select {label} image</span>
            <span className="text-[11px] text-slate-400">PNG, JPEG or WebP</span>
          </label>
        )}
      </div>
    </div>
  );
};

export const UploadPairView: React.FC<UploadPairViewProps> = ({ onAnalysisComplete }) => {
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [previewA, setPreviewA] = useState<string | null>(null);
  const [previewB, setPreviewB] = useState<string | null>(null);
  const [dimensionsA, setDimensionsA] = useState<ImageSize | null>(null);
  const [dimensionsB, setDimensionsB] = useState<ImageSize | null>(null);
  const [region, setRegion] = useState<NormalizedRegion>({ x: 0, y: 0, width: 1, height: 1 });
  const [sensitivity, setSensitivity] = useState(0.22);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!previewA) return;
    return () => URL.revokeObjectURL(previewA);
  }, [previewA]);

  useEffect(() => {
    if (!previewB) return;
    return () => URL.revokeObjectURL(previewB);
  }, [previewB]);

  const selectFile = (side: 'before' | 'after', file: File) => {
    const preview = URL.createObjectURL(file);
    if (side === 'before') {
      setFileA(file);
      setPreviewA(preview);
      setDimensionsA(null);
    } else {
      setFileB(file);
      setPreviewB(preview);
      setDimensionsB(null);
    }
    setRegion({ x: 0, y: 0, width: 1, height: 1 });
    setError(null);
  };

  const handleRunAnalysis = async () => {
    if (!fileA || !fileB) {
      setError('Select both before and after images to run the RGB screening.');
      return;
    }
    setIsProcessing(true);
    setError(null);
    try {
      const result = await analyzeUploadedPair(fileA, fileB, sensitivity, region);
      onAnalysisComplete(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process the image pair.');
    } finally {
      setIsProcessing(false);
    }
  };

  const cropWidth = dimensionsA ? Math.round(region.width * dimensionsA.width) : null;
  const cropHeight = dimensionsA ? Math.round(region.height * dimensionsA.height) : null;
  const aspectMismatch = dimensionsA && dimensionsB
    ? Math.abs(dimensionsA.width / dimensionsA.height - dimensionsB.width / dimensionsB.height) /
      Math.max(dimensionsA.width / dimensionsA.height, dimensionsB.width / dimensionsB.height) > 0.02
    : false;

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-2xl md:p-6">
        <div className="mb-4">
          <span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-cyan-400">
            Focused image comparison
          </span>
          <h2 className="text-xl font-bold tracking-tight text-white">Select a matched area to screen</h2>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-300">
            Use co-registered images of the same footprint. Drag on the Before image to select a focused region;
            the same normalized crop is applied to both dates. Processing preserves source detail up to 2,048 px
            on the long side and never upscales the lower-resolution image.
          </p>
        </div>

        {error && (
          <div role="alert" className="mb-4 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-200">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <RegionPreview
            label="Before"
            preview={previewA}
            dimensions={dimensionsA}
            region={region}
            onDimensions={setDimensionsA}
            onFileSelected={(file) => selectFile('before', file)}
            onRegionChange={setRegion}
          />
          <RegionPreview
            label="After"
            preview={previewB}
            dimensions={dimensionsB}
            region={region}
            onDimensions={setDimensionsB}
            onFileSelected={(file) => selectFile('after', file)}
          />
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-[11px]">
          <div className="flex items-center gap-2 text-slate-300">
            <Crosshair className="h-3.5 w-3.5 text-amber-300" />
            <span>
              {Math.round(region.width * 100)}% × {Math.round(region.height * 100)}% of each image
              {cropWidth && cropHeight ? ` · ${cropWidth.toLocaleString()} × ${cropHeight.toLocaleString()} px (Before)` : ''}
            </span>
            {region.width === 1 && region.height === 1 && <span className="text-slate-500">· full frame</span>}
          </div>
          <button
            type="button"
            onClick={() => setRegion({ x: 0, y: 0, width: 1, height: 1 })}
            className="inline-flex items-center gap-1 text-slate-400 hover:text-white"
          >
            <RotateCcw className="h-3 w-3" />
            Reset region
          </button>
        </div>

        {dimensionsA && dimensionsB && (
          <div className={`mt-2 flex items-start gap-2 rounded-lg border p-2.5 text-[11px] ${
            aspectMismatch
              ? 'border-amber-500/30 bg-amber-500/10 text-amber-200'
              : 'border-slate-800 bg-slate-950/40 text-slate-400'
          }`}>
            {aspectMismatch ? <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />}
            <span>
              {aspectMismatch
                ? 'Image aspect ratios differ. Align/crop both images to the same footprint before analyzing.'
                : 'Both image footprints have compatible aspect ratios. This does not verify pixel-level registration.'}
            </span>
          </div>
        )}

        <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-slate-800/80 pt-4">
          <label className="flex min-w-[250px] flex-1 items-center gap-3 text-xs text-slate-300">
            <span className="shrink-0">RGB difference threshold</span>
            <input
              type="range"
              min="0.1"
              max="0.4"
              step="0.02"
              value={sensitivity}
              onChange={(event) => setSensitivity(Number(event.target.value))}
              className="h-1.5 w-36 accent-cyan-400"
            />
            <span className="font-mono text-cyan-300">{sensitivity.toFixed(2)}</span>
          </label>
          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={!fileA || !fileB || isProcessing || Boolean(aspectMismatch)}
            className="flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-2.5 text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition-colors hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isProcessing ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                Screening selected region…
              </>
            ) : (
              <>
                <Crosshair className="h-4 w-4" />
                Screen selected region
              </>
            )}
          </button>
        </div>
        <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
          This is an RGB difference screen only—not a validated change classification. Image registration, scale,
          spectral bands, and acquisition metadata are not inferred. See the result warnings before interpretation.
        </p>
      </div>
    </div>
  );
};
