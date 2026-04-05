from xfinder.sdk import get_sdk
import time

# 初始化SDK
sdk = get_sdk()
print('SDK初始化成功')

# 测试基本搜索功能
print('\n1. 测试基本搜索功能:')
result = sdk.search(query='bun', limit=5)
print('搜索结果数量:', result['count'])
print('搜索耗时:', result['time'])
print('搜索结果:', result['results'])

# 测试按文件夹名称搜索
print('\n2. 测试按文件夹名称搜索:')
result = sdk.search(folder_name='join', limit=5)
print('搜索结果数量:', result['count'])
print('搜索耗时:', result['time'])
print('搜索结果:', result['results'])

# 测试按文件名称搜索
print('\n3. 测试按文件名称搜索:')
result = sdk.search(file_name='bun', limit=5)
print('搜索结果数量:', result['count'])
print('搜索耗时:', result['time'])
print('搜索结果:', result['results'])

# 测试按文件类型搜索
print('\n4. 测试按文件类型搜索:')
result = sdk.search(file_type='py', limit=5)
print('搜索结果数量:', result['count'])
print('搜索耗时:', result['time'])
print('搜索结果:', result['results'])

# 测试按大小搜索
print('\n5. 测试按大小搜索:')
result = sdk.search(size_min=100*1024, limit=5)
print('搜索结果数量:', result['count'])
print('搜索耗时:', result['time'])
print('搜索结果:', result['results'])

# 测试按修改日期搜索
print('\n6. 测试按修改日期搜索:')
seven_days_ago = int(time.time() - 7*24*3600)
result = sdk.search(date_min=seven_days_ago, limit=5)
print('搜索结果数量:', result['count'])
print('搜索耗时:', result['time'])
print('搜索结果:', result['results'])

# 测试组合搜索
print('\n7. 测试组合搜索:')
result = sdk.search(file_name='bun', file_type='lock', limit=5)
print('搜索结果数量:', result['count'])
print('搜索耗时:', result['time'])
print('搜索结果:', result['results'])
