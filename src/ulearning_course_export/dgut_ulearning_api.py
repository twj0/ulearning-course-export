"""
东莞理工学院优学院API模块 - 支持新旧API兼容性
该模块提供了对东莞理工学院优学院平台新旧API的统一接口，支持自动切换和兼容性处理
"""

import requests
import json
import os
from typing import Dict, List, Optional, Union, Any
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class DGUTUlearningAPI:
    """东莞理工学院优学院API类，支持新旧API兼容性"""
    
    def __init__(self, base_url: str = None, authorization_token: str = None, 
                 ua_authorization_token: str = None, api_version: str = "auto"):
        """
        初始化API客户端
        
        Args:
            base_url: API基础URL
            authorization_token: 授权令牌
            ua_authorization_token: UA授权令牌
            api_version: API版本，可选值为 "auto"(自动检测), "v1"(旧版), "v2"(新版)
        """
        self.base_url = base_url or os.getenv("BASE_API_URL", "https://ua.dgut.edu.cn")
        self.authorization_token = authorization_token or os.getenv("AUTHORIZATION_TOKEN")
        self.ua_authorization_token = ua_authorization_token or os.getenv("UA_AUTHORIZATION_TOKEN", "18016158863D724D29B3334BD9853C36")
        self.api_version = api_version
        self.session = requests.Session()
        
        # 设置默认请求头
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "authorization": self.authorization_token,
            "ua-authorization": self.ua_authorization_token,
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/"
        })
        
        # API端点映射 - 支持新旧版本
        self.api_endpoints = {
            "v1": {
                "course_directory": "/learnCourse/courseDirectory",
                "chapter_content": "/learnCourse/getWholeChapterPageContent",
                "question_answer": "/learnQuestion/getQuestionAnswer",
                "user_info": "/usercenter/user/getUserBasicInfo",
                "course_remaining": "/learnCourse/getCourseRemainingTime",
                "study_record": "/learnCourse/getUserStudyRecord",
                "study_heartbeat": "/learnCourse/saveUserLearnHeartbeat",
                "sync_personal_data": "/usercenter/user/syncPersonalData"
            },
            "v2": {
                "course_directory": "/api/v2/learnCourse/courseDirectory",
                "chapter_content": "/api/v2/learnCourse/getWholeChapterPageContent",
                "question_answer": "/api/v2/learnQuestion/getQuestionAnswer",
                "user_info": "/api/v2/usercenter/user/getUserBasicInfo",
                "course_remaining": "/api/v2/learnCourse/getCourseRemainingTime",
                "study_record": "/api/v2/learnCourse/getUserStudyRecord",
                "study_heartbeat": "/api/v2/learnCourse/saveUserLearnHeartbeat",
                "sync_personal_data": "/api/v2/usercenter/user/syncPersonalData"
            }
        }
    
    def _get_endpoint(self, endpoint_name: str) -> str:
        """
        获取API端点URL
        
        Args:
            endpoint_name: 端点名称
            
        Returns:
            完整的API端点URL
        """
        if self.api_version == "auto":
            # 自动检测API版本，先尝试v2，失败则尝试v1
            return self._try_endpoint_with_fallback(endpoint_name)
        else:
            # 使用指定版本
            version = self.api_version
            endpoint_path = self.api_endpoints.get(version, {}).get(endpoint_name)
            if not endpoint_path:
                raise ValueError(f"未找到端点 {endpoint_name} 在API版本 {version} 中")
            return f"{self.base_url}{endpoint_path}"
    
    def _try_endpoint_with_fallback(self, endpoint_name: str) -> str:
        """
        尝试使用v2 API，如果失败则回退到v1
        
        Args:
            endpoint_name: 端点名称
            
        Returns:
            可用的API端点URL
        """
        # 先尝试v2
        v2_path = self.api_endpoints.get("v2", {}).get(endpoint_name)
        if v2_path:
            v2_url = f"{self.base_url}{v2_path}"
            # 这里可以添加一个简单的健康检查
            if self._check_endpoint_health(v2_url):
                return v2_url
        
        # 回退到v1
        v1_path = self.api_endpoints.get("v1", {}).get(endpoint_name)
        if v1_path:
            return f"{self.base_url}{v1_path}"
        
        raise ValueError(f"未找到端点 {endpoint_name}")
    
    def _check_endpoint_health(self, url: str) -> bool:
        """
        检查API端点是否健康可用
        
        Args:
            url: API端点URL
            
        Returns:
            端点是否可用
        """
        try:
            # 发送一个简单的OPTIONS请求检查端点
            response = self.session.options(url, timeout=5)
            return response.status_code in [200, 204, 405]  # 405 Method Not Allowed也算可用
        except:
            return False
    
    def _make_request(self, method: str, endpoint_name: str, **kwargs) -> Optional[Dict]:
        """
        发送API请求
        
        Args:
            method: HTTP方法
            endpoint_name: 端点名称
            **kwargs: 请求参数
            
        Returns:
            API响应数据
        """
        url = self._get_endpoint(endpoint_name)
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=kwargs, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=kwargs, timeout=30)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            response.raise_for_status()
            
            # 尝试解析JSON响应
            try:
                return response.json()
            except json.JSONDecodeError:
                return {"data": response.text, "status_code": response.status_code}
                
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {e}")
            return None
    
    def _handle_response(self, response: Dict) -> Dict:
        """
        处理API响应，统一格式
        
        Args:
            response: 原始API响应
            
        Returns:
            统一格式的响应数据
        """
        if not response:
            return {"success": False, "message": "API请求失败", "data": None}
        
        # 检查响应格式并统一处理
        if "code" in response:
            # 新版API格式
            if response["code"] == 200:
                return {"success": True, "message": "请求成功", "data": response.get("data")}
            else:
                return {"success": False, "message": response.get("message", "请求失败"), "data": None}
        elif "success" in response:
            # 旧版API格式
            if response["success"]:
                return {"success": True, "message": "请求成功", "data": response.get("data")}
            else:
                return {"success": False, "message": response.get("message", "请求失败"), "data": None}
        else:
            # 直接返回数据
            return {"success": True, "message": "请求成功", "data": response}
    
    def get_course_directory(self, course_id: str, class_id: str) -> Optional[Dict]:
        """
        获取课程目录
        
        Args:
            course_id: 课程ID
            class_id: 班级ID
            
        Returns:
            课程目录数据
        """
        response = self._make_request("POST", "course_directory", 
                                    courseId=course_id, classId=class_id)
        return self._handle_response(response)
    
    def get_whole_chapter_page_content(self, node_id: str) -> Optional[Dict]:
        """
        获取整个章节页面内容
        
        Args:
            node_id: 节点ID
            
        Returns:
            章节内容数据
        """
        response = self._make_request("POST", "chapter_content", nodeId=node_id)
        return self._handle_response(response)
    
    def get_question_answer(self, question_id: str, parent_id: str) -> Optional[Dict]:
        """
        获取题目答案
        
        Args:
            question_id: 题目ID
            parent_id: 父级ID
            
        Returns:
            题目答案数据
        """
        response = self._make_request("POST", "question_answer", 
                                    questionId=question_id, parentId=parent_id)
        return self._handle_response(response)
    
    def get_user_info(self) -> Optional[Dict]:
        """
        获取用户信息
        
        Returns:
            用户信息数据
        """
        response = self._make_request("GET", "user_info")
        return self._handle_response(response)
    
    def get_course_remaining(self, course_id: str, class_id: str) -> Optional[Dict]:
        """
        获取课程剩余时间
        
        Args:
            course_id: 课程ID
            class_id: 班级ID
            
        Returns:
            课程剩余时间数据
        """
        response = self._make_request("POST", "course_remaining", 
                                    courseId=course_id, classId=class_id)
        return self._handle_response(response)
    
    def get_study_record(self, course_id: str, class_id: str) -> Optional[Dict]:
        """
        获取学习记录
        
        Args:
            course_id: 课程ID
            class_id: 班级ID
            
        Returns:
            学习记录数据
        """
        response = self._make_request("POST", "study_record", 
                                    courseId=course_id, classId=class_id)
        return self._handle_response(response)
    
    def send_study_heartbeat(self, course_id: str, class_id: str, node_id: str, 
                           current_time: int = None) -> Optional[Dict]:
        """
        发送学习心跳
        
        Args:
            course_id: 课程ID
            class_id: 班级ID
            node_id: 节点ID
            current_time: 当前时间戳
            
        Returns:
            心跳发送结果
        """
        if current_time is None:
            import time
            current_time = int(time.time() * 1000)
            
        response = self._make_request("POST", "study_heartbeat", 
                                    courseId=course_id, classId=class_id, 
                                    nodeId=node_id, currentTime=current_time)
        return self._handle_response(response)
    
    def sync_personal_data(self) -> Optional[Dict]:
        """
        同步个人数据
        
        Returns:
            同步结果
        """
        response = self._make_request("POST", "sync_personal_data")
        return self._handle_response(response)


