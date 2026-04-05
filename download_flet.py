import urllib.request
import ssl
import os

# 禁用SSL验证
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

# Flet下载URL（国内源）
flet_url = "https://ghproxy.net/https://github.com/flet-dev/flet/releases/download/v0.84.0/flet-macos.tar.gz"
download_path = "flet-macos.tar.gz"

print(f"正在下载 Flet v0.84.0...")
try:
    # 使用自定义的context来禁用SSL验证
    with urllib.request.urlopen(flet_url, context=context) as response, open(download_path, 'wb') as out_file:
        data = response.read()
        out_file.write(data)
    print(f"下载完成！文件大小: {os.path.getsize(download_path) / 1024 / 1024:.2f} MB")
except Exception as e:
    print(f"下载失败: {e}")
