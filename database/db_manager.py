import pymysql
from pymysql.cursors import DictCursor
from typing import Dict, List, Optional
import logging
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config

class DatabaseManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connection = None
        self.connect()
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DATABASE,
                charset='utf8mb4',
                cursorclass=DictCursor,
                autocommit=True
            )
            self.logger.info("Database connection established")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {str(e)}")
            raise
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """执行查询语句"""
        try:
            # 检查连接是否还活着
            self.connection.ping(reconnect=True)
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Query failed: {str(e)}")
            # 尝试重新连接
            try:
                self.connect()
                with self.connection.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.fetchall()
            except:
                return []
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新语句"""
        try:
            # 检查连接是否还活着
            self.connection.ping(reconnect=True)
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.rowcount
        except Exception as e:
            self.logger.error(f"Update failed: {str(e)}")
            # 尝试重新连接
            try:
                self.connect()
                with self.connection.cursor() as cursor:
                    cursor.execute(query, params)
                    return cursor.rowcount
            except:
                return 0
    
    def save_crawled_page(self, page_data: Dict) -> bool:
        """保存爬取的页面数据"""
        query = """
            INSERT INTO crawled_pages (url, title, content, page_type, category)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                content = VALUES(content),
                page_type = VALUES(page_type),
                category = VALUES(category),
                update_time = CURRENT_TIMESTAMP
        """
        params = (
            page_data.get('url', ''),
            page_data.get('title', ''),
            page_data.get('content', ''),
            page_data.get('page_type', 'general'),
            page_data.get('category', 'general')
        )
        
        try:
            self.execute_update(query, params)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save page: {str(e)}")
            return False
    
    def search_pages(self, keyword: str, limit: int = 10) -> List[Dict]:
        """搜索页面内容"""
        # 使用LIKE搜索替代全文搜索
        query = """
            SELECT id, url, title, 
                   SUBSTRING(content, 1, 200) as snippet,
                   page_type, category,
                   (CASE 
                    WHEN title LIKE %s THEN 2.0
                    WHEN content LIKE %s THEN 1.0
                    ELSE 0.5
                   END) as relevance
            FROM crawled_pages
            WHERE title LIKE %s OR content LIKE %s
            ORDER BY relevance DESC
            LIMIT %s
        """
        search_term = f'%{keyword}%'
        return self.execute_query(query, (search_term, search_term, search_term, search_term, limit))
    
    def get_knowledge_base(self, question: str, limit: int = 5) -> List[Dict]:
        """从知识库中搜索相关问答"""
        # 改进搜索算法：拆分关键词进行模糊匹配
        import jieba
        keywords = list(jieba.cut(question))
        keywords = [k.strip() for k in keywords if len(k.strip()) > 1 and k not in ['的', '有', '是', '在', '个', '多少', '哪些', '什么', '如何', '怎么']]
        
        if not keywords:
            keyword = f'%{question}%'
            keywords = [question]
        
        # 构建动态查询
        conditions = []
        params = []
        
        for keyword in keywords:
            keyword_pattern = f'%{keyword}%'
            conditions.append("(question LIKE %s OR answer LIKE %s OR keywords LIKE %s)")
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
        
        where_clause = " OR ".join(conditions)
        
        query = f"""
            SELECT id, question, answer, source_url, confidence_score,
                   (CASE 
                    WHEN question LIKE %s THEN 3.0
                    WHEN answer LIKE %s THEN 2.0
                    ELSE 1.0
                   END) as relevance
            FROM knowledge_base
            WHERE {where_clause}
            ORDER BY relevance DESC, confidence_score DESC
            LIMIT %s
        """
        
        # 添加完整匹配的参数
        full_question = f'%{question}%'
        final_params = [full_question, full_question] + params + [limit]
        
        return self.execute_query(query, final_params)
    
    def save_knowledge(self, question: str, answer: str, source_url: str = None, 
                      category: str = None, keywords: str = None, confidence: float = 1.0) -> bool:
        """保存知识条目"""
        query = """
            INSERT INTO knowledge_base (question, answer, source_url, category, keywords, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (question, answer, source_url, category, keywords, confidence)
        
        try:
            self.execute_update(query, params)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save knowledge: {str(e)}")
            return False
    
    def save_qa_history(self, session_id: str, question: str, answer: str, 
                       source: str = 'mixed', response_time: int = 0) -> bool:
        """保存问答历史"""
        query = """
            INSERT INTO qa_history (session_id, user_question, system_answer, answer_source, response_time_ms)
            VALUES (%s, %s, %s, %s, %s)
        """
        params = (session_id, question, answer, source, response_time)
        
        try:
            self.execute_update(query, params)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save QA history: {str(e)}")
            return False
    
    def get_recent_qa_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """获取最近的问答历史"""
        query = """
            SELECT user_question, system_answer, answer_source, response_time_ms, create_time
            FROM qa_history
            WHERE session_id = %s
            ORDER BY create_time DESC
            LIMIT %s
        """
        return self.execute_query(query, (session_id, limit))
    
    def update_satisfaction_score(self, qa_id: int, score: int) -> bool:
        """更新满意度评分"""
        query = "UPDATE qa_history SET satisfaction_score = %s WHERE id = %s"
        return self.execute_update(query, (score, qa_id)) > 0
    
    def get_system_config(self, key: str) -> Optional[str]:
        """获取系统配置"""
        query = "SELECT config_value FROM system_config WHERE config_key = %s"
        result = self.execute_query(query, (key,))
        return result[0]['config_value'] if result else None
    
    def set_system_config(self, key: str, value: str, description: str = None) -> bool:
        """设置系统配置"""
        query = """
            INSERT INTO system_config (config_key, config_value, description)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                config_value = VALUES(config_value),
                description = VALUES(description)
        """
        return self.execute_update(query, (key, value, description)) > 0
    
    def create_crawl_task(self, task_id: str, start_url: str) -> bool:
        """创建爬虫任务记录"""
        query = """
            INSERT INTO crawl_tasks (task_id, start_url, status, start_time)
            VALUES (%s, %s, 'running', NOW())
        """
        return self.execute_update(query, (task_id, start_url)) > 0
    
    def update_crawl_task(self, task_id: str, status: str, crawled: int = 0, 
                         total: int = 0, error_msg: str = None) -> bool:
        """更新爬虫任务状态"""
        query = """
            UPDATE crawl_tasks
            SET status = %s, crawled_pages = %s, total_pages = %s,
                error_message = %s,
                end_time = CASE WHEN %s IN ('completed', 'failed') THEN NOW() ELSE end_time END
            WHERE task_id = %s
        """
        return self.execute_update(query, (status, crawled, total, error_msg, status, task_id)) > 0
    
    def get_statistics(self) -> Dict:
        """获取系统统计信息"""
        stats = {}
        
        # 页面统计
        query = "SELECT COUNT(*) as total, page_type FROM crawled_pages GROUP BY page_type"
        page_stats = self.execute_query(query)
        stats['pages'] = {item['page_type']: item['total'] for item in page_stats}
        stats['total_pages'] = sum(stats['pages'].values())
        
        # 知识库统计
        query = "SELECT COUNT(*) as total FROM knowledge_base"
        result = self.execute_query(query)
        stats['knowledge_entries'] = result[0]['total'] if result else 0
        
        # 问答统计
        query = """
            SELECT COUNT(*) as total, 
                   AVG(response_time_ms) as avg_response_time,
                   AVG(satisfaction_score) as avg_satisfaction
            FROM qa_history
            WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """
        result = self.execute_query(query)
        if result:
            stats['recent_qa'] = {
                'total': result[0]['total'],
                'avg_response_time': float(result[0]['avg_response_time'] or 0),
                'avg_satisfaction': float(result[0]['avg_satisfaction'] or 0)
            }
        
        return stats
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("Database connection closed")

if __name__ == "__main__":
    # 测试数据库连接
    db = DatabaseManager()
    stats = db.get_statistics()
    print("Database statistics:", stats)
    db.close()