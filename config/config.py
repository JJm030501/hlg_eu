import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 数据库配置
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '123456')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'hlg_eu')
    
    # DeepSeek API配置（可选）
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'
    
    # Hugging Face API配置（可选）
    HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', '')
    
    # 爬虫配置
    BASE_URL = 'https://www.hljeu.edu.cn'
    CRAWL_DELAY = 1  # 爬取延迟（秒）
    MAX_DEPTH = 3  # 最大爬取深度
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # Flask配置
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = 5001
    FLASK_DEBUG = True
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # 日志配置
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'dongfang_zhida.log'