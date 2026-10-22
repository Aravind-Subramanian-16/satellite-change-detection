import React, { useState } from 'react';
import { UploadCloud, Image as ImageIcon, ArrowRight, AlertCircle, Sparkles } from 'lucide-react';
import { AnalysisResult } from '../types';
import { analyzeUploadedPair } from '../services/imageAnalysisService';

interface UploadPairViewProps {
  onAnalysisComplete: (result: AnalysisResult) => void;
}

export const UploadPairView: React.FC<UploadPairViewProps> = ({ onAnalysisComplete }) => {
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [previewA, setPreviewA] = useState<string | null>(null);
  const [previewB, setPreviewB] = useState<string | null>(null);
  const [sensitivity, setSensitivity] = useState<number>(0.22);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectA = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFileA(file);
      setPreviewA(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleSelectB = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFileB(file);
      setPreviewB(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleRunAnalysis = async () => {
    if (!fileA || !fileB) {
      setError('Please provide both Before and After images to run the differential analysis.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    try {
      const result = await analyzeUploadedPair(fileA, fileB, sensitivity);
      onAnalysisComplete(result);
    } catch (err: any) {
      setError(err?.message || 'Failed to process image pair.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto flex flex-col gap-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl backdrop-blur-md">
        <div className="mb-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400 block mb-1">
            Custom Imagery Differential Mode
          </span>
          <h2 className="text-xl font-bold tracking-tight text-white">Upload Satellite / Aerial Pair</h2>
          <p className="text-xs text-slate-400 mt-1">
            Compare any two orthophotos, drone captures, or satellite images. Detects structural changes,
            impervious surface construction, and ground disturbance.
          </p>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-200">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* File Box A: Before */}
          <label className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 hover:border-cyan-500/60 bg-slate-950/60 p-4 transition-all cursor-pointer aspect-square relative overflow-hidden group">
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleSelectA} className="hidden" />
            {previewA ? (
              <>
                <img src={previewA} alt="Before preview" className="h-full w-full object-cover rounded-lg" />
                <div className="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-xs font-semibold text-white">
                  Change Before Image
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center text-center p-4">
                <UploadCloud className="h-8 w-8 text-cyan-400 mb-2 opacity-80" />
                <span className="text-xs font-bold text-white">1. Select Before Image</span>
                <span className="text-[11px] text-slate-400 mt-1">PNG, JPEG or WebP</span>
              </div>
            )}
            <div className="absolute top-2 left-2 rounded bg-slate-900/80 px-2 py-0.5 text-[10px] font-semibold text-slate-300 border border-slate-800">
              Before
            </div>
          </label>

          {/* File Box B: After */}
          <label className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 hover:border-cyan-500/60 bg-slate-950/60 p-4 transition-all cursor-pointer aspect-square relative overflow-hidden group">
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleSelectB} className="hidden" />
            {previewB ? (
              <>
                <img src={previewB} alt="After preview" className="h-full w-full object-cover rounded-lg" />
                <div className="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-xs font-semibold text-white">
                  Change After Image
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center text-center p-4">
                <UploadCloud className="h-8 w-8 text-cyan-400 mb-2 opacity-80" />
                <span className="text-xs font-bold text-white">2. Select After Image</span>
                <span className="text-[11px] text-slate-400 mt-1">PNG, JPEG or WebP</span>
              </div>
            )}
            <div className="absolute top-2 left-2 rounded bg-slate-900/80 px-2 py-0.5 text-[10px] font-semibold text-cyan-300 border border-cyan-800">
              After
            </div>
          </label>
        </div>

        {/* Sensitivity & Trigger */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-4 border-t border-slate-800/80 pt-4">
          <div className="flex items-center gap-2 text-xs text-slate-300">
            <span>Detection Sensitivity:</span>
            <input
              type="range"
              min="0.1"
              max="0.4"
              step="0.02"
              value={sensitivity}
              onChange={(e) => setSensitivity(parseFloat(e.target.value))}
              className="h-1.5 w-28 bg-slate-700 rounded-lg appearance-none accent-cyan-400"
            />
            <span className="font-mono text-cyan-400 text-xs">{Math.round((1 - sensitivity) * 100)}%</span>
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={!fileA || !fileB || isProcessing}
            className="flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed px-5 py-2.5 text-xs font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition-all"
          >
            {isProcessing ? (
              <>
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-950 border-t-transparent" />
                Analyzing Differential...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Run Change Analysis & Generate Report
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
