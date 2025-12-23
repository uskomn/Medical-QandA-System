def format_user_response(raw_response):
    """
    将原始响应格式化为用户友好的格式

    Args:
        raw_response: 从 controlled_generation_with_subgraph 返回的原始响应

    Returns:
        格式化后的用户友好响应
    """

    # 1. 核心答案
    answer = raw_response.get('answer', '暂无答案')

    # 2. 提取关键信息
    validation = raw_response.get('validation', {})
    subgraph = raw_response.get('subgraph', {})
    reasoning_chains = raw_response.get('reasoning_chains', [])

    # 3. 计算可信度分数
    confidence_score = validation.get('overall_score', 0) * 100

    # 4. 提取相关实体(用于前端展示或进一步查询)
    relevant_entities = []
    for node in subgraph.get('nodes', [])[:10]:  # 最多10个
        relevant_entities.append({
            'name': node['name'],
            'type': node['type'],
            'consistency': node.get('consistency', 0)
        })

    # 5. 提取关键路径(用于展示知识来源)
    key_paths = []
    for path in subgraph.get('paths', [])[:5]:  # 最多5条
        key_paths.append({
            'description': path['description'],
            'consistency': path.get('consistency', 0)
        })

    # 6. 提取推理过程(如果有)
    reasoning_summary = []
    for chain in reasoning_chains[:3]:  # 最多3条
        reasoning_summary.append({
            'from': chain['from'],
            'to': chain['to'],
            'hops': chain['path'].get('hops', 0)
        })

    # 7. 构建用户友好的响应
    formatted = {
        # 主要答案
        'answer': answer,

        # 知识来源(可选展示)
        'knowledge_source': {
            'entity_count': len(subgraph.get('nodes', [])),
            'relation_count': len(subgraph.get('relationships', [])),
            'relevant_entities': relevant_entities,
            'key_paths': key_paths
        },

        # 推理信息(可选展示)
        'reasoning': {
            'has_reasoning': len(reasoning_chains) > 0,
            'chain_count': len(reasoning_chains),
            'summary': reasoning_summary
        },

        # 元数据
        'metadata': {
            'query': raw_response.get('query', ''),
            'total_nodes': len(subgraph.get('nodes', [])),
            'total_paths': len(subgraph.get('paths', [])),
            'consistency_info': raw_response.get('consistency_info', '').strip()
        }
    }

    return formatted