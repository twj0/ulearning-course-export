import requests
import json
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import datetime
from dotenv import load_dotenv

# 导入API模块，优先使用适配器以兼容DGUT环境
try:
    from api_adapter import (
        get_course_directory, get_whole_chapter_page_content,
        get_question_answer, api_adapter
    )
    from api_adapter import APIAdapter  # noqa: F401  # for potential type checking
    api = api_adapter.current_api
    API_HEADERS = api.session.headers
    IMAGE_DOWNLOAD_HEADERS = {
        "User-Agent": API_HEADERS.get("User-Agent", API_HEADERS.get("user-agent", "Mozilla/5.0")),
        "Referer": API_HEADERS.get("Referer", API_HEADERS.get("referer", ""))
    }
except ImportError:
    print("警告: 无法导入API适配器，回退到原始API模块")
    from ulearning_api import (
        api, get_course_directory, get_whole_chapter_page_content,
        get_question_answer, API_HEADERS, IMAGE_DOWNLOAD_HEADERS
    )

# --- Configuration ---
load_dotenv() # 从 .env 文件加载环境变量

COURSE_ID = os.getenv("COURSE_ID")
CLASS_ID = os.getenv("CLASS_ID")
AUTHORIZATION_TOKEN = os.getenv("AUTHORIZATION_TOKEN")
BASE_OUTPUT_DIR = os.getenv("BASE_OUTPUT_DIR", "ulearning_courseware_exports")

# --- 环境检查 ---
if not all([COURSE_ID, CLASS_ID, AUTHORIZATION_TOKEN]):
    print("错误：请确保 .env 文件中已配置 COURSE_ID, CLASS_ID, 和 AUTHORIZATION_TOKEN。")
    exit()

# --- Helper Functions (保持大部分不变) ---
def sanitize_filename(filename):
    if filename is None: filename = "untitled"
    filename = str(filename); filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename); filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_'); return filename[:100]

def get_clean_text_from_html(html_content):
    if not html_content or not isinstance(html_content, str): return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    for p_tag in soup.find_all("p"): p_tag.append("\n")
    for br_tag in soup.find_all("br"): br_tag.replace_with("\n")
    text = soup.get_text(separator='', strip=False)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'^\s*\n|\n\s*$', '', text)
    return text.strip()

def extract_image_urls_from_html(html_content): # 确保这个函数存在
    if not html_content or not isinstance(html_content, str): return []
    soup = BeautifulSoup(html_content, 'html.parser')
    img_tags = soup.find_all('img'); urls = []
    for img in img_tags:
        if 'src' in img.attrs and img['src'] and img['src'].strip(): urls.append(img['src'].strip())
    return list(set(urls))

def escape_latex_special_chars(text): # TeX相关，此处用不到但保留
    if not text: return ""; text = text.replace('\\', r'\textbackslash{}')
    text = text.replace('{', r'\{'); text = text.replace('}', r'\}')
    text = text.replace('&', r'\&'); text = text.replace('%', r'\%')
    text = text.replace('$', r'\$'); text = text.replace('#', r'\#')
    text = text.replace('_', r'\_'); text = text.replace('^', r'\^{}')
    text = text.replace('~', r'\textasciitilde{}'); return text

def download_image(url, save_path, headers): # 保留，但此功能不直接用于刷题平台格式
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        return True
    except Exception as e: print(f"  Error downloading image {url}: {e}"); return False

def has_fill_inputs(html_content: str) -> bool:
    if not html_content:
        return False
    return 'input-wrapper' in html_content or '<input' in html_content.lower()

def build_fill_stem(title_html: str, answers: list) -> str:
    if not title_html:
        return "".join([f"{{{ans}}}" if ans else "{___}" for ans in answers])
    soup = BeautifulSoup(title_html, 'html.parser')
    blank_nodes = soup.select('span.input-wrapper, input')
    for idx, node in enumerate(blank_nodes):
        answer_text = answers[idx] if idx < len(answers) else ''
        replacement_text = f"{{{answer_text}}}" if answer_text else "{___}"
        node.replace_with(replacement_text)
    rendered = get_clean_text_from_html(str(soup))
    if len(blank_nodes) < len(answers):
        extra = "".join([f"{{{ans}}}" for ans in answers[len(blank_nodes):]])
        rendered = f"{rendered} {extra}".strip()
    return rendered

