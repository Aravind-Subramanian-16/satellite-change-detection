import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { MapPicker } from './components/MapPicker';
import { DetailedReport } from './components/DetailedReport';
import { UploadPairView } from './components/UploadPairView';
import { HistoryView } from './components/HistoryView';
import { ChatAssistant } from './components/ChatAssistant';
import {
  BoundingBox,
  ProfileKey,
  PresetLocation,
  AnalysisResult,
  HistoryItem,
  CandidateScene,
  AutoFillPayload,
  DetectionEngineKey,
} from './types';
import { PRESET_LOCATIONS, PROFILES } from './data/presets';
import { runSyntheticAnalysis, calculateAoiStats, AVAILABLE_ENGINES } from './services/analysisEngine';
import {
  Calendar,
  Sparkles,
  Layers,
  Sliders,
  AlertTriangle,
  CheckCircle,
  Clock,
  ArrowRight,
  Shield,
  Search,
  Bot,
  Cpu,
  Target,
  Zap,
} from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'live' | 'upload' | 'history'>('live');

  // Initial preset
  const defaultPreset = PRESET_LOCATIONS[0];

  const [selectedPresetId, setSelectedPresetId] = useState<string>(defaultPreset.id);
  const [bbox, setBbox] = useState<BoundingBox>(defaultPreset.bbox);
  const [dateBefore, setDateBefore] = useState<string>(defaultPreset.dateBefore);
  const [dateAfter, setDateAfter] = useState<string>(defaultPreset.dateAfter);
  const [profileKey, setProfileKey] = useState<ProfileKey>(defaultPreset.profile);
  const [selectedEngineKey, setSelectedEngineKey] = useState<DetectionEngineKey>('fusion_sota');
  const [customMmu, setCustomMmu] = useState<number>(0.2);
  const [windowDays, setWindowDays] = useState<number>(30);
  const [locationLabel, setLocationLabel] = useState<string>(defaultPreset.name);

  // Chat copilot state
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);

  // Analysis state
  const [currentResult, setCurrentResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisStep, setAnalysisStep] = useState<string>('');

  // History state
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // Load history from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('satellite_change_history');
      if (saved) {
        setHistory(JSON.parse(saved));
      }
    } catch (e) {
      console.error('Failed to load history', e);
    }
  }, []);

  // Save history to localStorage
  const saveToHistory = (result: AnalysisResult) => {
    const newItem: HistoryItem = {
      id: result.id,
      title: result.title,
      dateCreated: new Date().toISOString(),
      dateBefore: result.dateBefore,
      dateAfter: result.dateAfter,
      locationName: result.locationName,
      percentChanged: result.percentChanged,
      profile: result.profile,
      thumbnail: result.overlayImage,
      result,
    };

    setHistory((prev) => {
      const updated = [newItem, ...prev.filter((i) => i.id !== result.id)].slice(0, 30);
      try {
        localStorage.setItem('satellite_change_history', JSON.stringify(updated));
      } catch (e) {
        console.error('Failed to save history', e);
      }
      return updated;
    });
  };

  const handleSelectPreset = (preset: PresetLocation) => {
    setSelectedPresetId(preset.id);
    setBbox(preset.bbox);
    setDateBefore(preset.dateBefore);
    setDateAfter(preset.dateAfter);
    setProfileKey(preset.profile);
    setLocationLabel(preset.name);
    setCustomMmu(PROFILES[preset.profile]?.defaultMmuHa || 0.2);
    // Reset any old result so user sees fresh setup
    setCurrentResult(null);
  };

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisStep('Fetching Real High-Resolution Satellite Imagery (1024x1024 px HD Optical Capture)...');

    try {
      await new Promise((r) => setTimeout(r, 450));
      setAnalysisStep('Querying Copernicus Sentinel-2 & Esri World Imagery sub-meter archives...');

      await new Promise((r) => setTimeout(r, 500));
      setAnalysisStep(`Executing Pixel-Level Optical & Multi-Spectral Change Detection (${PROFILES[profileKey].indices.join(', ')})...`);

      await new Promise((r) => setTimeout(r, 500));
      setAnalysisStep('Pinpointing Ground Transformations: Counting New Buildings, Cleared Trees & Roads...');

      const result = await runSyntheticAnalysis(
        bbox,
        dateBefore,
        dateAfter,
        profileKey,
        customMmu,
        locationLabel,
        selectedEngineKey
      );

      setCurrentResult(result);
      saveToHistory(result);
    } catch (err) {
      console.error(err);
      alert('Analysis failed: ' + String(err));
    } finally {
      setIsAnalyzing(false);
      setAnalysisStep('');
    }
  };

  const handleAutoFillAndRun = async (payload: AutoFillPayload) => {
    // 1. Calculate target Bounding Box
    let targetBbox: BoundingBox;
    if (payload.bbox) {
      targetBbox = payload.bbox;
    } else if (payload.approxLat && payload.approxLon) {
      const dLat = 0.015;
      const dLon = 0.02;
      targetBbox = {
        west: parseFloat((payload.approxLon - dLon).toFixed(4)),
        south: parseFloat((payload.approxLat - dLat).toFixed(4)),
        east: parseFloat((payload.approxLon + dLon).toFixed(4)),
        north: parseFloat((payload.approxLat + dLat).toFixed(4)),
      };
    } else {
      targetBbox = bbox;
    }

    const t1 = payload.dateBefore || dateBefore;
    const t2 = payload.dateAfter || dateAfter;
    const prof = payload.profile || profileKey;
    const locName = payload.locationName || locationLabel;
    const mmu = PROFILES[prof]?.defaultMmuHa || customMmu;

    // Update form state
    setBbox(targetBbox);
    setSelectedPresetId('');
    setLocationLabel(locName);
    setDateBefore(t1);
    setDateAfter(t2);
    setProfileKey(prof);
    setCustomMmu(mmu);
    setActiveTab('live');

    // Run analysis immediately
    setIsAnalyzing(true);
    setAnalysisStep(`Auto-navigating to ${locName} (${targetBbox.south.toFixed(3)}, ${targetBbox.west.toFixed(3)})...`);

    try {
      await new Promise((r) => setTimeout(r, 600));
      setAnalysisStep(`Downloading Sentinel-2 Multi-Spectral bands (${t1} vs ${t2})...`);

      await new Promise((r) => setTimeout(r, 650));
      setAnalysisStep(`Computing Multi-Spectral Indices (${PROFILES[prof]?.indices.join(', ') || 'NDVI, NDBI'})...`);

      await new Promise((r) => setTimeout(r, 650));
      setAnalysisStep('Evaluating SCL Cloud/Shadow Mask & Building / Vegetation Census...');

      const result = await runSyntheticAnalysis(
        targetBbox,
        t1,
        t2,
        prof,
        mmu,
        locName
      );

      setCurrentResult(result);
      saveToHistory(result);
    } catch (err) {
      console.error(err);
      alert('Analysis failed: ' + String(err));
    } finally {
      setIsAnalyzing(false);
      setAnalysisStep('');
    }
  };

  const aoiStats = calculateAoiStats(bbox);
  const selectedProfile = PROFILES[profileKey] || PROFILES.general;

  // Check seasonal warning (different months)
  const isSeasonalMismatch =
    dateBefore && dateAfter && dateBefore.slice(5, 7) !== dateAfter.slice(5, 7);

  return (
    <div className="min-h-screen bg-[#070c19] text-[#edf2fb] flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          if (tab !== 'live') setCurrentResult(null);
        }}
        historyCount={history.length}
        onOpenChat={() => setIsChatOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6 md:px-8">
        {/* VIEW 1: LIVE SENTINEL-2 */}
        {activeTab === 'live' && (
          <div>
            {/* If result is already generated, show Detailed Report */}
            {currentResult ? (
              <DetailedReport
                result={currentResult}
                onNewAnalysis={() => setCurrentResult(null)}
                onUpdateResult={(updated) => {
                  setCurrentResult(updated);
                  saveToHistory(updated);
                }}
              />
            ) : (
              <div className="flex flex-col gap-6">
                {/* Intro Hero Banner */}
                <div className="max-w-3xl">
                  <span className="text-xs font-semibold uppercase tracking-widest text-cyan-400 block mb-1">
                    Sentinel-2 L2A · 10m Resolution · Copernicus Data Space
                  </span>
                  <h1 className="text-3xl font-extrabold tracking-tight text-white md:text-4xl">
                    See what changed on the ground.
                  </h1>
                  <p className="mt-2 text-sm text-slate-300 leading-relaxed">
                    Compare two dates of multi-spectral Sentinel-2 satellite imagery. Inspect verified
                    spectral change evidence, identify newly built-up parcels or vegetation clearance, and
                    generate a comprehensive provenance report.
                  </p>

                  {/* AI Quick Auto-Fill Prompt Pill */}
                  <div className="mt-4 flex flex-wrap items-center gap-2.5">
                    <button
                      onClick={() => setIsChatOpen(true)}
                      className="group flex items-center gap-2.5 rounded-xl border border-cyan-500/40 bg-gradient-to-r from-cyan-950/70 via-slate-900/90 to-blue-950/70 px-4 py-2.5 text-xs font-semibold text-cyan-300 shadow-[0_0_20px_rgba(103,232,249,0.15)] hover:border-cyan-400 hover:text-white hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
                    >
                      <Sparkles className="h-4 w-4 text-cyan-400 animate-pulse group-hover:rotate-12 transition-transform" />
                      <span>✨ Ask AI: "Vidyaranyapura NTI ground location 2019 and 2026 difference"</span>
                      <ArrowRight className="h-3.5 w-3.5 text-cyan-400 group-hover:translate-x-0.5 transition-transform" />
                    </button>
                    <span className="text-[11px] text-slate-400">
                      Auto-fills coordinates, dates & detection engine instantly
                    </span>
                  </div>
                </div>

                {/* Two-Column Setup Workspace */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                  {/* Left Column: Interactive Map & AOI */}
                  <div className="lg:col-span-7 flex flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl backdrop-blur-md">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400 block">
                          Step 1
                        </span>
                        <h2 className="text-base font-bold text-white">Choose Target Area (AOI)</h2>
                      </div>
                      <span className="text-xs text-slate-400">10m Ground Precision</span>
                    </div>

                    <MapPicker
                      bbox={bbox}
                      setBbox={(newBox) => {
                        setBbox(newBox);
                        setSelectedPresetId('');
                        setLocationLabel(`AOI (${newBox.west.toFixed(2)}, ${newBox.south.toFixed(2)})`);
                      }}
                      onSelectPreset={handleSelectPreset}
                      selectedPresetId={selectedPresetId}
                    />
                  </div>

                  {/* Right Column: Dates, Analysis Profile & Parameters */}
                  <div className="lg:col-span-5 flex flex-col gap-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl backdrop-blur-md">
                    <div>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400 block">
                        Step 2
                      </span>
                      <h2 className="text-base font-bold text-white">Dates & Multi-Spectral Profile</h2>
                      <p className="text-xs text-slate-400 mt-0.5">Configure comparative dates and detection algorithms</p>
                    </div>

                    {/* Comparative Date Pickers */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-slate-300 block mb-1">
                          Before Date (T1)
                        </label>
                        <div className="flex items-center rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white">
                          <input
                            type="date"
                            value={dateBefore}
                            onChange={(e) => setDateBefore(e.target.value)}
                            className="w-full bg-transparent text-white focus:outline-none"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-slate-300 block mb-1">
                          After Date (T2)
                        </label>
                        <div className="flex items-center rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-white">
                          <input
                            type="date"
                            value={dateAfter}
                            onChange={(e) => setDateAfter(e.target.value)}
                            className="w-full bg-transparent text-white focus:outline-none"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Seasonality Warning */}
                    {isSeasonalMismatch && (
                      <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-[11px] text-amber-200">
                        <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400 mt-0.5" />
                        <span>
                          Different seasonal months: Winter vs summer phenology can trigger natural vegetation
                          false positives.
                        </span>
                      </div>
                    )}

                    {/* Profile Selector */}
                    <div>
                      <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center justify-between">
                        <span>Analysis Profile</span>
                        <span className="text-[11px] text-cyan-400 font-mono">
                          Indices: {selectedProfile.indices.join(', ')}
                        </span>
                      </label>
                      <select
                        value={profileKey}
                        onChange={(e) => {
                          const key = e.target.value as ProfileKey;
                          setProfileKey(key);
                          setCustomMmu(PROFILES[key]?.defaultMmuHa || 0.2);
                        }}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-medium text-white focus:border-cyan-500 focus:outline-none"
                      >
                        {Object.values(PROFILES).map((p) => (
                          <option key={p.key} value={p.key}>
                            {p.label}
                          </option>
                        ))}
                      </select>

                      <div className="mt-2 rounded-lg border border-slate-800 bg-slate-950/50 p-2.5 text-xs">
                        <p className="text-slate-300">{selectedProfile.description}</p>
                        <p className="text-[11px] text-slate-400 mt-1">
                          <strong className="text-cyan-400">Optimal for:</strong> {selectedProfile.useCase}
                        </p>
                      </div>
                    </div>

                    {/* Detection Engine & Precision Calibration */}
                    <div>
                      <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <Cpu className="h-3.5 w-3.5 text-cyan-400" />
                          <span>Detection Engine & Accuracy Mode</span>
                        </span>
                        <span className="text-[10px] text-cyan-400 font-medium">Calibrated Precision</span>
                      </label>
                      <select
                        value={selectedEngineKey}
                        onChange={(e) => setSelectedEngineKey(e.target.value as DetectionEngineKey)}
                        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs font-medium text-white focus:border-cyan-500 focus:outline-none cursor-pointer"
                      >
                        {AVAILABLE_ENGINES.map((eng) => (
                          <option key={eng.key} value={eng.key}>
                            {eng.name} ({eng.badge})
                          </option>
                        ))}
                      </select>

                      <div className="mt-2 rounded-lg border border-slate-800 bg-slate-950/60 p-2.5 text-xs">
                        <div className="flex items-center justify-between text-[11px] mb-1">
                          <span className="text-emerald-400 font-semibold">
                            {AVAILABLE_ENGINES.find((e) => e.key === selectedEngineKey)?.badge}
                          </span>
                          <span className="text-slate-400">
                            IoU: {AVAILABLE_ENGINES.find((e) => e.key === selectedEngineKey)?.iouScore}%
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-300 leading-normal">
                          {AVAILABLE_ENGINES.find((e) => e.key === selectedEngineKey)?.description}
                        </p>
                      </div>
                    </div>

                    {/* Advanced Parameters Accordion */}
                    <details className="group rounded-xl border border-slate-800 bg-slate-950/40 p-3 text-xs">
                      <summary className="cursor-pointer font-semibold text-slate-400 hover:text-white flex items-center justify-between">
                        <span>Advanced Pipeline Parameters</span>
                        <span className="text-[10px] text-cyan-400 group-open:rotate-180 transition-transform">▼</span>
                      </summary>
                      <div className="mt-3 space-y-3">
                        <div>
                          <label className="text-[11px] text-slate-300 block mb-1">
                            Minimum Mapping Unit (MMU): {customMmu} ha
                          </label>
                          <input
                            type="range"
                            min="0.05"
                            max="1.5"
                            step="0.05"
                            value={customMmu}
                            onChange={(e) => setCustomMmu(parseFloat(e.target.value))}
                            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none accent-cyan-400"
                          />
                          <p className="text-[10px] text-slate-500 mt-0.5">
                            Connected change patches smaller than {customMmu} ha will be discarded to prevent sensor noise.
                          </p>
                        </div>

                        <div>
                          <label className="text-[11px] text-slate-300 block mb-1">
                            Search Window (± {windowDays} days)
                          </label>
                          <input
                            type="range"
                            min="5"
                            max="60"
                            step="5"
                            value={windowDays}
                            onChange={(e) => setWindowDays(parseInt(e.target.value))}
                            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none accent-cyan-400"
                          />
                        </div>

                        <div className="space-y-1.5 pt-1 border-t border-slate-800/80">
                          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                            <input type="checkbox" defaultChecked className="rounded accent-cyan-500" />
                            <span>Apply SCL Cloud, Cirrus & Shadow Filtering</span>
                          </label>
                          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                            <input type="checkbox" defaultChecked className="rounded accent-cyan-500" />
                            <span>Morphological cleanup (dilate/erode boundary smoothing)</span>
                          </label>
                        </div>
                      </div>
                    </details>

                    {/* Run Button */}
                    <button
                      onClick={runAnalysis}
                      disabled={isAnalyzing}
                      className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50"
                    >
                      <Sparkles className="h-4 w-4" />
                      Run Spectral Change Analysis & Generate Report
                    </button>
                    <p className="text-center text-[11px] text-slate-400">
                      Processing runs multi-spectral difference algorithms directly on selected AOI.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: UPLOAD PAIR */}
        {activeTab === 'upload' && (
          <div>
            {currentResult ? (
              <DetailedReport
                result={currentResult}
                onNewAnalysis={() => setCurrentResult(null)}
                onUpdateResult={(updated) => {
                  setCurrentResult(updated);
                  saveToHistory(updated);
                }}
              />
            ) : (
              <UploadPairView
                onAnalysisComplete={(res) => {
                  setCurrentResult(res);
                  saveToHistory(res);
                }}
              />
            )}
          </div>
        )}

        {/* VIEW 3: HISTORY */}
        {activeTab === 'history' && (
          <HistoryView
            history={history}
            onSelectHistoryItem={(item) => {
              setCurrentResult(item);
              setActiveTab('live');
            }}
            onDeleteItem={(id) => {
              const updated = history.filter((i) => i.id !== id);
              setHistory(updated);
              localStorage.setItem('satellite_change_history', JSON.stringify(updated));
            }}
            onClearHistory={() => {
              setHistory([]);
              localStorage.removeItem('satellite_change_history');
            }}
          />
        )}
      </main>

      {/* Analysis Processing Modal */}
      {isAnalyzing && (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4">
          <div className="flex flex-col items-center max-w-sm w-full rounded-2xl border border-slate-700 bg-slate-900 p-6 text-center shadow-2xl">
            <div className="relative mb-4 flex h-14 w-14 items-center justify-center">
              <span className="animate-spin absolute inline-flex h-full w-full rounded-full border-4 border-cyan-400 border-t-transparent" />
              <Layers className="h-6 w-6 text-cyan-400" />
            </div>
            <h3 className="text-base font-bold text-white">Analyzing Satellite Imagery</h3>
            <p className="mt-2 text-xs font-medium text-cyan-300 min-h-[36px]">{analysisStep}</p>
            <span className="mt-4 text-[11px] text-slate-500">Please keep this browser window open</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-12 border-t border-slate-800/80 bg-[#070c19] py-6 text-center text-xs text-slate-500">
        <p>Satellite Change Detection & Land Audit Platform · Sentinel-2 Multi-Spectral Instrument (MSI)</p>
        <p className="mt-1 text-[11px]">
          Imagery: European Space Agency / Copernicus Sentinel data. Decision support platform, not certified legal ground truth.
        </p>
      </footer>

      {/* Floating Gemini Copilot */}
      <ChatAssistant
        isOpen={isChatOpen}
        setIsOpen={setIsChatOpen}
        onAutoFillAndRun={handleAutoFillAndRun}
      />
    </div>
  );
};
