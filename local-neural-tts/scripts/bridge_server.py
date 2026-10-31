"""本地神经语音 Web 控制台 —— 桥接服务（纯标准库，无外部依赖）。

职责：
  1. 自动拉起 / 复用本地 Qwen3-TTS 推理引擎（server.py，命名管道 \\.\\pipe\\tts）。
  2. 把引擎暴露为浏览器可用的 HTTP 接口：
       GET  /                -> 控制台页面 index.html
       GET  /api/status      -> 引擎状态（state/device/uptime/pid）
       POST /api/tts         -> 合成语音，返回 WAV 字节 + 元信息头
       GET  /api/engine-log  -> 引擎日志尾部（加载进度）
       POST /api/shutdown    -> 关闭引擎（释放 ~5.4GB 内存）
  3. 所有产物默认落在用户级 ~/.openvino（本机已 junction 到 D 盘，C 盘零占用）。

说明：本机模型根固定在 用户主目录/.openvino（Windows 即 USERPROFILE\\.openvino）。
若想改到其他盘，请用目录 junction（如 mklink /J C:\\Users\\<你>\\.openvino D:\\openvino），
不要直接改环境变量，否则引擎与 venv 路径会不一致。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from multiprocessing.connection import Client
from pathlib import Path

# ----------------------------- 路径配置（可移植） -----------------------------
SKILL_ROOT = Path(__file__).resolve().parent.parent
PIPE_ADDRESS = r"\\.\pipe\tts"
AUTHKEY = b"tts-local"
PORT = 8778
CREATE_NO_WINDOW = 0x08000000

# 模型 / venv / 日志根：固定为用户主目录下的 .openvino（与 server.py 一致）。
OPENVINO_ROOT = Path.home() / ".openvino"
VENV_DIR = OPENVINO_ROOT / "venv" / "t2i-tts"
if os.name == "nt":
    VENV_PY = VENV_DIR / "Scripts" / "pythonw.exe"
else:
    VENV_PY = VENV_DIR / "bin" / "python"
SERVER_PY = SKILL_ROOT / "scripts" / "server.py"
ENGINE_LOG = OPENVINO_ROOT / "log" / "tts-engine.log"
BRIDGE_LOG = OPENVINO_ROOT / "log" / "tts-web-bridge.log"
OUTPUTS_DIR = SKILL_ROOT / "assets" / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
# 确保日志目录存在（避免 FileHandler 因父目录缺失而崩溃）
OPENVINO_ROOT.mkdir(parents=True, exist_ok=True)
(OPENVINO_ROOT / "log").mkdir(parents=True, exist_ok=True)

# CORS：允许页面从任意来源（含 WorkBuddy 预览面板、file://）调用本控制台接口，
# 这样即便页面不是直接由 8778 提供，也能跨端口访问。
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

# 引擎进程句柄（由本桥拉起）
_engine_proc = None
_engine_lock = threading.Lock()
_manual_stop = False  # 用户手动停止后设为 True，阻止轮询自动重启

# ----------------------------- 日志 -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    handlers=[logging.FileHandler(BRIDGE_LOG, encoding="utf-8")],
)
log = logging.getLogger("tts-web-bridge")


# ----------------------------- 引擎管理 -----------------------------
def venv_ready() -> bool:
    return VENV_PY.exists()


def engine_is_up() -> bool:
    """管道存在即视为引擎已在运行。"""
    try:
        c = Client(PIPE_ADDRESS, authkey=AUTHKEY)
        c.close()
        return True
    except Exception:
        return False


def ensure_engine(allow_start: bool = True) -> str:
    """确保引擎运行。返回状态：'running'(已在跑) / 'started'(刚拉起) / 'no_venv'(未安装) / 'stopped'(手动停止)。"""
    global _manual_stop
    if engine_is_up():
        return "running"
    if not venv_ready():
        return "no_venv"
    if _manual_stop:
        return "stopped"
    with _engine_lock:
        global _engine_proc
        if _engine_proc is not None and _engine_proc.poll() is None:
            return "started"
        if not allow_start:
            return "stopped"
        env = dict(os.environ)
        env["LOCAL_TTS_SKILL_ROOT"] = str(SKILL_ROOT)
        log.info("拉起 TTS 引擎: %s %s", VENV_PY, SERVER_PY)
        _engine_proc = subprocess.Popen(
            [str(VENV_PY), str(SERVER_PY), "--log", str(ENGINE_LOG)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0,
            env=env,
        )
    return "started"


def pipe_request(op_dict: dict, timeout: float = 600.0) -> dict | None:
    """向引擎发送一条请求并等待回复。"""
    try:
        conn = Client(PIPE_ADDRESS, authkey=AUTHKEY)
    except Exception as exc:
        return {"ok": False, "error": f"引擎未连接: {exc}"}
    try:
        # Windows 命名管道连接不支持 settimeout，用阻塞接收。
        # 引擎对 status / generate / shutdown 总会回包，不会无限挂起。
        conn.send(op_dict)
        return conn.recv()
    except Exception as exc:
        return {"ok": False, "error": f"通信失败: {exc}"}
    finally:
        try:
            conn.close()
        except Exception:
            pass


def cleanup_old_outputs(max_age_days: int = 1) -> None:
    now = time.time()
    for p in OUTPUTS_DIR.glob("tts_*.wav"):
        try:
            if now - p.stat().st_mtime > max_age_days * 86400:
                p.unlink()
        except OSError:
            pass


# ----------------------------- HTTP 处理 -----------------------------
class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, body: bytes, content_type: str = "application/json; charset=utf-8",
              extra_headers: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, obj: dict):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            html = (SKILL_ROOT / "assets" / "index.html").read_text(encoding="utf-8")
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path == "/api/status":
            self._api_status()
            return
        if path == "/api/engine-log":
            self._api_engine_log()
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/tts":
            self._api_tts()
            return
        if path == "/api/shutdown":
            self._api_shutdown()
            return
        if path == "/api/start":
            self._api_start()
            return
        self._send_json(404, {"ok": False, "error": "not found"})

    # ---- 接口实现 ----
    def _api_status(self):
        if not venv_ready():
            self._send_json(200, {
                "ok": True, "running": False, "state": "not_installed",
                "device": None, "uptime_s": 0, "pid": None,
                "message": "环境尚未安装：请先运行 scripts/install_env.py 完成 venv 与模型下载。",
            })
            return
        ensure_engine(allow_start=False)  # 轮询时不自动重启
        if not engine_is_up():
            self._send_json(200, {
                "ok": True, "running": False, "state": "stopped",
                "device": None, "uptime_s": 0, "pid": None,
                "message": "引擎已停止（点「启动引擎」重新拉起）",
            })
            return
        reply = pipe_request({"op": "status"}, timeout=10.0)
        if not isinstance(reply, dict):
            self._send_json(200, {"ok": True, "running": True, "state": "unknown",
                                  "device": None, "uptime_s": 0, "pid": None})
            return
        state = reply.get("state", "unknown")
        self._send_json(200, {
            "ok": True,
            "running": state == "running",
            "state": state,
            "device": reply.get("loaded_device"),
            "uptime_s": reply.get("uptime_s", 0),
            "pid": reply.get("pid"),
            "model_id": reply.get("loaded_model_id"),
            "message": "" if state == "running" else f"引擎状态: {state}，请稍候…",
        })

    def _api_engine_log(self):
        try:
            lines = Path(ENGINE_LOG).read_text(encoding="utf-8", errors="ignore").splitlines()
            tail = lines[-50:]
        except Exception:
            tail = []
        self._send_json(200, {"ok": True, "lines": tail})

    def _api_tts(self):
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        text = (payload.get("text") or "").strip()
        if not text:
            self._send_json(400, {"ok": False, "error": "请输入要合成的文本"})
            return
        voice = payload.get("voice") or "default"
        language = payload.get("language") or "Chinese"
        if len(text) > 2000:
            self._send_json(400, {"ok": False, "error": "文本过长（上限 2000 字）"})
            return

        if not venv_ready():
            self._send_json(503, {"ok": False, "error": "环境尚未安装，请先运行 install_env.py"})
            return
        # 合成请求时允许自动拉起引擎
        ensure_engine(allow_start=True)
        if not engine_is_up():
            self._send_json(503, {"ok": False, "error": "引擎尚未就绪，请稍候再试"})
            return

        out_path = OUTPUTS_DIR / f"tts_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}.wav"
        reply = pipe_request({
            "op": "generate",
            "prompt": text,
            "voice": voice,
            "language": language,
            "output": str(out_path),
        }, timeout=600.0)

        if not isinstance(reply, dict):
            self._send_json(500, {"ok": False, "error": "引擎无响应"})
            return
        if not reply.get("success"):
            err = reply.get("error") or reply.get("error_code") or "未知错误"
            self._send_json(500, {"ok": False, "error": str(err)})
            return

        try:
            wav_bytes = out_path.read_bytes()
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": f"读取音频失败: {exc}"})
            return

        headers = {
            "X-TTS-Duration": f"{reply.get('duration_s', 0):.2f}",
            "X-TTS-RTF": f"{reply.get('rtf', 0):.2f}",
            "X-TTS-Device": str(reply.get("device") or ""),
            "X-TTS-Voice": str(reply.get("voice") or voice),
        }
        self._send(200, wav_bytes, "audio/wav", extra_headers=headers)
        log.info("合成完成: voice=%s dur=%.2fs rtf=%.2f", voice,
                 reply.get("duration_s", 0), reply.get("rtf", 0))

    def _api_shutdown(self):
        global _manual_stop
        _manual_stop = True
        reply = pipe_request({"op": "shutdown", "timeout": 8.0}, timeout=12.0)
        self._send_json(200, {"ok": True, "reply": reply})

    def _api_start(self):
        """用户主动请求启动引擎（清除 manual_stop 标志）。"""
        global _manual_stop
        _manual_stop = False
        state = ensure_engine(allow_start=True)
        self._send_json(200, {"ok": True, "state": state})

    def log_message(self, fmt, *args):  # 静默默认访问日志
        return


def main() -> int:
    try:
        cleanup_old_outputs()
        ensure_engine()  # 启动时即预拉起引擎（若已安装）
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
        log.info("Web 控制台已启动: http://localhost:%d", PORT)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log.info("收到中断，退出")
        finally:
            server.server_close()
    except Exception as exc:
        log.exception("主循环异常退出: %s", exc)
        import traceback
        traceback.print_exc()
    return 1


if __name__ == "__main__":
    sys.exit(main())
