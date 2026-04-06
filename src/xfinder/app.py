import flet as ft
import time
import subprocess
import threading
import platform
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from queue import Queue
import logging
import os
from xfinder.sdk import get_sdk

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
                            self.logger.error(f"Error handling event {event_type}: {e}")
                self.queue.task_done()
            except Exception:
                continue

class XFinderApp:
    """XFinder应用程序主类
    
    负责初始化UI界面，处理用户交互，管理事件总线，以及协调搜索和索引功能
    """
    def __init__(self, page: ft.Page):
        """初始化应用程序
        
        Args:
            page: Flet页面对象
        """
        self.page = page
        self.page.title = "XFinder"
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

        self.search_results = []  # 搜索结果列表
        self.current_query = ""  # 当前搜索查询
        self.is_building_index = False  # 索引构建状态

        # 排序状态
        self.sort_column = "name"  # 当前排序列
        self.sort_ascending = True  # 是否升序排序

        # 筛选状态
        self.file_type_filter = "All"  # 文件类型筛选
        self.item_type_filter_value = "All"  # 项目类型筛选（文件/文件夹）

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

        # 初始化日志
        self._init_logging()

        # 注册快捷键
        self.page.on_keyboard_event = self._on_keyboard_event

        self.init_ui()

    def init_ui(self):
        # 搜索输入框
        self.search_field = ft.TextField(
            hint_text="输入搜索关键词，实时显示结果...",
            on_change=self.on_search,
            autofocus=True,
            border=ft.InputBorder.OUTLINE,
            border_radius=0,
            text_size=13,
            height=35,
            content_padding=ft.Padding(left=10, top=8, right=10, bottom=8),
        )

        # 目录选择框
        # 默认扫描用户桌面目录
        desktop_path = str(Path.home() / "Downloads")
        self.directory_input = ft.TextField(
            value=desktop_path,
            hint_text="选择扫描目录",
            height=35,
            text_size=13,
        )
        
        # 重新构建按钮
        self.rebuild_button = ft.ElevatedButton(
            "重新构建",
            on_click=self.rebuild_index,
            height=35,
            style=ft.ButtonStyle(
                text_style=ft.TextStyle(size=13)
            )
        )
        
        # 权限设置按钮
        self.permission_button = ft.ElevatedButton(
            "权限设置",
            on_click=self.open_permission_settings,
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
            content=ft.Row([
                # 搜索框
                ft.Icon(ft.Icons.SEARCH, size=18, color="#666666"),
                self.search_field,
                
                # 文件类型筛选
                ft.Container(
                    content=ft.Text("文件类型:", size=13, color="#666666"),
                    padding=ft.Padding(left=20, top=0, right=5, bottom=0),
                ),
                self.type_filter,
                
                # 文件/文件夹筛选
                ft.Container(
                    content=ft.Text("类型:", size=13, color="#666666"),
                    padding=ft.Padding(left=20, top=0, right=5, bottom=0),
                ),
                self.item_type_filter,
                
                # 搜索按钮
                self.search_button,
                
                # 扫描目录
                ft.Container(
                    content=ft.Text("扫描目录:", size=13, color="#666666"),
                    padding=ft.Padding(left=20, top=0, right=5, bottom=0),
                ),
                self.directory_input,
                self.rebuild_button,
                self.permission_button,
            ], spacing=10, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=False),
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
            ], expand=True, spacing=10),
        )

        # 启动时不自动构建索引，只有当用户点击重新构建时才构建
        self.status_text = "就绪，点击重新构建按钮开始构建索引"
        self.status_bar.content.controls[0].value = self.status_text
        self.page.update()
    
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

        # 检查索引是否存在
        if not self.sdk.index_exists():
            def update_ui():
                self.status_bar.content.controls[0].value = "索引不存在，请先构建索引"
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

        # 检查索引是否存在
        if not self.sdk.index_exists():
            def update_ui():
                self.status_bar.content.controls[0].value = "索引不存在，请先构建索引"
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
        """异步构建索引
        
        在后台线程中构建索引，避免阻塞UI线程
        """
        self.logger.info("开始构建索引")
        # 先在主线程中更新UI
        self.is_building_index = True
        self.progress_container.visible = True
        self.status_bar.content.controls[0].value = "正在构建索引..."
        
        # 强制更新页面
        self.page.update()

        def build():
            """索引构建线程函数"""
            try:
                # 获取目录输入框中的路径
                directory = self.directory_input.value.strip()
                if not directory:
                    directory = str(Path.home())
                
                self.logger.info(f"开始扫描目录: {directory}")

                # 执行索引构建
                result = self.sdk.build_index(directory=directory)
                self.logger.info(f"索引构建完成，耗时 {result['time']*1000:.0f}ms")

                # 在主线程中更新UI
                def update_ui_after():
                    """索引构建完成后的UI更新"""
                    self.is_building_index = False
                    self.progress_container.visible = False
                    self.status_text = f"索引构建完成，耗时 {result['time']*1000:.0f}ms"
                    self.status_bar.content.controls[0].value = self.status_text
                    self.page.update()
                
                # 使用定时器在主线程中更新UI
                import threading
                threading.Timer(0.1, update_ui_after).start()
            except Exception as e:
                error_msg = str(e)
                self.logger.error(f"索引构建失败: {error_msg}")
                # 在主线程中更新UI
                def update_ui_error():
                    """索引构建失败后的UI更新"""
                    self.is_building_index = False
                    self.progress_container.visible = False
                    self.status_text = f"索引构建失败: {error_msg}"
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
        """在单独的线程中执行搜索，避免阻塞主线程
        
        从UI获取搜索参数，在后台线程中执行搜索，然后更新UI显示结果
        """
        self.logger.info(f"开始搜索: {self.current_query}")
        
        def search_thread():
            """搜索线程函数"""
            try:
                start_time = time.time()

                # 映射排序字段到搜索API的排序参数
                sort_map = {
                    "name": "name",      # 按名称排序
                    "path": "name",      # 按路径排序
                    "size": "size",      # 按大小排序
                    "mtime": "time",     # 按修改时间排序
                    "type": "name",      # 按类型排序
                }
                sort_by = sort_map.get(self.sort_column, "relevance")

                # 构建搜索参数
                params = {"query": self.current_query, "sort_by": sort_by, "limit": 1000}
                
                # 添加文件类型筛选
                if self.file_type_filter and self.file_type_filter != "全部":
                    file_type = self.file_type_filter.lstrip(".")
                    params["file_type"] = file_type
                    self.logger.info(f"添加文件类型筛选: {file_type}")

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
                        self.logger.info("筛选类型: 文件")
                    elif self.item_type_filter_value == "文件夹":
                        search_results = [item for item in search_results if item.get("is_directory", False)]
                        self.logger.info("筛选类型: 文件夹")

                # 对结果排序
                sort_key_map = {
                    "name": lambda x: x.get("name", "").lower(),  # 按名称小写排序
                    "path": lambda x: x.get("path", "").lower(),  # 按路径小写排序
                    "size": lambda x: x.get("size", 0),          # 按大小排序
                    "mtime": lambda x: x.get("mtime", 0),         # 按修改时间排序
                    "type": lambda x: x.get("extension", ""),     # 按扩展名排序
                }
                key_func = sort_key_map.get(self.sort_column, sort_key_map["name"])
                search_results.sort(key=key_func, reverse=not self.sort_ascending)

                # 在主线程中更新UI
                def update_ui():
                    """搜索完成后的UI更新"""
                    self.search_results = search_results
                    self.display_results()
                    count = len(self.search_results)
                    display_count = min(count, 200)  # 限制显示结果数量
                    if count > 200:
                        self.status_bar.content.controls[0].value = f"找到 {count} 个结果，显示前 {display_count} 个，耗时 {(end_time-start_time)*1000:.0f}ms"
                    else:
                        self.status_bar.content.controls[0].value = f"找到 {count} 个结果，耗时 {(end_time-start_time)*1000:.0f}ms"
                    self.page.update()
                    self.logger.info(f"搜索完成，找到 {count} 个结果，耗时 {(end_time-start_time)*1000:.0f}ms")

                # 使用定时器在主线程中更新UI
                import threading
                threading.Timer(0.1, update_ui).start()
            except Exception as e:
                self.logger.error(f"搜索失败: {str(e)}")
                # 在主线程中更新UI
                def update_ui_error():
                    """搜索失败后的UI更新"""
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
        self.logger.info(f"开始显示结果，结果数量: {len(self.search_results)}")
        
        # 创建新的行列表
        new_rows = []

        if not self.search_results:
            self.logger.info("搜索结果为空")
            self.result_table.rows = []
            self.page.update()
            return

        # 确保搜索结果不为空
        if len(self.search_results) > 0:
            self.logger.info(f"搜索结果数量: {len(self.search_results)}")
            for item in self.search_results[:200]:  # 限制显示200条
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

                    # 根据文件类型选择图标
                    try:
                        if is_directory:
                            icon = ft.Icon(ft.Icons.FOLDER, size=16, color="#4285f4")
                        elif extension in ["py"]:
                            icon = ft.Icon(ft.Icons.CODE, size=16, color="#3776ab")
                        elif extension in ["js", "ts"]:
                            icon = ft.Icon(ft.Icons.CODE, size=16, color="#f7df1e")
                        elif extension in ["html"]:
                            icon = ft.Icon(ft.Icons.CODE, size=16, color="#e34f26")
                        elif extension in ["css"]:
                            icon = ft.Icon(ft.Icons.CODE, size=16, color="#1572b6")
                        elif extension in ["json"]:
                            icon = ft.Icon(ft.Icons.CODE, size=16, color="#000000")
                        elif extension in ["yaml", "yml"]:
                            icon = ft.Icon(ft.Icons.CODE, size=16, color="#000000")
                        elif extension in ["toml"]:
                            icon = ft.Icon(ft.Icons.CODE, size=16, color="#000000")
                        elif extension in ["md"]:
                            icon = ft.Icon(ft.Icons.DESCRIPTION, size=16, color="#000000")
                        elif extension in ["txt"]:
                            icon = ft.Icon(ft.Icons.TEXT_SNIPPET, size=16, color="#000000")
                        elif extension in ["pdf"]:
                            icon = ft.Icon(ft.Icons.PICTURE_AS_PDF, size=16, color="#ea4335")
                        elif extension in ["jpg", "jpeg", "png", "gif", "bmp"]:
                            icon = ft.Icon(ft.Icons.IMAGE, size=16, color="#fbbc05")
                        elif extension in ["mp3", "wav", "flac", "aac"]:
                            icon = ft.Icon(ft.Icons.MUSIC_NOTE, size=16, color="#9c27b0")
                        elif extension in ["mp4", "avi", "mov", "mkv"]:
                            icon = ft.Icon(ft.Icons.MOVIE, size=16, color="#00bcd4")
                        elif extension in ["zip", "rar", "tar", "gz", "7z"]:
                            icon = ft.Icon(ft.Icons.ARCHIVE, size=16, color="#ff9800")
                        else:
                            # 使用FILE_COPY作为默认图标，避免使用可能不存在的FILE图标
                            icon = ft.Icon(ft.Icons.FILE_COPY, size=16, color="#666666")

                        # 创建数据行
                        row = ft.DataRow(
                            cells=[
                                ft.DataCell(
                                    ft.Container(
                                        content=ft.Row([
                                            icon,
                                            ft.Text(name, size=12, color="#333333", overflow=ft.TextOverflow.ELLIPSIS)
                                        ], spacing=5),
                                        padding=ft.Padding(left=5, top=0, right=5, bottom=0)
                                    )
                                ),
                                ft.DataCell(ft.Text(path, size=11, color="#666666", overflow=ft.TextOverflow.ELLIPSIS)),
                                ft.DataCell(ft.Text(size_str, size=11, color="#666666")),
                                ft.DataCell(ft.Text(type_str, size=11, color="#666666")),
                                ft.DataCell(ft.Text(mtime_str, size=11, color="#666666")),
                            ],
                            on_select_change=lambda e, p=path: self.open_item(p),
                        )
                    except Exception as e:
                        # 如果图标创建失败，使用不带图标的行
                        self.logger.warning(f"创建图标失败: {e}")
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
                    new_rows.append(row)
                except Exception as e:
                    # 打印错误信息以便调试
                    self.logger.error(f"创建行时出错: {e}")
                    continue

        self.logger.info(f"结果显示完成，添加了 {len(new_rows)} 行")
        # 一次性替换所有行，避免频繁更新
        self.result_table.rows = new_rows
        # 强制更新页面
        self.page.update()

    def _init_logging(self):
        """初始化日志配置"""
        # 确保日志目录存在
        try:
            # 首先尝试使用用户主目录
            log_dir = Path.home() / ".xfinder" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # 如果失败，使用应用程序当前目录
            log_dir = Path.cwd() / ".logs"
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径
        log_file = log_dir / f"xfinder_{time.strftime('%Y-%m-%d')}.log"
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"日志已初始化，日志文件保存位置: {log_file}")
    
    def _on_keyboard_event(self, e):
        """处理键盘事件"""
        # 检测control+command+f快捷键
        if e.ctrl and e.meta and e.key == "f":
            # 聚焦到搜索框
            self.search_field.focus()
            self.page.update()
            self.logger.info("快捷键 control+command+f 被触发，聚焦到搜索框")
    
    def rebuild_index(self, e=None):
        """重新构建索引"""
        directory = self.directory_input.value.strip()
        if directory:
            self.logger.info(f"重新构建索引，扫描目录: {directory}")
            # 重新构建索引
            self.event_bus.send_event("build_index")
        else:
            self.logger.warning("扫描目录不能为空")
            # 显示警告对话框
            dialog = ft.AlertDialog(
                title=ft.Text("警告"),
                content=ft.Text("扫描目录不能为空"),
                actions=[
                    ft.TextButton("确定", on_click=lambda e: setattr(self.page, "dialog", None) or self.page.update()),
                ],
            )
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
    
    def open_permission_settings(self, e=None):
        """打开系统设置中的权限设置页面"""
        try:
            system = platform.system()
            if system == "Darwin":
                # 打开macOS的隐私与安全性设置
                subprocess.run([
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_FilesAndFolders"
                ], check=True)
            elif system == "Windows":
                # 打开Windows的隐私设置
                subprocess.run(["start", "ms-settings:privacy"], shell=True, check=True)
        except Exception as ex:
            self.logger.error(f"打开权限设置失败: {ex}")
            # 显示错误对话框
            dialog = ft.AlertDialog(
                title=ft.Text("提示"),
                content=ft.Text("请手动打开系统设置 > 隐私与安全性 > 文件和文件夹"),
                actions=[
                    ft.TextButton("确定", on_click=lambda e: setattr(self.page, "dialog", None) or self.page.update()),
                ],
            )
            self.page.dialog = dialog
            dialog.open = True
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
