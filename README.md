# 优学院课件导出工具 (ulearning-course-export)

~~本项目是一个 Python 脚本~~，旨在帮助用户从优学院 (ulearning.cn) 导出指定课程的课件内容。主要功能包括提取课程结构、导出章节内的练习题目（包括题干、选项、题型）、下载题目中的图片，并获取正确答案。最终，脚本会将这些信息整理并输出为易于阅读和存档的 Markdown 和 TeX 文件

20251115：该项目还是支持导出优学院的课件题目, 也支持东莞理工学院的课件导出 ~~(其实就是换了个网址而已(笑~~

用户可以选择使用项目内的 pytho代码 和 js脚本文件 [点击访问脚本文件](https://github.com/twj0/ulearning-course-export/blob/main/js/_user.js)

**推荐使用js脚本**

## 使用方法|以js脚本为例

### 0. 下载浏览器拓展, 如果浏览器有`油猴`或者`脚本猫`的可以下滑
**下载地址：**
- 油猴/油猴beta：
   - [edge油猴](https://microsoftedge.microsoft.com/addons/detail/%E7%AF%A1%E6%94%B9%E7%8C%B4/iikmkjmpaadaobahmlepeloendndfphd)
   - [edge油猴beta](https://microsoftedge.microsoft.com/addons/detail/%E7%AF%A1%E6%94%B9%E7%8C%B4%E6%B5%8B%E8%AF%95%E7%89%88/fcmfnpggmnlmfebfghbfnillijihnkoh)
   - [chrome油猴](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo)
   - [chrome油猴beta](https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo)

### 1. 确保你有`脚本猫`或者`油猴`等浏览器拓展

复制粘贴后到优学院就可以使用了


---

## 核心功能

*   **课程结构解析**: 自动获取并解析指定课程的章节目录和单元结构。
*   **课件题目导出**:
    *   提取章节内各单元（如“练习题”）中的所有题目。
    *   获取题目的详细信息：题干、选项（针对选择题等）、题目类型。
    *   调用API获取每道题目的正确答案。
*   **图片处理**:
    *   自动识别并下载题目题干和选项中嵌入的图片。
    *   图片会保存在对应题目的专属文件夹下，方便管理。
*   **多种输出格式**:
    *   为整个课程（选定章节）生成一份图文并茂的 **Markdown (`.md`) 文件**。
    *   为整个课程（选定章节）生成一份高质量排版的 **TeX (`.tex`) 文件**。
*   **用户自定义选项**:
    *   **选择导出章节**: 用户可以指定导出课程中的一个或多个章节，或选择导出全部章节。
    *   **单个题目详情 (可选)**: 用户可以选择是否为每道题目在其专属文件夹内额外保存一个 `question_info.txt` 文件，包含该题目的完整文本信息（课程、章节、单元名、题干、选项、答案等）。
*   **智能文件组织**:
    *   导出的内容会保存在 `ulearning_courseware_exports` 目录下。
    *   每个课程会创建一个以课程ID和名称命名的子文件夹。
    *   （如果选择保存或题目含图片）在课程文件夹内，会进一步按 `章节 -> 单元 -> 题目` 的层级创建子文件夹存放图片和 `question_info.txt`。
    *   汇总的 Markdown 和 TeX 文件会以课程名命名，存放在课程主文件夹下。

## 环境要求

*   Python 3.x
*   必要的 Python 库:
    *   `requests` (用于网络请求)
    *   `beautifulsoup4` (用于解析HTML内容)

    您可以使用 pip (Python包管理器) 来安装这些依赖：
    ```bash
    pip install requests beautifulsoup4
    ```

    如果使用uv进行包管理还可以：
      ```bash
      uv venv -p 3.12
      ```

      ```bash
      uv pip install -r requirements.txt
      ```


*   **可选**: 如果您希望将生成的 `.tex` 文件编译为 PDF 文档，您需要在您的计算机上安装一套 LaTeX 发行版（例如 MiKTeX for Windows, TeX Live for Linux/cross-platform, MacTeX for macOS）。
*   不过这是为了编译PDF的方式而已，我认为最主要的还是json和markdown格式的文件，也生成在子文件夹内

## 使用python代码的方法

1.  **克隆或下载仓库**:
    将本项目代码下载到您的本地计算机。

2.  **配置必要信息**:
    打开脚本文件 (例如 `ulearning_course_export.py`)，在文件顶部的配置区域找到并修改以下变量，填入您从优学院获取的对应信息：
    ```python
    COURSE_ID = "你的课程ID"  # 例如: "46099"
    CLASS_ID = "你的班级ID"   # 例如: "851527"
    AUTHORIZATION_TOKEN = "你的授权Token" # 例如: "C79771B17441080DC52C42AF5C67289F"
    ```
    **如何获取这些信息？**
    *   **`COURSE_ID` 和 `CLASS_ID`**: 通常可以在浏览器地址栏的URL中找到，当您访问特定课程或班级相关页面时。
    *   **`AUTHORIZATION_TOKEN`**: 这是身份验证的关键。
        1.  登录优学院。
        2.  打开浏览器开发者工具 (通常按 F12 键)。
        3.  切换到“网络”(Network) 标签页。
        4.  进行一些操作，例如访问课程页面或点击课件内容，以产生网络请求。
        5.  在网络请求列表中，查找发往 `api.ulearning.cn` 域名的请求。
        6.  点击这些请求，查看其 **请求头 (Request Headers)**。找到名为 `authorization` 或 `ua-authorization` 的字段，并复制其完整的值。**请确保您复制的是这个头部的值**

3.  **运行脚本**:
    打开您的终端或命令提示符，导航到脚本所在的目录，然后执行：
    ```bash
    ulearning_course_export.py
    ```
    或者
    ```bash
    python ulearning_course_export.py
    ```

    如果是uv就使用
      ```bash
      uv run ulearning_course_export.py
      ```
    等待脚本运行完成，即可在 `ulearning_courseware_exports` 目录下找到导出的文件。

    如果您希望将生成的 `.tex` 文件编译为 PDF 文档，您可以使用 LaTeX 发行版提供的工具（如 `pdflatex`）来编译生成的 `.tex` 文件。

    使用下面的那个脚本会生成json，里面是佛脚考试的AI导入题目格式。

4.  **用户交互提示**:
    *   脚本运行时，会首先列出检测到的所有课程专题（章节）。
    *   您将被要求输入希望导出的专题序号（例如 `1,3,5`，或输入 `all` 导出全部）。
    *   接着，您将被询问是否为每个问题保存详细的 `question_info.txt` 文件（默认为否）。

5.  **等待导出完成**:
...

## Python 实现原理（以脚本为例）

> 本节是给想二次开发或读代码的人看的，简单说明 Python 脚本是如何“伪装成浏览器”去拿到题目数据的。

### 域名与环境变量

- **域名**：
  - 前端访问域名一般是 `https://ua.ulearning.cn` 或学校门户页面。
  - 实际 Python 请求使用的 API 域名在 `.env` 中配置，默认例如：
    ```python
    from dotenv import load_dotenv
    import os

    load_dotenv()

    BASE_API_URL = os.getenv("BASE_API_URL", "https://ua.dgut.edu.cn")
    ```
- **课程/班级等参数** 都来自 `.env`：
    ```python
    COURSE_ID = os.getenv("COURSE_ID")
    CLASS_ID = os.getenv("CLASS_ID")
    AUTHORIZATION_TOKEN = os.getenv("AUTHORIZATION_TOKEN")
    UA_AUTHORIZATION_TOKEN = os.getenv("UA_AUTHORIZATION_TOKEN")
    ```

### Cookie / Token 与请求头

脚本本身并不直接操作浏览器 Cookie，而是复用你在浏览器里已经登录好后抓到的 `authorization` / `ua-authorization` 值：

```python
import requests

session = requests.Session()
session.headers.update({
    "authorization": AUTHORIZATION_TOKEN,
    "ua-authorization": UA_AUTHORIZATION_TOKEN,
    "User-Agent": "Mozilla/5.0 ...",
    "Accept": "application/json, text/plain, */*",
})
```

实际代码里，这些头部在 `ulearning_api.py` / `dgut_ulearning_api.py` 中集中配置，然后通过 `requests.Session` 复用。

### 接口封装与网站特性

- **老优学院接口**：走 `UlearningAPI`，典型路径类似：
  - `/course/stu/{courseId}/directory`
  - `/questionAnswer/{questionId}?parentId={parentId}`
- **东莞理工新接口**：走 `DGUTUlearningAPI`，有版本前缀，例如：
  - `/api/v2/learnCourse/courseDirectory`
  - `/api/v2/learnQuestion/getQuestionAnswer`
- **自动适配**：
  - `api_adapter.APIAdapter` 会同时持有“旧 API 客户端”和“DGUT API 客户端”。
  - 通过 `get_user_info()` 或课程目录等请求自动探测哪个可用；如果新接口返回错误，会自动回退到旧接口。

一个简化版的“课程目录请求”示例（真实项目里是用类方法封装的）：

```python
def get_course_directory(course_id: str, class_id: str) -> dict:
    url = f"{BASE_API_URL}/uaapi/course/{course_id}/directory"
    resp = session.get(url, params={"classId": class_id}, timeout=15)
    resp.raise_for_status()
    return resp.json()
```

### 题目提取核心流程

Python 端的题目导出主要发生在 `process_courseware_questions()` 中，大致流程：

1. 调接口拿课程目录 `get_course_directory(COURSE_ID, CLASS_ID)`，得到所有章节的 `nodeid` / 标题。
2. 对每个选中的章节，调用 `get_whole_chapter_page_content(node_id)` 拿到整个章节下的“页面 + 练习题”结构。
3. 在返回 JSON 里，过滤出 `contentType == 7` 的单元（通常是“练习题/作业”区域）。
4. 遍历 `coursepageDTOList` → `questionDTOList`，逐题读取题干、选项、题型。
5. 对每道题再调用 `get_question_answer(question_id, parent_id)`，拿到正确答案及子题答案。
6. 把题干 HTML 转成纯文本 / Markdown，必要时下载题目中的图片，最终写入汇总的 `.md` / `.tex` 文件。

一个高度简化的遍历示例（去掉了异常处理和排版逻辑）：

```python
directory = get_course_directory(COURSE_ID, CLASS_ID)

for chapter in directory.get("chapters", []):
    node_id = chapter["nodeid"]
    chapter_content = get_whole_chapter_page_content(node_id)

    for item in chapter_content.get("wholepageItemDTOList", []):
        for wholepage in item.get("wholepageDTOList", []):
            if wholepage.get("contentType") != 7:
                continue  # skip non-exercise blocks

            parent_id = wholepage["id"]
            for page in wholepage.get("coursepageDTOList", []):
                for q in page.get("questionDTOList", []):
                    question_id = q["questionid"]
                    title_html = q.get("title", "")
                    options = q.get("choiceitemModels") or []

                    answer_data = get_question_answer(question_id, parent_id)
                    # extract correct answers from answer_data...
```

### 填空题与题型判断

优学院题库里，填空题有时并不会在目录 JSON 里显式标记类型，或者没有选项列表，因此代码做了额外的“启发式”判断：

- **原始题型码**：`type` 字段（1 单选、2 多选、4 判断、5 填空等）。
- **HTML 结构检查**：如果题干 HTML 中出现 `<input>` 或 `input-wrapper` 之类节点，也会当成“填空题”处理。
- **无选项时默认填空**：如果 `choiceitemModels` 为空，但又能拿到答案列表，也会优先按填空题导出。

对应的核心逻辑（简化版）：

```python
def is_fill_question(q_type: int, has_options: bool, title_html: str) -> bool:
    if q_type == 5:
        return True
    if not has_options:
        return True
    lower_html = (title_html or "").lower()
    return "input-wrapper" in lower_html or "<input" in lower_html
```

对于判断为填空的题目，脚本会用答案列表把题干里的空格替换成 `{answer}` 或 `{___}` 这样的占位符，方便在 Markdown / TeX 中直接看到“带答案的填空题”。

### 输出与文件组织

- 使用 `sanitize_filename()` 处理课程名/章节名等，避免路径中出现非法字符。
- 使用 `BeautifulSoup` 的 `get_text()` 把题干和选项 HTML 转成纯文本，再写入 Markdown / TeX。
- 用 `extract_image_urls_from_html()` 抓取 `<img>` 标签的 `src`，再通过 `requests.get()` 下载到对应题目文件夹。
- 同时生成：
  - 每门课一个 Markdown 汇总文件。
  - 每门课一个 TeX 汇总文件（可自行用 LaTeX 编译成 PDF）。
  - 按 `课程 -> 章节 -> 单元 -> 题目` 的层级存放图片与可选的 `question_info.txt`。

以上是高层的 Python 实现原理，如果你想改造接口或适配新的学校，只需要在 `ulearning_api.py` / `dgut_ulearning_api.py` / `api_adapter.py` 里扩展域名和路径，再保持返回结构一致即可。

## 注意事项

*   **Token 有效期**: `AUTHORIZATION_TOKEN` 通常具有时效性。如果脚本运行失败并提示认证错误（如HTTP 401），您可能需要重新从浏览器获取一个新的Token并更新到脚本中。
*   **API 变动风险**: 优学院的API接口可能会发生变更，这可能导致脚本功能异常或失效。如果遇到问题，建议检查最新的API请求情况。
*   **网络稳定性**: 请确保脚本运行时网络连接稳定，以便正常访问优学院API。
*   **文件名**: 脚本已对文件名和文件夹名中的特殊字符进行处理，但仍需注意不同操作系统对文件名的限制。
*   **负责任使用**: 请勿过于频繁地运行此脚本，避免对优学院服务器造成不必要的负担

---

powered by claudecode & claude sonnet 4.5

