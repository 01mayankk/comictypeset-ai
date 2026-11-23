"use client";

import React, { useEffect, useState } from "react";
import { UploadZone } from "@/components/UploadZone";
import { ComparisonViewer } from "@/components/ComparisonViewer";
import { BubbleEditor } from "@/components/BubbleEditor";
import { PipelineStatus } from "@/components/PipelineStatus";
import {
  BubbleItem,
  TranslationResponse,
  checkBackendHealth,
  translatePage,
} from "@/lib/api";
import { AlertCircle, CheckCircle } from "lucide-react";

export default function ComicTypesetStudio() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isSyntheticDemo, setIsSyntheticDemo] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [activeStage, setActiveStage] = useState<
    "segmentation" | "ocr" | "translation" | "typesetting" | "complete"
  >("segmentation");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [pipelineResult, setPipelineResult] = useState<TranslationResponse | null>(null);

  // Check backend health on mount
  useEffect(() => {
    checkBackendHealth()
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  // Cleanup object URLs to avoid memory leaks
  const handleFileSelect = (file: File, isSynthetic: boolean) => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    const url = URL.createObjectURL(file);
    setSelectedFile(file);
    setPreviewUrl(url);
    setIsSyntheticDemo(isSynthetic);
    setPipelineResult(null);
    setErrorMsg(null);
  };

  const handleSubmit = async (
    sourceLang: string,
    targetLang: string,
    readingDirection: string
  ) => {
    if (!selectedFile) return;

    setIsLoading(true);
    setErrorMsg(null);
    setActiveStage("segmentation");

    try {
      // Simulate visual stage progression
      const stageTimer1 = setTimeout(() => setActiveStage("ocr"), 300);
      const stageTimer2 = setTimeout(() => setActiveStage("translation"), 600);
      const stageTimer3 = setTimeout(() => setActiveStage("typesetting"), 900);

      const result = await translatePage(
        selectedFile,
        sourceLang,
        targetLang,
        readingDirection
      );

      clearTimeout(stageTimer1);
      clearTimeout(stageTimer2);
      clearTimeout(stageTimer3);

      setActiveStage("complete");
      setPipelineResult(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Pipeline request failed";
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // Client-side re-render on edited bubbles
  const handleReRender = (updatedBubbles: BubbleItem[]) => {
    if (!pipelineResult) return;

    // Redraw text onto the canvas from the final image
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.src = pipelineResult.final_image_base64;
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      // Draw base
      ctx.drawImage(img, 0, 0);

      // Inpaint/overlay updated text boxes
      for (const b of updatedBubbles) {
        const text = b.translated_text || "";
        if (!text.trim()) continue;

        const bx = b.bbox.x + b.bbox.width * 0.12;
        const by = b.bbox.y + b.bbox.height * 0.15;
        const bw = b.bbox.width * 0.76;
        const bh = b.bbox.height * 0.70;

        // White patch fill over previous lettering
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(bx, by, bw, bh);

        // Render updated centered text
        ctx.fillStyle = "#000000";
        ctx.font = "bold 13px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(text, bx + bw / 2, by + bh / 2, bw);
      }

      const updatedBase64 = canvas.toDataURL("image/png");
      setPipelineResult({
        ...pipelineResult,
        bubbles: updatedBubbles,
        final_image_base64: updatedBase64,
      });
    };
  };

  return (
    <div className="space-y-6">
      {/* Studio Header & Status Pill */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
            ComicTypeset AI Studio
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Automated speech bubble localization, multilingual OCR, deep translation, and seamless re-lettering.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border ${
              backendStatus === "online"
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : backendStatus === "offline"
                ? "bg-rose-50 text-rose-700 border-rose-200"
                : "bg-slate-50 text-slate-600 border-slate-200"
            }`}
          >
            {backendStatus === "online" ? (
              <>
                <CheckCircle className="w-3.5 h-3.5" />
                <span>Backend Online (Port 7860)</span>
              </>
            ) : backendStatus === "offline" ? (
              <>
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Backend Offline</span>
              </>
            ) : (
              <span>Checking API...</span>
            )}
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 text-xs text-rose-800 flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Execution Error: </span>
            {errorMsg}
          </div>
        </div>
      )}

      {/* 2-Column Responsive Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Upload & Pipeline Status */}
        <div className="lg:col-span-5 space-y-6">
          <UploadZone
            onFileSelect={handleFileSelect}
            onSubmit={handleSubmit}
            isLoading={isLoading}
            selectedFile={selectedFile}
            isSyntheticDemo={isSyntheticDemo}
          />

          <PipelineStatus
            isLoading={isLoading}
            activeStage={activeStage}
            detectorMode={pipelineResult?.detector_mode}
            timings={pipelineResult?.timings_ms}
            warnings={pipelineResult?.warnings}
          />
        </div>

        {/* Right Column: Comparison Viewer & Bubble Editor */}
        <div className="lg:col-span-7 space-y-6">
          <ComparisonViewer
            originalUrl={previewUrl}
            maskOverlayBase64={pipelineResult?.mask_overlay_base64 || null}
            finalImageBase64={pipelineResult?.final_image_base64 || null}
            totalBubbles={pipelineResult?.total_bubbles_detected || 0}
          />

          {pipelineResult && (
            <BubbleEditor
              bubbles={pipelineResult.bubbles}
              onReRender={handleReRender}
              isLoading={isLoading}
            />
          )}
        </div>
      </div>
    </div>
  );
}