def infer_platform_question_type(q_data: dict, answer_data: dict) -> str:
    raw_type = q_data.get("type")
    inferred = get_question_type_name(raw_type, for_platform=True)
    has_options = bool(q_data.get("choiceitemModels"))
    answers = []
    if answer_data and answer_data.get("correctAnswerList"):
        answers = [get_clean_text_from_html(str(ans)) for ans in answer_data["correctAnswerList"]]
    elif answer_data and answer_data.get("answer"):
        answers = [get_clean_text_from_html(str(answer_data["answer"]))]

    if inferred == "未知题型" and raw_type in (3, 5):
        inferred = "填空题"

    if inferred == "选择题" and not has_options and (answers or has_fill_inputs(q_data.get("title", ""))):
        inferred = "填空题"

    return inferred

def get_question_type_name(type_code_from_api, for_platform=False):
    # API 的 type_code: 1:单选, 2:多选, 4:判断, 5:填空, (可能还有其他，如简答)
    # 刷题平台格式: "选择题", "判断题", "填空题", "问答题"
    if for_platform:
        if type_code_from_api == 1: return "选择题"
        if type_code_from_api == 2: return "选择题" # 多选也归为选择题
        if type_code_from_api == 4: return "判断题"
        if type_code_from_api == 5: return "填空题"
        # 假设API中的简答题类型是6 (基于之前的get_question_type_name)
        if type_code_from_api == 6: return "问答题" 
        return "未知题型" # 平台未知
    else: # 原来的逻辑，用于MD/TeX
        type_map = {1: "单选题", 2: "多选题", 4: "判断题", 5: "填空题", 6: "简答题/论述题"}
        return type_map.get(type_code_from_api, f"API未知题型({type_code_from_api})")

# --- NEW FUNCTION for Platform Import Format ---
def generate_json_output(data, output_dir, filename, is_complete_json=False):
    """
    Generates a JSON file from the provided data.

    Args:
        data: The list of question dictionaries.
        output_dir: The directory to save the file in.
        filename: The name of the output file.
        is_complete_json: If True, saves the full original data structure.
                          If False, saves the simplified format for the platform.
    """
    output_path = os.path.join(output_dir, filename)
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # Use json.dump for proper JSON formatting, escaping, and indentation
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Successfully generated JSON file: {output_path}")
    except Exception as e:
        print(f"Error writing JSON file {filename}: {e}")

