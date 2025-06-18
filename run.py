#!/usr/bin/env python
import os
import sys
import argparse
from langgraph_agent import LOLAnalysisAgent
from config import BAILIAN_API_KEY, BAILIAN_API_URL, BAILIAN_AGENT_KEY, VERBOSE_DEBUG

def main():
    """LOL选手评分系统命令行入口"""
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='LOL选手评分系统')
    parser.add_argument('image_path', help='图片路径')
    parser.add_argument('--api_key', help='百炼API密钥')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 从环境变量或命令行参数获取API密钥
    api_key = args.api_key or BAILIAN_API_KEY
    if not api_key:
        print("警告: 未设置API密钥，可能会导致API调用失败")
    
    # 分析图片
    print(f"分析图片: {args.image_path}")
    print(f"百炼API URL: {BAILIAN_API_URL}")
    print(f"百炼API密钥: {api_key[:5]}..." if api_key else "百炼API密钥未设置")
    print(f"百炼应用ID: {BAILIAN_AGENT_KEY}")
    print(f"详细日志: 已启用")
    
    # 创建分析代理
    agent = LOLAnalysisAgent(
        llm_api_url=BAILIAN_API_URL,
        llm_api_key=api_key,
        bailian_agent_key=BAILIAN_AGENT_KEY
    )
    
    # 处理图像
    result = agent.process_image(args.image_path)
    
    if "error" in result:
        print(f"错误: {result['error']}")
        return 1
        
    # 打印结果
    print("\n【蓝队选手评分】")
    for player in result.get("blue_team", []):
        print(f"选手: {player['name']} ({player['position']})")
        print(f"评分: {player['rating']}/5")
        print(f"KDA: {player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}")
        print(f"补刀: {player['stats']['cs']}")
        print(f"伤害: {player['stats']['damage']}")
        print(f"评语: {player.get('comment', '无评语')}")
        print()
    
    print("\n【红队选手评分】")
    for player in result.get("red_team", []):
        print(f"选手: {player['name']} ({player['position']})")
        print(f"评分: {player['rating']}/5")
        print(f"KDA: {player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}")
        print(f"补刀: {player['stats']['cs']}")
        print(f"伤害: {player['stats']['damage']}")
        print(f"评语: {player.get('comment', '无评语')}")
        print()
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 