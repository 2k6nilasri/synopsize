"use client";

import React from "react";
import { DocumentPage, DocumentBlock, ConfidenceLevel } from "@/types";
import { Edit3, BarChart2, Layers } from "lucide-react";
import { MathEquation } from "@/components/MathContent";

interface PageViewerProps {
  pages: DocumentPage[];
  currentPageIndex: number;
  onSelectPage: (idx: number) => void;
  selectedBlockId: string | null;
  onSelectBlock: (blockId: string | null) => void;
  onEditBlock?: (block: DocumentBlock) => void;
  showLowConfidenceOnly?: boolean;
}

export default function PageViewer({
  pages,
  currentPageIndex,
  onSelectPage,
  selectedBlockId,
  onSelectBlock,
  onEditBlock,
  showLowConfidenceOnly = false
}: PageViewerProps) {
  const page = pages[currentPageIndex];

  React.useEffect(() => {
    if (selectedBlockId) {
      const el = document.getElementById(`block-element-${selectedBlockId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [selectedBlockId]);

  if (!page) return null;

  const filteredBlocks = showLowConfidenceOnly
    ? page.blocks.filter((b) => b.confidence < 0.90)
    : page.blocks;

  const getConfDot = (level: ConfidenceLevel, score: number) => {
    if (level === "green" || score >= 0.90) {
      return (
        <span
          title={`High extractor signal (${(score * 100).toFixed(0)}%); not a correctness probability`}
          className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[11px] font-mono bg-emerald-100 text-emerald-800 border border-emerald-300 shrink-0"
        >
          <span className="w-2 h-2 rounded-full bg-emerald-600 inline-block" />
          <span>● {(score * 100).toFixed(0)}%</span>
        </span>
      );
    } else if (level === "yellow" || score >= 0.70) {
      return (
        <span
          title={`Medium extractor signal (${(score * 100).toFixed(0)}%); review suggested`}
          className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[11px] font-mono bg-amber-100 text-amber-900 border border-amber-300 shrink-0"
        >
          <span className="w-2 h-2 rounded-full bg-amber-500 inline-block animate-pulse" />
          <span>▲ {(score * 100).toFixed(0)}%</span>
        </span>
      );
    } else {
      return (
        <span
          title={`Low extractor signal (${(score * 100).toFixed(0)}%); review suggested`}
          className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[11px] font-mono bg-rose-100 text-rose-900 border border-rose-300 shrink-0"
        >
          <span className="w-2 h-2 rounded-full bg-rose-600 inline-block" />
          <span>■ {(score * 100).toFixed(0)}%</span>
        </span>
      );
    }
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 mb-6">
      {/* Page Navigator Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div className="flex items-center space-x-2">
          <Layers className="w-4 h-4 text-slate-700" />
          <h3 className="text-sm font-bold text-slate-900">
            Page Navigator ({pages.length} Pages)
          </h3>
        </div>

        {/* Thumbnails / Page Selector */}
        <div className="flex items-center space-x-1.5">
          {pages.map((p, idx) => (
            <button
              key={p.page_number}
              onClick={() => onSelectPage(idx)}
              className={`px-3 py-1 text-xs font-semibold rounded transition ${
                currentPageIndex === idx
                  ? "bg-slate-900 text-white shadow-sm"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              Page {p.page_number}
            </button>
          ))}
        </div>
      </div>

      {/* Side-by-Side Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Left: Original Rendered Page Image with Bounding Box Overlays */}
        <div className="border border-slate-200 rounded bg-slate-100 p-2 relative flex flex-col items-center justify-start overflow-hidden">
          <div className="w-full flex items-center justify-between mb-2 text-xs font-semibold text-slate-600 px-2">
            <span>Original Document Canvas</span>
            <span>{page.width} x {page.height} px</span>
          </div>

          <div className="relative inline-block max-w-full">
            {/* Page Image */}
            <img
              src={page.image_data}
              alt={`Page ${page.page_number}`}
              className="w-full h-auto rounded border border-slate-300 block select-none"
            />

            {/* Bounding Box SVG Overlays */}
            <svg
              className="absolute top-0 left-0 w-full h-full pointer-events-auto"
              viewBox={`0 0 ${page.width} ${page.height}`}
            >
              {page.blocks.map((b) => {
                const [x0, y0, x1, y1] = b.bbox;
                const isSelected = selectedBlockId === b.id;
                const isLowConf = b.confidence < 0.70;
                
                return (
                  <rect
                    key={b.id}
                    x={x0}
                    y={y0}
                    width={Math.max(10, x1 - x0)}
                    height={Math.max(10, y1 - y0)}
                    onClick={() => onSelectBlock(b.id)}
                    className={`cursor-pointer transition ${
                      isSelected
                        ? "fill-teal-500/30 stroke-teal-600 stroke-[4]"
                        : isLowConf
                        ? "fill-rose-500/20 stroke-rose-600 stroke-[2] stroke-dasharray-[4,4]"
                        : "fill-transparent hover:fill-amber-500/20 stroke-slate-500 stroke-[1.5]"
                    }`}
                  />
                );
              })}
            </svg>
          </div>
        </div>

        {/* Right: Parsed Blocks & Region Inspection */}
        <div className="space-y-4 max-h-[650px] overflow-y-auto pr-1">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-700">
              Parsed Region Blocks ({filteredBlocks.length})
            </span>
            {showLowConfidenceOnly && (
              <span className="text-[11px] bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-medium">
                Filtering Low Confidence Blocks
              </span>
            )}
          </div>

          {filteredBlocks.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500 bg-slate-50 rounded border border-slate-200">
              No low-signal blocks found on this page. Review extracted content; signals do not verify correctness.
            </div>
          ) : (
            filteredBlocks.map((b) => {
              const isSelected = selectedBlockId === b.id;
              const isLowConf = b.confidence < 0.90;

              return (
                <div
                  key={b.id}
                  id={`block-element-${b.id}`}
                  onClick={() => onSelectBlock(b.id)}
                  className={`p-3.5 rounded-lg border transition ${
                    isSelected
                      ? "bg-teal-50/70 border-teal-500 ring-2 ring-teal-500/20 shadow-sm"
                      : "bg-white border-slate-200 hover:border-slate-300"
                  }`}
                >
                  {/* Block Header */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-bold px-1.5 py-0.5 rounded bg-slate-900 text-white">
                        #{b.reading_order}
                      </span>
                      <span className="text-xs font-semibold text-slate-800 uppercase tracking-wide px-2 py-0.5 rounded bg-slate-100 border border-slate-200">
                        {b.type}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                        {b.extractor}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span title={
                        b.confidence_basis === "ocr_engine_score"
                          ? "Based on the OCR engine's recognition output; not calibrated against ground truth."
                          : "Heuristic from the extractor; not calibrated against ground truth."
                      }>
                        {getConfDot(b.confidence_level, b.confidence)}
                      </span>

                      {/* Subtle Hidden Edit Action for Low Confidence Blocks */}
                      {isLowConf && onEditBlock && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onEditBlock(b);
                          }}
                          className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium flex items-center space-x-1 border border-slate-300 transition"
                          title="Inline edit text"
                        >
                          <Edit3 className="w-3 h-3 text-slate-600" />
                          <span>Edit</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Block Content Render */}
                  <div className="text-xs text-slate-800 leading-relaxed font-sans mt-1">
                    {b.type === "table" ? (
                      <div className="overflow-x-auto my-2 p-2 bg-slate-50 rounded border border-slate-200 font-mono text-[11px]">
                        <pre className="whitespace-pre">{b.content}</pre>
                      </div>
                    ) : b.type === "chart" || b.type === "image" ? (
                      <div className="my-2 p-3 bg-slate-50 rounded border border-slate-200">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-semibold text-slate-700 flex items-center gap-1">
                            <BarChart2 className="w-3.5 h-3.5 text-teal-700" />
                            Extracted {b.type === "chart" ? "Data Chart" : "Visual Figure"}
                          </span>
                          {b.metadata?.chart_type && (
                            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-teal-100 text-teal-800">
                              {b.metadata.chart_type}
                            </span>
                          )}
                        </div>

                        {b.content.includes("data:image") && (
                          <img
                            src={b.content.match(/data:image\/[^)]+/)?.[0]}
                            alt="Visual region"
                            className="max-h-48 rounded border border-slate-300 mx-auto my-2"
                          />
                        )}

                        {b.metadata?.series && (
                          <div className="mt-2 text-[11px] font-mono bg-white p-2 rounded border border-slate-200">
                            <p className="font-bold text-slate-800 mb-1">Extracted Series Data:</p>
                            {b.metadata.series.map((s, idx) => (
                              <div key={idx} className="flex justify-between py-0.5 border-b border-slate-100 last:border-0">
                                <span>{s.name}:</span>
                                <span>[{(s.data ?? s.values ?? []).join(", ")}]</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : b.type === "equation" ? (
                      <MathEquation content={b.metadata?.latex || b.content} />
                    ) : (
                      <p className="whitespace-pre-wrap">{b.content}</p>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

      </div>
    </div>
  );
}
