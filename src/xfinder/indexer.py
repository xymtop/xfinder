import os
import sqlite3
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from .config import config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.index_dir / 'xfinder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Indexer:
    def __init__(self, custom_paths=None, threads=32):
        self.index_dir = config.index_dir
        self.db_path = self.index_dir / 'xfinder.db'
        self.conn = None
        self.cursor = None
        self.custom_paths = custom_paths
        self.scan_paths = custom_paths if custom_paths else config.get_scan_paths()
        self.exclude_dirs = config.get_exclude_dirs()
        self.content_extensions = config.get_content_extensions()
        self.max_file_size = config.get_max_file_size()
        self.content_index_enabled = config.is_content_index_enabled()
        self.threads = threads
    
    def connect_db(self):
        print("连接数据库...")
        # 使用更高效的数据库配置
        self.conn = sqlite3.connect(
            str(self.db_path),
            timeout=30,
            isolation_level=None  # 禁用自动事务，使用手动事务
        )
        # 启用写同步，提高写入性能
        self.conn.execute('PRAGMA synchronous = OFF')
        # 启用内存临时表，提高查询性能
        self.conn.execute('PRAGMA temp_store = MEMORY')
        print("获取游标...")
        self.cursor = self.conn.cursor()
        print("创建表...")
        self.create_tables()
        print("数据库连接完成")
    
    def create_tables(self):
        # 文件信息表
        print("创建files表...")
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            name TEXT,
            extension TEXT,
            size INTEGER,
            mtime INTEGER,
            is_content_indexed INTEGER DEFAULT 0,
            is_directory INTEGER DEFAULT 0
        )
        ''')
        print("files表创建完成")
        
        # 检查并添加is_directory字段（如果不存在）
        try:
            self.cursor.execute("PRAGMA table_info(files)")
            columns = [column[1] for column in self.cursor.fetchall()]
            if 'is_directory' not in columns:
                self.cursor.execute("ALTER TABLE files ADD COLUMN is_directory INTEGER DEFAULT 0")
                print("添加is_directory字段")
        except Exception as e:
            logger.error(f"Error checking/adding is_directory column: {e}")
        
        # 全文索引表（如果启用）
        if self.content_index_enabled:
            print("创建file_content表...")
            self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS file_content USING FTS5(
                file_id,
                content
            )
            ''')
            print("file_content表创建完成")
        
        print("提交事务...")
        self.conn.commit()
        print("表创建完成")
    
    def close_db(self):
        if self.conn:
            self.conn.close()
    
    def build_index(self):
        # 检查索引是否已经存在
        index_state_file = self.index_dir / 'index_state.json'
        # 如果使用了自定义路径，强制重新构建索引
        if index_state_file.exists() and not self.custom_paths:
            logger.info("索引已经存在，跳过构建")
            print("索引已经存在，跳过构建")
            return
        
        logger.info("开始构建索引...")
        logger.info(f"扫描路径: {self.scan_paths}")
        print("正在构建索引...")
        
        self.connect_db()
        self.clear_index()
        
        total_files = 0
        content_indexed_files = 0
        
        start_time = time.time()
        
        # 扫描所有文件
        all_files = []
        logger.info("开始扫描文件...")
        
        # 并行处理多个扫描路径
        if len(self.scan_paths) > 1:
            from concurrent.futures import ThreadPoolExecutor
            
            def scan_path(scan_path):
                path = Path(scan_path)
                logger.info(f"扫描目录: {path}")
                if path.exists() and path.is_dir():
                    files = self.scan_directory(path)
                    logger.info(f"  扫描完成，找到 {len(files)} 个文件")
                    return files
                return []
            
            with ThreadPoolExecutor(max_workers=min(len(self.scan_paths), self.threads)) as executor:
                results = executor.map(scan_path, self.scan_paths)
                for files in results:
                    all_files.extend(files)
                    total_files += len(files)
        else:
            # 单个扫描路径，直接处理
            for scan_path in self.scan_paths:
                path = Path(scan_path)
                logger.info(f"扫描目录: {path}")
                if path.exists() and path.is_dir():
                    files = self.scan_directory(path)
                    all_files.extend(files)
                    total_files += len(files)
                    logger.info(f"  扫描完成，找到 {len(files)} 个文件")
        
        logger.info(f"总文件数: {total_files}")
        
        # 批量插入文件信息
        if all_files:
            logger.info("开始插入文件信息...")
            # 分批处理
            batch_size = 10000
            self.batch_insert_files(all_files)
        
        # 构建全文索引
        if self.content_index_enabled:
            logger.info("开始构建全文索引...")
            content_files = [f for f in all_files if self._should_index_content(f)]
            content_indexed_files = len(content_files)
            logger.info(f"需要索引内容的文件数: {content_indexed_files}")
            
            if content_files:
                # 分批处理
                batch_size = 1000
                self.batch_insert_content(content_files)
        
        end_time = time.time()
        
        logger.info(f"  扫描文件信息: {total_files} 个文件  ✓")
        logger.info(f"  构建全文索引: {content_indexed_files} 个文件  ✓")
        logger.info(f"  索引构建完成，耗时 {end_time - start_time:.2f} 秒")
        
        print(f"  扫描文件信息: {total_files} 个文件  ✓")
        if self.content_index_enabled:
            print(f"  构建全文索引: {content_indexed_files} 个文件  ✓")
        else:
            print("  全文索引: 已禁用")
        print(f"  索引构建完成，耗时 {end_time - start_time:.2f} 秒")
        
        # 保存索引状态
        import json
        index_state_file = self.index_dir / 'index_state.json'
        with open(index_state_file, 'w') as f:
            json.dump({
                'timestamp': int(time.time()),
                'total_files': total_files,
                'content_indexed_files': content_indexed_files
            }, f)
        
        self.close_db()
        print("索引构建完成！")
    
    def scan_directory(self, directory):
        """高效扫描目录，使用多线程并行处理"""
        all_files = []
        
        def scan_dir(path):
            """扫描单个目录"""
            items = []
            try:
                items = list(path.iterdir())
            except Exception as e:
                logger.error(f"Error scanning directory {path}: {e}")
                return [], []
            
            files = []
            subdirs = []
            
            for item in items:
                if item.name in self.exclude_dirs:
                    continue
                
                try:
                    # 检查是否是目录
                    try:
                        is_dir = item.is_dir()
                    except Exception:
                        is_dir = False
                    
                    # 检查是否是文件
                    try:
                        is_file = item.is_file()
                    except Exception:
                        is_file = False
                    
                    if is_dir:
                        subdirs.append(item)
                        # 存储文件夹信息
                        try:
                            files.append({
                                'path': str(item),
                                'name': item.name,
                                'extension': '',  # 文件夹没有扩展名
                                'size': 0,  # 文件夹大小设为0
                                'mtime': int(item.stat().st_mtime),
                                'is_directory': True  # 标记为文件夹
                            })
                        except Exception as e:
                            logger.error(f"Error processing directory {item}: {e}")
                    elif is_file:
                        try:
                            files.append({
                                'path': str(item),
                                'name': item.name,
                                'extension': item.suffix,
                                'size': item.stat().st_size,
                                'mtime': int(item.stat().st_mtime),
                                'is_directory': False  # 标记为文件
                            })
                        except Exception as e:
                            logger.error(f"Error processing file {item}: {e}")
                except Exception as e:
                    logger.error(f"Error processing item {item}: {e}")
            
            return files, subdirs
        
        # 使用队列和线程池并行扫描
        from queue import Queue
        import threading
        
        # 创建队列
        dir_queue = Queue()
        dir_queue.put(directory)
        
        # 线程安全的结果收集
        results = []
        lock = threading.Lock()
        
        def worker():
            """扫描工作线程"""
            while True:
                try:
                    path = dir_queue.get(block=False)
                except:
                    break
                
                files, subdirs = scan_dir(path)
                
                with lock:
                    results.extend(files)
                
                # 将子目录加入队列
                for subdir in subdirs:
                    dir_queue.put(subdir)
                
                dir_queue.task_done()
        
        # 启动线程
        num_threads = min(self.threads, os.cpu_count() * 4)
        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 等待所有目录处理完成
        dir_queue.join()
        
        return results
    
    def batch_insert_files(self, files):
        if not files:
            return
        
        try:
            # 开启事务
            self.conn.execute('BEGIN TRANSACTION')
            
            # 批量插入，每批50000条
            batch_size = 50000
            total = len(files)
            
            # 准备SQL语句
            sql = "INSERT OR REPLACE INTO files (path, name, extension, size, mtime, is_directory) VALUES (?, ?, ?, ?, ?, ?)"
            
            # 准备数据
            data = []
            for file in files:
                data.append((file['path'], file['name'], file['extension'], file['size'], file['mtime'], file.get('is_directory', 0)))
                
                # 当数据达到批量大小时，执行插入
                if len(data) >= batch_size:
                    self.cursor.executemany(sql, data)
                    logger.info(f"  已插入 {min(len(data), total)}/{total} 个文件")
                    data = []
            
            # 插入剩余数据
            if data:
                self.cursor.executemany(sql, data)
                logger.info(f"  已插入 {total}/{total} 个文件")
            
            # 一次性提交事务
            self.conn.commit()
            logger.info("文件信息插入完成")
        except Exception as e:
            logger.error(f"Error inserting files: {e}")
            # 发生错误时回滚事务
            self.conn.rollback()
    
    def batch_insert_content(self, files):
        if not files:
            return
        
        # 先批量获取所有文件的ID
        file_ids = {}
        try:
            # 批量查询文件ID
            paths = [file['path'] for file in files]
            # 分批处理，每批1000个
            batch_size = 1000
            for i in range(0, len(paths), batch_size):
                batch_paths = paths[i:i+batch_size]
                placeholders = ','.join(['?'] * len(batch_paths))
                query = f"SELECT id, path FROM files WHERE path IN ({placeholders})"
                self.cursor.execute(query, batch_paths)
                results = self.cursor.fetchall()
                for id, path in results:
                    file_ids[path] = id
            logger.info(f"成功获取 {len(file_ids)} 个文件的ID")
        except Exception as e:
            logger.error(f"Error getting file IDs: {e}")
            return
        
        # 定义函数读取文件内容
        def process_file(file_path):
            content = self._read_file_content(file_path)
            return file_path, content
        
        # 使用线程池并行读取文件内容
        max_workers = min(self.threads, os.cpu_count() * 4)  # 增加线程数以提高性能
        content_results = []
        
        # 分批处理文件
        batch_size = 1000
        for i in range(0, len(files), batch_size):
            batch_files = files[i:i+batch_size]
            batch_futures = []
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                for file in batch_files:
                    if file['path'] in file_ids:
                        future = executor.submit(process_file, file['path'])
                        batch_futures.append(future)
                
                for future in as_completed(batch_futures):
                    try:
                        file_path, content = future.result()
                        if content:
                            content_results.append((file_ids[file_path], content))
                    except Exception as e:
                        pass
            
            logger.info(f"  已读取 {min(i+batch_size, len(files))}/{len(files)} 个文件内容")
        
        # 批量插入内容
        try:
            # 开启事务
            self.conn.execute('BEGIN TRANSACTION')
            
            # 分批处理，每批10000条
            batch_size = 10000
            total = len(content_results)
            indexed_count = 0
            
            # 准备SQL语句
            insert_content_sql = "INSERT OR REPLACE INTO file_content (file_id, content) VALUES (?, ?)"
            
            # 准备数据
            content_data = []
            indexed_file_ids = []
            
            for file_id, content in content_results:
                content_data.append((file_id, content))
                indexed_file_ids.append(file_id)
                
                # 当数据达到批量大小时，执行插入
                if len(content_data) >= batch_size:
                    # 批量插入内容
                    self.cursor.executemany(insert_content_sql, content_data)
                    indexed_count += len(content_data)
                    logger.info(f"  已索引 {min(indexed_count, total)}/{total} 个文件")
                    content_data = []
            
            # 插入剩余数据
            if content_data:
                self.cursor.executemany(insert_content_sql, content_data)
                indexed_count += len(content_data)
                logger.info(f"  已索引 {min(indexed_count, total)}/{total} 个文件")
            
            # 批量更新文件状态（使用IN子句）
            if indexed_file_ids:
                # 分批更新，每批10000个
                update_batch_size = 10000
                for i in range(0, len(indexed_file_ids), update_batch_size):
                    batch_ids = indexed_file_ids[i:i+update_batch_size]
                    placeholders = ','.join(['?'] * len(batch_ids))
                    update_sql = f"UPDATE files SET is_content_indexed = 1 WHERE id IN ({placeholders})"
                    self.cursor.execute(update_sql, batch_ids)
            
            # 一次性提交事务
            self.conn.commit()
            logger.info("全文索引构建完成")
        except Exception as e:
            logger.error(f"Error inserting content: {e}")
            # 发生错误时回滚事务
            self.conn.rollback()
    
    def _should_index_content(self, file):
        return (file['extension'] in self.content_extensions and 
                file['size'] <= self.max_file_size)
    
    def _read_file_content(self, file_path):
        try:
            # 使用更快的文件读取方式
            with open(file_path, 'rb') as f:
                content = f.read()
            # 尝试解码为UTF-8，忽略错误
            return content.decode('utf-8', errors='ignore')
        except Exception:
            return None
    
    def clear_index(self):
        self.cursor.execute("DELETE FROM files")
        if self.content_index_enabled:
            self.cursor.execute("DELETE FROM file_content")
        self.conn.commit()
