"use client";

import React from "react";
import { CheckCircle2, Clock, AlertTriangle, Cpu } from "lucide-react";

interface PipelineStatusProps {
  isLoading: boolean;
  activeStage?: "segmentation" | "ocr" | "translation" | "typesetting" | "complete";
  detectorMode?: string;
  timings?: Record<string, number>;
  warnings?: string[];
}

export function PipelineStatus({
  isLoading,
  activeStage,
  detectorMode,
  timings,
  warnings,
}: PipelineStatusProps) {
  const stages = [
    { key: "segmentation", label: "Segmentation", timingKey: "segmentation" },
    { key: "ocr", label: "OCR Extraction", timingKey: "ocr" },
    { key: "translation", label: "Translation", timingKey: "translation" },
    { key: "typesetting", label: "Inpaint & Typeset", timingKey: "typesetting" },
  ];

  const isUnet = detectorMode === "unet";

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
          <Clock className="w-4 h-4 text-indigo-600" />
          Pipeline Execution
        </h3>

        {/* Detector Badge */}
        {detectorMode && (
          <div className="flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border">
            <Cpu className="w-3.5 h-3.5" />
            <span>Detector:</span>
            {isUnet ? (
              <span className="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                MobileNetV2-UNet
              </span>
            ) : (
              <span className="text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                OpenCV Fallback
              </span>
            )}
          </div>
        )}
      </div>

      {/* Stage Progression Steps */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {stages.map((st, idx) => {
          const isCurrent = isLoading && activeStage === st.key;
          const isDone = !isLoading && timings && timings[st.timingKey] !== undefined;
          const stageTime = timings ? timings[st.timingKey] : null;

          return (
            <div
              key={st.key}
              className={`p-3 rounded-lg border transition-colors ${
                isCurrent
                  ? "border-indigo-500 bg-indigo-50/50"
                  : isDone
                  ? "border-emerald-200 bg-emerald-50/30"
                  : "border-slate-100 bg-slate-50"
              }`}
            >
              <div className="flex items-center justify-between text-xs font-medium text-slate-500 mb-1">
                <span>Stage {idx + 1}</span>
                {isDone && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
              </div>
              <div className="text-xs font-semibold text-slate-800">{st.label}</div>
              {stageTime !== null && stageTime !== undefined && (
                <div className="text-[11px] text-slate-500 mt-1">{stageTime} ms</div>
              )}
            </div>
          );
        })}
      </div>

      {/* Total Latency Banner */}
      {timings && timings.total !== undefined && (
        <div className="flex justify-between items-center text-xs bg-slate-50 px-3 py-2 rounded text-slate-600 font-medium">
          <span>Total Pipeline Latency:</span>
          <span className="font-bold text-slate-800">{timings.total} ms</span>
        </div>
      )}

      {/* Warnings */}
      {warnings && warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 flex gap-2 items-start">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold">Pipeline Warnings:</span>
            {warnings.map((w, i) => (
              <div key={i}>• {w}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
