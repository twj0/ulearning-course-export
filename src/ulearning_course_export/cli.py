from .config import ConfigError, load_settings
from .exporter import export_course_questions


def main() -> int:
    try:
        settings = load_settings()
        result = export_course_questions(
            course_id=settings.course_id,
            class_id=settings.class_id,
            output_dir=settings.output_dir,
            api_version=settings.api_version,
        )
    except ConfigError as exc:
        print(f"配置错误: {exc}")
        return 2
    except Exception as exc:
        print(f"导出失败: {exc}")
        return 1

    print("\n--- 导出完成 ---")
    print(f"课程: {result.course_name}")
    print(f"题目数量: {result.question_count}")
    print(f"输出目录: {result.output_dir.resolve()}")
    print(f"完整 JSON: {result.complete_json.resolve()}")
    print(f"题库 JSON: {result.question_bank_json.resolve()}")
    return 0
