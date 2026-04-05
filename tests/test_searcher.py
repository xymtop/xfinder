import os
import tempfile
from pathlib import Path
from xfinder.searcher import Searcher
from xfinder.indexer import Indexer
from xfinder.config import Config

def setup_test_environment():
    """设置测试环境"""
    # 创建临时目录
    tmpdir = tempfile.mkdtemp()
    
    # 创建测试文件
    test_files = [
        'test1.txt',
        'test2.py',
        'subdir/test3.md',
        'subdir/test4.py'
    ]
    
    for file_path in test_files:
        full_path = Path(tmpdir) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(f'Content of {file_path}')
    
    return tmpdir

def test_search_basic():
    """测试基本搜索功能"""
    tmpdir = setup_test_environment()
    
    try:
        # 导入config实例
        from xfinder.config import config
        
        # 保存原始配置
        original_scan_paths = config.get('scan_paths')
        
        # 修改配置为测试目录
        config.config['scan_paths'] = [tmpdir]
        
        # 构建索引
        indexer = Indexer()
        indexer.build_index()
        
        # 测试搜索
        searcher = Searcher()
        
        # 测试文件名搜索
        result = searcher.search('test1')
        assert result['count'] >= 1
        
        # 测试扩展名过滤
        result = searcher.search('type:py')
        assert result['count'] >= 2
        
        # 测试路径搜索
        result = searcher.search('subdir')
        assert result['count'] >= 2
        
    finally:
        # 清理临时目录
        import shutil
        shutil.rmtree(tmpdir)
        
        # 恢复原始配置
        if 'original_scan_paths' in locals() and 'config' in locals():
            config.config['scan_paths'] = original_scan_paths

def test_search_sorting():
    """测试搜索排序功能"""
    tmpdir = setup_test_environment()
    
    try:
        # 导入config实例
        from xfinder.config import config
        
        # 修改配置为测试目录
        original_scan_paths = config.get('scan_paths')
        config.config['scan_paths'] = [tmpdir]
        
        # 构建索引
        indexer = Indexer()
        indexer.build_index()
        
        # 测试搜索
        searcher = Searcher()
        
        # 测试按名称排序
        result = searcher.search('test', sort_by='name')
        assert result['count'] >= 4
        
        # 测试按大小排序
        result = searcher.search('test', sort_by='size')
        assert result['count'] >= 4
        
        # 测试按时间排序
        result = searcher.search('test', sort_by='time')
        assert result['count'] >= 4
        
    finally:
        # 清理临时目录
        import shutil
        shutil.rmtree(tmpdir)
        
        # 恢复原始配置
        if 'original_scan_paths' in locals() and 'config' in locals():
            config.config['scan_paths'] = original_scan_paths
