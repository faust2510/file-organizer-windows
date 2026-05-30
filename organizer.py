"""核心引擎 — 文件扫描、分类、整理"""
import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from send2trash import send2trash

from config import EXT_MAP, IGNORE_DIRS, IGNORE_EXTS, CATEGORIES, get_target_root, PHOTO_DATE_FORMAT, load_user_rules


@dataclass
class FileInfo:
    path: Path
    size: int
    mtime: float
    ext: str
    category: str = ""
    target_path: Optional[Path] = None


class FileScanner:
    """递归扫描目录，收集文件信息"""

    def __init__(self, ignore_hidden=True, max_depth=10):
        self.ignore_hidden = ignore_hidden
        self.max_depth = max_depth

    def scan(self, dirs: list[Path], progress_cb=None) -> list[FileInfo]:
        """扫描多个目录，返回文件列表"""
        files = []
        for d in dirs:
            if d.exists():
                files.extend(self._scan_dir(d, depth=0, progress_cb=progress_cb))
        return files

    def _scan_dir(self, directory: Path, depth: int, progress_cb=None) -> list[FileInfo]:
        """递归扫描单个目录"""
        if depth > self.max_depth:
            return []

        files = []
        try:
            entries = list(directory.iterdir())
        except (PermissionError, OSError):
            return []

        for entry in entries:
            name = entry.name

            # 跳过隐藏文件/目录
            if self.ignore_hidden and name.startswith('.'):
                continue

            # 跳过忽略的目录
            if entry.is_dir() and name in IGNORE_DIRS:
                continue

            if entry.is_dir():
                files.extend(self._scan_dir(entry, depth + 1, progress_cb))
            elif entry.is_file():
                ext = entry.suffix.lower()
                if ext in IGNORE_EXTS:
                    continue

                try:
                    stat = entry.stat()
                    info = FileInfo(
                        path=entry,
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                        ext=ext,
                    )
                    files.append(info)

                    if progress_cb:
                        progress_cb(len(files), str(entry))
                except (PermissionError, OSError):
                    continue

        return files


class FileClassifier:
    """按扩展名分类文件"""

    def __init__(self):
        self.ext_map = {**EXT_MAP, **load_user_rules()}

    def classify(self, file_info: FileInfo) -> str:
        """返回分类名"""
        ext = file_info.ext
        if ext in self.ext_map:
            return self.ext_map[ext]
        return "其他"

    def classify_batch(self, files: list[FileInfo]) -> list[FileInfo]:
        """批量分类"""
        for f in files:
            f.category = self.classify(f)
        return files


class FileOrganizer:
    """文件整理 — 预览、执行、撤销"""

    def __init__(self, target_root: Path = None):
        self.target_root = target_root or get_target_root()

    def preview(self, files: list[FileInfo]) -> list[tuple[Path, Path]]:
        """生成移动计划 [(src, dst), ...]"""
        plan = []
        seen_targets = set()

        for f in files:
            if not f.category:
                continue

            dst = self._calc_target(f, seen_targets)
            if dst:
                f.target_path = dst
                plan.append((f.path, dst))
                seen_targets.add(str(dst))

        return plan

    def _calc_target(self, f: FileInfo, seen_targets: set) -> Optional[Path]:
        """计算目标路径（不创建目录）"""
        category = f.category
        cat_dir = CATEGORIES.get(category, "Others")

        # 照片按年-月分文件夹
        if category == "图片":
            date = self._get_photo_date(f)
            if date:
                sub = PHOTO_DATE_FORMAT.format(year=date.year, month=date.month)
                target_dir = self.target_root / cat_dir / sub
            else:
                target_dir = self.target_root / cat_dir
        else:
            target_dir = self.target_root / cat_dir

        # 处理重名
        dst = target_dir / f.path.name
        if str(dst) in seen_targets or dst.exists():
            stem = f.path.stem
            suffix = f.path.suffix
            counter = 1
            while dst.exists() or str(dst) in seen_targets:
                dst = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        return dst

    def _get_photo_date(self, f: FileInfo) -> Optional[datetime]:
        """获取照片拍摄日期（EXIF 或 mtime）"""
        try:
            from PIL import Image
            from PIL.ExifTags import Base as ExifBase
            img = Image.open(f.path)
            exif = img._getexif()
            if exif:
                date_str = exif.get(36867)  # DateTimeOriginal
                if date_str:
                    return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        except Exception:
            pass

        # 回退到文件修改时间
        return datetime.fromtimestamp(f.mtime)

    def execute(self, plan: list[tuple[Path, Path]], log_path: Path = None, progress_cb=None) -> dict:
        """执行移动（copy2 + send2trash），返回 {moved: [...], skipped: [...], errors: [...]}"""
        if log_path is None:
            log_path = self.target_root / "organize_log.json"

        result = {"moved": [], "skipped": [], "errors": []}
        log_entries = []
        total = len(plan)

        for i, (src, dst) in enumerate(plan):
            try:
                if dst.exists():
                    result["skipped"].append(str(src))
                    continue

                # 确保目标目录存在
                dst.parent.mkdir(parents=True, exist_ok=True)

                # 先复制到目标，成功后再删除源文件（安全策略）
                shutil.copy2(str(src), str(dst))
                send2trash(str(src))

                result["moved"].append({"src": str(src), "dst": str(dst)})
                log_entries.append({
                    "timestamp": datetime.now().isoformat(),
                    "src": str(src),
                    "dst": str(dst),
                })

                if progress_cb:
                    progress_cb(i + 1, total)
            except Exception as e:
                result["errors"].append({"src": str(src), "error": str(e)})

        # 写日志
        if log_entries:
            existing = []
            if log_path.exists():
                try:
                    existing = json.loads(log_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            existing.extend(log_entries)
            log_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

        return result

    def undo(self, log_path: Path = None) -> dict:
        """根据日志撤销移动（保留失败条目以便重试）"""
        if log_path is None:
            log_path = self.target_root / "organize_log.json"

        if not log_path.exists():
            return {"restored": [], "errors": [{"error": "日志文件不存在"}]}

        try:
            entries = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception as e:
            return {"restored": [], "errors": [{"error": f"读取日志失败: {e}"}]}

        result = {"restored": [], "errors": []}
        remaining = []  # 保留失败条目

        # 从后往前恢复
        for entry in reversed(entries):
            src = Path(entry["src"])
            dst = Path(entry["dst"])
            try:
                if src.exists():
                    result["errors"].append({"file": str(src), "error": "原位置已有文件"})
                    remaining.append(entry)
                    continue
                shutil.move(str(dst), str(src))
                result["restored"].append({"src": str(dst), "dst": str(src)})
            except Exception as e:
                result["errors"].append({"file": str(dst), "error": str(e)})
                remaining.append(entry)

        # 只保留失败条目（反转回正序）
        remaining.reverse()
        log_path.write_text(json.dumps(remaining, ensure_ascii=False, indent=2), encoding="utf-8")

        return result
