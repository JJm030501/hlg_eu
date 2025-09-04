// 主要的JavaScript功能

// 发送消息
async function sendMessage() {
    const input = document.getElementById('user-input');
    const question = input.value.trim();
    
    if (!question) {
        return;
    }
    
    // 添加用户消息到聊天界面
    addMessage(question, 'user');
    
    // 清空输入框
    input.value = '';
    
    // 显示加载状态
    addMessage('<div class="loading"></div>', 'system');
    
    try {
        // 发送API请求
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question: question })
        });
        
        // 移除加载状态
        removeLastMessage();
        
        if (response.ok) {
            const data = await response.json();
            
            // 构建回答内容
            let answerHtml = data.answer;
            
            // 添加参考链接
            if (data.references && data.references.length > 0) {
                answerHtml += '<div class="references"><h4>参考资料：</h4>';
                data.references.forEach(ref => {
                    answerHtml += `<div class="reference-item">
                        <a href="${ref.url}" target="_blank">${ref.title}</a>
                    </div>`;
                });
                answerHtml += '</div>';
            }
            
            // 添加相似问题
            if (data.similar_questions && data.similar_questions.length > 0) {
                answerHtml += '<div class="similar-questions"><h4>您可能还想问：</h4>';
                data.similar_questions.forEach(q => {
                    answerHtml += `<button class="similar-question-btn" onclick="quickQuestion('${q}')">${q}</button>`;
                });
                answerHtml += '</div>';
            }
            
            // 显示回答
            addMessage(answerHtml, 'system');
            
        } else {
            addMessage('抱歉，系统出现错误，请稍后重试。', 'system');
        }
    } catch (error) {
        removeLastMessage();
        console.error('Error:', error);
        addMessage('网络错误，请检查网络连接。', 'system');
    }
}

// 添加消息到聊天界面
function addMessage(content, type) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
    messagesContainer.appendChild(messageDiv);
    
    // 滚动到底部
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// 移除最后一条消息
function removeLastMessage() {
    const messagesContainer = document.getElementById('chat-messages');
    const lastMessage = messagesContainer.lastElementChild;
    if (lastMessage) {
        messagesContainer.removeChild(lastMessage);
    }
}

// 快速提问
function quickQuestion(question) {
    document.getElementById('user-input').value = question;
    sendMessage();
}

// 加载统计信息
async function loadStatistics() {
    try {
        const response = await fetch('/api/statistics');
        if (response.ok) {
            const data = await response.json();
            const statsDiv = document.getElementById('statistics');
            
            let html = `
                <p>总页面数：${data.total_pages || 0}</p>
                <p>知识条目：${data.knowledge_entries || 0}</p>
            `;
            
            if (data.recent_qa) {
                html += `
                    <p>本周问答：${data.recent_qa.total || 0}</p>
                    <p>平均响应：${Math.round(data.recent_qa.avg_response_time || 0)}ms</p>
                `;
            }
            
            statsDiv.innerHTML = html;
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// 加载热门问题
async function loadHotQuestions() {
    try {
        const response = await fetch('/api/hot_questions');
        if (response.ok) {
            const data = await response.json();
            const hotDiv = document.getElementById('hot-questions');
            
            if (data.length > 0) {
                let html = '<ul style="list-style: none; padding: 0;">';
                data.slice(0, 5).forEach(item => {
                    html += `<li style="margin-bottom: 8px;">
                        <a href="#" onclick="quickQuestion('${item.question}'); return false;" 
                           style="color: #667eea; text-decoration: none;">
                            ${item.question}
                        </a>
                        <span style="color: #999; font-size: 12px;">(${item.count}次)</span>
                    </li>`;
                });
                html += '</ul>';
                hotDiv.innerHTML = html;
            } else {
                hotDiv.innerHTML = '<p>暂无热门问题</p>';
            }
        }
    } catch (error) {
        console.error('Error loading hot questions:', error);
    }
}

// 回车发送消息
document.addEventListener('DOMContentLoaded', function() {
    const input = document.getElementById('user-input');
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // 加载初始数据
    loadStatistics();
    loadHotQuestions();
    
    // 定期刷新统计信息
    setInterval(loadStatistics, 60000); // 每分钟刷新
    setInterval(loadHotQuestions, 300000); // 每5分钟刷新
});