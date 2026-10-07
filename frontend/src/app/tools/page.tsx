"use client";

import React from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import {
  Compass,
  Sparkles,
  Maximize2,
  RotateCw,
  Sun,
  FileX,
  CopyCheck,
  FileImage,
  ArrowRight
} from "lucide-react";

export const TOOLS_LIST = [
  {
    id: "deskew",
    name: "Image Deskewing",
    description: "Detects text angle alignment and corrects rotational skew automatically.",
    icon: Compass,
    accept: ".png, .jpg, .jpeg"
  },
  {
    id: "denoise",
    name: "Noise & Background Removal",
    description: "Cleans background artifacts, paper scan shadows, and high-frequency sensor noise.",
    icon: Sparkles,
    accept: ".png, .jpg, .jpeg"
  },
  {
    id: "sharpness",
    name: "Sharpness Enhancement",
    description: "Improves edge contrast and text clarity using local sharpening without artificially enlarging the image.",
    icon: Maximize2,
    accept: ".png, .jpg, .jpeg"
  },
  {
    id: "rotate",
    name: "Rotation Correction",
    description: "Adjusts orientation manually by 90°, 180°, or 270° degrees.",
    icon: RotateCw,
    accept: ".png, .jpg, .jpeg"
  },
  {
    id: "contrast",
    name: "Contrast & Brightness Adjustment",
    description: "Fine-tunes image contrast (alpha) and brightness (beta) controls.",
    icon: Sun,
    accept: ".png, .jpg, .jpeg"
  },
  {
    id: "blank-pages",
    name: "Blank Page Detection",
    description: "Scans PDF pages or images and flags empty/blank pages using variance of Laplacian.",
    icon: FileX,
    accept: ".pdf, .png, .jpg, .jpeg"
  },
  {
    id: "duplicates",
    name: "Duplicate Page Detection",
    description: "Groups near-duplicate document pages using perceptual difference hashing (dhash).",
    icon: CopyCheck,
    accept: ".pdf"
  },
  {
    id: "render-pdf",
    name: "PDF Page Rendering",
    description: "Renders multi-page PDF documents into high-resolution PNG page images packaged in a .zip.",
    icon: FileImage,
    accept: ".pdf"
  }
];

export default function ToolsHubPage() {
  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans text-slate-900">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Image Tools Hub
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Standalone document pre-processing and quality enhancement utilities. All tools run strict magic byte validation and security threat scans.
          </p>
        </div>

        {/* 8 Tools Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {TOOLS_LIST.map((tool) => {
            const Icon = tool.icon;

            return (
              <Link
                key={tool.id}
                href={`/tools/${tool.id}`}
                className="bg-white rounded-lg border border-slate-200 hover:border-teal-500 hover:shadow-md p-6 flex flex-col justify-between transition group"
              >
                <div>
                  <div className="w-12 h-12 rounded-lg bg-teal-50 border border-teal-100 text-teal-800 flex items-center justify-center mb-4 group-hover:bg-teal-600 group-hover:text-white transition">
                    <Icon className="w-6 h-6" />
                  </div>

                  <h3 className="text-base font-bold text-slate-900 group-hover:text-teal-950 transition">
                    {tool.name}
                  </h3>

                  <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                    {tool.description}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-teal-700 group-hover:text-teal-900">
                  <span>Open Tool</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            );
          })}
        </div>

      </main>
    </div>
  );
}
