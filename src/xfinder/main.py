import click
import json
import time
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

from .config import config
from .indexer import Indexer
from .searcher import Searcher

# 创建主命令组
@click.group()
@click.option('--path', '-p', help='指定扫描目录')
@click.option('--threads', '-t', type=int, default=32, help='指定扫描和索引的线程数量')
@click.pass_context
def cli(ctx, path, threads):
    """xfinder - 快速文件搜索工具"""
    ctx.ensure_object(dict)
    ctx.obj['path'] = path
    ctx.obj['threads'] = threads

# 搜索子命令
@cli.command()
@click.argument('query')
@click.option('--json', is_flag=True, help='输出JSON格式')
@click.option('--limit', default=20, help='控制返回条数')
@click.option('--sort', default='relevance', help='排序方式: relevance, name, size, time')
@click.pass_context
def search(ctx, query, json, limit, sort):
    """一次性查询模式"""
    # 构建索引
    indexer = Indexer(custom_paths=[ctx.obj['path']] if ctx.obj['path'] else None, threads=ctx.obj['threads'])
    indexer.build_index()
    
    searcher = Searcher()
    result = searcher.search(query, limit=limit, sort_by=sort)
    
    if json:
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        click.echo(f"结果（共 {result['count']} 条，耗时 {result['time']*1000:.0f}ms）：")
        for i, item in enumerate(result['results'], 1):
            click.echo(f"  {i}. {item['path']}          [{item['match_type']}]")

# 应用程序子命令
@cli.command()
@click.pass_context
def app(ctx):
    """启动图形用户界面"""
    from .app import run_app
    run_app()


if __name__ == '__main__':
    cli()

