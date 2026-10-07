"use client";

import React, { useState } from "react";
import { DocumentBlock } from "@/types";
import { Check, X, Edit3 } from "lucide-react";
import { saveCorrection } from "@/lib/api";

interface InlineCorrectionModalProps {
  block: DocumentBlock | null;
  onClose: () => void;
  onSaveSuccess: (blockId: string, newContent: string) => void;
}

export default function InlineCorrectionModal({
  block,
  onClose,
  onSaveSuccess
}: InlineCorrectionModalProps) {
  if (!block) return null;

  const [text, setText] = useState(block.content);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Send silent correction log to backend
      await saveCorrection({
        original_text: block.content,
        corrected_text: text,
        page: block.page,
        extractor: block.extractor,
        confidence: block.confidence,
        bbox: block.bbox
      });

      onSaveSuccess(block.id, text);
      onClose();
    } catch (e) {
      console.error("Save error", e);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-lg w-full p-6">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <Edit3 className="w-4 h-4 text-slate-700" />
            <h3 className="text-sm font-bold text-slate-900">
              Edit Block Text (Page {block.page}, Block #{block.reading_order})
            </h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 font-bold text-lg">
            &times;
          </button>
        </div>

        <div className="my-4 space-y-3 text-xs">
          <div>
            <label className="block text-slate-500 font-semibold mb-1">
              Original Extracted Text ({block.extractor}, Score: {(block.confidence * 100).toFixed(0)}%):
            </label>
            <div className="p-2.5 rounded bg-slate-50 border border-slate-200 text-slate-600 font-mono line-clamp-3">
              {block.content}
            </div>
          </div>

          <div>
            <label className="block text-slate-800 font-semibold mb-1">
              Corrected Text:
            </label>
            <textarea
              rows={5}
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="w-full p-3 rounded border border-slate-300 text-slate-900 font-sans focus:ring-2 focus:ring-teal-500 focus:border-teal-500 focus:outline-none text-xs"
            />
          </div>
        </div>

        <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-sm"
          >
            <Check className="w-3.5 h-3.5" />
            <span>{isSaving ? "Saving..." : "Save Correction"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
