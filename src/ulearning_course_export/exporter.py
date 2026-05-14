import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from bs4 import BeautifulSoup

from .api_adapter import APIAdapter


@dataclass(frozen=True)
class ExportResult:
    course_name: str
    output_dir: Path
    complete_json: Path
    question_bank_json: Path
    question_count: int


def sanitize_filename(filename: Optional[str]) -> str:
    if filename is None:
        filename = "untitled"
    filename = str(filename)
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    filename = re.sub(r"\s+", "_", filename)
    filename = re.sub(r"_+", "_", filename)
    filename = filename.strip("_")
    return filename[:100] or "untitled"


def get_clean_text_from_html(html_content: Any) -> str:
    if not html_content or not isinstance(html_content, str):
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    for p_tag in soup.find_all("p"):
        p_tag.append("\n")
    for br_tag in soup.find_all("br"):
        br_tag.replace_with("\n")
    text = soup.get_text(separator="", strip=False)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    text = re.sub(r"^\s*\n|\n\s*$", "", text)
    return text.strip()


def has_fill_inputs(html_content: str) -> bool:
    if not html_content:
        return False
    lower_html = html_content.lower()
    return "input-wrapper" in lower_html or "<input" in lower_html


def build_fill_stem(title_html: str, answers: List[str]) -> str:
    if not title_html:
        return "".join([f"{{{answer}}}" if answer else "{___}" for answer in answers])

    soup = BeautifulSoup(title_html, "html.parser")
    blank_nodes = soup.select("span.input-wrapper, input")
    for idx, node in enumerate(blank_nodes):
        answer_text = answers[idx] if idx < len(answers) else ""
        node.replace_with(f"{{{answer_text}}}" if answer_text else "{___}")

    rendered = get_clean_text_from_html(str(soup))
    if len(blank_nodes) < len(answers):
        extra = "".join([f"{{{answer}}}" for answer in answers[len(blank_nodes):]])
        rendered = f"{rendered} {extra}".strip()
    return rendered


def get_question_type_name(type_code_from_api: Any) -> str:
    type_map = {
        1: "选择题",
        2: "选择题",
        4: "判断题",
        5: "填空题",
        6: "问答题",
    }
    return type_map.get(type_code_from_api, "未知题型")


def _answers_look_like_choice_letters(answers: Iterable[str]) -> bool:
    normalized = []
    for answer in answers:
        text = re.sub(r"[^A-Za-z]", "", (answer or "")).upper()
        if text:
            normalized.append(text)
    return bool(normalized) and all(text.isalpha() and len(text) <= 2 for text in normalized)


def _answers_look_like_true_false(answers: Iterable[str]) -> bool:
    tf_keywords = {"t", "f", "true", "false", "对", "错", "正确", "错误"}
    normalized = {
        re.sub(r"\s+", "", str(answer).strip()).lower()
        for answer in answers
        if answer
    }
    return bool(normalized) and normalized.issubset(tf_keywords)


def _clean_answers(answer_data: Optional[Dict[str, Any]]) -> List[str]:
    if not answer_data:
        return []
    if answer_data.get("correctAnswerList"):
        return [
            get_clean_text_from_html(str(answer))
            for answer in answer_data["correctAnswerList"]
        ]
    if answer_data.get("answer"):
        return [get_clean_text_from_html(str(answer_data["answer"]))]
    return []


def infer_platform_question_type(q_data: Dict[str, Any], answer_data: Optional[Dict[str, Any]]) -> str:
    raw_type = q_data.get("type")
    inferred = get_question_type_name(raw_type)
    has_options = bool(q_data.get("choiceitemModels"))
    title_html = q_data.get("title", "") or ""
    answers = _clean_answers(answer_data)

    if raw_type == 5 or has_fill_inputs(title_html):
        return "填空题"
    if answers and not has_options:
        if not _answers_look_like_choice_letters(answers) and not _answers_look_like_true_false(answers):
            return "填空题"
    if inferred == "未知题型" and raw_type in (3, 5):
        return "填空题"
    return inferred


def _unwrap_response(response: Any) -> Any:
    if not response:
        return None
    if isinstance(response, dict) and response.get("success") is True:
        return response.get("data")
    return response


def _normalize_true_false_answer(answers: List[str]) -> str:
    ans_text = answers[0].lower() if answers else ""
    return "正确" if ans_text in {"true", "t", "对", "正确"} else "错误"


