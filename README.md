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
## 注意事项

*   **Token 有效期**: `AUTHORIZATION_TOKEN` 通常具有时效性。如果脚本运行失败并提示认证错误（如HTTP 401），您可能需要重新从浏览器获取一个新的Token并更新到脚本中。
*   **API 变动风险**: 优学院的API接口可能会发生变更，这可能导致脚本功能异常或失效。如果遇到问题，建议检查最新的API请求情况。
*   **网络稳定性**: 请确保脚本运行时网络连接稳定，以便正常访问优学院API。
*   **文件名**: 脚本已对文件名和文件夹名中的特殊字符进行处理，但仍需注意不同操作系统对文件名的限制。
*   **负责任使用**: 请勿过于频繁地运行此脚本，避免对优学院服务器造成不必要的负担

---

powered by claudecode & claude sonnet 4.5
*哈基米快出3 pro 吧，别给A÷画面了*


## 贡献

如果您有任何改进建议、发现Bug或希望贡献代码，欢迎通过提交 Pull Requests 或 Issues 来参与。
