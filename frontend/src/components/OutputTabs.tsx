"use client";

import React, { useEffect, useState } from "react";
import { Copy, Download, FileText, Code, AlignLeft, Database, Check, Archive, ShieldCheck, ScrollText } from "lucide-react";
import { JobResult, DocumentBlock } from "@/types";
import ConfidenceLegend from "@/components/ConfidenceLegend";
import SemanticIndexTab from "@/components/SemanticIndexTab";
import MathContent from "@/components/MathContent";
import { getAuditLog, getExportUrl } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

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
  onSelectChunkBlocks
}: OutputTabsProps) {
  const [activeTab, setActiveTab] = useState<"md" | "json" | "ocr" | "semantic" | "validation" | "audit">("md");
  const [markdownMode, setMarkdownMode] = useState<"rendered" | "source">("rendered");
  const [copied, setCopied] = useState(false);
  const [auditContent, setAuditContent] = useState("Loading audit log...");

  const allBlocks = jobResult.pages.flatMap((p) => p.blocks);
  const redCount = allBlocks.filter((b) => b.confidence < 0.70).length;
  const yellowCount = allBlocks.filter((b) => b.confidence >= 0.70 && b.confidence < 0.90).length;
  const greenCount = allBlocks.filter((b) => b.confidence >= 0.90).length;
  const validationContent = JSON.stringify(
    {
      status: "complete",
      total_pages: jobResult.total_pages,
      overall_extraction_signal:
        jobResult.overall_extraction_signal ?? jobResult.overall_confidence,
      confidence_calibrated: jobResult.confidence_calibrated ?? false,
      review_blocks: allBlocks
        .filter((block) => block.flags?.includes("needs_review"))
        .map(({ id, type, page, confidence, flags }) => ({ id, type, page, confidence, flags })),
      stages: jobResult.stages,
    },
    null,
    2
  );

  const currentContent =
    activeTab === "md"
      ? jobResult.markdown
      : activeTab === "json"
      ? JSON.stringify(jobResult, null, 2)
      : activeTab === "ocr"
      ? jobResult.ocr_text
      : activeTab === "validation"
      ? validationContent
      : activeTab === "audit"
      ? auditContent
      : "";
  const renderableMarkdown = jobResult.markdown
    .replace(/\\\[([\s\S]*?)\\\]/g, (_match, equation: string) => `$$\n${equation}\n$$`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_match, equation: string) => `$${equation}$`);

  useEffect(() => {
    if (activeTab !== "audit") return;
    let cancelled = false;
    getAuditLog()
      .then((data) => {
        if (!cancelled) setAuditContent(JSON.stringify(data, null, 2));
      })
      .catch((error: Error) => {
        if (!cancelled) setAuditContent(JSON.stringify({ error: error.message }, null, 2));
      });
    return () => {
      cancelled = true;
    };
  }, [activeTab]);

  const handleCopy = () => {
    navigator.clipboard.writeText(currentContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSingleDownload = () => {
    const ext = activeTab === "md" ? "md" : activeTab === "ocr" ? "txt" : "json";
    const mime = activeTab === "md" ? "text/markdown" : activeTab === "ocr" ? "text/plain" : "application/json";
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

          <button
            onClick={() => setActiveTab("validation")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition ${
              activeTab === "validation"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Validation</span>
          </button>

          <button
            onClick={() => setActiveTab("audit")}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded text-xs font-semibold transition ${
              activeTab === "audit"
                ? "bg-slate-900 text-white shadow-sm"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            }`}
          >
            <ScrollText className="w-3.5 h-3.5" />
            <span>Audit</span>
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
          <>
            {activeTab === "md" && (
              <div className="mb-3 flex items-center justify-end gap-1">
                <span className="mr-2 text-xs text-slate-500">Markdown view</span>
                {(["rendered", "source"] as const).map((mode) => (
                  <button
                    key={mode}
                    type="button"
                    aria-pressed={markdownMode === mode}
                    onClick={() => setMarkdownMode(mode)}
                    className={`rounded px-3 py-1.5 text-xs font-semibold transition ${
                      markdownMode === mode
                        ? "bg-slate-900 text-white"
                        : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {mode === "rendered" ? "Rendered" : "Raw Markdown"}
                  </button>
                ))}
              </div>
            )}
            <div
              className={`rounded-lg p-4 text-xs leading-relaxed border shadow-inner overflow-x-auto max-h-[500px] ${
                activeTab === "md" && markdownMode === "rendered"
                  ? "markdown-preview bg-white text-slate-900 border-slate-200"
                  : "bg-slate-950 text-slate-100 border-slate-900 font-mono"
              }`}
            >
              {activeTab === "md" ? (
                markdownMode === "rendered" ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                      h1: ({ children }) => (
                        <h1 className="mb-3 text-xl font-bold">{children}</h1>
                      ),
                      h2: ({ children }) => (
                        <h2 className="mb-2 mt-4 text-lg font-bold">{children}</h2>
                      ),
                      h3: ({ children }) => (
                        <h3 className="mb-2 mt-3 text-base font-semibold">{children}</h3>
                      ),
                      p: ({ children }) => (
                        <p className="mb-2 whitespace-pre-wrap">{children}</p>
                      ),
                      ul: ({ children }) => (
                        <ul className="mb-2 list-disc pl-6">{children}</ul>
                      ),
                      ol: ({ children }) => (
                        <ol className="mb-2 list-decimal pl-6">{children}</ol>
                      ),
                      li: ({ children }) => <li className="mb-1">{children}</li>,
                      img: ({ src, alt }) => {
                        if (typeof src !== "string" || !src.trim()) return null;
                        return (
                          <img
                            src={src}
                            alt={alt || "Document image"}
                            className="my-2 max-h-96 max-w-full rounded border border-slate-200 object-contain"
                          />
                        );
                      },
                      pre: ({ children }) => (
                        <pre className="my-2 overflow-x-auto rounded bg-slate-100 p-3">
                          {children}
                        </pre>
                      ),
                      table: ({ children }) => (
                        <table className="my-3 border-collapse border border-slate-300">
                          {children}
                        </table>
                      ),
                      th: ({ children }) => (
                        <th className="border border-slate-300 bg-slate-100 px-2 py-1 text-left">
                          {children}
                        </th>
                      ),
                      td: ({ children }) => (
                        <td className="border border-slate-300 px-2 py-1">{children}</td>
                      ),
                    }}
                  >
                    {renderableMarkdown}
                  </ReactMarkdown>
                ) : (
                  <pre className="whitespace-pre-wrap">{currentContent}</pre>
                )
              ) : (
                <pre className="whitespace-pre-wrap">
                  {activeTab === "ocr" ? (
                    <MathContent content={currentContent} />
                  ) : (
                    currentContent
                  )}
                </pre>
              )}
            </div>
          </>
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
