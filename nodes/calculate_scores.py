import traceback
import os
import json
from dashscope import MultiModalConversation
from nodes.types import GraphState

def calculate_scores(state: GraphState) -> GraphState:
    """计算选手评分"""
    print("节点2: 评分计算...")
    
    if "error" in state and state["error"]:
        return state
        
    try:
        # 先使用规则计算评分
        blue_evaluations = [_evaluate_player(player, state["blue_team"]) for player in state["blue_team"]]
        red_evaluations = [_evaluate_player(player, state["red_team"]) for player in state["red_team"]]
        
        # 使用大模型辅助评分
        model_evaluations = _get_model_evaluations(state["blue_team"], state["red_team"])
        
        # 结合两种评分结果 (权重0.35:0.65)
        combined_blue_evaluations = []
        combined_red_evaluations = []
        
        # 结合蓝队评分
        for rule_eval in blue_evaluations:
            player_name = rule_eval["name"]
            model_eval = next((e for e in model_evaluations.get("blue_team", []) if e["name"] == player_name), None)
            if model_eval:
                combined_eval = rule_eval.copy()
                # 按5:5权重结合评分
                rule_score = rule_eval["rating"]
                model_score = model_eval["rating"]
                combined_score = (rule_score * 0.35) + (model_score * 0.65)
                # 四舍五入到0.5
                combined_score = round(combined_score * 2) / 2
                combined_eval["rating"] = combined_score
                combined_eval["rule_rating"] = rule_score  # 保存原规则评分
                combined_eval["model_rating"] = model_score  # 保存模型评分
                combined_blue_evaluations.append(combined_eval)
            else:
                combined_blue_evaluations.append(rule_eval)  # 如果没有找到对应的模型评分，使用规则评分
        
        # 结合红队评分
        for rule_eval in red_evaluations:
            player_name = rule_eval["name"]
            model_eval = next((e for e in model_evaluations.get("red_team", []) if e["name"] == player_name), None)
            if model_eval:
                combined_eval = rule_eval.copy()
                # 按5:5权重结合评分
                rule_score = rule_eval["rating"]
                model_score = model_eval["rating"]
                combined_score = (rule_score * 0.5) + (model_score * 0.5)
                # 四舍五入到0.5
                combined_score = round(combined_score * 2) / 2
                combined_eval["rating"] = combined_score
                combined_eval["rule_rating"] = rule_score
                combined_eval["model_rating"] = model_score
                combined_red_evaluations.append(combined_eval)
            else:
                combined_red_evaluations.append(rule_eval)
        
        # 合并评分结果
        evaluations = combined_blue_evaluations + combined_red_evaluations
        
        print(f"完成评分计算，蓝队 {len(combined_blue_evaluations)} 名选手，红队 {len(combined_red_evaluations)} 名选手")
        
        return {**state, "evaluations": evaluations}
    except Exception as e:
        traceback.print_exc()
        return {"error": f"评分计算失败: {str(e)}", **state}

def _get_model_evaluations(blue_team, red_team):
    """使用大语言模型对选手表现进行评分"""
    try:
        print("调用大模型进行辅助评分...")
        
        # 获取API密钥
        api_key = os.getenv("BAILIAN_API_KEY", "")
        if not api_key:
            print("警告: BAILIAN_API_KEY未设置，无法调用大模型进行评分")
            return {"blue_team": [], "red_team": []}
        
        # 构建选手数据
        players_data = []
        for player in blue_team:
            players_data.append({
                "name": player["name"],
                "position": player["position"],
                "team": "蓝队",
                "stats": {
                    "kills": player["stats"]["kills"],
                    "deaths": player["stats"]["deaths"],
                    "assists": player["stats"]["assists"],
                    "cs": player["stats"]["cs"],
                    "damage": player["stats"]["damage"],
                    "sight": player["stats"].get("sight", 0)
                }
            })
        
        for player in red_team:
            players_data.append({
                "name": player["name"],
                "position": player["position"],
                "team": "红队",
                "stats": {
                    "kills": player["stats"]["kills"],
                    "deaths": player["stats"]["deaths"],
                    "assists": player["stats"]["assists"],
                    "cs": player["stats"]["cs"],
                    "damage": player["stats"]["damage"],
                    "sight": player["stats"].get("sight", 0)
                }
            })
        
        # 构建提示词
        prompt = """
        你的任务是对以下提供的英雄联盟选手真实数据进行专业评分分析。

        请根据所提供的每位选手的实际数据，对每名选手进行1-5分的评分（可以有0.5的半分）。
        
        评分必须考虑以下因素：
        1. KDA比率（击杀+助攻/死亡）：比率越高，评分越高
        2. 补刀数(CS)：与其他同位置选手相比的优劣
        3. 伤害输出：总量及在团队中的占比
        4. 视野得分：特别是对辅助和打野位置尤为重要
        5. 位置特性：
           - 中单/ADC: 应有较高伤害输出和生存能力
           - 上单: 应有足够的坦度或伤害贡献
           - 打野: 应有较高的参团率和视野控制
           - 辅助: 应有良好的视野控制和助攻数
        
        请确保为每位选手分配符合其表现的评分，这些评分将与规则评分结合，对选手进行最终评价。
        
        必须返回以下格式的JSON（评分必须是数字，不要用字符串）：
        {
          "blue_team": [
            {"name": "实际选手名", "rating": 实际评分},
            ...
          ],
          "red_team": [
            {"name": "实际选手名", "rating": 实际评分},
            ...
          ]
        }
        
        仅返回JSON数据，不要添加任何解释或其他文本。我需要直接处理你返回的JSON。
        """
        
        # 构建系统消息和用户消息
        messages = [
            {
                "role": "system",
                "content": [{"text": "你是一位专业的英雄联盟数据分析师，擅长客观评价选手表现。"}]
            },
            {
                "role": "user",
                "content": [
                    {"text": prompt + "\n\n选手数据: " + json.dumps(players_data, ensure_ascii=False, indent=2)}
                ]
            }
        ]
        
        # 调用大模型API
        response = MultiModalConversation.call(
            api_key=api_key,
            model="qwen-vl-max",
            messages=messages
        )
        
        # 解析响应
        response_text = response.output.choices[0].message.content[0]['text']
        
        # 提取JSON部分
        json_str = response_text
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        
        # 解析JSON
        result = json.loads(json_str)
        print(f"大模型评分结果: {result}")
        
        return result
    except Exception as e:
        print(f"大模型评分失败: {str(e)}")
        # 出错时返回空结果
        return {"blue_team": [], "red_team": []}

