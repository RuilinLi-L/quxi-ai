from __future__ import annotations

from pathlib import Path


DEMO_MUSICXML = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN"
  "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="4.0">
  <work><work-title>无词歌风格钢琴小品</work-title></work>
  <identification>
    <creator type="composer">Demo Composer</creator>
    <encoding><software>曲析 AI demo fallback</software></encoding>
  </identification>
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions>
        <key><fifths>1</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <staves>2</staves>
        <clef number="1"><sign>G</sign><line>2</line></clef>
        <clef number="2"><sign>F</sign><line>4</line></clef>
      </attributes>
      <direction placement="above">
        <direction-type><words>Andante espressivo</words></direction-type>
        <sound tempo="76"/>
      </direction>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <backup><duration>8</duration></backup>
      <note><pitch><step>G</step><octave>2</octave></pitch><duration>4</duration><type>half</type><stem>down</stem><staff>2</staff></note>
      <note><pitch><step>D</step><octave>3</octave></pitch><duration>4</duration><type>half</type><stem>down</stem><staff>2</staff></note>
    </measure>
    <measure number="2">
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <backup><duration>8</duration></backup>
      <note><pitch><step>E</step><octave>3</octave></pitch><duration>4</duration><type>half</type><stem>down</stem><staff>2</staff></note>
      <note><pitch><step>B</step><octave>2</octave></pitch><duration>4</duration><type>half</type><stem>down</stem><staff>2</staff></note>
    </measure>
    <measure number="3">
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>D</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <backup><duration>8</duration></backup>
      <note><pitch><step>A</step><octave>2</octave></pitch><duration>4</duration><type>half</type><stem>down</stem><staff>2</staff></note>
      <note><pitch><step>E</step><octave>3</octave></pitch><duration>4</duration><type>half</type><stem>down</stem><staff>2</staff></note>
    </measure>
    <measure number="4">
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>2</duration><type>quarter</type><stem>up</stem><staff>1</staff></note>
      <backup><duration>8</duration></backup>
      <note><pitch><step>G</step><octave>2</octave></pitch><duration>8</duration><type>whole</type><stem>down</stem><staff>2</staff></note>
      <barline location="right"><bar-style>light-heavy</bar-style></barline>
    </measure>
  </part>
</score-partwise>
"""


DEMO_MIDI_BYTES = bytes(
    [
        0x4D, 0x54, 0x68, 0x64, 0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x01,
        0x01, 0xE0, 0x4D, 0x54, 0x72, 0x6B, 0x00, 0x00, 0x00, 0x5A, 0x00, 0xFF,
        0x51, 0x03, 0x07, 0xA1, 0x20, 0x00, 0xC0, 0x00, 0x00, 0x90, 0x43, 0x5A,
        0x83, 0x60, 0x80, 0x43, 0x40, 0x00, 0x90, 0x47, 0x5A, 0x83, 0x60, 0x80,
        0x47, 0x40, 0x00, 0x90, 0x4A, 0x5A, 0x83, 0x60, 0x80, 0x4A, 0x40, 0x00,
        0x90, 0x47, 0x5A, 0x83, 0x60, 0x80, 0x47, 0x40, 0x00, 0x90, 0x4C, 0x5A,
        0x83, 0x60, 0x80, 0x4C, 0x40, 0x00, 0x90, 0x4A, 0x5A, 0x83, 0x60, 0x80,
        0x4A, 0x40, 0x00, 0x90, 0x48, 0x5A, 0x83, 0x60, 0x80, 0x48, 0x40, 0x00,
        0x90, 0x47, 0x5A, 0x87, 0x40, 0x80, 0x47, 0x40, 0x00, 0xFF, 0x2F, 0x00,
    ]
)


def write_demo_score(musicxml_path: Path, midi_path: Path) -> None:
    musicxml_path.write_text(DEMO_MUSICXML, encoding="utf-8")
    midi_path.write_bytes(DEMO_MIDI_BYTES)
