import re
import logging
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
import jieba
jieba.setLogLevel(logging.WARNING)  # 设置jieba日志级别
import jieba.analyse
from collections import defaultdict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager

class KnowledgeBuilder:
    def __init__(self):
        self.db = DatabaseManager()
        self.logger = logging.getLogger(__name__)
        
        # 问答模板
        self.qa_templates = {
            'about': [
                ("黑龙江东方学院是什么性质的学校？", "黑龙江东方学院是一所应用型本科高等院校。"),
                ("学校的办学理念是什么？", ""),
                ("学校的发展历程是怎样的？", ""),
                ("学校的办学特色有哪些？", "")
            ],
            'admission': [
                ("如何报考黑龙江东方学院？", ""),
                ("学校的招生专业有哪些？", ""),
                ("录取分数线是多少？", ""),
                ("学校的招生政策是什么？", "")
            ],
            'academic': [
                ("学校有哪些重点学科？", ""),
                ("学校的科研成果有哪些？", ""),
                ("学校的教学质量如何？", ""),
                ("学校有哪些实验室和研究中心？", "")
            ],
            'campus': [
                ("学校的地理位置在哪里？", "学校位于黑龙江省哈尔滨市。"),
                ("校园环境怎么样？", ""),
                ("学校的住宿条件如何？", ""),
                ("学校有哪些学生组织和社团？", "")
            ]
        }
        
        # 关键词提取配置
        self.keyword_config = {
            'topK': 5,  # 提取前5个关键词
            'withWeight': False
        }
    
    def extract_keywords(self, text: str) -> List[str]:
        """提取文本关键词"""
        try:
            # 使用TF-IDF提取关键词
            keywords = jieba.analyse.extract_tags(
                text, 
                topK=self.keyword_config['topK'],
                withWeight=self.keyword_config['withWeight']
            )
            return keywords
        except:
            # 如果jieba失败，使用简单的分词
            words = re.findall(r'[\u4e00-\u9fa5]+', text)
            return list(set(words))[:5]
    
    def extract_qa_from_content(self, content: str, url: str = None) -> List[Tuple[str, str]]:
        """从页面内容中提取问答对"""
        qa_pairs = []
        
        # 1. 查找FAQ类型的内容
        faq_patterns = [
            r'问[:：]\s*(.+?)\s*答[:：]\s*(.+?)(?=问[:：]|\Z)',
            r'Q[:：]\s*(.+?)\s*A[:：]\s*(.+?)(?=Q[:：]|\Z)',
            r'【问】(.+?)【答】(.+?)(?=【问】|\Z)'
        ]
        
        for pattern in faq_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for q, a in matches:
                q = q.strip()[:200]  # 限制问题长度
                a = a.strip()[:500]  # 限制答案长度
                if len(q) > 5 and len(a) > 5:
                    qa_pairs.append((q, a))
        
        # 2. 从标题和内容提取
        title_pattern = r'([^。！？\n]{5,30}[？?])'
        potential_questions = re.findall(title_pattern, content)
        
        for question in potential_questions:
            # 查找问题后面的内容作为答案
            idx = content.find(question)
            if idx != -1:
                answer_start = idx + len(question)
                answer_end = answer_start + 300  # 最多取300个字符
                answer = content[answer_start:answer_end]
                
                # 清理答案
                answer = re.sub(r'\s+', ' ', answer).strip()
                if len(answer) > 20:
                    # 截断到句号
                    sentences = re.split(r'[。！？]', answer)
                    if sentences:
                        answer = sentences[0] + '。'
                        qa_pairs.append((question, answer))
        
        return qa_pairs
    
    def generate_qa_from_pages(self, page_type: str = None, limit: int = 100):
        """从爬取的页面生成问答知识库"""
        # 获取页面内容
        if page_type:
            query = "SELECT * FROM crawled_pages WHERE page_type = %s LIMIT %s"
            pages = self.db.execute_query(query, (page_type, limit))
        else:
            query = "SELECT * FROM crawled_pages LIMIT %s"
            pages = self.db.execute_query(query, (limit,))
        
        total_qa = 0
        
        for page in pages:
            content = page['content']
            url = page['url']
            category = page['category']
            
            # 提取问答对
            qa_pairs = self.extract_qa_from_content(content, url)
            
            # 保存到知识库
            for question, answer in qa_pairs:
                keywords = ' '.join(self.extract_keywords(question + ' ' + answer))
                success = self.db.save_knowledge(
                    question=question,
                    answer=answer,
                    source_url=url,
                    category=category,
                    keywords=keywords,
                    confidence=0.8
                )
                if success:
                    total_qa += 1
        
        self.logger.info(f"Generated {total_qa} QA pairs from {len(pages)} pages")
        return total_qa
    
    def build_structured_knowledge(self):
        """构建结构化知识"""
        # 统计页面分类
        query = """
            SELECT page_type, category, COUNT(*) as count,
                   GROUP_CONCAT(DISTINCT title SEPARATOR '|||') as titles
            FROM crawled_pages
            GROUP BY page_type, category
        """
        stats = self.db.execute_query(query)
        
        for stat in stats:
            page_type = stat['page_type']
            category = stat['category']
            count = stat['count']
            titles = stat['titles'].split('|||') if stat['titles'] else []
            
            # 生成分类相关的问答
            if page_type == 'academic':
                question = f"学校在{category}方面有哪些内容？"
                answer = f"学校在{category}方面有{count}个相关页面，包括：" + '、'.join(titles[:5])
                if len(titles) > 5:
                    answer += f"等{len(titles)}个方面的内容。"
                
                self.db.save_knowledge(
                    question=question,
                    answer=answer,
                    category=category,
                    confidence=0.9
                )
            
            elif page_type == 'news':
                question = f"学校最近有哪些{category}相关的新闻？"
                answer = f"最近的{category}相关新闻包括：" + '、'.join(titles[:3])
                
                self.db.save_knowledge(
                    question=question,
                    answer=answer,
                    category=category,
                    confidence=0.7
                )
    
    def analyze_content_topics(self):
        """分析内容主题"""
        query = "SELECT content FROM crawled_pages WHERE content IS NOT NULL AND content != ''"
        pages = self.db.execute_query(query)
        
        # 统计词频
        word_freq = defaultdict(int)
        
        for page in pages:
            keywords = self.extract_keywords(page['content'])
            for keyword in keywords:
                word_freq[keyword] += 1
        
        # 获取高频词
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
        
        # 基于高频词生成问答
        for word, freq in top_words[:20]:
            if len(word) >= 2:  # 过滤掉单字
                question = f"关于{word}的信息有哪些？"
                
                # 搜索包含该词的内容
                search_query = """
                    SELECT title, SUBSTRING(content, 1, 200) as snippet
                    FROM crawled_pages
                    WHERE content LIKE %s
                    LIMIT 3
                """
                results = self.db.execute_query(search_query, (f'%{word}%',))
                
                if results:
                    answer = f"关于{word}的相关信息包括："
                    for r in results:
                        if r['title']:
                            answer += f"\n- {r['title']}"
                    
                    self.db.save_knowledge(
                        question=question,
                        answer=answer,
                        keywords=word,
                        confidence=0.6
                    )
    
    def create_default_qa(self):
        """创建默认的问答对"""
        default_qas = [
            ("黑龙江东方学院的官网是什么？", "黑龙江东方学院的官方网站是 https://www.hljeu.edu.cn"),
            ("如何联系学校？", "您可以通过学校官网 https://www.hljeu.edu.cn 查找具体的联系方式，包括各部门电话和邮箱。"),
            ("学校在哪个城市？", "黑龙江东方学院位于黑龙江省哈尔滨市。"),
            ("学校是公办还是民办？", "黑龙江东方学院是一所应用型本科院校，具体办学性质请查询学校官网。"),
            ("学校有哪些学院？", "学校设有多个学院和教学部门，具体请访问学校官网的院系设置栏目。"),
            ("如何查询录取结果？", "录取结果可以通过学校招生网或招生办公室电话查询。"),
            ("学校的校训是什么？", "具体校训请访问学校官网的学校概况栏目查看。"),
            ("学校有研究生教育吗？", "关于研究生教育的信息，请访问学校官网的教育教学栏目。"),
            ("学校的特色专业有哪些？", "学校的特色专业信息可以在官网的专业建设栏目查看。"),
            ("如何申请奖学金？", "奖学金申请的具体要求和流程，请咨询学生处或查看学校官网相关通知。")
        ]
        
        for question, answer in default_qas:
            self.db.save_knowledge(
                question=question,
                answer=answer,
                category='general',
                keywords=' '.join(self.extract_keywords(question)),
                confidence=1.0
            )
        
        self.logger.info(f"Created {len(default_qas)} default QA pairs")
    
    def build_all(self):
        """构建完整的知识库"""
        self.logger.info("Starting knowledge base building...")
        
        # 1. 创建默认问答
        self.create_default_qa()
        
        # 2. 从页面内容生成问答
        self.generate_qa_from_pages()
        
        # 3. 构建结构化知识
        self.build_structured_knowledge()
        
        # 4. 分析内容主题
        self.analyze_content_topics()
        
        # 获取统计信息
        stats = self.db.get_statistics()
        self.logger.info(f"Knowledge base built. Total entries: {stats.get('knowledge_entries', 0)}")
        
        return stats

if __name__ == "__main__":
    builder = KnowledgeBuilder()
    stats = builder.build_all()
    print("Knowledge base statistics:", stats)