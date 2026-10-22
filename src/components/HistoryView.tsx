import React from 'react';
import { HistoryItem, AnalysisResult } from '../types';
import { FileText, Download, Trash2, ArrowUpRight, Calendar, Layers } from 'lucide-react';
import { generatePDFReport, exportGeoJSON, exportCSV } from '../services/reportService';

interface HistoryViewProps {
  history: HistoryItem[];
  onSelectHistoryItem: (result: AnalysisResult) => void;
  onDeleteItem: (id: string) => void;
  onClearHistory: () => void;
}

export const HistoryView: React.FC<HistoryViewProps> = ({
  history,
  onSelectHistoryItem,
  onDeleteItem,
  onClearHistory,
}) => {
  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-cyan-400 block mb-1">
              Local Audit Trail
            </span>
            <h2 className="text-xl font-bold tracking-tight text-white">Previous Change Analyses</h2>
            <p className="text-xs text-slate-400 mt-1">
              Locally stored audit logs of previous satellite change detections. Reload any analysis or export reports.
            </p>
          </div>

          {history.length > 0 && (
            <button
              onClick={onClearHistory}
              className="flex items-center gap-1.5 rounded-lg border border-red-500/30 bg-red-500/10 hover:bg-red-500/20 px-3 py-1.5 text-xs font-medium text-red-300 transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear History
            </button>
          )}
        </div>

        {history.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-400">
            No previous analyses recorded yet. Run a live Sentinel-2 analysis or upload a pair to populate your audit log.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {history.map((item) => (
              <div
                key={item.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4 hover:border-slate-700 hover:bg-slate-950/90 transition-all"
              >
                <div className="flex items-center gap-3">
                  <img
                    src={item.thumbnail}
                    alt={item.title}
                    className="h-14 w-14 rounded-lg object-cover border border-slate-800 shrink-0"
                  />
                  <div>
                    <h3 className="text-sm font-bold text-white line-clamp-1">{item.title}</h3>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 mt-0.5">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-cyan-400" />
                        {item.dateBefore} → {item.dateAfter}
                      </span>
                      <span>•</span>
                      <span className="font-semibold text-cyan-300">{item.percentChanged}% changed</span>
                    </div>
                    <span className="text-[10px] text-slate-500 block mt-0.5">
                      Created: {new Date(item.dateCreated).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => onSelectHistoryItem(item.result)}
                    className="flex items-center gap-1 rounded-lg bg-cyan-500 hover:bg-cyan-400 px-3 py-1.5 text-xs font-bold text-slate-950 transition-colors"
                  >
                    View Report
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </button>

                  <button
                    onClick={() => generatePDFReport(item.result)}
                    className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 text-xs text-slate-300 transition-colors"
                    title="Download PDF"
                  >
                    <FileText className="h-3.5 w-3.5 text-cyan-400" />
                  </button>

                  <button
                    onClick={() => exportGeoJSON(item.result)}
                    className="flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 text-xs text-slate-300 transition-colors"
                    title="Export GeoJSON"
                  >
                    <Download className="h-3.5 w-3.5 text-cyan-400" />
                  </button>

                  <button
                    onClick={() => onDeleteItem(item.id)}
                    className="rounded-lg border border-slate-800 p-1.5 text-slate-500 hover:text-red-400 hover:border-red-500/30 transition-colors"
                    title="Delete item"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
