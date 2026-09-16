from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class DubJobRequest(BaseModel):
    url: str = Field(..., description="Link to the source video")
    languages: List[str] = Field(
        ..., description="Target language codes, e.g. ['en', 'es', 'pt-br']"
    )


class Stage(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    SYNTHESIZING = "synthesizing"
    MUXING = "muxing"
    DONE = "done"
    FAILED = "failed"


class LanguageResult(BaseModel):
    language: str
    stage: Stage = Stage.QUEUED
    output_path: Optional[str] = None
    error: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    source_url: str
    stage: Stage = Stage.QUEUED
    error: Optional[str] = None
    transcript_preview: Optional[str] = None
    languages: Dict[str, LanguageResult] = {}
