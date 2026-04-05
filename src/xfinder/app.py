import flet as ft
import time
import subprocess
import threading
import platform
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from queue import Queue
from .sdk import get_sdk

class EventBus:
    """事件总线类，用于管理事件的发送和处理"""
    def __init__(self):
        self.queue = Queue()
        self.running = False
        self.thread = None
        self.handlers = {}
    
    def register_handler(self, event_type, handler):
        """注册事件处理器"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def send_event(self, event_type, **kwargs):
        """发送事件"""
        self.queue.put((event_type, kwargs))
    
    def start(self):
        """启动事件处理线程"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._process_events, daemon=True)
            self.thread.start()
    
    def stop(self):
        """停止事件处理线程"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
    
    def _process_events(self):
        """处理事件队列"""
        while self.running:
            try:
                event_type, kwargs = self.queue.get(block=True, timeout=0.1)
                if event_type in self.handlers:
                    for handler in self.handlers[event_type]:
                        try:
                            handler(**kwargs)
                        except Exception as e:
                            print(f"Error handling event {event_type}: {e}")
                self.queue.task_done()
            except Exception:
                continue

class XFinderApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "xfinder"
        self.page.window_width = 1200
        self.page.window_height = 800
        self.page.window_min_width = 900
        self.page.window_min_height = 600
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 0
        self.page.spacing = 0
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.page.vertical_alignment = ft.CrossAxisAlignment.STRETCH

        try:
            self.sdk = get_sdk()
            self.status_text = "正在构建索引..."
        except Exception as e:
            self.sdk = None
            self.status_text = f"初始化失败: {str(e)}"

        self.search_results = []
        self.current_query = ""
        self.is_building_index = False

        # 排序状态
        self.sort_column = "name"
        self.sort_ascending = True

        # 筛选状态
        self.file_type_filter = "All"
        self.item_type_filter_value = "All"

        # 列宽
        self.col_name_width = 0
        self.col_path_width = 0
        self.col_size_width = 0
        self.col_date_width = 0
        self.col_type_width = 0

        # 索引构建线程
        self.index_thread = None

        # 事件总线
        self.event_bus = EventBus()
        self._register_event_handlers()
        self.event_bus.start()

        self.init_ui()

    def init_ui(self):
        # 搜索输入框
        self.search_field = ft.TextField(
            hint_text="输入搜索关键词，实时显示结果...",
            on_change=self.on_search,
            autofocus=True,
            border=ft.InputBorder.OUTLINE,
            border_radius=0,
            text_size=14,
            height=35,
            content_padding=ft.Padding(left=10, top=8, right=10, bottom=8),
        )

        # 目录选择框
        # 默认扫描用户桌面目录
        desktop_path = str(Path.home() / "Downloads")
        self.directory_input = ft.TextField(
            value=desktop_path,
            hint_text="选择扫描目录",
            width=200,
            height=35,
            text_size=13,
        )
        
        # 浏览按钮
        self.browse_button = ft.ElevatedButton(
            "浏览",
            on_click=self.browse_directory,
            height=35,
            style=ft.ButtonStyle(
                text_style=ft.TextStyle(size=13)
            )
        )

        # 文件类型筛选
        self.type_filter = ft.Dropdown(
            options=[
                ft.dropdown.Option("全部"),
                ft.dropdown.Option(".py"),
                ft.dropdown.Option(".txt"),
                ft.dropdown.Option(".md"),
                ft.dropdown.Option(".json"),
                ft.dropdown.Option(".yaml"),
                ft.dropdown.Option(".toml"),
                ft.dropdown.Option(".lock"),
                ft.dropdown.Option(".ts"),
                ft.dropdown.Option(".js"),
                ft.dropdown.Option(".html"),
                ft.dropdown.Option(".css"),
                ft.dropdown.Option(".pdf"),
                ft.dropdown.Option(".jpg"),
                ft.dropdown.Option(".png"),
                ft.dropdown.Option(".mp4"),
                ft.dropdown.Option(".mp3"),
                ft.dropdown.Option(".zip"),
            ],
            width=120,
            height=35,
            text_size=13,
            value="全部",  # 设置默认值为全部
            on_select=self.on_filter_change,
        )
        
        # 文件/文件夹筛选
        self.item_type_filter = ft.Dropdown(
            options=[
                ft.dropdown.Option("全部"),
                ft.dropdown.Option("文件"),
                ft.dropdown.Option("文件夹"),
            ],
            width=100,
            height=35,
            text_size=13,
            value="全部",  # 设置默认值为全部
            on_select=self.on_filter_change,
        )

        # 搜索按钮
        self.search_button = ft.ElevatedButton(
            "搜索",
            on_click=self.on_search,
            height=35,
            style=ft.ButtonStyle(
                text_style=ft.TextStyle(size=13)
            )
        )

        # 搜索工具栏
        search_toolbar = ft.Container(
            content=ft.Column([
                # 第一行：搜索框和按钮
                ft.Row([
                    ft.Icon(ft.Icons.SEARCH, size=18, color="#666666"),
                    self.search_field,
                    self.search_button,
                ], spacing=10, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                # 第二行：筛选选项
                ft.Row([
                    ft.Container(
                        content=ft.Text("扫描目录:", size=13, color="#666666"),
                        padding=ft.Padding(left=20, top=5, right=5, bottom=0),
                    ),
                    self.directory_input,
                    self.browse_button,
                    ft.Container(
                        content=ft.Text("文件类型:", size=13, color="#666666"),
                        padding=ft.Padding(left=20, top=5, right=5, bottom=0),
                    ),
                    self.type_filter,
                    ft.Container(
                        content=ft.Text("类型:", size=13, color="#666666"),
                        padding=ft.Padding(left=20, top=5, right=5, bottom=0),
                    ),
                    self.item_type_filter,
                ], spacing=10, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ], spacing=5),
            padding=ft.Padding(left=10, top=5, right=10, bottom=5),
            bgcolor="#ffffff",
            border=ft.border.all(1, "#d0d0d0"),
        )

        # 列标题行（类似Everything的列头）
        self.header_row = ft.Container(
            content=ft.Row([
                self._create_header_cell("名称", "name", 300),
                self._create_header_cell("路径", "path", 350),
                self._create_header_cell("大小", "size", 100),
                self._create_header_cell("类型", "type", 80),
                self._create_header_cell("修改时间", "mtime", 180),
            ], spacing=0, alignment=ft.MainAxisAlignment.START),
            bgcolor="#f0f0f0",
            border=ft.border.all(1, "#d0d0d0"),
            padding=ft.Padding(left=0, top=0, right=0, bottom=0),
            height=28,
        )

        # 结果DataTable
        self.result_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("名称", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("路径", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("大小", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("类型", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("修改时间", size=12, weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            column_spacing=0,
            horizontal_margin=0,
            divider_thickness=0.5,
        )

        # 结果容器
        self.result_container = ft.Container(
            content=ft.ListView(
                [self.result_table],
                expand=True,
                spacing=0,
                padding=0,
            ),
            expand=True,
            bgcolor="#ffffff",
            border=ft.border.all(1, "#d0d0d0"),
        )

        # 状态栏
        self.status_bar = ft.Container(
            content=ft.Row([
                ft.Text(self.status_text, size=11, color="#666666"),
            ], alignment=ft.MainAxisAlignment.START),
            padding=ft.Padding(left=10, top=4, right=10, bottom=4),
            bgcolor="#f0f0f0",
            border=ft.border.only(top=ft.BorderSide(width=1, color="#d0d0d0")),
            height=28,
        )

        # 索引构建进度条
        self.progress_bar = ft.ProgressBar(
            width=200,
            color="#0078d4",
            bgcolor="#e0e0e0",
        )

        self.progress_container = ft.Container(
            content=ft.Row([
                ft.Text("构建索引中...", size=11, color="#666666"),
                self.progress_bar,
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            padding=ft.Padding(left=10, top=4, right=10, bottom=4),
            bgcolor="#fff9e6",
            visible=False,
            height=28,
        )

        # 主布局
        self.page.add(
            ft.Column([
                search_toolbar,
                self.header_row,
                self.result_container,
                self.progress_container,
                self.status_bar,
            ], expand=True, spacing=0),
        )

        # 启动后自动构建索引
        self.event_bus.send_event("build_index")
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        self.event_bus.register_handler("search", self._handle_search_event)
        self.event_bus.register_handler("filter_change", self._handle_filter_change_event)
        self.event_bus.register_handler("build_index", self._build_index_async)
        self.event_bus.register_handler("sort_change", self._handle_sort_change_event)
    
    def _handle_search_event(self, query=None):
        """处理搜索事件"""
        if self.is_building_index:
            def update_ui():
                self.status_bar.content.controls[0].value = "索引构建中，请稍候..."
                self.page.update()
            import threading
            threading.Timer(0.1, update_ui).start()
            return

        if not query:
            query = self.search_field.value.strip() if self.search_field.value else ""
        
        if not query:
            def update_ui():
                self.search_results = []
                self.result_table.rows.clear()
                self.status_bar.content.controls[0].value = "输入关键词开始搜索"
                self.page.update()
            import threading
            threading.Timer(0.1, update_ui).start()
            return

        if not self.sdk:
            def update_ui():
                self.status_bar.content.controls[0].value = "SDK未初始化"
                self.page.update()
            import threading
            threading.Timer(0.1, update_ui).start()
            return

        self.current_query = query
        # 获取筛选值
        self.file_type_filter = self.type_filter.value
        self.item_type_filter_value = self.item_type_filter.value

        # 执行搜索
        self.perform_search()
    
    def _handle_filter_change_event(self):
        """处理筛选条件变化事件"""
        if self.is_building_index:
            def update_ui():
                self.status_bar.content.controls[0].value = "索引构建中，请稍候..."
                self.page.update()
            import threading
            threading.Timer(0.1, update_ui).start()
            return

        query = self.search_field.value.strip() if self.search_field.value else ""
        if not query:
            return

        if not self.sdk:
            def update_ui():
                self.status_bar.content.controls[0].value = "SDK未初始化"
                self.page.update()
            import threading
            threading.Timer(0.1, update_ui).start()
            return

        # 获取筛选值
        self.file_type_filter = self.type_filter.value
        self.item_type_filter_value = self.item_type_filter.value

        # 执行搜索
        self.perform_search()

    def _create_header_cell(self, label, column_key, width):
        """创建列标题单元格"""
        return ft.Container(
            content=ft.Row([
                ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color="#333333"),
                ft.Icon(
                    ft.Icons.ARROW_UPWARD if (self.sort_column == column_key and self.sort_ascending) else
                    ft.Icons.ARROW_DOWNWARD if (self.sort_column == column_key and not self.sort_ascending) else
                    ft.Icons.ARROW_DOWNWARD,
                    size=12,
                    color="#999999" if self.sort_column != column_key else "#0078d4",
                ),
            ], spacing=2, alignment=ft.MainAxisAlignment.START),
            width=width,
            padding=ft.Padding(left=8, top=4, right=4, bottom=4),
            on_click=lambda e, col=column_key: self._on_sort_change(col),
        )

    def _on_sort_change(self, column):
        """处理排序切换，发送排序变化事件到事件总线"""
        self.event_bus.send_event("sort_change", column=column)
    
    def _handle_sort_change_event(self, column):
        """处理排序变化事件"""
        if self.sort_column == column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True

        def update_ui():
            self._update_header()
            self._apply_sort_to_results()
            self.display_results()
        
        # 使用定时器在主线程中更新UI
        import threading
        threading.Timer(0.1, update_ui).start()

    def _update_header(self):
        """更新列标题箭头"""
        self.header_row.content.controls.clear()
        for col_info in [("名称", "name", 300), ("路径", "path", 350), ("大小", "size", 100), ("类型", "type", 80), ("修改时间", "mtime", 180)]:
            label, col_key, width = col_info
            self.header_row.content.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(label, size=12, weight=ft.FontWeight.BOLD, color="#333333"),
                        ft.Icon(
                            ft.Icons.ARROW_UPWARD if (self.sort_column == col_key and self.sort_ascending) else
                            ft.Icons.ARROW_DOWNWARD,
                            size=12,
                            color="#999999" if self.sort_column != col_key else "#0078d4",
                        ),
                    ], spacing=2, alignment=ft.MainAxisAlignment.START),
                    width=width,
                    padding=ft.Padding(left=8, top=4, right=4, bottom=4),
                    on_click=lambda e, col=col_key: self._on_sort_change(col),
                )
            )
        self.page.update()

    def _build_index_async(self):
        """异步构建索引"""
        # 先在主线程中更新UI
        self.is_building_index = True
        self.progress_container.visible = True
        self.status_bar.content.controls[0].value = "正在构建索引..."
        
        # 强制更新页面
        self.page.update()

        def build():
            try:
                # 获取目录输入框中的路径
                directory = self.directory_input.value.strip()
                if not directory:
                    directory = str(Path.home())

                # 执行索引构建
                result = self.sdk.build_index(directory=directory)

                # 在主线程中更新UI
                def update_ui_after():
                    self.is_building_index = False
                    self.progress_container.visible = False
                    self.status_text = f"索引构建完成，耗时 {result['time']*1000:.0f}ms"
                    self.status_bar.content.controls[0].value = self.status_text
                    self.page.update()
                
                # 使用定时器在主线程中更新UI
                import threading
                threading.Timer(0.1, update_ui_after).start()
            except Exception as e:
                # 在主线程中更新UI
                def update_ui_error():
                    self.is_building_index = False
                    self.progress_container.visible = False
                    self.status_text = f"索引构建失败: {str(e)}"
                    self.status_bar.content.controls[0].value = self.status_text
                    self.page.update()
                
                # 使用定时器在主线程中更新UI
                import threading
                threading.Timer(0.1, update_ui_error).start()

        # 直接启动新的索引构建线程，不等待之前的线程
        # 这样可以避免界面卡顿，让用户操作更流畅
        self.index_thread = threading.Thread(target=build, daemon=True)
        self.index_thread.start()



    def on_search(self, e=None):
        """搜索事件触发，发送搜索事件到事件总线"""
        self.event_bus.send_event("search")

    def on_filter_change(self, e=None):
        """筛选条件变化时触发，发送筛选变化事件到事件总线"""
        self.event_bus.send_event("filter_change")

    def perform_search(self):
        """在单独的线程中执行搜索，避免阻塞主线程"""
        def search_thread():
            try:
                start_time = time.time()

                sort_map = {
                    "name": "name",
                    "path": "name",
                    "size": "size",
                    "mtime": "time",
                    "type": "name",
                }
                sort_by = sort_map.get(self.sort_column, "relevance")

                # 构建搜索参数
                params = {"query": self.current_query, "sort_by": sort_by, "limit": 1000}
                
                # 添加文件类型筛选
                if self.file_type_filter and self.file_type_filter != "全部":
                    file_type = self.file_type_filter.lstrip(".")
                    params["file_type"] = file_type

                # 执行搜索
                result = self.sdk.search(**params)
                end_time = time.time()

                search_results = result.get("results", [])

                # 手动筛选结果，确保只显示匹配的文件类型
                if self.file_type_filter and self.file_type_filter != "全部":
                    file_type = self.file_type_filter.lstrip(".")
                    search_results = [item for item in search_results if item.get("extension", "").lstrip(".") == file_type]

                # 手动筛选文件/文件夹类型
                if self.item_type_filter_value and self.item_type_filter_value != "全部":
                    if self.item_type_filter_value == "文件":
                        search_results = [item for item in search_results if not item.get("is_directory", False)]
                    elif self.item_type_filter_value == "文件夹":
                        search_results = [item for item in search_results if item.get("is_directory", False)]

                # 对结果排序
                sort_key_map = {
                    "name": lambda x: x.get("name", "").lower(),
                    "path": lambda x: x.get("path", "").lower(),
                    "size": lambda x: x.get("size", 0),
                    "mtime": lambda x: x.get("mtime", 0),
                    "type": lambda x: x.get("extension", ""),
                }
                key_func = sort_key_map.get(self.sort_column, sort_key_map["name"])
                search_results.sort(key=key_func, reverse=not self.sort_ascending)

                # 在主线程中更新UI
                def update_ui():
                    self.search_results = search_results
                    self.display_results()
                    count = len(self.search_results)
                    self.status_bar.content.controls[0].value = f"找到 {count} 个结果，耗时 {(end_time-start_time)*1000:.0f}ms"
                    self.page.update()

                # 使用定时器在主线程中更新UI
                import threading
                threading.Timer(0.1, update_ui).start()
            except Exception as e:
                # 在主线程中更新UI
                def update_ui_error():
                    self.status_bar.content.controls[0].value = f"搜索失败: {str(e)}"
                    self.page.update()

                # 使用定时器在主线程中更新UI
                import threading
                threading.Timer(0.1, update_ui_error).start()

        # 启动搜索线程
        search_thread = threading.Thread(target=search_thread, daemon=True)
        search_thread.start()

    def _apply_sort_to_results(self):
        """对搜索结果排序"""
        if not self.search_results:
            return

        sort_key_map = {
            "name": lambda x: x.get("name", "").lower(),
            "path": lambda x: x.get("path", "").lower(),
            "size": lambda x: x.get("size", 0),
            "mtime": lambda x: x.get("mtime", 0),
            "type": lambda x: x.get("extension", ""),
        }

        key_func = sort_key_map.get(self.sort_column, sort_key_map["name"])
        self.search_results.sort(key=key_func, reverse=not self.sort_ascending)

    def _format_size(self, size):
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024*1024):.1f} MB"
        else:
            return f"{size/(1024*1024*1024):.1f} GB"

    def _format_time(self, timestamp):
        """格式化时间戳"""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

    def _get_file_type(self, extension, is_directory):
        """获取文件类型描述"""
        if is_directory:
            return "文件夹"
        ext = extension.lower().lstrip(".")
        type_map = {
            "py": "Python",
            "js": "JavaScript",
            "ts": "TypeScript",
            "html": "HTML",
            "css": "CSS",
            "json": "JSON",
            "yaml": "YAML",
            "yml": "YAML",
            "toml": "TOML",
            "txt": "文本文件",
            "md": "Markdown",
            "pdf": "PDF",
            "jpg": "JPEG 图像",
            "jpeg": "JPEG 图像",
            "png": "PNG 图像",
            "gif": "GIF 图像",
            "mp4": "MP4 视频",
            "mp3": "MP3 音频",
            "zip": "ZIP 压缩",
            "rar": "RAR 压缩",
            "doc": "Word 文档",
            "docx": "Word 文档",
            "xls": "Excel 表格",
            "xlsx": "Excel 表格",
        }
        return type_map.get(ext, f"{extension.upper()} 文件") if ext else "文件"

    def display_results(self):
        self.result_table.rows.clear()

        if not self.search_results:
            self.page.update()
            return

        # 确保搜索结果不为空
        if len(self.search_results) > 0:
            for item in self.search_results[:500]:  # 限制显示500条
                try:
                    path = item.get("path", "")
                    name = item.get("name", "")
                    size = item.get("size", 0)
                    mtime = item.get("mtime", 0)
                    is_directory = item.get("is_directory", False)
                    extension = item.get("extension", "")

                    size_str = self._format_size(size) if not is_directory else ""
                    mtime_str = self._format_time(mtime)
                    type_str = self._get_file_type(extension, is_directory)

                    # 创建数据行
                    row = ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(name, size=12, color="#333333", overflow=ft.TextOverflow.ELLIPSIS)),
                            ft.DataCell(ft.Text(path, size=11, color="#666666", overflow=ft.TextOverflow.ELLIPSIS)),
                            ft.DataCell(ft.Text(size_str, size=11, color="#666666")),
                            ft.DataCell(ft.Text(type_str, size=11, color="#666666")),
                            ft.DataCell(ft.Text(mtime_str, size=11, color="#666666")),
                        ],
                        on_select_change=lambda e, p=path: self.open_item(p),
                    )
                    self.result_table.rows.append(row)
                except Exception as e:
                    # 打印错误信息以便调试
                    print(f"Error creating row: {e}")
                    continue

        # 强制更新页面
        self.page.update()

    def browse_directory(self, e=None):
        """浏览选择目录"""
        try:
            # 使用tkinter打开文件夹选择对话框
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            root.attributes('-topmost', True)  # 确保对话框在最前面
            
            # 打开文件夹选择对话框
            directory = filedialog.askdirectory(
                title="选择扫描目录",
                initialdir=self.directory_input.value
            )
            
            # 关闭tkinter窗口
            root.destroy()
            
            # 如果选择了目录，更新输入框并重新构建索引
            if directory and directory != self.directory_input.value:
                self.directory_input.value = directory
                self.page.update()
                
                # 重新构建索引
                self.event_bus.send_event("build_index")
        except Exception as e:
            self.status_bar.content.controls[0].value = f"浏览失败: {str(e)}"
            self.page.update()

    def open_item(self, path):
        """打开文件/文件夹"""
        try:
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["open", path], check=True)
            elif system == "Windows":
                subprocess.run(["start", path], shell=True, check=True)
            else:
                subprocess.run(["xdg-open", path], check=True)
        except Exception as e:
            self.status_bar.content.controls[0].value = f"打开失败: {str(e)}"
            self.page.update()


def run_app():
    def main(page: ft.Page):
        app = XFinderApp(page)

    ft.app(target=main)


if __name__ == "__main__":
    run_app()
