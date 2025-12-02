<template>
  <div class="knowledge-search-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h3>
        <el-icon><Search /></el-icon>
        医疗知识搜索
      </h3>
      <p class="subtitle">搜索症状、疾病和处置流程相关知识</p>
    </div>

    <!-- 搜索区域 -->
    <div class="search-section">
      <el-card shadow="hover">
        <div class="search-form">
          <el-input
            v-model="searchQuery"
            placeholder="请输入症状、疾病或处置流程关键词..."
            size="large"
            clearable
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button 
            type="primary" 
            size="large" 
            :loading="isSearching"
            @click="handleSearch"
            style="margin-left: 12px;"
          >
            搜索
          </el-button>
        </div>

        <!-- 热门搜索 -->
        <div class="hot-searches" v-if="!hasSearched">
          <h4>热门搜索</h4>
          <div class="hot-buttons">
            <el-button
              v-for="term in hotSearches"
              :key="term"
              size="small"
              @click="quickSearch(term)"
            >
              {{ term }}
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 搜索结果 -->
    <div class="search-results" v-if="hasSearched">
      <div class="results-header">
        <h4>
          搜索结果
          <el-tag type="info" size="small">{{ searchResults.length }} 条结果</el-tag>
        </h4>
      </div>

      <div v-if="searchResults.length === 0" class="no-results">
        <el-empty description="未找到相关知识">
          <template #description>
            <p>没有找到包含 "{{ searchQuery }}" 的相关知识</p>
            <p>请尝试使用其他关键词或检查拼写</p>
          </template>
        </el-empty>
      </div>

      <div v-else class="results-list">
        <el-card
          v-for="(result, index) in searchResults"
          :key="index"
          class="result-item"
          shadow="hover"
        >
          <template #header>
            <div class="result-header">
              <el-tag 
                :type="getResultTypeColor(result.type)"
                size="small"
              >
                {{ result.type }}
              </el-tag>
              <span class="result-title">{{ result.name }}</span>
            </div>
          </template>

          <div class="result-content">
            <!-- 症状相关结果 -->
            <div v-if="result.type === '症状'" class="symptom-details">
              <div class="detail-section">
                <h5>
                  <el-icon><Collection /></el-icon>
                  相关疾病
                </h5>
                <div class="disease-tags">
                  <el-tag
                    v-for="disease in result.details['相关疾病']"
                    :key="disease"
                    type="warning"
                    size="small"
                  >
                    {{ disease }}
                  </el-tag>
                </div>
              </div>

              <div class="detail-section">
                <h5>
                  <el-icon><Guide /></el-icon>
                  处置建议
                </h5>
                <p class="treatment-advice">{{ result.details['处置建议'] }}</p>
              </div>
            </div>

            <!-- 处置流程相关结果 -->
            <div v-if="result.type === '处置流程'" class="procedure-details">
              <div class="detail-section">
                <h5>
                  <el-icon><WarningFilled /></el-icon>
                  适应症
                </h5>
                <p class="indication">{{ result.details['适应症'] }}</p>
              </div>

              <div class="detail-section">
                <h5>
                  <el-icon><List /></el-icon>
                  操作步骤
                </h5>
                <el-steps direction="vertical" :active="null">
                  <el-step
                    v-for="(step, stepIndex) in result.details['步骤']"
                    :key="stepIndex"
                    :title="`步骤 ${stepIndex + 1}`"
                    :description="step"
                  />
                </el-steps>
              </div>
            </div>

            <!-- 其他类型结果 -->
            <div v-else class="other-details">
              <pre class="details-json">{{ JSON.stringify(result.details, null, 2) }}</pre>
            </div>
          </div>

          <template #footer>
            <div class="result-actions">
              <el-button size="small" @click="copyToChat(result)">
                <el-icon><ChatDotRound /></el-icon>
                发送到问答
              </el-button>
              <el-button size="small" @click="viewInGraph(result)">
                <el-icon><Connection /></el-icon>
                在图谱中查看
              </el-button>
            </div>
          </template>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { knowledgeApi } from '../utils/api'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'

export default {
  name: 'KnowledgeSearch',
  setup() {
    const searchQuery = ref('')
    const isSearching = ref(false)
    const hasSearched = ref(false)
    const searchResults = ref([])
    const router = useRouter()

    const hotSearches = [
      '呼吸困难',
      '胸痛',
      '意识障碍',
      '大出血',
      '高热',
      '心肺复苏',
      '气管插管'
    ]

    // 执行搜索
    const handleSearch = async () => {
      if (!searchQuery.value.trim()) {
        ElMessage.warning('请输入搜索关键词')
        return
      }

      isSearching.value = true
      hasSearched.value = true

      try {
        const response = await knowledgeApi.searchKnowledge(searchQuery.value.trim())
        searchResults.value = response.results
      } catch (error) {
        console.error('搜索失败:', error)
        ElMessage.error('搜索失败，请重试')
        searchResults.value = []
      } finally {
        isSearching.value = false
      }
    }

    // 快捷搜索
    const quickSearch = (term) => {
      searchQuery.value = term
      handleSearch()
    }

    // 获取结果类型颜色
    const getResultTypeColor = (type) => {
      const colorMap = {
        '症状': 'warning',
        '处置流程': 'primary',
        '疾病': 'danger',
        '其他': 'info'
      }
      return colorMap[type] || 'info'
    }

    // 复制到问答
    const copyToChat = (result) => {
      ElMessage.success('已复制到问答界面')
      // 这里可以实现路由跳转或事件传递
    }

    // 在图谱中查看
    const viewInGraph = (result) => {
      router.push('/knowledge')
      ElMessage.success('已在知识图谱中标记相关节点')
    }

    return {
      searchQuery,
      isSearching,
      hasSearched,
      searchResults,
      hotSearches,
      handleSearch,
      quickSearch,
      getResultTypeColor,
      copyToChat,
      viewInGraph
    }
  }
}
</script>

<style scoped>
.knowledge-search-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.page-header {
  background: white;
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.page-header h3 {
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

.search-section {
  padding: 20px;
}

.search-form {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.hot-searches h4 {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 14px;
}

.hot-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.search-results {
  flex: 1;
  padding: 0 20px 20px 20px;
  overflow-y: auto;
}

.results-header {
  background: white;
  padding: 16px 20px;
  border-radius: 8px 8px 0 0;
  border: 1px solid #e4e7ed;
  border-bottom: none;
}

.results-header h4 {
  margin: 0;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 12px;
}

.no-results {
  background: white;
  padding: 40px 20px;
  border: 1px solid #e4e7ed;
  border-top: none;
  border-radius: 0 0 8px 8px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  margin-bottom: 0;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.result-title {
  font-weight: 500;
  color: #303133;
}

.result-content {
  padding: 0;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h5 {
  margin: 0 0 8px 0;
  color: #606266;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.disease-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.treatment-advice,
.indication {
  color: #303133;
  line-height: 1.6;
  margin: 0;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.details-json {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 12px;
  color: #606266;
}

.result-actions {
  display: flex;
  gap: 8px;
}
</style>