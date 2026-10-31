---
name: local-neural-tts
description: 本地离线神经语音（TTS）合成与可视化控制台。基于 Qwen3-TTS 1.7B（OpenVINO INT8，CPU 推理），支持中文/英文/日文/韩文及默认/东北话/四川话三种音色，完全离线、不耗积分、数据不出本机。用于把文字转成自然语音（配音、解说、短视频旁白等），并提供浏览器控制台（在线试听+下载 WAV）。仅支持 Windows。
---

# 本地神经语音合成（local-neural-tts）

把文字转成高质量神经语音的**完全离线**方案。底层是 Qwen3-TTS 1.7B（OpenVINO INT8 量化，CPU 推理），
自带一个浏览器控制台（试听 / 下载 WAV），也可被直接调接口批量合成。

## 何时使用
- 用户要"本地配音 / 文字转语音 / TTS / 神经语音 / 语音合成"，且强调**离线、不耗积分、数据不出本机**。
- 给短视频、课程、演示做旁白 / 解说配音。
- 需要换音色（默认温柔女声 / 东北话 / 四川话）或换语言（中/英/日/韩）。

## 环境前提
- **必须**：WorkBuddy（本 skill 的运行容器）+ Windows 系统（推理引擎用 Windows 命名管道）。
- **首次使用需联网**：自动建 Python venv 并下载依赖与模型（~1.5GB 模型，整体占用约数 GB 磁盘）。
- 运行时占 **~5.4GB 内存**（CPU 推理）；机器太弱会慢。
- 模型 / venv 默认落在 `C:\Users\<你>\.openvino`（本机已用目录 junction 转到 D 盘，**C 盘零占用**）。

## SKILL 目录（SKILL_ROOT）
用户级：`~/.workbuddy/skills/local-neural-tts`
（Windows 展开为 `C:\Users\<用户名>\.workbuddy\skills\local-neural-tts`）
脚本在 `SKILL_ROOT/scripts/`，网页在 `SKILL_ROOT/assets/index.html`。

## Agent 操作步骤
按下面顺序执行：

1. **探测是否已安装**
   检查 venv 是否存在：`SKILL_ROOT/scripts/../..` 对应的 `venv` 实际路径为
   `<用户主目录>/.openvino/venv/t2i-tts/Scripts/python.exe`（Windows）。
   或运行：`python SKILL_ROOT/scripts/install_env.py --dry` 前的存在性判断——
   更简单：直接尝试启动 bridge，由它在状态里区分 `not_installed` / `starting` / `running`。

2. **若未安装（首次）**：运行自举脚本（会联网下载依赖+建 venv，约几分钟）：
   ```
   python SKILL_ROOT/scripts/install_env.py
   ```
   装好后无需再跑。

3. **启动控制台（后台常驻）**：
   ```
   python SKILL_ROOT/scripts/bridge_server.py
   ```
   它会自动拉起本地推理引擎（`server.py`），并在 `http://localhost:8778` 提供网页与接口。
   用 **后台方式** 启动（不要阻塞对话），日志在 `<用户主目录>/.openvino/log/tts-web-bridge.log`。

4. **等待引擎就绪**：轮询 `GET http://localhost:8778/api/status`，
   直到返回 `state=running`（首次加载模型约 30–60 秒，期间 `state=starting/loading/downloading`）。
   引擎日志可看 `GET http://localhost:8778/api/engine-log`。

5. **两种服务模式，按需选择**：
   - **A. 浏览器控制台（推荐给用户自助）**：
     告诉用户访问 `http://localhost:8778`（或直接用系统命令打开浏览器）。
     页面支持：粘贴文本、选音色/语言、在线试听、下载 WAV、看引擎状态、停止引擎。
     注意：点「停止引擎」后引擎**不会自动重启**，按钮会切换为「🚀 启动引擎」，
     需要时再手动点一次重新拉起（对应 `POST /api/start`）。
   - **B. 直接合成（用户给文本，你帮他出文件）**：
     调用 `POST http://localhost:8778/api/tts`，JSON 体：
     ```json
     {"text":"要合成的文本","voice":"default","language":"Chinese"}
     ```
     成功返回 `audio/wav` 二进制 + 响应头 `X-TTS-Duration / X-TTS-RTF / X-TTS-Voice`。
     把返回的 WAV 保存到用户指定路径（或 `SKILL_ROOT/assets/outputs/`），并告知文件路径与时长。

## 参数说明
- `voice`（音色）：`default`（默认温柔女声）/ `dongbei`（东北话/大连话）/ `sichuan`（四川话）。
- `language`（语言）：`Chinese` / `English` / `Japanese` / `Korean` / `Auto`。
- 文本上限 **2000 字**。

## 性能与体验（务必提前告知用户）
- **CPU 推理，非 GPU**：首句含模型编译约 1–2 分钟；之后复用常驻引擎，单句约 **35–40 秒**。
  比云端 TTS 慢是预期内的，换来"完全离线、不耗积分、可换音色"。
- 引擎常驻占 ~5.4GB 内存；不用时调用 `POST /api/shutdown` 或点页面「停止引擎」释放。
  停止后引擎保持停止（不会自动重启）；需要恢复时调用 `POST /api/start` 或点页面「🚀 启动引擎」。

## HTTP 接口速查（bridge_server.py，端口 8778）
- `GET  /api/status`     引擎状态（state: not_installed / loading / running / stopped）
- `POST /api/tts`        合成语音（返回 WAV 字节 + 元信息头）
- `GET  /api/engine-log` 引擎日志尾部（加载进度）
- `POST /api/shutdown`   停止引擎并释放内存（设置 manual_stop，之后**不会自动重启**）
- `POST /api/start`      手动重新拉起引擎（清除 manual_stop 标志）

## 注意事项 / 合规
- 本 skill 提供的是高仿真人声合成，**属深度合成技术**。若对外发布合成语音，请遵守当地法规
  （显著标识、不用于诈骗/冒用他人声音等）。
- 仅支持 Windows（推理引擎依赖 Windows 命名管道）；Linux/macOS 暂不支持。
- 不要删除 `<用户主目录>/.openvino` 下的 venv 与模型，否则需重新下载。
