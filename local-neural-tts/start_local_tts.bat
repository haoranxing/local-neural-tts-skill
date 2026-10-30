@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动本地神经语音控制台（首次会加载模型，请稍候）...
start "" pythonw "%~dp0scripts\bridge_server.py"
timeout /t 4 >nul
start http://localhost:8778
echo 已在浏览器打开 http://localhost:8778
echo 若页面显示「无法连接」，稍等几十秒让引擎加载完成，然后刷新页面。
exit /b 0