def _evaluate_player(player, team_players):
    """评估单个选手的表现"""
    # 复制选手数据
    evaluation = player.copy()
    
    # 计算KDA比率
    kills = player["stats"]["kills"]
    deaths = player["stats"]["deaths"]
    assists = player["stats"]["assists"]
    
    # 避免除以零
    if deaths == 0:
        kda_ratio = kills + assists  # 完美KDA
    else:
        kda_ratio = (kills + assists) / deaths
    
    # 计算伤害占比
    total_team_damage = sum(p["stats"]["damage"] for p in team_players)
    damage_percentage = (player["stats"]["damage"] / total_team_damage * 100) if total_team_damage > 0 else 0
    
    # 获取视野得分 (如果存在)
    sight_score = player["stats"].get("sight", 0)
    
    # 计算评分（1-5分）
    # 基础分3分
    base_score = 3.0
    
    # KDA加分/减分
    if kda_ratio >= 5:
        kda_score = 1.0
    elif kda_ratio >= 3:
        kda_score = 0.5
    elif kda_ratio <= 1:
        kda_score = -1.0
    elif kda_ratio <= 2:
        kda_score = -0.5
    else:
        kda_score = 0
    
    # 伤害占比加分/减分
    position = player["position"]
    if position in ["MID", "BOT", "ADC"]:  # 输出位置
        if damage_percentage >= 30:
            damage_score = 1.0
        elif damage_percentage >= 25:
            damage_score = 0.5
        elif damage_percentage <= 15:
            damage_score = -1.0
        elif damage_percentage <= 20:
            damage_score = -0.5
        else:
            damage_score = 0
    else:  # 非输出位置
        if damage_percentage >= 20:
            damage_score = 1.0
        elif damage_percentage >= 15:
            damage_score = 0.5
        elif damage_percentage <= 5:
            damage_score = -0.5
        else:
            damage_score = 0
    
    # 视野得分加分/减分
    # 根据位置不同，视野得分的权重不同
    sight_score_weight = 0.5  # 默认权重
    
    # 辅助位置视野得分权重更高
    if position in ["SUP", "SUPPORT"]:
        sight_score_weight = 1.0
    # 打野位置视野得分权重中等
    elif position in ["JNG", "JUNGLE"]:
        sight_score_weight = 0.75
        
    # 视野得分评估
    if sight_score >= 15:  # 视野得分很高
        sight_bonus = 0.5 * sight_score_weight
    elif sight_score >= 8:  # 视野得分中等偏上
        sight_bonus = 0.25 * sight_score_weight
    elif sight_score <= 3 and position in ["SUP", "SUPPORT", "JNG", "JUNGLE"]:  # 关键位置视野得分过低
        sight_bonus = -0.5 * sight_score_weight
    elif sight_score <= 5 and position in ["SUP", "SUPPORT"]:  # 辅助位置视野得分不达标
        sight_bonus = -0.25 * sight_score_weight
    else:
        sight_bonus = 0
    
    # 计算最终评分
    final_score = base_score + kda_score + damage_score + sight_bonus
    
    # 限制在1-5分范围内
    final_score = max(1, min(5, final_score))
    
    # 四舍五入到0.5
    final_score = round(final_score * 2) / 2
    
    # 添加评分到结果中
    evaluation["rating"] = final_score
    evaluation["kda_ratio"] = round(kda_ratio, 2)
    evaluation["damage_percentage"] = round(damage_percentage, 2)
    evaluation["sight_score"] = sight_score
    
    return evaluation 