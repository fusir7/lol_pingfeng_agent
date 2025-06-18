# LOL选手评分系统解析

## 项目概述

这是一个基于图像识别和大语言模型的英雄联盟(LOL)选手评分系统，可以从比赛截图中提取选手数据，计算评分，并生成专业评语。项目采用Python开发，使用了LangGraph框架构建处理流程，结合了计算机视觉和自然语言处理技术。

## 技术栈

- **后端框架**：Flask
- **图处理框架**：LangGraph
- **图像处理**：OpenCV, PIL, pytesseract
- **AI模型**：阿里云百炼API (Qwen-VL-Max视觉模型，Qwen-Max文本模型)
- **前端**：HTML, TailwindCSS

## 系统架构

系统采用清晰的三节点流程架构，基于LangGraph构建有向图处理流程：

### 1. 核心组件

- **`langgraph_agent.py`** - 主要代理类，负责构建和执行处理流程图
- **`run.py`** - 命令行入口
- **`app.py`** - Web应用入口
- **`nodes/`** - 包含处理流程的各个节点实现

### 2. 处理流程

系统的处理流程是一个三节点的有向图：

```
数据提取节点 -> 评分计算节点 -> 评语生成节点
```

每个节点负责特定的任务，输入和输出通过`GraphState`类型定义的状态对象传递。

## 数据结构

系统使用`GraphState`类型（在`nodes/types.py`中定义）作为节点间传递数据的载体：

```python
class GraphState(TypedDict):
    """图状态类"""
    image_path: str  # 图片路径
    players_data: List[Dict[str, Any]]  # 提取的选手数据
    blue_team: List[Dict[str, Any]]  # 蓝队数据
    red_team: List[Dict[str, Any]]  # 红队数据
    evaluations: List[Dict[str, Any]]  # 评分结果
    comments: Dict[str, List[str]]  # 评语
    final_result: Dict[str, List[Dict[str, Any]]]  # 最终结果
    error: str  # 错误信息
```

## 核心节点详细实现

### 1. 数据提取节点（`nodes/extract_data.py`）

**主要功能**：从LOL比赛截图中提取选手数据

**核心实现步骤**：

1. **图像预处理**：
   - 支持本地文件和远程URL图像
   - 对图像进行验证和格式转换（RGBA转RGB）
   - 将图像转换为Base64编码，便于API调用

2. **多模态模型调用**：
   - 使用阿里云百炼API的Qwen-VL-Max多模态模型
   - 构建提示词引导模型识别图像内容
   - 精心设计的提示词要求模型提取选手ID、队伍、位置、KDA数据、补刀数、伤害值和视野得分

3. **JSON解析与数据结构化**：
   - 从模型响应中提取JSON格式的数据
   - 使用正则表达式处理可能的不规范JSON格式
   - 将解析后的数据转换为标准结构

4. **团队分组处理**：
   - 将提取的选手数据按蓝队(BLUE)和红队(RED)分组
   - 执行基本验证，确保数据的完整性

5. **错误处理与备份机制**：
   - 当图像识别失败时，使用硬编码的默认数据
   - 详细的错误日志记录和异常捕获

**关键技术实现**：

```python
def _extract_stats_from_image(image_path):
    """从图片中提取数据"""
    # 准备图像数据
    img_str = _prepare_image(image_path)
    
    # 构建提示词
    prompt = """请分析这张英雄联盟比赛结果截图，提取所有10名选手的数据...
    以JSON格式输出，格式如下: [...]"""
    
    # 构建消息
    messages = [
        {"role": "system", "content": [{"text": "你是一个精确的数据提取助手..."}]},
        {"role": "user", "content": [
            {"image": f"data:image/jpeg;base64,{img_str}"},
            {"text": prompt}
        ]}
    ]
    
    # 调用多模态模型
    response = MultiModalConversation.call(
        api_key=os.getenv("BAILIAN_API_KEY", ""),
        model="qwen-vl-max",
        messages=messages
    )
    
    # 解析响应
    response_text = response.output.choices[0].message.content[0]['text']
    players_data = _parse_json_response(response_text)
    return players_data
```

