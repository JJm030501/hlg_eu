import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import logging
from typing import Set, Dict, List
import re
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from database.db_manager import DatabaseManager

class HLJEUSpider:
    def __init__(self):
        self.base_url = Config.BASE_URL
        self.visited_urls: Set[str] = set()
        self.to_visit: List[str] = []
        self.db = DatabaseManager()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': Config.USER_AGENT
        })
        
        # 配置日志
        logging.basicConfig(
            level=getattr(logging, Config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # URL模式分类
        self.url_patterns = {
            'news': [r'/news/', r'/xinwen/', r'/notice/'],
            'academic': [r'/jiaoxue/', r'/keyan/', r'/academic/'],
            'admission': [r'/zhaosheng/', r'/admission/'],
            'department': [r'/yuanxi/', r'/department/', r'/school/'],
            'about': [r'/about/', r'/jianjie/', r'/gaikuang/']
        }
    
    def classify_url(self, url: str) -> str:
        """根据URL模式对页面进行分类"""
        for category, patterns in self.url_patterns.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return category
        return 'general'
    
    def is_valid_url(self, url: str) -> bool:
        """检查URL是否有效且属于目标网站"""
        try:
            parsed = urlparse(url)
            # 检查是否是同一域名
            if parsed.netloc and not parsed.netloc.startswith('www.hljeu.edu.cn'):
                return False
            # 过滤掉一些不需要的URL
            exclude_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.jpg', '.png', '.gif']
            if any(url.lower().endswith(ext) for ext in exclude_extensions):
                return False
            return True
        except:
            return False
    
    def extract_page_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """提取页面内容"""
        # 提取标题
        title = ''
        if soup.title:
            title = soup.title.string
        elif soup.h1:
            title = soup.h1.get_text()
        
        # 提取正文内容
        content_parts = []
        
        # 尝试找到主要内容区域
        main_content = soup.find('div', {'class': ['content', 'main-content', 'article-content']})
        if main_content:
            content_parts.append(main_content.get_text(separator=' ', strip=True))
        else:
            # 提取所有段落
            for p in soup.find_all('p'):
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # 过滤掉太短的段落
                    content_parts.append(text)
            
            # 提取列表项
            for li in soup.find_all('li'):
                text = li.get_text(strip=True)
                if text and len(text) > 10:
                    content_parts.append(text)
        
        content = ' '.join(content_parts)
        
        # 清理内容
        content = re.sub(r'\s+', ' ', content)
        content = content[:10000]  # 限制内容长度
        
        return {
            'url': url,
            'title': title[:255] if title else '',
            'content': content,
            'page_type': self.classify_url(url),
            'category': self.extract_category(soup, url)
        }
    
    def extract_category(self, soup: BeautifulSoup, url: str) -> str:
        """提取页面分类信息"""
        # 尝试从面包屑导航提取
        breadcrumb = soup.find('div', {'class': ['breadcrumb', 'crumb', 'location']})
        if breadcrumb:
            crumb_text = breadcrumb.get_text(strip=True)
            if crumb_text:
                return crumb_text.split('>')[-1].strip()[:100]
        
        # 尝试从URL路径提取
        path_parts = urlparse(url).path.split('/')
        if len(path_parts) > 2:
            return path_parts[1]
        
        return 'general'
    
    def crawl_page(self, url: str, depth: int = 0) -> None:
        """爬取单个页面"""
        if depth > Config.MAX_DEPTH:
            return
        
        if url in self.visited_urls:
            return
        
        try:
            self.logger.info(f"Crawling: {url} (depth: {depth})")
            
            # 添加延迟，避免过快请求
            time.sleep(Config.CRAWL_DELAY)
            
            response = self.session.get(url, timeout=10)
            response.encoding = response.apparent_encoding or 'utf-8'
            
            if response.status_code != 200:
                self.logger.warning(f"Failed to fetch {url}: Status {response.status_code}")
                return
            
            self.visited_urls.add(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取并保存页面内容
            page_data = self.extract_page_content(soup, url)
            if page_data['content']:
                self.db.save_crawled_page(page_data)
                self.logger.info(f"Saved: {page_data['title'][:50]}")
            
            # 提取页面中的链接
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(self.base_url, link['href'])
                if self.is_valid_url(absolute_url) and absolute_url not in self.visited_urls:
                    self.to_visit.append((absolute_url, depth + 1))
            
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {str(e)}")
    
    def crawl_specific_urls(self, urls_file: str = 'wangye.txt'):
        """从文件读取并爬取特定URL"""
        try:
            # 读取URL文件
            file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), urls_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f.readlines() if line.strip() and line.strip().startswith('http')]
            
            if not urls:
                self.logger.error(f"No valid URLs found in {urls_file}")
                return
            
            self.logger.info(f"Found {len(urls)} URLs to crawl from {urls_file}")
            
            # 创建爬取任务
            task_id = f"specific_crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.db.create_crawl_task(task_id, f"Specific URLs from {urls_file}")
            
            crawled_count = 0
            
            for url in urls:
                if url not in self.visited_urls:
                    try:
                        self.logger.info(f"Crawling specific URL: {url}")
                        time.sleep(Config.CRAWL_DELAY)
                        
                        response = self.session.get(url, timeout=10)
                        # 尝试不同的编码
                        if response.encoding == 'ISO-8859-1':
                            response.encoding = 'utf-8'
                        else:
                            response.encoding = response.apparent_encoding or 'utf-8'
                        
                        if response.status_code != 200:
                            self.logger.warning(f"Failed to fetch {url}: Status {response.status_code}")
                            continue
                        
                        self.visited_urls.add(url)
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # 提取并保存页面内容
                        page_data = self.extract_page_content(soup, url)
                        if page_data['content']:
                            self.db.save_crawled_page(page_data)
                            self.logger.info(f"Saved: {page_data['title'][:50]}")
                            crawled_count += 1
                        
                        # 更新任务进度
                        if crawled_count % 5 == 0:
                            self.db.update_crawl_task(task_id, 'running', crawled_count, len(urls))
                            
                    except Exception as e:
                        self.logger.error(f"Error crawling {url}: {str(e)}")
            
            # 完成爬取
            self.db.update_crawl_task(task_id, 'completed', crawled_count, len(urls))
            self.logger.info(f"Specific crawling completed. Crawled {crawled_count} out of {len(urls)} URLs")
            
        except Exception as e:
            self.logger.error(f"Error in crawl_specific_urls: {str(e)}")
        finally:
            self.db.close()
    
    def start_crawling(self, start_urls: List[str] = None):
        """开始爬取"""
        if not start_urls:
            # 默认起始页面
            start_urls = [
                self.base_url,
                f"{self.base_url}/xxgk/",  # 学校概况
                f"{self.base_url}/jyjx/",  # 教育教学
                f"{self.base_url}/kxyj/",  # 科学研究
                f"{self.base_url}/zsxx/",  # 招生信息
                f"{self.base_url}/jyfw/",  # 就业服务
            ]
        
        # 创建爬取任务
        task_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.db.create_crawl_task(task_id, self.base_url)
        
        # 初始化待访问队列
        for url in start_urls:
            self.to_visit.append((url, 0))
        
        crawled_count = 0
        
        try:
            while self.to_visit and crawled_count < 500:  # 限制最多爬取500个页面
                url, depth = self.to_visit.pop(0)
                if url not in self.visited_urls:
                    self.crawl_page(url, depth)
                    crawled_count += 1
                    
                    # 更新任务进度
                    if crawled_count % 10 == 0:
                        self.db.update_crawl_task(task_id, 'running', crawled_count, len(self.visited_urls))
            
            # 完成爬取
            self.db.update_crawl_task(task_id, 'completed', crawled_count, len(self.visited_urls))
            self.logger.info(f"Crawling completed. Total pages: {len(self.visited_urls)}")
            
        except KeyboardInterrupt:
            self.logger.info("Crawling interrupted by user")
            self.db.update_crawl_task(task_id, 'failed', crawled_count, len(self.visited_urls), "User interrupted")
        except Exception as e:
            self.logger.error(f"Crawling failed: {str(e)}")
            self.db.update_crawl_task(task_id, 'failed', crawled_count, len(self.visited_urls), str(e))
        finally:
            self.db.close()

if __name__ == "__main__":
    import sys
    spider = HLJEUSpider()
    
    # 检查是否指定爬取特定URL
    if len(sys.argv) > 1 and sys.argv[1] == 'specific':
        # 爬取wangye.txt中的特定URL
        spider.crawl_specific_urls()
    else:
        # 默认爬取
        spider.start_crawling()