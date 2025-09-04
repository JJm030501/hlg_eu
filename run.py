#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
东方智答系统启动脚本
"""

import sys
import os
import argparse
import logging
from pathlib import Path
import warnings

# 忽略 pkg_resources 弃用警告
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
# 忽略 jieba 相关警告
warnings.filterwarnings("ignore", category=UserWarning, module="jieba")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.config import Config
from api.app import app
from database.db_manager import DatabaseManager
from crawler.spider import HLJEUSpider
from models.knowledge_builder import KnowledgeBuilder

# 配置日志
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_database():
    """检查数据库连接"""
    try:
        db = DatabaseManager()
        stats = db.get_statistics()
        logger.info(f"Database connected. Total pages: {stats.get('total_pages', 0)}")
        db.close()
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

def init_system():
    """初始化系统"""
    logger.info("Initializing system...")
    
    # 检查数据库
    if not check_database():
        logger.error("Please check your database configuration")
        return False
    
    # 检查API密钥（调试模式下不显示警告）
    if not Config.DEEPSEEK_API_KEY:
        logger.debug("DeepSeek API key not configured. Using HuggingFace API instead.")
    
    logger.info("System initialized successfully")
    return True

def run_crawler():
    """运行爬虫"""
    logger.info("Starting crawler...")
    spider = HLJEUSpider()
    spider.start_crawling()
    logger.info("Crawler completed")

def build_knowledge():
    """构建知识库"""
    logger.info("Building knowledge base...")
    builder = KnowledgeBuilder()
    stats = builder.build_all()
    logger.info(f"Knowledge base built. Entries: {stats.get('knowledge_entries', 0)}")

def run_server():
    """运行Web服务器"""
    logger.info(f"Starting web server on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='东方智答系统管理工具')
    parser.add_argument('command', choices=['init', 'crawl', 'build', 'server', 'all'],
                       help='要执行的命令')
    parser.add_argument('--force', action='store_true',
                       help='强制执行，忽略警告')
    
    args = parser.parse_args()
    
    # 初始化系统
    if not init_system() and not args.force:
        logger.error("System initialization failed. Use --force to continue anyway.")
        return
    
    # 执行命令
    if args.command == 'init':
        logger.info("System initialization completed")
    
    elif args.command == 'crawl':
        run_crawler()
    
    elif args.command == 'build':
        build_knowledge()
    
    elif args.command == 'server':
        run_server()
    
    elif args.command == 'all':
        # 执行完整流程
        logger.info("Running full setup process...")
        
        # 爬取数据
        if input("Do you want to crawl website data? (y/n): ").lower() == 'y':
            run_crawler()
        
        # 构建知识库
        if input("Do you want to build knowledge base? (y/n): ").lower() == 'y':
            build_knowledge()
        
        # 启动服务器
        if input("Do you want to start the web server? (y/n): ").lower() == 'y':
            run_server()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()