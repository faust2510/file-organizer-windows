"""文件整理核心引擎：扫描、分类、整理、多次撤销"""
import json
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from config import (
    CATEGORIES, EXT_MAP, IGNORE_DIRS, IGNORE_EXTS,
    get_target_root, load_user_rules, PHOTO_DATE_FORMAT,
)


@dataclass
class FileInfo:
    path: Path
    category: str = "其他"
    target_path: Optional[Path] = None
    size: int = 0

    def __post_init__(self):
        if self.size == 0 and self.path.exists():
            try:
                self.size = self.path.stat().st_size
            except OSError:
                self.size = 0


class FileScanner:
    def scan(self, dirs, max_depth=10, progress_cb=None):
        files = []
        count = [0]
        for d in dirs:
            if d.exists():
                self._walk(d, 0, max_depth, files, progress_cb, count)
        return files

    def _walk(self, path, depth, max_depth, files, progress_cb, counter):
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: e.name)
        except PermissionError:
            return
        for entry in entries:
            if entry.name in IGNORE_DIRS:
                continue
            if entry.is_dir():
                self._walk(entry, depth + 1, max_depth, files, progress_cb, counter)
            elif entry.is_file():
                ext = entry.suffix.lower()
                if ext in IGNORE_EXTS:
                    continue
                files.append(FileInfo(path=entry))
                counter[0] += 1
                if progress_cb:
                    progress_cb(counter[0], entry)


class FileClassifier:
    def classify_batch(self, files):
        user_rules = load_user_rules()
        merged = {**EXT_MAP, **user_rules}
        for f in files:
            ext = f.path.suffix.lower()
            f.category = merged.get(ext, "其他")
        return files


class FileOrganizer:
    LOG_FILENAME = "organize_log.json"

    def preview(self, files):
        target_root = get_target_root()
        plan = []
        seen = {}
        for f in files:
            if not f.path.exists():
                continue
            cat = f.category
            if cat == "图片":
                dest_dir = target_root / cat / self._get_photo_date(f.path)
            else:
                dest_dir = target_root / cat
            dest_name = f.path.name
            dest = dest_dir / dest_name
            key = str(dest).lower()
            if key in seen:
                seen[key] += 1
                dest = dest_dir / f"{f.path.stem}({seen[key]}){f.path.suffix}"
            else:
                seen[key] = 0
            f.target_path = dest
            plan.append((f.path, dest))
        return plan

    def execute(self, plan, log_path, progress_cb=None):
        moved, skipped, errors = [], [], []
        total = len(plan)
        for i, (src, dst) in enumerate(plan):
            if progress_cb:
                progress_cb(i + 1, total)
            try:
                if not src.exists():
                    skipped.append(str(src))
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
                _send2trash(src)
                moved.append({"original": str(src), "destination": str(dst), "timestamp": datetime.now().isoformat()})
            except Exception as e:
                errors.append(f"{src}: {e}")
        operation = {
            "id": int(time.time() * 1000),
            "timestamp": datetime.now().isoformat(),
            "description": f"整理 {len(moved)} 个文件",
            "moved": moved,
            "skipped": skipped,
            "errors": errors,
        }
        self._append_log(log_path, operation)
        return {"moved": moved, "skipped": skipped, "errors": errors}

    def get_undo_history(self, log_path):
        return list(reversed(self._read_log(log_path)))

    def undo_last(self, log_path):
        history = self._read_log(log_path)
        if not history:
            return {"restored": [], "errors": [], "message": "没有可撤销的操作"}
        last = history.pop()
        result = self._undo_operation(last)
        self._write_log(log_path, history)
        return result

    def undo_to(self, log_path, operation_id):
        history = self._read_log(log_path)
        if not history:
            return {"restored": [], "errors": [], "message": "没有可撤销的操作"}
        target_idx = None
        for i, op in enumerate(history):
            if op.get("id") == operation_id:
                target_idx = i
                break
        if target_idx is None:
            return {"restored": [], "errors": [], "message": "未找到该操作记录"}
        all_restored, all_errors = [], []
        for op in reversed(history[target_idx:]):
            r = self._undo_operation(op)
            all_restored.extend(r["restored"])
            all_errors.extend(r["errors"])
        self._write_log(log_path, history[:target_idx])
        return {"restored": all_restored, "errors": all_errors, "message": f"已撤销 {len(history) - target_idx} 次操作"}

    def undo(self, log_path):
        return self.undo_last(log_path)

    def _undo_operation(self, operation):
        restored, errors = [], []
        for entry in reversed(operation.get("moved", [])):
            src, dst = Path(entry["original"]), Path(entry["destination"])
            try:
                if dst.exists():
                    src.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(dst), str(src))
                    _send2trash(dst)
                    restored.append(str(src))
                else:
                    errors.append(f"文件已不存在: {dst}")
            except Exception as e:
                errors.append(f"{dst}: {e}")
        return {"restored": restored, "errors": errors}

    def _read_log(self, log_path):
        if not log_path.exists():
            return []
        try:
            data = json.loads(log_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if isinstance(data, dict):
            return [data]
        return data if isinstance(data, list) else []

    def _write_log(self, log_path, history):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_log(self, log_path, operation):
        history = self._read_log(log_path)
        history.append(operation)
        self._write_log(log_path, history)

    def _get_photo_date(self, path):
        try:
            from PIL import Image
            from PIL.ExifTags import Base as ExifBase
            with Image.open(path) as img:
                exif = img.getexif()
                date_str = exif.get(ExifBase.DateTime.value)
                if date_str:
                    dt = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                    return PHOTO_DATE_FORMAT.format(year=dt.year, month=dt.month)
        except Exception:
            pass
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            return PHOTO_DATE_FORMAT.format(year=mtime.year, month=mtime.month)
        except Exception:
            return "未知日期"


def _send2trash(path):
    try:
        from send2trash import send2trash
        send2trash(str(path))
    except Exception:
        try:
            os.remove(str(path))
        except Exception:
            pass
