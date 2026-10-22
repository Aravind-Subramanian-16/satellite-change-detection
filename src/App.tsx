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
} from './types';
import { PRESET_LOCATIONS, PROFILES } from './data/presets';
import { runSyntheticAnalysis, calculateAoiStats } from './services/analysisEngine';
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
    // Reset any old result so user sees fresh setup
    setCurrentResult(null);
  };

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisStep('Requesting comparison imagery from configured providers…');

    try {
      const result = await runSyntheticAnalysis(
        bbox,
        dateBefore,
        dateAfter,
        profileKey,
        locationLabel
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

    // Update form state
    setBbox(targetBbox);
    setSelectedPresetId('');
    setLocationLabel(locName);
    setDateBefore(t1);
    setDateAfter(t2);
    setProfileKey(prof);
    setActiveTab('live');

    // Run analysis immediately
    setIsAnalyzing(true);
    setAnalysisStep(`Auto-navigating to ${locName} (${targetBbox.south.toFixed(3)}, ${targetBbox.west.toFixed(3)})...`);

    try {
      setAnalysisStep('Requesting imagery and screening visible RGB differences…');
      const result = await runSyntheticAnalysis(targetBbox, t1, t2, prof, locName);

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
                    RGB imagery screening · Provider coverage and capture dates vary
                  </span>
                  <h1 className="text-3xl font-extrabold tracking-tight text-white md:text-4xl">
                    See what changed on the ground.
                  </h1>
                  <p className="mt-2 text-sm text-slate-300 leading-relaxed">
                    Request imagery for two dates and screen visible RGB pixel differences. This interface does
                    not provide semantic land-cover classification or validated environmental findings; when
                    imagery cannot be retrieved, it shows clearly labelled synthetic demonstration imagery.
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
                      <span className="text-xs text-slate-400">Map area selected by bounding box</span>
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
                      <h2 className="text-base font-bold text-white">Dates & screening context</h2>
                      <p className="text-xs text-slate-400 mt-0.5">Imagery source dates and RGB screening limitations apply</p>
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
                        <span className="text-[11px] text-amber-300">
                          Context only · RGB screen does not compute indices
                        </span>
                      </label>
                      <select
                        value={profileKey}
                        onChange={(e) => {
                          const key = e.target.value as ProfileKey;
                          setProfileKey(key);
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
                        <p className="mt-1 text-[11px] text-slate-400">
                          This profile is context only. The current comparison uses visible RGB pixel differences
                          and does not calculate the profile’s named spectral indices or classify land cover.
                        </p>
                      </div>
                    </div>

                    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-100">
                      RGB screening only: no semantic classifier, cloud/shadow correction, image registration,
                      minimum mapping unit, or validated accuracy estimate is applied.
                    </div>

                    {/* Run Button */}
                    <button
                      onClick={runAnalysis}
                      disabled={isAnalyzing}
                      className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-500/20 transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50"
                    >
                      <Sparkles className="h-4 w-4" />
                      Run RGB Difference Screen
                    </button>
                    <p className="text-center text-[11px] text-slate-400">
                      Results identify RGB pixel differences only; imagery availability and capture-date alignment are not guaranteed.
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
            ) : null}
            <div className={currentResult ? 'hidden' : ''}>
              <UploadPairView
                onAnalysisComplete={(res) => {
                  setCurrentResult(res);
                  saveToHistory(res);
                }}
              />
            </div>
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
            <h3 className="text-base font-bold text-white">Requesting and screening imagery</h3>
            <p className="mt-2 text-xs font-medium text-cyan-300 min-h-[36px]">{analysisStep}</p>
            <span className="mt-4 text-[11px] text-slate-500">Please keep this browser window open</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="mt-12 border-t border-slate-800/80 bg-[#070c19] py-6 text-center text-xs text-slate-500">
        <p>Satellite Change Detection & Land Audit Platform · RGB screening and imagery review</p>
        <p className="mt-1 text-[11px]">
          Provider imagery and dates vary. Synthetic fallback is demonstration-only; results are not validated ground truth.
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
