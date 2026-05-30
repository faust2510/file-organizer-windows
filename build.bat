@echo off
echo === 妈妈文件整理助手 - 打包脚本 ===
echo.

echo [1/3] 安装依赖...
pip install -r requirements.txt

echo.
echo [2/3] 打包为 exe...
pyinstaller --onefile --windowed --name "妈妈文件整理助手" main.py

echo.
echo [3/3] 完成！
echo 输出文件: dist\妈妈文件整理助手.exe
echo.
pause
