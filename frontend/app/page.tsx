"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  FileAudio2,
  FileText,
  Loader2,
  Music2,
  Play,
  RefreshCw,
  Upload,
  WandSparkles
} from "lucide-react";
import { ScoreViewer } from "@/components/ScoreViewer";
import { StageGrid } from "@/components/StageGrid";
import {
  analyzeProject,
  apiUrl,
  createProject,
  getProject,
  listProjects,
  Project,
  recognizeProject,
  reportProject
} from "@/lib/api";

const statusText: Record<string, string> = {
  empty: "等待上传",
  uploaded: "已上传",
  recognizing: "识谱中",
  recognized: "已识谱",
  analyzing: "分析中",
  analyzed: "已分析",
  reporting: "生成报告中",
  completed: "报告完成",
  failed: "处理失败"
};

export default function Home() {
  const [project, setProject] = useState<Project | null>(null);
  const [recent, setRecent] = useState<Project[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [log, setLog] = useState<string[]>([]);

  useEffect(() => {
    listProjects()
      .then((projects) => {
        setRecent(projects.slice(0, 4));
        if (!project && projects.length) {
          setProject(projects[0]);
        }
      })
      .catch(() => undefined);
  }, []);

  const canRecognize = project && ["uploaded", "failed"].includes(project.status);
  const canAnalyze = project && project.recognition && ["recognized", "failed"].includes(project.status);
  const canReport = project && project.analysis && ["analyzed", "failed"].includes(project.status);

  const sourceIsImage = useMemo(() => {
    return project?.source_mime.startsWith("image/") ?? false;
  }, [project]);

  async function refresh(id = project?.id) {
    if (!id) {
      return;
    }
    const fresh = await getProject(id);
    setProject(fresh);
    const projects = await listProjects().catch(() => recent);
    setRecent(projects.slice(0, 4));
  }

  async function runStep(label: string, action: () => Promise<Project>) {
    setBusy(true);
    setError("");
    setLog((items) => [`${label}...`, ...items].slice(0, 6));
    try {
      const next = await action();
      setProject(next);
      setLog((items) => [`${label}完成`, ...items].slice(0, 6));
      await refresh(next.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "操作失败";
      setError(message);
      setLog((items) => [`${label}失败：${message}`, ...items].slice(0, 6));
    } finally {
      setBusy(false);
    }
  }

  async function handleFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setBusy(true);
    setError("");
    setLog([`上传 ${file.name}...`]);
    try {
      const created = await createProject(file);
      setProject(created);
      setLog((items) => ["上传完成，等待识谱", ...items].slice(0, 6));
      await refresh(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setBusy(false);
    }
  }

  async function runFullDemo() {
    if (!project) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      setLog((items) => ["开始完整处理流程", ...items].slice(0, 6));
      let next = project;
      if (!next.recognition) {
        next = await recognizeProject(next.id);
        setProject(next);
      }
      if (!next.analysis) {
        next = await analyzeProject(next.id);
        setProject(next);
      }
      if (!next.report) {
        next = await reportProject(next.id);
        setProject(next);
      }
      setLog((items) => ["完整报告已生成", ...items].slice(0, 6));
      await refresh(next.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "完整流程失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Music2 size={25} />
          </div>
          <div>
            <h1>曲析 AI</h1>
            <p>拍谱识别、乐理结构化分析、课程作业级中文报告</p>
          </div>
        </div>
        <div className="status-pill">
          {busy ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
          {statusText[project?.status ?? "empty"]}
        </div>
      </header>

      <div className="workspace">
        <aside className="panel upload-panel">
          <div className="panel-header">
            <div>
              <h2 className="panel-title">工作台</h2>
              <p className="panel-subtitle">上传钢琴谱图片或 PDF，先跑通识谱到报告的完整闭环。</p>
            </div>
          </div>
          <div className="upload-body">
            <label className="dropzone">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff,application/pdf"
                onChange={(event) => handleFile(event.target.files?.[0])}
              />
              <Upload size={34} />
              <strong>拖入或点击上传谱面</strong>
              <span>建议使用清晰钢琴印刷谱。倾斜、反光、手写标注会被记录为识别风险。</span>
            </label>

            <div className="button-row">
              <button className="primary-button" disabled={!project || busy} onClick={runFullDemo}>
                <WandSparkles size={18} />
                一键生成报告
              </button>
              <button className="secondary-button" disabled={!project || busy} onClick={() => refresh()}>
                <RefreshCw size={18} />
                刷新
              </button>
            </div>

            <div className="button-row">
              <button
                className="secondary-button"
                disabled={!canRecognize || busy}
                onClick={() => project && runStep("识谱", () => recognizeProject(project.id))}
              >
                <FileText size={18} />
                识谱
              </button>
              <button
                className="secondary-button"
                disabled={!canAnalyze || busy}
                onClick={() => project && runStep("乐理分析", () => analyzeProject(project.id))}
              >
                <Music2 size={18} />
                分析
              </button>
              <button
                className="secondary-button"
                disabled={!canReport || busy}
                onClick={() => project && runStep("报告生成", () => reportProject(project.id))}
              >
                <FileText size={18} />
                报告
              </button>
            </div>

            <ul className="hint-list">
              <li>
                <CheckCircle2 size={16} /> 第一版重点支持钢琴印刷谱，复杂手写谱会提示风险。
              </li>
              <li>
                <AlertTriangle size={16} /> 未安装真实 OMR 引擎时，识谱会明确失败；仅需演示固定谱时可设置 ALLOW_DEMO_OMR=1。
              </li>
              <li>
                <FileAudio2 size={16} /> MIDI 用于试听核对，不作为完整谱面语义来源。
              </li>
            </ul>

            {error ? <p className="error">{error}</p> : null}

            <div className="log">
              {log.map((item, index) => (
                <div className="log-item" key={`${item}-${index}`}>
                  {item}
                </div>
              ))}
            </div>

            {recent.length ? (
              <div>
                <p className="panel-subtitle">最近项目</p>
                <div className="log">
                  {recent.map((item) => (
                    <button className="log-item" key={item.id} onClick={() => setProject(item)}>
                      {item.title} · {statusText[item.status]}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </aside>

        <section className="main-grid">
          <StageGrid status={project?.status ?? "empty"} />

          {!project ? (
            <section className="panel empty-state">
              <div>
                <h2>把纸上的钢琴谱变成一份可讲清楚的作品分析</h2>
                <p>
                  首版原型聚焦音乐学院课程作业：拍谱、识谱、试听、提取和声曲式线索，并生成可导出的中文分析报告。
                </p>
              </div>
            </section>
          ) : (
            <>
              <section className="panel">
                <div className="panel-header">
                  <div>
                    <h2 className="panel-title">{project.title}</h2>
                    <p className="panel-subtitle">
                      {project.source_filename} · {statusText[project.status]}
                    </p>
                  </div>
                  <div className="button-row">
                    {project.recognition?.musicxml_url ? (
                      <a className="icon-button" href={apiUrl(`/api/projects/${project.id}/musicxml`)}>
                        <Download size={17} />
                        MusicXML
                      </a>
                    ) : null}
                    {project.report?.pdf_url ? (
                      <a className="primary-button" href={apiUrl(`/api/projects/${project.id}/report.pdf`)} target="_blank">
                        <Download size={17} />
                        PDF
                      </a>
                    ) : null}
                  </div>
                </div>

                <div className="review-grid">
                  <div className="score-source">
                    {sourceIsImage ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={apiUrl(project.source_url)} alt="上传的原始谱面" />
                    ) : (
                      <div className="pdf-placeholder">
                        <FileText size={44} />
                        <p>PDF 已上传。识谱后可在右侧查看电子谱。</p>
                      </div>
                    )}
                  </div>
                  <ScoreViewer musicxmlUrl={project.recognition?.musicxml_url} />
                </div>

                <div className="player-row">
                  <div>
                    <strong>试听核对</strong>
                    <p className="panel-subtitle">
                      置信度 {project.recognition ? `${Math.round(project.recognition.confidence * 100)}%` : "待识别"} · 引擎{" "}
                      {project.recognition?.engine ?? "待选择"}
                    </p>
                  </div>
                  {project.recognition?.midi_url ? (
                    <audio controls src={apiUrl(project.recognition.midi_url)}>
                      <track kind="captions" />
                    </audio>
                  ) : (
                    <button className="secondary-button" disabled>
                      <Play size={17} />
                      等待 MIDI
                    </button>
                  )}
                </div>

                {project.recognition?.warnings.length || project.recognition?.errors.length ? (
                  <div className="player-row">
                    <div className="log">
                      {[...(project.recognition?.warnings ?? []), ...(project.recognition?.errors ?? [])].map((item) => (
                        <div className="log-item" key={item}>
                          {item}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {project.analysis ? (
                  <div className="analysis-strip">
                    <div className="metric">
                      <span>调性</span>
                      <strong>{project.analysis.key}</strong>
                    </div>
                    <div className="metric">
                      <span>拍号</span>
                      <strong>{project.analysis.time_signature}</strong>
                    </div>
                    <div className="metric">
                      <span>小节</span>
                      <strong>{project.analysis.measure_count}</strong>
                    </div>
                    <div className="metric">
                      <span>曲式候选</span>
                      <strong>{project.analysis.form_candidates.join(" / ")}</strong>
                    </div>
                  </div>
                ) : null}
              </section>

              {project.report ? (
                <section className="panel">
                  <div className="panel-header">
                    <div>
                      <h2 className="panel-title">分析报告</h2>
                      <p className="panel-subtitle">系统识别结果与 AI 推测内容已在正文中区分说明。</p>
                    </div>
                    <a className="primary-button" href={apiUrl(project.report.pdf_url)} target="_blank">
                      <Download size={17} />
                      导出 PDF
                    </a>
                  </div>
                  <article className="report-body" dangerouslySetInnerHTML={{ __html: project.report.html }} />
                </section>
              ) : null}
            </>
          )}
        </section>
      </div>
    </main>
  );
}
