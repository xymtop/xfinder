import sys
import yaml
from pathlib import Path

# 直接读取配置文件
config_file = Path.home() / '.xfinder' / 'config.yaml'

print(f"配置文件路径: {config_file}")
print(f"配置文件是否存在: {config_file.exists()}")

if config_file.exists():
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        print("配置文件内容:")
        print(yaml.dump(config, allow_unicode=True))
        print("\n扫描路径:")
        if 'scan_paths' in config:
            print(config['scan_paths'])
        else:
            print("未找到 scan_paths 配置")
else:
    print("配置文件不存在")
