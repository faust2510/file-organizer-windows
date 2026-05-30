"""妈妈文件整理助手 — 入口"""
import sys
import os

# 打包后资源路径兼容
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from gui import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
