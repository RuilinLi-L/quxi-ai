from __future__ import annotations

import shutil
import subprocess
import os
import re
import sys
import uuid
from pathlib import Path

from ..models import RecognitionResult
from ..storage import asset_url
from .demo_score import write_demo_score


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
DEMO_OMR_ENV = "ALLOW_DEMO_OMR"
SUBPROCESS_ERROR_LIMIT = 1600
OEMER_PATH_ENV = "OEMER_PATH"
OEMER_CUDA_DLL_DIR_ENV = "OEMER_CUDA_DLL_DIR"
OEMER_PRELOAD_CUDA_ENV = "OEMER_PRELOAD_CUDA"
AUDIVERIS_PATH_ENV = "AUDIVERIS_PATH"
OMR_TIMEOUT_ENV = "OMR_TIMEOUT_SECONDS"
OEMER_TIMEOUT_ENV = "OEMER_TIMEOUT_SECONDS"
AUDIVERIS_TIMEOUT_ENV = "AUDIVERIS_TIMEOUT_SECONDS"
OEMER_ENABLE_DESKEW_ENV = "OEMER_ENABLE_DESKEW"
DEFAULT_OEMER_TIMEOUT_SECONDS = 600
DEFAULT_AUDIVERIS_TIMEOUT_SECONDS = 300
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CUDA_DLL_MARKERS = ("cublasLt64_12.dll", "cudnn64_9.dll")
OEMER_WRAPPER_CODE = r"""
import sys

dll_dir = sys.argv[1] or None
img_path = sys.argv[2]
output_path = sys.argv[3]
extra_args = sys.argv[4:]

if dll_dir:
    import onnxruntime as ort

    ort.preload_dlls(directory=dll_dir)

from oemer.ete import main

sys.argv = ["oemer", img_path, "-o", output_path, *extra_args]
main()
"""


