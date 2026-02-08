import json
import logging
import os
from typing import List, Optional
import urllib.request
from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
try:
    from langchain_qwq import ChatQwQ, ChatQwen
except Exception:
    ChatQwQ = None
    ChatQwen = None
import random
import time
from dotenv import load_dotenv

# 加载 .env 文件
# 尝试在当前目录和上级目录寻找 .env
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

MODELSCOPE_API_KEY_LIST = os.getenv("MODELSCOPE_API_KEYS", "").split(",")
# 过滤掉空字符串
MODELSCOPE_API_KEY_LIST = [key for key in MODELSCOPE_API_KEY_LIST if key]

SiliconFlow_API_KEY_LIST = os.getenv("SILICONFLOW_API_KEYS", "").split(",")
# 过滤掉空字符串
SiliconFlow_API_KEY_LIST = [key for key in SiliconFlow_API_KEY_LIST if key]

def setup_logger(name: Optional[str] = None, log_file: Optional[str] = None, level=logging.INFO, console_output: bool = True, clear_existing: bool = False):
    """设置 Logger，支持输出到控制台和文件"""
    # 如果没有提供名字，或者名字为空，则配置根日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 如果要求清除现有 Handler
    if clear_existing:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # 防止重复添加 Handler
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 控制台 Handler
        if console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # 文件 Handler
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
    return logger

def _normalize_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return base_url
    # Most LangChain OpenAI-compatible clients expect a trailing slash, e.g. ".../v1/".
    return base_url if base_url.endswith("/") else base_url + "/"


def get_model_from_name(
    model: str = MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    late_time: float = 3.0,
    **kwargs,
):
    if "instruct" in model.lower():
        return llm_qwen(model=model, api_key=api_key, base_url=base_url, late_time=late_time, **kwargs)
    elif "thinking" in model.lower():
        return llm_qwq(model=model, api_key=api_key, base_url=base_url, late_time=late_time, **kwargs)
    else:
        return llm_modelscope(model=model, api_key=api_key, base_url=base_url, late_time=late_time, **kwargs)

def llm_qwq(model: str = MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    late_time: float = 3.0,
    **kwargs,
):
    if ChatQwQ is None:
        raise RuntimeError("Missing dependency: langchain-qwq. Install with pip install -e .[qwq]")
    if not api_key:
        api_key = random.choice(MODELSCOPE_API_KEY_LIST)
    if not base_url:
        base_url = "https://api-inference.modelscope.cn/v1/"
    base_url = _normalize_base_url(base_url)
    time.sleep(late_time)
    
    # 默认开启Thinking
    model_think = ChatQwQ(
        model = model,
        base_url = base_url,
        api_key = api_key,
        **kwargs,
    )
    
    return model_think

def llm_qwen(
    model: str = MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    late_time: float = 3.0,
    **kwargs,
):
    if ChatQwen is None:
        raise RuntimeError("Missing dependency: langchain-qwq. Install with pip install -e .[qwq]")
    if not api_key:
        api_key = random.choice(MODELSCOPE_API_KEY_LIST)
    if not base_url:
        base_url = "https://api-inference.modelscope.cn/v1/"
    base_url = _normalize_base_url(base_url)
    time.sleep(late_time)
    
    # 确保 enable_thinking 在非流式调用下为 False
    if 'enable_thinking' not in kwargs:
        kwargs['enable_thinking'] = False
        
    model_think = ChatQwen(
        model=model,
        base_url=base_url,
        api_key=api_key,
        **kwargs,
    )
    
    return model_think

def llm_modelscope(
    model: str = MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    late_time: float = 3.0,
    **kwargs,
):
    if not api_key:
        api_key = random.choice(MODELSCOPE_API_KEY_LIST)
    if not base_url:
        base_url = "https://api-inference.modelscope.cn/v1/"
    base_url = _normalize_base_url(base_url)
    time.sleep(late_time)
    
    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )
    
    return llm

def llm_siliconflow(
    model: str = MODEL,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    late_time: float = 3.0,
    **kwargs,
):
    if not api_key:
        api_key = random.choice(SiliconFlow_API_KEY_LIST)
    if not base_url:
        base_url = "https://api.siliconflow.cn/v1/"
    base_url = _normalize_base_url(base_url)
    time.sleep(late_time)
    
    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        **kwargs,
    )
    return llm


