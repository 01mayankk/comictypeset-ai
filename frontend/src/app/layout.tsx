import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ComicTypeset AI — Speech Bubble Segmentation, Translation & Re-Lettering",
  description: "End-to-end computer-vision and NLP studio for automated comic and manga translation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen flex flex-col bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white shadow-sm sticky top-0 z-30">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="text-2xl">💬</span>
              <div>
                <span className="font-extrabold text-lg text-indigo-600 tracking-tight">ComicTypeset</span>
                <span className="ml-1 text-xs font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">AI</span>
              </div>
            </div>
            <div className="text-xs text-slate-500 font-medium hidden sm:block">
              Speech Bubble Segmentation • OCR • Translation • Inpainting • Re-Lettering
            </div>
          </div>
        </header>
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-500">
          ComicTypeset AI Studio &copy; 2026. Automated Speech Bubble Segmentation, Translation & Re-Lettering.
        </footer>
      </body>
    </html>
  );
}