# --- Main Processing Logic (Modified to collect data for platform format) ---
def process_courseware_questions():
    directory_data = get_course_directory(COURSE_ID, CLASS_ID)
    if not directory_data: print("Failed to fetch course directory. Exiting."); return

    course_name_raw = directory_data.get("coursename", f"UnknownCourse_{COURSE_ID}")
    course_name_sanitized = sanitize_filename(course_name_raw)
    course_output_dir = os.path.join(BASE_OUTPUT_DIR, f"course_{COURSE_ID}_{course_name_sanitized}")
    os.makedirs(course_output_dir, exist_ok=True)
    print(f"Processing course: {course_name_raw}")

    # Data list for the new platform format
    platform_data_list = []
    # (MD and TeX content lists can remain if you still want those outputs)
    # all_course_questions_md_content = [f"# {course_name_raw} - 课件题目汇总\n\n"]
    # all_course_questions_tex_content = [...] # TeX preamble

    chapters = directory_data.get("chapters", [])
    if not chapters: print("No chapters found."); return

    for chapter_idx, chapter in enumerate(chapters):
        chapter_title_raw = chapter.get("nodetitle", f"UnknownChapter_{chapter_idx+1}")
        chapter_node_id = chapter.get("nodeid")
        if not chapter_node_id: print(f"Skipping chapter '{chapter_title_raw}' due to missing nodeId."); continue
        
        # (MD/TeX chapter titles can be added here if needed)
        print(f"\nProcessing Chapter: {chapter_title_raw} (NodeID: {chapter_node_id})")

        chapter_content = get_whole_chapter_page_content(chapter_node_id)
        if not chapter_content: print(f"  Failed content for chapter '{chapter_title_raw}'."); continue

        wholepage_item_list = chapter_content.get("wholepageItemDTOList", [])
        
        for item_dto in wholepage_item_list:
            for wholepage_dto in item_dto.get("wholepageDTOList", []):
                if wholepage_dto.get("contentType") == 7: # Question set
                    parent_id = wholepage_dto.get("id")
                    unit_title_raw = wholepage_dto.get("content", f"UnknownUnit_{parent_id}")
                    print(f"  Processing Unit: {unit_title_raw} (ParentID: {parent_id})")
                    
                    # (MD/TeX unit titles can be added here if needed)

                    coursepage_list = wholepage_dto.get("coursepageDTOList", [])
                    if not coursepage_list: continue
                    
                    for coursepage in coursepage_list:
                        questions_list = coursepage.get("questionDTOList", [])
                        if not questions_list: continue # No questions in this page, check next one
                        
                        for q_data in questions_list:
                            platform_entry = {} # For the new format

                            question_id = q_data.get("questionid")
                            q_title_html = q_data.get("title", "N/A")
                            q_type_code_api = q_data.get("type") # API's type code
                            q_options_raw_api = q_data.get("choiceitemModels", [])

                            # Fetch answer
                            answer_data = get_question_answer(question_id, parent_id)
                            correct_answers_clean_list = []
                            if answer_data and answer_data.get("correctAnswerList"):
                                correct_answers_clean_list = [get_clean_text_from_html(str(ans)) for ans in answer_data["correctAnswerList"]]
                            elif answer_data and answer_data.get("answer"):
                                correct_answers_clean_list = [get_clean_text_from_html(str(answer_data["answer"]))]

                            # Infer platform-specific question type
                            platform_entry["题型"] = infer_platform_question_type(q_data, answer_data)
                            
                            # Get clean question stem
                            if platform_entry["题型"] == "填空题":
                                question_stem_clean = build_fill_stem(q_title_html, correct_answers_clean_list)
                            else:
                                question_stem_clean = get_clean_text_from_html(q_title_html)
                            
                            # --- Populate platform_entry based on question type ---
                            if platform_entry["题型"] == "选择题":
                                platform_entry["题干"] = question_stem_clean
                                options_list = []
                                for opt_idx, opt in enumerate(q_options_raw_api):
                                    opt_text = get_clean_text_from_html(opt.get("title", ""))
                                    options_list.append(opt_text)
                                platform_entry["选项"] = options_list

                                # The correct_answers_clean_list already contains the option letters (e.g., ['A', 'B'])
                                # We just need to join and sort them.
                                platform_entry["答案"] = "".join(sorted(list(set(correct_answers_clean_list))))
                                # Remove debug prints as the issue is understood
                                # if not platform_entry["答案"] and correct_answers_clean_list:
                                #     print(f"        DEBUG: Failed to map correct answer to options for QID {question_id}.")
                                #     print(f"        DEBUG: Raw correct_answers_clean_list: {correct_answers_clean_list}")
                                #     print(f"        DEBUG: Raw q_options_raw_api: {json.dumps(q_options_raw_api, indent=2, ensure_ascii=False)}")
                                #     pass

                            elif platform_entry["题型"] == "判断题":
                                platform_entry["题干"] = question_stem_clean
                                ans_text = correct_answers_clean_list[0].lower() if correct_answers_clean_list else ""
                                platform_entry["答案"] = "正确" if ans_text in ["true", "t", "对"] else "错误"
                            
                            elif platform_entry["题型"] == "填空题":
                                platform_entry["题干"] = question_stem_clean

                            elif platform_entry["题型"] == "问答题":
                                platform_entry["题干"] = question_stem_clean
                                platform_entry["答案"] = "\n".join(correct_answers_clean_list) # Join parts if any
                            
                            else: # Unknown type for platform
                                platform_entry["题型"] = "未知题型"
                                platform_entry["题干"] = question_stem_clean
                                platform_entry["答案"] = "未知题型答案: " + " | ".join(correct_answers_clean_list)

                            platform_entry["解析"] = "" # Placeholder, need to check if API provides this
                            
                            platform_data_list.append(platform_entry)
                            print(f"    Processed QID: {question_id} for platform import.")

    # Generate the platform import file
    # --- Generate Output Files ---
    # 1. Simplified JSON for the platform
    platform_json_filename = f"{course_name_sanitized}_questions_platform.json"
    generate_json_output(platform_data_list, course_output_dir, platform_json_filename, is_complete_json=False)

    # 2. Complete JSON with all raw data (optional, but good for debugging)
    # We can create a more detailed list if needed, for now we use the same one.
    complete_json_filename = f"{course_name_sanitized}_questions_complete.json"
    generate_json_output(platform_data_list, course_output_dir, complete_json_filename, is_complete_json=True)


    # (The old generate_platform_import_file function is now replaced by generate_json_output)

    print("\n--- 数据导出与JSON文件生成处理完成 ---")
    print(f"请检查输出目录: {os.path.abspath(course_output_dir)}")


if __name__ == "__main__":
    process_courseware_questions()
