<template>
  <div class="knowledge-graph-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h3>
        <el-icon><Connection /></el-icon>
        医疗知识图谱
      </h3>
      <p class="subtitle">可视化展示重症伤员处置相关的知识关联</p>
    </div>

    <!-- 控制面板 -->
    <div class="control-panel">
      <el-row :gutter="16" align="middle">
        <el-col :span="8">
          <el-button @click="resetView" type="primary" plain>
            <el-icon><Refresh /></el-icon>
            重置视图
          </el-button>
          <el-button @click="toggleLabels">
            <el-icon><View /></el-icon>
            {{ showLabels ? '隐藏标签' : '显示标签' }}
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-select v-model="selectedNodeType" placeholder="筛选节点类型" clearable>
            <el-option label="全部" value="" />
            <el-option label="疾病" value="disease" />
            <el-option label="治疗" value="treatment" />
            <el-option label="检查" value="examination" />
            <el-option label="药物" value="medication" />
            <el-option label="生命体征" value="vital_signs" />
            <el-option label="并发症" value="complication" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <div class="graph-info">
            <el-tag :type="databaseStatusType" size="small">
              {{ databaseStatus }}
            </el-tag>
          </div>
        </el-col>
        <el-col :span="5">
          <div class="graph-info">
            <el-tag type="info" size="small">
              节点: {{ filteredNodes.length }} | 连接: {{ filteredLinks.length }}
            </el-tag>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- 图谱容器 -->
    <div class="graph-container" ref="graphContainer">
      <div v-if="isLoading" class="loading">
        <el-icon class="loading-icon"><Loading /></el-icon>
        <span>正在加载知识图谱...</span>
      </div>
      <svg v-show="!isLoading" ref="svg" :width="svgWidth" :height="svgHeight"></svg>
    </div>

    <!-- 节点详情面板 - Neo4j 风格 -->
    <el-drawer
      v-model="showDetails"
      title="Node properties"
      direction="rtl"
      size="400px"
      :show-close="true"
    >
      <div v-if="selectedNode" class="neo4j-properties-panel">
        <!-- 节点标题 -->
        <div class="neo4j-node-title">
          <div class="node-icon-circle" :style="{ backgroundColor: nodeColors[selectedNode.group] || '#999' }">
          </div>
          <div class="node-name">{{ selectedNode.label }}</div>
        </div>

        <!-- 节点标签 -->
        <div class="neo4j-node-labels">
          <el-tag
            :style="{
              backgroundColor: nodeColors[selectedNode.group] || '#999',
              border: 'none',
              color: '#fff',
              fontWeight: '500',
              fontSize: '13px',
              padding: '6px 12px'
            }"
            size="default"
          >
            {{ getNodeTypeText(selectedNode.group) }}
          </el-tag>
        </div>

        <!-- 节点属性列表 -->
        <div class="neo4j-properties-list" v-if="selectedNode.properties">
          <div
            class="neo4j-property-item"
            v-for="(value, key) in getFilteredProperties(selectedNode.properties)"
            :key="key"
          >
            <div class="property-row">
              <span class="property-label">{{ formatPropertyKey(key) }}</span>
              <span class="property-value">{{ value }}</span>
            </div>
          </div>
        </div>

      </div>
    </el-drawer>

    <!-- 图例 -->
    <div class="legend">
      <h5>图例</h5>
      <div class="legend-items">
        <div class="legend-item" v-for="(color, type) in nodeColors" :key="type">
          <div class="legend-color" :style="{ backgroundColor: color }"></div>
          <span>{{ getNodeTypeText(type) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { knowledgeApi, knowledgeTestApi } from '../utils/api'
import { ElMessage } from 'element-plus'
import * as d3 from 'd3'

export default {
  name: 'KnowledgeGraph',
  setup() {
    const graphContainer = ref(null)
    const svg = ref(null)
    const isLoading = ref(true)
    const showLabels = ref(true)
    const showDetails = ref(false)
    const selectedNode = ref(null)
    const selectedNodeType = ref('')
    const isRefreshing = ref(false)

    const svgWidth = ref(800)
    const svgHeight = ref(600)

    // 数据库状态
    const databaseStatus = ref('检查中...')
    const databaseStatusType = ref('info')

    const graphData = ref({ nodes: [], links: [] })

    // 节点颜色映射
    const nodeColors = {
      disease: '#e74c3c',
      treatment: '#3498db',
      examination: '#f39c12',
      medication: '#9b59b6',
      vital_signs: '#1abc9c',
      complication: '#e67e22',
      other: '#95a5a6'
    }

    // 计算过滤后的节点和连接
    const filteredNodes = computed(() => {
      if (!selectedNodeType.value) return graphData.value.nodes
      return graphData.value.nodes.filter(node => node.group === selectedNodeType.value)
    })

    const filteredLinks = computed(() => {
      if (!selectedNodeType.value) {
        return graphData.value.links
      }

      const nodeIds = new Set(filteredNodes.value.map(node => node.id))
      return graphData.value.links.filter(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source
        const targetId = typeof link.target === 'object' ? link.target.id : link.target
        return nodeIds.has(sourceId) || nodeIds.has(targetId)
      })
    })

    // 检查数据库状态
    const checkDatabaseStatus = async () => {
      try {
        const healthResponse = await knowledgeTestApi.testConnection()
        const healthData = await healthResponse.json()
        if (healthData.database && healthData.message.includes('正常')) {
          databaseStatus.value = 'Neo4j数据库状态正常'
          databaseStatusType.value = 'success'
        } else {
          databaseStatus.value = 'Neo4j数据库状态正常'
          databaseStatusType.value = 'warning'
        }
      } catch (error) {
        databaseStatus.value = '数据库连接失败'
        databaseStatusType.value = 'danger'
      }
    }

    // 初始化图谱
    const initGraph = async () => {
      try {
        isLoading.value = true
        await checkDatabaseStatus()

        const response = await knowledgeApi.getKnowledgeGraph()
        graphData.value = response

        await nextTick()
        renderGraph()
      } catch (error) {
        console.error('加载知识图谱失败:', error)
        ElMessage.error('加载知识图谱失败')
      } finally {
        isLoading.value = false
      }
    }

    // 渲染图谱 - Neo4j 风格
    const renderGraph = () => {
      if (!svg.value || !graphContainer.value) return

      const containerRect = graphContainer.value.getBoundingClientRect()
      svgWidth.value = containerRect.width - 20
      svgHeight.value = containerRect.height - 20

      d3.select(svg.value).selectAll('*').remove()

      const svgElement = d3.select(svg.value)
      const g = svgElement.append('g')

      const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          g.attr('transform', event.transform)
        })

      svgElement.call(zoom)

      const simulation = d3.forceSimulation(filteredNodes.value)
        .force('link', d3.forceLink(filteredLinks.value).id(d => d.id).distance(120))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(svgWidth.value / 2, svgHeight.value / 2))
        .force('collision', d3.forceCollide().radius(30))

      // 绘制连接线 - Neo4j 风格
      const links = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(filteredLinks.value)
        .enter().append('line')
        .attr('stroke', '#a5abb3')
        .attr('stroke-opacity', 0.5)
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
          d3.select(this)
            .attr('stroke', '#4c8eda')
            .attr('stroke-width', 3)
            .attr('stroke-opacity', 0.8)

          g.selectAll('.link-label').style('opacity', link => link === d ? 1 : 0.2)
        })
        .on('mouseout', function(event, d) {
          d3.select(this)
            .attr('stroke', '#a5abb3')
            .attr('stroke-width', 2)
            .attr('stroke-opacity', 0.5)

          g.selectAll('.link-label').style('opacity', 0.85)
        })

      // 创建节点组
      const nodeGroup = g.append('g')
        .selectAll('g')
        .data(filteredNodes.value)
        .enter().append('g')
        .attr('class', 'node-group')
        .style('cursor', 'pointer')
        .call(d3.drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended)
        )

      // 添加阴影
      nodeGroup.append('circle')
        .attr('r', 22)
        .attr('fill', '#000')
        .attr('opacity', 0.15)
        .attr('cx', 2)
        .attr('cy', 2)

      // 主圆形节点
      nodeGroup.append('circle')
        .attr('r', 20)
        .attr('fill', d => nodeColors[d.group] || '#999')
        .attr('stroke', '#fff')
        .attr('stroke-width', 3)
        .on('click', (event, d) => {
          selectedNode.value = d
          showDetails.value = true
        })
        .on('mouseover', function(event, d) {
          d3.select(this.parentNode).select('circle:first-child')
            .transition().duration(200)
            .attr('r', 26)
            .attr('opacity', 0.25)
          d3.select(this)
            .transition().duration(200)
            .attr('r', 24)
        })
        .on('mouseout', function(event, d) {
          d3.select(this.parentNode).select('circle:first-child')
            .transition().duration(200)
            .attr('r', 22)
            .attr('opacity', 0.15)
          d3.select(this)
            .transition().duration(200)
            .attr('r', 20)
        })

      // 在节点中心添加标签（带省略号处理）
      nodeGroup.append('text')
        .attr('class', 'node-center-label')
        .text(d => {
          const label = d.label || ''
          // 根据节点大小限制字符数（圆形半径20，大约能容纳3-4个中文字符）
          return label.length > 4 ? label.substring(0, 4) + '...' : label
        })
        .attr('font-size', 11)
        .attr('font-weight', '500')
        .attr('fill', '#fff')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-family', "'Segoe UI', 'Microsoft YaHei', sans-serif")
        .style('pointer-events', 'none')
        .style('display', showLabels.value ? 'block' : 'none')

      // 添加关系标签 - Neo4j 风格（在连线上方显示）
      const linkLabelGroups = g.append('g')
        .attr('class', 'link-labels')
        .selectAll('.link-label-group')
        .data(filteredLinks.value)
        .enter().append('g')
        .attr('class', 'link-label-group')

      // 添加文字
      linkLabelGroups.append('text')
        .attr('class', 'link-label-text')
        .text(d => d.relationshipType || '')
        .attr('font-size', 9)
        .attr('fill', '#717171')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .attr('font-family', "'Segoe UI', 'Microsoft YaHei', sans-serif")
        .style('pointer-events', 'none')
        .style('font-weight', '400')

      // 更新位置
      simulation.on('tick', () => {
        links
          .attr('x1', d => (typeof d.source === 'object' ? d.source.x : 0) || 0)
          .attr('y1', d => (typeof d.source === 'object' ? d.source.y : 0) || 0)
          .attr('x2', d => (typeof d.target === 'object' ? d.target.x : 0) || 0)
          .attr('y2', d => (typeof d.target === 'object' ? d.target.y : 0) || 0)

        nodeGroup.attr('transform', d => `translate(${d.x || 0}, ${d.y || 0})`)

        // 更新关系标签位置
        linkLabelGroups.each(function(d) {
          const sx = (typeof d.source === 'object' ? d.source.x : 0) || 0
          const sy = (typeof d.source === 'object' ? d.source.y : 0) || 0
          const tx = (typeof d.target === 'object' ? d.target.x : 0) || 0
          const ty = (typeof d.target === 'object' ? d.target.y : 0) || 0

          const mx = (sx + tx) / 2
          const my = (sy + ty) / 2

          // 计算连线的角度
          const dx = tx - sx
          const dy = ty - sy
          const angle = Math.atan2(dy, dx) * 180 / Math.PI

          // 更新文字位置和旋转
          const text = d3.select(this).select('.link-label-text')
          text
            .attr('x', mx)
            .attr('y', my - 8)  // 向上偏移一点
            .attr('transform', `rotate(${angle}, ${mx}, ${my - 8})`)
        })
      })

      // 拖拽函数
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      }

      function dragged(event, d) {
        d.fx = event.x
        d.fy = event.y
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
      }
    }

    // 重置视图
    const resetView = () => {
      const svgElement = d3.select(svg.value)
      svgElement.transition().duration(750).call(
        d3.zoom().transform,
        d3.zoomIdentity
      )
    }

    // 切换标签显示
    const toggleLabels = () => {
      showLabels.value = !showLabels.value
      const labels = d3.select(svg.value).selectAll('.node-center-label')
      labels.style('display', showLabels.value ? 'block' : 'none')
    }

    // 获取节点类型文本
    const getNodeTypeText = (type) => {
      const textMap = {
        disease: '疾病',
        treatment: '治疗',
        examination: '检查',
        medication: '药物',
        vital_signs: '生命体征',
        complication: '并发症',
        other: '其他'
      }
      return textMap[type] || type
    }

    // 过滤属性 - 移除不需要显示的字段
    const getFilteredProperties = (properties) => {
      if (!properties) return {}
      const filtered = {}
      Object.keys(properties).forEach(key => {
        if (properties[key] &&
            key !== 'id' &&
            key !== 'elementId' &&
            key !== 'type' &&
            key !== 'label') {
          filtered[key] = properties[key]
        }
      })
      return filtered
    }

    // 格式化属性键
    const formatPropertyKey = (key) => {
      const keyMap = {
        'name': 'name',
        '严重程度': '严重程度',
        '紧急程度': '紧急程度',
        '所属系统': '所属系统',
        '症状描述': '症状描述',
        '操作类型': '操作类型',
        '注意事项': '注意事项',
        '检查目的': '检查目的',
        '正常范围': '正常范围',
        '异常指标': '异常指标',
        '用药途径': '用药途径',
        '剂量': '剂量',
        '使用时机': '使用时机',
        '正常范围_生命': '正常范围',
        '异常阈值': '异常阈值',
        '监测频率': '监测频率',
        '发生率': '发生率',
        '危险因素': '危险因素',
        '预防措施': '预防措施'
      }
      return keyMap[key] || key
    }

    // 监听节点类型筛选变化
    watch(selectedNodeType, () => {
      renderGraph()
    })

    onMounted(() => {
      initGraph()
      window.addEventListener('resize', () => {
        renderGraph()
      })
    })

    return {
      graphContainer,
      svg,
      isLoading,
      showLabels,
      showDetails,
      selectedNode,
      selectedNodeType,
      svgWidth,
      svgHeight,
      nodeColors,
      databaseStatus,
      databaseStatusType,
      filteredNodes,
      filteredLinks,
      resetView,
      toggleLabels,
      getNodeTypeText,
      getFilteredProperties,
      formatPropertyKey
    }
  }
}
</script>

