from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProjectStatus(str, Enum):
    uploaded = "uploaded"
    recognizing = "recognizing"
    recognized = "recognized"
    analyzing = "analyzing"
    analyzed = "analyzed"
    reporting = "reporting"
    completed = "completed"
    failed = "failed"


class RecognitionResult(BaseModel):
    musicxml_url: str | None = None
    midi_url: str | None = None
    confidence: float = 0.0
    engine: str = "demo-fallback"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    extracted_title: str | None = None


class MusicAnalysis(BaseModel):
    key: str = "未知"
    time_signature: str = "未知"
    tempo: str = "Andante espressivo"
    measure_count: int = 0
    part_count: int = 0
    chords: list[dict[str, Any]] = Field(default_factory=list)
    roman_numerals: list[dict[str, Any]] = Field(default_factory=list)
    phrases: list[dict[str, Any]] = Field(default_factory=list)
    texture: list[str] = Field(default_factory=list)
    form_candidates: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class Report(BaseModel):
    title: str
    markdown: str
    html: str
    pdf_url: str | None = None
    generated_at: datetime
    provider: str = "unknown"
    model: str | None = None
    provider_error: str | None = None


class Project(BaseModel):
    id: str
    title: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    source_filename: str
    source_url: str
    source_mime: str
    recognition: RecognitionResult | None = None
    analysis: MusicAnalysis | None = None
    report: Report | None = None
    error: str | None = None
