import os
import json
from typing import Dict, List, Any
from langgraph.graph import StateGraph

# 导入节点模块
from nodes.types import GraphState
from nodes.extract_data import extract_data
from nodes.calculate_scores import calculate_scores
from nodes.generate_comments import generate_comments
from nodes.flow_control import decide_next_step
from config import BAILIAN_API_URL, BAILIAN_API_KEY, BAILIAN_AGENT_KEY, VERBOSE_DEBUG

class LOLAnalysisAgent:
    """英雄联盟比赛分析代理"""
    
    def __init__(self, llm_api_url=None, llm_api_key=None, bailian_agent_key=None):
        """初始化代理"""
        # 设置环境变量
        if llm_api_url:
            os.environ["BAILIAN_API_URL"] = llm_api_url
        else:
            os.environ["BAILIAN_API_URL"] = BAILIAN_API_URL
        
        if llm_api_key:
            os.environ["BAILIAN_API_KEY"] = llm_api_key
        else:
            os.environ["BAILIAN_API_KEY"] = BAILIAN_API_KEY
            
        if bailian_agent_key:
            os.environ["BAILIAN_AGENT_KEY"] = bailian_agent_key
        else:
            os.environ["BAILIAN_AGENT_KEY"] = BAILIAN_AGENT_KEY
        
        os.environ["VERBOSE_DEBUG"] = VERBOSE_DEBUG
            
        # 打印环境变量
        print(f"百炼API URL: {os.getenv('BAILIAN_API_URL', '')}")
        print(f"百炼API密钥: {os.getenv('BAILIAN_API_KEY', '')[:5]}...")
        print(f"百炼应用ID: {os.getenv('BAILIAN_AGENT_KEY', '')}")
        print(f"详细日志: 已启用")
        
        # 创建图
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
        print(f"开始分析图片: {image_path}")
        
        # 创建初始状态
        state = {"image_path": image_path}
        
        # 运行图
        result = self.graph.invoke(state)
        
        # 检查是否有错误
        if "error" in result and result["error"]:
            return {"error": result["error"]}
        
        # 返回最终结果
        return result.get("final_result", {"error": "未生成结果"})

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        agent = LOLAnalysisAgent()
        result = agent.process_image(sys.argv[1])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("请提供图片路径") 