-- 使用已存在的数据库
USE hlg_eu;

-- 爬取的网页数据表
CREATE TABLE IF NOT EXISTS crawled_pages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(255),
    content LONGTEXT,
    page_type VARCHAR(50),  -- 页面类型：news/notice/academic等
    category VARCHAR(100),  -- 分类
    crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_page_type (page_type),
    INDEX idx_category (category),
    FULLTEXT idx_content (title, content) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 知识库表
CREATE TABLE IF NOT EXISTS knowledge_base (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    source_url VARCHAR(500),
    category VARCHAR(100),
    keywords VARCHAR(255),
    confidence_score FLOAT DEFAULT 1.0,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    FULLTEXT idx_qa (question, answer, keywords) WITH PARSER ngram
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用户问答记录表
CREATE TABLE IF NOT EXISTS qa_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100),
    user_question TEXT NOT NULL,
    system_answer TEXT,
    answer_source VARCHAR(50),  -- deepseek/knowledge_base/mixed
    satisfaction_score INT,  -- 用户满意度评分 1-5
    response_time_ms INT,  -- 响应时间（毫秒）
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_create_time (create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    description VARCHAR(255),
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 爬虫任务记录表
CREATE TABLE IF NOT EXISTS crawl_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    start_url VARCHAR(500),
    status ENUM('pending', 'running', 'completed', 'failed') DEFAULT 'pending',
    total_pages INT DEFAULT 0,
    crawled_pages INT DEFAULT 0,
    start_time TIMESTAMP NULL,
    end_time TIMESTAMP NULL,
    error_message TEXT,
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入初始配置
INSERT INTO system_config (config_key, config_value, description) VALUES
('crawl_enabled', 'true', '是否启用自动爬取'),
('crawl_interval_hours', '24', '爬取间隔（小时）'),
('max_crawl_depth', '3', '最大爬取深度'),
('deepseek_model', 'deepseek-chat', '使用的DeepSeek模型'),
('answer_max_length', '500', '回答最大长度')
ON DUPLICATE KEY UPDATE config_value = VALUES(config_value);