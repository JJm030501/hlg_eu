-- 创建招生数据专门的表

-- 招生计划表（按专业和省份）
CREATE TABLE IF NOT EXISTS admission_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL,                    -- 年份
    province VARCHAR(50) NOT NULL,        -- 省份
    major VARCHAR(100) NOT NULL,          -- 专业名称
    major_code VARCHAR(20),               -- 专业代码
    batch VARCHAR(50),                    -- 批次（本科一批、本科二批等）
    plan_count INT,                       -- 计划招生人数
    actual_count INT,                     -- 实际录取人数
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_year_province (year, province),
    INDEX idx_major (major)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 历年录取分数线表
CREATE TABLE IF NOT EXISTS admission_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL,                    -- 年份
    province VARCHAR(50) NOT NULL,        -- 省份
    major VARCHAR(100),                   -- 专业（如果为NULL表示学校整体分数线）
    category VARCHAR(20),                 -- 文理科（文科/理科/综合）
    batch VARCHAR(50),                    -- 批次
    min_score INT,                        -- 最低分
    avg_score INT,                        -- 平均分
    max_score INT,                        -- 最高分
    rank_position INT,                    -- 位次
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_year_province_category (year, province, category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 招生简章和政策表
CREATE TABLE IF NOT EXISTS admission_policies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    year INT NOT NULL,                    -- 年份
    title VARCHAR(255) NOT NULL,          -- 标题
    content TEXT,                         -- 内容
    policy_type VARCHAR(50),              -- 类型（招生简章/录取规则/特殊类型等）
    url VARCHAR(500),                     -- 原文链接
    publish_date DATE,                    -- 发布日期
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_year_type (year, policy_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 学校基本信息表（存储关键数据）
CREATE TABLE IF NOT EXISTS school_info (
    id INT AUTO_INCREMENT PRIMARY KEY,
    info_key VARCHAR(100) NOT NULL UNIQUE, -- 信息键（如：total_students, campus_area等）
    info_value TEXT,                       -- 信息值
    info_type VARCHAR(50),                 -- 信息类型（basic/contact/facility等）
    description VARCHAR(255),              -- 描述
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (info_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;