# LOL选手评分系统

这是一个基于图像识别和大语言模型的LOL（英雄联盟）选手评分系统，可以从比赛截图中提取选手数据，计算评分，并生成专业评语。支持将分析结果导出为PDF格式。

## 系统架构

系统采用清晰的三节点流程架构：

1. **数据提取节点**：从图片中提取选手数据（KDA、补刀、伤害等）
2. **评分计算节点**：根据提取的数据计算选手评分
3. **评语生成节点**：使用大语言模型生成专业评语
4. **结果导出功能**：支持将分析结果导出为PDF文件

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/lol_pingfeng_agent.git
cd lol_pingfeng_agent
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 设置环境变量：
```bash
# Linux/Mac
export BAILIAN_API_KEY="你的百炼API密钥"

# Windows
set BAILIAN_API_KEY=你的百炼API密钥
```

## 使用方法

### 命令行方式

```bash
python run.py data.png
```

### Web应用方式

```bash
python app.py
```

然后在浏览器中访问 http://localhost:5000

### PDF导出功能

在Web界面中分析完成后，点击"导出PDF"按钮，可将选手评分报告保存为PDF文件，方便分享和存档。

## 核心文件说明

- `langgraph_agent.py`: 核心处理模块，包含三个主要节点和辅助函数
- `run.py`: 命令行入口
- `app.py`: Web应用入口
- `requirements.txt`: 依赖项列表
- `nodes/`: 节点实现目录
  - `extract_data.py`: 数据提取节点
  - `calculate_scores.py`: 评分计算节点
  - `generate_comments.py`: 评语生成节点

## API密钥

系统使用阿里云百炼平台的API，需要设置以下环境变量：

- `BAILIAN_API_KEY`: 百炼API密钥

## 示例输出

```
【蓝队选手评分】
选手: AL Flandre (TOP)
评分: 4.0/5
KDA: 2/1/5
补刀: 300
伤害: 14217
评语: Flandre在上路展现出色表现，2/1/5的KDA体现了他的稳健与团队贡献。300的补刀数量领先，伤害输出可观，是团队的重要支柱。

...

【红队选手评分】
选手: BLG Bin (TOP)
评分: 3.0/5
KDA: 0/2/1
补刀: 290
伤害: 12769
评语: Bin上路面对压力，虽0/2/1的KDA不佳，但290的补刀和12769的伤害显示了他在劣势下的坚韧与输出能力。
...
```

## 许可证

MIT
