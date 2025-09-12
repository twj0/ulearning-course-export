import requests
import json
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import datetime
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv() # 从 .env 文件加载环境变量

COURSE_ID = os.getenv("COURSE_ID")
CLASS_ID = os.getenv("CLASS_ID")
AUTHORIZATION_TOKEN = os.getenv("AUTHORIZATION_TOKEN")
BASE_API_URL = os.getenv("BASE_API_URL", "https://api.ulearning.cn")
BASE_OUTPUT_DIR = os.getenv("BASE_OUTPUT_DIR", "ulearning_courseware_exports")


# --- API Headers ---
# 确保在获取配置后再定义 API_HEADERS
if not all([COURSE_ID, CLASS_ID, AUTHORIZATION_TOKEN]):
    print("错误：请确保 .env 文件中已配置 COURSE_ID, CLASS_ID, 和 AUTHORIZATION_TOKEN。")
    exit()

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
    "ua-authorization": AUTHORIZATION_TOKEN,
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
}

IMAGE_DOWNLOAD_HEADERS = {
    "User-Agent": API_HEADERS["user-agent"]
}

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

# --- API Call Functions (保持不变) ---
def get_course_directory(course_id, class_id, headers):
    url = f"{BASE_API_URL}/course/stu/{course_id}/directory?classId={class_id}"; print(f"Fetching course directory: {url}")
    try: response = requests.get(url, headers=headers, timeout=15); response.raise_for_status(); return response.json()
    except Exception as e: print(f"Error fetching course directory: {e}"); return None

def get_whole_chapter_page_content(node_id, headers):
    url = f"{BASE_API_URL}/wholepage/chapter/stu/{node_id}"; print(f"Fetching whole chapter page content for nodeId: {node_id} from {url}")
    try: response = requests.get(url, headers=headers, timeout=20); response.raise_for_status(); return response.json()
    except Exception as e:
        print(f"Error fetching whole chapter page content for nodeId {node_id}: {e}")
        if hasattr(e, 'response') and e.response is not None: print(f"Response text: {e.response.text[:500]}")
        return None
        
def get_question_answer(question_id, parent_id, headers):
    url = f"{BASE_API_URL}/questionAnswer/{question_id}?parentId={parent_id}"
    try: response = requests.get(url, headers=headers, timeout=10); response.raise_for_status(); return response.json()
    except Exception as e: print(f"  Error fetching answer for QID {question_id}, PID {parent_id}: {e}"); return None

# --- NEW FUNCTION for Platform Import Format ---
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
    global API_HEADERS
    API_HEADERS["authorization"] = AUTHORIZATION_TOKEN
    API_HEADERS["ua-authorization"] = AUTHORIZATION_TOKEN

    directory_data = get_course_directory(COURSE_ID, CLASS_ID, API_HEADERS)
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

        chapter_content = get_whole_chapter_page_content(chapter_node_id, API_HEADERS)
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

                            # Get platform-specific question type name
                            platform_entry["题型"] = get_question_type_name(q_type_code_api, for_platform=True)
                            
                            # Get clean question stem
                            question_stem_clean = get_clean_text_from_html(q_title_html)
                            
                            # Fetch answer
                            answer_data = get_question_answer(question_id, parent_id, API_HEADERS)
                            correct_answers_clean_list = []
                            if answer_data and answer_data.get("correctAnswerList"):
                                correct_answers_clean_list = [get_clean_text_from_html(str(ans)) for ans in answer_data["correctAnswerList"]]
                            elif answer_data and answer_data.get("answer"):
                                correct_answers_clean_list = [get_clean_text_from_html(str(answer_data["answer"]))]
                            
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
                                temp_stem = question_stem_clean
                                # Regex to find common placeholders like ___, （）, ()
                                # This regex looks for sequences of underscores, or parentheses that might contain spaces
                                placeholder_pattern = r"_{2,}|（\s*）|\(\s*\)"
                                
                                # Find all placeholders in the stem
                                placeholders_in_stem = list(re.finditer(placeholder_pattern, temp_stem))
                                
                                # If number of answers matches number of placeholders, replace them
                                if len(placeholders_in_stem) == len(correct_answers_clean_list) and len(placeholders_in_stem) > 0:
                                    # Replace from right to left to avoid issues with changing indices
                                    for i in range(len(placeholders_in_stem) - 1, -1, -1):
                                        ph_match = placeholders_in_stem[i]
                                        ans = correct_answers_clean_list[i]
                                        temp_stem = temp_stem[:ph_match.start()] + "{" + ans + "}" + temp_stem[ph_match.end():]
                                else: # If no clear placeholders or mismatch, append all answers
                                    if correct_answers_clean_list:
                                        formatted_answers = "".join(["{" + ans + "}" for ans in correct_answers_clean_list])
                                        temp_stem += " " + formatted_answers # Append with a space
                                
                                platform_entry["题干"] = temp_stem

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
