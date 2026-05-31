"""文件搜索 — 倒排索引 + 实时搜索"""
from pathlib import Path
from typing import Optional
from organizer import FileInfo


class FileSearcher:
    """基于文件名的搜索"""

    def __init__(self):
        self._files: list[FileInfo] = []
        self._index: dict[str, list[int]] = {}  # token -> [file_indices]

    def build_index(self, files: list[FileInfo]):
        """构建倒排索引"""
        self._files = files
        self._index.clear()

        for i, f in enumerate(files):
            name = f.path.name.lower()
            # 按字符分词（支持中文逐字搜索）
            tokens = set()
            tokens.add(name)
            # 添加文件名各部分
            for part in name.replace(".", " ").replace("-", " ").replace("_", " ").split():
                tokens.add(part)
            # 添加每个字符（支持中文逐字匹配）
            for ch in name:
                if ch not in " .-_":
                    tokens.add(ch)

            for token in tokens:
                if token not in self._index:
                    self._index[token] = []
                self._index[token].append(i)

    def search(self, keyword: str) -> list[FileInfo]:
        """搜索文件名包含关键词的文件"""
        if not keyword.strip():
            return list(self._files)

        kw = keyword.lower().strip()
        matched_indices = set()

        # 在索引中查找
        for token, indices in self._index.items():
            if kw in token:
                matched_indices.update(indices)

        # 排序：文件名开头匹配 > 包含匹配
        results = []
        starts_with = []
        contains = []

        for idx in matched_indices:
            f = self._files[idx]
            name = f.path.name.lower()
            if name.startswith(kw):
                starts_with.append(f)
            else:
                contains.append(f)

        # 按文件名排序
        starts_with.sort(key=lambda f: f.path.name.lower())
        contains.sort(key=lambda f: f.path.name.lower())

        return starts_with + contains

    def search_by_category(self, category: str) -> list[FileInfo]:
        """按分类筛选"""
        return [f for f in self._files if f.category == category]

    def search_combined(self, keyword: str = "", category: str = "") -> list[FileInfo]:
        """组合搜索：关键词 + 分类筛选"""
        results = self.search(keyword) if keyword else list(self._files)
        if category and category != "全部":
            results = [f for f in results if f.category == category]
        return results
