"""妈妈文件整理助手 — GUI 界面"""
import threading
import customtkinter as ctk
from tkinter import ttk, messagebox
from pathlib import Path
from collections import Counter

from config import (
    get_scan_dirs, get_target_root, CATEGORIES, EXT_MAP,
    load_user_rules, save_user_rules,
)
from organizer import FileScanner, FileClassifier, FileOrganizer, FileInfo
from search import FileSearcher


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 窗口设置
        self.title("妈妈文件整理助手")
        self.geometry("960x640")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # 核心对象
        self.scanner = FileScanner()
        self.classifier = FileClassifier()
        self.organizer = FileOrganizer()
        self.searcher = FileSearcher()

        self.files: list[FileInfo] = []
        self.plan: list[tuple[Path, Path]] = []
        self.is_scanning = False
        self.is_organizing = False

        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        # 顶部按钮栏
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(16, 8))

        self.btn_scan = ctk.CTkButton(
            btn_frame, text="扫描文件", width=160, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2563EB", hover_color="#1D4ED8",
            command=self._on_scan,
        )
        self.btn_scan.pack(side="left", padx=(0, 12))

        self.btn_organize = ctk.CTkButton(
            btn_frame, text="整理文件", width=160, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#16A34A", hover_color="#15803D",
            command=self._on_organize, state="disabled",
        )
        self.btn_organize.pack(side="left", padx=(0, 12))

        self.btn_undo = ctk.CTkButton(
            btn_frame, text="撤销整理", width=160, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#EA580C", hover_color="#C2410C",
            command=self._on_undo,
        )
        self.btn_undo.pack(side="left", padx=(0, 12))

        self.btn_settings = ctk.CTkButton(
            btn_frame, text="设置", width=100, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#6B7280", hover_color="#4B5563",
            command=self._open_settings,
        )
        self.btn_settings.pack(side="right")

        # 搜索 + 筛选栏
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        search_entry = ctk.CTkEntry(
            filter_frame, placeholder_text="搜索文件名...",
            textvariable=self.search_var, height=36,
            font=ctk.CTkFont(size=14),
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.category_var = ctk.StringVar(value="全部")
        categories = ["全部"] + list(CATEGORIES.keys())
        category_menu = ctk.CTkOptionMenu(
            filter_frame, values=categories,
            variable=self.category_var, width=140, height=36,
            font=ctk.CTkFont(size=14),
            command=lambda _: self._apply_filter(),
        )
        category_menu.pack(side="right")

        # 文件列表
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        columns = ("name", "category", "source", "target")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)

        self.tree.heading("name", text="文件名")
        self.tree.heading("category", text="分类")
        self.tree.heading("source", text="原路径")
        self.tree.heading("target", text="目标路径")

        self.tree.column("name", width=180, minwidth=120)
        self.tree.column("category", width=80, minwidth=60)
        self.tree.column("source", width=300, minwidth=150)
        self.tree.column("target", width=300, minwidth=150)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 进度条
        self.progress = ctk.CTkProgressBar(self, height=8)
        self.progress.pack(fill="x", padx=16, pady=(0, 4))
        self.progress.set(0)

        # 状态栏
        self.status_var = ctk.StringVar(value='点击"扫描文件"开始')
        status_label = ctk.CTkLabel(
            self, textvariable=self.status_var,
            font=ctk.CTkFont(size=14),
            anchor="w",
        )
        status_label.pack(fill="x", padx=16, pady=(0, 12))

    def _on_scan(self):
        """扫描按钮"""
        if self.is_scanning:
            return
        self.is_scanning = True
        self.btn_scan.configure(state="disabled", text="扫描中...")
        self.btn_organize.configure(state="disabled")
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self.plan.clear()
        self.progress.set(0)
        self.status_var.set("正在扫描文件...")

        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        """后台扫描"""
        dirs = get_scan_dirs()
        count = [0]

        def on_progress(n, path):
            count[0] = n
            self.after(0, lambda: self.status_var.set(f"已扫描 {n} 个文件..."))

        files = self.scanner.scan(dirs, progress_cb=on_progress)
        files = self.classifier.classify_batch(files)
        self.files = files

        # 构建搜索索引
        self.searcher.build_index(files)

        # 生成预览计划
        self.plan = self.organizer.preview(files)

        self.after(0, self._scan_done)

    def _scan_done(self):
        """扫描完成"""
        self.is_scanning = False
        self.btn_scan.configure(state="normal", text="扫描文件")
        self.btn_organize.configure(state="normal" if self.plan else "disabled")
        self.progress.set(1)
        self._show_files(self.files)
        self.status_var.set(f"扫描完成！共 {len(self.files)} 个文件，{len(self.plan)} 个待整理")

    def _show_files(self, files: list[FileInfo]):
        """在列表中显示文件"""
        self.tree.delete(*self.tree.get_children())
        limit = 2000
        for f in files[:limit]:
            target = str(f.target_path) if f.target_path else ""
            source = str(f.path.parent)
            self.tree.insert("", "end", values=(
                f.path.name, f.category, source, target
            ))
        if len(files) > limit:
            self.status_var.set(f"共 {len(files)} 个文件（仅显示前 {limit} 个，请用搜索筛选）")

    def _apply_filter(self):
        """搜索 + 分类筛选"""
        keyword = self.search_var.get()
        category = self.category_var.get()
        results = self.searcher.search_combined(keyword=keyword, category=category)
        self._show_files(results)
        self.status_var.set(f"显示 {len(results)} 个文件")

    def _on_organize(self):
        """整理按钮 — 先弹出预览"""
        if not self.plan:
            messagebox.showinfo("提示", "没有需要整理的文件")
            return
        self._show_preview()

    def _show_preview(self):
        """整理前预览对话框"""
        # 统计每个分类的文件数
        cat_counter = Counter()
        for src, dst in self.plan:
            # 从目标路径提取分类文件夹名
            parts = dst.relative_to(get_target_root()).parts
            cat_counter[parts[0]] += 1

        total = len(self.plan)
        target = get_target_root()

        win = ctk.CTkToplevel(self)
        win.title("整理预览")
        win.geometry("420x400")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(
            win, text=f"共 {total} 个文件，分为 {len(cat_counter)} 个分类",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            win, text=f"目标目录：{target}",
            font=ctk.CTkFont(size=13), text_color="#9CA3AF",
        ).pack(pady=(0, 10))

        # 分类详情列表
        frame = ctk.CTkFrame(win)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        for cat, count in cat_counter.most_common():
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(
                row, text=cat, font=ctk.CTkFont(size=14), anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=f"{count} 个文件", font=ctk.CTkFont(size=14),
                text_color="#9CA3AF", anchor="e",
            ).pack(side="right")

        # 按钮
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkButton(
            btn_row, text="取消", width=120, height=40,
            fg_color="#6B7280", hover_color="#4B5563",
            command=win.destroy,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_row, text="确认整理", width=120, height=40,
            fg_color="#16A34A", hover_color="#15803D",
            command=lambda: self._confirm_organize(win),
        ).pack(side="right")

    def _confirm_organize(self, dialog):
        """用户确认后开始整理"""
        dialog.destroy()
        self.is_organizing = True
        self.btn_organize.configure(state="disabled", text="整理中...")
        self.btn_scan.configure(state="disabled")
        self.progress.set(0)
        self.status_var.set("正在整理文件...")

        threading.Thread(target=self._organize_worker, daemon=True).start()

    def _organize_worker(self):
        """后台整理"""
        log_path = get_target_root() / "organize_log.json"

        def on_progress(current, total):
            ratio = current / total if total > 0 else 0
            self.after(0, lambda: self.progress.set(ratio))
            self.after(0, lambda: self.status_var.set(f"正在整理... {current}/{total}"))

        result = self.organizer.execute(self.plan, log_path=log_path, progress_cb=on_progress)
        self.organize_result = result
        self.after(0, self._organize_done)

    def _organize_done(self):
        """整理完成"""
        self.is_organizing = False
        self.btn_organize.configure(state="normal", text="整理文件")
        self.btn_scan.configure(state="normal")
        self.progress.set(1)

        r = self.organize_result
        moved = len(r["moved"])
        skipped = len(r["skipped"])
        errors = len(r["errors"])
        self.status_var.set(f"整理完成！已移动 {moved} 个，跳过 {skipped} 个，错误 {errors} 个")
        messagebox.showinfo("整理完成", f"已整理 {moved} 个文件\n跳过 {skipped} 个\n错误 {errors} 个")

        # 清空列表
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self.plan.clear()

    def _on_undo(self):
        """撤销按钮"""
        log_path = get_target_root() / "organize_log.json"
        if not log_path.exists():
            messagebox.showinfo("提示", "没有找到整理记录，无法撤销")
            return

        if not messagebox.askyesno("确认撤销", "确定要撤销上次整理吗？\n文件将恢复到原来的位置。"):
            return

        self.btn_undo.configure(state="disabled", text="撤销中...")
        self.btn_scan.configure(state="disabled")
        self.btn_organize.configure(state="disabled")
        self.progress.set(0)
        self.status_var.set("正在撤销...")

        threading.Thread(target=self._undo_worker, daemon=True).start()

    def _undo_worker(self):
        """后台撤销"""
        log_path = get_target_root() / "organize_log.json"
        result = self.organizer.undo(log_path)
        self.undo_result = result
        self.after(0, self._undo_done)

    def _undo_done(self):
        """撤销完成"""
        self.btn_undo.configure(state="normal", text="撤销整理")
        self.btn_scan.configure(state="normal")
        self.progress.set(1)

        result = self.undo_result
        restored = len(result["restored"])
        errors = len(result["errors"])

        if errors > 0:
            msg = f"已恢复 {restored} 个文件\n{errors} 个文件恢复失败（可再次尝试撤销）"
        else:
            msg = f"已恢复 {restored} 个文件"

        self.status_var.set(f"撤销完成：{msg}")
        messagebox.showinfo("撤销完成", msg)

    def _open_settings(self):
        """打开设置窗口 — 自定义分类规则"""
        win = ctk.CTkToplevel(self)
        win.title("自定义分类规则")
        win.geometry("560x480")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(
            win, text="扩展名 → 分类映射",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(16, 8))

        # 规则列表
        list_frame = ctk.CTkFrame(win)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        columns = ("ext", "category")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        tree.heading("ext", text="扩展名")
        tree.heading("category", text="分类")
        tree.column("ext", width=120)
        tree.column("category", width=200)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def refresh_tree():
            tree.delete(*tree.get_children())
            current = {**EXT_MAP, **load_user_rules()}
            for ext in sorted(current):
                tree.insert("", "end", values=(ext, current[ext]))

        refresh_tree()

        # 添加/修改区域
        edit_frame = ctk.CTkFrame(win, fg_color="transparent")
        edit_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(edit_frame, text="扩展名：", font=ctk.CTkFont(size=13)).pack(side="left")
        ext_entry = ctk.CTkEntry(edit_frame, width=100, placeholder_text=".xyz")
        ext_entry.pack(side="left", padx=(4, 12))

        ctk.CTkLabel(edit_frame, text="分类：", font=ctk.CTkFont(size=13)).pack(side="left")
        cat_var = ctk.StringVar(value=list(CATEGORIES.keys())[0])
        cat_menu = ctk.CTkOptionMenu(
            edit_frame, values=list(CATEGORIES.keys()),
            variable=cat_var, width=120,
        )
        cat_menu.pack(side="left", padx=(4, 12))

        def add_rule():
            ext = ext_entry.get().strip()
            if not ext:
                return
            if not ext.startswith("."):
                ext = "." + ext
            cat = cat_var.get()
            rules = load_user_rules()
            rules[ext] = cat
            save_user_rules(rules)
            ext_entry.delete(0, "end")
            refresh_tree()

        ctk.CTkButton(
            edit_frame, text="添加/修改", width=90, height=32,
            fg_color="#2563EB", hover_color="#1D4ED8",
            command=add_rule,
        ).pack(side="left")

        # 删除按钮
        def delete_rule():
            sel = tree.selection()
            if not sel:
                return
            ext = tree.item(sel[0])["values"][0]
            rules = load_user_rules()
            if ext in rules:
                del rules[ext]
                save_user_rules(rules)
            refresh_tree()

        def on_tree_select(event):
            sel = tree.selection()
            if sel:
                values = tree.item(sel[0])["values"]
                ext_entry.delete(0, "end")
                ext_entry.insert(0, values[0])
                if values[1] in CATEGORIES:
                    cat_var.set(values[1])

        tree.bind("<<TreeviewSelect>>", on_tree_select)

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(
            btn_row, text="删除选中", width=100, height=36,
            fg_color="#DC2626", hover_color="#B91C1C",
            command=delete_rule,
        ).pack(side="left")

        ctk.CTkButton(
            btn_row, text="关闭", width=100, height=36,
            fg_color="#6B7280", hover_color="#4B5563",
            command=win.destroy,
        ).pack(side="right")
