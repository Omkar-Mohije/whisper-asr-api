from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ExportFormatEnum(str, Enum):
    TXT = "txt"
    SRT = "srt"
    VTT = "vtt"
    JSON = "json"
    ZIP = "zip"


class WordItem(BaseModel):
    start: Optional[float] = Field(None, description="Start time in seconds")
    end: Optional[float] = Field(None, description="End time in seconds")
    word: str = Field(..., description="Recognized word or token")
    probability: Optional[float] = Field(None, description="Confidence score between 0 and 1")


class SegmentItem(BaseModel):
    id: int = Field(..., description="Segment sequential index")
    start: float = Field(..., description="Segment start timestamp in seconds")
    end: float = Field(..., description="Segment end timestamp in seconds")
    text: str = Field(..., description="Segment transcript text")
    avg_logprob: Optional[float] = Field(None, description="Average token log probability")
    no_speech_prob: Optional[float] = Field(None, description="Probability that the segment contains no speech")
    words: List[WordItem] = Field(default_factory=list, description="Word-level alignments with timestamps")


class ASRMetadata(BaseModel):
    language: Optional[str] = Field(None, description="Detected or specified ISO language code")
    language_probability: Optional[float] = Field(None, description="Language detection confidence")
    duration: float = Field(..., description="Audio duration in seconds")
    processing_seconds: float = Field(..., description="Total wall-clock processing time")
    rtf: float = Field(..., description="Real-time factor (processing_seconds / duration)")
    model_size: str = Field(..., description="Whisper model size used for transcription")
    device: str = Field(..., description="Device used (cuda or cpu)")
    compute_type: str = Field(..., description="Quantization compute type (float16, int8, etc.)")


class TranscriptionResponse(BaseModel):
    success: bool = True
    metadata: ASRMetadata
    transcript: str = Field(..., description="Full joined transcript text")
    segments: List[SegmentItem] = Field(default_factory=list, description="Timestamped segments list")


class EvaluationRequest(BaseModel):
    reference_text: str = Field(..., min_length=1, description="Ground truth human transcript")
    hypothesis_text: str = Field(..., min_length=1, description="Model generated transcript")


class EvaluationResponse(BaseModel):
    wer: float = Field(..., description="Word Error Rate (0.0 = perfect match)")
    cer: float = Field(..., description="Character Error Rate (0.0 = perfect match)")
    reference_words: int = Field(..., description="Number of words in reference text")
    hypothesis_words: int = Field(..., description="Number of words in hypothesis text")


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    model_loaded: bool
    current_model: str
    device: str
    compute_type: str
    cuda_available: bool
    gpu_name: Optional[str] = None
