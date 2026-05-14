# 优学院题库导出工具

这个工具用于从优学院**课件的章节测试**中导出题目数据。
>当前 Python 入口已经标准化为根目录的 `main.py`，核心代码位于 `src/ulearning_course_export/`。

## 功能

- 自动读取课程目录和章节题目
- 自动获取题目答案
- 导出完整 JSON：包含课程、章节、单元、题目 ID、原始 HTML、原始答案数据等元信息
- 导出题库 JSON：保留刷题导入常用字段，如题型、题干、选项、答案、解析


## 安装依赖

```bash
pip install -r requirements.txt
```

如果使用 uv：

```bash
uv sync
```

## 配置 `.env`

复制 `.env.example` 为 `.env`，并填写课程与登录凭据：


```env
COURSE_ID=你的课程ID
CLASS_ID=你的班级ID
AUTHORIZATION_TOKEN=浏览器请求头里的 authorization
UA_AUTHORIZATION_TOKEN=浏览器请求头里的 ua-authorization
BASE_API_URL=https://ua.ulearning.cn
BASE_OUTPUT_DIR=ulearning_courseware_exports
API_VERSION=auto
```

`COURSE_ID` 和 `CLASS_ID` 是必填项。如果缺少这两个变量，运行时会直接报错并提示补充。

`AUTHORIZATION_TOKEN` / `UA_AUTHORIZATION_TOKEN` 通常需要从浏览器开发者工具的 Network 请求头中复制。
## 运行

```bash
python main.py
```

导出完成后，文件会生成到：

```text
ulearning_courseware_exports/course_<COURSE_ID>_<课程名>/
```

包含两个 JSON 文件：

- `<课程名>_questions_complete.json`
- `<课程名>_questions_shuati.json`
