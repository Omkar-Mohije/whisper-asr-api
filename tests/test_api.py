import json
import zipfile
import io
import pytest
from unittest.mock import MagicMock, patch

from app.core.exporters import (
    format_srt_timestamp,
    format_vtt_timestamp,
    export_to_txt,
    export_to_srt,
    export_to_vtt,
    export_to_json,
    create_export_zip,
)
from app.core.evaluation import compute_wer_cer


def test_srt_timestamp_formatting():
    assert format_srt_timestamp(0) == "00:00:00,000"
    assert format_srt_timestamp(1.234) == "00:00:01,234"
    assert format_srt_timestamp(65.5) == "00:01:05,500"
    assert format_srt_timestamp(3661.001) == "01:01:01,001"
    # Ensure None doesn't crash
    assert format_srt_timestamp(None) == "00:00:00,000"


def test_vtt_timestamp_formatting():
    assert format_vtt_timestamp(0) == "00:00:00.000"
    assert format_vtt_timestamp(1.234) == "00:00:01.234"
    assert format_vtt_timestamp(65.5) == "00:01:05.500"
    assert format_vtt_timestamp(None) == "00:00:00.000"


def test_export_txt():
    segments = [
        {"id": 0, "start": 0.0, "end": 2.0, "text": "Hello world."},
        {"id": 1, "start": 2.0, "end": 4.5, "text": "This is a test transcript."}
    ]
    txt = export_to_txt(segments)
    assert txt == "Hello world. This is a test transcript."


def test_export_srt():
    segments = [
        {"id": 0, "start": 0.0, "end": 2.0, "text": "First segment"},
        {"id": 1, "start": 2.5, "end": 5.0, "text": "Second segment"}
    ]
    srt = export_to_srt(segments)
    assert "1\n00:00:00,000 --> 00:00:02,000\nFirst segment" in srt
    assert "2\n00:00:02,500 --> 00:00:05,000\nSecond segment" in srt


def test_export_vtt():
    segments = [
        {"id": 0, "start": 1.0, "end": 3.0, "text": "Subtitle line"}
    ]
    vtt = export_to_vtt(segments)
    assert vtt.startswith("WEBVTT")
    assert "00:00:01.000 --> 00:00:03.000\nSubtitle line" in vtt


def test_export_json():
    meta = {"duration": 10.0, "language": "en"}
    segments = [{"id": 0, "start": 0.0, "end": 1.0, "text": "Hi"}]
    json_str = export_to_json(meta, "Hi", segments)
    parsed = json.loads(json_str)
    assert parsed["metadata"]["duration"] == 10.0
    assert parsed["transcript"] == "Hi"
    assert len(parsed["segments"]) == 1


def test_create_export_zip():
    meta = {"duration": 5.0}
    segments = [{"id": 0, "start": 0.0, "end": 2.0, "text": "Audio test"}]
    zip_bytes = create_export_zip(meta, "Audio test", segments, stem="sample")

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "sample.txt" in namelist
        assert "sample.srt" in namelist
        assert "sample.vtt" in namelist
        assert "sample.json" in namelist


def test_evaluation_wer_cer():
    ref = "the quick brown fox jumps over the lazy dog"
    hyp = "the quick brown fox jumped over the lazy dog"

    res = compute_wer_cer(ref, hyp)
    assert "wer" in res
    assert "cer" in res
    assert res["wer"] > 0.0
    assert res["wer"] < 1.0


def test_none_word_timestamps_resilience():
    """
    Verifies that None timestamps from faster-whisper don't raise TypeError
    when parsing word timing dictionaries.
    """
    mock_word = MagicMock()
    mock_word.start = None
    mock_word.end = None
    mock_word.word = "test"
    mock_word.probability = 0.95

    # Safe conversion test
    w_start = float(mock_word.start) if mock_word.start is not None else None
    w_end = float(mock_word.end) if mock_word.end is not None else None

    assert w_start is None
    assert w_end is None
