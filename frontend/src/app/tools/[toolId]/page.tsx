"use client";

import React, { useState, Suspense } from "react";
import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import { TOOLS_LIST } from "../page";
import { applyImageTool } from "@/lib/api";
import {
  UploadCloud,
  ArrowLeft,
  Play,
  Download,
  AlertCircle,
  FileCheck,
  Sparkles
} from "lucide-react";

function ToolContent() {
  const params = useParams();
  const router = useRouter();
  const toolId = params?.toolId as string;

  const toolConfig = TOOLS_LIST.find((t) => t.id === toolId);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [beforePreview, setBeforePreview] = useState<string | null>(null);
  const [afterPreview, setAfterPreview] = useState<string | null>(null);
  const [resultBlob, setResultBlob] = useState<Blob | null>(null);
  const [jsonResult, setJsonResult] = useState<any | null>(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Parameter states
  const [strength, setStrength] = useState(10);
  const [sharpnessIntensity, setSharpnessIntensity] = useState(1.5);
  const [angle, setAngle] = useState(90);
  const [alpha, setAlpha] = useState(1.3);
  const [beta, setBeta] = useState(10);
  const [dpi, setDpi] = useState(150);

  if (!toolConfig) {
    return (
      <div className="p-8 text-center text-slate-700 font-semibold">
        Tool not found. <button onClick={() => router.push("/tools")} className="text-teal-600 underline">Return to Tools Hub</button>
      </div>
    );
  }

  const handleFileChange = (file: File) => {
    setSelectedFile(file);
    setErrorMsg(null);
    setAfterPreview(null);
    setResultBlob(null);
    setJsonResult(null);

    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = (e) => setBeforePreview(e.target?.result as string);
      reader.readAsDataURL(file);
    } else {
      setBeforePreview(null);
    }
  };

  const handleApply = async () => {
    if (!selectedFile) return;
    setIsProcessing(true);
    setErrorMsg(null);

    try {
      const paramsMap: Record<string, any> = {};
      if (toolId === "denoise") paramsMap.strength = strength;
      if (toolId === "sharpness") paramsMap.intensity = sharpnessIntensity;
      if (toolId === "rotate") paramsMap.angle = angle;
      if (toolId === "contrast") {
        paramsMap.alpha = alpha;
        paramsMap.beta = beta;
      }
      if (toolId === "render-pdf") paramsMap.dpi = dpi;

      const result = await applyImageTool(toolId, selectedFile, paramsMap);

      if (result instanceof Blob) {
        setResultBlob(result);
        if (result.type.startsWith("image/")) {
          const url = URL.createObjectURL(result);
          setAfterPreview(url);
        } else {
          setAfterPreview(null);
        }
      } else {
        setJsonResult(result);
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to process image.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDownloadResult = () => {
    if (resultBlob) {
      const url = URL.createObjectURL(resultBlob);
      const a = document.createElement("a");
      a.href = url;
      const ext = resultBlob.type === "application/zip" ? "zip" : "png";
      a.download = `${selectedFile?.name.split(".")[0]}_${toolId}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const Icon = toolConfig.icon;

  return (
    <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
      
      {/* Back Link & Title */}
      <div className="mb-6">
        <button
          onClick={() => router.push("/tools")}
          className="flex items-center space-x-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 mb-2 transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Tools Hub</span>
        </button>

        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-lg bg-teal-600 text-white flex items-center justify-center">
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">{toolConfig.name}</h1>
            <p className="text-xs text-slate-500 mt-0.5">{toolConfig.description}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left: Input & Parameter Controls Card */}
        <div className="lg:col-span-4 bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-5">
          <h3 className="text-sm font-bold text-slate-900 border-b border-slate-100 pb-2">
            Tool Controls & Upload
          </h3>

          {/* Upload Box */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-700">Select Document/Image:</label>
            <input
              type="file"
              accept={toolConfig.accept}
              onChange={(e) => e.target.files?.[0] && handleFileChange(e.target.files[0])}
              className="w-full text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-900 file:text-white hover:file:bg-slate-800 cursor-pointer"
            />
            {selectedFile && (
              <p className="text-[11px] text-emerald-700 font-medium flex items-center gap-1">
                <FileCheck className="w-3.5 h-3.5" />
                {selectedFile.name} ({(selectedFile.size / (1024 * 1024)).toFixed(2)} MB)
              </p>
            )}
          </div>

          {/* Tool Specific Sliders & Inputs */}
          {toolId === "denoise" && (
            <div className="space-y-1 text-xs">
              <label className="font-semibold text-slate-700 flex justify-between">
                <span>Filter Strength:</span>
                <span className="font-mono text-teal-700">{strength}</span>
              </label>
              <input
                type="range"
                min={3}
                max={30}
                value={strength}
                onChange={(e) => setStrength(Number(e.target.value))}
                className="w-full"
              />
            </div>
          )}

          {toolId === "sharpness" && (
            <div className="space-y-1 text-xs">
              <label className="font-semibold text-slate-700 flex justify-between">
                <span>Sharpness Level:</span>
                <span className="font-mono text-teal-700">{sharpnessIntensity.toFixed(1)}</span>
              </label>
              <input
                type="range"
                min={0.5}
                max={3.0}
                step={0.1}
                value={sharpnessIntensity}
                onChange={(e) => setSharpnessIntensity(Number(e.target.value))}
                className="w-full"
              />
            </div>
          )}

          {toolId === "rotate" && (
            <div className="space-y-2 text-xs">
              <label className="font-semibold text-slate-700">Orientation Correction:</label>
              <div className="grid grid-cols-4 gap-1.5">
                {[
                  { label: "Auto", value: 0 },
                  { label: "90°", value: 90 },
                  { label: "180°", value: 180 },
                  { label: "270°", value: 270 }
                ].map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setAngle(opt.value)}
                    className={`py-1.5 rounded font-semibold text-xs transition ${
                      angle === opt.value
                        ? "bg-slate-900 text-white"
                        : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {toolId === "contrast" && (
            <div className="space-y-4 text-xs">
              <div>
                <label className="font-semibold text-slate-700 flex justify-between">
                  <span>Contrast (Alpha):</span>
                  <span className="font-mono text-teal-700">{alpha}</span>
                </label>
                <input
                  type="range"
                  min={0.5}
                  max={3.0}
                  step={0.1}
                  value={alpha}
                  onChange={(e) => setAlpha(Number(e.target.value))}
                  className="w-full"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 flex justify-between">
                  <span>Brightness (Beta):</span>
                  <span className="font-mono text-teal-700">{beta}</span>
                </label>
                <input
                  type="range"
                  min={-50}
                  max={50}
                  value={beta}
                  onChange={(e) => setBeta(Number(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
          )}

          {toolId === "render-pdf" && (
            <div className="space-y-2 text-xs">
              <label className="font-semibold text-slate-700">Rendering Resolution DPI:</label>
              <select
                value={dpi}
                onChange={(e) => setDpi(Number(e.target.value))}
                className="w-full p-2 rounded border border-slate-300 bg-white font-medium text-xs"
              >
                <option value={72}>72 DPI (Draft)</option>
                <option value={150}>150 DPI (Standard)</option>
                <option value={300}>300 DPI (High Resolution)</option>
              </select>
            </div>
          )}

          {/* Apply Button */}
          <button
            onClick={handleApply}
            disabled={!selectedFile || isProcessing}
            className="w-full py-2.5 rounded bg-teal-700 hover:bg-teal-600 disabled:bg-slate-300 text-white text-xs font-bold flex items-center justify-center space-x-2 shadow-sm transition"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>{isProcessing ? "Processing Filter..." : "Apply Filter"}</span>
          </button>

          {errorMsg && (
            <div className="p-3 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>

        {/* Right: Before / After Preview Canvas */}
        <div className="lg:col-span-8 bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <h3 className="text-sm font-bold text-slate-900">
              Before / After Canvas Preview
            </h3>

            {resultBlob && (
              <button
                onClick={handleDownloadResult}
                className="px-3 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-sm transition"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Result</span>
              </button>
            )}
          </div>

          {/* Image Preview Canvas Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* Before Card */}
            <div className="border border-slate-200 rounded p-3 bg-slate-50 flex flex-col items-center justify-center min-h-[300px]">
              <span className="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wider">
                Original Input
              </span>
              {beforePreview ? (
                <img src={beforePreview} alt="Original" className="max-h-[320px] rounded border border-slate-300 object-contain" />
              ) : (
                <p className="text-xs text-slate-400 font-medium">Select a file to preview original input</p>
              )}
            </div>

            {/* After Card */}
            <div className="border border-slate-200 rounded p-3 bg-slate-50 flex flex-col items-center justify-center min-h-[300px]">
              <span className="text-xs font-semibold text-teal-800 mb-2 uppercase tracking-wider">
                Processed Result
              </span>
              {isProcessing ? (
                <div className="flex flex-col items-center space-y-2 text-xs text-slate-500">
                  <div className="w-6 h-6 border-2 border-teal-600 border-t-transparent rounded-full animate-spin" />
                  <span>Executing OpenCV engine...</span>
                </div>
              ) : afterPreview ? (
                <img src={afterPreview} alt="Result" className="max-h-[320px] rounded border border-teal-500 shadow-sm object-contain" />
              ) : jsonResult ? (
                <div className="w-full text-left bg-slate-900 text-slate-100 p-4 rounded font-mono text-xs overflow-x-auto max-h-[320px]">
                  <pre>{JSON.stringify(jsonResult, null, 2)}</pre>
                </div>
              ) : (
                <p className="text-xs text-slate-400 font-medium">Click "Apply Filter" to see processed preview</p>
              )}
            </div>

          </div>
        </div>

      </div>

    </main>
  );
}

export default function DedicatedToolPage() {
  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans text-slate-900">
      <Navbar />
      <Suspense fallback={<div className="p-8 text-center text-xs text-slate-500">Loading tool...</div>}>
        <ToolContent />
      </Suspense>
    </div>
  );
}
