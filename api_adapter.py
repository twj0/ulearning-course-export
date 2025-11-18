"""
API适配器模块 - 处理新旧API之间的兼容性和转换
该模块提供了一个适配器层，用于统一处理新旧API之间的差异，确保上层应用无需关心底层API的变化
"""

import os
import json
from typing import Dict, List, Optional, Any, Union
from dgut_ulearning_api import DGUTUlearningAPI
from ulearning_api import UlearningAPI


class APIAdapter:
    """API适配器类，用于统一处理新旧API之间的差异"""
    
    def __init__(self, api_version: str = "auto"):
        """
        初始化API适配器
        
        Args:
            api_version: API版本，可选值为 "auto"(自动检测), "old"(旧版), "new"(新版)
        """
        self.api_version = api_version
        self.old_api = UlearningAPI()
        self.new_api = DGUTUlearningAPI(api_version="v2" if api_version == "new" else "auto")
        self.current_api = None
        
        # 自动检测并选择最佳API
        if api_version == "auto":
            self._detect_best_api()
        elif api_version == "old":
            self.current_api = self.old_api
        elif api_version == "new":
            self.current_api = self.new_api
        else:
            raise ValueError(f"不支持的API版本: {api_version}")
    
    def _detect_best_api(self):
        """自动检测并选择最佳API"""
        # 尝试使用新API获取用户信息
        try:
            user_info = self.new_api.get_user_info()
            if user_info and user_info.get("success"):
                self.current_api = self.new_api
                print("检测到新API可用，使用新API")
            else:
                self.current_api = self.old_api
                print("新API不可用，回退到旧API")
        except Exception as e:
            print(f"检测新API失败: {e}，回退到旧API")
            self.current_api = self.old_api
    
    def _convert_response_format(self, response: Dict, api_type: str) -> Dict:
        """
        转换响应格式为统一格式
        
        Args:
            response: 原始响应
            api_type: API类型 ("old" 或 "new")
            
        Returns:
            统一格式的响应
        """
        if not response:
            return {"success": False, "message": "API请求失败", "data": None}
        
        # 新API已经返回统一格式，直接返回
        if api_type == "new":
            return response
        
        # 旧API需要转换格式
        if isinstance(response, dict):
            if "data" in response:
                return {"success": True, "message": "请求成功", "data": response["data"]}
            else:
                return {"success": True, "message": "请求成功", "data": response}
        else:
            return {"success": True, "message": "请求成功", "data": response}
    
    def get_course_directory(self, course_id: str, class_id: str) -> Optional[Dict]:
        """
        获取课程目录
        
        Args:
            course_id: 课程ID
            class_id: 班级ID
            
        Returns:
            统一格式的课程目录数据
        """
        if self.current_api == self.new_api:
            try:
                response = self.new_api.get_course_directory(course_id, class_id)
                # 如果新API返回404或其他错误，自动切换到旧API
                if not response or not response.get("success"):
                    print("新API获取课程目录失败，自动切换到旧API")
                    self.current_api = self.old_api
                    response = self.old_api.get_course_directory(course_id, class_id)
                    return self._convert_response_format(response, "old")
                return self._convert_response_format(response, "new")
            except Exception as e:
                print(f"新API获取课程目录异常: {e}，自动切换到旧API")
                self.current_api = self.old_api
                response = self.old_api.get_course_directory(course_id, class_id)
                return self._convert_response_format(response, "old")
        else:
            response = self.old_api.get_course_directory(course_id, class_id)
            return self._convert_response_format(response, "old")
    
    def get_whole_chapter_page_content(self, node_id: str) -> Optional[Dict]:
        """
        获取整个章节页面内容
        
        Args:
            node_id: 节点ID
            
        Returns:
            统一格式的章节内容数据
        """
        if self.current_api == self.new_api:
            try:
                response = self.new_api.get_whole_chapter_page_content(node_id)
                # 如果新API返回404或其他错误，自动切换到旧API
                if not response or not response.get("success"):
                    print("新API获取章节内容失败，自动切换到旧API")
                    self.current_api = self.old_api
                    response = self.old_api.get_whole_chapter_page_content(node_id)
                    return self._convert_response_format(response, "old")
                return self._convert_response_format(response, "new")
            except Exception as e:
                print(f"新API获取章节内容异常: {e}，自动切换到旧API")
                self.current_api = self.old_api
                response = self.old_api.get_whole_chapter_page_content(node_id)
                return self._convert_response_format(response, "old")
        else:
            response = self.old_api.get_whole_chapter_page_content(node_id)
            return self._convert_response_format(response, "old")
    
    def get_question_answer(self, question_id: str, parent_id: str) -> Optional[Dict]:
        """
        获取题目答案
        
        Args:
            question_id: 题目ID
            parent_id: 父级ID
            
        Returns:
            统一格式的题目答案数据
        """
        if self.current_api == self.new_api:
            response = self.new_api.get_question_answer(question_id, parent_id)
            return self._convert_response_format(response, "new")
        else:
            response = self.old_api.get_question_answer(question_id, parent_id)
            return self._convert_response_format(response, "old")
    
    def get_user_info(self) -> Optional[Dict]:
        """
        获取用户信息
        
        Returns:
            统一格式的用户信息数据
        """
        if self.current_api == self.new_api:
            try:
                response = self.new_api.get_user_info()
                # 如果新API返回404或其他错误，自动切换到旧API
                if not response or not response.get("success"):
                    print("新API获取用户信息失败，自动切换到旧API")
                    self.current_api = self.old_api
                    response = self.old_api.get_user_info()
                    return self._convert_response_format(response, "old")
                return self._convert_response_format(response, "new")
            except Exception as e:
                print(f"新API获取用户信息异常: {e}，自动切换到旧API")
                self.current_api = self.old_api
                response = self.old_api.get_user_info()
                return self._convert_response_format(response, "old")
        else:
            response = self.old_api.get_user_info()
            return self._convert_response_format(response, "old")
    
    def get_course_remaining(self, course_id: str, class_id: str) -> Optional[Dict]:
        """
        获取课程剩余时间
        
        Args:
            course_id: 课程ID
            class_id: 班级ID
            
        Returns:
            统一格式的课程剩余时间数据
        """
        if self.current_api == self.new_api:
            response = self.new_api.get_course_remaining(course_id, class_id)
            return self._convert_response_format(response, "new")
        else:
            response = self.old_api.get_course_remaining(course_id, class_id)
            return self._convert_response_format(response, "old")
    
    def get_study_record(self, course_id: str, class_id: str) -> Optional[Dict]:
        """
        获取学习记录
        
        Args:
            course_id: 课程ID
            class_id: 班级ID
            
        Returns:
            统一格式的学习记录数据
        """
        if self.current_api == self.new_api:
            response = self.new_api.get_study_record(course_id, class_id)
            return self._convert_response_format(response, "new")
        else:
            response = self.old_api.get_study_record(course_id, class_id)
            return self._convert_response_format(response, "old")
    
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
            统一格式的心跳发送结果
        """
        if self.current_api == self.new_api:
            response = self.new_api.send_study_heartbeat(course_id, class_id, node_id, current_time)
            return self._convert_response_format(response, "new")
        else:
            response = self.old_api.send_study_heartbeat(course_id, class_id, node_id, current_time)
            return self._convert_response_format(response, "old")
    
    def sync_personal_data(self) -> Optional[Dict]:
        """
        同步个人数据
        
        Returns:
            统一格式的同步结果
        """
        if self.current_api == self.new_api:
            response = self.new_api.sync_personal_data()
            return self._convert_response_format(response, "new")
        else:
            response = self.old_api.sync_personal_data()
            return self._convert_response_format(response, "old")
    
    def get_current_api_type(self) -> str:
        """
        获取当前使用的API类型
        
        Returns:
            当前API类型 ("new" 或 "old")
        """
        return "new" if self.current_api == self.new_api else "old"
    
    def switch_api(self, api_version: str):
        """
        手动切换API版本
        
        Args:
            api_version: API版本 ("old" 或 "new")
        """
        if api_version == "old":
            self.current_api = self.old_api
            print("已切换到旧API")
        elif api_version == "new":
            self.current_api = self.new_api
            print("已切换到新API")
        else:
            raise ValueError(f"不支持的API版本: {api_version}")


# 创建全局API适配器实例
api_adapter = APIAdapter()

# 向后兼容的函数接口
def get_course_directory(course_id: str, class_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的课程目录获取函数"""
    response = api_adapter.get_course_directory(course_id, class_id)
    return response.get("data") if response and response.get("success") else response

