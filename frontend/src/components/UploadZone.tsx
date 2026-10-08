"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, FileCheck, AlertCircle, RefreshCw } from "lucide-react";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  isLoading?: boolean;
  selectedFile?: File | null;
  onReset?: () => void;
}

const ALLOWED_EXTENSIONS = [
  ".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".heic",
  ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".csv",
  ".html", ".htm", ".md", ".txt", ".rtf", ".eml", ".msg"
];

export default function UploadZone({
  onFileSelect,
  isLoading = false,
  selectedFile = null,
  onReset
}: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    const ext = "." + file.name.split(".").pop()?.toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setErrorMsg(`Unsupported file type '${ext}'. Accepted: ${ALLOWED_EXTENSIONS.join(", ")}`);
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      setErrorMsg(`File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds 50 MB limit.`);
      return;
    }

    setErrorMsg(null);
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 mb-6">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
        <div>
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold">1</span>
            Document Upload
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Supported: PDF, images, Office, CSV, text, HTML, RTF and email (Max 50 MB)
          </p>
        </div>

        {selectedFile && onReset && (
          <button
            onClick={onReset}
            disabled={isLoading}
            className="flex items-center space-x-1 text-xs font-medium text-slate-600 hover:text-slate-900 px-2.5 py-1.5 rounded border border-slate-200 hover:bg-slate-50 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Upload Another File</span>
          </button>
        )}
      </div>

      {!selectedFile ? (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition ${
            isDragOver
              ? "border-teal-500 bg-teal-50/50"
              : "border-slate-300 hover:border-slate-400 bg-slate-50/50"
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFiles(e.target.files)}
            accept={ALLOWED_EXTENSIONS.join(",")}
            className="hidden"
          />

          <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-600 mx-auto flex items-center justify-center mb-3">
            <UploadCloud className="w-6 h-6 text-slate-700" />
          </div>

          <p className="text-sm font-semibold text-slate-800">
            Drag and drop your document here, or <span className="text-teal-700 underline">browse</span>
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Engineered with strict magic byte validation, macro scanning & decompression protection.
          </p>
        </div>
      ) : (
        <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 border border-slate-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded bg-teal-100 text-teal-800 flex items-center justify-center font-semibold text-xs uppercase">
              {selectedFile.name.split(".").pop()}
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-900 truncate max-w-md">
                {selectedFile.name}
              </p>
              <p className="text-xs text-slate-500">
                Size: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB &bull; Type: {selectedFile.type || "Document"}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1">
              <FileCheck className="w-3.5 h-3.5" />
              File Selected
            </span>
          </div>
        </div>
      )}

      {errorMsg && (
        <div className="mt-3 p-3 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}
