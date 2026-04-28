@echo off
chcp 65001 >nul
title 车载传感器测试系统 - 启动器

REM ============================================================
REM   车载环境传感器自动化测试系统 - 一键启动脚本
REM   说明：自动启动后端服务、前端服务和传感器模拟器
REM ============================================================

REM 设置虚拟环境路径（如果换电脑需修改这一行）
set VENV_PATH=X:\Code Projects\pyven\.venv

REM 设置项目路径（自动获取脚本所在目录）
set PROJECT_ROOT=%~dp0

echo.
echo ================================================
echo   基于MQTT的车载环境传感器测试系统
echo ================================================
echo   项目目录: %PROJECT_ROOT%
echo   虚拟环境: %VENV_PATH%
echo ================================================
echo.

REM 检查虚拟环境是否存在
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo [错误] 找不到虚拟环境: %VENV_PATH%
    echo 请检查 start.bat 中的 VENV_PATH 配置
    pause
    exit /b 1
)

echo [1/3] 正在启动后端服务 (FastAPI + Uvicorn) ...
start "后端服务 - FastAPI" cmd /k "call "%VENV_PATH%\Scripts\activate.bat" && cd /d "%PROJECT_ROOT%backend" && echo [后端服务启动中...] && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM 等待 3 秒，让后端先启动
timeout /t 3 /nobreak >nul

echo [2/3] 正在启动传感器模拟器 ...
start "传感器模拟器" cmd /k "call "%VENV_PATH%\Scripts\activate.bat" && cd /d "%PROJECT_ROOT%backend" && echo [模拟器启动中...] && python sensor_simulator.py"

REM 等待 2 秒
timeout /t 2 /nobreak >nul

echo [3/3] 正在启动前端服务 (Vite) ...
start "前端服务 - Vite" cmd /k "cd /d "%PROJECT_ROOT%frontend" && echo [前端服务启动中...] && npm run dev"

echo.
echo ================================================
echo   所有服务已启动，请查看对应的窗口
echo ================================================
echo.
echo   后端 API 文档: http://localhost:8000/docs
echo   前端访问地址: http://localhost:5173
echo.
echo   关闭服务请直接关闭对应的命令行窗口
echo ================================================
echo.

pause