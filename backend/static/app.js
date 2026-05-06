const API = "";

const statusText = {
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

const stages = [
  ["图片处理与 OMR", "矫正谱面并生成 MusicXML", ["uploaded", "recognizing"], ["recognized", "analyzing", "analyzed", "reporting", "completed"]],
  ["乐谱校验", "原图、电子谱与 MIDI 对照", ["recognized"], ["analyzing", "analyzed", "reporting", "completed"]],
  ["乐理分析", "调性、和声、乐句与曲式线索", ["analyzing"], ["analyzed", "reporting", "completed"]],
  ["中文报告", "生成课程作业级分析稿", ["reporting"], ["completed"]]
];

let project = null;
let recent = [];
let busy = false;

const $ = (id) => document.getElementById(id);

function apiUrl(path) {
  return path || "";
}

async function request(path, options = {}) {
  const response = await fetch(API + path, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `请求失败：${response.status}`);
  }
  return response.json();
}

function setLog(message) {
  const item = document.createElement("div");
  item.className = "log-item";
  item.textContent = message;
  $("log").prepend(item);
  while ($("log").children.length > 6) $("log").lastChild.remove();
}

function setError(message) {
  $("errorText").textContent = message || "";
}

function setBusy(value) {
  busy = value;
  render();
}

function renderStages(status) {
  $("stageGrid").innerHTML = "";
  stages.forEach(([title, text, active, done]) => {
    const el = document.createElement("div");
    el.className = "stage";
    if (active.includes(status)) el.classList.add("active");
    if (done.includes(status)) el.classList.add("done");
    el.innerHTML = `<strong>${title}</strong><span>${text}</span>`;
    $("stageGrid").appendChild(el);
  });
}

async function loadRecent() {
  recent = await request("/api/projects").catch(() => []);
  const list = $("recentList");
  list.innerHTML = "";
  $("recentBlock").hidden = !recent.length;
  recent.slice(0, 4).forEach((item) => {
    const button = document.createElement("button");
    button.className = "log-item";
    button.textContent = `${item.title} · ${statusText[item.status]}`;
    button.addEventListener("click", () => {
      project = item;
      render();
    });
    list.appendChild(button);
  });
}

async function refresh() {
  if (!project) return;
  project = await request(`/api/projects/${project.id}`);
  await loadRecent();
  render();
}

async function fetchXml(url) {
  if (!url) {
    $("xmlPreview").textContent = "等待 MusicXML 识别结果";
    return;
  }
  const text = await fetch(apiUrl(url)).then((response) => response.text());
  $("xmlPreview").textContent = text.slice(0, 9000);
}

