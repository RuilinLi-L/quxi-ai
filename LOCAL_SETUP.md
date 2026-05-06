# 曲析 AI 本地运行说明

本文档记录在 Windows 本地启动曲析 AI 的完整步骤。项目需要同时启动后端和前端：后端负责上传、OMR 识谱、乐理分析和报告生成；前端负责浏览器界面。

## 目录约定

以下命令默认项目位于：

```powershell
D:\code\Projects\quxiai
```

如果你的项目目录不同，请把命令里的路径替换成自己的实际路径。建议项目路径使用英文，避免部分 OMR / OpenCV 依赖在 Windows 下读取中文路径失败。

## 运行前准备

需要本机已安装：

- Anaconda，本文示例路径为 `D:\Anaconda3`
- Node.js / npm
- Git 可选，仅用于拉取代码

真实 OMR 识别需要 Python 包 `oemer`。如果只做产品演示，可以开启 `ALLOW_DEMO_OMR=1` 使用内置演示谱，但该结果不会反映上传谱面内容。

## 第一次配置后端

打开 PowerShell，执行：

```powershell
cd D:\code\Projects\quxiai\backend

$env:Path = "D:\Anaconda3;D:\Anaconda3\Scripts;D:\Anaconda3\Library\bin;$env:Path"
$Conda = "D:\Anaconda3\Scripts\conda.exe"

& $Conda create -n quxiai python=3.10 -y

& "D:\Anaconda3\envs\quxiai\python.exe" -m pip install --upgrade pip
& "D:\Anaconda3\envs\quxiai\python.exe" -m pip install -r requirements.txt
& "D:\Anaconda3\envs\quxiai\python.exe" -m pip install oemer
```

说明：

- `$env:Path` 这一行很重要，用完整路径调用旧版 Anaconda 时，需要把 `D:\Anaconda3\Library\bin` 加进当前窗口 PATH，否则可能出现 SSL 模块不可用。
- `quxiai` 是本项目的 Python 环境名。
- 不需要使用 `conda activate`。本文档直接调用环境里的 `python.exe`，更稳定。

## 启动后端

每次运行后端，打开一个 PowerShell，执行：

```powershell
cd D:\code\Projects\quxiai\backend

$env:Path = "D:\Anaconda3\envs\quxiai;D:\Anaconda3\envs\quxiai\Scripts;$env:Path"

& "D:\Anaconda3\envs\quxiai\python.exe" -m uvicorn app.main:app --reload --port 8000
```

看到类似下面的信息，说明后端已启动：

```text
Uvicorn running on http://127.0.0.1:8000
```

后端窗口不要关闭，保持运行。

## 启动前端

另开一个 PowerShell，执行：

```powershell
cd D:\code\Projects\quxiai\frontend

npm install
npm run dev
```

然后打开浏览器访问：

```text
http://127.0.0.1:3000
```

如果 `3000` 端口被占用，可以临时换端口：

```powershell
npx next dev -H 127.0.0.1 -p 3001
```

然后访问：

```text
http://127.0.0.1:3001
```

## 正常使用流程

1. 保持后端窗口运行在 `8000` 端口。
2. 保持前端窗口运行在 `3000` 端口。
3. 浏览器打开 `http://127.0.0.1:3000`。
4. 上传钢琴谱图片或 PDF。
5. 点击识谱、分析或一键生成报告。

第一次运行 `oemer` 可能较慢，模型加载和识别都需要等待。若本机 ONNX Runtime 没有可用的 CUDA / cuDNN，`oemer` 会回落到 CPU 推理，单页谱面可能需要 5-10 分钟。

## 检查 OMR 是否可用

在后端环境中检查：

```powershell
cd D:\code\Projects\quxiai\backend

$env:Path = "D:\Anaconda3\envs\quxiai;D:\Anaconda3\envs\quxiai\Scripts;$env:Path"

oemer --help
```

如果能看到帮助信息，说明后端可以检测到 `oemer`。

如果 PowerShell 能运行 `oemer --help`，但后端仍提示未检测到引擎，可以显式指定可执行文件：

```powershell
$env:OEMER_PATH = "D:\Anaconda3\envs\quxiai\Scripts\oemer.EXE"
```

## 启用 oemer CUDA 加速

