import requests
import json
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
import datetime

# --- Configuration ---
COURSE_ID = "46099"  # 替换为你的 Course ID
CLASS_ID = "851527"   # 替换为你的 Class ID
AUTHORIZATION_TOKEN = "C79771B17441080DC52C42AF5C67289F" # 替换为你的 Token

BASE_API_URL = "https://api.ulearning.cn"
BASE_OUTPUT_DIR = "ulearning_courseware_exports" # 新的输出目录名

API_HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01", # Adjusted for these APIs
    "accept-language": "zh",
    "authorization": AUTHORIZATION_TOKEN,
    "content-type": "application/json",
    "origin": "https://ua.ulearning.cn", # Often checked
    "referer": "https://ua.ulearning.cn/", # Often checked
    "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "ua-authorization": AUTHORIZATION_TOKEN, # Specific header seen in logs
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
}

IMAGE_DOWNLOAD_HEADERS = { # Simplified for image download
    "User-Agent": API_HEADERS["user-agent"]
}

# --- Helper Functions (sanitize_filename, get_clean_text_from_html, escape_latex_special_chars, download_image, get_question_type_name) ---


def sanitize_filename(filename):
    if filename is None: filename = "untitled"
    filename = str(filename)
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_')
    return filename[:100]

def get_clean_text_from_html(html_content):
    if not html_content or not isinstance(html_content, str): return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    for p_tag in soup.find_all("p"): p_tag.append("\n")
    for br_tag in soup.find_all("br"): br_tag.replace_with("\n")
    text = soup.get_text(separator='', strip=False)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'^\s*\n|\n\s*$', '', text)
    return text.strip()

def extract_image_urls_from_html(html_content):
    """Extracts all unique image URLs from an HTML string."""
    if not html_content or not isinstance(html_content, str):
        return []
    soup = BeautifulSoup(html_content, 'html.parser')
    img_tags = soup.find_all('img')
    urls = []
    for img in img_tags:
        if 'src' in img.attrs and img['src'] and img['src'].strip(): # Ensure src exists and is not empty
            urls.append(img['src'].strip())
    return list(set(urls)) # Return unique URLs


def escape_latex_special_chars(text):
    if not text: return ""
    text = text.replace('\\', r'\textbackslash{}')
    text = text.replace('{', r'\{'); text = text.replace('}', r'\}')
    text = text.replace('&', r'\&'); text = text.replace('%', r'\%')
    text = text.replace('$', r'\$'); text = text.replace('#', r'\#')
    text = text.replace('_', r'\_'); text = text.replace('^', r'\^{}')
    text = text.replace('~', r'\textasciitilde{}')
    return text