function renderProject() {
  $("emptyState").hidden = Boolean(project);
  $("projectPanel").hidden = !project;
  $("reportPanel").hidden = !project?.report;

  if (!project) return;

  $("projectTitle").textContent = project.title;
  $("projectSubtitle").textContent = `${project.source_filename} · ${statusText[project.status]}`;

  const source = $("sourcePreview");
  source.innerHTML = "";
  if (project.source_mime.startsWith("image/")) {
    const img = document.createElement("img");
    img.src = apiUrl(project.source_url);
    img.alt = "上传的原始谱面";
    source.appendChild(img);
  } else {
    source.innerHTML = `<div class="placeholder">PDF 已上传。识谱后可在右侧查看 MusicXML。</div>`;
  }

  $("musicxmlLink").hidden = !project.recognition?.musicxml_url;
  $("musicxmlLink").href = `/api/projects/${project.id}/musicxml`;
  $("pdfLink").hidden = !project.report?.pdf_url;
  $("pdfLink").href = `/api/projects/${project.id}/report.pdf`;

  if (project.recognition) {
    $("recognitionMeta").textContent = `置信度 ${Math.round(project.recognition.confidence * 100)}% · 引擎 ${project.recognition.engine}`;
    $("audioPlayer").hidden = !project.recognition.midi_url;
    $("audioPlaceholder").hidden = Boolean(project.recognition.midi_url);
    if (project.recognition.midi_url) $("audioPlayer").src = apiUrl(project.recognition.midi_url);
    const warnings = [...project.recognition.warnings, ...project.recognition.errors];
    $("warningRow").hidden = !warnings.length;
    $("warnings").innerHTML = warnings.map((item) => `<div class="log-item">${item}</div>`).join("");
    fetchXml(project.recognition.musicxml_url);
  } else {
    $("recognitionMeta").textContent = "待识别";
    $("audioPlayer").hidden = true;
    $("audioPlaceholder").hidden = false;
    $("warningRow").hidden = true;
    $("xmlPreview").textContent = "等待 MusicXML 识别结果";
  }

  if (project.analysis) {
    $("analysisStrip").hidden = false;
    $("analysisStrip").innerHTML = [
      ["调性", project.analysis.key],
      ["拍号", project.analysis.time_signature],
      ["小节", project.analysis.measure_count],
      ["曲式候选", project.analysis.form_candidates.join(" / ")]
    ]
      .map(([label, value]) => `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`)
      .join("");
  } else {
    $("analysisStrip").hidden = true;
  }

  if (project.report) {
    $("reportBody").innerHTML = project.report.html;
    $("reportPdfButton").href = `/api/projects/${project.id}/report.pdf`;
  }
}

function renderButtons() {
  $("fullDemoBtn").disabled = !project || busy;
  $("refreshBtn").disabled = !project || busy;
  $("recognizeBtn").disabled = !project || busy || !["uploaded", "failed"].includes(project.status);
  $("analyzeBtn").disabled = !project || busy || !project.recognition || !["recognized", "failed"].includes(project.status);
  $("reportBtn").disabled = !project || busy || !project.analysis || !["analyzed", "failed"].includes(project.status);
}

function render() {
  $("statusPill").textContent = busy ? "处理中..." : statusText[project?.status || "empty"];
  renderStages(project?.status || "empty");
  renderButtons();
  renderProject();
}

async function upload(file) {
  if (!file) return;
  setBusy(true);
  setError("");
  setLog(`上传 ${file.name}...`);
  try {
    const form = new FormData();
    form.append("file", file);
    project = await request("/api/projects", { method: "POST", body: form });
    setLog("上传完成，等待识谱");
    await loadRecent();
  } catch (error) {
    setError(error.message);
  } finally {
    setBusy(false);
  }
}

async function runAction(label, action) {
  if (!project) return;
  setBusy(true);
  setError("");
  setLog(`${label}...`);
  try {
    project = await request(`/api/projects/${project.id}/${action}`, { method: "POST" });
    setLog(`${label}完成`);
    await loadRecent();
  } catch (error) {
    setError(error.message);
  } finally {
    setBusy(false);
  }
}

async function runFullDemo() {
  if (!project) return;
  setBusy(true);
  setError("");
  try {
    setLog("开始完整处理流程");
    if (!project.recognition) project = await request(`/api/projects/${project.id}/recognize`, { method: "POST" });
    if (!project.analysis) project = await request(`/api/projects/${project.id}/analyze`, { method: "POST" });
    if (!project.report) project = await request(`/api/projects/${project.id}/report`, { method: "POST" });
    setLog("完整报告已生成");
    await loadRecent();
  } catch (error) {
    setError(error.message);
  } finally {
    setBusy(false);
  }
}

$("fileInput").addEventListener("change", (event) => upload(event.target.files[0]));
$("fullDemoBtn").addEventListener("click", runFullDemo);
$("refreshBtn").addEventListener("click", refresh);
$("recognizeBtn").addEventListener("click", () => runAction("识谱", "recognize"));
$("analyzeBtn").addEventListener("click", () => runAction("乐理分析", "analyze"));
$("reportBtn").addEventListener("click", () => runAction("报告生成", "report"));

loadRecent().then(() => {
  project = recent[0] || null;
  render();
});
