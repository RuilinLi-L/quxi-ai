# 曲析 AI

面向音乐学院学生的拍谱识别与曲式和声分析 Web 原型。用户上传钢琴谱图片或 PDF，系统生成可预览的 MusicXML/MIDI，并输出课程作业级中文作品分析报告。

## 项目结构

```text
backend/   FastAPI 后端：文件上传、OMR 适配、乐理分析、报告与 PDF
frontend/  Next.js 前端：上传工作台、乐谱校验、报告阅读与导出
samples/   演示样例与生成资产
```

## 本地启动

后端：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

如果当前机器的 Python 虚拟环境或 pip 受限，可以直接使用无第三方 Web 框架的演示后端：

```powershell
cd backend
python dev_server.py
```

然后打开 `http://127.0.0.1:8000`。这个入口会直接提供静态前端和同源 API，适合本地项目展示。

前端：

```powershell
cd frontend
npm install
npm run dev
```

打开 `http://localhost:3000`，上传谱面文件后即可处理完整流程。

## 说明

- 默认不会用固定演示谱冒充识谱结果：本机需要安装 `oemer` 或 `Audiveris` 才能执行真实 OMR。仅做产品展示时，可临时设置 `ALLOW_DEMO_OMR=1`，系统会明确标记结果来自内置演示谱，且不会反映上传谱面内容。
- 如果配置了 `OPENAI_API_KEY`，报告生成会尝试调用 OpenAI；未配置时会使用本地模板生成报告。
- 商业化前需要重新审查 OMR 依赖许可证与乐谱版权。
