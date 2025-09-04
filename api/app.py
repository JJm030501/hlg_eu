from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import uuid
import logging
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from database.db_manager import DatabaseManager
from models.knowledge_builder import KnowledgeBuilder

# 导入AI客户端类
DeepSeekClient = None
HuggingFaceClient = None

# 尝试导入AI客户端，优先使用DeepSeek
try:
    from models.deepseek_client import DeepSeekClient
    ai_client = DeepSeekClient()
    print("Using DeepSeek API")
except ImportError:
    try:
        from models.huggingface_client import HuggingFaceClient
        ai_client = HuggingFaceClient()
        print("Using HuggingFace API (Free)")
    except:
        ai_client = None
        print("Warning: No AI client available")

app = Flask(__name__, 
            template_folder='../web/templates',
            static_folder='../web/static')
app.config['SECRET_KEY'] = Config.SECRET_KEY
CORS(app)

# 配置日志
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化组件
db = DatabaseManager()
knowledge_builder = KnowledgeBuilder()

# 测试数据库连接
try:
    stats = db.get_statistics()
    logger.info(f"Database initialized with {stats.get('total_pages', 0)} pages and {stats.get('knowledge_entries', 0)} knowledge entries")
except Exception as e:
    logger.error(f"Database initialization error: {e}")

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天接口"""
    print("[FLASK] Chat endpoint被访问")
    logger.info(">>> CHAT ENDPOINT HIT! <<<")
    try:
        data = request.json
        # 兼容前端发送的message或question参数
        question = data.get('question', data.get('message', '')).strip()
        
        if not question:
            return jsonify({'error': '请输入问题'}), 400
        
        # 获取或创建会话ID
        # 优先使用请求中的session_id，否则从session中获取或创建新的
        session_id = data.get('session_id')
        if not session_id:
            if 'session_id' not in session:
                session['session_id'] = str(uuid.uuid4())
            session_id = session['session_id']
        
        # 1. 从知识库搜索相关内容
        logger.info(f"Searching knowledge base for: {question}")
        knowledge_results = db.get_knowledge_base(question, limit=5)
        logger.info(f"Knowledge base returned {len(knowledge_results)} results")
        
        # 2. 搜索相关页面
        page_results = db.search_pages(question, limit=3)
        
        # 3. 获取最相关页面的完整内容
        page_content = ""
        if page_results:
            # 获取最相关页面的完整内容
            most_relevant_url = page_results[0]['url']
            full_page_query = "SELECT content FROM crawled_pages WHERE url = %s"
            full_page_result = db.execute_query(full_page_query, (most_relevant_url,))
            if full_page_result:
                page_content = full_page_result[0]['content']
                logger.info(f"Found page content for {most_relevant_url}: {len(page_content)} chars")
        
        # 4. 获取历史对话
        history = db.get_recent_qa_history(session_id, limit=3)
        
        # 5. 强制使用DeepSeek生成智能答案（不管知识库是否有匹配）
        if ai_client:
            try:
                logger.info(f"*** FORCING DeepSeek API call for question: {question} ***")
                
                # 获取更多相关信息
                additional_info = []
                
                # 从school_info表获取相关信息
                school_info_query = "SELECT info_key, info_value FROM school_info WHERE info_value IS NOT NULL"
                school_info = db.execute_query(school_info_query)
                for info in school_info:
                    additional_info.append(f"{info['info_key']}: {info['info_value']}")
                
                context_info = "\n".join(additional_info)
                logger.info(f"Added school info context: {len(additional_info)} items")
                
                # 强制使用DeepSeek来生成智能回答，传递页面内容
                if isinstance(ai_client, DeepSeekClient):
                    logger.info("*** Calling DeepSeek API with context ***")
                    result = ai_client.answer_with_context(question, knowledge_results, history, context_info)
                    logger.info(f"*** DeepSeek API returned result with source: {result['source']} ***")
                else:
                    logger.info("*** Using non-DeepSeek client ***")
                    result = ai_client.answer_with_context(question, knowledge_results, history)
                
                # 强制设置source为deepseek相关，确保不使用knowledge_base
                if result.get('source') == 'knowledge_base':
                    result['source'] = 'deepseek_fallback'
                    logger.warning("*** Result source was knowledge_base, changed to deepseek_fallback ***")
                
            except Exception as e:
                logger.error(f"*** AI client failed with error: {str(e)} ***")
                import traceback
                logger.error(f"*** Full error traceback: {traceback.format_exc()} ***")
                
                # AI失败时回退到知识库
                if knowledge_results:
                    best_result = max(knowledge_results, key=lambda x: x.get('relevance', 0))
                    result = {
                        'answer': best_result['answer'],
                        'source': 'knowledge_base_fallback',
                        'response_time': 0,
                        'confidence': best_result.get('confidence_score', 0.7)
                    }
                else:
                    result = {
                        'answer': '抱歉，系统暂时无法处理您的问题。请稍后重试。',
                        'source': 'error',
                        'response_time': 0,
                        'confidence': 0
                    }
        else:
            logger.error("AI client is None - this should not happen!")
            # 如果没有AI客户端，使用纯知识库模式
            if knowledge_results:
                best_result = max(knowledge_results, key=lambda x: x.get('relevance', 0))
                result = {
                    'answer': best_result['answer'],
                    'source': 'knowledge_base_no_ai',
                    'response_time': 0,
                    'confidence': best_result.get('confidence_score', 0.7)
                }
            else:
                result = {
                    'answer': '抱歉，暂时找不到相关信息。建议您访问学校官网 https://www.hljeu.edu.cn 查询。',
                    'source': 'default',
                    'response_time': 0,
                    'confidence': 0.3
                }
        
        # 6. 保存问答记录
        db.save_qa_history(
            session_id=session_id,
            question=question,
            answer=result['answer'],
            source=result['source'],
            response_time=result['response_time']
        )
        
        # 7. 生成相关问题推荐
        if ai_client and hasattr(ai_client, 'generate_similar_questions'):
            similar_questions = ai_client.generate_similar_questions(question)
        else:
            # 默认推荐问题
            similar_questions = [
                "学校有哪些特色专业？",
                "如何报考黑龙江东方学院？",
                "学校的地理位置在哪里？"
            ]
        
        response = {
            'answer': result['answer'],
            'source': result['source'],
            'confidence': result['confidence'],
            'response_time': result['response_time'],
            'similar_questions': similar_questions,
            'references': []
        }
        
        # 添加参考链接
        if page_results:
            for page in page_results[:3]:
                response['references'].append({
                    'title': page['title'],
                    'url': page['url'],
                    'snippet': page['snippet']
                })
        
        return jsonify(response)
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Chat error: {str(e)}\n{error_detail}")
        return jsonify({'error': '系统错误，请稍后重试', 'detail': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def feedback():
    """用户反馈接口"""
    try:
        data = request.json
        qa_id = data.get('qa_id')
        score = data.get('score')
        
        if not qa_id or score not in [1, 2, 3, 4, 5]:
            return jsonify({'error': '参数错误'}), 400
        
        success = db.update_satisfaction_score(qa_id, score)
        
        if success:
            return jsonify({'message': '感谢您的反馈！'})
        else:
            return jsonify({'error': '反馈失败'}), 500
    
    except Exception as e:
        logger.error(f"Feedback error: {str(e)}")
        return jsonify({'error': '系统错误'}), 500

@app.route('/api/statistics')
def statistics():
    """获取系统统计信息"""
    try:
        stats = db.get_statistics()
        logger.info(f"Statistics data: {stats}")
        return jsonify(stats)
    except Exception as e:
        import traceback
        logger.error(f"Statistics error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'error': '获取统计信息失败'}), 500

@app.route('/api/search', methods=['GET'])
def search():
    """搜索接口"""
    try:
        keyword = request.args.get('keyword', '').strip()
        page_type = request.args.get('type', None)
        limit = int(request.args.get('limit', 10))
        
        if not keyword:
            return jsonify({'error': '请输入搜索关键词'}), 400
        
        # 搜索知识库
        knowledge_results = db.get_knowledge_base(keyword, limit=limit)
        
        # 搜索页面
        page_results = db.search_pages(keyword, limit=limit)
        
        return jsonify({
            'knowledge': knowledge_results,
            'pages': page_results
        })
    
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': '搜索失败'}), 500

@app.route('/api/categories')
def get_categories():
    """获取分类列表"""
    try:
        query = """
            SELECT DISTINCT category, COUNT(*) as count
            FROM crawled_pages
            WHERE category IS NOT NULL
            GROUP BY category
            ORDER BY count DESC
        """
        categories = db.execute_query(query)
        return jsonify(categories)
    
    except Exception as e:
        logger.error(f"Categories error: {str(e)}")
        return jsonify({'error': '获取分类失败'}), 500

@app.route('/api/hot_questions')
def hot_questions():
    """获取热门问题"""
    try:
        query = """
            SELECT user_question as question, COUNT(*) as count
            FROM qa_history
            WHERE create_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY user_question
            ORDER BY count DESC
            LIMIT 10
        """
        questions = db.execute_query(query)
        return jsonify(questions)
    
    except Exception as e:
        logger.error(f"Hot questions error: {str(e)}")
        return jsonify({'error': '获取热门问题失败'}), 500

@app.route('/api/admin/crawl', methods=['POST'])
def start_crawl():
    """启动爬虫（需要管理员权限）"""
    try:
        # 这里应该添加权限验证
        auth_token = request.headers.get('Authorization')
        if auth_token != f"Bearer {Config.SECRET_KEY}":  # 简单的认证
            return jsonify({'error': '未授权'}), 401
        
        # 启动爬虫任务（实际应该异步执行）
        from crawler.spider import HLJEUSpider
        spider = HLJEUSpider()
        
        # 这里应该使用异步任务队列（如Celery）
        # 现在只是示例
        import threading
        thread = threading.Thread(target=spider.start_crawling)
        thread.start()
        
        return jsonify({'message': '爬虫任务已启动'})
    
    except Exception as e:
        logger.error(f"Crawl error: {str(e)}")
        return jsonify({'error': '启动爬虫失败'}), 500

@app.route('/api/admin/build_knowledge', methods=['POST'])
def build_knowledge():
    """构建知识库（需要管理员权限）"""
    try:
        # 权限验证
        auth_token = request.headers.get('Authorization')
        if auth_token != f"Bearer {Config.SECRET_KEY}":
            return jsonify({'error': '未授权'}), 401
        
        # 构建知识库
        import threading
        thread = threading.Thread(target=knowledge_builder.build_all)
        thread.start()
        
        return jsonify({'message': '知识库构建已启动'})
    
    except Exception as e:
        logger.error(f"Build knowledge error: {str(e)}")
        return jsonify({'error': '构建知识库失败'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '接口不存在'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500

if __name__ == '__main__':
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )