import os
import sqlite3
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # 使用更高效的数据库配置
        self.conn = sqlite3.connect(
            str(self.db_path),
            timeout=30,
            check_same_thread=False,  # 允许跨线程访问
            isolation_level=None  # 禁用自动事务，使用手动事务
        )
        # 启用WAL模式，提高并发性能
        self.conn.execute('PRAGMA journal_mode = WAL')
        # 启用写同步，提高写入性能
        self.conn.execute('PRAGMA synchronous = NORMAL')
        # 启用内存临时表，提高查询性能
        self.conn.execute('PRAGMA temp_store = MEMORY')
        # 设置缓存大小
        self.conn.execute('PRAGMA cache_size = -64000')  # 64MB
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # 文件信息表
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
        
        # 检查并添加is_directory字段（如果不存在）
        try:
            self.cursor.execute("PRAGMA table_info(files)")
            columns = [column[1] for column in self.cursor.fetchall()]
            if 'is_directory' not in columns:
                self.cursor.execute("ALTER TABLE files ADD COLUMN is_directory INTEGER DEFAULT 0")
        except Exception as e:
            logger.error(f"Error checking/adding is_directory column: {e}")
        
        # 全文索引表（如果启用）
        if self.content_index_enabled:
            self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS file_content USING FTS5(
                file_id,
                content
            )
            ''')

        self.create_indexes()
        
        self.conn.commit()

    def create_indexes(self):
        """为高频过滤和排序字段创建索引。"""
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_size ON files(size)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_mtime ON files(mtime)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_is_directory ON files(is_directory)")
    
    def close_db(self):
        if self.conn:
            self.conn.close()
    
    def build_index(self):
        logger.info("开始构建索引...")
        logger.info(f"扫描路径: {self.scan_paths}")
        
        self.connect_db()
        
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
            existing_mtime_map = self._get_existing_mtime_map([f["path"] for f in all_files])
            self.batch_insert_files(all_files)
            self._delete_removed_entries(all_files)
        else:
            existing_mtime_map = {}
        
        # 构建全文索引
        if self.content_index_enabled:
            logger.info("开始构建全文索引...")
            content_files = [
                f for f in all_files
                if self._should_index_content(f)
                and (f["path"] not in existing_mtime_map or existing_mtime_map[f["path"]] != f["mtime"])
            ]
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
    
    def scan_directory(self, directory):
        """高效扫描目录，使用多线程并行处理"""
        def scan_dir(path):
            """扫描单个目录"""
            try:
                entries = list(os.scandir(path))
            except Exception as e:
                logger.error(f"Error scanning directory {path}: {e}")
                return [], []
            
            files = []
            subdirs = []
            
            for entry in entries:
                if entry.name in self.exclude_dirs:
                    continue
                
                try:
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except Exception:
                        is_dir = False
                    
                    try:
                        is_file = entry.is_file(follow_symlinks=False)
                    except Exception:
                        is_file = False
                    
                    if is_dir:
                        subdirs.append(Path(entry.path))
                        try:
                            stat = entry.stat(follow_symlinks=False)
                            files.append({
                                'path': str(entry.path),
                                'name': entry.name,
                                'extension': '',
                                'size': 0,
                                'mtime': int(stat.st_mtime),
                                'is_directory': True
                            })
                        except Exception as e:
                            logger.error(f"Error processing directory {entry.path}: {e}")
                    elif is_file:
                        try:
                            stat = entry.stat(follow_symlinks=False)
                            files.append({
                                'path': str(entry.path),
                                'name': entry.name,
                                'extension': Path(entry.name).suffix,
                                'size': stat.st_size,
                                'mtime': int(stat.st_mtime),
                                'is_directory': False
                            })
                        except Exception as e:
                            logger.error(f"Error processing file {entry.path}: {e}")
                except Exception as e:
                    logger.error(f"Error processing item {entry.path}: {e}")
            
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
            sql = """
            INSERT INTO files (path, name, extension, size, mtime, is_directory)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                name=excluded.name,
                extension=excluded.extension,
                size=excluded.size,
                mtime=excluded.mtime,
                is_directory=excluded.is_directory
            """
            
            # 准备数据
            data = []
            for file in files:
                data.append((file['path'], file['name'], file['extension'], file['size'], file['mtime'], file.get('is_directory', 0)))
                
                # 当数据达到批量大小时，执行插入
                if len(data) >= batch_size:
                    self.cursor.executemany(sql, data)
                    logger.info(f"  已处理 {min(len(data), total)}/{total} 个文件")
                    data = []
            
            # 插入剩余数据
            if data:
                self.cursor.executemany(sql, data)
                logger.info(f"  已处理 {total}/{total} 个文件")
            
            # 一次性提交事务
            self.conn.commit()
            logger.info("文件信息插入完成")
        except Exception as e:
            logger.error(f"Error inserting files: {e}")
            # 发生错误时回滚事务
            self.conn.rollback()

    def _get_existing_mtime_map(self, paths):
        """批量读取已有文件 mtime，用于增量内容索引判断。"""
        if not paths:
            return {}
        result = {}
        batch_size = 1000
        for i in range(0, len(paths), batch_size):
            batch_paths = paths[i:i+batch_size]
            placeholders = ",".join(["?"] * len(batch_paths))
            query = f"SELECT path, mtime FROM files WHERE path IN ({placeholders})"
            self.cursor.execute(query, batch_paths)
            for row_path, row_mtime in self.cursor.fetchall():
                result[row_path] = row_mtime
        return result

    def _delete_removed_entries(self, all_files):
        """删除已不在扫描目录中的历史索引记录。"""
        current_paths = {f["path"] for f in all_files}
        if not self.scan_paths:
            return

        stale_ids = []
        for scan_path in self.scan_paths:
            like_pattern = str(Path(scan_path)) + "%"
            self.cursor.execute("SELECT id, path FROM files WHERE path LIKE ?", (like_pattern,))
            for file_id, path in self.cursor.fetchall():
                if path not in current_paths:
                    stale_ids.append(file_id)

        if not stale_ids:
            return

        logger.info(f"检测到 {len(stale_ids)} 条失效索引，准备清理")
        batch_size = 1000
        for i in range(0, len(stale_ids), batch_size):
            batch_ids = stale_ids[i:i+batch_size]
            placeholders = ",".join(["?"] * len(batch_ids))
            if self.content_index_enabled:
                self.cursor.execute(f"DELETE FROM file_content WHERE file_id IN ({placeholders})", batch_ids)
            self.cursor.execute(f"DELETE FROM files WHERE id IN ({placeholders})", batch_ids)
    
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
        
        def process_file(file_path):
            return file_path, self._read_file_content(file_path)

        # 边读取边写入，避免在内存中累积大量文件内容
        try:
            self.conn.execute('BEGIN TRANSACTION')

            insert_content_sql = "INSERT OR REPLACE INTO file_content (file_id, content) VALUES (?, ?)"
            indexed_file_ids = []
            pending_rows = []
            flush_size = 2000
            indexed_count = 0

            candidate_paths = [f["path"] for f in files if f["path"] in file_ids]
            max_workers = min(self.threads, os.cpu_count() * 4)
            total = len(candidate_paths)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(process_file, path) for path in candidate_paths]
                for i, future in enumerate(as_completed(futures), 1):
                    try:
                        file_path, content = future.result()
                        if not content:
                            continue
                        file_id = file_ids[file_path]
                        pending_rows.append((file_id, content))
                        indexed_file_ids.append(file_id)
                        if len(pending_rows) >= flush_size:
                            self.cursor.executemany(insert_content_sql, pending_rows)
                            indexed_count += len(pending_rows)
                            pending_rows = []
                    except Exception:
                        continue

                    if i % 1000 == 0 or i == total:
                        logger.info(f"  已处理 {i}/{total} 个文件内容")

            if pending_rows:
                self.cursor.executemany(insert_content_sql, pending_rows)
                indexed_count += len(pending_rows)

            if indexed_file_ids:
                update_batch_size = 10000
                for i in range(0, len(indexed_file_ids), update_batch_size):
                    batch_ids = indexed_file_ids[i:i+update_batch_size]
                    placeholders = ','.join(['?'] * len(batch_ids))
                    update_sql = f"UPDATE files SET is_content_indexed = 1 WHERE id IN ({placeholders})"
                    self.cursor.execute(update_sql, batch_ids)

            self.conn.commit()
            logger.info(f"全文索引构建完成，共索引 {indexed_count} 个文件")
        except Exception as e:
            logger.error(f"Error inserting content: {e}")
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
