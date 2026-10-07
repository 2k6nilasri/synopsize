"use client";

import React, { useState } from "react";
import { CheckCircle2, Clock, AlertCircle, Info, ChevronRight } from "lucide-react";
import { PipelineStage } from "@/types";

interface StageStepperProps {
  stages: PipelineStage[];
  currentStageNum: number;
}

export default function StageStepper({ stages, currentStageNum }: StageStepperProps) {
  const [selectedStage, setSelectedStage] = useState<PipelineStage | null>(null);

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 w-full">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-100">
        <h3 className="text-sm font-bold text-slate-900 tracking-tight flex items-center gap-1.5">
          <span>Pipeline Stages</span>
        </h3>
        <span className="text-xs text-slate-500 font-mono">
          Stage {Math.min(currentStageNum, 7)} / 7
        </span>
      </div>

      <div className="space-y-3 relative">
        {/* Connecting Vertical Line */}
        <div className="absolute left-[15px] top-3 bottom-3 w-0.5 bg-slate-200 -z-0" />

        {stages.map((stg) => {
          const isCurrent = currentStageNum === stg.id && stg.status === "running";
          const isDone = stg.status === "done";
          const isFailed = stg.status === "failed";
          const isPending = stg.status === "pending";

          return (
            <div
              key={stg.id}
              onClick={() => (isDone || isFailed) && setSelectedStage(stg)}
              className={`relative z-10 flex items-start space-x-3 p-2 rounded-md transition cursor-pointer ${
                isCurrent
                  ? "bg-teal-50/80 border border-teal-200 shadow-sm"
                  : isDone
                  ? "hover:bg-slate-50"
                  : "opacity-60"
              }`}
            >
              {/* Icon Circle */}
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-bold transition ${
                  isDone
                    ? "bg-emerald-600 text-white"
                    : isCurrent
                    ? "bg-teal-600 text-white animate-pulse"
                    : isFailed
                    ? "bg-rose-600 text-white"
                    : "bg-slate-100 text-slate-500 border border-slate-300"
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4" />
                ) : isCurrent ? (
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : isFailed ? (
                  <AlertCircle className="w-4 h-4" />
                ) : (
                  stg.id
                )}
              </div>

              {/* Text Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className={`text-xs font-semibold ${isCurrent ? "text-teal-950 font-bold" : "text-slate-900"}`}>
                    {stg.name}
                  </h4>
                  {isDone && (
                    <div className="flex items-center space-x-1">
                      {stg.timing_ms !== undefined && stg.timing_ms > 0 && (
                        <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                          {stg.timing_ms >= 1000 ? `${(stg.timing_ms / 1000).toFixed(1)}s` : `${stg.timing_ms}ms`}
                        </span>
                      )}
                      <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                        Done
                      </span>
                    </div>
                  )}
                  {isCurrent && (
                    <span className="text-[10px] font-mono text-teal-700 bg-teal-100 px-1.5 py-0.5 rounded animate-pulse">
                      Running
                    </span>
                  )}
                </div>

                <p className="text-[11px] text-slate-500 truncate mt-0.5">
                  {stg.summary || stg.description}
                </p>
              </div>

              {stg.summary && (
                <ChevronRight className="w-3.5 h-3.5 text-slate-400 self-center shrink-0" />
              )}
            </div>
          );
        })}
      </div>

      {/* Summary Modal / Popup for clicked completed stage */}
      {selectedStage && (
        <div className="mt-4 p-3 rounded bg-slate-900 text-white text-xs border border-slate-800 shadow-lg">
          <div className="flex items-center justify-between mb-1 pb-1 border-b border-slate-800">
            <span className="font-semibold text-teal-400">Stage {selectedStage.id}: {selectedStage.name} Summary</span>
            <button
              onClick={() => setSelectedStage(null)}
              className="text-slate-400 hover:text-white font-bold"
            >
              &times;
            </button>
          </div>
          <p className="text-slate-300 mt-1 leading-relaxed">
            {selectedStage.summary || selectedStage.description}
          </p>
        </div>
      )}
    </div>
  );
}
