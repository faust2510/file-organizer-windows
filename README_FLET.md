# 妈妈文件整理助手 - Flet 现代化版本

## 🎨 版本对比

| 特性 | 旧版本 (CustomTkinter) | 新版本 (Flet) |
|------|------------------------|---------------|
| **UI 框架** | CustomTkinter | Flet (Flutter) |
| **设计风格** | 传统桌面应用 | Material Design 3 |
| **动画效果** | 无 | 流畅动画 |
| **主题支持** | 暗色/亮色 | 自动适配系统主题 |
| **响应式** | 固定布局 | 自适应布局 |
| **跨平台** | Windows/macOS/Linux | Windows/macOS/Linux/Web |

## 🚀 快速开始

### 方式一：直接运行（开发模式）

```bash
# 1. 安装依赖
pip install -r requirements_flet.txt

# 2. 运行 Flet 版本
python main_flet.py
```

### 方式二：打包为 exe（给妈妈用）

```bash
# Windows 用户直接双击
build_flet.bat
```

打包完成后，可执行文件在 `dist/妈妈文件整理助手.exe`

## 📁 文件说明

```
file-organizer-windows/
├── main_flet.py          # Flet 版本入口
├── gui_flet.py           # Flet 版本 GUI 界面
├── requirements_flet.txt # Flet 版本依赖
├── build_flet.bat        # Flet 版本打包脚本
├── README_FLET.md        # 本文档
│
├── main.py               # 旧版本入口（保留）
├── gui.py                # 旧版本 GUI（保留）
├── config.py             # 配置文件（共用）
├── organizer.py          # 核心逻辑（共用）
├── search.py             # 搜索功能（共用）
└── requirements.txt      # 旧版本依赖（保留）
```

## ✨ 新版本特性

### 1. 现代化界面
- **Material Design 3** 设计语言
- **圆角卡片** 布局
- **柔和配色**，不刺眼
- **分类标签** 带颜色区分

### 2. 流畅动画
- 按钮点击 **涟漪效果**
- 进度条 **平滑动画**
- 对话框 **弹出动画**

### 3. 更好的交互
- **即时搜索** - 输入即筛选
- **SnackBar 提示** - 操作反馈更友好
- **确认对话框** - 防止误操作

### 4. 响应式布局
- 窗口可自由调整大小
- 最小尺寸限制（800x600）
- 列表自适应高度

## 🎯 功能对比

| 功能 | 旧版本 | 新版本 | 说明 |
|------|:------:|:------:|------|
| 扫描文件 | ✅ | ✅ | 完全保留 |
| 整理文件 | ✅ | ✅ | 完全保留 |
| 撤销整理 | ✅ | ✅ | 完全保留 |
| 搜索筛选 | ✅ | ✅ | 即时搜索 |
| 自定义规则 | ✅ | ✅ | Material 对话框 |
| 文件列表 | 表格 | DataTable | 更现代 |
| 进度条 | 基础 | 动画 | 更流畅 |
| 提示信息 | 弹窗 | SnackBar | 更友好 |

## 🔧 自定义修改

### 修改主题颜色

在 `gui_flet.py` 的 `_setup_page` 方法中：

```python
self.page.theme = ft.Theme(
    color_scheme_seed=ft.Colors.BLUE,  # 改成你想要的颜色
)
```

可选颜色：
- `ft.Colors.BLUE` - 蓝色（默认）
- `ft.Colors.GREEN` - 绿色
- `ft.Colors.PURPLE` - 紫色
- `ft.Colors.ORANGE` - 橙色

### 修改窗口大小

```python
self.page.window.width = 1200   # 宽度
self.page.window.height = 800   # 高度
```

## 🐛 常见问题

### Q: 运行时报错 "No module named 'flet'"
A: 确保已安装 flet：
```bash
pip install flet
```

### Q: 打包后 exe 无法运行
A: 检查是否所有依赖都已打包：
```bash
pip install pyinstaller
pyinstaller --onefile --windowed main_flet.py
```

### Q: 界面显示异常
A: 尝试更新 flet 到最新版本：
```bash
pip install --upgrade flet
```

## 📝 更新日志

### v2.0 (Flet 版本)
- ✨ 全新 Material Design 3 界面
- ✨ 流畅动画效果
- ✨ 即时搜索功能
- ✨ 响应式布局
- ✨ SnackBar 提示
- ✨ 分类标签颜色区分

### v1.0 (CustomTkinter 版本)
- 🎉 初始版本
- ✅ 基础文件整理功能
- ✅ 搜索筛选
- ✅ 自定义规则

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
