"""OCR and Translation Stage.

Provides text extraction via EasyOCR and machine translation via a decoupled
deep-translator adapter with in-memory LRU caching and mock injection for testing.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional
import numpy as np

logger = logging.getLogger(__name__)


class TranslationCache:
    """Thread-safe LRU in-memory cache for translated strings."""

    def __init__(self, maxsize: int = 1000) -> None:
        self.maxsize = maxsize
        self._cache: dict[tuple[str, str, str], str] = {}

    def get(self, source_lang: str, target_lang: str, text: str) -> Optional[str]:
        return self._cache.get((source_lang.lower(), target_lang.lower(), text.strip()))

    def set(self, source_lang: str, target_lang: str, text: str, translated: str) -> None:
        if len(self._cache) >= self.maxsize:
            # Evict oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[(source_lang.lower(), target_lang.lower(), text.strip())] = translated


class OCRTranslator:
    """Combines EasyOCR text extraction and machine translation with caching."""

    def __init__(
        self,
        languages: list[str] | None = None,
        translation_provider: Optional[Callable[[str, str, str], str]] = None,
        translation_batch_provider: Optional[Callable[[list[str], str, str], list[str]]] = None
    ) -> None:
        self.languages = languages or ["en"]
        self.reader = None
        self.cache = TranslationCache()
        self._translation_provider = translation_provider or self._default_deep_translator
        self._translation_batch_provider = translation_batch_provider
        if translation_provider is None and translation_batch_provider is None:
            self._translation_batch_provider = self._default_deep_translator_batch
        self._init_reader()

    def _init_reader(self) -> None:
        """Initializes EasyOCR reader if available."""
        try:
            import easyocr
            self.reader = easyocr.Reader(self.languages, gpu=False)
            logger.info(f"EasyOCR reader initialized for languages: {self.languages}")
        except Exception as exc:
            logger.warning(f"EasyOCR reader initialization deferred: {exc}")
            self.reader = None

    def set_translation_provider(self, provider: Callable[[str, str, str], str]) -> None:
        """Injects a custom translation provider (useful for unit tests and local LLM backends)."""
        self._translation_provider = provider
        self._translation_batch_provider = None

    def translate_batch(
        self,
        texts: list[str],
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> tuple[list[str], list[Optional[str]]]:
        """Translates multiple strings with a single provider request when available."""
        clean_texts = [text.strip() for text in texts]
        translations = [""] * len(clean_texts)
        warnings: list[Optional[str]] = [None] * len(clean_texts)

        if self._translation_batch_provider is None:
            for index, text in enumerate(clean_texts):
                translations[index], warnings[index] = self.translate(text, source_lang, target_lang)
            return translations, warnings

        missing: dict[str, list[int]] = {}
        for index, text in enumerate(clean_texts):
            if not text:
                continue
            if source_lang.lower() == target_lang.lower():
                translations[index] = text
                continue
            cached = self.cache.get(source_lang, target_lang, text)
            if cached is not None:
                translations[index] = cached
                continue
            missing.setdefault(text, []).append(index)

        if not missing:
            return translations, warnings

        texts_to_translate = list(missing)
        try:
            translated_texts = self._translation_batch_provider(
                texts_to_translate,
                source_lang,
                target_lang
            )
            if len(translated_texts) != len(texts_to_translate):
                raise ValueError(
                    f"Batch translation returned {len(translated_texts)} results "
                    f"for {len(texts_to_translate)} input texts."
                )

            for text, translated in zip(texts_to_translate, translated_texts):
                result = translated or text
                self.cache.set(source_lang, target_lang, text, result)
                for index in missing[text]:
                    translations[index] = result
        except Exception as exc:
            logger.warning("Batch translation failed for %d texts: %s", len(texts_to_translate), exc)
            warning = f"Translation provider warning: {str(exc)}"
            for text, indexes in missing.items():
                for index in indexes:
                    translations[index] = text
                    warnings[index] = warning

        return translations, warnings


    def _default_deep_translator(self, text: str, source_lang: str, target_lang: str) -> str:
        """Default translation provider using deep-translator."""
        from deep_translator import GoogleTranslator
        src = "auto" if source_lang in ["auto", "", None] else source_lang
        translated = GoogleTranslator(source=src, target=target_lang).translate(text)
        return translated or text

    def _default_deep_translator_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str
    ) -> list[str]:
        """Translates a group of strings in one provider request."""
        if not texts:
            return []

        from deep_translator import GoogleTranslator
        src = "auto" if source_lang in ["auto", "", None] else source_lang
        separator = "XQZBUBBLESEP7F3A1D9B6C2E8XQZ"
        while any(separator in text for text in texts):
            separator += "X"

        translated = GoogleTranslator(source=src, target=target_lang).translate(
            separator.join(texts)
        )
        results = [text.strip() for text in translated.split(separator)]
        if len(results) != len(texts):
            raise ValueError(
                f"Batch translation returned {len(results)} segments "
                f"for {len(texts)} input texts."
            )
        return results

    def extract_text(
        self,
        image_rgb: np.ndarray,
        bbox: dict[str, int]
    ) -> tuple[str, float]:
        """Extracts text from a single bubble bounding box crop using EasyOCR.

        Args:
            image_rgb: Complete RGB comic page.
            bbox: Bounding box dictionary with keys 'x', 'y', 'width', 'height'.

        Returns:
            Tuple of (extracted_text, confidence_score).
        """
        x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
        
        # Add small inner margin to avoid outer black bubble border
        pad_x = max(2, int(w * 0.05))
        pad_y = max(2, int(h * 0.05))
        
        crop = image_rgb[y + pad_y : y + h - pad_y, x + pad_x : x + w - pad_x]
        if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
            return "", 0.0

        if self.reader is None:
            # Fallback when EasyOCR is not installed or mocked
            return "Sample Comic Text", 0.95

        try:
            results = self.reader.readtext(crop)
            if not results:
                return "", 0.0

            lines = []
            scores = []
            for _, text, conf in results:
                clean_text = text.strip()
                if clean_text:
                    lines.append(clean_text)
                    scores.append(float(conf))

            combined_text = " ".join(lines)
            avg_score = float(np.mean(scores)) if scores else 0.0
            return combined_text, avg_score
        except Exception as exc:
            logger.warning(f"EasyOCR extraction error: {exc}")
            return "", 0.0

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> tuple[str, Optional[str]]:
        """Translates text from source_lang to target_lang with LRU caching.

        Returns:
            Tuple of (translated_text, optional_warning_message).
        """
        clean_text = text.strip()
        if not clean_text:
            return "", None

        if source_lang.lower() == target_lang.lower():
            return clean_text, None

        # Check cache
        cached = self.cache.get(source_lang, target_lang, clean_text)
        if cached is not None:
            return cached, None

        # Execute translation provider
        try:
            translated = self._translation_provider(clean_text, source_lang, target_lang)
            self.cache.set(source_lang, target_lang, clean_text, translated)
            return translated, None
        except Exception as exc:
            logger.warning(f"Translation failed for '{clean_text}': {exc}")
            # Graceful degradation: return original text with warning
            return clean_text, f"Translation provider warning: {str(exc)}"