def demo_omr_enabled() -> bool:
    return os.getenv(DEMO_OMR_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_timeout(names: tuple[str, ...], default: int) -> int:
    for name in names:
        raw = os.getenv(name, "").strip()
        if not raw:
            continue
        try:
            seconds = int(raw)
        except ValueError:
            continue
        if seconds > 0:
            return seconds
    return default


def resolve_executable(command: str, env_name: str) -> str | None:
    configured = os.getenv(env_name, "").strip().strip('"')
    if configured:
        return configured
    return shutil.which(command) or shutil.which(f"{command}.exe")


def has_cuda_dlls(directory: Path) -> bool:
    return directory.is_dir() and all((directory / marker).exists() for marker in CUDA_DLL_MARKERS)


def iter_cuda_dll_dirs() -> list[Path]:
    candidates: list[Path] = []
    configured = os.getenv(OEMER_CUDA_DLL_DIR_ENV, "").strip().strip('"')
    if configured:
        candidates.append(Path(configured))

    current_prefix = Path(sys.prefix)
    candidates.append(current_prefix / "Lib" / "site-packages" / "torch" / "lib")

    conda_envs = current_prefix.parent
    if conda_envs.name.lower() == "envs":
        for env_dir in conda_envs.iterdir():
            candidates.append(env_dir / "Lib" / "site-packages" / "torch" / "lib")

    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique


def resolve_oemer_cuda_dll_dir() -> Path | None:
    if not env_flag(OEMER_PRELOAD_CUDA_ENV, default=True):
        return None
    for directory in iter_cuda_dll_dirs():
        if has_cuda_dlls(directory):
            return directory
    return None


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


def clean_subprocess_text(value: str | bytes | None) -> str:
    if not value:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    value = ANSI_ESCAPE_RE.sub("", value)
    return value.replace("\x00", "").replace("\r", "\n").strip()


def subprocess_details(*parts: str | bytes | None) -> str:
    details = "\n".join(clean_subprocess_text(part) for part in parts if part).strip()
    return details[-SUBPROCESS_ERROR_LIMIT:] if details else ""


def timeout_hint(command_name: str) -> str:
    name = command_name.lower()
    if "audiveris" in name:
        return f"{AUDIVERIS_TIMEOUT_ENV} 或 {OMR_TIMEOUT_ENV}"
    if "oemer" in name:
        return f"{OEMER_TIMEOUT_ENV} 或 {OMR_TIMEOUT_ENV}"
    return OMR_TIMEOUT_ENV


def run_omr_command(command: list[str], timeout: int, label: str | None = None) -> None:
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        details = subprocess_details(exc.stderr, exc.stdout)
        command_name = label or Path(command[0]).name
        message = (
            f"{command_name} 超过 {timeout} 秒仍未完成；"
            f"如果本机回落到 CPU 推理，单页识谱可能需要数分钟。"
            f"可调高 {timeout_hint(command_name)}，也可以上传裁剪更干净的单页谱面后重试。"
        )
        if details:
            message = f"{message}\n最近输出：{details}"
        raise RuntimeError(message) from exc
    except subprocess.CalledProcessError as exc:
        details = subprocess_details(exc.stderr, exc.stdout)
        if details:
            raise RuntimeError(f"{Path(command[0]).name} 退出码 {exc.returncode}：{details}") from exc
        raise RuntimeError(f"{Path(command[0]).name} 退出码 {exc.returncode}") from exc


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


def run_oemer(oemer: str, input_path: Path, musicxml_path: Path) -> float:
    # oemer/OpenCV can fail to read image paths containing non-ASCII characters on Windows.
    # Keep temp files in an ASCII-named project subdirectory, then copy the result back.
    temp_path = musicxml_path.parent / f"quxi_omr_{uuid.uuid4().hex}"
    temp_path.mkdir()
    try:
        temp_input = temp_path / f"source{input_path.suffix.lower() or '.png'}"
        shutil.copy2(input_path, temp_input)

        extra_args: list[str] = []
        if not env_flag(OEMER_ENABLE_DESKEW_ENV):
            extra_args.append("--without-deskew")
        cuda_dll_dir = resolve_oemer_cuda_dll_dir()
        if cuda_dll_dir:
            command = [
                sys.executable,
                "-c",
                OEMER_WRAPPER_CODE,
                str(cuda_dll_dir),
                str(temp_input),
                str(temp_path),
                *extra_args,
            ]
        else:
            command = [oemer, str(temp_input), "-o", str(temp_path), *extra_args]
        timeout = env_timeout((OEMER_TIMEOUT_ENV, OMR_TIMEOUT_ENV), DEFAULT_OEMER_TIMEOUT_SECONDS)
        run_omr_command(command, timeout=timeout, label="oemer")

        candidates = list(temp_path.glob("*.musicxml")) + list(temp_path.glob("*.xml")) + list(temp_path.glob("*.mxl"))
        if not candidates:
            raise RuntimeError("oemer did not produce a MusicXML file")
        shutil.copy2(candidates[0], musicxml_path)
        return 0.78
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def recognize_score(project_id: str, project_path: Path, source_path: Path) -> RecognitionResult:
    musicxml_path = project_path / "score.musicxml"
    midi_path = project_path / "score.mid"
    preprocessed_path = project_path / "preprocessed.png"
    warnings = preprocess_source(source_path, preprocessed_path)

    engine = ""
    confidence = 0.0
    errors: list[str] = []

    oemer = resolve_executable("oemer", OEMER_PATH_ENV)
    audiveris = resolve_executable("audiveris", AUDIVERIS_PATH_ENV)

    try:
        if oemer and source_path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
            engine = "oemer"
            if not env_flag(OEMER_ENABLE_DESKEW_ENV):
                warnings.append(f"已跳过 oemer 内置去倾斜以减少 CPU 识别卡顿；若原图明显倾斜，可设置 {OEMER_ENABLE_DESKEW_ENV}=1 后重试。")
            cuda_dll_dir = resolve_oemer_cuda_dll_dir()
            if cuda_dll_dir:
                warnings.append(f"已为 oemer 预加载 CUDA/cuDNN 运行库：{cuda_dll_dir}")
            oemer_input_path = preprocessed_path if preprocessed_path.exists() else source_path
            confidence = run_oemer(oemer, oemer_input_path, musicxml_path)
        elif audiveris:
            engine = "audiveris"
            timeout = env_timeout((AUDIVERIS_TIMEOUT_ENV, OMR_TIMEOUT_ENV), DEFAULT_AUDIVERIS_TIMEOUT_SECONDS)
            run_omr_command([audiveris, "-batch", "-export", str(source_path)], timeout=timeout)
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
                reason = f"未检测到 oemer 或 Audiveris，无法执行真实谱面识别。可设置 {OEMER_PATH_ENV} 或 {AUDIVERIS_PATH_ENV} 指向本机引擎可执行文件。"
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
