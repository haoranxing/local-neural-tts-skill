"""本地神经语音 Skill —— 环境自举脚本（跨平台）。

一次性运行：创建 Python 3.12 虚拟环境、安装推理依赖（OpenVINO / torch / qwen-tts 等）。
模型权重（~1.5GB）会在首次启动引擎时自动从 ModelScope 下载，无需本脚本预先下载。

用法：
  python install_env.py            # 自动探测 / 获取 Python 3.12 并安装
  python install_env.py --python D:/path/python.exe   # 指定已有 Python 3.12

注意：
  - 需要联网（下载依赖包与模型）。
  - 依赖 openvino>=2026.2 目前无 cp313 wheels，必须用 Python 3.12（不支持 3.13）。
  - 产物位置：<用户主目录>/.openvino/venv/t2i-tts（Windows 即 USERPROFILE\\.openvino）。
    想改到其他盘请用目录 junction，不要直接改路径。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

OPENVINO_ROOT = Path.home() / ".openvino"
VENV_DIR = OPENVINO_ROOT / "venv" / "t2i-tts"
SKILL_ROOT = Path(__file__).resolve().parent.parent
REQ_FILE = SKILL_ROOT / "requirements.txt"
PYTHON_VERSION = "3.12"
NUGET_PY_URL = "https://www.nuget.org/api/v2/package/python/3.12.10"
PIP_MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"


def log(msg: str) -> None:
    print(f"[install] {msg}", flush=True)


def run(cmd, **kw):
    log("运行: " + " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, **kw)


def find_system_python() -> str | None:
    candidates = [
        f"python{PYTHON_VERSION}",
        f"python{PYTHON_VERSION.replace('.', '')}",
        "py",
    ]
    for name in candidates:
        exe = shutil.which(name)
        if not exe:
            continue
        # 用 `py -3.12` 形式验证版本
        try:
            if name == "py":
                out = subprocess.run([exe, f"-{PYTHON_VERSION}", "--version"],
                                     capture_output=True, text=True, timeout=20)
                if out.returncode != 0:
                    continue
                return f'{exe} -{PYTHON_VERSION}'
            out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20)
            if out.returncode == 0 and PYTHON_VERSION in out.stdout + out.stderr:
                return exe
        except Exception:
            continue
    return None


def fetch_python_via_nuget(target: Path) -> str:
    """Windows 兜底：从 nuget 下载内嵌 Python 3.12 并解压到 target。"""
    target.mkdir(parents=True, exist_ok=True)
    nupkg = target / "python.3.12.10.nupkg"
    log(f"从 nuget 下载 Python {PYTHON_VERSION}（Windows 兜底）: {NUGET_PY_URL}")
    urlretrieve(NUGET_PY_URL, nupkg)
    log("解压 nupkg ...")
    with zipfile.ZipFile(nupkg) as z:
        z.extractall(target)
    nupkg.unlink()
    # nupkg 内 python 在 tools/ 下
    py = target / "tools" / "python.exe"
    if not py.exists():
        raise RuntimeError("nuget python 解压后未找到 tools/python.exe")
    return str(py)


def get_python(explicit: str | None) -> str:
    if explicit:
        if not Path(explicit).exists():
            raise RuntimeError(f"指定的 Python 不存在: {explicit}")
        return explicit
    found = find_system_python()
    if found:
        log(f"检测到系统 Python: {found}")
        return found
    if os.name == "nt":
        log("系统无 Python 3.12，尝试 nuget 下载（需联网）")
        return fetch_python_via_nuget(OPENVINO_ROOT / "python312")
    raise RuntimeError(
        "未找到 Python 3.12。请先安装 Python 3.12（https://www.python.org）或 "
        "用 --python 指定解释器路径。"
    )


def make_venv(python: str) -> str:
    venv_py = (VENV_DIR / "Scripts" / "python.exe") if os.name == "nt" else (VENV_DIR / "bin" / "python")
    if venv_py.exists():
        log(f"venv 已存在: {VENV_DIR}")
        return str(venv_py)
    VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
    run([python, "-m", "venv", str(VENV_DIR)])
    return str(venv_py)


def pip_install(venv_py: str) -> None:
    # 升级 pip 并用清华镜像安装依赖
    run([venv_py, "-m", "pip", "install", "--upgrade", "pip", "-i", PIP_MIRROR])
    run([venv_py, "-m", "pip", "install", "-r", str(REQ_FILE), "-i", PIP_MIRROR])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=None, help="指定已有 Python 3.12 解释器路径")
    args = ap.parse_args()

    log("开始安装本地神经语音运行环境 …")
    python = get_python(args.python)
    venv_py = make_venv(python)
    pip_install(venv_py)
    log("依赖安装完成。")

    # 校验关键包可导入
    try:
        subprocess.run([venv_py, "-c", "import openvino, torch, qwen_tts; print('import ok')"],
                       check=True)
    except subprocess.CalledProcessError:
        log("警告：关键包导入校验失败，请检查上方安装日志。")
        return 1

    log("✅ 环境就绪。模型权重会在首次启动引擎时自动下载（~1.5GB）。")
    log(f"下一步：运行 scripts/bridge_server.py 启动控制台，浏览器访问 http://localhost:8778")
    return 0


if __name__ == "__main__":
    sys.exit(main())
