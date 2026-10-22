import React, { useState } from 'react';
import { ChangedRegion } from '../types';
import { Copy, Check, Filter, MapPin, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface RegionsTableProps {
  regions: ChangedRegion[];
  onSelectRegion?: (region: ChangedRegion) => void;
}

export const RegionsTable: React.FC<RegionsTableProps> = ({ regions, onSelectRegion }) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const types = Array.from(new Set(regions.map((r) => r.type)));
  const filtered = filterType === 'all' ? regions : regions.filter((r) => r.type === filterType);

  const copyCoords = (reg: ChangedRegion) => {
    navigator.clipboard.writeText(`${reg.centroid[0]}, ${reg.centroid[1]}`);
    setCopiedId(reg.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getBadgeColor = (type: ChangedRegion['type']) => {
    switch (type) {
      case 'Built-up / Urban':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'Vegetation Loss':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'Water Dynamics':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      case 'Infrastructure':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      default:
        return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold text-slate-300">
          Flagged Clusters ({filtered.length} of {regions.length})
        </span>

        {types.length > 1 && (
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="h-3.5 w-3.5 text-slate-400" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Classifications</option>
              {types.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950/70">
        <div className="max-h-[380px] overflow-y-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="sticky top-0 z-10 bg-slate-900 border-b border-slate-800 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-2.5 px-3">Sector Label</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Area</th>
                <th className="py-2.5 px-3">Centroid</th>
                <th className="py-2.5 px-3">Why Conclusion Was Reached</th>
                <th className="py-2.5 px-3 text-right">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filtered.map((reg) => {
                const isExpanded = expandedId === reg.id;
                return (
                  <React.Fragment key={reg.id}>
                    <tr
                      onClick={() => {
                        setExpandedId(isExpanded ? null : reg.id);
                        onSelectRegion?.(reg);
                      }}
                      className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                    >
                      <td className="py-2.5 px-3 font-semibold text-white">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                          <span>{reg.label}</span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold ${getBadgeColor(
                            reg.type
                          )}`}
                        >
                          {reg.type}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-cyan-300 font-semibold whitespace-nowrap">
                        {reg.areaHa} ha
                      </td>
                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-300 whitespace-nowrap">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            copyCoords(reg);
                          }}
                          className="flex items-center gap-1 hover:text-cyan-300 transition-colors"
                          title="Click to copy coordinates"
                        >
                          <span>
                            {reg.centroid[0].toFixed(3)}, {reg.centroid[1].toFixed(3)}
                          </span>
                          {copiedId === reg.id ? (
                            <Check className="h-3 w-3 text-emerald-400" />
                          ) : (
                            <Copy className="h-3 w-3 opacity-60 hover:opacity-100" />
                          )}
                        </button>
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 max-w-[280px]">
                        <p className="line-clamp-2 text-[11px] leading-relaxed text-slate-300">
                          {reg.reasonForConclusion || reg.description}
                        </p>
                      </td>
                      <td className="py-2.5 px-3 text-right whitespace-nowrap">
                        <span
                          className={`text-[11px] font-semibold ${
                            reg.confidence === 'High' ? 'text-emerald-400' : 'text-amber-400'
                          }`}
                        >
                          {reg.confidence} ({Math.round(reg.meanDelta * 100)}%)
                        </span>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="bg-slate-900/90 border-b border-slate-800">
                        <td colSpan={6} className="px-4 py-3">
                          <div className="flex flex-col gap-1.5 text-xs">
                            <div className="flex items-center gap-1.5 text-cyan-300 font-semibold">
                              <HelpCircle className="h-3.5 w-3.5 text-cyan-400" />
                              <span>Decision Rationale for {reg.label}:</span>
                            </div>
                            <p className="text-slate-200 text-xs bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                              {reg.reasonForConclusion}
                            </p>
                            <span className="text-[11px] text-slate-400">{reg.description}</span>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    No changed regions match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