import re

def md2txt(md_text: str) -> str:
    """
    将Markdown文本转换为纯文本
    
    Args:
        md_text: 包含Markdown格式的文本
        
    Returns:
        转换后的纯文本
    """
    # 移除代码块 (```code```)
    plain_text = re.sub(r'```.*?```', '', md_text, flags=re.DOTALL)
    
    # 移除行内代码 (`code`)
    plain_text = re.sub(r'`(.*?)`', r'\1', plain_text)
    
    # 移除标题标记 (#, ##, ### 等)
    plain_text = re.sub(r'^#+\s*', '', plain_text, flags=re.MULTILINE)
    
    # 移除粗体标记 (**text** 或 __text__)
    plain_text = re.sub(r'\*\*(.*?)\*\*|__(.*?)__', r'\1\2', plain_text)
    
    # 移除斜体标记 (*text* 或 _text_)
    plain_text = re.sub(r'\*(.*?)\*|_(.*?)_', r'\1\2', plain_text)
    
    # 移除链接和图片
    # 先处理图片 (![alt](url))
    plain_text = re.sub(r'!\[.*?\]\(.*?\)', '', plain_text)
    # 再处理链接 ([text](url))
    plain_text = re.sub(r'\[.*?\]\(.*?\)', '', plain_text)
    
    # 移除引用标记 (>)
    plain_text = re.sub(r'^>\s*', '', plain_text, flags=re.MULTILINE)
    
    # 移除列表标记 (- *, + 或数字.)
    plain_text = re.sub(r'^\s*[-*+]\s*', '', plain_text, flags=re.MULTILINE)
    plain_text = re.sub(r'^\s*\d+\.\s*', '', plain_text, flags=re.MULTILINE)
    
    # 移除水平线 (---, *** 或 ___)
    plain_text = re.sub(r'^[-*_]{3,}$', '', plain_text, flags=re.MULTILINE)
    
    # 移除表格格式
    # 首先移除表格分隔线
    plain_text = re.sub(r'^[-:|\s]+$', '', plain_text, flags=re.MULTILINE)
    # 然后移除表格行
    plain_text = re.sub(r'^\|.*?\|$', '', plain_text, flags=re.MULTILINE)
    
    # 移除多余的空白行
    plain_text = '\n'.join(line.strip() for line in plain_text.splitlines() if line.strip())
    
    return plain_text


class SiliconFlowEmbeddings(BaseModel, Embeddings):
    """硅基流动词向量模型适配器"""
    
    model: str = Field(default="BAAI/bge-m3", description="要使用的模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    base_url: str = Field(default="https://api.siliconflow.cn/v1/embeddings", description="API的基础URL")
    batch_size: int = Field(default=4, description="每批处理的文本数量")
    
    def get_api_key(self):
        if not self.api_key:
            self.api_key = random.choice(SiliconFlow_API_KEY_LIST)
        
        return self.api_key

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """为多个文本生成嵌入向量，支持批量处理"""
        all_embeddings = []
        
        # 分批处理文本
        n = len(texts)
        for i in range(0, n, self.batch_size):
            batch_texts = texts[i:min(i + self.batch_size, n)]
            
            # 硅基流API的请求头
            headers = {
                "Authorization": f"Bearer {self.get_api_key()}",
                "Content-Type": "application/json"
            }
            
            # 构造请求数据
            data = {
                "model": self.model,
                "input": batch_texts,
                "encoding_format": "float"
            }
            
            # 发送POST请求
            request = urllib.request.Request(
                self.base_url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers
            )
            
            try:
                with urllib.request.urlopen(request) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    # 收集嵌入向量
                    all_embeddings.extend([item['embedding'] for item in result['data']])
            except Exception as e:
                print(f"总共{n}条文本，处理第{i}到{min(i + self.batch_size, n)}条文本时出错: {str(e)}")
                for idx in range(i, min(i + self.batch_size, n)):
                    print(idx, texts[idx])
                raise Exception(f"请求硅基流API时出错: {str(e)}")
        
        return all_embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """为单个文本生成嵌入向量"""
        # 对于单个文本，我们仍然使用embed_documents方法
        return self.embed_documents([text])[0]
