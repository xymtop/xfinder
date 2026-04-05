"""xfinder SDK - 对外提供的开发接口"""

from pathlib import Path
from .indexer import Indexer
from .searcher import Searcher
from .config import config


class XFinderSDK:
    """xfinder SDK类，提供对外接口"""
    
    def __init__(self, custom_paths=None, threads=32):
        """初始化SDK
        
        Args:
            custom_paths: 自定义扫描路径列表，None表示使用配置文件中的路径
            threads: 扫描和索引的线程数量
        """
        self.custom_paths = custom_paths
        self.threads = threads
        self.indexer = None
        self.searcher = None
    
    def build_index(self, directory=None):
        """构建索引
        
        Args:
            directory: 自定义扫描目录，None表示使用配置文件中的路径
            
        Returns:
            dict: 索引构建结果，包含文件数、耗时等信息
        """
        import time
        
        start_time = time.time()
        
        # 确定扫描路径
        custom_paths = self.custom_paths
        if directory:
            custom_paths = [directory]
        
        # 初始化索引器
        self.indexer = Indexer(custom_paths=custom_paths, threads=self.threads)
        
        # 构建索引
        self.indexer.build_index()
        
        # 初始化搜索器
        self.searcher = Searcher()
        
        end_time = time.time()
        
        return {
            'status': 'success',
            'time': end_time - start_time
        }
    
    def search(self, query=None, folder_name=None, file_name=None, file_type=None, size_min=None, size_max=None, date_min=None, date_max=None, limit=20, sort_by='relevance'):
        """搜索文件
        
        Args:
            query: 搜索关键词
            folder_name: 文件夹名称
            file_name: 文件名称
            file_type: 文件类型（扩展名）
            size_min: 最小文件大小（字节）
            size_max: 最大文件大小（字节）
            date_min: 最小修改日期（时间戳）
            date_max: 最大修改日期（时间戳）
            limit: 返回结果数量限制
            sort_by: 排序方式，可选值: relevance, name, size, time
        
        Returns:
            dict: 搜索结果，包含结果列表、总数、耗时等信息
        """
        # 如果搜索器未初始化，初始化它
        if not self.searcher:
            self.searcher = Searcher()
        
        # 执行搜索
        result = self.searcher.search(query, folder_name=folder_name, file_name=file_name, file_type=file_type, 
                                     size_min=size_min, size_max=size_max, date_min=date_min, date_max=date_max, 
                                     limit=limit, sort_by=sort_by)
        
        return result
    
    def index_exists(self):
        """检查索引是否存在
        
        Returns:
            bool: 索引是否存在
        """
        from pathlib import Path
        # 检查索引数据库文件是否存在
        db_path = config.index_dir / 'xfinder.db'
        return db_path.exists() and db_path.stat().st_size > 0
    
    def get_config(self):
        """获取当前配置
        
        Returns:
            dict: 配置信息
        """
        return {
            'scan_paths': config.get_scan_paths(),
            'exclude_dirs': config.get_exclude_dirs(),
            'content_extensions': config.get_content_extensions(),
            'max_file_size': config.get_max_file_size(),
            'content_index_enabled': config.is_content_index_enabled()
        }
    
    def update_config(self, **kwargs):
        """更新配置
        
        Args:
            **kwargs: 配置参数
                scan_paths: 扫描路径列表
                exclude_dirs: 排除目录列表
                content_extensions: 内容索引的文件扩展名列表
                max_file_size: 内容索引的最大文件大小
                content_index_enabled: 是否启用内容索引
        
        Returns:
            dict: 更新后的配置
        """
        # 这里可以添加配置更新逻辑
        # 目前返回当前配置
        return self.get_config()


# 导出SDK实例
def get_sdk(custom_paths=None, threads=32):
    """获取SDK实例
    
    Args:
        custom_paths: 自定义扫描路径列表
        threads: 扫描和索引的线程数量
    
    Returns:
        XFinderSDK: SDK实例
    """
    return XFinderSDK(custom_paths=custom_paths, threads=threads)