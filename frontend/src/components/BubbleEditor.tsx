"use client";

import React, { useState } from "react";
import { BubbleItem } from "@/lib/api";
import { Edit3, RefreshCw, Check } from "lucide-react";

interface BubbleEditorProps {
  bubbles: BubbleItem[];
  onReRender: (updatedBubbles: BubbleItem[]) => void;
  isLoading: boolean;
}

export function BubbleEditor({ bubbles, onReRender, isLoading }: BubbleEditorProps) {
  const [editedBubbles, setEditedBubbles] = useState<BubbleItem[]>(bubbles);
  const [hasChanges, setHasChanges] = useState(false);

  // Sync state if bubbles prop changes
  React.useEffect(() => {
    setEditedBubbles(bubbles);
    setHasChanges(false);
  }, [bubbles]);

  const handleTextChange = (id: number, newTranslatedText: string) => {
    const next = editedBubbles.map((b) =>
      b.id === id ? { ...b, translated_text: newTranslatedText } : b
    );
    setEditedBubbles(next);
    setHasChanges(true);
  };

  const handleApply = () => {
    onReRender(editedBubbles);
    setHasChanges(false);
  };

  if (!bubbles || bubbles.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Edit3 className="w-4 h-4 text-indigo-600" />
          <h2 className="text-base font-bold text-slate-800">3. Edit Speech Bubbles & OCR</h2>
        </div>
        <button
          type="button"
          onClick={handleApply}
          disabled={!hasChanges || isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          Re-Render Typeset Page
        </button>
      </div>

      <p className="text-xs text-slate-500">
        Review OCR extractions and refine translated text. Click <strong>Re-Render</strong> to update the final typeset image.
      </p>

      {/* Bubble List */}
      <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
        {editedBubbles.map((bubble) => (
          <div
            key={bubble.id}
            className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2 hover:border-slate-300 transition"
          >
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
                Bubble #{bubble.order}
              </span>
              <div className="text-[11px] text-slate-500 flex items-center gap-2">
                <span>
                  BBox: [{bubble.bbox.x}, {bubble.bbox.y}, {bubble.bbox.width}x{bubble.bbox.height}]
                </span>
                {bubble.confidence !== undefined && (
                  <span className="bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded">
                    {(bubble.confidence * 100).toFixed(0)}% conf
                  </span>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
              <div>
                <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                  Extracted OCR Text
                </label>
                <div className="bg-white p-2 rounded border border-slate-200 text-slate-700 font-mono text-[11px] min-h-[38px] select-all">
                  {bubble.raw_text || "(No text detected)"}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-500 mb-0.5">
                  Translated Text (Editable)
                </label>
                <textarea
                  rows={2}
                  value={bubble.translated_text}
                  onChange={(e) => handleTextChange(bubble.id, e.target.value)}
                  className="w-full p-2 bg-white rounded border border-slate-300 text-slate-800 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Enter translated text..."
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
