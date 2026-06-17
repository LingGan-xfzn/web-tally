@echo off
chcp 65001 >nul
title web-telly - 潍坊工商融媒体中心
cd /d "%~dp0"
python gui_server.py
pause
