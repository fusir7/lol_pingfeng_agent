from typing import Dict, List, Any, TypedDict

# 定义状态类型
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