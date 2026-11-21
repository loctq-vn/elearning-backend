"""Tests for Whisper Audio Transcription Adapter (Phase D1.01, D1.03, Spec 11 §5.2)."""

from __future__ import annotations

import tempfile
from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.ai.whisper import (
    WhisperAdapter,
    WhisperError,
    WhisperSegmentResult,
)
from app.core.config import Settings

MockRawSegment = namedtuple("MockRawSegment", ["start", "end", "text"])
MockTranscriptionInfo = namedtuple("MockTranscriptionInfo", ["duration", "language"])


def test_whisper_adapter_cpu_int8_guard() -> None:
    """Spec 11 §5.2: Enforce int8 on CPU, preventing invalid float16 compute type."""
    cfg = Settings(whisper_device="cpu", whisper_compute_type="float16")
    adapter = WhisperAdapter(config=cfg)
    assert adapter.device == "cpu"
    assert adapter.compute_type == "int8"


def test_whisper_adapter_file_not_found() -> None:
    """Transcription must raise WhisperError when input audio does not exist."""
    adapter = WhisperAdapter()
    with pytest.raises(WhisperError, match="Audio file not found"):
        adapter.transcribe("non_existent_audio_file.wav")


def test_whisper_transcribe_mocked_segments_and_constraints() -> None:
    """Verify segment parsing, whitespace stripping, and constraint normalization."""
    adapter = WhisperAdapter()

    # Raw segments with edge cases:
    # - segment 1: normal
    # - segment 2: end <= start (violating check constraint if not normalized)
    # - segment 3: empty whitespace text (should be filtered out)
    # - segment 4: negative start (should be clamped to 0.0)
    mock_segments = [
        MockRawSegment(start=0.0, end=2.5, text=" Xin chào các bạn! "),
        MockRawSegment(start=2.5, end=2.5, text="Đây là bài giảng"),
        MockRawSegment(start=2.5, end=3.0, text="   "),
        MockRawSegment(start=-0.5, end=4.2, text="Kiến trúc hệ thống"),
    ]
    mock_info = MockTranscriptionInfo(duration=5.0, language="vi")

    progress_reports: list[float] = []

    def on_progress(p: float) -> None:
        progress_reports.append(p)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
        tmp_path = Path(tmp_audio.name)

    try:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter(mock_segments), mock_info)
        adapter._model = mock_model

        results = adapter.transcribe(
            tmp_path,
            language="vi",
            progress_callback=on_progress,
        )

        assert len(results) == 3
        # Check segment 0
        assert results[0].segment_index == 0
        assert results[0].start_time == 0.0
        assert results[0].end_time == 2.5
        assert results[0].text == "Xin chào các bạn!"

        # Check segment 1 normalized end_time > start_time
        assert results[1].segment_index == 1
        assert results[1].start_time == 2.5
        assert results[1].end_time > 2.5
        assert results[1].text == "Đây là bài giảng"

        # Check segment 2 clamped start_time >= 0
        assert results[2].segment_index == 2
        assert results[2].start_time >= 0.0
        assert results[2].end_time > results[2].start_time
        assert results[2].text == "Kiến trúc hệ thống"

        # Check progress callback completed to 100%
        assert 100.0 in progress_reports
    finally:
        tmp_path.unlink(missing_ok=True)
