from __future__ import annotations

import html
import json
import mimetypes
import os
import shutil
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "projects"
STATIC = ROOT / "static"
MAX_UPLOAD_SIZE = 20 * 1024 * 1024
ALLOWED_SUFFIX = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}
DEMO_OMR_ENV = "ALLOW_DEMO_OMR"


DEMO_MUSICXML = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <work><work-title>无词歌风格钢琴小品</work-title></work>
  <identification><creator type="composer">Demo Composer</creator></identification>
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1"><attributes><divisions>2</divisions><key><fifths>1</fifths></key><time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves><clef number="1"><sign>G</sign><line>2</line></clef><clef number="2"><sign>F</sign><line>4</line></clef></attributes><direction placement="above"><direction-type><words>Andante espressivo</words></direction-type><sound tempo="76"/></direction><note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>D</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><backup><duration>8</duration></backup><note><pitch><step>G</step><octave>2</octave></pitch><duration>4</duration><type>half</type><staff>2</staff></note><note><pitch><step>D</step><octave>3</octave></pitch><duration>4</duration><type>half</type><staff>2</staff></note></measure>
    <measure number="2"><note><pitch><step>E</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>D</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><backup><duration>8</duration></backup><note><pitch><step>E</step><octave>3</octave></pitch><duration>4</duration><type>half</type><staff>2</staff></note><note><pitch><step>B</step><octave>2</octave></pitch><duration>4</duration><type>half</type><staff>2</staff></note></measure>
    <measure number="3"><note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>E</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>D</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><backup><duration>8</duration></backup><note><pitch><step>A</step><octave>2</octave></pitch><duration>4</duration><type>half</type><staff>2</staff></note><note><pitch><step>E</step><octave>3</octave></pitch><duration>4</duration><type>half</type><staff>2</staff></note></measure>
    <measure number="4"><note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><staff>1</staff></note><backup><duration>8</duration></backup><note><pitch><step>G</step><octave>2</octave></pitch><duration>8</duration><type>whole</type><staff>2</staff></note><barline location="right"><bar-style>light-heavy</bar-style></barline></measure>
  </part>