### 2. 评分计算节点（`nodes/calculate_scores.py`）

**主要功能**：根据提取的数据计算选手评分

**核心实现步骤**：

1. **数据准备**：
   - 分别处理蓝队和红队选手数据
   - 为每个选手生成评分结果

2. **KDA评估**：
   - 计算KDA比率：(击杀+助攻)/死亡
   - 处理无死亡情况（完美KDA）
   - 根据KDA比率给予加减分

3. **伤害评估**：
   - 计算选手伤害在团队中的占比
   - 根据位置不同应用不同标准
   - 输出位置（中单/ADC）与非输出位置（上单/打野/辅助）采用不同评分标准

4. **视野评估**：
   - 基于选手的视野得分评估
   - 根据位置设置不同权重（辅助>打野>其他位置）
   - 高视野得分给予加分，低视野得分给予减分

5. **综合评分计算**：
   - 基础分为3分
   - 根据KDA、伤害、视野得分进行加减分
   - 最终评分限制在1-5分范围内，并四舍五入到0.5分制

**具体评分算法**：

```python
def _evaluate_player(player, team_players):
    """评估单个选手的表现"""
    # 复制选手数据
    evaluation = player.copy()
    
    # 计算KDA比率
    kills = player["stats"]["kills"]
    deaths = player["stats"]["deaths"]
    assists = player["stats"]["assists"]
    kda_ratio = (kills + assists) / deaths if deaths > 0 else (kills + assists)
    
    # 计算伤害占比
    total_team_damage = sum(p["stats"]["damage"] for p in team_players)
    damage_percentage = (player["stats"]["damage"] / total_team_damage * 100) if total_team_damage > 0 else 0
    
    # 获取视野得分
    sight_score = player["stats"].get("sight", 0)
    
    # 基础分3分
    base_score = 3.0
    
    # KDA加分/减分
    kda_score = 1.0 if kda_ratio >= 5 else \
               0.5 if kda_ratio >= 3 else \
              -1.0 if kda_ratio <= 1 else \
              -0.5 if kda_ratio <= 2 else 0
    
    # 伤害占比加分/减分（根据位置不同）
    position = player["position"]
    if position in ["MID", "BOT", "ADC"]:  # 输出位置
        # ...详细的伤害评分逻辑...
    else:  # 非输出位置
        # ...详细的伤害评分逻辑...
    
    # 视野得分加分/减分
    sight_score_weight = 1.0 if position in ["SUP", "SUPPORT"] else \
                        0.75 if position in ["JNG", "JUNGLE"] else 0.5
                        
    # ...详细的视野评分逻辑...
    
    # 计算最终评分并四舍五入到0.5
    final_score = max(1, min(5, base_score + kda_score + damage_score + sight_bonus))
    final_score = round(final_score * 2) / 2
    
    return evaluation
```

### 3. 评语生成节点（`nodes/generate_comments.py`）

**主要功能**：使用大语言模型生成专业评语

**核心实现步骤**：

1. **数据分组**：
   - 按队伍分别处理评分结果
   - 确保每个选手数据完整性

2. **提示词构建**：
   - 精心设计专业解说风格的提示词
   - 包含评语要求（专业、深入、有洞察力）
   - 详细添加每个选手的所有统计数据，包括KDA比率、伤害占比等

3. **LLM模型调用**：
   - 使用阿里云百炼API的Qwen-Max模型
   - 设置合适的生成参数（温度、top_p等）
   - 确保生成内容的专业性和符合电竞解说风格

4. **响应解析**：
   - 从模型响应中提取JSON格式的评语
   - 处理可能的非标准JSON格式
   - 正则表达式辅助提取JSON内容

