"""单元测试 — 扫描与分类"""
import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import EXT_MAP
from organizer import FileScanner, FileClassifier, FileInfo, FileOrganizer
from search import FileSearcher


def make_temp_files(structure: dict) -> Path:
    """创建临时文件结构: {"sub/file.txt": "content", ...}"""
    root = Path(tempfile.mkdtemp())
    for rel_path, content in structure.items():
        p = root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return root


class TestFileScanner:
    def test_scan_returns_file_info(self):
        root = make_temp_files({"a.txt": "hello", "b.pdf": "world"})
        try:
            scanner = FileScanner()
            files = scanner.scan([root])
            assert len(files) == 2
            for f in files:
                assert isinstance(f, FileInfo)
                assert f.path.exists()
                assert f.size > 0
                assert f.ext in (".txt", ".pdf")
        finally:
            shutil.rmtree(root)

    def test_scan_recursive(self):
        root = make_temp_files({
            "a.txt": "root",
            "sub/b.txt": "sub",
            "sub/deep/c.txt": "deep",
        })
        try:
            scanner = FileScanner()
            files = scanner.scan([root])
            assert len(files) == 3
        finally:
            shutil.rmtree(root)

    def test_scan_skips_hidden(self):
        root = make_temp_files({
            "visible.txt": "yes",
            ".hidden.txt": "no",
            ".hidden_dir/file.txt": "no",
        })
        try:
            scanner = FileScanner(ignore_hidden=True)
            files = scanner.scan([root])
            assert len(files) == 1
            assert files[0].path.name == "visible.txt"
        finally:
            shutil.rmtree(root)

    def test_scan_skips_ignored_dirs(self):
        root = make_temp_files({
            "normal.txt": "yes",
            "__pycache__/cached.pyc": "no",
            "node_modules/pkg/index.js": "no",
        })
        try:
            scanner = FileScanner()
            files = scanner.scan([root])
            assert len(files) == 1
            assert files[0].path.name == "normal.txt"
        finally:
            shutil.rmtree(root)

    def test_scan_skips_ignored_exts(self):
        root = make_temp_files({
            "doc.txt": "yes",
            "link.lnk": "no",
            "temp.tmp": "no",
        })
        try:
            scanner = FileScanner()
            files = scanner.scan([root])
            assert len(files) == 1
            assert files[0].path.name == "doc.txt"
        finally:
            shutil.rmtree(root)

    def test_scan_progress_callback(self):
        root = make_temp_files({"a.txt": "1", "b.txt": "2", "c.txt": "3"})
        try:
            counts = []
            scanner = FileScanner()
            scanner.scan([root], progress_cb=lambda n, p: counts.append(n))
            assert len(counts) == 3
            assert counts == [1, 2, 3]
        finally:
            shutil.rmtree(root)

    def test_scan_nonexistent_dir(self):
        scanner = FileScanner()
        files = scanner.scan([Path("/nonexistent/path")])
        assert files == []


class TestFileClassifier:
    def test_classify_known_exts(self):
        classifier = FileClassifier()
        test_cases = [
            (".docx", "文档"), (".pdf", "文档"), (".xlsx", "文档"),
            (".jpg", "图片"), (".png", "图片"), (".gif", "图片"),
            (".mp4", "视频"), (".avi", "视频"),
            (".mp3", "音乐"), (".flac", "音乐"),
            (".zip", "压缩包"), (".rar", "压缩包"),
            (".py", "代码"), (".js", "代码"),
            (".psd", "设计"),
            (".exe", "安装包"),
        ]
        for ext, expected in test_cases:
            info = FileInfo(path=Path(f"test{ext}"), size=0, mtime=0, ext=ext)
            assert classifier.classify(info) == expected, f"{ext} should be {expected}"

    def test_classify_unknown_ext(self):
        classifier = FileClassifier()
        info = FileInfo(path=Path("test.xyz"), size=0, mtime=0, ext=".xyz")
        assert classifier.classify(info) == "其他"

    def test_classify_batch(self):
        classifier = FileClassifier()
        files = [
            FileInfo(path=Path("a.txt"), size=0, mtime=0, ext=".txt"),
            FileInfo(path=Path("b.jpg"), size=0, mtime=0, ext=".jpg"),
            FileInfo(path=Path("c.mp4"), size=0, mtime=0, ext=".mp4"),
        ]
        result = classifier.classify_batch(files)
        assert result[0].category == "文档"
        assert result[1].category == "图片"
        assert result[2].category == "视频"

    def test_all_ext_map_covered(self):
        """验证 EXT_MAP 中每个扩展名都能正确分类"""
        classifier = FileClassifier()
        for ext, expected_cat in EXT_MAP.items():
            info = FileInfo(path=Path(f"test{ext}"), size=0, mtime=0, ext=ext)
            assert classifier.classify(info) == expected_cat, f"{ext} -> {expected_cat} failed"