</score-partwise>
"""

DEMO_MIDI_BYTES = bytes(
    [
        77, 84, 104, 100, 0, 0, 0, 6, 0, 0, 0, 1, 1, 224, 77, 84, 114, 107,
        0, 0, 0, 90, 0, 255, 81, 3, 7, 161, 32, 0, 192, 0, 0, 144, 67, 90,
        131, 96, 128, 67, 64, 0, 144, 71, 90, 131, 96, 128, 71, 64, 0, 144,
        74, 90, 131, 96, 128, 74, 64, 0, 144, 71, 90, 131, 96, 128, 71, 64,
        0, 144, 76, 90, 131, 96, 128, 76, 64, 0, 144, 74, 90, 131, 96, 128,
        74, 64, 0, 144, 72, 90, 131, 96, 128, 72, 64, 0, 144, 71, 90, 135,
        64, 128, 71, 64, 0, 255, 47, 0,
    ]
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def project_dir(project_id: str) -> Path:
    return DATA / project_id


def project_path(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def asset_url(project_id: str, filename: str) -> str:
    return f"/api/projects/{project_id}/assets/{filename}"


def demo_omr_enabled() -> bool:
    return os.getenv(DEMO_OMR_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def save_project(project: dict) -> dict:
    directory = project_dir(project["id"])
    directory.mkdir(parents=True, exist_ok=True)
    project["updated_at"] = now()
    project_path(project["id"]).write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    return project


def load_project(project_id: str) -> dict:
    return json.loads(project_path(project_id).read_text(encoding="utf-8"))


def list_projects() -> list[dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    projects = []
    for path in DATA.glob("*/project.json"):
        try:
            projects.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            pass
    return sorted(projects, key=lambda item: item.get("created_at", ""), reverse=True)


def html_from_markdown(markdown: str) -> str:
    output = []
    in_list = False
    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            if in_list:
                output.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{html.escape(line[2:])}</li>")
        else:
            if in_list:
                output.append("</ul>")
                in_list = False
            output.append(f"<p>{html.escape(line)}</p>")
    if in_list:
        output.append("</ul>")
    return "\n".join(output)


def write_pdf(path: Path, project: dict, markdown: str) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate

        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="CNTitle", fontName="STSong-Light", fontSize=20, leading=28, textColor=colors.HexColor("#26312b")))
        styles.add(ParagraphStyle(name="CNHeading", fontName="STSong-Light", fontSize=13, leading=20, spaceBefore=10, textColor=colors.HexColor("#2f5d50")))
        styles.add(ParagraphStyle(name="CNBody", fontName="STSong-Light", fontSize=10.5, leading=17, spaceAfter=5))
        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=18 * mm)
        story = []
        for raw in markdown.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("# "):
                story.append(Paragraph(line[2:], styles["CNTitle"]))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], styles["CNHeading"]))
            elif line.startswith("- "):
                story.append(Paragraph("• " + line[2:], styles["CNBody"]))
            else:
                story.append(Paragraph(line, styles["CNBody"]))
        doc.build(story)
    except Exception:
        fallback = (
            b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            b"4 0 obj << /Length 86 >> stream\nBT /F1 16 Tf 72 760 Td (Quxi AI analysis report generated. Open web report for Chinese text.) Tj ET\nendstream endobj\n"
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
            b"trailer << /Root 1 0 R >>\n%%EOF\n"
        )
        path.write_bytes(fallback)


def analysis_payload() -> dict:
    return {
        "key": "G major / e minor 关系调区域",
        "time_signature": "4/4",
        "tempo": "Andante espressivo",
        "measure_count": 4,
        "part_count": 1,
        "chords": [
            {"measure": 1, "symbol": "G", "function": "主和弦色彩"},
            {"measure": 2, "symbol": "Em", "function": "下中音和弦，带来抒情转暗"},
            {"measure": 3, "symbol": "Am", "function": "预备性和声"},
            {"measure": 4, "symbol": "G", "function": "回到主和声"},
        ],
        "roman_numerals": [
            {"measure": 1, "roman": "I"},
            {"measure": 2, "roman": "vi"},
            {"measure": 3, "roman": "ii"},
            {"measure": 4, "roman": "I"},
        ],
        "phrases": [
            {"label": "a", "measures": "1-2", "description": "主题动机呈示。"},
            {"label": "a'", "measures": "3-4", "description": "回应并收束。"},
        ],
        "texture": ["右手旋律突出", "左手分解和弦/支撑低音", "歌唱性钢琴小品织体"],
        "form_candidates": ["平行乐段", "一段体扩展", "无词歌式小品结构"],
        "caveats": ["当前为本地演示分析，真实 OMR 接入后需基于完整 MusicXML 复核。"],
    }


def report_markdown(project: dict) -> str:
    analysis = project["analysis"]
    recognition = project["recognition"]
    confidence = round(recognition["confidence"] * 100)
    romans = "、".join(f"m.{item['measure']} {item['roman']}" for item in analysis["roman_numerals"])
    form = " / ".join(analysis["form_candidates"])
    warnings = "；".join(recognition["warnings"]) or "未发现关键警告。"
    return f"""# {project['title']} 作品分析报告

## 1. 作品基本信息
- 作品名称：{project['title']}
- 目标乐器：钢琴
- 识别引擎：{recognition['engine']}
- 识别置信度：{confidence}%
- 调性判断：{analysis['key']}
- 拍号：{analysis['time_signature']}
- 速度/表情：{analysis['tempo']}

## 2. 谱面识别说明
系统已将上传谱面转为 MusicXML，并生成 MIDI 供试听核对。当前识别警告：{warnings}

## 3. 调性与拍号分析
当前结构化分析显示作品主要处在 {analysis['key']}，拍号为 {analysis['time_signature']}。正式提交前应结合原谱复核临时升降号和低音进行。

## 4. 曲式结构分析
自动曲式候选为：{form}。从课程作业角度，可以先把作品理解为主题呈示、回应/发展、收束组成的小型钢琴曲结构。

## 5. 和声进行分析
系统提取到的罗马数字线索为：{romans}。这些结果适合作为和声分析初稿，后续需要结合旋律骨干音、低音进行和终止式位置进行人工修订。

## 6. 主题动机与织体分析
作品呈现出 {', '.join(analysis['texture'])} 的特征。右手通常承担歌唱性旋律，左手提供和声支撑或分解和弦音型。

## 7. 演奏难点与练习建议
- 先核对旋律声部，确认句法重音和呼吸位置。
- 左手伴奏保持均匀，避免盖过右手旋律。
- 对疑似转调或离调处，先慢速分手练习，再合手确认和声方向。
- 若 OMR 识别有错音，优先修正关键低音和临时升降号。

