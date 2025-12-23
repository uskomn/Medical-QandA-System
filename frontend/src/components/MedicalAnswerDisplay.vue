<template>
  <div class="medical-qa-display">
    <!-- 核心答案区域 -->
    <div class="answer-section core-answer">
      <div class="section-header">
        <div class="header-icon">
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
          </svg>
        </div>
        <h2 class="section-title">核心答案</h2>
      </div>
      <div class="section-content" v-html="formatCoreAnswer(coreAnswer)"></div>
    </div>

    <!-- 详细说明区域 -->
    <div class="answer-section detailed-info">
      <div class="section-header">
        <div class="header-icon info">
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
          </svg>
        </div>
        <h2 class="section-title">详细说明</h2>
      </div>
      <div class="section-content">
        <p class="intro-text">{{ getIntroText() }}</p>
        
        <!-- 紧急治疗 -->
        <div class="info-category" v-if="emergencyTreatment.length > 0">
          <div class="category-header">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c1.93 0 3.5 1.57 3.5 3.5S13.93 13 12 13s-3.5-1.57-3.5-3.5S10.07 6 12 6zm7 13H5v-.23c0-.62.28-1.2.76-1.58C7.47 15.82 9.64 15 12 15s4.53.82 6.24 2.19c.48.38.76.97.76 1.58V19z"/>
            </svg>
            <h3>紧急治疗</h3>
          </div>
          <ul class="info-list">
            <li v-for="(item, index) in emergencyTreatment" :key="'emergency-' + index">
              <span class="bullet"></span>
              <span v-html="formatText(item)"></span>
            </li>
          </ul>
        </div>

        <!-- 持续监测 -->
        <div class="info-category" v-if="monitoring.length > 0">
          <div class="category-header">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z"/>
            </svg>
            <h3>持续监测</h3>
          </div>
          <ul class="info-list">
            <li v-for="(item, index) in monitoring" :key="'monitor-' + index">
              <span class="bullet"></span>
              <span v-html="formatText(item)"></span>
            </li>
          </ul>
        </div>

        <!-- 必要检查 -->
        <div class="info-category" v-if="examinations.length > 0">
          <div class="category-header">
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-4 6h-4v1H9v2h2v1h-2v2h4v-2h-2v-1h2v-2h-2V9h4v2h-2v1z"/>
            </svg>
            <h3>必要检查</h3>
          </div>
          <ul class="info-list">
            <li v-for="(item, index) in examinations" :key="'exam-' + index">
              <span class="bullet"></span>
              <span v-html="formatText(item)"></span>
            </li>
          </ul>
        </div>
      </div>
    </div>

    <!-- 重要提示区域 -->
    <div class="answer-section important-notes">
      <div class="section-header">
        <div class="header-icon warning">
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
          </svg>
        </div>
        <h2 class="section-title">重要提示</h2>
      </div>
      <div class="section-content">
        <ul class="notes-list">
          <li v-for="(note, index) in importantNotes" :key="'note-' + index">
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            <span v-html="formatText(note)"></span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  // 原始答案数据
  answerData: {
    type: Object,
    default: () => ({
      coreAnswer: '',
      detailedInfo: '',
      importantNotes: ''
    })
  }
})

// 解析核心答案
const coreAnswer = computed(() => {
  return props.answerData.coreAnswer || 
    '根据知识图谱信息，对于出现呼吸困难的患者，应立即进行吸氧、建立静脉通路等紧急治疗，并同步监测血氧饱和度、心率等关键指标，同时安排血气分析、血糖、心电图等必要检查。'
})

// 解析详细说明中的各个部分
const getIntroText = () => {
  const detailed = props.answerData.detailedInfo || 
    '基于提供的知识图谱，针对"呼吸困难"这一急症，应采取以下措施：'
  return detailed.split('\n')[0]
}

const emergencyTreatment = computed(() => {
  const text = props.answerData.detailedInfo || 
    '根据"呼吸困难[需要治疗] -> 吸氧"的关系，应尽快为患者进行吸氧。根据"呼吸困难[需要治疗] -> 建立静脉通路"的关系，应立即为患者建立静脉通路。在极端紧急情况下，根据"呼吸困难[需要治疗] -> 环甲膜穿刺"的关系，可能需要立即进行环甲膜穿刺。'
  
  return extractItemsFromText(text, ['吸氧', '静脉通路', '环甲膜穿刺'])
})

