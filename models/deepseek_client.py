#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DeepSeek API客户端 - 按照官方文档重写
"""

import requests
import json
import logging
from typing import Dict, List, Optional
import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config

class DeepSeekClient:
    def __init__(self):
        self.api_key = Config.DEEPSEEK_API_KEY
        self.api_url = "https://api.deepseek.com/chat/completions"  # 官方标准接口
        self.logger = logging.getLogger(__name__)
        
        # 强制设置日志级别为DEBUG
        self.logger.setLevel(logging.DEBUG)
        
        # 如果没有handler，添加一个console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.info(f"*** DeepSeek Client初始化完成 ***")
        self.logger.info(f"*** API Key: {self.api_key[:20]}...（已配置）***" if self.api_key else "*** API Key未配置 ***")
        
        # 输出到控制台用于调试
        print(f"[INIT] DeepSeek Client初始化 - API Key: {'已配置' if self.api_key else '未配置'}")
        
    def call_api(self, messages: List[Dict]) -> Optional[str]:
        """调用DeepSeek API - 严格按照官方文档"""
        print(f"[DEBUG] call_api被调用，消息数量: {len(messages)}")
        
        if not self.api_key:
            print("[ERROR] DeepSeek API key未配置")
            self.logger.error("*** DeepSeek API key未配置 ***")
            return None
        
        # 构建请求体 - 完全按照官方文档
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            self.logger.info(f"*** 开始调用DeepSeek API ***")
            self.logger.info(f"*** 请求URL: {self.api_url} ***")
            self.logger.info(f"*** 消息数量: {len(messages)} ***")
            
            start_time = time.time()
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,  # 使用json参数而不是data
                timeout=30
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            self.logger.info(f"*** API响应状态码: {response.status_code} ***")
            self.logger.info(f"*** 响应时间: {response_time}ms ***")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    self.logger.info(f"*** API响应解析成功 ***")
                    
                    if 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0]['message']['content']
                        self.logger.info(f"*** DeepSeek回答长度: {len(content)} 字符 ***")
                        self.logger.info(f"*** DeepSeek回答前100字符: {content[:100]}... ***")
                        return content
                    else:
                        self.logger.error(f"*** API响应格式错误，无choices字段: {result} ***")
                        return None
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"*** JSON解析失败: {e} ***")
                    self.logger.error(f"*** 原始响应: {response.text[:500]} ***")
                    return None
            else:
                self.logger.error(f"*** DeepSeek API错误: {response.status_code} ***")
                self.logger.error(f"*** 错误内容: {response.text} ***")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("*** DeepSeek API请求超时 ***")
            return None
        except Exception as e:
            self.logger.error(f"*** DeepSeek API异常: {str(e)} ***")
            import traceback
            self.logger.error(f"*** 完整错误: {traceback.format_exc()} ***")
            return None

    def answer_with_context(self, question: str, knowledge_base_results: List[Dict], 
                           history: List[Dict] = None, page_content: str = None) -> Dict:
        """基于上下文回答问题"""
        self.logger.info(f"*** DeepSeek answer_with_context被调用 ***")
        self.logger.info(f"*** 问题: {question} ***")
        
        # 构建上下文
        context_parts = []
        
        if knowledge_base_results:
            context_parts.append("【知识库信息】")
            for i, kb in enumerate(knowledge_base_results[:3]):
                context_parts.append(f"Q{i+1}: {kb.get('question', '')}")
                context_parts.append(f"A{i+1}: {kb.get('answer', '')}")
        
        if page_content:
            context_parts.append(f"【参考内容】\n{page_content[:1000]}")
        
        context_text = "\n".join(context_parts)
        
        # 构建消息 - 按照官方文档格式
        messages = [
            {
                "role": "system", 
                "content": """你是黑龙江东方学院的智能助手"东方智答"。请基于提供的参考信息，准确回答用户问题。

要求：
1. 优先使用参考信息中的具体数据
2. 回答要专业、准确、详细
3. 如果有具体数字，请直接引用
4. 保持友好和专业的语气"""
            }
        ]
        
        # 添加历史对话
        if history:
            for h in history[-2:]:  # 保留最近2轮
                if h.get('user_question'):
                    messages.append({"role": "user", "content": h['user_question']})
                if h.get('system_answer'):
                    messages.append({"role": "assistant", "content": h['system_answer']})
        
        # 添加当前问题和上下文
        user_content = f"参考信息：\n{context_text}\n\n用户问题：{question}"
        messages.append({"role": "user", "content": user_content})
        
        self.logger.info(f"*** 构建消息完成，共{len(messages)}条 ***")
        
        # 强制调用DeepSeek API
        start_time = time.time()
        answer = self.call_api(messages)
        response_time = int((time.time() - start_time) * 1000)
        
        if answer:
            self.logger.info(f"*** DeepSeek API调用成功！返回结果 ***")
            return {
                'answer': answer,
                'source': 'deepseek_api',  # 明确标记为DeepSeek API
                'response_time': response_time,
                'confidence': 0.95
            }
        else:
            self.logger.warning(f"*** DeepSeek API调用失败，回退到知识库 ***")
            # API调用失败，回退到知识库
            if knowledge_base_results:
                best_result = max(knowledge_base_results, key=lambda x: x.get('relevance', 0))
                return {
                    'answer': best_result['answer'],
                    'source': 'knowledge_base_fallback_after_deepseek_failed',
                    'response_time': response_time,
                    'confidence': best_result.get('confidence_score', 0.6)
                }
            else:
                return {
                    'answer': "抱歉，系统暂时无法处理您的问题。请稍后重试或联系招生办：0451-87505389。",
                    'source': 'deepseek_api_failed',
                    'response_time': response_time,
                    'confidence': 0
                }

    def generate_similar_questions(self, question: str) -> List[str]:
        """生成相似问题推荐"""
        messages = [
            {"role": "system", "content": "基于用户的问题，生成3个相关的问题推荐。每个问题用换行分隔，不要编号。"},
            {"role": "user", "content": f"用户问题：{question}\n\n请生成3个相关问题："}
        ]
        
        response = self.call_api(messages)
        
        if response:
            questions = [q.strip() for q in response.split('\n') if q.strip()]
            return questions[:3]
        
        return [
            "学校有哪些热门专业？",
            "如何报考这所学校？", 
            "学校的录取分数线如何？"
        ]

# 测试函数
def test_deepseek_client():
    """测试DeepSeek客户端"""
    client = DeepSeekClient()
    
    # 简单测试
    print("=== 测试DeepSeek API ===")
    test_messages = [
        {"role": "system", "content": "你是一个有用的助手"},
        {"role": "user", "content": "你好，请介绍一下黑龙江东方学院"}
    ]
    
    result = client.call_api(test_messages)
    if result:
        print(f"测试成功！")
        print(f"回答: {result[:200]}...")
    else:
        print("测试失败！")
    
    return result is not None

if __name__ == "__main__":
    test_deepseek_client()