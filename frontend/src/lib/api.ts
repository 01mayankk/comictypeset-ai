/**
 * API Client & Type Definitions for ComicTypeset AI.
 * Synchronized with backend/app/schemas.py.
 */

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BubbleItem {
  id: number;
  order: number;
  bbox: BoundingBox;
  raw_text: string;
  translated_text: string;
  confidence: number;
  polygon?: number[][];
}

export interface TranslationResponse {
  success: boolean;
  detector_mode: string;
  reading_direction: string;
  source_lang: string;
  target_lang: string;
  total_bubbles_detected: number;
  bubbles: BubbleItem[];
  final_image_base64: string;
  mask_overlay_base64: string;
  timings_ms: Record<string, number>;
  warnings: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
  detector_mode: string;
  model_loaded: boolean;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:7860";

/**
 * Checks backend API health.
 */
export async function checkBackendHealth(): Promise<HealthResponse> {
  const resp = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
  if (!resp.ok) {
    throw new Error(`Backend health check failed: HTTP ${resp.status}`);
  }
  return resp.json();
}

/**
 * Submits a comic page file for segmentation, OCR, translation, and typesetting.
 */
export async function translatePage(
  file: File,
  sourceLang: string = "auto",
  targetLang: string = "en",
  readingDirection: string = "ltr"
): Promise<TranslationResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("source_lang", sourceLang);
  formData.append("target_lang", targetLang);
  formData.append("reading_direction", readingDirection);

  const resp = await fetch(`${API_BASE_URL}/api/v1/translate-page`, {
    method: "POST",
    body: formData,
  });

  if (!resp.ok) {
    let errMsg = `Server error (HTTP ${resp.status})`;
    try {
      const errJson = await resp.json();
      if (errJson.detail) errMsg = errJson.detail;
    } catch {
      // Keep default error message
    }
    throw new Error(errMsg);
  }

  return resp.json();
}

/**
 * Generates an in-browser synthetic comic page on HTML5 Canvas.
 * Allows instant testing without needing external comic scans.
 */
export async function generateSyntheticComicPage(): Promise<File> {
  return new Promise((resolve, reject) => {
    try {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 512;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        throw new Error("Could not acquire 2D rendering context");
      }

      // Background
      ctx.fillStyle = "#f8f8f6";
      ctx.fillRect(0, 0, 512, 512);

      // Draw Top Panel
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "#000000";
      ctx.lineWidth = 3;
      ctx.fillRect(16, 16, 480, 230);
      ctx.strokeRect(16, 16, 480, 230);

      // Subtle Halftone Dots in top panel
      ctx.fillStyle = "#e2e8f0";
      for (let x = 24; x < 490; x += 12) {
        for (let y = 24; y < 240; y += 12) {
          ctx.beginPath();
          ctx.arc(x, y, 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Draw Bottom Panel
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(16, 260, 480, 236);
      ctx.strokeRect(16, 260, 480, 236);

      // Character Silhouette in bottom panel
      ctx.fillStyle = "#334155";
      ctx.beginPath();
      ctx.arc(120, 410, 30, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillRect(80, 440, 80, 50);

      // Speech Bubble 1 in Top Panel
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "#000000";
      ctx.lineWidth = 3;
      // Tail
      ctx.beginPath();
      ctx.moveTo(80, 160);
      ctx.lineTo(60, 200);
      ctx.lineTo(110, 165);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Bubble Ellipse
      ctx.beginPath();
      ctx.ellipse(140, 110, 85, 55, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Text inside Bubble 1
      ctx.fillStyle = "#000000";
      ctx.font = "bold 13px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("HELLO THERE!", 140, 100);
      ctx.fillText("WHAT IS THIS?", 140, 120);

      // Speech Bubble 2 in Bottom Panel
      ctx.fillStyle = "#ffffff";
      ctx.beginPath();
      ctx.moveTo(350, 370);
      ctx.lineTo(390, 410);
      ctx.lineTo(375, 370);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      ctx.beginPath();
      ctx.ellipse(320, 325, 95, 50, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#000000";
      ctx.fillText("THIS IS COMICTYPESET AI!", 320, 315);
      ctx.fillText("AUTOMATED TRANSLATION!", 320, 335);

      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error("Canvas export failed"));
          return;
        }
        const file = new File([blob], "synthetic_sample_comic.png", {
          type: "image/png",
        });
        resolve(file);
      }, "image/png");
    } catch (err) {
      reject(err);
    }
  });
}
