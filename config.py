"""分类规则配置"""
import json
import os
from pathlib import Path

# 分类目录名
CATEGORIES = {
    "Word文档": "Word文档",
    "PDF文档": "PDF文档",
    "Excel表格": "Excel表格",
    "PPT演示": "PPT演示",
    "文本文件": "文本文件",
    "图片": "图片",
    "视频": "视频",
    "音乐": "音乐",
    "压缩包": "压缩包",
    "代码": "代码",
    "设计": "设计",
    "安装包": "安装包",
    "其他": "其他",
}

# 用户自定义规则配置文件路径
USER_RULES_FILE = Path.home() / ".file-organizer-rules.json"


def load_user_rules() -> dict:
    """加载用户自定义扩展名映射规则"""
    if USER_RULES_FILE.exists():
        try:
            return json.loads(USER_RULES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_user_rules(rules: dict):
    """保存用户自定义规则到配置文件"""
    USER_RULES_FILE.write_text(
        json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8"
    )

# 扩展名 → 分类映射
EXT_MAP = {
    # Word文档
    ".doc": "Word文档", ".docx": "Word文档",
    # PDF文档
    ".pdf": "PDF文档",
    # Excel表格
    ".xls": "Excel表格", ".xlsx": "Excel表格", ".csv": "Excel表格",
    ".numbers": "Excel表格",
    # PPT演示
    ".ppt": "PPT演示", ".pptx": "PPT演示", ".key": "PPT演示",
    # 文本文件
    ".txt": "文本文件", ".md": "文本文件", ".rtf": "文本文件",
    ".odt": "文本文件", ".epub": "文本文件", ".pages": "文本文件",
    # 图片
    ".jpg": "图片", ".jpeg": "图片", ".png": "图片", ".gif": "图片",
    ".bmp": "图片", ".webp": "图片", ".svg": "图片", ".ico": "图片",
    ".tiff": "图片", ".tif": "图片", ".heic": "图片", ".heif": "图片",
    ".raw": "图片", ".cr2": "图片", ".nef": "图片", ".arw": "图片",
    # 视频
    ".mp4": "视频", ".avi": "视频", ".mkv": "视频", ".mov": "视频",
    ".wmv": "视频", ".flv": "视频", ".webm": "视频", ".m4v": "视频",
    ".mpg": "视频", ".mpeg": "视频", ".3gp": "视频", ".ts": "视频",
    # 音乐
    ".mp3": "音乐", ".wav": "音乐", ".flac": "音乐", ".aac": "音乐",
    ".ogg": "音乐", ".wma": "音乐", ".m4a": "音乐", ".opus": "音乐",
    ".mid": "音乐", ".midi": "音乐",
    # 压缩包
    ".zip": "压缩包", ".rar": "压缩包", ".7z": "压缩包", ".tar": "压缩包",
    ".gz": "压缩包", ".bz2": "压缩包", ".xz": "压缩包", ".zst": "压缩包",
    # 代码
    ".py": "代码", ".js": "代码", ".html": "代码", ".css": "代码",
    ".java": "代码", ".cpp": "代码", ".c": "代码", ".go": "代码",
    ".rs": "代码", ".jsx": "代码", ".tsx": "代码",
    ".rb": "代码", ".php": "代码", ".swift": "代码", ".kt": "代码",
    ".sh": "代码", ".bat": "代码", ".ps1": "代码", ".sql": "代码",
    ".json": "代码", ".xml": "代码", ".yaml": "代码", ".yml": "代码",
    ".toml": "代码", ".ini": "代码", ".cfg": "代码",
    ".mts": "代码", ".m2ts": "代码",
    # 设计
    ".psd": "设计", ".ai": "设计", ".sketch": "设计", ".fig": "设计",
    ".xd": "设计", ".afdesign": "设计", ".afphoto": "设计",
    # 安装包
    ".exe": "安装包", ".msi": "安装包", ".dmg": "安装包", ".apk": "安装包",
    ".deb": "安装包", ".rpm": "安装包", ".appimage": "安装包",
}

# 扫描目录（Windows 路径，macOS 开发时自动适配）
def get_scan_dirs():
    """获取要扫描的目录列表"""
    home = Path.home()
    dirs = [
        home / "Desktop",
        home / "Downloads",
        home / "Documents",
    ]
    return [d for d in dirs if d.exists()]

# 整理目标根目录
def get_target_root():
    """整理目标目录"""
    return Path.home() / "OrganizedFiles"

# 照片整理的目标子目录格式
PHOTO_DATE_FORMAT = "{year}-{month:02d}"

# 忽略的目录名
IGNORE_DIRS = {
    ".", "..", ".git", ".svn", ".DS_Store", "__pycache__",
    "node_modules", ".Trash", ".cache", "$RECYCLE.BIN",
    "System Volume Information",
}

# 忽略的文件扩展名（系统/临时文件）
IGNORE_EXTS = {
    ".tmp", ".temp", ".swp", ".swo", ".lnk", ".url",
}
