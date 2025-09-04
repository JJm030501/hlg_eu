import requests
import json
import logging
from typing import Dict, List, Optional
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config

class HuggingFaceClient:
    def __init__(self):
        # Hugging Face API Token (可选，有token限额更高)
        self.api_token = Config.HUGGINGFACE_API_KEY if hasattr(Config, 'HUGGINGFACE_API_KEY') else None
        
        # 模型选择（可以更换其他模型）
        self.models = {
            'qwen': 'Qwen/Qwen2.5-7B-Instruct',
            'chatglm': 'THUDM/chatglm3-6b', 
            'yi': '01-ai/Yi-6B-Chat',
            'bloom': 'bigscience/bloom',  # 多语言模型
            'llama': 'meta-llama/Llama-2-7b-chat-hf'  # 需要许可
        }
        
        # 默认使用Qwen模型
        self.current_model = self.models['qwen']
        
        # API端点
        self.api_url = f"https://api-inference.huggingface.co/models/{self.current_model}"
        
        self.logger = logging.getLogger(__name__)
        
        # 系统提示词
        self.system_prompt = """你是黑龙江东方学院的智能助手"东方智答"。你的任务是基于学校的官方信息，为用户提供准确、专业、友好的问答服务。

请遵循以下原则：
1. 回答要准确、简洁、专业
2. 如果不确定答案，请诚实说明并建议用户查询官方渠道
3. 保持友好和专业的语气
4. 优先使用知识库中的信息回答
5. 涉及具体政策、分数线等信息时，提醒用户以官方发布为准

你可以回答关于以下方面的问题：
- 学校概况和历史
- 院系专业设置
- 招生政策和录取信息
- 教学科研情况
- 校园生活和设施
- 就业指导和服务"""
    
    def switch_model(self, model_name: str):
        """切换模型"""
        if model_name in self.models:
            self.current_model = self.models[model_name]
            self.api_url = f"https://api-inference.huggingface.co/models/{self.current_model}"
            self.logger.info(f"Switched to model: {self.current_model}")
        else:
            self.logger.error(f"Unknown model: {model_name}")
    
    def create_prompt(self, user_question: str, context: str = None, history: List[Dict] = None) -> str:
        """创建提示词"""
        prompt_parts = []
        
        # 添加系统提示
        prompt_parts.append(f"系统提示：{self.system_prompt}\n")
        
        # 添加历史对话（只保留最近2轮）
        if history and len(history) > 0:
            prompt_parts.append("历史对话：")
            for h in history[-2:]:
                prompt_parts.append(f"用户：{h.get('user_question', '')}")
                prompt_parts.append(f"助手：{h.get('system_answer', '')}")
            prompt_parts.append("")
        
        # 添加上下文信息
        if context:
            prompt_parts.append(f"参考信息：\n{context}\n")
        
        # 添加当前问题
        prompt_parts.append(f"用户问题：{user_question}")
        prompt_parts.append("助手回答：")
        
        return "\n".join(prompt_parts)
    
    def call_api(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """调用Hugging Face API"""
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.7,
                "top_p": 0.95,
                "do_sample": True,
                "return_full_text": False
            },
            "options": {
                "wait_for_model": True  # 等待模型加载
            }
        }
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=60  # 增加超时时间
                )
                
                response_time = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 处理不同格式的响应
                    if isinstance(result, list) and len(result) > 0:
                        text = result[0].get('generated_text', '')
                    elif isinstance(result, dict):
                        text = result.get('generated_text', '')
                    else:
                        text = str(result)
                    
                    # 清理输出
                    text = self.clean_response(text, prompt)
                    
                    self.logger.info(f"HuggingFace API call successful. Response time: {response_time}ms")
                    return text
                    
                elif response.status_code == 503:
                    # 模型正在加载，等待后重试
                    wait_time = 20 * (attempt + 1)
                    self.logger.warning(f"Model is loading, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                    
                else:
                    self.logger.error(f"HuggingFace API error: {response.status_code} - {response.text}")
                    
                    # 如果是速率限制，等待后重试
                    if response.status_code == 429:
                        time.sleep(30)
                        continue
                    
                    return None
                    
            except requests.exceptions.Timeout:
                self.logger.error("HuggingFace API timeout")
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                    
            except Exception as e:
                self.logger.error(f"HuggingFace API exception: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
        
        return None
    
    def clean_response(self, text: str, prompt: str) -> str:
        """清理响应文本"""
        # 移除原始prompt
        if prompt in text:
            text = text.replace(prompt, '')
        
        # 移除重复的系统提示
        if self.system_prompt in text:
            text = text.replace(self.system_prompt, '')
        
        # 提取助手回答部分
        if '助手回答：' in text:
            parts = text.split('助手回答：')
            if len(parts) > 1:
                text = parts[-1]
        elif '助手：' in text:
            parts = text.split('助手：')
            if len(parts) > 1:
                text = parts[-1]
        
        # 清理首尾空白
        text = text.strip()
        
        # 如果还是太长，截断
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        return text
    
    def answer_with_context(self, question: str, knowledge_base_results: List[Dict], 
                           history: List[Dict] = None) -> Dict:
        """基于知识库上下文回答问题"""
        start_time = time.time()
        
        # 优先使用知识库中的精确匹配
        if knowledge_base_results and len(knowledge_base_results) > 0:
            # 如果知识库有高置信度的答案，直接使用
            best_result = knowledge_base_results[0]
            # 降低门槛，让更多知识库答案能被使用
            if best_result.get('relevance', 0) >= 1.0 or best_result.get('confidence_score', 0) >= 0.7:
                response_time = int((time.time() - start_time) * 1000)
                return {
                    'answer': best_result['answer'],
                    'source': 'knowledge_base',
                    'response_time': response_time,
                    'confidence': best_result.get('confidence_score', 0.9)
                }
        
        # 构建上下文
        context = self.build_context(knowledge_base_results)
        
        # 创建提示词
        prompt = self.create_prompt(question, context, history)
        
        # 尝试调用API（但设置更短的超时）
        answer = None
        try:
            answer = self.call_api(prompt, max_retries=1)  # 减少重试次数
        except:
            pass  # 忽略API错误，使用后备方案
        
        response_time = int((time.time() - start_time) * 1000)
        
        if answer:
            return {
                'answer': answer,
                'source': 'huggingface',
                'model': self.current_model,
                'response_time': response_time,
                'confidence': 0.8 if context else 0.6
            }
        else:
            # 如果API调用失败，使用知识库或默认回答
            if knowledge_base_results:
                return {
                    'answer': knowledge_base_results[0]['answer'],
                    'source': 'knowledge_base',
                    'response_time': response_time,
                    'confidence': knowledge_base_results[0].get('confidence_score', 0.6)
                }
            else:
                # 提供更有用的默认回答
                return {
                    'answer': "抱歉，我暂时没有找到相关信息。您可以访问学校官网 https://www.hljeu.edu.cn 或致电招生办公室了解详情。",
                    'source': 'default',
                    'response_time': response_time,
                    'confidence': 0.3
                }
    
    def build_context(self, knowledge_base_results: List[Dict]) -> str:
        """构建上下文信息"""
        if not knowledge_base_results:
            return ""
        
        context_parts = []
        for i, item in enumerate(knowledge_base_results[:3], 1):  # 最多使用3条
            context_parts.append(f"{i}. 问题：{item['question']}")
            context_parts.append(f"   答案：{item['answer']}")
            if item.get('source_url'):
                context_parts.append(f"   来源：{item['source_url']}")
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def generate_similar_questions(self, question: str) -> List[str]:
        """生成相似问题推荐"""
        prompt = f"""基于用户问题："{question}"
        
请生成3个相关的问题，每个问题用换行分隔，不要编号。

相关问题："""
        
        response = self.call_api(prompt)
        
        if response:
            questions = [q.strip() for q in response.split('\n') if q.strip()]
            # 过滤掉包含数字编号的行
            questions = [q for q in questions if not q[0].isdigit()]
            return questions[:3]
        
        return []
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = self.call_api("你好")
            return response is not None
        except:
            return False

if __name__ == "__main__":
    # 测试Hugging Face客户端
    client = HuggingFaceClient()
    
    print("Testing Hugging Face API connection...")
    if client.test_connection():
        print("✓ Connection successful!")
        
        # 测试基本问答
        test_question = "黑龙江东方学院有哪些专业？"
        result = client.answer_with_context(test_question, [])
        print(f"\nQuestion: {test_question}")
        print(f"Answer: {result['answer']}")
        print(f"Model: {result.get('model', 'unknown')}")
        print(f"Response time: {result['response_time']}ms")
    else:
        print("✗ Connection failed. Please check your network.")