5. **结果整合**：
   - 将评语与之前的评分数据合并
   - 构建最终输出结构

**提示词工程示例**：

```python
def _create_prompt(blue_team, red_team):
    """创建评语生成的提示词"""
    prompt = """
    你是一位英雄联盟职业比赛的资深解说和分析师，请根据以下选手数据，为每位选手的表现生成一段深度分析的评价。
    
    评价要求：
    1. 详细分析KDA、伤害占比、补刀数、视野得分等数据，揭示选手在比赛中的表现和影响力
    2. 结合位置特点(上单/打野/中单/ADC/辅助)分析选手的表现，不同位置有不同的职责和评判标准
    3. 评价风格应当专业、深入、有洞察力，像专业解说一样分析选手的优势和不足
    4. 可以适当推测选手在比赛中的战术选择和团队贡献
    5. 每位选手的评价控制在30-50字，要有深度但不冗长
    6. 评价要基于数据客观公正，不要过于主观或情绪化
    
    特别注意：
    - 视野得分(Sight)是衡量选手地图控制和信息收集能力的重要指标
    ...
    """
    
    # 添加蓝队和红队数据细节
    # ...
    
    return prompt
```

**模型调用示例**：

```python
def _call_llm(prompt):
    """调用大模型生成评语"""
    try:
        from dashscope import Generation
        
        # 调用百炼API
        response = Generation.call(
            model='qwen-max',
            prompt=prompt,
            api_key=os.getenv("BAILIAN_API_KEY", ""),
            max_tokens=2000,
            temperature=0.7,
            top_p=0.9
        )
        
        # 解析响应...
    except Exception as e:
        print(f"调用LLM失败: {e}")
        return _get_default_comments()
```

### 4. 流程控制节点（`nodes/flow_control.py`）

**主要功能**：控制处理流程的执行

**核心实现**：

```python
def decide_next_step(state: GraphState) -> str:
    """决定下一步操作"""
    if "error" in state and state["error"]:
        print(f"发生错误: {state['error']}")
        return END
    
    if "final_result" in state and state["final_result"]:
        return END
        
    return "continue" 
```

**实现逻辑**：
- 检查状态中是否有错误，有则终止流程
- 检查是否已生成最终结果，是则终止流程
- 否则继续执行下一个节点

## 主要代理类实现

`LOLAnalysisAgent`类（在`langgraph_agent.py`中）是整个系统的核心，负责构建和执行处理流程图：

```python
class LOLAnalysisAgent:
    """英雄联盟比赛分析代理"""
    
    def __init__(self, llm_api_url=None, llm_api_key=None, bailian_agent_key=None):
        """初始化代理"""
        # 设置环境变量...
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """构建处理图"""
        # 创建图
        builder = StateGraph(GraphState)
        
        # 添加节点
        builder.add_node("extract_data", extract_data)
        builder.add_node("calculate_scores", calculate_scores)
        builder.add_node("generate_comments", generate_comments)
        
        # 设置入口节点
        builder.set_entry_point("extract_data")
        
        # 添加边
        builder.add_edge("extract_data", "calculate_scores")
        builder.add_edge("calculate_scores", "generate_comments")
        
        # 编译图
        graph = builder.compile()
        return graph
    
    def process_image(self, image_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """处理图片并返回分析结果"""
        # 创建初始状态
        state = {"image_path": image_path}
        
        # 运行图
        result = self.graph.invoke(state)
        
        # 检查是否有错误并返回结果
        if "error" in result and result["error"]:
            return {"error": result["error"]}
        return result.get("final_result", {"error": "未生成结果"})
```

## 用户接口实现

### 1. 命令行接口（`run.py`）

**功能**：命令行方式运行评分系统

**实现细节**：
- 使用`argparse`库解析命令行参数
- 支持指定图片路径、API密钥、详细日志等参数
- 创建`LOLAnalysisAgent`实例处理图片
- 格式化输出蓝队和红队选手的评分结果

