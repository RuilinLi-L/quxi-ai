from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models import MusicAnalysis, Project, Report
from ..storage import asset_url


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    html_lines: list[str] = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue
        if stripped.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{html.escape(stripped[2:])}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append(f"<p>{html.escape(stripped)}</p>")
    if in_list:
        html_lines.append("</ul>")
    return "\n".join(html_lines)


def build_local_report(project: Project, analysis: MusicAnalysis) -> str:
    recognition = project.recognition
    confidence = f"{(recognition.confidence if recognition else 0) * 100:.0f}%"
    engine = recognition.engine if recognition else "未知"
    warning_text = "；".join(recognition.warnings if recognition else []) or "未发现关键警告。"
    chords = "、".join(f"m.{item['measure']} {item['roman']}" for item in analysis.roman_numerals[:8]) or "暂无稳定罗马数字结果"
    form = " / ".join(analysis.form_candidates) or "待确认"

    return f"""# {project.title} 作品分析报告

## 1. 作品基本信息
- 作品名称：{project.title}
- 目标乐器：钢琴
- 识别引擎：{engine}
- 识别置信度：{confidence}
- 调性判断：{analysis.key}
- 拍号：{analysis.time_signature}
- 速度/表情：{analysis.tempo}

## 2. 谱面识别说明
系统已将上传谱面转为 MusicXML，并生成 MIDI 供试听核对。当前识别警告：{warning_text}

需要注意的是，OMR 结果可能受到拍照角度、反光、纸张弯曲、谱面标注和分辨率影响。正式提交分析前，应重点检查小节拍数、调号、临时升降号、连线和左右手声部。

## 3. 调性与拍号分析
当前结构化分析显示作品主要处在 {analysis.key}，拍号为 {analysis.time_signature}。若谱面存在中段转调或短暂离调，建议在人工校验 MusicXML 后继续细化。

## 4. 曲式结构分析
自动曲式候选为：{form}。从课程作业角度，可以先把作品理解为由主题呈示、回应/发展、收束组成的小型钢琴曲结构。

## 5. 和声进行分析
系统提取到的罗马数字线索为：{chords}。这些结果适合作为和声分析初稿，后续需要结合旋律骨干音、低音进行和终止式位置进行人工修订。

## 6. 主题动机与织体分析
作品呈现出 {", ".join(analysis.texture)} 的特征。右手通常承担歌唱性旋律，左手提供和声支撑或分解和弦音型，整体接近浪漫主义钢琴小品的写作习惯。

## 7. 演奏难点与练习建议
- 先单独核对旋律声部，确认句法重音和呼吸位置。
- 左手伴奏应保持均匀，避免盖过右手旋律。
- 对疑似转调或离调处，先慢速分手练习，再合手确认和声方向。
- 若 OMR 识别有错音，优先修正关键低音和临时升降号。

## 8. 结论
这份报告可作为音乐学院课程作业初稿：它提供了作品基本信息、识谱说明、调性拍号、曲式候选、和声线索、织体特点和演奏建议。最终版本仍应结合原谱与课堂理论进行人工校订。
"""


async def generate_report(project: Project, analysis: MusicAnalysis) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return build_local_report(project, analysis)

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {
                    "role": "system",
                    "content": "你是一位音乐学院曲式与和声教师。请用中文生成课程作业级作品分析报告，明确区分识别事实和推测。",
                },
                {
                    "role": "user",
                    "content": f"项目：{project.title}\n结构化分析：{analysis.model_dump_json(indent=2)}\n请按 8 个固定章节生成报告。",
                },
            ],
            temperature=0.35,
        )
        return response.choices[0].message.content or build_local_report(project, analysis)
    except Exception:
        return build_local_report(project, analysis)


def build_report_model(project_id: str, title: str, markdown: str) -> Report:
    return Report(
        title=title,
        markdown=markdown,
        html=markdown_to_html(markdown),
        pdf_url=asset_url(project_id, "report.pdf"),
        generated_at=datetime.now(timezone.utc),
    )


def write_report_pdf(path: Path, project: Project, report: Report) -> None:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ChineseTitle", fontName="STSong-Light", fontSize=20, leading=28, spaceAfter=12, textColor=colors.HexColor("#26312b")))
    styles.add(ParagraphStyle(name="ChineseHeading", fontName="STSong-Light", fontSize=13, leading=18, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#2f5d50")))
    styles.add(ParagraphStyle(name="ChineseBody", fontName="STSong-Light", fontSize=10.5, leading=17, spaceAfter=6))

    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    story = [Paragraph(report.title, styles["ChineseTitle"])]
    if project.analysis:
        table = Table(
            [
                ["调性", project.analysis.key, "拍号", project.analysis.time_signature],
                ["小节数", str(project.analysis.measure_count), "识别状态", project.status.value],
            ],
            colWidths=[24 * mm, 58 * mm, 24 * mm, 58 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#edf3ee")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#26312b")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c7d4cc")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend([table, Spacer(1, 8)])

    for raw_line in report.markdown.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("# "):
            continue
        if line.startswith("## "):
            story.append(Paragraph(line[3:], styles["ChineseHeading"]))
        elif line.startswith("- "):
            story.append(Paragraph("• " + line[2:], styles["ChineseBody"]))
        else:
            story.append(Paragraph(line, styles["ChineseBody"]))

    document.build(story)