# 创建全局API实例
dgut_api = DGUTUlearningAPI()

# 向后兼容的函数接口
def get_course_directory(course_id: str, class_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的课程目录获取函数"""
    response = dgut_api.get_course_directory(course_id, class_id)
    return response.get("data") if response and response.get("success") else None

def get_whole_chapter_page_content(node_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的章节内容获取函数"""
    response = dgut_api.get_whole_chapter_page_content(node_id)
    return response.get("data") if response and response.get("success") else None

def get_question_answer(question_id: str, parent_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的题目答案获取函数"""
    response = dgut_api.get_question_answer(question_id, parent_id)
    return response.get("data") if response and response.get("success") else None

def get_user_info(headers: Dict = None) -> Optional[Dict]:
    """向后兼容的用户信息获取函数"""
    response = dgut_api.get_user_info()
    return response.get("data") if response and response.get("success") else None

def get_course_remaining(course_id: str, class_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的课程剩余时间获取函数"""
    response = dgut_api.get_course_remaining(course_id, class_id)
    return response.get("data") if response and response.get("success") else None

def get_study_record(course_id: str, class_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的学习记录获取函数"""
    response = dgut_api.get_study_record(course_id, class_id)
    return response.get("data") if response and response.get("success") else None

def send_study_heartbeat(course_id: str, class_id: str, node_id: str, 
                       current_time: int = None, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的学习心跳发送函数"""
    response = dgut_api.send_study_heartbeat(course_id, class_id, node_id, current_time)
    return response.get("data") if response and response.get("success") else None

def sync_personal_data(headers: Dict = None) -> Optional[Dict]:
    """向后兼容的个人数据同步函数"""
    response = dgut_api.sync_personal_data()
    return response.get("data") if response and response.get("success") else None