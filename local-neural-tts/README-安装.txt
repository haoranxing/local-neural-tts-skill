本地神经语音合成 Skill · 安装与使用说明
========================================

这是一个 WorkBuddy 技能包（Skill），把开源 Qwen3-TTS 神经语音模型封装成
「浏览器控制台 + 命令行」的本地离线语音合成系统。

【分发给别人怎么用】
1) 把解压出来的 `local-neural-tts` 文件夹，整个复制到：
      Windows：  C:\Users\<你的用户名>\.workbuddy\skills\
      macOS/Linux： ~/.workbuddy/skills/
   也就是：  <skills目录>/local-neural-tts/SKILL.md 这样的结构。
2) 打开 WorkBuddy，让 AI 读这个 skill（首次会自动检测并安装环境）。
   或直接双击 `local-neural-tts/start_local_tts.bat` 启动浏览器控制台。

【前置条件】
- 必须安装 WorkBuddy 客户端（skill 只能在 WorkBuddy 内运行/被识别）。
- Windows 系统（当前版本引擎基于 Windows 命名管道）。
- 首次运行需要联网，自动下载：
    · Python 3.12 运行时（约 15MB）
    · 推理依赖 OpenVino / torch / transformers / qwen-tts 等（约数百 MB）
    · Qwen3-TTS 模型权重（约 1.5GB，ModelScope 源）
  请预留至少 5~6GB 磁盘空间，并保持网络畅通（下载可能需 5~15 分钟）。

【硬件要求】
- CPU 推理（无需显卡）：建议 8 核以上、内存 ≥ 8GB（引擎常驻约占 5.4GB）。
- 首次合成需编译模型约 1~2 分钟，之后单句约 35~40 秒。

【怎么用】
方式 A（推荐）：在 WorkBuddy 里说
    “用本地语音合成帮我把这段文案转成配音”
  AI 会自动启动服务、调用接口、把 wav 文件给你。

方式 B（手动）：双击 `start_local_tts.bat`
    → 自动启动引擎 → 打开浏览器 http://localhost:8778
    → 粘贴文字、选音色（默认 / 东北话 / 四川话）、点生成、试听、下载。

【合规提示】
AI 语音合成属于「深度合成」，若对外公开提供需遵守相关法规
（算法备案、内容显著标识、用户实名、内容审核）。自用 / 内部无限制。

【目录结构】
  SKILL.md            技能说明 + 触发词 + 给 AI 的操作步骤
  scripts/
    server.py         推理引擎（Qwen3-TTS 1.7B）
    bridge_server.py  HTTP 桥（端口 8778，带 CORS）
    install_env.py    跨平台环境自举（Python+依赖）
    qwen_3_tts_helper.py / voices.py / model_download.py  推理支撑模块
  assets/
    index.html        浏览器控制台页面
    ref/              三种音色参考音频（默认 / 东北话 / 四川话）
  start_local_tts.bat 一键启动器
  info.json / requirements.txt  模型元数据 / 依赖清单

【常见问题】
- 控制台显示「无法连接」？ 确认已先运行 start_local_tts.bat，或让 AI 先启动服务。
- 想换音色？ 控制台音色下拉即可；文本接口传 voice=default|dongbeihua|sichuanhua。
- 想停止引擎释放内存？ 控制台内点「停止引擎」，或关掉后台 pythonw 进程。
