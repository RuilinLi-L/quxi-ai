from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from fastapi import UploadFile

from .models import Project, ProjectStatus


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"


def ensure_storage() -> None:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def project_dir(project_id: str) -> Path:
    return PROJECTS_DIR / project_id


def project_json_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def asset_url(project_id: str, filename: str) -> str:
    return f"/api/projects/{project_id}/assets/{filename}"


def save_project(project: Project) -> Project:
    ensure_storage()
    directory = project_dir(project.id)
    directory.mkdir(parents=True, exist_ok=True)
    project.updated_at = utcnow()
    project_json_path(project.id).write_text(project.model_dump_json(indent=2), encoding="utf-8")
    return project


def load_project(project_id: str) -> Project:
    data = json.loads(project_json_path(project_id).read_text(encoding="utf-8"))
    return Project.model_validate(data)


def list_projects() -> list[Project]:
    ensure_storage()
    projects: list[Project] = []
    for path in PROJECTS_DIR.glob("*/project.json"):
        try:
            projects.append(Project.model_validate_json(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return sorted(projects, key=lambda project: project.created_at, reverse=True)


async def store_upload(project_id: str, upload: UploadFile) -> Path:
    directory = project_dir(project_id)
    directory.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "score").suffix.lower()
    destination = directory / f"source{suffix}"
    with destination.open("wb") as file:
        while chunk := await upload.read(1024 * 1024):
            file.write(chunk)
    return destination


def set_status(project: Project, status: ProjectStatus) -> Project:
    project.status = status
    return save_project(project)


def public_asset_path(project_id: str, filename: str) -> Path:
    path = project_dir(project_id) / filename
    if not path.exists():
        raise FileNotFoundError(filename)
    return path