class TestFileOrganizer:
    def test_preview_returns_plan(self):
        src_dir = make_temp_files({"a.txt": "hello", "b.jpg": "img"})
        target_dir = Path(tempfile.mkdtemp())
        try:
            scanner = FileScanner()
            classifier = FileClassifier()
            organizer = FileOrganizer(target_root=target_dir)

            files = scanner.scan([src_dir])
            files = classifier.classify_batch(files)
            plan = organizer.preview(files)

            assert len(plan) == 2
            for src, dst in plan:
                assert isinstance(src, Path)
                assert isinstance(dst, Path)
                assert str(target_dir) in str(dst)
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(target_dir)

    def test_execute_moves_files(self):
        src_dir = make_temp_files({"doc.txt": "hello", "img.jpg": "img"})
        target_dir = Path(tempfile.mkdtemp())
        try:
            scanner = FileScanner()
            classifier = FileClassifier()
            organizer = FileOrganizer(target_root=target_dir)

            files = scanner.scan([src_dir])
            files = classifier.classify_batch(files)
            plan = organizer.preview(files)
            result = organizer.execute(plan)

            assert len(result["moved"]) == 2
            assert len(result["errors"]) == 0

            # 验证文件已移动
            for entry in result["moved"]:
                assert not Path(entry["src"]).exists()
                assert Path(entry["dst"]).exists()
        finally:
            shutil.rmtree(target_dir)

    def test_rename_on_conflict(self):
        """目标位置已有同名文件时，自动重命名"""
        src_dir = make_temp_files({"doc.txt": "hello"})
        target_dir = Path(tempfile.mkdtemp())
        try:
            cat_dir = target_dir / "文档"
            cat_dir.mkdir(parents=True)
            (cat_dir / "doc.txt").write_text("existing")

            scanner = FileScanner()
            classifier = FileClassifier()
            organizer = FileOrganizer(target_root=target_dir)

            files = scanner.scan([src_dir])
            files = classifier.classify_batch(files)
            plan = organizer.preview(files)
            result = organizer.execute(plan)

            # 应该被重命名为 doc_1.txt
            assert len(result["moved"]) == 1
            assert "doc_1.txt" in result["moved"][0]["dst"]
            # 源文件已移走
            assert not Path(src_dir / "doc.txt").exists()
            # 两个文件都存在于目标
            assert (cat_dir / "doc.txt").exists()
            assert (cat_dir / "doc_1.txt").exists()
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(target_dir)

    def test_undo_restores_files(self):
        src_dir = make_temp_files({"a.txt": "hello", "b.txt": "world"})
        target_dir = Path(tempfile.mkdtemp())
        try:
            scanner = FileScanner()
            classifier = FileClassifier()
            organizer = FileOrganizer(target_root=target_dir)

            files = scanner.scan([src_dir])
            files = classifier.classify_batch(files)
            plan = organizer.preview(files)
            organizer.execute(plan)

            # 验证文件已移走
            assert not Path(src_dir / "a.txt").exists()

            # 撤销
            log_path = target_dir / "organize_log.json"
            undo_result = organizer.undo(log_path)

            assert len(undo_result["restored"]) == 2
            assert Path(src_dir / "a.txt").exists()
            assert Path(src_dir / "b.txt").exists()
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(target_dir)

    def test_execute_creates_log(self):
        src_dir = make_temp_files({"a.txt": "hello"})
        target_dir = Path(tempfile.mkdtemp())
        try:
            scanner = FileScanner()
            classifier = FileClassifier()
            organizer = FileOrganizer(target_root=target_dir)

            files = scanner.scan([src_dir])
            files = classifier.classify_batch(files)
            plan = organizer.preview(files)
            organizer.execute(plan)

            log_path = target_dir / "organize_log.json"
            assert log_path.exists()

            import json
            log = json.loads(log_path.read_text())
            assert len(log) == 1
            assert "src" in log[0]
            assert "dst" in log[0]
            assert "timestamp" in log[0]
        finally:
            shutil.rmtree(target_dir)

    def test_photo_by_date(self):
        """照片文件应按年-月分文件夹"""
        src_dir = make_temp_files({"photo.jpg": "img"})
        target_dir = Path(tempfile.mkdtemp())
        try:
            scanner = FileScanner()
            classifier = FileClassifier()
            organizer = FileOrganizer(target_root=target_dir)

            files = scanner.scan([src_dir])
            files = classifier.classify_batch(files)
            plan = organizer.preview(files)

            assert len(plan) == 1
            dst = plan[0][1]
            # 目标路径应包含年-月子目录
            assert dst.parent.name != "Images"  # 不是直接在 Images 下
        finally:
            shutil.rmtree(src_dir)
            shutil.rmtree(target_dir)


