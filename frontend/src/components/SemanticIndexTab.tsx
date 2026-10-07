"use client";

import React, { useState } from "react";
import { SemanticChunk } from "@/types";
import { Search, Download, Database, Layers, Sparkles, Check } from "lucide-react";
import { searchSemanticChunks } from "@/lib/api";

interface SemanticIndexTabProps {
  jobId: string;
  chunks: SemanticChunk[];
  onSelectChunkBlocks?: (blockIds: string[]) => void;
}

export default function SemanticIndexTab({
  jobId,
  chunks: initialChunks,
  onSelectChunkBlocks
}: SemanticIndexTabProps) {
  const [query, setQuery] = useState("");
  const [chunks, setChunks] = useState<SemanticChunk[]>(initialChunks);
  const [isSearching, setIsSearching] = useState(false);
  const [copiedJsonl, setCopiedJsonl] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setChunks(initialChunks);
      return;
    }
    setIsSearching(true);
    try {
      const res = await searchSemanticChunks(jobId, query);
      if (res.results) {
        setChunks(res.results);
      }
    } catch (err) {
      console.error("Semantic search failed", err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleDownloadJsonl = () => {
    const jsonlStr = initialChunks.map((c) => JSON.stringify(c)).join("\n");
    const blob = new Blob([jsonlStr], { type: "application/x-jsonlines" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `synopsize_semantic_chunks_${jobId.slice(0, 8)}.jsonl`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      {/* Top Controls & Vector Search Header */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 p-4 rounded-lg bg-slate-900 text-white shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded bg-teal-600 flex items-center justify-center font-bold text-white shrink-0">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold tracking-tight">Semantic Index & Vector Embeddings</h4>
            <p className="text-xs text-slate-300">
              {initialChunks.length} Structural Chunks &bull; Model: <span className="font-mono text-teal-300">all-MiniLM-L6-v2</span>
            </p>
          </div>
        </div>

        {/* Search Bar & Export Button */}
        <div className="flex items-center space-x-2">
          <form onSubmit={handleSearch} className="flex items-center relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search vector index..."
              className="pl-8 pr-3 py-1.5 rounded-l text-xs bg-slate-800 border border-slate-700 text-white focus:outline-none focus:ring-1 focus:ring-teal-500 w-48 sm:w-64"
            />
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <button
              type="submit"
              disabled={isSearching}
              className="px-3 py-1.5 rounded-r bg-teal-600 hover:bg-teal-500 text-white text-xs font-medium transition flex items-center gap-1"
            >
              {isSearching ? "Searching..." : "Search"}
            </button>
          </form>

          <button
            onClick={handleDownloadJsonl}
            className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white text-xs font-medium flex items-center space-x-1.5 transition shrink-0"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export JSONL</span>
          </button>
        </div>
      </div>

      {/* Chunks List */}
      <div className="space-y-3 max-h-[550px] overflow-y-auto pr-1">
        {chunks.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500 bg-white rounded border border-slate-200">
            No matching semantic chunks found for "{query}".
          </div>
        ) : (
          chunks.map((c) => (
            <div
              key={c.chunk_id}
              onClick={() => onSelectChunkBlocks && onSelectChunkBlocks(c.block_ids)}
              className="p-4 rounded-lg bg-white border border-slate-200 hover:border-teal-400 transition cursor-pointer shadow-sm group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-teal-100 text-teal-800">
                    {c.chunk_id}
                  </span>
                  <span className="text-xs font-semibold text-slate-700">
                    {c.section_path}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Pages {c.page_range[0]}–{c.page_range[1]}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  {c.score !== undefined && (
                    <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-200">
                      Score: {(c.score * 100).toFixed(1)}%
                    </span>
                  )}
                  <span className="text-[11px] font-mono text-slate-400">
                    ~{c.token_count || c.text.split(" ").length} tokens
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-800 leading-relaxed font-sans line-clamp-3 bg-slate-50 p-2.5 rounded border border-slate-100">
                {c.text}
              </p>

              <div className="mt-2 text-[11px] text-slate-400 flex items-center justify-between">
                <span>Associated Block IDs: {c.block_ids.join(", ")}</span>
                <span className="text-teal-600 group-hover:underline font-medium">Click to highlight on canvas &rarr;</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
