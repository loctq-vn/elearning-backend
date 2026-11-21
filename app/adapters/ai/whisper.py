"""Whisper speech-to-text adapter boundary (Spec 11 §5.2)."""

from __future__ import annotations

import logging
import shutil
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import ctranslate2
import numpy as np
from faster_whisper import WhisperModel

from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


class WhisperError(RuntimeError):
    """Raised when audio transcription fails."""


@dataclass(slots=True)
class WhisperSegmentResult:
    """Normalized subtitle segment with precise start and end timestamps."""

    segment_index: int
    start_time: float
    end_time: float
    text: str


def load_audio_samples(audio_path: str | Path) -> np.ndarray | str:
    """Load WAV file directly into a 16kHz float32 numpy array.

    Using Python's built-in wave module bypasses external PyAV container
    version incompatibilities (e.g. metadata_errors parameter changes in PyAV 15+).
    """
    path = Path(audio_path)
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sampwidth = wf.getsampwidth()
            n_channels = wf.getnchannels()

            if sampwidth == 2:
                samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            elif sampwidth == 4:
                samples = np.frombuffer(frames, dtype=np.float32)
            else:
                samples = np.frombuffer(frames, dtype=np.int8).astype(np.float32) / 128.0

            if n_channels > 1:
                samples = samples.reshape(-1, n_channels).mean(axis=1)
            return samples
    except Exception as exc:
        logger.debug("Native wave parsing fallback for '%s': %s", path.name, exc)
        return str(path)


class WhisperAdapter:
    """Encapsulates faster-whisper local model inference for audio transcription."""

    def __init__(
        self,
        config: Settings = settings,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        download_root: str | None = None,
    ) -> None:
        self.config = config
        self.model_size = model_size or config.whisper_model_size
        self.device = device or config.whisper_device
        self.compute_type = compute_type or config.whisper_compute_type
        self.download_root = download_root

        # Resolve device and compute_type according to Spec 11 §5.2:
        # "int8 khi chạy CPU, float16 khi chạy GPU. Không dùng float16 trên CPU"
        has_cuda = bool(ctranslate2.get_cuda_device_count() > 0)
        if self.device == "auto":
            if has_cuda:
                self.device = "cuda"
                if self.compute_type in ("int8", "auto"):
                    # keep int8 or float16 if user specified
                    pass
            else:
                self.device = "cpu"
                self.compute_type = "int8"
        elif self.device == "cpu":
            # Guard against float16 on CPU
            if self.compute_type in ("float16", "auto"):
                self.compute_type = "int8"

        self._model: WhisperModel | None = None

    @property
    def model(self) -> WhisperModel:
        """Lazy-load the WhisperModel instance upon first invocation."""
        if self._model is None:
            logger.info(
                "Loading faster-whisper model '%s' (device=%s, compute_type=%s)...",
                self.model_size,
                self.device,
                self.compute_type,
            )
            try:
                self._model = WhisperModel(
                    model_size_or_path=self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    download_root=self.download_root,
                )
            except Exception as exc:
                logger.error("Failed to load faster-whisper model '%s': %s", self.model_size, exc)
                raise WhisperError(f"Failed to initialize Whisper model: {exc}") from exc
        return self._model

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
        beam_size: int | None = None,
        vad_filter: bool | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> list[WhisperSegmentResult]:
        """Transcribe local audio file into structured timestamped segments (Spec 11 §5.2)."""
        audio_file = Path(audio_path)
        if not audio_file.is_file():
            raise WhisperError(f"Audio file not found: '{audio_path}'")

        target_lang = language or self.config.whisper_language
        target_beam = beam_size or self.config.whisper_beam_size
        target_vad = vad_filter if vad_filter is not None else self.config.whisper_vad_filter

        logger.info(
            "Starting Whisper transcription for '%s' (lang=%s, beam=%d, vad=%s)...",
            audio_file.name,
            target_lang,
            target_beam,
            target_vad,
        )

        try:
            audio_input = load_audio_samples(audio_file)
            segments_gen, info = self.model.transcribe(
                audio_input,
                language=target_lang,
                beam_size=target_beam,
                vad_filter=target_vad,
            )
            # Materialize first segment to catch any lazy CUDA DLL initialization errors early
            first_segment = None
            try:
                first_segment = next(segments_gen, None)
            except RuntimeError as exc:
                if any(k in str(exc).lower() for k in ("cublas", "cuda", "cudnn")):
                    logger.warning(
                        "CUDA dynamic library missing (%s). Falling back to CPU int8 inference...",
                        exc,
                    )
                    self.device = "cpu"
                    self.compute_type = "int8"
                    self._model = WhisperModel(
                        model_size_or_path=self.model_size,
                        device="cpu",
                        compute_type="int8",
                        download_root=self.download_root,
                    )
                    segments_gen, info = self.model.transcribe(
                        audio_input,
                        language=target_lang,
                        beam_size=target_beam,
                        vad_filter=target_vad,
                    )
                    first_segment = next(segments_gen, None)
                else:
                    raise

            # Recombine first_segment with remaining generator
            if first_segment is not None:
                segments_iterable = [first_segment] + list(segments_gen)
            else:
                segments_iterable = []
        except Exception as exc:
            logger.error("Whisper transcription process failed: %s", exc)
            raise WhisperError(f"Whisper inference error: {exc}") from exc

        total_duration = float(info.duration) if info and info.duration else 0.0
        results: list[WhisperSegmentResult] = []
        seg_index = 0

        for seg in segments_iterable:
            clean_text = seg.text.strip()
            if not clean_text:
                continue

            raw_start = max(0.0, float(seg.start))
            raw_end = float(seg.end)

            # Ensure strict check constraint: end_time > start_time and start_time >= 0
            start_time = round(raw_start, 2)
            end_time = round(raw_end, 2)
            if end_time <= start_time:
                end_time = round(start_time + 0.1, 2)

            results.append(
                WhisperSegmentResult(
                    segment_index=seg_index,
                    start_time=start_time,
                    end_time=end_time,
                    text=clean_text,
                )
            )
            seg_index += 1

            if progress_callback and total_duration > 0.0:
                pct = min(99.0, round((end_time / total_duration) * 100.0, 1))
                progress_callback(pct)

        if progress_callback:
            progress_callback(100.0)

        logger.info(
            "Transcription completed for '%s': produced %d segments (duration=%.1fs)",
            audio_file.name,
            len(results),
            total_duration,
        )
        return results
