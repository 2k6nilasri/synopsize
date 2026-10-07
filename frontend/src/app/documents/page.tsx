"use client";

import React from "react";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { FolderOpen, FileText, ArrowRight, ShieldCheck, Clock } from "lucide-react";

export default function DocumentsPage() {
  const mockDocuments = [
    {
      id: "doc-sample-1",
      filename: "Financial_Report_Q3_2026.pdf",
      file_type: "pdf",
      total_pages: 14,
      confidence: 0.94,
      confidence_level: "green",
      created_at: "2026-10-07 15:40:00",
      size: "4.2 MB"
    },
    {
      id: "doc-sample-2",
      filename: "Employee_Form_Scan.png",
      file_type: "png",
      total_pages: 1,
      confidence: 0.82,
      confidence_level: "yellow",
      created_at: "2026-10-07 14:12:00",
      size: "1.8 MB"
    },
    {
      id: "doc-sample-3",
      filename: "Supply_Chain_Analytics.xlsx",
      file_type: "xlsx",
      total_pages: 3,
      confidence: 0.98,
      confidence_level: "green",
      created_at: "2026-10-07 11:05:00",
      size: "620 KB"
    }
  ];

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans text-slate-900">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Documents Library
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              History of parsed documents and extracted structured outputs.
            </p>
          </div>

          <Link
            href="/"
            className="px-4 py-2 rounded bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center space-x-1.5 shadow-sm transition"
          >
            <FileText className="w-4 h-4" />
            <span>Process New Document</span>
          </Link>
        </div>

        {/* Documents Table */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-900 text-slate-200 font-semibold border-b border-slate-800">
                <th className="p-3.5">Document Name</th>
                <th className="p-3.5">Format</th>
                <th className="p-3.5">Size</th>
                <th className="p-3.5">Pages</th>
                <th className="p-3.5">Confidence</th>
                <th className="p-3.5">Processed Date</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {mockDocuments.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-50 transition">
                  <td className="p-3.5 font-bold text-slate-900 flex items-center space-x-2">
                    <FileText className="w-4 h-4 text-teal-700" />
                    <span>{doc.filename}</span>
                  </td>
                  <td className="p-3.5">
                    <span className="uppercase font-mono px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700 font-bold">
                      {doc.file_type}
                    </span>
                  </td>
                  <td className="p-3.5 font-mono text-slate-600">{doc.size}</td>
                  <td className="p-3.5 font-mono text-slate-600">{doc.total_pages} Pages</td>
                  <td className="p-3.5">
                    <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                      <span className="w-2 h-2 rounded-full bg-emerald-600" />
                      <span>{(doc.confidence * 100).toFixed(0)}%</span>
                    </span>
                  </td>
                  <td className="p-3.5 font-mono text-slate-500">{doc.created_at}</td>
                  <td className="p-3.5 text-right">
                    <Link
                      href="/"
                      className="text-teal-700 hover:text-teal-900 font-semibold flex items-center justify-end space-x-1"
                    >
                      <span>View Results</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </main>
    </div>
  );
}
