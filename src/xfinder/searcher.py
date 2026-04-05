import sqlite3
import time
from pathlib import Path
from .config import config

class Searcher:
    def __init__(self):
        self.db_path = config.index_dir / 'xfinder.db'
        self.conn = None
        self.cursor = None
        self.content_index_enabled = config.is_content_index_enabled()
    
    def connect_db(self):
        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()
    
    def close_db(self):
        if self.conn:
            self.conn.close()
    
    def search(self, query=None, folder_name=None, file_name=None, file_type=None, size_min=None, size_max=None, date_min=None, date_max=None, limit=20, sort_by='relevance'):
        self.connect_db()
        
        start_time = time.time()
        
        # 构建搜索条件
        conditions = []
        params = []
        
        # 解析查询字符串（如果提供）
        parsed_query = self._parse_query(query) if query else {'text': '', 'extension': None, 'size_op': None, 'size': None, 'time_op': None, 'time': None}
        
        # 关键词搜索（来自查询字符串）
        if parsed_query['text']:
            text = parsed_query['text']
            # 转换通配符为SQL LIKE模式
            text_like = text.replace('*', '%').replace('?', '_')
            # 确保模糊匹配，即使没有通配符也添加%
            if not text_like.startswith('%'):
                text_like = '%' + text_like
            if not text_like.endswith('%'):
                text_like = text_like + '%'
            conditions.append('(name LIKE ? OR path LIKE ?)')
            params.extend([text_like, text_like])
        
        # 文件夹名称过滤
        if folder_name:
            folder_like = folder_name.replace('*', '%').replace('?', '_')
            if not folder_like.startswith('%'):
                folder_like = '%' + folder_like
            if not folder_like.endswith('%'):
                folder_like = folder_like + '%'
            conditions.append('(name LIKE ? AND is_directory = 1)')
            params.append(folder_like)
        
        # 文件名称过滤
        if file_name:
            file_like = file_name.replace('*', '%').replace('?', '_')
            if not file_like.startswith('%'):
                file_like = '%' + file_like
            if not file_like.endswith('%'):
                file_like = file_like + '%'
            conditions.append('(name LIKE ? AND is_directory = 0)')
            params.append(file_like)
        
        # 文件类型过滤（来自参数）
        if file_type:
            conditions.append('extension = ?')
            params.append(f'.{file_type}')
        # 文件类型过滤（来自查询字符串）
        elif parsed_query['extension']:
            conditions.append('extension = ?')
            params.append(f'.{parsed_query["extension"]}')
        
        # 大小过滤（来自参数）
        if size_min is not None:
            conditions.append('size >= ?')
            params.append(size_min)
        if size_max is not None:
            conditions.append('size <= ?')
            params.append(size_max)
        # 大小过滤（来自查询字符串）
        elif parsed_query['size_op'] and parsed_query['size']:
            size_bytes = self._parse_size(parsed_query['size'])
            if parsed_query['size_op'] == '>':
                conditions.append('size > ?')
            elif parsed_query['size_op'] == '<':
                conditions.append('size < ?')
            elif parsed_query['size_op'] == '=':
                conditions.append('size = ?')
            params.append(size_bytes)
        
        # 时间过滤（来自参数）
        if date_min is not None:
            conditions.append('mtime >= ?')
            params.append(date_min)
        if date_max is not None:
            conditions.append('mtime <= ?')
            params.append(date_max)
        # 时间过滤（来自查询字符串）
        elif parsed_query['time_op'] and parsed_query['time']:
            time_timestamp = self._parse_time(parsed_query['time'])
            if parsed_query['time_op'] == '>':
                conditions.append('mtime > ?')
            elif parsed_query['time_op'] == '<':
                conditions.append('mtime < ?')
            params.append(time_timestamp)
        
        # 构建基础查询
        if conditions:
            where_clause = 'WHERE ' + ' AND '.join(conditions)
        else:
            where_clause = ''
        
        # 执行基础搜索
        base_query = f"SELECT id, path, name, extension, size, mtime, is_directory FROM files {where_clause}"
        
        # 排序
        if sort_by == 'name':
            base_query += ' ORDER BY name'
        elif sort_by == 'size':
            base_query += ' ORDER BY size DESC'
        elif sort_by == 'time':
            base_query += ' ORDER BY mtime DESC'
        else:  # relevance
            # 简单的相关性排序：文件名匹配优先，然后是路径匹配
            if parsed_query['text']:
                base_query += ' ORDER BY CASE WHEN name LIKE ? THEN 0 ELSE 1 END, path LIKE ?'
                params.extend([text_like, text_like])
        
        # 执行查询
        try:
            self.cursor.execute(base_query, params)
            results = self.cursor.fetchall()
        except Exception as e:
            print(f"Error searching: {e}")
            results = []
        
        # 全文搜索
        content_results = []
        if self.content_index_enabled and parsed_query['text']:
            content_query = """
            SELECT f.id, f.path, f.name, f.extension, f.size, f.mtime, f.is_directory 
            FROM files f
            JOIN file_content fc ON f.id = fc.file_id
            WHERE fc.content MATCH ?
            """
            try:
                self.cursor.execute(content_query, (parsed_query['text'],))
                content_results = self.cursor.fetchall()
            except Exception as e:
                print(f"Error in content search: {e}")
        
        # 合并结果，去重
        all_results = {}
        for result in results:
            all_results[result[0]] = result
        for result in content_results:
            all_results[result[0]] = result
        
        # 转换为列表
        final_results = list(all_results.values())
        
        # 限制结果数量
        final_results = final_results[:limit]
        
        end_time = time.time()
        
        # 格式化结果
        formatted_results = []
        for result in final_results:
            file_id, path, name, extension, size, mtime, is_directory = result
            match_type = '文件名匹配' if result in results else '内容匹配'
            if is_directory:
                match_type += ' (文件夹)'
            formatted_results.append({
                'path': path,
                'name': name,
                'extension': extension,
                'size': size,
                'mtime': mtime,
                'is_directory': is_directory,
                'match_type': match_type
            })
        
        self.close_db()
        
        return {
            'results': formatted_results,
            'count': len(formatted_results),
            'time': end_time - start_time
        }
    
    def _parse_query(self, query):
        """解析查询字符串"""
        parts = query.split()
        text_parts = []
        extension = None
        size_op = None
        size = None
        time_op = None
        time = None
        
        for part in parts:
            # 扩展名过滤: type:pdf
            if part.startswith('type:'):
                extension = part[5:]
            # 大小过滤: size>1MB, size<100KB
            elif part.startswith('size'):
                if '>' in part:
                    size_op = '>'
                    size = part[5:]
                elif '<' in part:
                    size_op = '<'
                    size = part[5:]
                elif '=' in part:
                    size_op = '='
                    size = part[5:]
            # 时间过滤: modified:7d, modified:2024-01
            elif part.startswith('modified:'):
                time_str = part[9:]
                time_op = '>'  # 默认是大于（最近）
                time = time_str
            else:
                text_parts.append(part)
        
        return {
            'text': ' '.join(text_parts),
            'extension': extension,
            'size_op': size_op,
            'size': size,
            'time_op': time_op,
            'time': time
        }
    
    def _parse_size(self, size_str):
        """解析文件大小字符串"""
        size_str = size_str.strip().upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def _parse_time(self, time_str):
        """解析时间字符串"""
        import datetime
        
        # 处理天数: 7d
        if time_str.endswith('d'):
            days = int(time_str[:-1])
            return int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())
        # 处理月份: 2024-01
        elif len(time_str) == 7 and '-' in time_str:
            year, month = map(int, time_str.split('-'))
            return int(datetime.datetime(year, month, 1).timestamp())
        # 处理日期: 2024-01-01
        elif len(time_str) == 10 and '-' in time_str:
            year, month, day = map(int, time_str.split('-'))
            return int(datetime.datetime(year, month, day).timestamp())
        else:
            return int(time_str)
