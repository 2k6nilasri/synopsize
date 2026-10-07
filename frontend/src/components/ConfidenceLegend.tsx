"use client";

import React from "react";
import { Filter } from "lucide-react";

interface ConfidenceLegendProps {
  showLowConfidenceOnly: boolean;
  onToggleFilter: (val: boolean) => void;
  redCount?: number;
  yellowCount?: number;
  greenCount?: number;
}

export default function ConfidenceLegend({
  showLowConfidenceOnly,
  onToggleFilter,
  redCount = 0,
  yellowCount = 0,
  greenCount = 0
}: ConfidenceLegendProps) {
  return (
    <div className="bg-slate-50 rounded-lg border border-slate-200 p-4 mt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
      {/* Dots Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs font-semibold">
        <span className="text-slate-500 font-bold uppercase tracking-wider text-[10px]">
          Confidence Legend:
        </span>

        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-rose-50 border border-rose-200 text-rose-900">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-600 inline-block" />
          <span>■ Red (Low &lt; 0.70)</span>
          {redCount > 0 && <span className="ml-1 font-mono font-bold">({redCount})</span>}
        </div>

        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-amber-50 border border-amber-200 text-amber-900">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
          <span>▲ Yellow (Average 0.70–0.89)</span>
          {yellowCount > 0 && <span className="ml-1 font-mono font-bold">({yellowCount})</span>}
        </div>

        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-emerald-50 border border-emerald-200 text-emerald-900">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 inline-block" />
          <span>● Green (High ≥ 0.90)</span>
          {greenCount > 0 && <span className="ml-1 font-mono font-bold">({greenCount})</span>}
        </div>
      </div>

      {/* Filter Checkbox */}
      <label className="flex items-center space-x-2 text-xs font-semibold text-slate-700 cursor-pointer bg-white px-3 py-1.5 rounded border border-slate-300 hover:bg-slate-50 transition shrink-0">
        <input
          type="checkbox"
          checked={showLowConfidenceOnly}
          onChange={(e) => onToggleFilter(e.target.checked)}
          className="rounded border-slate-300 text-teal-600 focus:ring-teal-500 w-4 h-4"
        />
        <Filter className="w-3.5 h-3.5 text-slate-500" />
        <span>Show only low confidence (&lt; 0.90)</span>
      </label>
    </div>
  );
}
