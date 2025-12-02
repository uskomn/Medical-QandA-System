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
        <el-col :span="6">
          <div class="graph-info">
            <el-tag :type="databaseStatusType" size="small">
              {{ databaseStatus }}
            </el-tag>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="graph-info">
            <el-tag type="info" size="small">
              节点: {{ filteredNodes.length }} | 连接: {{ filteredLinks.length }}
            </el-tag>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="graph-actions">
            <el-button 
              size="small" 
              @click="refreshData" 
              :loading="isRefreshing"
              plain
            >
              <el-icon><Refresh /></el-icon>
              刷新数据
            </el-button>
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

    <!-- 节点详情面板 -->
    <el-drawer
      v-model="showDetails"
      :title="selectedNode ? '节点详情 - ' + selectedNode.label : '节点详情'"
      direction="rtl"
      size="35%"
    >
      <div v-if="selectedNode" class="neo4j-details-panel">
        <!-- 节点基本信息 -->
        <div class="node-header">
          <div class="node-icon" :style="{ backgroundColor: nodeColors[selectedNode.group] || '#999' }">
            {{ getNodeTypeIcon(selectedNode.group) }}
          </div>
          <div class="node-basic-info">
            <h3>{{ selectedNode.label }}</h3>
            <el-tag :type="getNodeTypeColor(selectedNode.group)" size="default">
              {{ selectedNode.type }}
            </el-tag>
            <el-tag v-if="selectedNode.group === 'disease'" type="danger" size="small">
              ID: {{ selectedNode.id }}
            </el-tag>
          </div>
        </div>
        
        <!-- 节点属性信息 -->
        <div class="node-properties" v-if="selectedNode.properties">
          <h5>
            <el-icon><Document /></el-icon>
            属性信息
          </h5>
          <div class="properties-grid">
            <div class="property-card" v-for="(value, key) in selectedNode.properties" :key="key" v-if="value">
              <div class="property-key">{{ formatPropertyKey(key) }}</div>
              <div class="property-value">{{ value }}</div>
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
import { knowledgeApi } from '../utils/api'
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
    
    // 节点颜色映射，适配新的实体类型
    const nodeColors = {
      disease: '#e74c3c',      // 疾病 - 红色
      treatment: '#3498db',    // 治疗 - 蓝色
      examination: '#f39c12',  // 检查 - 橙色
      medication: '#9b59b6',   // 药物 - 紫色
      vital_signs: '#1abc9c',  // 生命体征 - 青色
      complication: '#e67e22', // 并发症 - 深橙色
      other: '#95a5a6'         // 其他 - 灰色
    }

    // 计算过滤后的节点和连接
    const filteredNodes = computed(() => {
      if (!selectedNodeType.value) return graphData.value.nodes
      return graphData.value.nodes.filter(node => node.group === selectedNodeType.value)
    })

    const filteredLinks = computed(() => {
      // 如果没有筛选，返回所有连线
      if (!selectedNodeType.value) {
        return graphData.value.links
      }
      
      // 如果有筛选，只显示与选中节点类型相关的连线
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
        const healthResponse = await fetch('http://localhost:5000/knowledge_graph/test_connection')
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

    // 刷新数据
    const refreshData = async () => {
      isRefreshing.value = true
      try {
        await checkDatabaseStatus()
        await initGraph()
        ElMessage.success('数据刷新成功')
      } catch (error) {
        console.error('刷新数据失败:', error)
        ElMessage.error('刷新数据失败')
      } finally {
        isRefreshing.value = false
      }
    }

    // 渲染图谱
    const renderGraph = () => {
      if (!svg.value || !graphContainer.value) return

      // 调试信息
      console.log('渲染图谱 - 节点数量:', filteredNodes.value.length)
      console.log('渲染图谱 - 连线数量:', filteredLinks.value.length)
      console.log('渲染图谱 - 节点数据:', filteredNodes.value.slice(0, 2))
      console.log('渲染图谱 - 连线数据:', filteredLinks.value.slice(0, 2))

      // 获取容器尺寸
      const containerRect = graphContainer.value.getBoundingClientRect()
      svgWidth.value = containerRect.width - 20
      // 使用更合适的边距，避免过度预留空间
      svgHeight.value = containerRect.height - 20

      // 清空之前的内容
      d3.select(svg.value).selectAll('*').remove()

      const svgElement = d3.select(svg.value)
      const g = svgElement.append('g')

      // 设置缩放行为
      const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          g.attr('transform', event.transform)
        })

      svgElement.call(zoom)

      // 创建力导向图
      const simulation = d3.forceSimulation(filteredNodes.value)
        .force('link', d3.forceLink(filteredLinks.value).id(d => d.id).distance(80))
        .force('charge', d3.forceManyBody().strength(-250))
        .force('center', d3.forceCenter(svgWidth.value / 2, svgHeight.value / 2))
        .force('collision', d3.forceCollide().radius(25))

      // 自动缩放函数
      const autoFit = () => {
        if (filteredNodes.value.length === 0) return
        
        // 计算图谱的边界
        const bounds = g.node().getBBox()
        const parent = g.node().parentNode
        const fullWidth = svgWidth.value
        const fullHeight = svgHeight.value
        
        const width = bounds.width
        const height = bounds.height
        
        if (width === 0 || height === 0) return
        
        // 计算缩放比例，留一些边距
        const scale = 0.85 / Math.max(width / fullWidth, height / fullHeight)
        const translate = [
          fullWidth / 2 - scale * (bounds.x + width / 2),
          fullHeight / 2 - scale * (bounds.y + height / 2)
        ]
        
        // 应用变换
        const transform = d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        svgElement.transition().duration(1000).call(zoom.transform, transform)
      }

      // 绘制连接线
      const links = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(filteredLinks.value)
        .enter().append('line')
        .attr('stroke', '#9aa0a6')
        .attr('stroke-opacity', 0.7)
        .attr('stroke-width', d => Math.sqrt(d.value || 1))
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
          d3.select(this).attr('stroke-width', Math.sqrt(d.value || 1) * 1.5).attr('stroke-opacity', 1)
          
          // 显示关系标签的悬浮效果
          const linkLabel = g.selectAll('.link-label')
          linkLabel.style('opacity', link => link === d ? 1 : 0.3)
        })
        .on('mouseout', function(event, d) {
          d3.select(this).attr('stroke-width', Math.sqrt(d.value || 1)).attr('stroke-opacity', 0.7)
          
          // 恢复关系标签的正常显示
          const linkLabel = g.selectAll('.link-label')
          linkLabel.style('opacity', 1)
        })
        .style('display', filteredLinks.value.length > 0 ? 'block' : 'none')

      // 绘制节点
      const nodes = g.append('g')
        .selectAll('circle')
        .data(filteredNodes.value)
        .enter().append('circle')
        .attr('r', 15)
        .attr('fill', d => nodeColors[d.group] || '#999')
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
          selectedNode.value = d
          showDetails.value = true
        })
        .on('mouseover', function(event, d) {
          d3.select(this).attr('r', 18)
        })
        .on('mouseout', function(event, d) {
          d3.select(this).attr('r', 15)
        })
        .call(d3.drag()
          .on('start', dragstarted)
          .on('drag', dragged)
          .on('end', dragended)
        )

      // 添加节点标签
      const labels = g.append('g')
        .selectAll('.node-label')
        .data(filteredNodes.value)
        .enter().append('text')
        .attr('class', 'node-label')
        .text(d => d.label)
        .attr('font-size', 11)
        .attr('dx', 20)
        .attr('dy', 4)
        .attr('fill', '#2d3748')
        .attr('font-weight', 'bold')
        .style('pointer-events', 'none')
        .style('text-shadow', '1px 1px 2px rgba(255,255,255,0.8)')
        .style('display', showLabels.value ? 'block' : 'none')
        
      // 添加关系标签
      const linkLabels = g.append('g')
        .attr('class', 'link-labels')
        .selectAll('.link-label')
        .data(filteredLinks.value)
        .enter().append('text')
        .attr('class', 'link-label')
        .text(d => d.relationshipType || '')
        .attr('font-size', 10)
        .attr('fill', '#4a5568')
        .attr('text-anchor', 'middle')
        .attr('stroke', 'white')
        .attr('stroke-width', 0.5)
        .attr('paint-order', 'stroke')
        .style('pointer-events', 'none')
        .style('font-style', 'italic')
        .style('opacity', 0.8)

      // 更新位置
      simulation.on('tick', () => {
        links
          .attr('x1', d => {
            const source = typeof d.source === 'object' ? d.source : {x: 0, y: 0}
            return source.x || 0
          })
          .attr('y1', d => {
            const source = typeof d.source === 'object' ? d.source : {x: 0, y: 0}
            return source.y || 0
          })
          .attr('x2', d => {
            const target = typeof d.target === 'object' ? d.target : {x: 0, y: 0}
            return target.x || 0
          })
          .attr('y2', d => {
            const target = typeof d.target === 'object' ? d.target : {x: 0, y: 0}
            return target.y || 0
          })

        nodes
          .attr('cx', d => d.x || 0)
          .attr('cy', d => d.y || 0)

        labels
          .attr('x', d => (d.x || 0) + 20)
          .attr('y', d => (d.y || 0) + 4)
          
        // 更新关系标签位置（在连线中点显示）
        linkLabels
          .attr('x', d => {
            const source = typeof d.source === 'object' ? d.source : {x: 0, y: 0}
            const target = typeof d.target === 'object' ? d.target : {x: 0, y: 0}
            return ((source.x || 0) + (target.x || 0)) / 2
          })
          .attr('y', d => {
            const source = typeof d.source === 'object' ? d.source : {x: 0, y: 0}
            const target = typeof d.target === 'object' ? d.target : {x: 0, y: 0}
            return ((source.y || 0) + (target.y || 0)) / 2
          })
      })
      
      // 仿真完成后自动缩放适配
      simulation.on('end', () => {
        // 延迟一下确保所有元素都已渲染
        setTimeout(() => {
          autoFit()
        }, 100)
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
      const labels = d3.select(svg.value).selectAll('text')
      labels.style('display', showLabels.value ? 'block' : 'none')
    }

    // 获取节点类型颜色
    const getNodeTypeColor = (type) => {
      const colorMap = {
        disease: 'danger',
        treatment: 'primary', 
        examination: 'warning',
        medication: 'info',
        vital_signs: 'success',
        complication: '',
        other: 'info'
      }
      return colorMap[type] || 'info'
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

    // 获取节点连接
    const getNodeConnections = (nodeId) => {
      return graphData.value.links.filter(link => 
        link.source === nodeId || link.target === nodeId ||
        link.source.id === nodeId || link.target.id === nodeId
      )
    }

    // 获取节点名称
    const getNodeName = (nodeId) => {
      const node = graphData.value.nodes.find(n => n.id === nodeId)
      return node ? node.label : nodeId
    }

    // 获取节点类型图标
    const getNodeTypeIcon = (type) => {
      const iconMap = {
        disease: '🏥',
        treatment: '⚕️',
        examination: '🔬',
        medication: '💊',
        vital_signs: '📊',
        complication: '⚠️',
        other: '🔵'
      }
      return iconMap[type] || '🔵'
    }

    // 格式化属性键
    const formatPropertyKey = (key) => {
      const keyMap = {
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

    // 获取关系方向
    const getRelationshipDirection = (currentNodeId, link) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source
      const targetId = typeof link.target === 'object' ? link.target.id : link.target
      
      if (sourceId === currentNodeId) {
        return '→'
      } else if (targetId === currentNodeId) {
        return '←'
      }
      return '↔'
    }

    // 获取关系类型颜色
    const getRelationshipTypeColor = (relationshipType) => {
      const colorMap = {
        '需要治疗': 'danger',
        '需要检查': 'warning',
        '使用药物': 'info',
        '监测指标': 'success',
        '引起并发症': 'danger',
        '治疗': 'primary',
        '检查': 'warning',
        '药物': 'info',
        '指标': 'success',
        '并发症': 'danger'
      }
      return colorMap[relationshipType] || 'info'
    }

    // 突出显示连接
    const highlightConnection = (link) => {
      // 这里可以添加高亮特定连接的逻辑
      console.log('高亮连接:', link)
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
      isRefreshing,
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
      refreshData,
      checkDatabaseStatus,
      getNodeTypeColor,
      getNodeTypeText,
      getNodeTypeIcon,
      formatPropertyKey,
      getRelationshipDirection,
      getRelationshipTypeColor,
      highlightConnection,
      getNodeConnections,
      getNodeName
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

.graph-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.graph-container {
  flex: 1;
  position: relative;
  margin: 10px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
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

/* Neo4j风格详情面板样式 */
.neo4j-details-panel {
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #dee2e6;
}

.node-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}

.node-basic-info h3 {
  margin: 0 0 8px 0;
  color: #2d3748;
  font-size: 18px;
  font-weight: 600;
}

.node-properties {
  margin-bottom: 24px;
}

.node-properties h5 {
  margin: 0 0 12px 0;
  color: #4a5568;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.properties-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.property-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
  transition: all 0.2s ease;
}

.property-card:hover {
  border-color: #cbd5e0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.property-key {
  font-size: 12px;
  color: #718096;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.property-value {
  font-size: 14px;
  color: #2d3748;
  font-weight: 500;
}

.node-connections {
  margin-top: 24px;
}

.node-connections h5 {
  margin: 0 0 16px 0;
  color: #4a5568;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.connections-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.connection-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.connection-item:hover {
  border-color: #3182ce;
  box-shadow: 0 2px 8px rgba(49, 130, 206, 0.1);
  transform: translateY(-1px);
}

.connection-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.connected-node {
  font-size: 14px;
  color: #2d3748;
  font-weight: 500;
}

.relationship-arrow {
  font-size: 16px;
  color: #718096;
  font-weight: bold;
  margin: 0 8px;
}

.relationship-tag {
  margin-bottom: 8px;
}

.relation-properties {
  margin-top: 8px;
}

.property-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.relation-property-tag {
  font-size: 11px !important;
  height: 20px !important;
  line-height: 18px !important;
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
:deep(.node) {
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
  transition: all 0.2s ease;
}

:deep(.node:hover) {
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
}

:deep(.link) {
  transition: all 0.2s ease;
}

:deep(.node-label) {
  user-select: none;
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

:deep(.link-label) {
  user-select: none;
  font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
  text-shadow: 1px 1px 2px rgba(255,255,255,0.9);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .node-header {
    flex-direction: column;
    text-align: center;
  }
  
  .properties-grid {
    grid-template-columns: 1fr;
  }
  
  .connection-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style>