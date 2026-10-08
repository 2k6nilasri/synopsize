"use client";

import React from "react";
import { CheckCircle2, XCircle, ShieldCheck, AlertTriangle, Play } from "lucide-react";
import { ValidationReport as ValidationReportType } from "@/types";

interface ValidationReportProps {
  report: ValidationReportType | null;
  isValidating?: boolean;
  onStartProcessing?: () => void;
  isProcessing?: boolean;
}

export default function ValidationReport({
  report,
  isValidating = false,
  onStartProcessing,
  isProcessing = false
}: ValidationReportProps) {
  if (isValidating) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
        <div className="flex items-center space-x-3 text-slate-700">
          <div className="w-4 h-4 rounded-full border-2 border-slate-900 border-t-transparent animate-spin" />
          <span className="text-sm font-semibold">Checking file format, size, integrity, structural safety, and configured antivirus...</span>
        </div>
      </div>
    );
  }

  if (!report) return null;

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold">2</span>
          File Security & Integrity Validation
        </h2>
        <span className="text-xs text-slate-500 font-mono">ID: {report.file_id.slice(0, 8)}</span>
      </div>

      {/* Check Lines */}
      <div className="space-y-2 mb-4">
        {report.checks.map((check, idx) => (
          <div
            key={idx}
            className={`p-3 rounded border text-xs flex items-start space-x-3 transition ${
              check.passed === true
                ? "bg-slate-50 border-slate-200 text-slate-800"
                : check.passed === null
                ? "bg-amber-50 border-amber-200 text-amber-900"
                : "bg-rose-50 border-rose-200 text-rose-900"
            }`}
          >
            {check.passed === true ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : check.passed === null ? (
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <span className="font-semibold text-slate-900 mr-2">{check.name}{check.passed === null ? " (not run)" : ""}:</span>
              <span className="text-slate-700">{check.message}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Banner */}
      <div
        className={`p-4 rounded-md border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          report.is_valid
            ? "bg-emerald-50 border-emerald-300 text-emerald-900"
            : "bg-rose-50 border-rose-300 text-rose-900"
        }`}
      >
        <div className="flex items-center space-x-3">
          {report.is_valid ? (
            <ShieldCheck className="w-6 h-6 text-emerald-700 shrink-0" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-rose-700 shrink-0" />
          )}
          <div>
            <h3 className="text-sm font-bold">{report.banner_message}</h3>
            {report.is_valid ? (
              <p className="text-xs text-emerald-800 mt-0.5">
                Ready to execute 7-stage Universal Document Intelligence Pipeline.
              </p>
            ) : (
              <p className="text-xs mt-0.5 text-rose-800">
                Pipeline execution halted. Bad or suspicious files are blocked for security.
              </p>
            )}
          </div>
        </div>

        {report.is_valid && onStartProcessing && (
          <button
            onClick={onStartProcessing}
            disabled={isProcessing}
            className="px-4 py-2 rounded bg-slate-900 hover:bg-slate-800 disabled:bg-slate-600 text-white text-xs font-bold flex items-center justify-center space-x-2 shadow-sm transition shrink-0"
          >
            {isProcessing ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Processing Pipeline...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Start Processing Pipeline</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
