"""xfinder SDK 使用示例"""

from xfinder import get_sdk


def main():
    """SDK使用示例"""
    print("=== xfinder SDK 使用示例 ===")
    
    # 1. 初始化SDK
    print("\n1. 初始化SDK")
    sdk = get_sdk(
        custom_paths=["/Users/xiaoyemiao/Desktop/joinai-code"],
        threads=64  # 使用64个线程
    )
    
    # 2. 获取配置
    print("\n2. 获取当前配置")
    config = sdk.get_config()
    print(f"扫描路径: {config['scan_paths']}")
    print(f"排除目录: {config['exclude_dirs']}")
    print(f"内容索引扩展名: {config['content_extensions']}")
    print(f"最大文件大小: {config['max_file_size']} bytes")
    print(f"是否启用内容索引: {config['content_index_enabled']}")
    
    # 3. 构建索引
    print("\n3. 构建索引")
    result = sdk.build_index()
    print(f"索引构建结果: {result['status']}")
    print(f"索引构建耗时: {result['time']:.2f} 秒")
    
    # 4. 搜索文件
    print("\n4. 搜索文件")
    search_result = sdk.search("bun", limit=10)
    print(f"搜索结果数量: {search_result['count']}")
    print(f"搜索耗时: {search_result['time']*1000:.0f} ms")
    
    print("\n搜索结果:")
    for i, item in enumerate(search_result['results'], 1):
        print(f"  {i}. {item['path']} [{item['match_type']}]")
    
    # 5. 搜索其他关键词
    print("\n5. 搜索其他关键词")
    search_result = sdk.search("join", limit=10)
    print(f"搜索结果数量: {search_result['count']}")
    print(f"搜索耗时: {search_result['time']*1000:.0f} ms")
    
    print("\n搜索结果:")
    for i, item in enumerate(search_result['results'], 1):
        print(f"  {i}. {item['path']} [{item['match_type']}]")
    
    print("\n=== SDK 使用示例结束 ===")


if __name__ == "__main__":
    main()