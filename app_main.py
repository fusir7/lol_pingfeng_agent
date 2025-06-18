from dashscope import MultiModalConversation
from flask import Flask, request, render_template, jsonify
import os
import io
from PIL import Image
import pytesseract  # 用于OCR识别

app = Flask(__name__)

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')  # 返回你的美化后的HTML页面


@app.route('/analyze_image', methods=['POST','GET'])
def analyze_image():
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
            local_path = os.path.join(os.getcwd(), 'uploaded_image.png')
            file.save(local_path)
            image_path = f"file://{local_path}"
            messages = [{"role": "system",
                 "content": [{"text": "你是一名资深的英雄联盟赛事分析师"}]},
                {'role': 'user',
                 'content': [{'image': image_path},
                             {'text': '请根据这个图片上的数据，对场上十名选手的数据表现进行评分，满分5星，输出给出选手名字跟评分和各自一小段评语'}]}]

            response = MultiModalConversation.call(
            api_key="你自己的apikey，阿里的",
            model="qwen-vl-max",
            messages=messages
            )
            return response.output.choices[0].message.content[0]['text']
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)