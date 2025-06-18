import os
import json
import traceback
from nodes.types import GraphState

def generate_comments(state: GraphState) -> GraphState:
    """生成选手评语"""
    print("节点3: 评语生成...")
    
    if "error" in state and state["error"]:
        return state
        
    try:
        # 按团队分组
        blue_team = [e for e in state["evaluations"] if e.get('team') == 'BLUE']
        red_team = [e for e in state["evaluations"] if e.get('team') == 'RED']
        
        # 生成提示词
        prompt = _create_prompt(blue_team, red_team)
        
        # 调用LLM生成评语
        comments = _call_llm(prompt)
        
        # 合并结果
        final_result = {
            "blue_team": [],
            "red_team": []
        }
        
        # 为蓝队选手添加评语
        for i, eval_data in enumerate(blue_team):
            if i < len(comments["blue_team"]):
                eval_data_with_comment = {**eval_data, "comment": comments["blue_team"][i]}
                final_result["blue_team"].append(eval_data_with_comment)
        
        # 为红队选手添加评语
        for i, eval_data in enumerate(red_team):
            if i < len(comments["red_team"]):
                eval_data_with_comment = {**eval_data, "comment": comments["red_team"][i]}
                final_result["red_team"].append(eval_data_with_comment)
                
        print("评语生成完成")
        
        return {**state, "comments": comments, "final_result": final_result}
    except Exception as e:
        traceback.print_exc()
        return {"error": f"评语生成失败: {str(e)}", **state}

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
    - 辅助和打野位置的视野得分尤为重要，对团队整体战术有重大影响
    - 高视野得分(15+)表明选手视野控制出色，中等视野得分(8-14)表现良好
    - 关键位置(辅助/打野)的低视野得分(<5)是明显缺陷
    
    蓝队选手数据：
    """
    
    # 添加蓝队数据
    for player in blue_team:
        prompt += f"\n{player['name']}({player['position']}): KDA {player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}，KDA比率 {player['kda_ratio']}，补刀 {player['stats']['cs']}，伤害 {player['stats']['damage']}，伤害占比 {player['damage_percentage']}%，视野得分 {player.get('sight_score', 0)}，评分 {player['rating']}/5"
    
    prompt += """
    
    红队选手数据：
    """
    
    # 添加红队数据
    for player in red_team:
        prompt += f"\n{player['name']}({player['position']}): KDA {player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}，KDA比率 {player['kda_ratio']}，补刀 {player['stats']['cs']}，伤害 {player['stats']['damage']}，伤害占比 {player['damage_percentage']}%，视野得分 {player.get('sight_score', 0)}，评分 {player['rating']}/5"
    
    prompt += """
    
    请以JSON格式输出，格式如下：
    {
      "blue_team": [
        "选手1的深度分析评价",
        "选手2的深度分析评价",
        "选手3的深度分析评价",
        "选手4的深度分析评价",
        "选手5的深度分析评价"
      ],
      "red_team": [
        "选手1的深度分析评价",
        "选手2的深度分析评价",
        "选手3的深度分析评价",
        "选手4的深度分析评价",
        "选手5的深度分析评价"
      ]
    }
    
    注意：
    1. 评价顺序要与上面提供的选手顺序一致
    2. 不要在评价中重复数据，而是基于数据进行深入分析
    3. 评价要有洞察力，揭示数据背后的意义
    4. 使用电竞解说的专业术语和表达方式
    5. 对于视野得分特别突出或特别不足的选手，应当在评价中特别提及
    """
    
    return prompt

def _call_llm(prompt):
    """调用大模型生成评语"""
    try:
        from dashscope import Generation
        
        # 调用百炼API
        response = Generation.call(
            model='qwen-max',
            prompt=prompt,
            api_key=os.getenv("BAILIAN_API_KEY", ""),
            # 增加最大token数，确保生成更详细的评语
            max_tokens=2000,
            # 降低温度，使输出更加确定性和专业
            temperature=0.7,
            # 增加top_p值，保持一定的创造性
            top_p=0.9
        )
        
        # 解析响应
        if hasattr(response, 'output') and hasattr(response.output, 'text'):
            response_text = response.output.text
            
            # 提取JSON部分
            try:
                # 尝试解析整个响应
                result = json.loads(response_text)
                return result
            except:
                # 如果失败，尝试提取JSON部分
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        return json.loads(json_str)
                    except:
                        print("JSON解析失败，使用默认评语")
                        return _get_default_comments()
        
        # 如果无法解析，返回默认评语
        print("无法从响应中提取文本，使用默认评语")
        return _get_default_comments()
    except Exception as e:
        print(f"调用LLM失败: {e}")
        traceback.print_exc()
        return _get_default_comments()

def _get_default_comments():
    """返回默认评语"""
    return {
        "blue_team": [
            "作为上单位置，展现出色的生存能力和团战贡献。KDA比率高，伤害输出稳定，在团战中能有效吸收伤害并创造进场机会，是队伍的坚实前排。",
            "打野节奏把控出色，无死亡记录体现了极高的地图意识。KDA比率达11，成功带动全队节奏，gank效率高，野区资源控制能力突出。",
            "中路对线压制力强，KDA和伤害占比均衡。团战中的伤害输出稳定可靠，能够精准找到切入时机，是队伍的核心输出点。",
            "ADC位置表现亮眼，零死亡的同时保持高伤害占比。团战中的站位和输出都很到位，补刀领先对手，经济转化为装备优势明显。",
            "辅助视野控制到位，零死亡高助攻体现了出色的保护能力。团战中的开团决策精准，游走支援节奏把握得当，为队伍创造大量优势。"
        ],
        "red_team": [
            "上路面对较大压力，但仍然保持了不错的补刀和伤害输出。虽然KDA不佳，但在团战中尽力发挥了前排作用，个人能力值得肯定。",
            "打野入侵和资源控制欠佳，KDA数据反映了节奏被对手掌控的现状。野区压力大导致gank效率低下，需要改善与队友的配合。",
            "中单个人能力突出，是队伍中为数不多的亮点。虽然团队整体处于劣势，但仍然保持了不错的KDA和伤害输出，与队友配合有待提高。",
            "下路输出稳定，但在关键团战中的发挥不够理想。补刀和经济发育相对落后，位置选择和团战站位需要更加谨慎，伤害效率有待提升。",
            "辅助在劣势局面中承受了巨大压力，死亡次数较多反映了视野争夺的困境。保护核心的意识有待加强，需要更好地与打野协作控制资源。"
        ]
    } 