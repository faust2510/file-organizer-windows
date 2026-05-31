@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo 妈妈文件整理助手 - 本地测试打包
echo ========================================
echo.

:: 读取版本号
set "VERSION=1.0.0"
if exist "VERSION" (
    set /p VERSION=<VERSION
    for /f "tokens=* delims= " %%a in ("%VERSION%") do set "VERSION=%%a"
)
echo 版本号: %VERSION%
echo.

:: 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python！
    pause
    exit /b 1
)

echo [1/4] 检查 Python 环境...
python --version
echo.

:: 激活虚拟环境（如果存在）
echo [2/4] 准备环境...
if exist "venv_build" (
    call venv_build\Scripts\activate.bat
    echo 使用已有虚拟环境
) else (
    echo 使用系统 Python
)
echo.

:: 清理旧的打包文件
echo [3/4] 清理旧文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec
echo 清理完成
echo.

:: 打包
echo [4/4] 正在打包为 exe...
echo.
pyinstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name "妈妈文件整理助手" ^
    --add-data "config.py;." ^
    --add-data "organizer.py;." ^
    --add-data "search.py;." ^
    --add-data "gui_flet.py;." ^
    --exclude-module tkinter ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module PIL ^
    --exclude-module cv2 ^
    --exclude-module PyQt5 ^
    --exclude-module PySide2 ^
    --exclude-module gtk ^
    main_flet.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

:: 创建快捷启动脚本
echo @echo off > "dist\妈妈文件整理助手\启动.bat"
echo cd /d "%%~dp0" >> "dist\妈妈文件整理助手\启动.bat"
echo start "" "妈妈文件整理助手.exe" >> "dist\妈妈文件整理助手\启动.bat"

echo.
echo ========================================
echo 本地打包完成！
echo 版本: %VERSION%
echo 位置: dist\妈妈文件整理助手\妈妈文件整理助手.exe
echo ========================================
echo.
pause
