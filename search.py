"""文件搜索：倒排索引 + 中文逐字匹配"""
from collections import defaultdict
from pathlib import Path
from typing import Optional


class FileSearcher:
    def __init__(self):
        self._index: dict[str, list[int]] = defaultdict(list)
        self._files: list = []

    def build_index(self, files):
        self._files = files
        self._index.clear()
        for i, f in enumerate(files):
            name = f.path.name.lower()
            for ch in name:
                if ch.strip():
                    self._index[ch].append(i)

    def search(self, keyword: str) -> list:
        if not keyword.strip():
            return list(self._files)
        keyword = keyword.lower()
        matched = set()
        for ch in keyword:
            if ch in self._index:
                if not matched:
                    matched = set(self._index[ch])
                else:
                    matched &= set(self._index[ch])
            else:
                return []
        return [self._files[i] for i in sorted(matched)]

    def search_combined(self, keyword: str = "", category: str = "全部") -> list:
        if category and category != "全部":
            results = [f for f in self._files if f.category == category]
        else:
            results = list(self._files)
        if keyword.strip():
            keyword = keyword.lower()
            results = [f for f in results if keyword in f.path.name.lower()]
        return results
