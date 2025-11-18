"""
优学院API更新模块
处理与优学院系统新版本的API交互
"""

import requests
import json
import os
from dotenv import load_dotenv
from urllib.parse import urljoin

# 加载环境变量
load_dotenv()

# API配置
COURSE_ID = os.getenv("COURSE_ID")
CLASS_ID = os.getenv("CLASS_ID")
AUTHORIZATION_TOKEN = os.getenv("AUTHORIZATION_TOKEN")
UA_AUTHORIZATION_TOKEN = os.getenv("UA_AUTHORIZATION_TOKEN", "18016158863D724D29B3334BD9853C36")  # 从network.txt中获取的值

# API基础URL - 更新为新系统的URL
BASE_API_URL = os.getenv("BASE_API_URL", "https://ua.dgut.edu.cn")
API_PREFIX = "/uaapi"  # 新API前缀

# 请求头配置
API_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "zh",
    "authorization": AUTHORIZATION_TOKEN,
    "content-type": "application/json",
    "origin": "https://ua.ulearning.cn", 
    "referer": "https://ua.ulearning.cn/", 
    "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "ua-authorization": UA_AUTHORIZATION_TOKEN,  # 使用专门的ua-authorization
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
}

# 图片下载请求头
IMAGE_DOWNLOAD_HEADERS = { 
    "User-Agent": API_HEADERS["user-agent"]
}

class UlearningAPI:
    """优学院API交互类"""
    
    def __init__(self, base_url=None, headers=None):
        self.base_url = base_url or BASE_API_URL
        self.headers = headers or API_HEADERS
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def _make_request(self, method, endpoint, params=None, data=None, timeout=15):
        """通用请求方法"""
        url = urljoin(self.base_url, endpoint)
        print(f"Making {method} request to: {url}")
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text[:500]}")
            return None
        except Exception as e:
            print(f"Request failed: {e}")
            return None
    
    def get_course_directory(self, course_id, class_id):
        """获取课程目录 - 更新API路径"""
        # 尝试新API路径
        endpoint = f"{API_PREFIX}/course/{course_id}/directory?classId={class_id}"
        result = self._make_request('GET', endpoint)
        
        # 如果新API失败，尝试旧API路径
        if not result:
            print("New API failed, trying old API path...")
            endpoint = f"/course/stu/{course_id}/directory?classId={class_id}"
            result = self._make_request('GET', endpoint)
        
        return result
    
    def get_course_remaining(self, course_id):
        """获取课程剩余内容 - 新API"""
        endpoint = f"{API_PREFIX}/course/{course_id}/remaining"
        return self._make_request('GET', endpoint)
    
    def get_user_info(self):
        """获取用户信息 - 新API"""
        endpoint = f"{API_PREFIX}/user"
        return self._make_request('GET', endpoint)
    
    def get_whole_chapter_page_content(self, node_id):
        """获取章节内容 - 更新API路径"""
        # 尝试新API路径
        endpoint = f"{API_PREFIX}/wholepage/chapter/stu/{node_id}"
        result = self._make_request('GET', endpoint, timeout=20)
        
        # 如果新API失败，尝试旧API路径
        if not result:
            print("New API failed, trying old API path...")
            endpoint = f"/wholepage/chapter/stu/{node_id}"
            result = self._make_request('GET', endpoint, timeout=20)
        
        return result
    
    def get_question_answer(self, question_id, parent_id):
        """获取题目答案 - 更新API路径"""
        # 尝试新API路径
        endpoint = f"{API_PREFIX}/questionAnswer/{question_id}?parentId={parent_id}"
        result = self._make_request('GET', endpoint, timeout=10)
        
        # 如果新API失败，尝试旧API路径
        if not result:
            print("New API failed, trying old API path...")
            endpoint = f"/questionAnswer/{question_id}?parentId={parent_id}"
            result = self._make_request('GET', endpoint, timeout=10)
        
        return result
    
    def get_study_record(self, record_id):
        """获取学习记录 - 新API"""
        endpoint = f"{API_PREFIX}/studyrecord/item/{record_id}"
        return self._make_request('GET', endpoint)
    
    def send_study_heartbeat(self, record_id, timestamp):
        """发送学习心跳 - 新API"""
        endpoint = f"{API_PREFIX}/studyrecord/heartbeat/{record_id}/{timestamp}"
        return self._make_request('GET', endpoint)
    
    def sync_personal_data(self, encrypted_data):
        """同步个人数据 - 新API"""
        endpoint = f"{API_PREFIX}/yws/api/personal/sync"
        return self._make_request('POST', endpoint, data=encrypted_data)

# 创建全局API实例
api = UlearningAPI()

# 向后兼容的函数，保持与原代码的接口一致
def get_course_directory(course_id, class_id):
    """向后兼容的课程目录获取函数"""
    return api.get_course_directory(course_id, class_id)

def get_whole_chapter_page_content(node_id):
    """向后兼容的章节内容获取函数"""
    return api.get_whole_chapter_page_content(node_id)

def get_question_answer(question_id, parent_id):
    """向后兼容的题目答案获取函数"""
    return api.get_question_answer(question_id, parent_id)

# 新增的API函数
def get_user_info():
    """获取用户信息"""
    return api.get_user_info()

def get_course_remaining(course_id):
    """获取课程剩余内容"""
    return api.get_course_remaining(course_id)

def get_study_record(record_id):
    """获取学习记录"""
    return api.get_study_record(record_id)

def send_study_heartbeat(record_id, timestamp):
    """发送学习心跳"""
    return api.send_study_heartbeat(record_id, timestamp)

def sync_personal_data(encrypted_data):
    """同步个人数据"""
    return api.sync_personal_data(encrypted_data)