def download_image(url, save_path, headers):
    try:
        # print(f"  Downloading image: {url} \n    to: {save_path}")
        response = requests.get(url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        # print(f"  Successfully downloaded.")
        return True
    except Exception as e:
        print(f"  Error downloading image {url}: {e}")
    return False

def get_question_type_name(type_code): # As defined before
    type_map = {1: "单选题", 2: "多选题", 3: "不定项选择题", 4: "判断题", 5: "填空题", 6: "简答题/论述题"} # Adjusted based on typical usage
    return type_map.get(type_code, f"未知题型({type_code})")

# --- API Call Functions ---
def get_course_directory(course_id, class_id, headers):
    url = f"{BASE_API_URL}/course/stu/{course_id}/directory?classId={class_id}"
    print(f"Fetching course directory: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching course directory: {e}")
        return None

def get_whole_chapter_page_content(node_id, headers):
    url = f"{BASE_API_URL}/wholepage/chapter/stu/{node_id}"
    print(f"Fetching whole chapter page content for nodeId: {node_id} from {url}")
    try:
        response = requests.get(url, headers=headers, timeout=20) # Might be a large response
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching whole chapter page content for nodeId {node_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response text: {e.response.text[:500]}")
        return None
        
def get_question_answer(question_id, parent_id, headers):
    url = f"{BASE_API_URL}/questionAnswer/{question_id}?parentId={parent_id}"
    # print(f"  Fetching answer for QID: {question_id}, PID: {parent_id}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  Error fetching answer for QID {question_id}, PID {parent_id}: {e}")
        return None

# --- Main Processing Logic ---
# ... (所有之前的代码，包括配置、辅助函数、API调用函数都保持不变) ...
# Make sure extract_image_urls_from_html is defined correctly as provided before.

def process_courseware_questions():
    global API_HEADERS
    API_HEADERS["authorization"] = AUTHORIZATION_TOKEN
    API_HEADERS["ua-authorization"] = AUTHORIZATION_TOKEN

    directory_data = get_course_directory(COURSE_ID, CLASS_ID, API_HEADERS)
    if not directory_data:
        print("Failed to fetch course directory. Exiting.")
        return

    course_name_raw = directory_data.get("coursename", f"UnknownCourse_{COURSE_ID}")
    course_name_sanitized = sanitize_filename(course_name_raw)
    course_output_dir = os.path.join(BASE_OUTPUT_DIR, f"course_{COURSE_ID}_{course_name_sanitized}")
    os.makedirs(course_output_dir, exist_ok=True)
    print(f"Processing course: {course_name_raw}")

    all_course_questions_md_content = [f"# {course_name_raw} - 课件题目汇总\n\n"]
    all_course_questions_tex_content = [
        r"\documentclass[12pt,UTF8]{ctexart}",
        r"\usepackage{graphicx}", r"\usepackage{amsmath, amsfonts, amssymb}",
        r"\usepackage[a4paper, margin=1in]{geometry}", r"\usepackage{enumitem}",
        r"\usepackage{hyperref}", r"\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue, citecolor=green}",
        r"\usepackage{array,longtable}",
        f"\\title{{{escape_latex_special_chars(course_name_raw)} - 课件题目汇总}}",
        f"\\author{{优学院导出}}", f"\\date{{{datetime.date.today().strftime('%Y-%m-%d')}}}",
        r"\begin{document}", r"\maketitle", "\n"
    ]

    chapters = directory_data.get("chapters", [])
    if not chapters:
        print("No chapters found in course directory.")
        return

    for chapter_idx, chapter in enumerate(chapters):
        chapter_title_raw = chapter.get("nodetitle", f"UnknownChapter_{chapter_idx+1}")
        chapter_node_id = chapter.get("nodeid")
        
        if not chapter_node_id:
            print(f"Skipping chapter '{chapter_title_raw}' due to missing nodeId.")
            continue
        
        chapter_title_sanitized = sanitize_filename(chapter_title_raw)
        print(f"\nProcessing Chapter: {chapter_title_raw} (NodeID: {chapter_node_id})")

        all_course_questions_md_content.append(f"## {chapter_title_raw}\n\n")
        all_course_questions_tex_content.append(f"\\section*{{{escape_latex_special_chars(chapter_title_raw)}}}\n\\hrulefill\n")

        chapter_content = get_whole_chapter_page_content(chapter_node_id, API_HEADERS)
        if not chapter_content:
            print(f"  Failed to fetch content for chapter '{chapter_title_raw}'. Skipping.")
            continue

        wholepage_item_list = chapter_content.get("wholepageItemDTOList", [])
        question_counter_in_chapter = 0

        for item_dto in wholepage_item_list:
            for wholepage_dto in item_dto.get("wholepageDTOList", []):
                if wholepage_dto.get("contentType") == 7: # Question set
                    parent_id = wholepage_dto.get("id")
                    unit_title_raw = wholepage_dto.get("content", f"UnknownUnit_{parent_id}")
                    unit_title_sanitized = sanitize_filename(unit_title_raw)
                    
                    print(f"  Processing Unit: {unit_title_raw} (ParentID: {parent_id})")

                    all_course_questions_md_content.append(f"### {unit_title_raw}\n\n")
                    all_course_questions_tex_content.append(f"\\subsection*{{{escape_latex_special_chars(unit_title_raw)}}}\n")

                    coursepage_list = wholepage_dto.get("coursepageDTOList", [])
                    if not coursepage_list: continue
                    questions_list = coursepage_list[0].get("questionDTOList", [])
                    if not questions_list:
                        print(f"    No questions found in unit '{unit_title_raw}'.")
                        continue
                    
                    for q_data in questions_list:
                        question_counter_in_chapter += 1
                        question_id = q_data.get("questionid")
                        q_title_html = q_data.get("title", "N/A")
                        q_type_code = q_data.get("type")
                        q_type_name = get_question_type_name(q_type_code)
                        q_options_raw = q_data.get("choiceitemModels", [])

                        question_img_subfolder_relative = os.path.join(
                            f"chapter_{chapter_node_id}_{chapter_title_sanitized}", 
                            f"unit_{parent_id}_{unit_title_sanitized}", 
                            f"question_{question_id}"
                        )
                        question_folder_absolute = os.path.join(course_output_dir, question_img_subfolder_relative) # Renamed for clarity
                        os.makedirs(question_folder_absolute, exist_ok=True)
                        
                        # print(f"    Processing Q: {question_id} (Type: {q_type_name}) - Data in '{question_img_subfolder_relative}'")

                        answer_data = get_question_answer(question_id, parent_id, API_HEADERS)
                        correct_answer_str_list = []
                        if answer_data and answer_data.get("correctAnswerList"):
                            correct_answer_str_list = [get_clean_text_from_html(str(ans)) for ans in answer_data["correctAnswerList"]]
                        elif answer_data and answer_data.get("answer"):
                            correct_answer_str_list = [get_clean_text_from_html(str(answer_data["answer"]))]
                        
                        title_text_clean = get_clean_text_from_html(q_title_html)
                        
                        # --- Save individual question_info.txt ---
                        info_txt_path = os.path.join(question_folder_absolute, "question_info.txt")
                        with open(info_txt_path, 'w', encoding='utf-8') as f_info:
                            f_info.write(f"课程名称: {course_name_raw}\n")
                            f_info.write(f"章节名称: {chapter_title_raw}\n")
                            f_info.write(f"单元名称: {unit_title_raw}\n")
                            f_info.write(f"题目ID: {question_id}\n")
                            f_info.write(f"ParentID (单元ID): {parent_id}\n")
                            f_info.write(f"题型: {q_type_name}\n\n")
                            f_info.write(f"【题干】:\n{title_text_clean}\n\n")
                            if q_options_raw:
                                f_info.write("【选项】:\n")
                                for opt_idx_info, opt_info in enumerate(q_options_raw):
                                    opt_title_html_info = opt_info.get("title", "")
                                    opt_text_clean_info = get_clean_text_from_html(opt_title_html_info)
                                    opt_soup_info = BeautifulSoup(opt_title_html_info, 'html.parser')
                                    p_tag_info = opt_soup_info.find('p')
                                    prefix_info = chr(ord('A') + opt_idx_info) + ". "
                                    if p_tag_info and len(p_tag_info.get_text(strip=True)) == 1 and p_tag_info.get_text(strip=True).isalpha():
                                        prefix_text_info = p_tag_info.get_text(strip=True)
                                        prefix_info = prefix_text_info + ". "
                                        if opt_text_clean_info.startswith(prefix_text_info):
                                            opt_text_clean_info = opt_text_clean_info[len(prefix_text_info):].lstrip(". ")
                                    f_info.write(f"{prefix_info}{opt_text_clean_info}\n")
                                f_info.write("\n")
                            f_info.write(f"【正确答案】:\n{' | '.join(correct_answer_str_list) or '未获取到'}\n")
                        # print(f"      Info text saved to: {info_txt_path}")


                        # --- Markdown Content Generation ---
                        md_q_entry = [f"#### {question_counter_in_chapter}. ({q_type_name}) QID: {question_id} (ParentID: {parent_id})\n"]
                        md_q_entry.append(f"**题干:**\n{title_text_clean}\n")
                        
                        for img_idx, img_url in enumerate(extract_image_urls_from_html(q_title_html)):
                            img_filename = f"title_img_{img_idx+1}{os.path.splitext(urlparse(img_url).path)[1] or '.png'}"
                            img_save_path = os.path.join(question_folder_absolute, img_filename)
                            if download_image(img_url, img_save_path, IMAGE_DOWNLOAD_HEADERS):
                                img_relative_path_for_md = os.path.join(question_img_subfolder_relative, img_filename).replace("\\", "/")
                                md_q_entry.append(f"![题干图片 {img_idx+1}]({img_relative_path_for_md})\n")
                        md_q_entry.append("\n")

                        if q_options_raw:
                            md_q_entry.append("**选项:**\n")
                            for opt_idx, opt in enumerate(q_options_raw):
                                opt_title_html = opt.get("title", "")
                                opt_text_clean = get_clean_text_from_html(opt_title_html)
                                opt_soup = BeautifulSoup(opt_title_html, 'html.parser')
                                p_tag = opt_soup.find('p')
                                prefix = chr(ord('A') + opt_idx) + ". "
                                option_letter_for_img = chr(ord('A') + opt_idx)
                                if p_tag and len(p_tag.get_text(strip=True)) == 1 and p_tag.get_text(strip=True).isalpha():
                                    prefix_text = p_tag.get_text(strip=True)
                                    prefix = prefix_text + ". "
                                    option_letter_for_img = prefix_text
                                    if opt_text_clean.startswith(prefix_text):
                                        opt_text_clean = opt_text_clean[len(prefix_text):].lstrip(". ")
                                md_q_entry.append(f"- {prefix}{opt_text_clean}\n")
                                for img_idx, img_url in enumerate(extract_image_urls_from_html(opt_title_html)):
                                    img_filename = f"option_{option_letter_for_img}_img_{img_idx+1}{os.path.splitext(urlparse(img_url).path)[1] or '.png'}"
                                    img_save_path = os.path.join(question_folder_absolute, img_filename)
                                    if download_image(img_url, img_save_path, IMAGE_DOWNLOAD_HEADERS):
                                        img_relative_path_for_md = os.path.join(question_img_subfolder_relative, img_filename).replace("\\", "/")
                                        md_q_entry.append(f"  ![选项 {option_letter_for_img} 图片 {img_idx+1}]({img_relative_path_for_md})\n")
                            md_q_entry.append("\n")
                        
                        md_q_entry.append(f"**正确答案:**\n{' | '.join(correct_answer_str_list) or '未获取到'}\n")
                        md_q_entry.append("---\n")
                        all_course_questions_md_content.extend(md_q_entry)

                        # --- TeX Content Generation ---
                        tex_q_entry = [f"\\subsubsection*{{{question_counter_in_chapter}. ({escape_latex_special_chars(q_type_name)}) \\small QID: {question_id} (ParentID: {parent_id})}}\n"]
                        title_text_tex = escape_latex_special_chars(title_text_clean).replace('\n\n', '\n\\par\n') # Already cleaned title_text_clean
                        tex_q_entry.append(f"\\textbf{{{escape_latex_special_chars('题干')}:}}\n{title_text_tex}\n")
                        for img_idx, img_url in enumerate(extract_image_urls_from_html(q_title_html)):
                            img_filename = f"title_img_{img_idx+1}{os.path.splitext(urlparse(img_url).path)[1] or '.png'}"
                            img_relative_path_for_tex = os.path.join(question_img_subfolder_relative, img_filename).replace("\\", "/")
                            if os.path.exists(os.path.join(question_folder_absolute, img_filename)):
                                tex_q_entry.append(f"\\begin{{center}}\\includegraphics[width=0.8\\textwidth,keepaspectratio]{{{img_relative_path_for_tex}}}\\end{{center}}\n")
                        tex_q_entry.append("\n")
                        
                        if q_options_raw:
                            tex_q_entry.append(f"\\textbf{{{escape_latex_special_chars('选项')}:}}\n\\begin{{itemize}}[leftmargin=*]\n")
                            for opt_idx, opt in enumerate(q_options_raw):
                                opt_title_html = opt.get("title", "")
                                opt_text_clean_raw = get_clean_text_from_html(opt_title_html) # Use already cleaned text
                                opt_soup = BeautifulSoup(opt_title_html, 'html.parser') # Still need soup for prefix
                                p_tag = opt_soup.find('p')
                                prefix_raw = chr(ord('A') + opt_idx) + ". "
                                option_letter_for_img = chr(ord('A') + opt_idx)
                                if p_tag and len(p_tag.get_text(strip=True)) == 1 and p_tag.get_text(strip=True).isalpha():
                                    prefix_text = p_tag.get_text(strip=True)
                                    prefix_raw = prefix_text + ". "
                                    option_letter_for_img = prefix_text
                                    if opt_text_clean_raw.startswith(prefix_text):
                                        opt_text_clean_raw = opt_text_clean_raw[len(prefix_text):].lstrip(". ")
                                opt_text_tex = escape_latex_special_chars(prefix_raw + opt_text_clean_raw).replace('\n\n', '\n\\par\n')
                                tex_q_entry.append(f"  \\item {opt_text_tex}\n")
                                for img_idx, img_url in enumerate(extract_image_urls_from_html(opt_title_html)):
                                    img_filename = f"option_{option_letter_for_img}_img_{img_idx+1}{os.path.splitext(urlparse(img_url).path)[1] or '.png'}"
                                    img_relative_path_for_tex = os.path.join(question_img_subfolder_relative, img_filename).replace("\\", "/")
                                    if os.path.exists(os.path.join(question_folder_absolute, img_filename)):
                                        tex_q_entry.append(f"  \\begin{{center}}\\includegraphics[width=0.7\\textwidth,keepaspectratio]{{{img_relative_path_for_tex}}}\\end{{center}}\n")
                            tex_q_entry.append("\\end{itemize}\n")
                        
                        tex_q_entry.append(f"\\textbf{{{escape_latex_special_chars('正确答案')}:}}\n{escape_latex_special_chars(' | '.join(correct_answer_str_list) or '未获取到')}\n")
                        tex_q_entry.append("\\vspace{0.3em}\\hrulefill\\vspace{0.7em}\n")
                        all_course_questions_tex_content.extend(tex_q_entry)

        if question_counter_in_chapter == 0:
             all_course_questions_md_content.append(f"本章节未找到练习题。\n\n")
             all_course_questions_tex_content.append(f"本章节未找到练习题。\n\n")

    md_file_path = os.path.join(course_output_dir, f"{course_name_sanitized}_课件题目.md")
    with open(md_file_path, 'w', encoding='utf-8') as f: f.write("".join(all_course_questions_md_content))
    print(f"\nAggregated Markdown file saved to: {md_file_path}")

    all_course_questions_tex_content.append(r"\end{document}")
    tex_file_path = os.path.join(course_output_dir, f"{course_name_sanitized}_课件题目.tex")
    with open(tex_file_path, 'w', encoding='utf-8') as f: f.write("\n".join(all_course_questions_tex_content))
    print(f"Aggregated TeX file saved to: {tex_file_path}")

if __name__ == "__main__":
    if not all([COURSE_ID, CLASS_ID, AUTHORIZATION_TOKEN]):
        print("请在脚本顶部配置 COURSE_ID, CLASS_ID, 和 AUTHORIZATION_TOKEN。")
    else:
        process_courseware_questions()