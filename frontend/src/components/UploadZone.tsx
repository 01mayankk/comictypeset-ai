"use client";

import React, { useRef, useState } from "react";
import { Upload, Sparkles, FileImage, ArrowRight } from "lucide-react";
import { generateSyntheticComicPage } from "@/lib/api";

interface UploadZoneProps {
  onFileSelect: (file: File, isSynthetic: boolean) => void;
  onSubmit: (sourceLang: string, targetLang: string, readingDirection: string) => void;
  isLoading: boolean;
  selectedFile: File | null;
  isSyntheticDemo: boolean;
}

export function UploadZone({
  onFileSelect,
  onSubmit,
  isLoading,
  selectedFile,
  isSyntheticDemo,
}: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [sourceLang, setSourceLang] = useState("auto");
  const [targetLang, setTargetLang] = useState("en");
  const [readingDirection, setReadingDirection] = useState("ltr");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith("image/")) {
        onFileSelect(file, false);
      }
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileSelect(e.target.files[0], false);
    }
  };

  const handleLoadSample = async () => {
    try {
      const sampleFile = await generateSyntheticComicPage();
      onFileSelect(sampleFile, true);
    } catch (err) {
      console.error("Failed to generate sample page:", err);
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
      <div className="border-b border-slate-100 pb-3 flex justify-between items-center">
        <h2 className="text-base font-bold text-slate-800">1. Upload Comic Page</h2>
        <button
          type="button"
          onClick={handleLoadSample}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition disabled:opacity-50"
        >
          <Sparkles className="w-3.5 h-3.5" />
          Load Sample Page (Synthetic Demo)
        </button>
      </div>

      {/* Drag & Drop Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${
          isDragOver
            ? "border-indigo-500 bg-indigo-50/50"
            : "border-slate-300 hover:border-indigo-400 bg-slate-50/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={handleFileInput}
          disabled={isLoading}
        />
        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="p-3 bg-white rounded-full shadow-sm border border-slate-200 text-indigo-600">
            <Upload className="w-6 h-6" />
          </div>
          <div>
            <span className="font-semibold text-slate-800">Click to upload</span> or drag and drop
            <p className="text-xs text-slate-500 mt-1">PNG, JPEG, or WebP scans up to 15 MB</p>
          </div>
        </div>
      </div>

      {/* Selected File Badge */}
      {selectedFile && (
        <div className="flex items-center justify-between p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs">
          <div className="flex items-center gap-2 text-slate-700 font-medium truncate">
            <FileImage className="w-4 h-4 text-indigo-600 shrink-0" />
            <span className="truncate">{selectedFile.name}</span>
            <span className="text-slate-400">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
          </div>
          {isSyntheticDemo && (
            <span className="shrink-0 bg-amber-100 text-amber-800 text-[10px] font-semibold px-2 py-0.5 rounded border border-amber-300">
              Synthetic Demo Content
            </span>
          )}
        </div>
      )}

      {/* Controls: Source/Target Language and Reading Direction */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Source Language</label>
          <select
            value={sourceLang}
            onChange={(e) => setSourceLang(e.target.value)}
            disabled={isLoading}
            className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="auto">Auto-Detect</option>
            <option value="ja">Japanese (日本語)</option>
            <option value="en">English</option>
            <option value="ko">Korean (한국어)</option>
            <option value="zh-CN">Chinese (Simplified)</option>
            <option value="es">Spanish</option>
            <option value="fr">French</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Target Language</label>
          <select
            value={targetLang}
            onChange={(e) => setTargetLang(e.target.value)}
            disabled={isLoading}
            className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="en">English</option>
            <option value="es">Spanish (Español)</option>
            <option value="fr">French (Français)</option>
            <option value="de">German (Deutsch)</option>
            <option value="ja">Japanese (日本語)</option>
            <option value="ko">Korean (한국어)</option>
            <option value="zh-CN">Chinese (Simplified)</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Reading Order</label>
          <select
            value={readingDirection}
            onChange={(e) => setReadingDirection(e.target.value)}
            disabled={isLoading}
            className="w-full text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="ltr">Left-to-Right (Western / Manhwa)</option>
            <option value="rtl">Right-to-Left (Japanese Manga)</option>
          </select>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="button"
        onClick={() => onSubmit(sourceLang, targetLang, readingDirection)}
        disabled={isLoading || !selectedFile}
        className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm rounded-lg shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            <span>Processing Comic Pipeline...</span>
          </div>
        ) : (
          <>
            <span>Translate & Re-Letter Page</span>
            <ArrowRight className="w-4 h-4" />
          </>
        )}
      </button>
    </div>
  );
}
