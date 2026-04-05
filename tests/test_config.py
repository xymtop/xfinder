import os
import tempfile
from pathlib import Path
from xfinder.config import Config

def test_config_loading():
    """测试配置加载功能"""
    # 创建临时配置文件
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / '.xfinder'
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'config.yaml'
        
        # 写入测试配置
        test_config = {
            'scan_paths': ['/tmp/test1', '/tmp/test2'],
            'exclude_dirs': ['.git', 'node_modules'],
            'content_index': {
                'enabled': True,
                'extensions': ['.txt', '.md'],
                'max_file_size': '10MB'
            },
            'llm_index': {
                'enabled': False
            }
        }
        
        import yaml
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # 直接创建配置实例，确保使用正确的配置目录
        config = Config()
        # 手动设置配置文件路径
        config.config_file = config_file
        # 重新加载配置
        config.config = config.load_config()
        
        # 测试配置读取
        assert config.get_scan_paths() == ['/tmp/test1', '/tmp/test2']
        assert config.get_exclude_dirs() == ['.git', 'node_modules']
        assert config.is_content_index_enabled() is True
        assert config.get_content_extensions() == ['.txt', '.md']
        assert config.get_max_file_size() == 10 * 1024 * 1024
        assert config.is_llm_index_enabled() is False

def test_default_config():
    """测试默认配置"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / '.xfinder'
        
        # 创建配置实例
        config = Config()
        # 手动设置配置目录
        config.config_dir = config_dir
        # 重新加载配置
        config.config = config.load_config()
        
        # 测试默认配置
        assert len(config.get_scan_paths()) == 1
        assert '.git' in config.get_exclude_dirs()
        assert config.is_content_index_enabled() is True
        assert '.py' in config.get_content_extensions()
        assert config.get_max_file_size() == 5 * 1024 * 1024
        assert config.is_llm_index_enabled() is False
