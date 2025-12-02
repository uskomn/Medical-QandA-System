<template>
  <div id="app">
    <el-container style="height: 100vh;">
      <!-- 头部 -->
      <el-header style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center;">
          <el-icon size="24" style="margin-right: 10px;">
            <Medical-Box />
          </el-icon>
          <h2 style="margin: 0;">重症伤员处置问答系统</h2>
        </div>
        <div>
          <el-tag 
            type="info" 
            size="small" 
            @click="showSystemInfo = true"
            style="cursor: pointer; transition: all 0.3s;"
            @mouseenter="handleTagHover"
            @mouseleave="handleTagLeave"
          >
            <el-icon><InfoFilled /></el-icon>
            系统须知
          </el-tag>
        </div>
      </el-header>

      <!-- 主体内容 -->
      <el-container>
        <!-- 左侧导航 -->
        <el-aside width="250px" style="background-color: #f5f7fa;">
          <el-menu
            :default-active="activeTab"
            @select="handleTabChange"
            style="border: none; height: 100%;"
          >
            <el-menu-item index="chat">
              <el-icon><ChatDotRound /></el-icon>
              <span>问答咨询</span>
            </el-menu-item>
            <el-menu-item index="knowledge">
              <el-icon><Connection /></el-icon>
              <span>知识图谱</span>
            </el-menu-item>
            <el-menu-item index="search">
              <el-icon><Search /></el-icon>
              <span>知识搜索</span>
            </el-menu-item>
          </el-menu>
        </el-aside>

        <!-- 主要内容区域 -->
        <el-main style="padding: 0;">
          <!-- 问答界面 -->
          <div v-if="activeTab === 'chat'" style="height: 100%;">
            <ChatInterface />
          </div>

          <!-- 知识图谱 -->
          <div v-if="activeTab === 'knowledge'" style="height: 100%;">
            <KnowledgeGraph />
          </div>

          <!-- 知识搜索 -->
          <div v-if="activeTab === 'search'" style="height: 100%;">
            <KnowledgeSearch />
          </div>
        </el-main>
      </el-container>

      <!-- 系统须知对话框 -->
      <el-dialog
        v-model="showSystemInfo"
        title="系统须知"
        width="60%"
        :before-close="handleClose"
        center
      >
        <div class="system-info-content">
          <el-alert
            title="重要提醒"
            type="warning"
            :closable="false"
            show-icon
            style="margin-bottom: 20px;"
          >
            本系统仅供学习和参考使用，不能替代专业医疗诊断和治疗。
          </el-alert>

          <div class="info-section">
            <h4>
              <el-icon><WarningFilled /></el-icon>
              使用限制
            </h4>
            <ul>
              <li>本系统提供的信息仅供参考，不构成医疗建议</li>
              <li>实际医疗决策应由合格的医疗专业人员做出</li>
              <li>紧急情况请立即联系专业医疗机构或拨打急救电话</li>
              <li>系统建议不能替代专业医疗诊断</li>
            </ul>
          </div>

          <div class="info-section">
            <h4>
              <el-icon><Guide /></el-icon>
              知识库来源
            </h4>
            <p>
              本系统知识库文档来源为中国政府网《需要紧急救治的急危重伤病标准及诊疗规范》，网页链接：
              <a href="https://www.gov.cn/gzdt/att/att/site1/20131125/1c6f6506c7f813fd8aa701.doc" target="_blank" rel="noopener noreforrer">
                https://www.gov.cn/gzdt/att/att/site1/20131125/1c6f6506c7f813fd8aa701.doc
              </a>
            </p>
          </div>

          <div class="info-section">
            <h4>
              <el-icon><InfoFilled /></el-icon>
              技术支持
            </h4>
            <p>
              如遇到技术问题或有改进建议，请及时反馈。本系统将持续优化和更新。
            </p>
          </div>
        </div>
      </el-dialog>
    </el-container>
  </div>
</template>

<script>
import { ref } from 'vue'
import ChatInterface from './views/ChatInterface.vue'
import KnowledgeGraph from './views/KnowledgeGraph.vue'
import KnowledgeSearch from './views/KnowledgeSearch.vue'

export default {
  name: 'App',
  components: {
    ChatInterface,
    KnowledgeGraph,
    KnowledgeSearch
  },
  setup() {
    const activeTab = ref('chat')
    const showSystemInfo = ref(false)

    const handleTabChange = (key) => {
      activeTab.value = key
    }

    const handleTagHover = (event) => {
      event.target.style.transform = 'scale(1.1)'
      event.target.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)'
    }

    const handleTagLeave = (event) => {
      event.target.style.transform = 'scale(1)'
      event.target.style.boxShadow = 'none'
    }

    const handleClose = (done) => {
      done()
    }

    return {
      activeTab,
      showSystemInfo,
      handleTabChange,
      handleTagHover,
      handleTagLeave,
      handleClose
    }
  }
}
</script>

<style>
#app {
  height: 100vh;
}

.el-menu-item {
  height: 60px;
  line-height: 60px;
}

.el-menu-item.is-active {
  background-color: #e6f7ff;
  border-right: 3px solid #409eff;
}

/* 系统须知对话框样式 */
.system-info-content {
  padding: 10px 0;
}

.info-section {
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}

.info-section:last-child {
  margin-bottom: 0;
}

.info-section h4 {
  margin: 0 0 12px 0;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.info-section ul {
  margin: 0;
  padding-left: 20px;
}

.info-section li {
  margin-bottom: 8px;
  color: #606266;
  line-height: 1.6;
}

.info-section li:last-child {
  margin-bottom: 0;
}

.info-section strong {
  color: #409eff;
  font-weight: 600;
}

.disclaimer {
  color: #606266;
  line-height: 1.8;
  margin: 0;
  text-align: justify;
  background: #fff3cd;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #ffeaa7;
}
</style>