const monitoring = computed(() => {
  const text = props.answerData.detailedInfo || 
    '根据"呼吸困难[监测指标] -> 血氧饱和度"和"呼吸困难[监测指标] -> 心率"的关系，需要持续监测患者的血氧饱和度（正常范围95%-100%）和心率（正常范围60-100次/分）。'
  
  return extractItemsFromText(text, ['血氧饱和度', '心率'])
})

const examinations = computed(() => {
  const text = props.answerData.detailedInfo || 
    '为了评估病因，根据"呼吸困难[需要检查] -> 血气分析"、"呼吸困难[需要检查] -> 血糖"以及"呼吸困难[需要检查] -> 心电图"的关系，需要为患者安排血气分析（用于呼吸功能评估）、血糖（用于血糖水平检测）和心电图（用于心律失常诊断）检查。'
  
  return extractItemsFromText(text, ['血气分析', '血糖', '心电图'])
})

const importantNotes = computed(() => {
  const notes = props.answerData.importantNotes || 
    '呼吸困难是急症，所有操作均需在专业医疗人员指导下进行。环甲膜穿刺是一项紧急手术操作，仅在气道严重梗阻、其他通气方式无效时由有经验的医生执行。图谱中暂无关于吸氧具体流量、建立静脉通路具体位置、检查具体时机等属性信息，临床操作需遵循具体医疗规范和患者实际情况。'
  
  return notes.split(/(?=呼吸困难是|环甲膜穿刺是一项|图谱中暂无)/)
    .filter(item => item.trim().length > 0)
})

// 从文本中提取特定项目
function extractItemsFromText(text, keywords) {
  const items = []
  keywords.forEach(keyword => {
    if (text.includes(keyword)) {
      // 尝试找到包含该关键词的完整句子
      const sentences = text.split(/[。！？]/)
      sentences.forEach(sentence => {
        if (sentence.includes(keyword) && sentence.trim().length > 10) {
          items.push(sentence.trim() + '。')
        }
      })
    }
  })
  return items
}

// 格式化核心答案
function formatCoreAnswer(text) {
  // 清理特殊符号并格式化
  let formatted = cleanText(text)
  // 高亮关键操作
  formatted = formatted
    .replace(/(吸氧|静脉通路|环甲膜穿刺|血氧饱和度|心率|血气分析|血糖|心电图)/g, 
      '<span class="highlight">$1</span>')
  return `<p>${formatted}</p>`
}