def get_whole_chapter_page_content(node_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的章节内容获取函数"""
    response = api_adapter.get_whole_chapter_page_content(node_id)
    return response.get("data") if response and response.get("success") else response

def get_question_answer(question_id: str, parent_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的题目答案获取函数"""
    response = api_adapter.get_question_answer(question_id, parent_id)
    return response.get("data") if response and response.get("success") else response

def get_user_info(headers: Dict = None) -> Optional[Dict]:
    """向后兼容的用户信息获取函数"""
    response = api_adapter.get_user_info()
    return response.get("data") if response and response.get("success") else response

def get_course_remaining(course_id: str, class_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的课程剩余时间获取函数"""
    response = api_adapter.get_course_remaining(course_id, class_id)
    return response.get("data") if response and response.get("success") else response

def get_study_record(course_id: str, class_id: str, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的学习记录获取函数"""
    response = api_adapter.get_study_record(course_id, class_id)
    return response.get("data") if response and response.get("success") else response

def send_study_heartbeat(course_id: str, class_id: str, node_id: str, 
                       current_time: int = None, headers: Dict = None) -> Optional[Dict]:
    """向后兼容的学习心跳发送函数"""
    response = api_adapter.send_study_heartbeat(course_id, class_id, node_id, current_time)
    return response.get("data") if response and response.get("success") else response

def sync_personal_data(headers: Dict = None) -> Optional[Dict]:
    """向后兼容的个人数据同步函数"""
    response = api_adapter.sync_personal_data()
    return response.get("data") if response and response.get("success") else response