class TestFileSearcher:
    def _make_files(self, names):
        files = []
        for name in names:
            ext = Path(name).suffix.lower()
            files.append(FileInfo(path=Path(f"/test/{name}"), size=100, mtime=0, ext=ext))
        return files

    def test_search_exact_match(self):
        searcher = FileSearcher()
        files = self._make_files(["report.pdf", "photo.jpg", "music.mp3"])
        searcher.build_index(files)
        results = searcher.search("report")
        assert len(results) == 1
        assert results[0].path.name == "report.pdf"

    def test_search_partial_match(self):
        searcher = FileSearcher()
        files = self._make_files(["report_2024.pdf", "report_old.doc", "photo.jpg"])
        searcher.build_index(files)
        results = searcher.search("report")
        assert len(results) == 2

    def test_search_starts_with_priority(self):
        """文件名开头匹配应排在前面"""
        searcher = FileSearcher()
        files = self._make_files(["data.csv", "metadata.json", "database.sql"])
        searcher.build_index(files)
        results = searcher.search("data")
        assert results[0].path.name == "data.csv"

    def test_search_empty_keyword(self):
        searcher = FileSearcher()
        files = self._make_files(["a.txt", "b.txt"])
        searcher.build_index(files)
        results = searcher.search("")
        assert len(results) == 2

    def test_search_case_insensitive(self):
        searcher = FileSearcher()
        files = self._make_files(["README.md", "readme.txt"])
        searcher.build_index(files)
        results = searcher.search("readme")
        assert len(results) == 2

    def test_search_by_category(self):
        searcher = FileSearcher()
        files = self._make_files(["a.txt", "b.jpg", "c.mp4"])
        files[0].category = "文档"
        files[1].category = "图片"
        files[2].category = "视频"
        searcher.build_index(files)
        results = searcher.search_by_category("图片")
        assert len(results) == 1
        assert results[0].path.name == "b.jpg"

    def test_search_combined(self):
        searcher = FileSearcher()
        files = self._make_files(["photo_2024.jpg", "photo.txt", "video.mp4"])
        files[0].category = "图片"
        files[1].category = "文档"
        files[2].category = "视频"
        searcher.build_index(files)
        results = searcher.search_combined(keyword="photo", category="图片")
        assert len(results) == 1
        assert results[0].path.name == "photo_2024.jpg"

    def test_search_no_match(self):
        searcher = FileSearcher()
        files = self._make_files(["a.txt", "b.jpg"])
        searcher.build_index(files)
        results = searcher.search("nonexistent")
        assert len(results) == 0

    def test_search_chinese(self):
        searcher = FileSearcher()
        files = self._make_files(["报告.pdf", "照片.jpg", "报告_final.doc"])
        searcher.build_index(files)
        results = searcher.search("报告")
        assert len(results) == 2


def run_tests():
    tests = [
        TestFileScanner(),
        TestFileClassifier(),
        TestFileOrganizer(),
        TestFileSearcher(),
    ]
    passed = 0
    failed = 0
    errors = []

    for suite in tests:
        for name in dir(suite):
            if not name.startswith("test_"):
                continue
            try:
                getattr(suite, name)()
                passed += 1
                print(f"  PASS: {suite.__class__.__name__}.{name}")
            except Exception as e:
                failed += 1
                errors.append(f"{suite.__class__.__name__}.{name}: {e}")
                print(f"  FAIL: {suite.__class__.__name__}.{name}: {e}")

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