// 清理文本中的特殊符号
function cleanText(text) {
  if (!text) return ''
  
  return text
    .replace(/【/g, '')
    .replace(/】/g, '')
    .replace(/\*/g, '')
    .replace(/•/g, '')
    .replace(/·/g, '')
    .replace(/□/g, '')
    .replace(/■/g, '')
    .replace(/○/g, '')
    .replace(/●/g, '')
    .replace(/∶/g, ':')
    .replace(/：/g, ':')
    .replace(/；/g, ';')
    .replace(/，/g, ',')
    .replace(/。/g, '.')
    .replace(/、/g, ', ')
    .replace(/"/g, '"')
    .replace(/"/g, '"')
    .replace(/'/g, "'")
    .replace(/'/g, "'")
    .replace(/\s+/g, ' ')
    .trim()
}

// 格式化普通文本
function formatText(text) {
  if (!text) return ''
  
  let formatted = cleanText(text)
  
  // 格式化关系描述
  formatted = formatted
    .replace(/\[需要治疗\]/g, '<span class="tag treatment">需要治疗</span>')
    .replace(/\[监测指标\]/g, '<span class="tag monitoring">监测指标</span>')
    .replace(/\[需要检查\]/g, '<span class="tag examination">需要检查</span>')
  
  // 高亮关键术语
  const medicalTerms = [
    '吸氧', '静脉通路', '环甲膜穿刺',
    '血氧饱和度', '心率', '心律失常',
    '血气分析', '血糖', '心电图',
    '呼吸功能', '气道梗阻', '专业医疗人员'
  ]
  
  medicalTerms.forEach(term => {
    const regex = new RegExp(`(${term})`, 'g')
    formatted = formatted.replace(regex, '<span class="highlight">$1</span>')
  })
  
  // 格式化正常范围
  formatted = formatted
    .replace(/（([^）]+)）/g, ' <span class="range">($1)</span>')
    .replace(/\(([^)]+)\)/g, ' <span class="range">($1)</span>')
  
  return formatted
}
</script>

<style scoped>
.medical-qa-display {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: #2c3e50;
  line-height: 1.8;
}

/* 通用区块样式 */
.answer-section {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #e8e8e8;
  transition: box-shadow 0.3s ease;
}

.answer-section:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
}

/* 区块头部 */
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f0f0f0;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-icon.info {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.header-icon.warning {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.section-content {
  color: #4a4a6a;
  font-size: 15px;
}

/* 核心答案特殊样式 */
.core-answer {
  background: linear-gradient(135deg, #667eea08 0%, #764ba208 100%);
  border-left: 4px solid #667eea;
}

.core-answer .section-content {
  font-size: 16px;
  line-height: 1.9;
  color: #2d3748;
  font-weight: 500;
}

/* 介绍文字 */
.intro-text {
  color: #718096;
  font-style: italic;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: #f7fafc;
  border-radius: 8px;
  border-left: 3px solid #667eea;
}

/* 信息分类 */
.info-category {
  margin-bottom: 20px;
  padding: 16px;
  background: #fafbfc;
  border-radius: 10px;
  border: 1px solid #edf2f7;
}

.info-category:last-child {
  margin-bottom: 0;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  color: #4a5568;
}

.category-header h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  color: #2d3748;
}

.category-header svg {
  color: #667eea;
}

/* 列表样式 */
.info-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.info-list li {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed #e2e8f0;
}

.info-list li:last-child {
  border-bottom: none;
}

.info-list .bullet {
  width: 8px;
  height: 8px;
  min-width: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  margin-top: 6px;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.4);
}

/* 重要提示样式 */
.important-notes {
  background: linear-gradient(135deg, #fff5f5 0%, #fff0f0 100%);
  border-left: 4px solid #f5576c;
}

.important-notes .section-header {
  border-bottom-color: #fed7d7;
}

.important-notes .section-title {
  color: #c53030;
}

.notes-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.notes-list li {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  color: #c53030;
  font-weight: 500;
}

.notes-list li:first-child {
  padding-top: 0;
}

.notes-list li:last-child {
  padding-bottom: 0;
}

.notes-list svg {
  color: #f5576c;
  margin-top: 2px;
  flex-shrink: 0;
}

/* 高亮标签 */
:deep(.tag) {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  margin: 0 4px;
}

:deep(.tag.treatment) {
  background: linear-gradient(135deg, #fed7d7 0%, #feb2b2 100%);
  color: #c53030;
}

:deep(.tag.monitoring) {
  background: linear-gradient(135deg, #c6f6d5 0%, #9ae6b4 100%);
  color: #276749;
}

:deep(.tag.examination) {
  background: linear-gradient(135deg, #bee3f8 0%, #90cdf4 100%);
  color: #2b6cb0;
}

/* 高亮医学术语 */
:deep(.highlight) {
  background: linear-gradient(120deg, #fef3c7 0%, #fde68a 100%);
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  color: #92400e;
}

/* 正常范围样式 */
:deep(.range) {
  color: #059669;
  font-weight: 500;
  font-size: 13px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .medical-qa-display {
    padding: 16px;
  }
  
  .answer-section {
    padding: 16px;
  }
  
  .section-title {
    font-size: 16px;
  }
  
  .core-answer .section-content {
    font-size: 15px;
  }
  
  .info-category {
    padding: 12px;
  }
}

/* 动画效果 */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.answer-section {
  animation: fadeInUp 0.5s ease-out forwards;
}

.answer-section:nth-child(1) {
  animation-delay: 0.1s;
}

.answer-section:nth-child(2) {
  animation-delay: 0.2s;
}

.answer-section:nth-child(3) {
  animation-delay: 0.3s;
}
</style>