## 8. 结论
这份报告可作为音乐学院课程作业初稿：它提供了作品基本信息、识谱说明、调性拍号、曲式候选、和声线索、织体特点和演奏建议。最终版本仍应结合原谱与课堂理论进行人工校订。
"""


def extract_response_text(payload: dict) -> str:
    text = payload.get("output_text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    chunks: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                value = content.get("text")
                if isinstance(value, str):
                    chunks.append(value)
    return "\n".join(chunks).strip()


def generate_openai_report(project: dict) -> tuple[str, str | None]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return report_markdown(project), None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    instructions = (
        "你是一位音乐学院曲式与和声教师。请用中文生成课程作业级作品分析报告，"
        "明确区分“系统识别结果”和“AI 推测内容”。"
    )
    prompt = (
        "请基于下面的识谱和乐理分析 JSON，生成 Markdown 格式中文报告。\n\n"
        "必须使用这 8 个章节：\n"
        "1. 作品基本信息\n"
        "2. 谱面识别说明\n"
        "3. 调性与拍号分析\n"
        "4. 曲式结构分析\n"
        "5. 和声进行分析\n"
        "6. 主题动机与织体分析\n"
        "7. 演奏难点与练习建议\n"
        "8. 结论\n\n"
        "要求：不要编造确定作曲家；不要宣称 OMR 完全准确；"
        "如果数据不足，用“需人工复核”表述。\n\n"
        f"{json.dumps(project, ensure_ascii=False, indent=2)}"
    )
    request_body = json.dumps(
        {
            "model": model,
            "instructions": instructions,
            "input": prompt,
            "max_output_tokens": 2600,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=request_body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
        text = extract_response_text(payload)
        if text:
            return text, None
        return report_markdown(project), "OpenAI 返回了空报告，已改用本地模板。"
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")[:500]
        return report_markdown(project), f"OpenAI API HTTP {exc.code}: {details}"
    except Exception as exc:
        return report_markdown(project), f"OpenAI API 调用失败：{exc}"


class Handler(BaseHTTPRequestHandler):
    server_version = "QuxiDevServer/0.1"

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "http://localhost:3000")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.end_headers()

    def send_json(self, payload, status=200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, detail: str) -> None:
        self.send_json({"detail": detail}, status)

    def parse_multipart_upload(self) -> tuple[str, bytes]:
        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_UPLOAD_SIZE:
            raise ValueError("文件过大，请上传 20MB 以内的谱面。")
        body = self.rfile.read(length)
        if "boundary=" not in content_type:
            raise ValueError("上传格式不正确。")
        boundary = ("--" + content_type.split("boundary=", 1)[1]).encode()
        for part in body.split(boundary):
            if b"Content-Disposition" not in part or b'filename="' not in part:
                continue
            header, data = part.split(b"\r\n\r\n", 1)
            filename = header.split(b'filename="', 1)[1].split(b'"', 1)[0].decode("utf-8", errors="ignore")
            return filename, data.rstrip(b"\r\n-")
        raise ValueError("没有找到上传文件。")

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/":
            self.send_file(STATIC / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/static/"):
            asset = STATIC / path.removeprefix("/static/")
            self.send_file(asset, mimetypes.guess_type(asset.name)[0] or "application/octet-stream")
            return
        if path == "/api/health":
            self.send_json({"status": "ok"})
            return
        if path == "/api/projects":
            self.send_json(list_projects())
            return
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 3 and parts[0] == "api" and parts[1] == "projects":
            project_id = parts[2]
            try:
                if len(parts) == 3:
                    self.send_json(load_project(project_id))
                    return
                if len(parts) == 4 and parts[3] == "musicxml":
                    self.send_file(project_dir(project_id) / "score.musicxml", "application/vnd.recordare.musicxml+xml")
                    return
                if len(parts) == 4 and parts[3] == "midi":
                    self.send_file(project_dir(project_id) / "score.mid", "audio/midi")
                    return
                if len(parts) == 4 and parts[3] == "report.pdf":
                    self.send_file(project_dir(project_id) / "report.pdf", "application/pdf")
                    return
                if len(parts) == 5 and parts[3] == "assets":
                    asset = project_dir(project_id) / parts[4]
                    self.send_file(asset, mimetypes.guess_type(asset.name)[0] or "application/octet-stream")
                    return
            except FileNotFoundError:
                self.send_error_json(404, "项目或文件不存在")
                return
        self.send_error_json(404, "路径不存在")

    def do_POST(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path == "/api/projects":
            self.create_project()
            return
        parts = [part for part in path.split("/") if part]
        if len(parts) == 4 and parts[0] == "api" and parts[1] == "projects":
            project_id = parts[2]
            action = parts[3]
            if action == "recognize":
                self.recognize(project_id)
                return
            if action == "analyze":
                self.analyze(project_id)
                return
            if action == "report":
                self.report(project_id)
                return
        self.send_error_json(404, "路径不存在")

    def create_project(self) -> None:
        try:
            filename, data = self.parse_multipart_upload()
            suffix = Path(filename).suffix.lower()
            if suffix not in ALLOWED_SUFFIX:
                self.send_error_json(400, "仅支持 JPG、PNG、WEBP、TIFF 或 PDF 乐谱文件。")
                return
            project_id = uuid.uuid4().hex[:12]
            directory = project_dir(project_id)
            directory.mkdir(parents=True, exist_ok=True)
            source_name = f"source{suffix}"
            (directory / source_name).write_bytes(data)
            created = now()
            project = {
                "id": project_id,
                "title": Path(filename).stem or "未命名谱面",
                "status": "uploaded",
                "created_at": created,
                "updated_at": created,
                "source_filename": filename,
                "source_url": asset_url(project_id, source_name),
                "source_mime": mimetypes.guess_type(filename)[0] or "application/octet-stream",
                "recognition": None,
                "analysis": None,
                "report": None,
                "error": None,
            }
            self.send_json(save_project(project))
        except Exception as exc:
            self.send_error_json(400, str(exc))

    def recognize(self, project_id: str) -> None:
        try:
            project = load_project(project_id)
            directory = project_dir(project_id)
            project["recognition"] = None
            project["analysis"] = None
            project["report"] = None
            project["error"] = None
            project["status"] = "recognizing"
            save_project(project)
            source = next(directory.glob("source.*"), None)
            if not source:
                raise RuntimeError("找不到上传源文件。")

            if source and source.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}:
                try:
                    from PIL import Image, ImageOps

                    with Image.open(source) as image:
                        image = ImageOps.exif_transpose(image).convert("L")
                        ImageOps.autocontrast(image).save(directory / "preprocessed.png")
                except Exception:
                    shutil.copyfile(source, directory / "preprocessed.png")

            if not demo_omr_enabled():
                raise RuntimeError(
                    f"dev_server.py 只提供演示谱，不执行真实 OMR。"
                    f"请使用 FastAPI 后端并安装 oemer 或 Audiveris；如仅需产品演示，可设置 {DEMO_OMR_ENV}=1。"
                )

            (directory / "score.musicxml").write_text(DEMO_MUSICXML, encoding="utf-8")
            (directory / "score.mid").write_bytes(DEMO_MIDI_BYTES)
            project["title"] = "无词歌风格钢琴小品"
            project["status"] = "recognized"
            project["recognition"] = {
                "musicxml_url": asset_url(project_id, "score.musicxml"),
                "midi_url": asset_url(project_id, "score.mid"),
                "confidence": 0.48,
                "engine": "demo-fallback",
                "warnings": [f"已开启 {DEMO_OMR_ENV}，本次使用内置演示谱；该结果不会反映上传谱面内容。", "正式识谱接入后，请复核小节拍数、调号、临时升降号和连线。"],
                "errors": [],
                "extracted_title": "无词歌风格钢琴小品",
            }
            self.send_json(save_project(project))
        except Exception as exc:
            try:
                project = load_project(project_id)
                project["status"] = "failed"
                project["error"] = str(exc)
                save_project(project)
            except Exception:
                pass
            self.send_error_json(500, str(exc))

    def analyze(self, project_id: str) -> None:
        try:
            project = load_project(project_id)
            project["status"] = "analyzed"
            project["analysis"] = analysis_payload()
            self.send_json(save_project(project))
        except Exception as exc:
            self.send_error_json(500, str(exc))

    def report(self, project_id: str) -> None:
        try:
            project = load_project(project_id)
            if not project.get("analysis"):
                self.send_error_json(400, "请先完成乐理分析。")
                return
            markdown, openai_warning = generate_openai_report(project)
            if openai_warning:
                project.setdefault("recognition", {}).setdefault("warnings", []).append(openai_warning)
            project["status"] = "completed"
            project["report"] = {
                "title": f"{project['title']} 作品分析报告",
                "markdown": markdown,
                "html": html_from_markdown(markdown),
                "pdf_url": asset_url(project_id, "report.pdf"),
                "generated_at": now(),
            }
            write_pdf(project_dir(project_id) / "report.pdf", project, markdown)
            self.send_json(save_project(project))
        except Exception as exc:
            self.send_error_json(500, str(exc))

    def send_file(self, path: Path, media_type: str) -> None:
        if not path.exists():
            raise FileNotFoundError(path)
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
        self.end_headers()
        self.wfile.write(data)


def run() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("曲析 AI dev API running at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    run()
