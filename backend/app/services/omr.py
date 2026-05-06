from __future__ import annotations

import shutil
import subprocess
import os
from pathlib import Path

from ..models import RecognitionResult
from ..storage import asset_url
from .demo_score import write_demo_score


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
DEMO_OMR_ENV = "ALLOW_DEMO_OMR"


def demo_omr_enabled() -> bool:
    return os.getenv(DEMO_OMR_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def write_demo_fallback(musicxml_path: Path, midi_path: Path, warnings: list[str], errors: list[str], reason: str) -> RecognitionResult:
    warnings.append(f"真实 OMR 未成功：{reason}")
    warnings.append(f"已开启 {DEMO_OMR_ENV}，本次使用内置演示谱；该结果不会反映上传谱面内容。")
    write_demo_score(musicxml_path, midi_path)
    return RecognitionResult(
        musicxml_url="",
        midi_url=None,
        confidence=0.48,
        engine="demo-fallback",
        warnings=warnings,
        errors=errors,
        extracted_title="无词歌风格钢琴小品",
    )


def preprocess_source(source_path: Path, output_path: Path) -> list[str]:
    warnings: list[str] = []
    if source_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        warnings.append("当前文件不是图片，已跳过拍照矫正预处理。")
        return warnings

    try:
        from PIL import Image, ImageOps
    except ImportError:
        warnings.append("Pillow 未安装，已跳过图片灰度化与自动对比度预处理。")
        return warnings

    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("L")
        image = ImageOps.autocontrast(image)
        image.save(output_path)

        if min(image.size) < 900:
            warnings.append("图片分辨率偏低，建议使用更清晰的谱面照片。")
        if max(image.size) / max(1, min(image.size)) > 2.4:
            warnings.append("图片长宽比例较极端，可能只包含局部谱面或裁切不完整。")

    return warnings


def recognize_score(project_id: str, project_path: Path, source_path: Path) -> RecognitionResult:
    musicxml_path = project_path / "score.musicxml"
    midi_path = project_path / "score.mid"
    preprocessed_path = project_path / "preprocessed.png"
    warnings = preprocess_source(source_path, preprocessed_path)

    engine = ""
    confidence = 0.0
    errors: list[str] = []

    oemer = shutil.which("oemer")
    audiveris = shutil.which("audiveris")

    try:
        if oemer and source_path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
            engine = "oemer"
            oemer_input_path = preprocessed_path if preprocessed_path.exists() else source_path
            subprocess.run(
                [oemer, str(oemer_input_path), "-o", str(project_path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            candidates = list(project_path.glob("*.musicxml")) + list(project_path.glob("*.xml"))
            if candidates:
                candidates[0].replace(musicxml_path)
                confidence = 0.78
            else:
                raise RuntimeError("oemer did not produce a MusicXML file")
        elif audiveris:
            engine = "audiveris"
            subprocess.run(
                [audiveris, "-batch", "-export", str(source_path)],
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
            candidates = list(source_path.parent.glob("*.mxl")) + list(source_path.parent.glob("*.musicxml")) + list(source_path.parent.glob("*.xml"))
            if candidates:
                candidates[0].replace(musicxml_path)
                confidence = 0.74
            else:
                raise RuntimeError("Audiveris did not produce a MusicXML file")
        else:
            if oemer:
                reason = "oemer 仅支持图片输入；当前 PDF 需要安装 Audiveris 才能识别。"
            else:
                reason = "未检测到 oemer 或 Audiveris，无法执行真实谱面识别。"
            if demo_omr_enabled():
                fallback = write_demo_fallback(musicxml_path, midi_path, warnings, errors, reason)
                fallback.musicxml_url = asset_url(project_id, "score.musicxml")
                fallback.midi_url = asset_url(project_id, "score.mid") if midi_path.exists() else None
                return fallback
            raise RuntimeError(f"{reason} 如需产品演示，可临时设置 {DEMO_OMR_ENV}=1。")
    except Exception as exc:
        errors.append(f"{engine or 'OMR'} 调用失败：{exc}")
        if demo_omr_enabled():
            fallback = write_demo_fallback(musicxml_path, midi_path, warnings, errors, str(exc))
            fallback.musicxml_url = asset_url(project_id, "score.musicxml")
            fallback.midi_url = asset_url(project_id, "score.mid") if midi_path.exists() else None
            return fallback
        raise RuntimeError(f"真实 OMR 识别失败：{exc}") from exc

    if not midi_path.exists():
        try:
            from music21 import converter

            score = converter.parse(str(musicxml_path))
            score.write("midi", fp=str(midi_path))
        except Exception as exc:
            errors.append(f"MIDI 导出失败：{exc}")

    return RecognitionResult(
        musicxml_url=asset_url(project_id, "score.musicxml"),
        midi_url=asset_url(project_id, "score.mid") if midi_path.exists() else None,
        confidence=confidence,
        engine=engine,
        warnings=warnings,
        errors=errors,
        extracted_title=None,
    )
