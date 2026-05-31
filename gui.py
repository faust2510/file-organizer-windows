"""妈妈文件整理助手 — GUI 界面（多次撤销版）"""
import threading
import customtkinter as ctk
from tkinter import ttk, messagebox
from pathlib import Path
from collections import Counter
from datetime import datetime

from config import (
    get_scan_dirs, get_target_root, CATEGORIES, EXT_MAP,
    load_user_rules, save_user_rules,
)
from organizer import FileScanner, FileClassifier, FileOrganizer, FileInfo
from search import FileSearcher


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("妈妈文件整理助手")
        self.geometry("960x640")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

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
        # 顶部按钮栏
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(16, 8))

        self.btn_scan = ctk.CTkButton(
            btn_frame, text="扫描文件", width=140, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2563EB", hover_color="#1D4ED8",
            command=self._on_scan,
        )
        self.btn_scan.pack(side="left", padx=(0, 10))

        self.btn_organize = ctk.CTkButton(
            btn_frame, text="整理文件", width=140, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#16A34A", hover_color="#15803D",
            command=self._on_organize, state="disabled",
        )
        self.btn_organize.pack(side="left", padx=(0, 10))

        self.btn_undo = ctk.CTkButton(
            btn_frame, text="撤销整理", width=140, height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#EA580C", hover_color="#C2410C",
            command=self._on_undo,
        )
        self.btn_undo.pack(side="left", padx=(0, 10))

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
            font=ctk.CTkFont(size=14), anchor="w",
        )
        status_label.pack(fill="x", padx=16, pady=(0, 12))

    # ── 扫描 ──────────────────────────────────────────────

    def _on_scan(self):
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
        dirs = get_scan_dirs()
        count = [0]
        def on_progress(n, path):
            count[0] = n
            self.after(0, lambda: self.status_var.set(f"已扫描 {n} 个文件..."))
        files = self.scanner.scan(dirs, progress_cb=on_progress)
        files = self.classifier.classify_batch(files)
        self.files = files
        self.searcher.build_index(files)
        self.plan = self.organizer.preview(files)
        self.after(0, self._scan_done)

    def _scan_done(self):
        self.is_scanning = False
        self.btn_scan.configure(state="normal", text="扫描文件")
        self.btn_organize.configure(state="normal" if self.plan else "disabled")
        self.progress.set(1)
        self._show_files(self.files)
        self.status_var.set(f"扫描完成！共 {len(self.files)} 个文件，{len(self.plan)} 个待整理")

    def _show_files(self, files):
        self.tree.delete(*self.tree.get_children())
        limit = 2000
        for f in files[:limit]:
            target = str(f.target_path) if f.target_path else ""
            source = str(f.path.parent)
            self.tree.insert("", "end", values=(f.path.name, f.category, source, target))
        if len(files) > limit:
            self.status_var.set(f"共 {len(files)} 个文件（仅显示前 {limit} 个，请用搜索筛选）")

    def _apply_filter(self):
        keyword = self.search_var.get()
        category = self.category_var.get()
        results = self.searcher.search_combined(keyword=keyword, category=category)
        self._show_files(results)
        self.status_var.set(f"显示 {len(results)} 个文件")

    # ── 整理 ──────────────────────────────────────────────

    def _on_organize(self):
        if not self.plan:
            messagebox.showinfo("提示", "没有需要整理的文件")
            return
        self._show_preview()

    def _show_preview(self):
        cat_counter = Counter()
        for src, dst in self.plan:
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

        frame = ctk.CTkFrame(win)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        for cat, count in cat_counter.most_common():
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=cat, font=ctk.CTkFont(size=14), anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=f"{count} 个文件", font=ctk.CTkFont(size=14),
                         text_color="#9CA3AF", anchor="e").pack(side="right")

        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkButton(btn_row, text="取消", width=120, height=40,
                       fg_color="#6B7280", hover_color="#4B5563",
                       command=win.destroy).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="确认整理", width=120, height=40,
                       fg_color="#16A34A", hover_color="#15803D",
                       command=lambda: self._confirm_organize(win)).pack(side="right")

    def _confirm_organize(self, dialog):
        dialog.destroy()
        self.is_organizing = True
        self.btn_organize.configure(state="disabled", text="整理中...")
        self.btn_scan.configure(state="disabled")
        self.progress.set(0)
        self.status_var.set("正在整理文件...")
        threading.Thread(target=self._organize_worker, daemon=True).start()

    def _organize_worker(self):
        log_path = get_target_root() / "organize_log.json"
        def on_progress(current, total):
            ratio = current / total if total > 0 else 0
            self.after(0, lambda: self.progress.set(ratio))
            self.after(0, lambda: self.status_var.set(f"正在整理... {current}/{total}"))
        result = self.organizer.execute(self.plan, log_path=log_path, progress_cb=on_progress)
        self.organize_result = result
        self.after(0, self._organize_done)

    def _organize_done(self):
        self.is_organizing = False
        self.btn_organize.configure(state="normal", text="整理文件")
        self.btn_scan.configure(state="normal")
        self.progress.set(1)
        r = self.organize_result
        moved, skipped, errors = len(r["moved"]), len(r["skipped"]), len(r["errors"])
        self.status_var.set(f"整理完成！已移动 {moved} 个，跳过 {skipped} 个，错误 {errors} 个")
        messagebox.showinfo("整理完成", f"已整理 {moved} 个文件\n跳过 {skipped} 个\n错误 {errors} 个")
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self.plan.clear()

    # ── 多次撤销 ──────────────────────────────────────────

    def _on_undo(self):
        log_path = get_target_root() / "organize_log.json"
        history = self.organizer.get_undo_history(log_path)
        if not history:
            messagebox.showinfo("提示", "没有找到整理记录，无法撤销")
            return
        self._show_undo_dialog(log_path, history)

    def _show_undo_dialog(self, log_path, history):
        """撤销历史对话框"""
        win = ctk.CTkToplevel(self)
        win.title("撤销历史")
        win.geometry("560x420")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(
            win, text="选择要撤销的操作",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(16, 8))

        ctk.CTkLabel(
            win, text="选择一条记录，将撤销该操作及之后的所有操作",
            font=ctk.CTkFont(size=12), text_color="#9CA3AF",
        ).pack(pady=(0, 8))

        # 历史列表
        list_frame = ctk.CTkFrame(win)
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        columns = ("time", "desc", "count")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        tree.heading("time", text="时间")
        tree.heading("desc", text="操作描述")
        tree.heading("count", text="文件数")
        tree.column("time", width=170)
        tree.column("desc", width=220)
        tree.column("count", width=80)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for i, op in enumerate(history):
            ts = op.get("timestamp", "未知时间")
            try:
                dt = datetime.fromisoformat(ts)
                ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            desc = op.get("description", "整理操作")
            count = len(op.get("moved", []))
            tree.insert("", "end", iid=str(op.get("id", i)), values=(ts, desc, count))

        # 默认选中第一条（最新）
        children = tree.get_children()
        if children:
            tree.selection_set(children[0])

        # 按钮
        btn_row = ctk.CTkFrame(win, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 16))

        def do_undo():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("提示", "请先选择一条记录")
                return
            op_id = int(sel[0])
            # 如果选的是第一条（最新），用 undo_last
            if sel[0] == children[0]:
                self._do_undo_action(log_path, "last", None, win)
            else:
                self._do_undo_action(log_path, "to", op_id, win)

        def do_undo_all():
            if not messagebox.askyesno("确认", "确定要撤销所有操作吗？所有文件将恢复到原始位置。"):
                return
            self._do_undo_action(log_path, "all", None, win)

        ctk.CTkButton(btn_row, text="撤销选中操作", width=140, height=40,
                       fg_color="#EA580C", hover_color="#C2410C",
                       command=do_undo).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="撤销全部", width=100, height=40,
                       fg_color="#DC2626", hover_color="#B91C1C",
                       command=do_undo_all).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="取消", width=100, height=40,
                       fg_color="#6B7280", hover_color="#4B5563",
                       command=win.destroy).pack(side="right")

    def _do_undo_action(self, log_path, mode, op_id, dialog):
        """执行撤销操作"""
        dialog.destroy()
        self.btn_undo.configure(state="disabled", text="撤销中...")
        self.btn_scan.configure(state="disabled")
        self.btn_organize.configure(state="disabled")
        self.progress.set(0)
        self.status_var.set("正在撤销...")
        threading.Thread(target=self._undo_worker, args=(log_path, mode, op_id), daemon=True).start()

    def _undo_worker(self, log_path, mode, op_id):
        if mode == "last":
            result = self.organizer.undo_last(log_path)
        elif mode == "to":
            result = self.organizer.undo_to(log_path, op_id)
        elif mode == "all":
            history = self.organizer.get_undo_history(log_path)
            if history:
                first_id = history[-1].get("id")
                result = self.organizer.undo_to(log_path, first_id)
            else:
                result = {"restored": [], "errors": [], "message": "没有操作记录"}
        else:
            result = {"restored": [], "errors": [], "message": "未知操作"}
        self.undo_result = result
        self.after(0, self._undo_done)

    def _undo_done(self):
        self.btn_undo.configure(state="normal", text="撤销整理")
        self.btn_scan.configure(state="normal")
        self.progress.set(1)
        result = self.undo_result
        restored = len(result["restored"])
        errors = len(result["errors"])
        msg = result.get("message", "")
        if errors > 0:
            msg = f"已恢复 {restored} 个文件\n{errors} 个文件恢复失败"
        else:
            msg = f"已恢复 {restored} 个文件" + (f"\n{msg}" if msg else "")
        self.status_var.set(f"撤销完成：{msg}")
        messagebox.showinfo("撤销完成", msg)

    # ── 设置 ──────────────────────────────────────────────

    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("自定义分类规则")
        win.geometry("560x480")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text="扩展名 → 分类映射",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(16, 8))

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

        edit_frame = ctk.CTkFrame(win, fg_color="transparent")
        edit_frame.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(edit_frame, text="扩展名：", font=ctk.CTkFont(size=13)).pack(side="left")
        ext_entry = ctk.CTkEntry(edit_frame, width=100, placeholder_text=".xyz")
        ext_entry.pack(side="left", padx=(4, 12))
        ctk.CTkLabel(edit_frame, text="分类：", font=ctk.CTkFont(size=13)).pack(side="left")
        cat_var = ctk.StringVar(value=list(CATEGORIES.keys())[0])
        cat_menu = ctk.CTkOptionMenu(edit_frame, values=list(CATEGORIES.keys()), variable=cat_var, width=120)
        cat_menu.pack(side="left", padx=(4, 12))

        def add_rule():
            ext = ext_entry.get().strip()
            if not ext:
                return
            if not ext.startswith("."):
                ext = "." + ext
            rules = load_user_rules()
            rules[ext] = cat_var.get()
            save_user_rules(rules)
            ext_entry.delete(0, "end")
            refresh_tree()

        ctk.CTkButton(edit_frame, text="添加/修改", width=90, height=32,
                       fg_color="#2563EB", hover_color="#1D4ED8",
                       command=add_rule).pack(side="left")

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
        ctk.CTkButton(btn_row, text="删除选中", width=100, height=36,
                       fg_color="#DC2626", hover_color="#B91C1C",
                       command=delete_rule).pack(side="left")
        ctk.CTkButton(btn_row, text="关闭", width=100, height=36,
                       fg_color="#6B7280", hover_color="#4B5563",
                       command=win.destroy).pack(side="right")
