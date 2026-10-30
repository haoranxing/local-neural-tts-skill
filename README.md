# local-neural-tts-skill

> WorkBuddy Skill · 本地离线神经语音合成（Qwen3-TTS 1.7B · 浏览器控制台 · Windows）

把开源的 **Qwen3-TTS** 神经语音模型封装成一个完全本地、离线运行的语音合成系统：
你说一句话，它在你自己的电脑上用 CPU 合成自然的中文/英文语音，不联网、不耗积分、不泄露文本。
配套一个**浏览器控制台**，粘贴文字 → 选音色 → 一键生成 → 在线试听 + 下载 WAV。

---

## ✨ 功能特性

- **完全离线**：推理在你本机 CPU 完成，不上传任何文本，不消耗云端积分。
- **神经语音质量**：基于 Qwen3-TTS 1.7B（OpenVINO INT8），自然度远超系统自带 SAPI 机械音。
- **三种音色**（离线可用）：默认（温柔女声）/ 东北话 / 四川话。
- **可视化控制台**：暗色科技风网页，支持文本输入、音色/语言选择、在线试听、下载 WAV、引擎状态显示与一键停机。
- **WebBuddy 内自然语言调用**：在 WorkBuddy 里说"帮我用本地语音合成配音"，AI 自动启动服务并合成。
- **自包含 Skill**：不依赖外部路径，复制到 `~/.workbuddy/skills/` 即可被识别。

---

## 📁 仓库结构

```
local-neural-tts-skill/
├── README.md            # 本文件（项目说明）
├── LICENSE              # MIT 许可证
└── local-neural-tts/    # WorkBuddy Skill 本体（整目录丢进 skills/ 即可）
    ├── SKILL.md             # 技能说明 + 触发词 + 给 AI 的操作步骤
    ├── README-安装.txt       # 面向非 AI 用户的中文安装说明
    ├── scripts/
    │   ├── server.py         # 推理引擎（Qwen3-TTS 1.7B）
    │   ├── bridge_server.py  # HTTP 桥（端口 8778，带 CORS）
    │   ├── install_env.py    # 跨平台环境自举（Python + 依赖）
    │   ├── qwen_3_tts_helper.py / voices.py / model_download.py  # 推理支撑
    ├── assets/
    │   ├── index.html        # 浏览器控制台页面
    │   └── ref/              # 三种音色参考音频（默认/东北话/四川话）
    ├── start_local_tts.bat   # 一键启动器（双击即用）
    ├── info.json             # 模型元数据
    └── requirements.txt      # 依赖清单
```

> ⚠️ 仓库**不含 1.5GB 模型权重**——首次运行时由 `install_env.py` 自动从 ModelScope 下载，所以克隆本仓库很小。

---

## 🚀 安装与食用方法

### 方式 A：作为 WorkBuddy Skill 使用（推荐）

1. 把本仓库克隆/下载后，将 **`local-neural-tts/`** 整个目录复制到：
   - Windows：`C:\Users\<你的用户名>\.workbuddy\skills\`
   - macOS / Linux：`~/.workbuddy/skills/`
2. 打开 WorkBuddy，对 AI 说：
   > “用本地语音合成帮我把这段文案转成配音”
   AI 会自动检测环境 → 必要时安装 → 启动控制台 → 调用接口 → 把 WAV 文件给你。

### 方式 B：手动双击启动（不依赖 AI 对话）

直接双击 `local-neural-tts/start_local_tts.bat`：
→ 自动启动引擎 → 打开浏览器 `http://localhost:8778`
→ 粘贴文字、选音色、点「生成语音」、试听、下载。

详见 `local-neural-tts/README-安装.txt`。

---

## ⚙️ 环境要求

| 项目 | 要求 |
|---|---|
| 操作系统 | **Windows**（推理引擎基于 Windows 命名管道） |
| 客户端 | 需安装 WorkBuddy（仅方式 A 需要） |
| 运行时 | 首次自动拉取 Python 3.12 + OpenVINO / torch / qwen-tts 等依赖 |
| 模型权重 | 首次联网下载 Qwen3-TTS 约 **1.5GB**（ModelScope 源） |
| 磁盘空间 | 建议预留 **5~6GB** |
| 硬件 | CPU 推理（无需显卡）；建议 ≥8 核、内存 ≥8GB（引擎常驻约占 5.4GB） |
| 网络 | 仅首次下载时需要联网 |

**性能**：首次合成需编译模型约 1~2 分钟；之后常驻服务下，单句约 **35~40 秒**（CPU 实时率约 8~9 倍）。

---

## 🔒 合规提示

AI 语音合成属于「深度合成」范畴。若你**对外公开提供**合成语音服务，请遵守《互联网信息服务深度合成管理规定》（算法备案、内容显著标识、用户实名、内容审核等）。**个人自用 / 内部使用无限制**。

---

## 📜 许可证

MIT License · © 2026 冯新（haoranxing）

详见 [LICENSE](./LICENSE)。
