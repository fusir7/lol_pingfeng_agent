import os
from dotenv import load_dotenv

# 加载.env文件中的环境变量（如果存在）
load_dotenv()

# 百炼API配置
BAILIAN_API_KEY = os.getenv("BAILIAN_API_KEY")  # API密钥
BAILIAN_API_URL = os.getenv("BAILIAN_API_URL", "https://bailian.aliyuncs.com/v2/app")
BAILIAN_AGENT_KEY = os.getenv("BAILIAN_AGENT_KEY")  # 应用ID

# 应用配置
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
VERBOSE_DEBUG = os.getenv("VERBOSE_DEBUG", "1")  # 详细日志级别

# Flask配置
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")  # 主机
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))  # 端口
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"  # Flask调试模式

# 上传配置
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # 允许上传的文件类型
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.getcwd(), 'uploads'))  # 上传目录
MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "16777216"))  # 16MB

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 模型配置
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "qwen-vl-max")  # 图像模型名称
TEXT_MODEL = os.getenv("TEXT_MODEL", "qwen-max")  # 文本模型名称

# LLM生成配置
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))  # 最大令牌数
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))  # 温度参数
TOP_P = float(os.getenv("TOP_P", "0.9"))  # TOP-P采样参数 