def _build_complete_entry(
    course_name: str,
    chapter_title: str,
    unit_title: str,
    parent_id: Any,
    q_data: Dict[str, Any],
    answer_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    q_title_html = q_data.get("title", "N/A")
    q_options_raw = q_data.get("choiceitemModels", []) or []
    answers = _clean_answers(answer_data)
    question_type = infer_platform_question_type(q_data, answer_data)

    if question_type == "填空题":
        question_stem = build_fill_stem(q_title_html, answers)
    else:
        question_stem = get_clean_text_from_html(q_title_html)

    entry: Dict[str, Any] = {
        "题型": question_type,
        "题干": question_stem,
        "解析": "",
        "课程名称": course_name,
        "章节名称": chapter_title,
        "单元名称": unit_title,
        "题目ID": q_data.get("questionid"),
        "ParentID": parent_id,
        "原始题型码": q_data.get("type"),
        "原始题干HTML": q_title_html,
        "原始选项HTML": [opt.get("title", "") for opt in q_options_raw],
        "原始答案数据": answer_data,
    }

    if question_type == "选择题":
        entry["选项"] = [get_clean_text_from_html(opt.get("title", "")) for opt in q_options_raw]
        entry["答案"] = "".join(sorted(set(answers)))
    elif question_type == "判断题":
        entry["答案"] = _normalize_true_false_answer(answers)
    elif question_type == "问答题":
        entry["答案"] = "\n".join(answers)
    elif question_type == "未知题型":
        entry["答案"] = "未知题型答案: " + " | ".join(answers)

    return entry


def _to_question_bank_entry(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    qtype = entry.get("题型")
    if qtype == "选择题":
        return {
            "题型": "选择题",
            "题干": entry.get("题干", ""),
            "选项": entry.get("选项", []) or [],
            "答案": entry.get("答案", "") or "",
            "解析": entry.get("解析", "") or "",
        }
    if qtype == "判断题":
        return {
            "题型": "判断题",
            "题干": entry.get("题干", ""),
            "答案": entry.get("答案", "") or "",
            "解析": entry.get("解析", "") or "",
        }
    if qtype == "填空题":
        return {
            "题型": "填空题",
            "题干": entry.get("题干", ""),
            "解析": entry.get("解析", "") or "",
        }
    if qtype == "问答题":
        return {
            "题型": "问答题",
            "题干": entry.get("题干", ""),
            "答案": entry.get("答案", "") or "",
            "解析": entry.get("解析", "") or "",
        }
    return None


def _write_json(path: Path, data: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(f"已生成 JSON 文件: {path}")


def export_course_questions(
    course_id: str,
    class_id: str,
    output_dir: str = "ulearning_courseware_exports",
    api_version: str = "auto",
) -> ExportResult:
    api = APIAdapter(api_version=api_version)

    directory_data = _unwrap_response(api.get_course_directory(course_id, class_id))
    if not directory_data:
        raise RuntimeError("获取课程目录失败，请检查课程ID、班级ID和登录凭据。")

    course_name = directory_data.get("coursename", f"UnknownCourse_{course_id}")
    course_name_sanitized = sanitize_filename(course_name)
    course_output_dir = Path(output_dir) / f"course_{course_id}_{course_name_sanitized}"
    course_output_dir.mkdir(parents=True, exist_ok=True)
    print(f"正在导出课程: {course_name}")

    complete_entries: List[Dict[str, Any]] = []
    chapters = directory_data.get("chapters", []) or []
    if not chapters:
        raise RuntimeError("课程目录中没有找到章节。")

    for chapter_idx, chapter in enumerate(chapters):
        chapter_title = chapter.get("nodetitle", f"UnknownChapter_{chapter_idx + 1}")
        chapter_node_id = chapter.get("nodeid")
        if not chapter_node_id:
            print(f"跳过缺少 nodeid 的章节: {chapter_title}")
            continue

        print(f"\n处理章节: {chapter_title} (NodeID: {chapter_node_id})")
        chapter_content = _unwrap_response(api.get_whole_chapter_page_content(chapter_node_id))
        if not chapter_content:
            print(f"  获取章节内容失败，已跳过: {chapter_title}")
            continue

        for item_dto in chapter_content.get("wholepageItemDTOList", []) or []:
            for wholepage_dto in item_dto.get("wholepageDTOList", []) or []:
                if wholepage_dto.get("contentType") != 7:
                    continue

                parent_id = wholepage_dto.get("id")
                unit_title = wholepage_dto.get("content", f"UnknownUnit_{parent_id}")
                print(f"  处理单元: {unit_title} (ParentID: {parent_id})")

                for coursepage in wholepage_dto.get("coursepageDTOList", []) or []:
                    for q_data in coursepage.get("questionDTOList", []) or []:
                        question_id = q_data.get("questionid")
                        answer_data = _unwrap_response(api.get_question_answer(question_id, parent_id))
                        complete_entries.append(
                            _build_complete_entry(
                                course_name=course_name,
                                chapter_title=chapter_title,
                                unit_title=unit_title,
                                parent_id=parent_id,
                                q_data=q_data,
                                answer_data=answer_data,
                            )
                        )
                        print(f"    已处理题目: {question_id}")

    question_bank_entries = [
        entry
        for entry in (_to_question_bank_entry(item) for item in complete_entries)
        if entry is not None
    ]

    complete_json = course_output_dir / f"{course_name_sanitized}_questions_complete.json"
    question_bank_json = course_output_dir / f"{course_name_sanitized}_questions_shuati.json"
    _write_json(complete_json, complete_entries)
    _write_json(question_bank_json, question_bank_entries)

    return ExportResult(
        course_name=course_name,
        output_dir=course_output_dir,
        complete_json=complete_json,
        question_bank_json=question_bank_json,
        question_count=len(question_bank_entries),
    )
