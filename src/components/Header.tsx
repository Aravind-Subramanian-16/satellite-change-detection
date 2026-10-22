import React from 'react';
import { Satellite, UploadCloud, History, Layers, Sparkles } from 'lucide-react';

interface HeaderProps {
  activeTab: 'live' | 'upload' | 'history';
  setActiveTab: (tab: 'live' | 'upload' | 'history') => void;
  historyCount: number;
  onOpenChat?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  historyCount,
  onOpenChat,
}) => {
  return (
    <header className="sticky top-0 z-50 flex flex-wrap items-center justify-between gap-4 border-b border-slate-700/60 bg-[#070c19]/90 px-4 py-3.5 backdrop-blur-md md:px-8">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shadow-[0_0_15px_rgba(103,232,249,0.2)]">
          <Satellite className="h-5 w-5" />
        </div>
        <div>
          <span className="font-bold tracking-tight text-white flex items-center gap-2 text-base">
            Satellite Change Detection
            <span className="rounded-full bg-cyan-950 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-cyan-300 border border-cyan-800">
              Sentinel-2 High-Precision
            </span>
          </span>
          <p className="text-xs text-slate-400">10m Multi-Spectral Surface Dynamics & Enhanced Cadastral Analytics</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <nav className="flex items-center gap-1.5 rounded-full border border-slate-700/70 bg-slate-900/80 p-1">
          <button
            onClick={() => setActiveTab('live')}
            className={`flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'live'
                ? 'bg-blue-600/30 text-cyan-300 border border-blue-500/50 shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            Live Sentinel-2
          </button>

          <button
            onClick={() => setActiveTab('upload')}
            className={`flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'upload'
                ? 'bg-blue-600/30 text-cyan-300 border border-blue-500/50 shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <UploadCloud className="h-3.5 w-3.5" />
            Upload Pair
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs font-medium transition-all cursor-pointer ${
              activeTab === 'history'
                ? 'bg-blue-600/30 text-cyan-300 border border-blue-500/50 shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <History className="h-3.5 w-3.5" />
            History
            {historyCount > 0 && (
              <span className="ml-0.5 rounded-full bg-blue-500/30 px-1.5 py-0.2 text-[10px] text-blue-200">
                {historyCount}
              </span>
            )}
          </button>
        </nav>

        {onOpenChat && (
          <button
            onClick={onOpenChat}
            className="flex items-center gap-2 rounded-full border border-cyan-500/40 bg-cyan-950/40 px-3.5 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/50 shadow-[0_0_15px_rgba(103,232,249,0.15)] transition-all"
            title="Open AI Satellite Copilot"
          >
            <Sparkles className="h-3.5 w-3.5 text-cyan-400 animate-pulse" />
            <span>AI Copilot</span>
          </button>
        )}
      </div>

      <div className="hidden lg:flex items-center gap-2 text-xs text-slate-400">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span>Decision Support Active</span>
      </div>
    </header>
  );
};
