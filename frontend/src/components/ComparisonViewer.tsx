"use client";

import React, { useState } from "react";
import { Download, Columns, Layers, Eye, Image as ImageIcon } from "lucide-react";

interface ComparisonViewerProps {
  originalUrl: string | null;
  maskOverlayBase64: string | null;
  finalImageBase64: string | null;
  totalBubbles: number;
}

export function ComparisonViewer({
  originalUrl,
  maskOverlayBase64,
  finalImageBase64,
  totalBubbles,
}: ComparisonViewerProps) {
  const [viewMode, setViewMode] = useState<"split" | "final" | "mask" | "original">("split");

  const handleDownload = () => {
    if (!finalImageBase64) return;
    const a = document.createElement("a");
    a.href = finalImageBase64;
    a.download = `comictypeset_translated_page_${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
      {/* Viewer Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-bold text-slate-800">2. Typeset Comparison</h2>
          {totalBubbles > 0 && (
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
              {totalBubbles} bubbles
            </span>
          )}
        </div>

        {/* View Mode Tabs & Download */}
        <div className="flex items-center gap-2">
          <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-50 text-xs">
            <button
              type="button"
              onClick={() => setViewMode("split")}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition ${
                viewMode === "split" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Columns className="w-3.5 h-3.5" />
              Split
            </button>
            <button
              type="button"
              onClick={() => setViewMode("final")}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition ${
                viewMode === "final" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Typeset
            </button>
            <button
              type="button"
              onClick={() => setViewMode("mask")}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition ${
                viewMode === "mask" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Mask
            </button>
            <button
              type="button"
              onClick={() => setViewMode("original")}
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition ${
                viewMode === "original" ? "bg-white text-indigo-600 shadow-sm" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <ImageIcon className="w-3.5 h-3.5" />
              Original
            </button>
          </div>

          {finalImageBase64 && (
            <button
              type="button"
              onClick={handleDownload}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg shadow-sm transition"
            >
              <Download className="w-3.5 h-3.5" />
              Download PNG
            </button>
          )}
        </div>
      </div>

      {/* Image Display Area */}
      <div className="bg-slate-100/70 border border-slate-200 rounded-xl p-4 min-h-[460px] flex items-center justify-center overflow-auto">
        {!originalUrl && (
          <div className="text-center text-slate-400 text-sm">
            <ImageIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
            Upload a comic page to preview and compare results
          </div>
        )}

        {/* Split View */}
        {originalUrl && viewMode === "split" && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
            <div className="flex flex-col items-center">
              <span className="text-xs font-semibold text-slate-500 mb-1.5">Original Page</span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={originalUrl}
                alt="Original comic page"
                className="max-h-[500px] w-auto object-contain rounded-lg shadow border border-slate-200 bg-white"
              />
            </div>
            <div className="flex flex-col items-center">
              <span className="text-xs font-semibold text-slate-500 mb-1.5">
                {finalImageBase64 ? "Final Typeset Result" : "Processed Output (Pending)"}
              </span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={finalImageBase64 || originalUrl}
                alt="Translated and typeset result"
                className={`max-h-[500px] w-auto object-contain rounded-lg shadow border border-slate-200 bg-white ${
                  !finalImageBase64 ? "opacity-40" : ""
                }`}
              />
            </div>
          </div>
        )}

        {/* Final Typeset Single View */}
        {viewMode === "final" && (
          <div className="flex flex-col items-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={finalImageBase64 || originalUrl || ""}
              alt="Typeset page"
              className="max-h-[550px] w-auto object-contain rounded-lg shadow-lg border border-slate-200 bg-white"
            />
          </div>
        )}

        {/* Bubble Mask Overlay View */}
        {viewMode === "mask" && (
          <div className="flex flex-col items-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={maskOverlayBase64 || originalUrl || ""}
              alt="Speech bubble mask overlay"
              className="max-h-[550px] w-auto object-contain rounded-lg shadow border border-slate-200 bg-white"
            />
          </div>
        )}

        {/* Original Single View */}
        {viewMode === "original" && originalUrl && (
          <div className="flex flex-col items-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={originalUrl}
              alt="Original page"
              className="max-h-[550px] w-auto object-contain rounded-lg shadow border border-slate-200 bg-white"
            />
          </div>
        )}
      </div>
    </div>
  );
}
