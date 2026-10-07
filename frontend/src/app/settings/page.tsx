"use client";

import React, { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import { Settings, Shield, Sliders, Check, Lock, EyeOff } from "lucide-react";

export default function SettingsPage() {
  const [consentEnabled, setConsentEnabled] = useState(true);
  const [piiRedaction, setPiiRedaction] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    fetch("http://127.0.0.1:8000/api/settings/consent")
      .then((res) => res.json())
      .then((data) => {
        if (data.consent_enabled !== undefined) {
          setConsentEnabled(data.consent_enabled);
        }
      })
      .catch(() => {});

    fetch("http://127.0.0.1:8000/api/settings/pii")
      .then((res) => res.json())
      .then((data) => {
        if (data.pii_redaction !== undefined) {
          setPiiRedaction(data.pii_redaction);
        }
      })
      .catch(() => {});
  }, []);

  const handleSaveSettings = async () => {
    const consentData = new FormData();
    consentData.append("enabled", consentEnabled.toString());
    await fetch("http://127.0.0.1:8000/api/settings/consent", {
      method: "POST",
      body: consentData,
    });

    const piiData = new FormData();
    piiData.append("enabled", piiRedaction.toString());
    await fetch("http://127.0.0.1:8000/api/settings/pii", {
      method: "POST",
      body: piiData,
    });

    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans text-slate-900">
      <Navbar />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            System & Privacy Settings
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Configure correction consent, PII detection filters, and confidence threshold ranges.
          </p>
        </div>

        {/* Setting Card 1: Hidden Correction Logging Consent */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
            <Shield className="w-5 h-5 text-teal-700" />
            <h3 className="text-base font-bold text-slate-900">
              Low-Confidence Correction Recording Consent
            </h3>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">
            When low-confidence blocks are corrected inline, SYNOPSIZE records the before/after text, page number, and bounding box region. This data is used solely for isolated model fine-tuning and never includes unedited document content.
          </p>

          <label className="flex items-center space-x-3 text-xs font-semibold text-slate-800 cursor-pointer bg-slate-50 p-3.5 rounded border border-slate-200">
            <input
              type="checkbox"
              checked={consentEnabled}
              onChange={(e) => setConsentEnabled(e.target.checked)}
              className="rounded border-slate-300 text-teal-600 focus:ring-teal-500 w-4 h-4"
            />
            <span>Enable silent recording of user-edited low-confidence blocks (Default: Enabled)</span>
          </label>
        </div>

        {/* Setting Card 2: PII Detection & Redaction Toggle */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
            <EyeOff className="w-5 h-5 text-teal-700" />
            <h3 className="text-base font-bold text-slate-900">
              PII Detection & Auto-Redaction Toggle
            </h3>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">
            Automatically scans extracted document text for Personally Identifiable Information (SSN, Email addresses, Credit Card numbers) and masks or redacts them in exported Markdown and JSON.
          </p>

          <label className="flex items-center space-x-3 text-xs font-semibold text-slate-800 cursor-pointer bg-slate-50 p-3.5 rounded border border-slate-200">
            <input
              type="checkbox"
              checked={piiRedaction}
              onChange={(e) => setPiiRedaction(e.target.checked)}
              className="rounded border-slate-300 text-teal-600 focus:ring-teal-500 w-4 h-4"
            />
            <span>Enable PII detection and automatic text masking in output</span>
          </label>
        </div>

        {/* Setting Card 3: Confidence Indicators Config View */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
            <Sliders className="w-5 h-5 text-teal-700" />
            <h3 className="text-base font-bold text-slate-900">
              Confidence Indicator Threshold Rules
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-4 rounded bg-rose-50 border border-rose-200 text-rose-900">
              <span className="font-bold flex items-center gap-1.5 mb-1">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-600" />
                Red Indicator (Low)
              </span>
              <p className="font-mono font-semibold">Score &lt; 0.70 (Below 70%)</p>
              <p className="text-[11px] text-rose-700 mt-1">Requires reviewer inspection & inline edit.</p>
            </div>

            <div className="p-4 rounded bg-amber-50 border border-amber-200 text-amber-900">
              <span className="font-bold flex items-center gap-1.5 mb-1">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                Yellow Indicator (Average)
              </span>
              <p className="font-mono font-semibold">0.70 ≤ Score &lt; 0.90</p>
              <p className="text-[11px] text-amber-700 mt-1">Acceptable quality; review recommended.</p>
            </div>

            <div className="p-4 rounded bg-emerald-50 border border-emerald-200 text-emerald-900">
              <span className="font-bold flex items-center gap-1.5 mb-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
                Green Indicator (High)
              </span>
              <p className="font-mono font-semibold">Score ≥ 0.90 (90%+)</p>
              <p className="text-[11px] text-emerald-700 mt-1">High fidelity extraction verified.</p>
            </div>
          </div>
        </div>

        {/* Save Settings Button */}
        <div className="flex items-center justify-end space-x-3">
          {savedSuccess && (
            <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1">
              <Check className="w-4 h-4" />
              Settings saved successfully!
            </span>
          )}

          <button
            onClick={handleSaveSettings}
            className="px-5 py-2.5 rounded bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold shadow-sm transition"
          >
            Save Preferences
          </button>
        </div>

      </main>
    </div>
  );
}