**关键代码**：

```python
def main():
    """LOL选手评分系统命令行入口"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='LOL选手评分系统')
    parser.add_argument('image_path', help='图片路径')
    parser.add_argument('--api_key', help='百炼API密钥')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    # 解析命令行参数...
    
    # 创建分析代理并处理图像
    agent = LOLAnalysisAgent(
        llm_api_url=BAILIAN_API_URL,
        llm_api_key=api_key,
        bailian_agent_key=BAILIAN_AGENT_KEY
    )
    result = agent.process_image(args.image_path)
    
    # 打印结果...
```

### 2. Web接口（`app.py`）

**功能**：提供Web界面上传并分析LOL比赛截图

**实现细节**：
- 使用Flask框架创建Web应用
- 提供首页和图片分析接口
- 处理文件上传和类型验证
- 使用TailwindCSS构建美观的UI界面
- 格式化分析结果为HTML展示

**关键路由**：

```python
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_image', methods=['POST', 'GET'])
def analyze_image_route():
    # 处理GET请求...
    
    # 处理POST请求
    if 'image' not in request.files:
        return jsonify({"error": "没有上传图片"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '没有选择图片'}), 400

    if file and allowed_file(file.filename):
        try:
            # 保存上传的图片
            local_path = os.path.join(os.getcwd(), 'uploaded_image.png')
            file.save(local_path)
            
            # 创建分析代理并处理图像
            agent = LOLAnalysisAgent(...)
            result = agent.process_image(local_path)
            
            # 格式化结果为HTML
            formatted_results = format_results(result)
            return formatted_results
            
        except Exception as e:
            # 错误处理...
```

## 前端实现

系统前端使用TailwindCSS构建了英雄联盟风格的UI界面：

1. **设计风格**：
   - 暗色背景与金色/蓝色强调色
   - 符合英雄联盟游戏UI风格的元素和动效
   - 响应式布局，适配不同设备

2. **主要组件**：
   - 图片上传区域
   - 选手数据展示卡片
   - 蓝队/红队分组展示
   - 评分和评语可视化

3. **交互体验**：
   - 拖放上传功能
   - 动画和过渡效果增强体验
   - 精美的卡片布局展示分析结果

## 文件间的依赖关系

1. **主入口依赖**：
   - `app.py`和`run.py`都依赖于`langgraph_agent.py`
   - `langgraph_agent.py`依赖于`nodes`目录下的各个模块

2. **节点间依赖**：
   - 所有节点都依赖于`nodes/types.py`中定义的`GraphState`类型
   - 节点之间通过状态对象传递数据，没有直接依赖

3. **外部依赖**：
   - 百炼API：系统依赖阿里云百炼平台的多模态模型和文本生成模型
   - LangGraph框架：用于构建和执行工作流图
   - 图像处理库：用于预处理比赛截图

## 项目特色和优势

1. **模块化架构**：基于LangGraph的模块化设计，每个节点负责特定功能，易于维护和扩展

2. **多模态融合**：结合计算机视觉和自然语言处理技术，实现从图像到专业评价的端到端处理

3. **专业评分系统**：根据LOL比赛特点设计的多维度评分算法，考虑不同位置的特殊性

4. **错误处理机制**：在各个环节都有完善的错误处理和备选方案，保证系统稳定性

5. **用户友好界面**：设计精美的LOL风格Web界面，提供直观的使用体验

## 总结

这个LOL选手评分系统是一个将计算机视觉、自然语言处理和领域专业知识融合的优秀项目。通过LangGraph框架构建的三节点工作流，系统能够从比赛截图中提取数据，计算专业评分，并生成深度分析评语。系统提供了命令行和Web两种使用方式，满足不同场景的需求。项目代码结构清晰，模块化设计良好，易于维护和扩展。 