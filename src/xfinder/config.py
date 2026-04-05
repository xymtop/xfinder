import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

class Config:
    def __init__(self):
        # 使用项目根目录作为配置和索引的存储位置
        self.project_root = Path(__file__).parent.parent.parent  # src/xfinder/../.. = 项目根目录
        self.config_dir = self.project_root / '.xfinder'
        self.config_file = self.config_dir / 'config.yaml'
        self.index_dir = self.config_dir / 'index'
        self.default_config = {
            'scan_paths': [str(self.project_root)],
            'exclude_dirs': ['.git', 'node_modules', '__pycache__'],
            'content_index': {
                'enabled': False,
                'extensions': ['.txt', '.md', '.py', '.js', '.ts', '.go', '.java', '.json', '.yaml'],
                'max_file_size': '5MB'
            },
            'llm_index': {
                'enabled': False,
                'base_url': os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                'embedding_model': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
            }
        }
        self.config = self.load_config()
        # 从.env文件中覆盖配置
        self._load_from_env()
    
    def load_config(self):
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.index_dir.exists():
            self.index_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.config_file.exists():
            self.save_config(self.default_config)
            return self.default_config
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config
    
    def save_config(self, config):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    def get(self, key, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_scan_paths(self):
        paths = self.get('scan_paths', [str(Path.home())])
        # 确保路径是绝对路径
        absolute_paths = []
        for path in paths:
            absolute_path = Path(path).expanduser().absolute()
            absolute_paths.append(str(absolute_path))
        return absolute_paths
    
    def get_exclude_dirs(self):
        return self.get('exclude_dirs', ['.git', 'node_modules', '__pycache__'])
    
    def is_content_index_enabled(self):
        return self.get('content_index.enabled', False)
    
    def get_content_extensions(self):
        return self.get('content_index.extensions', ['.txt', '.md', '.py', '.js', '.ts', '.go', '.java', '.json', '.yaml'])
    
    def get_max_file_size(self):
        size_str = self.get('content_index.max_file_size', '5MB')
        return self._parse_size(size_str)
    
    def is_llm_index_enabled(self):
        return self.get('llm_index.enabled', False)
    
    def _parse_size(self, size_str):
        size_str = size_str.strip().upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def _load_from_env(self):
        """从.env文件中加载配置"""
        # 加载大模型配置
        if 'OPENAI_BASE_URL' in os.environ:
            if 'llm_index' not in self.config:
                self.config['llm_index'] = {}
            self.config['llm_index']['base_url'] = os.environ['OPENAI_BASE_URL']
        
        if 'OPENAI_API_KEY' in os.environ:
            if 'llm_index' not in self.config:
                self.config['llm_index'] = {}
            self.config['llm_index']['api_key'] = os.environ['OPENAI_API_KEY']
        
        if 'OPENAI_MODEL' in os.environ:
            if 'llm_index' not in self.config:
                self.config['llm_index'] = {}
            self.config['llm_index']['model'] = os.environ['OPENAI_MODEL']
        
        if 'OPENAI_EMBEDDING_MODEL' in os.environ:
            if 'llm_index' not in self.config:
                self.config['llm_index'] = {}
            self.config['llm_index']['embedding_model'] = os.environ['OPENAI_EMBEDDING_MODEL']

config = Config()
