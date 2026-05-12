from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import load_local_env
from .models import Project, ProjectStatus
from .services.analysis import analyze_musicxml
from .services.omr import recognize_score
from .services.reporting import build_report_model, generate_report, write_report_pdf
from .storage import (
    asset_url,
    list_projects,
    load_project,
    project_dir,
    public_asset_path,
    save_project,
    set_status,
    store_upload,
    utcnow,
)


load_local_env()


app = FastAPI(title="曲析 AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff", "application/pdf"}
ALLOWED_SUFFIX = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}
MAX_UPLOAD_SIZE = 20 * 1024 * 1024


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/projects")
def get_projects() -> list[Project]:
    return list_projects()


@app.post("/api/projects")
async def create_project(file: UploadFile = File(...)) -> Project:
    suffix = Path(file.filename or "").suffix.lower()
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    if suffix not in ALLOWED_SUFFIX or mime not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="仅支持 JPG、PNG、WEBP、TIFF 或 PDF 乐谱文件。")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，请上传 20MB 以内的谱面。")
    await file.seek(0)

    project_id = uuid.uuid4().hex[:12]
    source_path = await store_upload(project_id, file)
    title = Path(file.filename or "未命名谱面").stem
    now = utcnow()
    project = Project(
        id=project_id,
        title=title,
        status=ProjectStatus.uploaded,
        created_at=now,
        updated_at=now,
        source_filename=file.filename or source_path.name,
        source_url=asset_url(project_id, source_path.name),
        source_mime=mime,
    )
    return save_project(project)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> Project:
    try:
        return load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="项目不存在")


@app.post("/api/projects/{project_id}/recognize")
def recognize(project_id: str) -> Project:
    project = load_project(project_id)
    project.recognition = None
    project.analysis = None
    project.report = None
    project.error = None
    set_status(project, ProjectStatus.recognizing)
    try:
        directory = project_dir(project_id)
        source_candidates = list(directory.glob("source.*"))
        if not source_candidates:
            raise RuntimeError("找不到上传源文件。")
        project.recognition = recognize_score(project_id, directory, source_candidates[0])
        project.status = ProjectStatus.recognized
        if project.recognition.extracted_title:
            project.title = project.recognition.extracted_title
        return save_project(project)
    except Exception as exc:
        project.status = ProjectStatus.failed
        project.error = str(exc)
        save_project(project)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/projects/{project_id}/analyze")
def analyze(project_id: str) -> Project:
    project = load_project(project_id)
    set_status(project, ProjectStatus.analyzing)
    try:
        musicxml_path = project_dir(project_id) / "score.musicxml"
        if not musicxml_path.exists():
            raise RuntimeError("请先完成识谱，生成 MusicXML。")
        project.analysis = analyze_musicxml(musicxml_path)
        project.status = ProjectStatus.analyzed
        return save_project(project)
    except Exception as exc:
        project.status = ProjectStatus.failed
        project.error = str(exc)
        save_project(project)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/projects/{project_id}/report")
async def report(project_id: str) -> Project:
    project = load_project(project_id)
    if not project.analysis:
        raise HTTPException(status_code=400, detail="请先完成乐理分析。")
    set_status(project, ProjectStatus.reporting)
    try:
        markdown = await generate_report(project, project.analysis)
        report_model = build_report_model(project_id, f"{project.title} 作品分析报告", markdown)
        project.report = report_model
        project.status = ProjectStatus.completed
        save_project(project)
        write_report_pdf(project_dir(project_id) / "report.pdf", project, report_model)
        return save_project(project)
    except Exception as exc:
        project.status = ProjectStatus.failed
        project.error = str(exc)
        save_project(project)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/projects/{project_id}/musicxml")
def get_musicxml(project_id: str) -> FileResponse:
    path = public_asset_path(project_id, "score.musicxml")
    return FileResponse(path, media_type="application/vnd.recordare.musicxml+xml", filename=f"{project_id}.musicxml")


@app.get("/api/projects/{project_id}/midi")
def get_midi(project_id: str) -> FileResponse:
    path = public_asset_path(project_id, "score.mid")
    return FileResponse(path, media_type="audio/midi", filename=f"{project_id}.mid")


@app.get("/api/projects/{project_id}/report.pdf")
def get_report_pdf(project_id: str) -> FileResponse:
    path = public_asset_path(project_id, "report.pdf")
    return FileResponse(path, media_type="application/pdf", filename=f"{project_id}-analysis.pdf")


@app.get("/api/projects/{project_id}/assets/{filename}")
def get_asset(project_id: str, filename: str) -> FileResponse:
    path = public_asset_path(project_id, filename)
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)
