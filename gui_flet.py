"""妈妈文件整理助手 — Flet 0.85 现代化 UI"""
import threading
import flet as ft
from pathlib import Path
from collections import Counter

from config import (
    get_scan_dirs, get_target_root, CATEGORIES, EXT_MAP,
    load_user_rules, save_user_rules,
)
from organizer import FileScanner, FileClassifier, FileOrganizer, FileInfo
from search import FileSearcher


class FileOrganizerApp:
    """Flet 版本的文件整理助手"""

    def __init__(self, page: ft.Page):
        self.page = page
        self._setup_page()
        self._init_core()
        self._build_ui()

    def _setup_page(self):
        """页面基础设置"""
        self.page.title = "妈妈文件整理助手"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.BLUE,
            visual_density=ft.VisualDensity.COMFORTABLE,
        )
        self.page.padding = 0
        self.page.spacing = 0

    def _init_core(self):
        """初始化核心业务对象"""
        self.scanner = FileScanner()
        self.classifier = FileClassifier()
        self.organizer = FileOrganizer()
        self.searcher = FileSearcher()

        self.files: list[FileInfo] = []
        self.plan: list[tuple[Path, Path]] = []
        self.is_scanning = False
        self.is_organizing = False

        # 自定义目标目录：{文件原路径: 新目标目录}
        self.custom_targets: dict[str, str] = {}
        # 当前正在修改目标的文件索引
        self._editing_plan_index: int | None = None

    def _build_ui(self):
        """构建主界面"""
        # 顶部应用栏
        self.appbar = ft.AppBar(
            title=ft.Text("妈妈文件整理助手", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            center_title=False,
            bgcolor=ft.Colors.BLUE_700,
            actions=[
                ft.IconButton(
                    ft.Icons.SETTINGS,
                    tooltip="设置",
                    icon_color=ft.Colors.WHITE,
                    on_click=self._open_settings,
                ),
            ],
        )

        # 工具栏按钮
        self.btn_scan = ft.FilledButton(
            "扫描文件",
            icon=ft.Icons.SEARCH,
            style=ft.ButtonStyle(padding=16, shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=self._on_scan,
        )
        self.btn_organize = ft.FilledButton(
            "整理文件",
            icon=ft.Icons.FOLDER_OPEN,
            style=ft.ButtonStyle(padding=16, shape=ft.RoundedRectangleBorder(radius=8), bgcolor=ft.Colors.GREEN_700),
            on_click=self._on_organize,
            disabled=True,
        )
        self.btn_undo = ft.FilledButton(
            "撤销整理",
            icon=ft.Icons.UNDO,
            style=ft.ButtonStyle(padding=16, shape=ft.RoundedRectangleBorder(radius=8), bgcolor=ft.Colors.ORANGE_700),
            on_click=self._on_undo,
        )
        self.btn_change_root = ft.OutlinedButton(
            "更改目标目录",
            icon=ft.Icons.FOLDER_SPECIAL,
            style=ft.ButtonStyle(padding=16, shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=self._on_change_root,
            tooltip="更改整理目标根目录",
        )

        # 搜索框
        self.search_field = ft.TextField(
            hint_text="搜索文件名...",
            prefix_icon=ft.Icons.SEARCH,
            border_radius=8,
            expand=True,
            on_change=self._apply_filter,
        )

        # 分类筛选
        self.category_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option("全部")] + [
                ft.dropdown.Option(cat) for cat in CATEGORIES.keys()
            ],
            value="全部",
            width=150,
            border_radius=8,
            on_select=self._apply_filter,
        )

        # 数据表格
        self.data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("文件名", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("分类", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("原路径", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("目标路径", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.GREY_300),
                bottom=ft.BorderSide(1, ft.Colors.GREY_300),
                left=ft.BorderSide(1, ft.Colors.GREY_300),
                right=ft.BorderSide(1, ft.Colors.GREY_300),
            ),
            border_radius=8,
            heading_row_color=ft.Colors.BLUE_50,
            heading_row_height=48,
            data_row_min_height=48,
            data_row_max_height=64,
            column_spacing=24,
            horizontal_margin=16,
            show_checkbox_column=False,
        )

        # 文件选择器（用于修改目标目录）
        self.folder_picker = ft.FilePicker(on_result=self._on_folder_picked)
        self.page.overlay.append(self.folder_picker)

        # 进度条
        self.progress_bar = ft.ProgressBar(
            value=0,
            bar_height=8,
            border_radius=4,
            color=ft.Colors.BLUE_700,
            bgcolor=ft.Colors.GREY_200,
        )

        # 状态栏
        self.status_text = ft.Text(
            '点击"扫描文件"开始',
            size=14,
            color=ft.Colors.GREY_700,
        )

        # 主布局
        self.page.add(
            self.appbar,
            # 工具栏
            ft.Container(
                content=ft.Row(
                    controls=[self.btn_scan, self.btn_organize, self.btn_undo, self.btn_change_root],
                    spacing=12,
                ),
                padding=ft.Padding.only(left=16, top=12, right=16, bottom=12),
                bgcolor=ft.Colors.GREY_50,
            ),
            # 搜索 + 筛选
            ft.Container(
                content=ft.Row(
                    controls=[self.search_field, self.category_dropdown],
                    spacing=12,
                ),
                padding=ft.Padding.only(left=16, top=8, right=16, bottom=8),
            ),
            # 文件列表
            ft.Container(
                content=ft.ListView(
                    controls=[self.data_table],
                    expand=True,
                    auto_scroll=True,
                ),
                padding=ft.Padding.only(left=16, top=8, right=16, bottom=8),
                expand=True,
            ),
            # 进度条
            ft.Container(
                content=self.progress_bar,
                padding=ft.Padding.only(left=16, top=4, right=16, bottom=4),
            ),
            # 状态栏
            ft.Container(
                content=self.status_text,
                padding=ft.Padding.only(left=16, top=12, right=16, bottom=12),
                bgcolor=ft.Colors.GREY_50,
            ),
        )

    def _on_scan(self, e):
        """扫描按钮"""
        if self.is_scanning:
            return
        self.is_scanning = True
        self.btn_scan.disabled = True
        self.btn_scan.text = "扫描中..."
        self.btn_organize.disabled = True
        self.data_table.rows.clear()
        self.files.clear()
        self.plan.clear()
        self.progress_bar.value = 0
        self.status_text.value = "正在扫描文件..."
        self.page.update()

        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        """后台扫描"""
        dirs = get_scan_dirs()
        count = [0]

        def on_progress(n, path):
            count[0] = n
            self.page.run_thread(lambda: self._update_status(f"已扫描 {n} 个文件..."))

        files = self.scanner.scan(dirs, progress_cb=on_progress)
        files = self.classifier.classify_batch(files)
        self.files = files
        self.searcher.build_index(files)
        self.plan = self.organizer.preview(files)
        self.page.run_thread(self._scan_done)

    def _scan_done(self):
        """扫描完成"""
        self.is_scanning = False
        self.btn_scan.disabled = False
        self.btn_scan.text = "扫描文件"
        self.btn_organize.disabled = not self.plan
        self.progress_bar.value = 1
        self._show_files(self.files)
        self.status_text.value = f"扫描完成！共 {len(self.files)} 个文件，{len(self.plan)} 个待整理"
        self.page.update()

    def _show_files(self, files: list[FileInfo]):
        """显示文件列表"""
        self.data_table.rows.clear()
        limit = 2000
        for f in files[:limit]:
            target = str(f.target_path) if f.target_path else ""
            source = str(f.path.parent)
            self.data_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f.path.name, size=13)),
                        ft.DataCell(self._build_category_chip(f.category)),
                        ft.DataCell(ft.Text(source, size=12, color=ft.Colors.GREY_600)),
                        ft.DataCell(ft.Text(target, size=12, color=ft.Colors.GREY_600)),
                    ],
                ),
            )
        if len(files) > limit:
            self.status_text.value = f"共 {len(files)} 个文件（仅显示前 {limit} 个，请用搜索筛选）"
        self.page.update()

    def _build_category_chip(self, category: str):
        """分类标签"""
        color_map = {
            "文档": ft.Colors.BLUE_100,
            "图片": ft.Colors.PURPLE_100,
            "视频": ft.Colors.RED_100,
            "音乐": ft.Colors.AMBER_100,
            "压缩包": ft.Colors.CYAN_100,
            "代码": ft.Colors.GREEN_100,
            "设计": ft.Colors.PINK_100,
            "安装包": ft.Colors.ORANGE_100,
            "其他": ft.Colors.GREY_200,
        }
        return ft.Container(
            content=ft.Text(category, size=12),
            bgcolor=color_map.get(category, ft.Colors.GREY_200),
            padding=ft.Padding.only(left=8, top=4, right=8, bottom=4),
            border_radius=4,
        )

    def _apply_filter(self, e=None):
        """搜索 + 分类筛选"""
        keyword = self.search_field.value or ""
        category = self.category_dropdown.value or "全部"
        results = self.searcher.search_combined(keyword=keyword, category=category)
        self._show_files(results)
        self.status_text.value = f"显示 {len(results)} 个文件"
        self.page.update()

    def _on_organize(self, e):
        """整理按钮"""
        if not self.plan:
            self._show_snackbar("没有需要整理的文件", ft.Colors.ORANGE_700)
            return
        self._show_preview()

    def _show_preview(self):
        """整理前预览 — 显示每个文件的目标目录，支持修改"""
        total = len(self.plan)
        target = get_target_root()

        # 分类统计
        cat_counter = Counter()
        for src, dst in self.plan:
            try:
                parts = dst.relative_to(target).parts
                cat_counter[parts[0]] += 1
            except ValueError:
                cat_counter["自定义"] += 1

        # 构建文件预览表格
        preview_rows = []
        for i, (src, dst) in enumerate(self.plan):
            try:
                rel = dst.relative_to(target)
                cat = rel.parts[0] if rel.parts else "其他"
            except ValueError:
                cat = "自定义"

            preview_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(src.name, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=160)),
                        ft.DataCell(self._build_category_chip(cat)),
                        ft.DataCell(ft.Text(str(dst.parent), size=11, color=ft.Colors.GREY_600, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, width=280)),
                        ft.DataCell(
                            ft.IconButton(
                                ft.Icons.FOLDER_OPEN,
                                tooltip="修改目标目录",
                                icon_size=18,
                                icon_color=ft.Colors.BLUE_700,
                                on_click=lambda e, idx=i: self._change_target(idx),
                            )
                        ),
                    ],
                ),
            )

        preview_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("文件名", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("分类", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("目标目录", weight=ft.FontWeight.BOLD, size=12)),
                ft.DataColumn(ft.Text("操作", weight=ft.FontWeight.BOLD, size=12)),
            ],
            rows=preview_rows,
            column_spacing=12,
            horizontal_margin=8,
            heading_row_height=36,
            data_row_min_height=36,
            data_row_max_height=44,
        )

        # 分类统计栏
        summary = ft.Row(
            controls=[
                ft.Text(f"共 {total} 个文件", size=13, weight=ft.FontWeight.BOLD),
                ft.Text(f"  |  ", size=13, color=ft.Colors.GREY_400),
                *[
                    ft.Text(f"{cat}: {count}", size=12, color=ft.Colors.GREY_600)
                    for cat, count in cat_counter.most_common()
                ],
            ],
            wrap=True,
        )

        self._preview_dialog_ref = None  # 用于外部引用

        def on_confirm(e):
            self._preview_dialog_ref.open = False
            self.page.update()
            self._start_organize()

        def on_cancel(e):
            self._preview_dialog_ref.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"整理预览 — {total} 个文件"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        summary,
                        ft.Container(
                            content=ft.ListView(
                                controls=[preview_table],
                                height=350,
                                auto_scroll=False,
                            ),
                            bgcolor=ft.Colors.GREY_50,
                            border_radius=8,
                            padding=8,
                        ),
                        ft.Text("点击 📁 图标可修改单个文件的目标目录", size=11, color=ft.Colors.GREY_500),
                    ],
                    spacing=8,
                ),
                width=650,
                height=450,
            ),
            actions=[
                ft.TextButton("取消", on_click=on_cancel),
                ft.FilledButton(
                    "确认整理",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_700),
                    on_click=on_confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._preview_dialog_ref = dialog
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _change_target(self, plan_index: int):
        """点击修改按钮 → 打开文件夹选择器"""
        self._editing_plan_index = plan_index
        self.folder_picker.get_directory_path(dialog_title="选择目标文件夹")

    def _on_folder_picked(self, e: ft.FilePickerResultEvent):
        """文件夹选择回调"""
        if not e.path or self._editing_plan_index is None:
            return

        new_root = Path(e.path)

        # 全局根目录修改
        if self._editing_plan_index == -1:
            self._editing_plan_index = None
            self._change_global_root(new_root)
            return

        # 单个文件目标修改
        idx = self._editing_plan_index
        if idx >= len(self.plan):
            return

        src, old_dst = self.plan[idx]
        new_dst = new_root / src.name

        # 处理重名
        counter = 1
        while new_dst.exists():
            new_dst = new_root / f"{src.stem}_{counter}{src.suffix}"
            counter += 1

        # 更新 plan
        self.plan[idx] = (src, new_dst)

        # 同步更新对应 FileInfo 的 target_path
        for f in self.files:
            if f.path == src:
                f.target_path = new_dst
                break

        # 记录自定义目标
        self.custom_targets[str(src)] = str(new_root)

        # 刷新预览对话框
        self._editing_plan_index = None
        self._refresh_preview()

    def _change_global_root(self, new_root: Path):
        """更改全局目标根目录，重新生成 plan"""

        # 重新计算 plan
        new_plan = []
        for src, old_dst in self.plan:
            # 从旧目标路径推断分类子目录
            try:
                old_rel = old_dst.relative_to(get_target_root())
                cat_sub = old_rel.parent  # e.g. "文档" or "图片/2025-05"
                new_dst = new_root / cat_sub / src.name
            except ValueError:
                # 自定义目标的文件，保留其子目录结构
                new_dst = new_root / old_dst.parent.name / src.name

            # 处理重名
            counter = 1
            while new_dst.exists():
                new_dst = new_root / cat_sub / f"{src.stem}_{counter}{src.suffix}"
                counter += 1

            new_plan.append((src, new_dst))

            # 更新 FileInfo
            for f in self.files:
                if f.path == src:
                    f.target_path = new_dst
                    break

        self.plan = new_plan
        self._show_snackbar(f"目标目录已更改为：{new_root}", ft.Colors.GREEN_700)

        # 刷新预览（如果有打开的预览对话框）
        if self._preview_dialog_ref and self._preview_dialog_ref.open:
            self._refresh_preview()

    def _refresh_preview(self):
        """关闭旧预览，重新打开（刷新内容）"""
        if self._preview_dialog_ref:
            self._preview_dialog_ref.open = False
            self.page.update()
        self._show_preview()

    def _start_organize(self):
        """开始整理"""
        self.is_organizing = True
        self.btn_organize.disabled = True
        self.btn_organize.text = "整理中..."
        self.btn_scan.disabled = True
        self.progress_bar.value = 0
        self.status_text.value = "正在整理文件..."
        self.page.update()

        threading.Thread(target=self._organize_worker, daemon=True).start()

    def _organize_worker(self):
        """后台整理"""
        log_path = get_target_root() / "organize_log.json"

        def on_progress(current, total):
            ratio = current / total if total > 0 else 0
            self.page.run_thread(lambda: self._update_progress(ratio))
            self.page.run_thread(lambda: self._update_status(f"正在整理... {current}/{total}"))

        result = self.organizer.execute(self.plan, log_path=log_path, progress_cb=on_progress)
        self.organize_result = result
        self.page.run_thread(self._organize_done)

    def _organize_done(self):
        """整理完成"""
        self.is_organizing = False
        self.btn_organize.disabled = False
        self.btn_organize.text = "整理文件"
        self.btn_scan.disabled = False
        self.progress_bar.value = 1

        r = self.organize_result
        moved = len(r["moved"])
        skipped = len(r["skipped"])
        errors = len(r["errors"])
        self.status_text.value = f"整理完成！已移动 {moved} 个，跳过 {skipped} 个，错误 {errors} 个"
        self._show_snackbar(f"已整理 {moved} 个文件", ft.Colors.GREEN_700)

        self.data_table.rows.clear()
        self.files.clear()
        self.plan.clear()
        self.page.update()

    def _on_undo(self, e):
        """撤销按钮"""
        log_path = get_target_root() / "organize_log.json"
        if not log_path.exists():
            self._show_snackbar("没有找到整理记录，无法撤销", ft.Colors.ORANGE_700)
            return

        def on_confirm(e):
            dialog.open = False
            self.page.update()
            self._start_undo()

        def on_cancel(e):
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("确认撤销"),
            content=ft.Text("确定要撤销上次整理吗？\n文件将恢复到原来的位置。"),
            actions=[
                ft.TextButton("取消", on_click=on_cancel),
                ft.FilledButton(
                    "确认撤销",
                    style=ft.ButtonStyle(bgcolor=ft.Colors.ORANGE_700),
                    on_click=on_confirm,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _start_undo(self):
        """开始撤销"""
        self.btn_undo.disabled = True
        self.btn_undo.text = "撤销中..."
        self.btn_scan.disabled = True
        self.btn_organize.disabled = True
        self.progress_bar.value = 0
        self.status_text.value = "正在撤销..."
        self.page.update()

        threading.Thread(target=self._undo_worker, daemon=True).start()

    def _undo_worker(self):
        """后台撤销"""
        log_path = get_target_root() / "organize_log.json"
        result = self.organizer.undo(log_path)
        self.undo_result = result
        self.page.run_thread(self._undo_done)

    def _undo_done(self):
        """撤销完成"""
        self.btn_undo.disabled = False
        self.btn_undo.text = "撤销整理"
        self.btn_scan.disabled = False
        self.progress_bar.value = 1

        result = self.undo_result
        restored = len(result["restored"])
        errors = len(result["errors"])

        if errors > 0:
            msg = f"已恢复 {restored} 个文件\n{errors} 个文件恢复失败（可再次尝试撤销）"
        else:
            msg = f"已恢复 {restored} 个文件"

        self.status_text.value = f"撤销完成：{msg}"
        self._show_snackbar(msg, ft.Colors.GREEN_700 if errors == 0 else ft.Colors.ORANGE_700)
        self.page.update()

    def _open_settings(self, e):
        """设置对话框"""
        rules = {**EXT_MAP, **load_user_rules()}

        rules_column = ft.Column(
            controls=[
                ft.ListTile(
                    title=ft.Text(ext),
                    subtitle=ft.Text(cat),
                    trailing=ft.IconButton(
                        ft.Icons.DELETE,
                        icon_color=ft.Colors.RED_700,
                        on_click=lambda e, ext=ext: self._delete_rule(ext, rules_column),
                    ),
                )
                for ext, cat in sorted(rules.items())
            ],
            spacing=0,
            height=300,
            scroll=ft.ScrollMode.AUTO,
        )

        ext_field = ft.TextField(hint_text="扩展名（如 .xyz）", width=150, border_radius=8)
        cat_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(cat) for cat in CATEGORIES.keys()],
            value=list(CATEGORIES.keys())[0],
            width=120,
            border_radius=8,
        )

        def add_rule(e):
            ext = ext_field.value.strip()
            if not ext:
                return
            if not ext.startswith("."):
                ext = "." + ext
            cat = cat_dropdown.value
            user_rules = load_user_rules()
            user_rules[ext] = cat
            save_user_rules(user_rules)
            rules_column.controls.append(
                ft.ListTile(
                    title=ft.Text(ext),
                    subtitle=ft.Text(cat),
                    trailing=ft.IconButton(
                        ft.Icons.DELETE,
                        icon_color=ft.Colors.RED_700,
                        on_click=lambda e, ext=ext: self._delete_rule(ext, rules_column),
                    ),
                ),
            )
            ext_field.value = ""
            self.page.update()

        def close_dialog(e):
            dialog.open = False
            self.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("自定义分类规则"),
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=rules_column,
                        bgcolor=ft.Colors.GREY_50,
                        border_radius=8,
                        padding=8,
                    ),
                    ft.Row(
                        controls=[
                            ext_field,
                            cat_dropdown,
                            ft.FilledButton(
                                "添加",
                                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_700, shape=ft.RoundedRectangleBorder(radius=8)),
                                on_click=add_rule,
                            ),
                        ],
                        spacing=12,
                    ),
                ],
                spacing=16,
                width=500,
            ),
            actions=[
                ft.TextButton("关闭", on_click=close_dialog),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def _delete_rule(self, ext: str, rules_column: ft.Column):
        """删除规则"""
        rules = load_user_rules()
        if ext in rules:
            del rules[ext]
            save_user_rules(rules)
        rules_column.controls = [c for c in rules_column.controls if c.title.value != ext]
        self.page.update()

    def _on_change_root(self, e):
        """更改目标根目录"""
        # 复用同一个 picker，但用标记区分用途
        self._editing_plan_index = -1  # -1 表示修改全局根目录
        self.folder_picker.get_directory_path(dialog_title="选择整理目标根目录")

    def _update_progress(self, value: float):
        self.progress_bar.value = value
        self.page.update()

    def _update_status(self, text: str):
        self.status_text.value = text
        self.page.update()

    def _show_snackbar(self, message: str, color: str = ft.Colors.BLUE_700):
        """显示提示条"""
        snackbar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),
            bgcolor=color,
            duration=3000,
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()


def main(page: ft.Page):
    """应用入口"""
    FileOrganizerApp(page)


if __name__ == "__main__":
    ft.app(target=main)
