# 东方智答 - 黑龙江东方学院智能问答系统

## 项目简介
"东方智答"是基于黑龙江东方学院官网数据的智能问答系统，通过爬取官网数据构建知识库，结合DeepSeek大模型提供智能问答服务。

## 技术栈
- **后端**: Python 3.8+, Flask
- **数据库**: MySQL 5.7+
- **AI模型**: DeepSeek API
- **爬虫**: BeautifulSoup4, Requests
- **前端**: HTML5, CSS3, JavaScript

## 项目结构
```
hlj_eu/
├── api/                # API接口
│   └── app.py         # Flask应用主文件
├── config/            # 配置文件
│   └── config.py      # 系统配置
├── crawler/           # 爬虫模块
│   └── spider.py      # 网站爬虫
├── database/          # 数据库相关
│   ├── db_manager.py  # 数据库管理
│   └── schema.sql     # 数据库结构
├── models/            # 模型层
│   ├── deepseek_client.py  # DeepSeek客户端
│   └── knowledge_builder.py # 知识库构建
├── web/               # Web前端
│   ├── templates/     # HTML模板
│   └── static/        # 静态资源
├── utils/             # 工具函数
├── .env               # 环境变量配置
├── requirements.txt   # 依赖包列表
└── README.md         # 项目说明
```

## 安装部署

### 1. 环境要求
- Python 3.8 或更高版本
- MySQL 5.7 或更高版本
- 稳定的网络连接

### 2. 安装依赖
```bash
cd hlj_eu
pip install -r requirements.txt
```

### 3. 配置数据库
1. 创建MySQL数据库：
```bash
mysql -u root -p
```

2. 执行数据库脚本：
```sql
source database/schema.sql
```

### 4. 配置环境变量
编辑 `.env` 文件，设置以下配置：
```
# MySQL配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=dongfang_zhida

# DeepSeek API配置
DEEPSEEK_API_KEY=your_api_key_here
```

### 5. 运行系统

#### 第一次运行前的准备：
1. 爬取网站数据：
```bash
python crawler/spider.py
```

2. 构建知识库：
```bash
python models/knowledge_builder.py
```

#### 启动Web服务：
```bash
python api/app.py
```

访问 http://localhost:5000 即可使用系统。

## 功能特性

### 1. 数据爬取
- 自动爬取学校官网数据
- 智能分类和存储
- 增量更新机制

### 2. 知识库构建
- 自动提取问答对
- 关键词提取
- 主题分析

### 3. 智能问答
- 基于知识库的精确回答
- DeepSeek大模型增强
- 上下文理解

### 4. Web界面
- 友好的聊天界面
- 实时响应
- 热门问题推荐
- 相关问题推荐

## API接口文档

### 1. 聊天接口
**POST** `/api/chat`

请求参数：
```json
{
    "question": "用户的问题"
}
```

响应：
```json
{
    "answer": "系统的回答",
    "source": "knowledge_base/deepseek/mixed",
    "confidence": 0.9,
    "response_time": 1200,
    "similar_questions": ["相关问题1", "相关问题2"],
    "references": [
        {
            "title": "参考标题",
            "url": "参考链接",
            "snippet": "内容摘要"
        }
    ]
}
```

### 2. 搜索接口
**GET** `/api/search?keyword=关键词&limit=10`

### 3. 统计信息
**GET** `/api/statistics`

### 4. 热门问题
**GET** `/api/hot_questions`

## 管理功能

### 启动爬虫任务
```bash
curl -X POST http://localhost:5000/api/admin/crawl \
  -H "Authorization: Bearer your-secret-key"
```

### 重建知识库
```bash
curl -X POST http://localhost:5000/api/admin/build_knowledge \
  -H "Authorization: Bearer your-secret-key"
```

## 注意事项

1. **API密钥安全**：请妥善保管DeepSeek API密钥，不要提交到版本控制系统。

2. **爬虫使用**：请遵守网站的robots.txt规则，合理设置爬取频率。

3. **数据库备份**：定期备份数据库，防止数据丢失。

4. **性能优化**：
   - 使用缓存机制减少数据库查询
   - 异步处理耗时任务
   - 定期清理过期数据

## 开发计划

- [ ] 添加用户认证系统
- [ ] 实现多轮对话功能
- [ ] 添加语音输入支持
- [ ] 移动端适配
- [ ] 添加数据可视化分析
- [ ] 实现自动问答质量评估

## 许可证
本项目仅供学习和研究使用。

## 联系方式
如有问题，请联系项目维护者。"# hlg_eu"  