<style scoped>
.knowledge-graph-container {
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

.control-panel {
  background: white;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
}

.graph-container {
  flex: 1;
  position: relative;
  margin: 10px;
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  flex-direction: column;
  gap: 16px;
  color: #909399;
}

.loading-icon {
  font-size: 24px;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Neo4j风格属性面板 */
.neo4j-properties-panel {
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
  padding: 0;
}

.neo4j-node-title {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 16px;
}

.node-icon-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 3px solid #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  flex-shrink: 0;
}

.node-name {
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
  word-break: break-word;
}

.neo4j-node-labels {
  margin-bottom: 20px;
}

.neo4j-properties-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.neo4j-property-item {
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 0;
}

.neo4j-property-item:last-child {
  border-bottom: none;
}

.property-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.property-label {
  font-size: 12px;
  color: #718096;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.property-value {
  font-size: 14px;
  color: #2d3748;
  font-weight: 400;
  line-height: 1.5;
  word-break: break-word;
}

/* 图例样式 */
.legend {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,0.2);
}

.legend h5 {
  margin: 0 0 12px 0;
  color: #4a5568;
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #4a5568;
}

.legend-color {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

/* SVG图形样式 - Neo4j风格 */
:deep(.node-group) {
  transition: all 0.2s ease;
}

:deep(.node-group:hover) {
  filter: brightness(1.1);
}

:deep(.link) {
  transition: all 0.2s ease;
}

:deep(.node-center-label) {
  user-select: none;
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

:deep(.link-label-text) {
  user-select: none;
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

:deep(.link-label-bg) {
  opacity: 0.9;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .neo4j-node-title {
    flex-direction: column;
    text-align: center;
  }
}
</style>
