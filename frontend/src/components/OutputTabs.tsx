"use client";

import React, { useState } from "react";
import { Copy, Download, FileText, Code, AlignLeft, Database, Check, Archive } from "lucide-react";
import { JobResult, DocumentBlock } from "@/types";
import ConfidenceLegend from "@/components/ConfidenceLegend";
import SemanticIndexTab from "@/components/SemanticIndexTab";
import { getExportUrl } from "@/lib/api";

interface OutputTabsProps {
  jobResult: JobResult;
  showLowConfidenceOnly: boolean;
  onToggleFilter: (val: boolean) => void;
  onEditBlock?: (block: DocumentBlock) => void;
  onSelectChunkBlocks?: (blockIds: string[]) => void;
}

export default function OutputTabs({
  jobResult,
  showLowConfidenceOnly,
  onToggleFilter,
  onEditBlock,
  onSelectChunkBlocks
}: OutputTabsProps) {
  const [activeTab, setActiveTab] = useState<"md" | "json" | "ocr" | "semantic">("md");
  const [copied, setCopied] = useState(false);

  const allBlocks = jobResult.pages.flatMap((p) => p.blocks);
  const redCount = allBlocks.filter((b) => b.confidence < 0.70).length;
  const yellowCount = allBlocks.filter((b) => b.confidence >= 0.70 && b.confidence < 0.90).length;
  const greenCount = allBlocks.filter((b) => b.confidence >= 0.90).length;

  const currentContent =
    activeTab === "md"
      ? jobResult.markdown
      : activeTab === "json"
      ? JSON.stringify(jobResult, null, 2)
      : activeTab === "ocr"
      ? jobResult.ocr_text
      : "";

  const handleCopy = () => {
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSingleDownload = () => {
    const ext = activeTab === "md" ? "md" : activeTab === "json" ? "json" : "txt";
    const mime = activeTab === "json" ? "application/json" : "text/plain";
    const blob = new Blob([currentContent], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${jobResult.filename.split(".")[0]}_synopsize.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 mb-6">
      {/* Tabs Bar & Export Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-1 border-b sm:border-b-0 border-slate-200 pb-2 sm:pb-0">
          <button
            onClick={() => setActiveTab("md")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition ${
              activeTab === "md"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Markdown</span>
          </button>

          <button
            onClick={() => setActiveTab("json")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition ${
              activeTab === "json"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            <span>JSON</span>
          </button>

          <button
            onClick={() => setActiveTab("ocr")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition ${
              activeTab === "ocr"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <AlignLeft className="w-3.5 h-3.5" />
            <span>OCR Text</span>
          </button>

          <button
            onClick={() => setActiveTab("semantic")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition ${
              activeTab === "semantic"
                ? "bg-teal-700 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <Database className="w-3.5 h-3.5 text-teal-300" />
            <span>Semantic Index</span>
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          {activeTab !== "semantic" && (
            <>
              <button
                onClick={handleCopy}
                className="px-2.5 py-1.5 rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-medium flex items-center space-x-1 transition"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>

              <button
                onClick={handleSingleDownload}
                className="px-2.5 py-1.5 rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-medium flex items-center space-x-1 transition"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                <span>Download</span>
              </button>
            </>
          )}

          <a
            href={getExportUrl(jobResult.document_id, "zip")}
            download
            className="px-3 py-1.5 rounded bg-teal-700 hover:bg-teal-600 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-sm transition"
          >
            <Archive className="w-3.5 h-3.5" />
            <span>Download All (.zip)</span>
          </a>
        </div>
      </div>

      {/* Tab Output Body */}
      <div className="mt-4">
        {activeTab === "semantic" ? (
          <SemanticIndexTab
            jobId={jobResult.document_id}
            chunks={jobResult.chunks}
            onSelectChunkBlocks={onSelectChunkBlocks}
          />
        ) : (
          <div className="bg-slate-950 text-slate-100 rounded-lg p-4 font-mono text-xs overflow-x-auto max-h-[500px] leading-relaxed border border-slate-900 shadow-inner">
            <pre className="whitespace-pre-wrap">{currentContent}</pre>
          </div>
        )}
      </div>

      {/* Confidence Indicators Legend */}
      <ConfidenceLegend
        showLowConfidenceOnly={showLowConfidenceOnly}
        onToggleFilter={onToggleFilter}
        redCount={redCount}
        yellowCount={yellowCount}
        greenCount={greenCount}
      />
    </div>
  );
}
