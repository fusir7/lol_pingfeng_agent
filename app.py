from flask import Flask, request, render_template, jsonify, send_file
import os
import time
import tempfile
import json
from io import BytesIO
# 导入reportlab相关库
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from langgraph_agent import LOLAnalysisAgent
from config import (
    BAILIAN_API_KEY, BAILIAN_API_URL, BAILIAN_AGENT_KEY, 
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG, ALLOWED_EXTENSIONS,
    UPLOAD_FOLDER, MAX_CONTENT_LENGTH
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 尝试注册中文字体
try:
    # 尝试不同的可能路径
    possible_font_paths = [
        os.path.join(os.path.dirname(__file__), 'SimSun.ttf'),
        r'C:\Windows\Fonts\simsun.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Linux可能的路径
        # macOS中文字体路径
        '/System/Library/Fonts/PingFang.ttc',  # 苹方
        '/System/Library/Fonts/STHeiti Light.ttc',  # 华文细黑
        '/System/Library/Fonts/STHeiti Medium.ttc',  # 华文中黑
        '/Library/Fonts/Arial Unicode.ttf',  # Arial Unicode MS
        '/System/Library/Fonts/Hiragino Sans GB.ttc',  # 冬青黑体
        '~/Library/Fonts/Songti.ttc'  # 用户安装的宋体可能位置
    ]
    
    font_registered = False
    for font_path in possible_font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                print(f"成功注册中文字体: {font_path}")
                font_registered = True
                break
            except Exception as e:
                print(f"尝试注册字体 {font_path} 时出错: {str(e)}")
    
    if not font_registered:
        print("警告: 未能注册任何中文字体，PDF中的中文可能无法正确显示")
except Exception as e:
    print(f"字体注册过程中出错: {str(e)}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_image', methods=['POST', 'GET'])
def analyze_image_route():
    # 处理GET请求
    if request.method == 'GET':
        return '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>图片分析</title>
            </head>
            <body>
                <h1>上传图片进行分析</h1>
                <form method="post" enctype="multipart/form-data">
                    <input type="file" name="image" accept="image/*">
                    <input type="submit" value="提交">
                </form>
            </body>
            </html>
            '''
    
    # 处理POST请求
    if 'image' not in request.files:
        return jsonify({"error": "没有上传图片"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '没有选择图片'}), 400

    if file and allowed_file(file.filename):
        try:
            # 保存上传的图片到本地
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            local_path = os.path.join(UPLOAD_FOLDER, 'uploaded_image.png')
            file.save(local_path)
            
            # 创建分析代理
            agent = LOLAnalysisAgent(
                llm_api_url=BAILIAN_API_URL,
                llm_api_key=BAILIAN_API_KEY,
                bailian_agent_key=BAILIAN_AGENT_KEY
            )
            
            # 使用代理分析图片
            result = agent.process_image(local_path)
            
            if "error" in result:
                return jsonify({"error": result["error"]}), 500
                
            # 将结果格式化为HTML
            formatted_results = format_results(result)
            
            # 直接返回格式化后的HTML结果
            return formatted_results
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

@app.route('/export_pdf', methods=['POST'])
def export_pdf():
    """将分析结果导出为PDF"""
    try:
        # 获取提交的数据
        blue_team_data = request.form.get('blue_team_data', '[]')
        red_team_data = request.form.get('red_team_data', '[]')
        
        # 解析JSON数据
        try:
            blue_team = json.loads(blue_team_data)
            red_team = json.loads(red_team_data)
            
            # 确保评分值是数字
            for team in [blue_team, red_team]:
                for player in team:
                    if 'rating' in player:
                        try:
                            player['rating'] = float(player['rating'])
                        except (ValueError, TypeError):
                            player['rating'] = 0
        except json.JSONDecodeError:
            return jsonify({"error": "无效的JSON数据"}), 400
        
        print("蓝队数据:", blue_team)  # 调试输出
        print("红队数据:", red_team)  # 调试输出
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
            
        # 创建PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, title="LOL选手评分报告")
        
        # 使用适当的字体
        chinese_font_name = 'ChineseFont' if 'ChineseFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        
        # 添加中文支持的样式
        styles = getSampleStyleSheet()
        
        # 自定义样式
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontName=chinese_font_name,
            alignment=TA_CENTER,
            fontSize=20,
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Heading2'],
            fontName=chinese_font_name,
            fontSize=16,
            spaceAfter=10
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontName=chinese_font_name,
            fontSize=10
        )
        
        # 创建文档内容
        elements = []
        
        # 添加标题
        elements.append(Paragraph("LOL Player Analysis Report", title_style))
        elements.append(Spacer(1, 10))
        
        # 添加蓝队标题
        elements.append(Paragraph("Blue Team Player Ratings", heading_style))
        elements.append(Spacer(1, 5))
        
        # 添加蓝队数据
        for player in blue_team:
            # 获取玩家数据，使用ASCII兼容字符
            name = player.get('name', '')
            position = player.get('position', '')
            rating = float(player.get('rating', 0))  # 确保是数字
            kda = player.get('kda', '')
            cs = player.get('cs', '')
            damage = player.get('damage', '')
            sight = player.get('sight', '')
            comment = player.get('comment', '')
            
            # 创建表格数据
            data = [
                [f"{name} ({position})", f"Rating: {rating}/5"],
                ["KDA", kda],
                ["CS", cs],
                ["Damage", damage],
                ["Sight Score", sight],
                ["Comment", Paragraph(comment, normal_style)]
            ]
            
            # 创建表格
            table = Table(data, colWidths=[150, 350])
            
            # 添加表格样式
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (1, 0), chinese_font_name),
                ('FONTSIZE', (0, 0), (1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (1, 0), 5),
                ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), chinese_font_name),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 10))
        
        # 添加红队标题
        elements.append(Paragraph("Red Team Player Ratings", heading_style))
        elements.append(Spacer(1, 5))
        
        # 添加红队数据
        for player in red_team:
            # 获取玩家数据
            name = player.get('name', '')
            position = player.get('position', '')
            rating = float(player.get('rating', 0))  # 确保是数字
            kda = player.get('kda', '')
            cs = player.get('cs', '')
            damage = player.get('damage', '')
            sight = player.get('sight', '')
            comment = player.get('comment', '')
            
            # 创建表格数据
            data = [
                [f"{name} ({position})", f"Rating: {rating}/5"],
                ["KDA", kda],
                ["CS", cs],
                ["Damage", damage],
                ["Sight Score", sight],
                ["Comment", Paragraph(comment, normal_style)]
            ]
            
            # 创建表格
            table = Table(data, colWidths=[150, 350])
            
            # 添加表格样式
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.lightcoral),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (1, 0), chinese_font_name),
                ('FONTSIZE', (0, 0), (1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (1, 0), 5),
                ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), chinese_font_name),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 10))
        
        # 构建PDF
        try:
            doc.build(elements)
            
            # 保存PDF
            with open(pdf_path, 'wb') as file:
                file.write(buffer.getvalue())
            
            # 返回生成的PDF文件
            return send_file(pdf_path, as_attachment=True, download_name='lol_player_analysis.pdf')
        except Exception as e:
            print(f"构建PDF时出错: {str(e)}")
            # 如果构建失败，尝试使用不带中文的更简单方式
            return generate_simple_pdf(blue_team, red_team)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def generate_simple_pdf(blue_team, red_team):
    """生成一个简单的PDF，只使用ASCII字符，以确保生成成功"""
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
            
        # 创建PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, title="LOL Player Analysis Report")
        
        # 添加样式
        styles = getSampleStyleSheet()
        
        # 创建文档内容
        elements = []
        
        # 添加标题
        elements.append(Paragraph("LOL Player Analysis Report", styles["Title"]))
        elements.append(Spacer(1, 10))
        
        # 添加蓝队标题
        elements.append(Paragraph("Blue Team Player Ratings", styles["Heading2"]))
        elements.append(Spacer(1, 5))
        
        # 添加蓝队数据
        for player in blue_team:
            # 获取数据并确保评分是数字
            try:
                rating = float(player.get('rating', 0))
            except (ValueError, TypeError):
                rating = 0
                
            # 创建表格数据
            data = [
                [f"{player.get('name', '')} ({player.get('position', '')})", f"Rating: {rating}/5"],
                ["KDA", player.get('kda', '')],
                ["CS", player.get('cs', '')],
                ["Damage", player.get('damage', '')],
                ["Sight", player.get('sight', '')],
            ]
            
            # 创建表格
            table = Table(data, colWidths=[150, 350])
            
            # 添加表格样式
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTSIZE', (0, 0), (1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (1, 0), 5),
                ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 10))
        
        # 添加红队标题
        elements.append(Paragraph("Red Team Player Ratings", styles["Heading2"]))
        elements.append(Spacer(1, 5))
        
        # 添加红队数据
        for player in red_team:
            # 获取数据并确保评分是数字
            try:
                rating = float(player.get('rating', 0))
            except (ValueError, TypeError):
                rating = 0
                
            # 创建表格数据
            data = [
                [f"{player.get('name', '')} ({player.get('position', '')})", f"Rating: {rating}/5"],
                ["KDA", player.get('kda', '')],
                ["CS", player.get('cs', '')],
                ["Damage", player.get('damage', '')],
                ["Sight", player.get('sight', '')],
            ]
            
            # 创建表格
            table = Table(data, colWidths=[150, 350])
            
            # 添加表格样式
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.lightcoral),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.black),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTSIZE', (0, 0), (1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (1, 0), 5),
                ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 10))
        
        # 构建PDF
        doc.build(elements)
        
        # 保存PDF
        with open(pdf_path, 'wb') as file:
            file.write(buffer.getvalue())
        
        # 返回生成的PDF文件
        return send_file(pdf_path, as_attachment=True, download_name='lol_player_analysis.pdf')
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"生成简单PDF失败: {str(e)}"}), 500

def format_results(results):
    """将评分结果格式化为美观的HTML，蓝队和红队分别在独立的框内"""
    if "error" in results:
        return f'<div class="error-message">{results["error"]}</div>'
    
    # 添加CSS样式
    output = """
    <style>
        .analysis-container {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        .team-box {
            background-color: #0a1929;
            color: #e0e0e0;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
            margin-bottom: 20px;
            padding: 20px;
            border-top: 3px solid;
        }
        .blue-team {
            border-color: #3498db;
        }
        .red-team {
            border-color: #e74c3c;
        }
        .team-header {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid;
            display: flex;
            align-items: center;
        }
        .blue-header {
            border-color: #3498db;
            color: #3498db;
        }
        .red-header {
            border-color: #e74c3c;
            color: #e74c3c;
        }
        .player-card {
            background-color: #1a2a3a;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s;
        }
        .player-card:hover {
            transform: translateY(-3px);
        }
        .player-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .player-name {
            font-size: 20px;
            font-weight: bold;
        }
        .player-position {
            background-color: #2c3e50;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 14px;
        }
        .player-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 10px;
        }
        .stat-item {
            background-color: #263747;
            padding: 8px;
            border-radius: 6px;
            text-align: center;
        }
        .stat-label {
            font-size: 12px;
            color: #95a5a6;
            margin-bottom: 3px;
        }
        .stat-value {
            font-size: 16px;
            font-weight: bold;
        }
        .rating {
            color: gold;
            font-size: 24px;
            letter-spacing: 2px;
        }
        .comment {
            margin-top: 10px;
            padding: 15px;
            background-color: #263747;
            border-radius: 6px;
            line-height: 1.6;
        }
        .comment-title {
            color: #3498db;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 14px;
            border-bottom: 1px solid rgba(52, 152, 219, 0.3);
            padding-bottom: 5px;
        }
        .comment-content {
            font-style: italic;
            color: #e0e0e0;
            text-align: justify;
        }
        .team-icon {
            margin-right: 10px;
            font-size: 24px;
        }
        .analysis-title {
            text-align: center;
            color: #e0e0e0;
            margin-bottom: 20px;
            font-size: 28px;
            font-weight: bold;
        }
        .gold-star {
            color: gold;
        }
    </style>
    <div class="analysis-container">
        <h1 class="analysis-title">
            <span class="gold-star">★</span> 英雄联盟选手评分分析 <span class="gold-star">★</span>
        </h1>
    """
    
    # 蓝队结果 - 独立框
    output += '<div class="team-box blue-team">'
    output += '<div class="team-header blue-header"><span class="team-icon">🔵</span>蓝队选手评分</div>'
    
    for player in results.get("blue_team", []):
        # 格式化星级评分
        stars = "★" * int(player["rating"])
        if player["rating"] % 1 == 0.5:
            stars += "☆"
            
        output += f'''
        <div class="player-card">
            <div class="player-header">
                <div class="player-name">{player['name']}</div>
                <div class="player-position">{get_position_name(player['position'])}</div>
            </div>
            <div class="rating">{stars}</div>
            <div class="player-stats">
                <div class="stat-item">
                    <div class="stat-label">KDA</div>
                    <div class="stat-value">{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">补刀</div>
                    <div class="stat-value">{player['stats']['cs']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">伤害</div>
                    <div class="stat-value">{player['stats']['damage']:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">视野</div>
                    <div class="stat-value">{player['stats'].get('sight', 0)}</div>
                </div>
            </div>
            <div class="comment">
                <div class="comment-title">解说评价</div>
                <div class="comment-content">{player.get('comment', '无评语')}</div>
            </div>
        </div>
        '''
    
    output += '</div>'  # 结束蓝队框
    
    # 红队结果 - 独立框
    output += '<div class="team-box red-team">'
    output += '<div class="team-header red-header"><span class="team-icon">🔴</span>红队选手评分</div>'
    
    for player in results.get("red_team", []):
        # 格式化星级评分
        stars = "★" * int(player["rating"])
        if player["rating"] % 1 == 0.5:
            stars += "☆"
            
        output += f'''
        <div class="player-card">
            <div class="player-header">
                <div class="player-name">{player['name']}</div>
                <div class="player-position">{get_position_name(player['position'])}</div>
            </div>
            <div class="rating">{stars}</div>
            <div class="player-stats">
                <div class="stat-item">
                    <div class="stat-label">KDA</div>
                    <div class="stat-value">{player['stats']['kills']}/{player['stats']['deaths']}/{player['stats']['assists']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">补刀</div>
                    <div class="stat-value">{player['stats']['cs']}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">伤害</div>
                    <div class="stat-value">{player['stats']['damage']:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">视野</div>
                    <div class="stat-value">{player['stats'].get('sight', 0)}</div>
                </div>
            </div>
            <div class="comment">
                <div class="comment-title">解说评价</div>
                <div class="comment-content">{player.get('comment', '无评语')}</div>
            </div>
        </div>
        '''
    
    output += '</div>'  # 结束红队框
    output += '</div>'  # 结束分析容器
    return output

def get_position_name(position):
    """转换位置为中文名称"""
    positions = {
        'TOP': '上单',
        'JUNGLE': '打野',
        'JNG': '打野',
        'MID': '中单',
        'BOT': 'ADC',
        'ADC': 'ADC',
        'SUP': '辅助',
        'SUPPORT': '辅助'
    }
    return positions.get(position, position)

if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG) 