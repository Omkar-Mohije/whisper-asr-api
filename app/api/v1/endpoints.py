import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.asr_engine import get_whisper_engine
from app.core.audio_utils import preprocess_audio, AudioProcessingError
from app.core.evaluation import compute_wer_cer
from app.core.exporters import (
    create_export_zip,
    export_to_json,
    export_to_srt,
    export_to_txt,
    export_to_vtt,
)
from app.schemas.asr import (
    EvaluationRequest,
    EvaluationResponse,
    ExportFormatEnum,
    HealthResponse,
    TranscriptionResponse,
)

router = APIRouter()


AVAILABLE_MODELS = [
    "tiny", "tiny.en",
    "base", "base.en",
    "small", "small.en",
    "medium", "medium.en",
    "large-v1", "large-v2", "large-v3",
    "large-v3-turbo"
]


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Returns service health, GPU status, and currently loaded model info."""
    engine = get_whisper_engine()
    cuda_avail = False
    gpu_name = None

    try:
        import torch
        cuda_avail = torch.cuda.is_available()
        if cuda_avail:
            gpu_name = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    dev, comp = settings.resolve_device_and_compute()

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        model_loaded=engine.is_loaded,
        current_model=engine.model_info["model_size"] or settings.WHISPER_MODEL_SIZE,
        device=engine.model_info["device"] or dev,
        compute_type=engine.model_info["compute_type"] or comp,
        cuda_available=cuda_avail,
        gpu_name=gpu_name,
    )


@router.get("/models", tags=["System"])
async def list_models():
    """Lists standard supported Whisper model sizes and active configuration."""
    engine = get_whisper_engine()
    return {
        "available_models": AVAILABLE_MODELS,
        "active_model": engine.model_info["model_size"] or settings.WHISPER_MODEL_SIZE,
        "default_device": settings.WHISPER_DEVICE,
        "default_compute_type": settings.WHISPER_COMPUTE_TYPE,
    }


async def _save_upload_file_safely(upload_file: UploadFile) -> Path:
    """Streams uploaded audio file to a sandboxed temporary location while enforcing size limits."""
    suffix = Path(upload_file.filename or "audio.wav").suffix or ".wav"
    temp_path = settings.TEMP_DIR / f"upload_{uuid.uuid4().hex}{suffix}"

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_written = 0

    try:
        with open(temp_path, "wb") as f:
            while chunk := await upload_file.read(1024 * 1024):  # 1MB chunks
                total_written += len(chunk)
                if total_written > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB}MB."
                    )
                f.write(chunk)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise

    return temp_path


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    tags=["Transcription"],
    summary="Transcribe audio/video to structured JSON"
)
async def transcribe_audio_endpoint(
    file: UploadFile = File(..., description="Audio or video file (WAV, MP3, MP4, M4A, FLAC, OGG, WEBM)"),
    model_size: Optional[str] = Form(None, description="Optional whisper model size override"),
    language: Optional[str] = Form(None, description="ISO-639-1 language code (e.g., 'en', 'es', 'hi') or omit for auto-detect"),
    task: str = Form("transcribe", description="'transcribe' or 'translate' to English"),
    beam_size: Optional[int] = Form(None, ge=1, le=10, description="Beam search width"),
    vad_filter: bool = Form(True, description="Enable Voice Activity Detection silence filtering"),
    condition_on_previous_text: bool = Form(True, description="Condition token generation on previous segment text"),
    min_silence_duration_ms: Optional[int] = Form(None, description="Minimum silence duration for VAD splits"),
    speech_pad_ms: Optional[int] = Form(None, description="Speech padding ms before and after chunks"),
    word_timestamps: bool = Form(True, description="Enable word-level timestamps")
):
    """
    Upload an audio/video file and receive the full transcript, metadata,
    and timestamped segments with optional word alignments.
    """
    temp_file = await _save_upload_file_safely(file)
    engine = get_whisper_engine()

    try:
        # Load custom model size if specified
        if model_size and model_size != engine.model_info["model_size"]:
            engine.load_model(model_size=model_size)

        audio_arr, sr, duration, is_silent = preprocess_audio(temp_file)

        result = engine.transcribe(
            audio_array=audio_arr,
            duration=duration,
            language=language,
            task=task,
            beam_size=beam_size,
            vad_filter=vad_filter,
            condition_on_previous_text=condition_on_previous_text,
            min_silence_duration_ms=min_silence_duration_ms,
            speech_pad_ms=speech_pad_ms,
            word_timestamps=word_timestamps,
            is_silent=is_silent,
        )

        return TranscriptionResponse(
            success=True,
            metadata=result["metadata"],
            transcript=result["transcript"],
            segments=result["segments"],
        )

    except AudioProcessingError as ape:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ape))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Transcription failed: {str(e)}")
    finally:
        if temp_file.exists():
            temp_file.unlink()


@router.post(
    "/transcribe/export",
    tags=["Transcription"],
    summary="Transcribe and download directly in TXT, SRT, VTT, JSON, or ZIP format"
)
async def transcribe_and_export_endpoint(
    file: UploadFile = File(...),
    export_format: ExportFormatEnum = Form(ExportFormatEnum.SRT, description="Desired export format"),
    model_size: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    task: str = Form("transcribe"),
    beam_size: Optional[int] = Form(None),
    vad_filter: bool = Form(True),
    condition_on_previous_text: bool = Form(True),
    word_timestamps: bool = Form(True)
):
    """Transcribes the uploaded media and returns the result directly as a downloadable formatted file."""
    temp_file = await _save_upload_file_safely(file)
    engine = get_whisper_engine()
    stem = Path(file.filename or "transcription").stem

    try:
        if model_size and model_size != engine.model_info["model_size"]:
            engine.load_model(model_size=model_size)

        audio_arr, sr, duration, is_silent = preprocess_audio(temp_file)

        result = engine.transcribe(
            audio_array=audio_arr,
            duration=duration,
            language=language,
            task=task,
            beam_size=beam_size,
            vad_filter=vad_filter,
            condition_on_previous_text=condition_on_previous_text,
            word_timestamps=word_timestamps,
            is_silent=is_silent,
        )

        segments = result["segments"]
        metadata = result["metadata"]
        transcript = result["transcript"]

        if export_format == ExportFormatEnum.SRT:
            content = export_to_srt(segments)
            return Response(
                content=content,
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{stem}.srt"'}
            )
        elif export_format == ExportFormatEnum.VTT:
            content = export_to_vtt(segments)
            return Response(
                content=content,
                media_type="text/vtt; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{stem}.vtt"'}
            )
        elif export_format == ExportFormatEnum.TXT:
            content = export_to_txt(segments)
            return Response(
                content=content + "\n",
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{stem}.txt"'}
            )
        elif export_format == ExportFormatEnum.JSON:
            content = export_to_json(metadata, transcript, segments)
            return Response(
                content=content,
                media_type="application/json; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{stem}.json"'}
            )
        elif export_format == ExportFormatEnum.ZIP:
            zip_bytes = create_export_zip(metadata, transcript, segments, stem=stem)
            return Response(
                content=zip_bytes,
                media_type="application/zip",
                headers={"Content-Disposition": f'attachment; filename="{stem}_asr_bundle.zip"'}
            )

    except AudioProcessingError as ape:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ape))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Export failed: {str(e)}")
    finally:
        if temp_file.exists():
            temp_file.unlink()


@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    tags=["Evaluation"],
    summary="Compute WER and CER between ground-truth reference and hypothesis"
)
async def evaluate_text_endpoint(payload: EvaluationRequest):
    """Calculates Word Error Rate (WER) and Character Error Rate (CER) via jiwer."""
    try:
        metrics = compute_wer_cer(payload.reference_text, payload.hypothesis_text)
        return EvaluationResponse(**metrics)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Evaluation failed: {str(e)}")