本机有 NVIDIA 显卡时，`oemer` 仍需要在 Python 环境中找到 ONNX Runtime GPU 所需的 CUDA 12 / cuDNN 9 DLL。项目会自动在当前 Conda 的兄弟环境中查找 `Lib\site-packages\torch\lib`；如果找到了完整 DLL，会在运行 `oemer` 前自动预加载。

如果需要手动指定 DLL 目录，可以启动后端前设置：

```powershell
$env:OEMER_CUDA_DLL_DIR = "D:\Anaconda3\envs\base-llm\Lib\site-packages\torch\lib"
```

如果临时需要关闭 CUDA 预加载，使用：

```powershell
$env:OEMER_PRELOAD_CUDA = "0"
```

## 调整真实 OMR 超时

后端默认给 `oemer` 600 秒、`Audiveris` 300 秒。CPU 推理较慢或谱面较复杂时，可以在启动后端前调高：

```powershell
$env:OEMER_TIMEOUT_SECONDS = "600"
# 或统一设置所有 OMR 引擎超时：
$env:OMR_TIMEOUT_SECONDS = "600"
```

项目默认会跳过 `oemer` 自带去倾斜步骤，以减少清晰扫描谱在 CPU 环境中的卡顿。如果上传的是明显倾斜的照片，可以启动后端前打开：

```powershell
$env:OEMER_ENABLE_DESKEW = "1"
```

`oemer` 运行时会在对应项目目录内创建 ASCII 名称的临时识别目录，结束后自动清理。这样可以避开部分 Windows 图像库读取中文路径失败的问题。

## 仅做演示时跳过真实 OMR

如果本机暂时没有真实 OMR 环境，又只需要展示流程，可以启动后端前设置：

```powershell
cd D:\code\Projects\quxiai\backend

$env:ALLOW_DEMO_OMR = "1"
$env:Path = "D:\Anaconda3\envs\quxiai;D:\Anaconda3\envs\quxiai\Scripts;$env:Path"

& "D:\Anaconda3\envs\quxiai\python.exe" -m uvicorn app.main:app --reload --port 8000
```

注意：演示 OMR 使用内置固定谱，不代表上传谱面的真实识别结果。

## 常见问题

### `conda` 无法识别

本机没有把 Conda 加进 PATH。本文档不直接使用 `conda` 命令，而是使用：

```powershell
$Conda = "D:\Anaconda3\Scripts\conda.exe"
& $Conda create -n quxiai python=3.10 -y
```

如果你的 Anaconda 不在 `D:\Anaconda3`，先找到实际路径，再替换命令。

### Conda 报 SSL module is not available

先在当前 PowerShell 加入 Anaconda 的必要路径：

```powershell
$env:Path = "D:\Anaconda3;D:\Anaconda3\Scripts;D:\Anaconda3\Library\bin;$env:Path"
```

然后重新执行 `conda create`。

### `python -m venv` 创建失败

旧版 Anaconda 自带 Python 的 `venv` 可能缺文件。不要用 `.venv`，按本文档使用 Conda 环境 `quxiai`。

### `真实 OMR 识别失败：未检测到 oemer`

启动后端前确认 PATH 包含环境目录：

```powershell
$env:Path = "D:\Anaconda3\envs\quxiai;D:\Anaconda3\envs\quxiai\Scripts;$env:Path"
$env:OEMER_PATH = "D:\Anaconda3\envs\quxiai\Scripts\oemer.EXE"
```

并确认安装过：

```powershell
& "D:\Anaconda3\envs\quxiai\python.exe" -m pip install oemer
```

### `listen EADDRINUSE: address already in use 127.0.0.1:3000`

说明前端端口 `3000` 被占用。可以直接访问 `http://127.0.0.1:3000` 看是否已有前端在运行，或换端口：

```powershell
npx next dev -H 127.0.0.1 -p 3001
```

### OMR 读取图片路径失败

项目路径建议使用英文，例如：

```text
D:\code\Projects\quxiai
```

避免中文路径导致部分 Windows 图像处理库读取文件失败。

## 前端正式编译

如果需要构建前端生产版本：

```powershell
cd D:\code\Projects\quxiai\frontend

npm install
npm run build
npm run start
```
