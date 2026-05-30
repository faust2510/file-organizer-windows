@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo 妈妈文件整理助手 - Windows 打包脚本
echo ========================================
echo.

:: 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python！
    echo 请先安装 Python 3.8+：https://www.python.org/downloads/
    echo 安装时记得勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/5] 检查 Python 环境...
python --version
echo.

:: 创建虚拟环境
echo [2/5] 创建虚拟环境...
if not exist "venv_build" (
    python -m venv venv_build
    echo 虚拟环境创建成功
) else (
    echo 虚拟环境已存在，跳过创建
)
echo.

:: 激活虚拟环境
echo [3/5] 激活虚拟环境并安装依赖...
call venv_build\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install flet send2trash pyinstaller --quiet
echo 依赖安装完成
echo.

:: 清理旧的打包文件
echo [4/5] 清理旧文件...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec
echo 清理完成
echo.

:: 打包
echo [5/5] 正在打包为 exe（可能需要 1-3 分钟）...
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
    main_flet.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请检查错误信息。
    pause
    exit /b 1
)

:: 创建快捷启动脚本
echo @echo off > "dist\妈妈文件整理助手\启动.bat"
echo start "" "妈妈文件整理助手.exe" >> "dist\妈妈文件整理助手\启动.bat"

echo.
echo ========================================
echo 打包完成！
echo.
echo 可执行文件位置：
echo   dist\妈妈文件整理助手\妈妈文件整理助手.exe
echo.
echo 发给妈妈使用：
echo   1. 把整个 "dist\妈妈文件整理助手" 文件夹压缩成 zip
echo   2. 发送 zip 文件
echo   3. 妈妈解压后双击 "妈妈文件整理助手.exe" 即可使用
echo ========================================
echo.
pause
