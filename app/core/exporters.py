import io
import json
import zipfile
from typing import List, Dict, Any, Union


def format_srt_timestamp(seconds: Union[float, int, None]) -> str:
    """Format seconds into SubRip (SRT) timestamp format: HH:MM:SS,mmm"""
    if seconds is None:
        seconds = 0.0
    milliseconds = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_vtt_timestamp(seconds: Union[float, int, None]) -> str:
    """Format seconds into WebVTT timestamp format: HH:MM:SS.mmm"""
    if seconds is None:
        seconds = 0.0
    milliseconds = max(0, int(round(float(seconds) * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def export_to_txt(segments: List[Dict[str, Any]]) -> str:
    """Join all segment texts into a single string transcript."""
    return " ".join(s["text"].strip() for s in segments if s.get("text", "").strip()).strip()


def export_to_srt(segments: List[Dict[str, Any]]) -> str:
    """Convert segments to SubRip (.srt) subtitle string."""
    blocks = []
    idx = 1
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        start_ts = format_srt_timestamp(seg.get("start", 0.0))
        end_ts = format_srt_timestamp(seg.get("end", 0.0))
        blocks.append(f"{idx}\n{start_ts} --> {end_ts}\n{text}\n")
        idx += 1
    return "\n".join(blocks)


def export_to_vtt(segments: List[Dict[str, Any]]) -> str:
    """Convert segments to WebVTT (.vtt) subtitle string."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue
        start_ts = format_vtt_timestamp(seg.get("start", 0.0))
        end_ts = format_vtt_timestamp(seg.get("end", 0.0))
        lines.append(f"{start_ts} --> {end_ts}\n{text}\n")
    return "\n".join(lines)


def export_to_json(
    metadata: Dict[str, Any],
    transcript: str,
    segments: List[Dict[str, Any]]
) -> str:
    """Serialize full recognition data into indented JSON."""
    payload = {
        "metadata": metadata,
        "transcript": transcript,
        "segments": segments,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def create_export_zip(
    metadata: Dict[str, Any],
    transcript: str,
    segments: List[Dict[str, Any]],
    stem: str = "transcription"
) -> bytes:
    """Bundle TXT, SRT, VTT, and JSON representations into a single in-memory ZIP archive."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(f"{stem}.txt", export_to_txt(segments) + "\n")
        zip_file.writestr(f"{stem}.srt", export_to_srt(segments))
        zip_file.writestr(f"{stem}.vtt", export_to_vtt(segments))
        zip_file.writestr(f"{stem}.json", export_to_json(metadata, transcript, segments))

    buffer.seek(0)
    return buffer.getvalue()
