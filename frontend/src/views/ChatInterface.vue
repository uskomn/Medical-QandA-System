<template>
  <div class="chat-container">
    <!-- 聊天标题 -->
    <div class="chat-header">
      <h3>
        <el-icon><ChatDotRound /></el-icon>
        专业问答咨询
      </h3>
      <p class="subtitle">输入症状或问题，获取专业处置建议</p>
    </div>

    <!-- 聊天消息区域 -->
    <div class="chat-messages" ref="messagesContainer">
      <div
        v-for="(message, index) in messages"
        :key="index"
        :class="['message', message.type]"
      >
        <div class="message-content">
          <div class="message-avatar">
            <el-avatar :size="40" :icon="message.type === 'user' ? User : Service" />
          </div>
          <div class="message-text">
            <div class="message-bubble" :class="message.type">
              <p v-html="formatMessage(message.content)"></p>
              <span class="message-time">{{ formatTime(message.timestamp) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="isLoading" class="message bot">
        <div class="message-content">
          <div class="message-avatar">
            <el-avatar :size="40" icon="Service" />
          </div>
          <div class="message-text">
            <div class="message-bubble bot loading">
              <el-icon class="loading-icon"><Loading /></el-icon>
              <span>正在思考...</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="chat-input">
      <div class="input-container">
        <el-input
          v-model="currentMessage"
          type="textarea"
          :rows="3"
          placeholder="请描述症状或提问，例如：患者出现呼吸困难怎么办？"
          :disabled="isLoading"
          @keydown.enter.exact="handleSend"
          @keydown.enter.ctrl="handleSend"
        />
        <div class="input-actions">
          <el-button
            type="primary"
            :loading="isLoading"
            :disabled="!currentMessage.trim() || isLoading"
            @click="handleSend"
          >
            <el-icon><Promotion /></el-icon>
            发送
          </el-button>
          <el-button @click="clearChat" :disabled="isLoading">
            <el-icon><Delete /></el-icon>
            清空
          </el-button>
        </div>
      </div>
    </div>

    <!-- 快捷问题 -->
    <div class="quick-questions">
      <p class="quick-title">常见问题：</p>
      <div class="quick-buttons">
        <el-button
          v-for="question in quickQuestions"
          :key="question"
          size="small"
          @click="sendQuickQuestion(question)"
          :disabled="isLoading"
        >
          {{ question }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, nextTick, onMounted } from 'vue'
import { chatApi } from '../utils/api'
import { ElMessage } from 'element-plus'

export default {
  name: 'ChatInterface',
  setup() {
    const messages = ref([])
    const currentMessage = ref('')
    const isLoading = ref(false)
    const messagesContainer = ref(null)

    const quickQuestions = [
      '患者出现呼吸困难怎么办？',
      '胸痛的处置流程是什么？',
      '意识障碍的评估方法？',
      '大出血的紧急处理？',
      '心肺复苏的操作步骤？'
    ]

    // 发送消息
    const sendMessage = async () => {
      const message = currentMessage.value.trim()
      if (!message || isLoading.value) return

      // 添加用户消息
      messages.value.push({
        type: 'user',
        content: message,
        timestamp: new Date().toISOString()
      })

      currentMessage.value = ''
      isLoading.value = true

      try {
        // 调用API
        const response = await chatApi.sendMessage(message)
        
        // 添加机器人回复
        messages.value.push({
          type: 'bot',
          content: response.response,
          timestamp: response.timestamp
        })
      } catch (error) {
        console.error('发送消息失败:', error)
        ElMessage.error('发送消息失败，请重试')
        messages.value.push({
          type: 'bot',
          content: '抱歉，服务暂时不可用，请稍后重试。',
          timestamp: new Date().toISOString()
        })
      } finally {
        isLoading.value = false
        scrollToBottom()
      }
    }

    // 处理发送
    const handleSend = (event) => {
      if (event && event.type === 'keydown') {
        if (event.key === 'Enter' && !event.ctrlKey) {
          event.preventDefault()
          return
        }
      }
      sendMessage()
    }

    // 发送快捷问题
    const sendQuickQuestion = (question) => {
      currentMessage.value = question
      sendMessage()
    }

    // 清空聊天
    const clearChat = () => {
      messages.value = []
      ElMessage.success('聊天记录已清空')
    }

    // 格式化消息
    const formatMessage = (content) => {
      return content.replace(/\n/g, '<br>')
    }

    // 格式化时间
    const formatTime = (timestamp) => {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('zh-CN', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    }

    // 滚动到底部
    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }

    // 添加欢迎消息
    const addWelcomeMessage = () => {
      messages.value.push({
        type: 'bot',
        content: '您好！我是重症伤员处置专业助手。\n\n我可以帮助您：\n• 分析症状和病情\n• 提供处置建议\n• 指导急救流程\n\n请描述您遇到的具体情况，我会尽力提供帮助。',
        timestamp: new Date().toISOString()
      })
    }

    onMounted(() => {
      addWelcomeMessage()
    })

    return {
      messages,
      currentMessage,
      isLoading,
      messagesContainer,
      quickQuestions,
      handleSend,
      sendQuickQuestion,
      clearChat,
      formatMessage,
      formatTime
    }
  }
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
}

.chat-header {
  background: white;
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.chat-header h3 {
  margin: 0;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.subtitle {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7fa;
}

.message {
  margin-bottom: 20px;
}

.message-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.message.user .message-content {
  flex-direction: row-reverse;
}

.message-text {
  flex: 1;
  max-width: 70%;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
  word-wrap: break-word;
}

.message-bubble.user {
  background: #409eff;
  color: white;
  margin-left: 20px;
}

.message-bubble.bot {
  background: white;
  color: #303133;
  border: 1px solid #e4e7ed;
  margin-right: 20px;
}

.message-bubble.loading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-style: italic;
}

.loading-icon {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.message-time {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 4px;
  display: block;
}

.chat-input {
  background: white;
  padding: 20px;
  border-top: 1px solid #e4e7ed;
}

.input-container {
  max-width: 100%;
}

.input-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
  justify-content: flex-end;
}

.quick-questions {
  background: white;
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
}

.quick-title {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 14px;
  font-weight: 500;
}

.quick-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-buttons .el-button {
  font-size: 12px;
}
</style>