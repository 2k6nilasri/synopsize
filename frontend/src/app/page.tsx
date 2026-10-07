"use client";

import React, { useState } from "react";
import Navbar from "@/components/Navbar";
import UploadZone from "@/components/UploadZone";
import ValidationReportComponent from "@/components/ValidationReport";
import StageStepper from "@/components/StageStepper";
import PageViewer from "@/components/PageViewer";
import OutputTabs from "@/components/OutputTabs";
import InlineCorrectionModal from "@/components/InlineCorrectionModal";

import { ValidationReport, JobResult, PipelineStage, DocumentBlock } from "@/types";
import { validateFile, startParseJob, getJobResult, deleteJobData } from "@/lib/api";

const DEFAULT_STAGES: PipelineStage[] = [
  { id: 1, name: "Input", description: "Validation & security scan", status: "pending" },
  { id: 2, name: "Pre-processing", description: "Deskew & noise removal", status: "pending" },
  { id: 3, name: "Agent routing", description: "Extractor routing", status: "pending" },
  { id: 4, name: "Extract and assemble", description: "Region & reading order parsing", status: "pending" },
  { id: 5, name: "Enrich and validate", description: "Confidence scoring", status: "pending" },
  { id: 6, name: "Structured output", description: "Generating MD, JSON, OCR Text", status: "pending" },
  { id: 7, name: "Semantic indexing", description: "Chunking & vector embedding index", status: "pending" },
];

export default function DashboardPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  
  const [isProcessing, setIsProcessing] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [stages, setStages] = useState<PipelineStage[]>(DEFAULT_STAGES);
  const [currentStageNum, setCurrentStageNum] = useState<number>(1);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [editingBlock, setEditingBlock] = useState<DocumentBlock | null>(null);
  const [showLowConfidenceOnly, setShowLowConfidenceOnly] = useState(false);

  // File Select Handler: Validates live first
  const handleFileSelect = async (file: File) => {
    setSelectedFile(file);
    setIsValidating(true);
    setValidationReport(null);
    setJobResult(null);
    setJobId(null);
    setIsProcessing(false);
    setStages(DEFAULT_STAGES);

    try {
      // Step 2: Validate file live
      const report = await validateFile(file);
      setValidationReport(report);
      setIsValidating(false);

      if (!report.is_valid) {
        return; // Stop pipeline if bad file!
      }
    } catch (err: any) {
      setIsValidating(false);
      alert(err.message || "Failed to validate file.");
    }
  };

  // Launch the 7-stage Document Processing Pipeline
  const handleStartProcessing = async () => {
    if (!selectedFile || isProcessing) return;
    setIsProcessing(true);
    setJobResult(null);
    setStages(DEFAULT_STAGES);

    try {
      // Step 3: Start parsing job & SSE progress stream
      const jobRes = await startParseJob(selectedFile);
      const newJobId = jobRes.job_id;
      setJobId(newJobId);

      // Listen to SSE stage events
      const eventSource = new EventSource(`http://127.0.0.1:8000/api/jobs/${newJobId}/events`);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.stage_num) {
            setCurrentStageNum(data.stage_num);
            setStages((prev) =>
              prev.map((stg) => {
                if (stg.id < data.stage_num) return { ...stg, status: "done" };
                if (stg.id === data.stage_num)
                  return {
                    ...stg,
                    status: data.status,
                    summary: data.summary,
                    description: data.detail,
                    timing_ms: data.timing_ms
                  };
                return stg;
              })
            );
          }

          if (data.done) {
            eventSource.close();
            setIsProcessing(false);
            // Fetch final result
            getJobResult(newJobId).then((res) => {
              setJobResult(res);
              if (res.stages) {
                setStages(res.stages);
              } else {
                setStages((prev) => prev.map((s) => ({ ...s, status: "done" })));
              }
            });
          }
        } catch (err) {
          console.error("SSE parse error", err);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        // Fallback polling fetch
        setTimeout(() => {
          getJobResult(newJobId).then((res) => {
            setJobResult(res);
            setIsProcessing(false);
            if (res.stages) setStages(res.stages);
          });
        }, 1500);
      };

    } catch (err: any) {
      setIsProcessing(false);
      alert(err.message || "Failed to process file.");
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setValidationReport(null);
    setJobId(null);
    setJobResult(null);
    setStages(DEFAULT_STAGES);
    setCurrentPageIndex(0);
    setSelectedBlockId(null);
  };

  const handleDeleteData = async () => {
    if (jobId) {
      await deleteJobData(jobId);
    }
    handleReset();
  };

  const handleCorrectionSuccess = (blockId: string, newText: string) => {
    if (!jobResult) return;
    const updatedPages = jobResult.pages.map((p) => ({
      ...p,
      blocks: p.blocks.map((b) =>
        b.id === blockId ? { ...b, content: newText, confidence: 0.99, confidence_level: "green" as const } : b
      )
    }));
    setJobResult({ ...jobResult, pages: updatedPages });
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans text-slate-900">
      <Navbar
        overallConfidence={jobResult?.overall_confidence}
        overallConfidenceLevel={jobResult?.overall_confidence_level}
        onDeleteData={jobId ? handleDeleteData : undefined}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        
        {/* Main 3-Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Left Column: Pipeline Stages Stepper (Visible throughout) */}
          <div className="lg:col-span-3 space-y-4">
            <StageStepper stages={stages} currentStageNum={currentStageNum} />
          </div>

          {/* Center & Right Column: Upload, Validation, Results */}
          <div className="lg:col-span-9 space-y-6">
            
            {/* Step 1: Upload */}
            <UploadZone
              onFileSelect={handleFileSelect}
              isLoading={isValidating}
              selectedFile={selectedFile}
              onReset={handleReset}
            />

            {/* Step 2: Live Validation Report */}
            {(isValidating || validationReport) && (
              <ValidationReportComponent
                report={validationReport}
                isValidating={isValidating}
                onStartProcessing={handleStartProcessing}
                isProcessing={isProcessing}
              />
            )}

            {/* Step 4 & 5: Parsed Output Pages & Tabs */}
            {jobResult && (
              <>
                <PageViewer
                  pages={jobResult.pages}
                  currentPageIndex={currentPageIndex}
                  onSelectPage={setCurrentPageIndex}
                  selectedBlockId={selectedBlockId}
                  onSelectBlock={setSelectedBlockId}
                  onEditBlock={setEditingBlock}
                  showLowConfidenceOnly={showLowConfidenceOnly}
                />

                <OutputTabs
                  jobResult={jobResult}
                  showLowConfidenceOnly={showLowConfidenceOnly}
                  onToggleFilter={setShowLowConfidenceOnly}
                  onEditBlock={setEditingBlock}
                  onSelectChunkBlocks={(bIds) => {
                    if (bIds && bIds.length > 0) {
                      setSelectedBlockId(bIds[0]);
                    }
                  }}
                />
              </>
            )}

          </div>

        </div>

      </main>

      {/* Hidden Inline Correction Modal for Low-Confidence Block Edits */}
      <InlineCorrectionModal
        block={editingBlock}
        onClose={() => setEditingBlock(null)}
        onSaveSuccess={handleCorrectionSuccess}
      />
    </div>
  );
}
