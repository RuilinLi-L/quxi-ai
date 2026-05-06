from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models import MusicAnalysis


def _fallback_analysis(reason: str) -> MusicAnalysis:
    return MusicAnalysis(
        key="G major / e minor 关系调区域",
        time_signature="4/4",
        tempo="Andante espressivo",
        measure_count=4,
        part_count=1,
        chords=[
            {"measure": 1, "symbol": "G", "function": "主和弦色彩"},
            {"measure": 2, "symbol": "Em", "function": "下中音和弦，带来抒情转暗"},
            {"measure": 3, "symbol": "Am", "function": "预备性和声"},
            {"measure": 4, "symbol": "G", "function": "回到主和声"},
        ],
        roman_numerals=[
            {"measure": 1, "roman": "I"},
            {"measure": 2, "roman": "vi"},
            {"measure": 3, "roman": "ii"},
            {"measure": 4, "roman": "I"},
        ],
        phrases=[
            {"label": "a", "measures": "1-2", "description": "呈示动机，旋律以上行三度与级进回落为主。"},
            {"label": "a'", "measures": "3-4", "description": "回应并收束，保持同类织体。"},
        ],
        texture=["右手旋律突出", "左手分解和弦/支撑低音", "歌唱性钢琴小品织体"],
        form_candidates=["平行乐段", "一段体扩展", "无词歌式小品结构"],
        caveats=[f"分析使用演示降级结果：{reason}", "正式 OMR 接入后需要以真实 MusicXML 重新计算。"],
    )


def analyze_musicxml(musicxml_path: Path) -> MusicAnalysis:
    try:
        from music21 import chord, converter, key, roman

        score = converter.parse(str(musicxml_path))
        flattened = score.flatten()
        analyzed_key = score.analyze("key")
        key_name = analyzed_key.tonic.name + (" major" if analyzed_key.mode == "major" else " minor")
        time_signature = "未知"
        for ts in flattened.getTimeSignatures():
            time_signature = ts.ratioString
            break

        parts = list(score.parts)
        measures = []
        if parts:
            measures = list(parts[0].getElementsByClass("Measure"))

        chords: list[dict[str, Any]] = []
        roman_numerals: list[dict[str, Any]] = []
        for measure in measures[:24]:
            notes = []
            for part in parts:
                part_measure = part.measure(measure.number)
                if part_measure:
                    notes.extend(part_measure.flatten().notes)
            if not notes:
                continue
            chord_obj = chord.Chord(notes)
            symbol = chord_obj.pitchedCommonName
            chords.append(
                {
                    "measure": measure.number,
                    "symbol": symbol,
                    "function": "由该小节主要音高集合估算",
                }
            )
            try:
                rn = roman.romanNumeralFromChord(chord_obj, analyzed_key)
                roman_numerals.append({"measure": measure.number, "roman": rn.figure})
            except Exception:
                roman_numerals.append({"measure": measure.number, "roman": "待人工确认"})

        measure_count = max((measure.number or 0 for measure in measures), default=len(measures))
        midpoint = max(1, measure_count // 2)

        return MusicAnalysis(
            key=key_name,
            time_signature=time_signature,
            tempo="Andante / 需结合谱面速度术语确认",
            measure_count=measure_count,
            part_count=len(parts),
            chords=chords,
            roman_numerals=roman_numerals,
            phrases=[
                {"label": "A", "measures": f"1-{midpoint}", "description": "主题材料呈示，建议结合谱面分句线复核。"},
                {"label": "A' / B", "measures": f"{midpoint + 1}-{measure_count}", "description": "后半段可能为回应、发展或收束。"},
            ],
            texture=["钢琴大谱表", "旋律加伴奏织体", "和声节奏需要结合 OMR 纠错后复核"],
            form_candidates=["一段体", "二段体", "小型三段体雏形"],
            caveats=["自动曲式判断仅作为课程分析初稿，需要人工结合主题材料确认。"],
        )
    except Exception as exc:
        return _fallback_analysis(str(exc))
