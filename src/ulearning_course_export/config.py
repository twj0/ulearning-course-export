import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    course_id: str
    class_id: str
    output_dir: str
    api_version: str


class ConfigError(RuntimeError):
    pass


def load_settings(env_path: str = ".env") -> Settings:
    env_file = Path(env_path)
    load_dotenv(env_file if env_file.exists() else None)

    missing = _missing_required_vars(["COURSE_ID", "CLASS_ID"])
    if missing:
        joined = ", ".join(missing)
        raise ConfigError(
            f"缺少必要环境变量: {joined}。请在 .env 文件中填写 COURSE_ID 和 CLASS_ID。"
        )

    if not os.getenv("AUTHORIZATION_TOKEN") and not os.getenv("UA_AUTHORIZATION_TOKEN"):
        print("提示: 未检测到 AUTHORIZATION_TOKEN 或 UA_AUTHORIZATION_TOKEN，接口请求可能会失败。")

    return Settings(
        course_id=os.environ["COURSE_ID"].strip(),
        class_id=os.environ["CLASS_ID"].strip(),
        output_dir=os.getenv("BASE_OUTPUT_DIR", "ulearning_courseware_exports").strip(),
        api_version=os.getenv("API_VERSION", "auto").strip() or "auto",
    )


def _missing_required_vars(names: List[str]) -> List[str]:
    return [name for name in names if not os.getenv(name, "").strip()]
