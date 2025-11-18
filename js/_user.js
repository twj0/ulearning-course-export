// ==UserScript==
// @name         Ulearning Course Exporter
// @namespace    https://github.com/twj0/ulearning-course-export
// @version      0.2.0
// @description  Export Ulearning courseware questions as Markdown directly from the browser. Supports manual API export and automatic pagination export with debug mode for Tampermonkey / ScriptCat users.v0.2.0 can export json file
// @author       twj0
// @match        https://ua.ulearning.cn/learnCourse/learnCourse.html?*
// @match        https://ua.ulearning.cn/learnCourseNew/learnCourse.html?*
// @match        https://ua.ulearning.cn/learnCourse/learnCourseNew.html?*
// @match        https://ua.dgut.edu.cn/learnCourse/learnCourse.html?*
// @match        https://ua.dgut.edu.cn/learnCourseNew/learnCourse.html?*
// @match        https://ua.dgut.edu.cn/learnCourse/learnCourseNew.html?*
// @match        https://lms.dgut.edu.cn/*
// @grant        GM_addStyle
// @grant        GM_download
// @grant        GM_notification
// @connect      ua.ulearning.cn
// @connect      ua.dgut.edu.cn
// @connect      lms.dgut.edu.cn
// @connect      nx-s3.ntalker.com
// @connect      nx-s3-trail.ntalker.com
// ==/UserScript==

(function () {
  "use strict";

  const HOSTNAME = window.location.hostname;
  const API_BASE = window.location.origin;
  const ENV = detectEnvironment(HOSTNAME);

  const ENDPOINTS = {
    course_directory: [
      { path: "/api/v2/learnCourse/courseDirectory", method: "POST" },
      { path: "/learnCourse/courseDirectory", method: "POST" }
    ],
    chapter_content: [
      { path: "/api/v2/learnCourse/getWholeChapterPageContent", method: "POST" },
      { path: "/learnCourse/getWholeChapterPageContent", method: "POST" }
    ],
    question_answer: [
      { path: "/api/v2/learnQuestion/getQuestionAnswer", method: "POST" },
      { path: "/learnQuestion/getQuestionAnswer", method: "POST" }
    ]
  };

  const ENV_ENDPOINTS = {
    dgut: {
      course_directory: [
        {
          path: ({ courseId, classId }) =>
            `/uaapi/course/stu/${encodeURIComponent(courseId)}/directory?classId=${encodeURIComponent(classId)}`,
          method: "GET"
        }
      ],
      chapter_content: [
        {
          path: ({ nodeId }) => `/uaapi/wholepage/chapter/stu/${encodeURIComponent(nodeId)}`,
          method: "GET"
        }
      ],
      question_answer: [
        {
          path: ({ questionId, parentId }) =>
            `/uaapi/questionAnswer/${encodeURIComponent(questionId)}?parentId=${encodeURIComponent(parentId)}`,
          method: "GET"
        }
      ]
    }
  };

  const QUESTION_TYPE_NAME = {
    1: "单选题",
    2: "多选题",
    3: "不定项选择题",
    4: "判断题",
    5: "填空题",
    6: "简答题/论述题",
    7: "文件题",
    11: "阅读理解",
    12: "排序题",
    17: "选词填空",
    24: "综合题"
  };

  const FILL_IN_TYPE_CODE = 5;

  const TYPE_NAME_TO_CODE = Object.fromEntries(
    Object.entries(QUESTION_TYPE_NAME).flatMap(([code, name]) => {
      const normalized = normalizeTypeLabel(name);
      return normalized && normalized !== name
        ? [[name, Number(code)], [normalized, Number(code)]]
        : [[name, Number(code)]];
    })
  );

  const DEBUG_STORAGE_KEY = "ulearning_md_export_debug";
  const DEBUG_TOGGLE_ID = "ulearning-md-export-debug";
  const AUTO_EXPORT_BTN_ID = "ulearning-auto-export-btn";
  const BUTTON_ID = "ulearning-md-export-btn";
  const STYLE_ID = "ulearning-md-export-style";

  let debugEnabled = (() => {
    try {
      return localStorage.getItem(DEBUG_STORAGE_KEY) === "true";
    } catch (err) {
      console.warn("[Ulearning Markdown Exporter] Failed to read debug flag", err);
      return false;
    }
  })();

  const autoExportState = {
    running: false,
    pageResults: [],
    visitedPageIds: new Set(),
    totalQuestions: 0
  };

  init();

  function init() {
    addStyle();
    createExportButton();
    createDebugToggle();
  }

  function addStyle() {
    const css = `
      #${BUTTON_ID}, #${DEBUG_TOGGLE_ID} {
        position: fixed;
        right: 24px;
        z-index: 999999;
        background: #4285f4;
        color: #fff;
        border: none;
        border-radius: 6px;
        padding: 10px 16px;
        font-size: 14px;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(66, 133, 244, 0.35);
        min-width: 180px;
      }
      #${BUTTON_ID} {
        top: 90px;
      }
      #${DEBUG_TOGGLE_ID} {
        top: 150px;
        background: #fbbc04;
        color: #000;
      }
      #${BUTTON_ID}:hover {
        background: #2f6fdb;
      }
      #${DEBUG_TOGGLE_ID}:hover {
        background: #f9ab00;
      }
      #${BUTTON_ID}.running {
        background: #34a853;
        cursor: wait;
      }
      #${BUTTON_ID}.running:hover {
        background: #34a853;
      }
    `;

    if (typeof GM_addStyle === "function") {
      GM_addStyle(css);
      return;
    }

    let styleEl = document.getElementById(STYLE_ID);
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.id = STYLE_ID;
      styleEl.textContent = css;
      document.head.appendChild(styleEl);
    }
  }

  function createExportButton() {
    if (document.getElementById(BUTTON_ID)) {
      return;
    }
    const btn = document.createElement("button");
    btn.id = BUTTON_ID;
    btn.textContent = "导出课件题目";
    btn.addEventListener("click", () => {
      if (autoExportState.running) {
        stopAutoExport();
        btn.classList.remove("running");
        btn.textContent = "导出课件题目";
        return;
      }
      btn.classList.add("running");
      btn.textContent = "准备中...";
      toggleAutoExport().catch((err) => {
        notify("导出失败: " + (err && err.message ? err.message : err));
        logDebug("Export failed", err);
      }).finally(() => {
        btn.classList.remove("running");
        btn.textContent = "导出课件题目";
      });
    });
    document.body.appendChild(btn);
  }

  function createDebugToggle() {
    if (document.getElementById(DEBUG_TOGGLE_ID)) {
      updateDebugToggle();
      return;
    }
    const btn = document.createElement("button");
    btn.id = DEBUG_TOGGLE_ID;
    updateDebugToggle(btn);
    btn.addEventListener("click", () => {
      debugEnabled = !debugEnabled;
      try {
        localStorage.setItem(DEBUG_STORAGE_KEY, String(debugEnabled));
      } catch (err) {
        console.warn("[Ulearning Markdown Exporter] Failed to persist debug flag", err);
      }
      updateDebugToggle(btn);
      logDebug("Debug mode toggled", debugEnabled);
    });
    document.body.appendChild(btn);
  }

  function updateExportProgress(current, total, status) {
    const btn = document.getElementById(BUTTON_ID);
    if (!btn) {
      return;
    }
    if (status) {
      btn.textContent = status;
    } else if (total > 0) {
      btn.textContent = `导出中 ${current}/${total}`;
    } else {
      btn.textContent = `已收集 ${current} 题`;
    }
  }

  function updateDebugToggle(btn) {
    const target = btn || document.getElementById(DEBUG_TOGGLE_ID);
    if (!target) {
      return;
    }
    target.textContent = debugEnabled ? "调试模式: 开" : "调试模式: 关";
  }

  function logDebug(message, payload) {
    if (!debugEnabled) {
      return;
    }
    if (typeof payload === "undefined") {
      console.log("[Ulearning Markdown Exporter][DEBUG]", message);
    } else {
      console.log("[Ulearning Markdown Exporter][DEBUG]", message, payload);
    }
  }

  async function exportCourseware() {
    const { courseId, classId } = extractIdsFromUrl();
    if (!courseId || !classId) {
      throw new Error("未能从地址栏解析到 courseId 或 classId。");
    }

    notify("开始导出课件题目...", true);

    const directoryResp = await requestEndpoint(
      "course_directory",
      { courseId, classId }
    );

    if (!directoryResp || !directoryResp.success || !directoryResp.data) {
      throw new Error("获取课程目录失败，请确认已登录且具备权限。");
    }

    const courseData = normalizeDirectory(directoryResp.data);
    const courseNameRaw = courseData.coursename || `course_${courseId}`;
    const courseNameSanitized = sanitizeFilename(courseNameRaw);
    const chapters = Array.isArray(courseData.chapters) ? courseData.chapters : [];

    if (!chapters.length) {
      throw new Error("课程目录中未发现章节。");
    }

    const markdownParts = [];
    markdownParts.push(`# ${courseNameRaw} - 课件题目汇总\n\n`);

    let questionCounter = 0;

    for (const chapter of chapters) {
      const chapterTitle = chapter.nodetitle || chapter.title || "未命名专题";
      const chapterNodeId = chapter.nodeid || chapter.id;
      markdownParts.push(`## ${chapterTitle}\n\n`);

      if (!chapterNodeId) {
        markdownParts.push("> 未找到章节 nodeId，跳过该章节。\n\n");
        continue;
      }

      const chapterContentResp = await requestEndpoint(
        "chapter_content",
        { nodeId: chapterNodeId }
      );

      if (!chapterContentResp || !chapterContentResp.data) {
        markdownParts.push(
          "> 获取章节内容失败，可能没有练习题或需要重新登录。\n\n"
        );
        continue;
      }

      const itemList = normalizeChapterContent(chapterContentResp.data);
      for (const itemDTO of itemList) {
        const wholepageDTOList = itemDTO.wholepageDTOList || [];
        for (const wholepageDTO of wholepageDTOList) {
          if (wholepageDTO.contentType !== 7) {
            continue;
          }
          const unitTitle = wholepageDTO.content || "未命名单元";
          const parentId = wholepageDTO.id;
          markdownParts.push(`### ${unitTitle}\n\n`);

          const coursepageList = wholepageDTO.coursepageDTOList || [];
          let questionsFound = false;

          for (const coursepage of coursepageList) {
            const questions = normalizeQuestions(coursepage);
            if (!questions.length) {
              continue;
            }
            questionsFound = true;

            for (const question of questions) {
              questionCounter += 1;
              const questionId = question.questionid;
              let questionTypeCode = question.type;
              let questionTypeName = QUESTION_TYPE_NAME[questionTypeCode] || `未知题型(${questionTypeCode})`;
              const titleHtml = question.title || "";
              const rawChoices = question.choiceitemModels || [];
              const answerResp = questionId
                ? await requestEndpoint("question_answer", {
                    questionId,
                    parentId
                  })
                : null;

              const answerValues = collectAnswerValues(answerResp);
              const answerInfo = answerValues.length ? answerValues.join(" | ") : extractAnswer(answerResp);
              const answerTypeCode = extractQuestionTypeFromAnswer(answerResp);
              const treatAsFillBlank = shouldTreatAsFillBlank(questionTypeCode, titleHtml, rawChoices);
              if (treatAsFillBlank) {
                questionTypeCode = FILL_IN_TYPE_CODE;
                questionTypeName = QUESTION_TYPE_NAME[FILL_IN_TYPE_CODE];
              }
              if (Number.isFinite(answerTypeCode) && answerTypeCode > 0) {
                questionTypeCode = answerTypeCode;
                questionTypeName = QUESTION_TYPE_NAME[questionTypeCode] || questionTypeName;
              }

              const renderAnswers = answerValues.length ? answerValues : answerInfo ? [answerInfo] : [];
              const titleText = questionTypeCode === FILL_IN_TYPE_CODE
                ? renderFillQuestionText(titleHtml, renderAnswers)
                : htmlToText(titleHtml) || "(题干缺失)";

              markdownParts.push(`#### ${questionCounter}. (${questionTypeName}) QID: ${questionId || "-"}\n`);
              markdownParts.push(`**题干:**\n${titleText}\n\n`);

              if (questionTypeCode !== FILL_IN_TYPE_CODE && rawChoices.length) {
                markdownParts.push("**选项:**\n");
                rawChoices.forEach((choice, idx) => {
                  const label = choice.option || String.fromCharCode(65 + idx);
                  const text = htmlToText(choice.title || "");
                  markdownParts.push(`- ${label}. ${text || "(无内容)"}`);
                });
                markdownParts.push("\n");
              }

              markdownParts.push(
                `**正确答案:**\n${answerInfo || "未获取到"}\n---\n`
              );
            }
          }

          if (!questionsFound) {
            markdownParts.push(
              "> 当前单元未检测到题目。\n\n"
            );
          }
        }
      }
    }

    if (questionCounter === 0) {
      markdownParts.push("在选定专题中未找到练习题。\n\n");
    }

    const markdownContent = markdownParts.join("\n");
    const filename = `${courseNameSanitized}_课件题目.md`;
    await downloadMarkdown(filename, markdownContent);
    notify(`导出完成，共收集 ${questionCounter} 道题目。`);
  }

  async function toggleAutoExport() {
    if (autoExportState.running) {
      stopAutoExport();
      return;
    }

    const format = await promptExportFormat();
    if (!format) return;

    autoExportState.running = true;
    updateExportProgress(0, 0, "启动中...");
    notify("开始导出...", true);
    try {
      await exportViaAPI(format);
    } finally {
      stopAutoExport();
    }
  }

  function promptExportFormat() {
    return new Promise((resolve) => {
      const choice = prompt("选择导出格式:\n1 - Markdown (.md)\n2 - JSON (.json)\n3 - 题库 JSON (.json)\n\n请输入 1 / 2 / 3:", "1");
      if (choice === null) {
        resolve(null);
      } else if (choice === "2") {
        resolve("json");
      } else if (choice === "3") {
        resolve("bank");
      } else {
        resolve("md");
      }
    });
  }

  async function exportViaAPI(format = "md") {
    try {
      const { courseId, classId } = extractIdsFromUrl();
      if (!courseId || !classId) {
        throw new Error("未能从地址栏解析到 courseId 或 classId");
      }

      updateExportProgress(0, 0, "获取课程目录...");
      const directoryResp = await requestEndpoint("course_directory", { courseId, classId });

      if (!directoryResp || !directoryResp.success || !directoryResp.data) {
        throw new Error("获取课程目录失败");
      }

      const courseData = normalizeDirectory(directoryResp.data);
      const courseName = courseData.coursename || `course_${courseId}`;
      const chapters = Array.isArray(courseData.chapters) ? courseData.chapters : [];

      logDebug("Course data loaded", { courseName, chaptersCount: chapters.length });

      if (!chapters.length) {
        throw new Error("课程目录中未发现章节");
      }

      const jsonData = {
        course_id: courseId,
        course_name: courseName,
        export_time: new Date().toISOString(),
        chapters: []
      };

      const markdownParts = [`# ${courseName} - 课件题目\n\n`];
      let totalQuestions = 0;

      for (let i = 0; i < chapters.length; i++) {
        try {
          const chapter = chapters[i];
          const chapterTitle = chapter.nodetitle || chapter.title || "未命名章节";
          const chapterNodeId = chapter.nodeid || chapter.id;

          updateExportProgress(i + 1, chapters.length, `处理: ${chapterTitle}`);
          logDebug("Processing chapter", { chapterTitle, chapterNodeId, index: i + 1 });

          markdownParts.push(`## ${chapterTitle}\n\n`);

          const chapterJson = {
            chapter_id: chapterNodeId,
            chapter_title: chapterTitle,
            units: []
          };

          if (!chapterNodeId) {
            markdownParts.push("> 未找到章节 ID，跳过\n\n");
            logDebug("Chapter skipped - no ID");
            jsonData.chapters.push(chapterJson);
            continue;
          }

          const chapterContentResp = await requestEndpoint("chapter_content", { nodeId: chapterNodeId });

          if (!chapterContentResp || !chapterContentResp.data) {
            markdownParts.push("> 获取章节内容失败\n\n");
            logDebug("Chapter content fetch failed");
            jsonData.chapters.push(chapterJson);
            continue;
          }

          const itemList = normalizeChapterContent(chapterContentResp.data);
          logDebug("Chapter content normalized", { itemsCount: itemList.length });

          for (const itemDTO of itemList) {
            const wholepageDTOList = itemDTO.wholepageDTOList || [];

            for (const wholepageDTO of wholepageDTOList) {
              if (wholepageDTO.contentType !== 7) continue;

              const unitTitle = wholepageDTO.content || "未命名单元";
              const parentId = wholepageDTO.id;
              markdownParts.push(`### ${unitTitle}\n\n`);

              const unitJson = {
                unit_id: parentId,
                unit_title: unitTitle,
                questions: []
              };

              const coursepageList = wholepageDTO.coursepageDTOList || [];
              let hasQuestions = false;

              for (const coursepage of coursepageList) {
                const questions = normalizeQuestions(coursepage);
                if (!questions.length) continue;

                hasQuestions = true;
                logDebug("Found questions in unit", { unitTitle, questionsCount: questions.length });

                for (const question of questions) {
                  totalQuestions++;
                  const questionId = question.questionid;
                  let questionTypeCode = question.type;
                  let questionTypeName = QUESTION_TYPE_NAME[questionTypeCode] || `未知题型(${questionTypeCode})`;
                  const titleHtml = question.title || "";
                  const choices = question.choiceitemModels || [];

                  let answerValues = [];
                  let answerText = "";
                  if (questionId && parentId) {
                    try {
                      const answerResp = await requestEndpoint("question_answer", { questionId, parentId });
                      answerValues = collectAnswerValues(answerResp);
                      answerText = answerValues.length ? answerValues.join(" | ") : extractAnswer(answerResp);
                      const answerTypeCode = extractQuestionTypeFromAnswer(answerResp);
                      if (Number.isFinite(answerTypeCode) && answerTypeCode > 0) {
                        questionTypeCode = answerTypeCode;
                        questionTypeName = QUESTION_TYPE_NAME[questionTypeCode] || questionTypeName;
                      }
                    } catch (err) {
                      logDebug("Failed to fetch answer", { questionId, err });
                    }
                  }

                  const isFillQuestion = shouldTreatAsFillBlank(questionTypeCode, titleHtml, choices);
                  if (isFillQuestion && questionTypeCode !== FILL_IN_TYPE_CODE) {
                    questionTypeCode = FILL_IN_TYPE_CODE;
                    questionTypeName = QUESTION_TYPE_NAME[FILL_IN_TYPE_CODE];
                  }

                  const renderAnswers = answerValues.length ? answerValues : (answerText ? [answerText] : []);
                  const titleText = isFillQuestion
                    ? renderFillQuestionText(titleHtml, renderAnswers)
                    : htmlToText(titleHtml) || "(题干缺失)";

                  markdownParts.push(`#### ${totalQuestions}. (${questionTypeName}) QID: ${questionId || "-"}\n`);
                  markdownParts.push(`**题干:**\n${titleText}\n\n`);

                  const questionJson = {
                    question_id: questionId,
                    question_type: questionTypeCode,
                    question_type_name: questionTypeName,
                    title: titleText,
                    rendered_title: titleText,
                    options: [],
                    answer: answerText || "",
                    answer_list: renderAnswers,
                    is_fill_question: isFillQuestion
                  };

                  if (!isFillQuestion && choices.length) {
                    markdownParts.push("**选项:**\n");
                    choices.forEach((choice, idx) => {
                      const label = choice.option || String.fromCharCode(65 + idx);
                      const text = htmlToText(choice.title || "");
                      markdownParts.push(`- ${label}. ${text || "(无内容)"}\n`);
                      questionJson.options.push({ label, text: text || "(无内容)" });
                    });
                    markdownParts.push("\n");
                  }

                  markdownParts.push(
                    `**正确答案:**\n${answerText || "未获取到"}\n---\n\n`
                  );
                  unitJson.questions.push(questionJson);
                  updateExportProgress(totalQuestions, 0);
                }
              }

              if (!hasQuestions) {
                markdownParts.push("> 当前单元未检测到题目\n\n");
              }

              if (unitJson.questions.length > 0) {
                chapterJson.units.push(unitJson);
              }
            }
          }

          if (chapterJson.units.length > 0) {
            jsonData.chapters.push(chapterJson);
          }

          logDebug("Chapter completed", { chapterTitle, totalQuestionsNow: totalQuestions });
        } catch (chapterErr) {
          logDebug("Error processing chapter", chapterErr);
          markdownParts.push(`> 处理章节时出错: ${chapterErr.message}\n\n`);
        }
      }

      if (totalQuestions === 0) {
        markdownParts.push("未找到练习题\n\n");
      }

      jsonData.total_questions = totalQuestions;
      logDebug("All chapters processed", { totalQuestions, chaptersCount: chapters.length });

      updateExportProgress(0, 0, "生成文件中...");

      if (format === "json") {
        const jsonContent = JSON.stringify(jsonData, null, 2);
        logDebug("JSON generated", { contentLength: jsonContent.length });
        const filename = `${sanitizeFilename(courseName)}_课件题目.json`;
        await downloadJson(filename, jsonContent);
      } else if (format === "bank") {
        const bankData = buildQuestionBank(jsonData);
        const jsonContent = JSON.stringify(bankData, null, 2);
        logDebug("Question bank JSON generated", { contentLength: jsonContent.length, count: bankData.length });
        const filename = `题库.json`;
        await downloadJson(filename, jsonContent);
      } else {
        const markdownContent = markdownParts.join("");
        logDebug("Markdown generated", { contentLength: markdownContent.length });
        const filename = `${sanitizeFilename(courseName)}_课件题目.md`;
        await downloadMarkdown(filename, markdownContent);
      }

      updateExportProgress(0, 0, `完成! ${totalQuestions} 题`);
      notify(`导出完成，共 ${totalQuestions} 道题目`);
      await delay(2000);
    } catch (err) {
      logDebug("Export failed with error", err);
      throw err;
    }
  }

  async function runAutoExportLoop() {
    let safetyCounter = 0;
    let pageCount = 0;

    while (autoExportState.running) {
      safetyCounter += 1;
      if (safetyCounter > 600) {
        logDebug("Auto export reached safety iteration limit", safetyCounter);
        break;
      }

      closeActiveModals();

      const previousPageId = getActivePageId();
      const parentId = getCurrentParentId();
      const pageTitle = getActivePageTitle();
      logDebug("Scanning page", { previousPageId, parentId, pageTitle });

      if (!autoExportState.visitedPageIds.has(previousPageId)) {
        pageCount += 1;
        updateExportProgress(autoExportState.totalQuestions, 0, `扫描第 ${pageCount} 页...`);

        const questions = await collectQuestionsFromDom(parentId, pageTitle);
        if (questions.length) {
          autoExportState.pageResults.push({ pageId: previousPageId, pageTitle, questions });
          autoExportState.visitedPageIds.add(previousPageId);
          autoExportState.totalQuestions += questions.length;
          updateExportProgress(autoExportState.totalQuestions, 0);
          logDebug("Collected questions", { pageTitle, count: questions.length });
        } else {
          logDebug("No questions detected", { pageTitle });
          autoExportState.visitedPageIds.add(previousPageId);
        }
      } else {
        logDebug("Page already processed", previousPageId);
      }

      const moved = await goToNextPage();
      if (!moved) {
        logDebug("Next page not available, stopping");
        break;
      }
      await waitForPageChange(previousPageId);
      await delay(250);
    }

    if (!autoExportState.pageResults.length) {
      updateExportProgress(0, 0, "未找到题目");
      notify("未捕获到任何题目", true);
      await delay(2000);
      return;
    }

    updateExportProgress(0, 0, "生成文件中...");
    const markdown = buildAutoMarkdown(autoExportState.pageResults);
    const filename = `${sanitizeFilename(getCourseName()) || "course"}_导出.md`;
    await downloadMarkdown(filename, markdown);
    updateExportProgress(0, 0, `完成! ${autoExportState.totalQuestions} 题`);
    notify(`导出完成，共 ${autoExportState.totalQuestions} 道题目`);
    await delay(2000);
  }

  function stopAutoExport() {
    autoExportState.running = false;
  }

  function closeActiveModals() {
    const modal = document.querySelector(".modal.fade.in");
    if (!modal) {
      return;
    }

    const modalId = modal.getAttribute("id");
    logDebug("Detected modal", modalId);

    if (modalId === "statModal") {
      const btn = modal.querySelector("#statModal .btn-hollow");
      if (btn) {
        btn.click();
        logDebug("Closed statModal");
        return;
      }
    }

    if (modalId === "alertModal") {
      const hollowBtn = modal.querySelector("#alertModal .btn-hollow");
      if (hollowBtn) {
        hollowBtn.click();
        logDebug("Closed alertModal with hollow button");
        return;
      }
      const submitBtn = modal.querySelector("#alertModal .btn-submit");
      if (submitBtn) {
        submitBtn.click();
        logDebug("Closed alertModal with submit button");
        return;
      }
    }

    const closeBtn = modal.querySelector(".btn-hollow, .btn-submit, .close, [data-dismiss='modal']");
    if (closeBtn) {
      closeBtn.click();
      logDebug("Closed modal with generic button");
    }
  }

  async function collectQuestionsFromDom(parentId, pageTitle) {
    const lookupSelectors = [
      ".question-element-node",
      ".question-item",
      ".question-area .question-wrapper"
    ];
    const nodes = new Set();
    lookupSelectors.forEach((selector) => {
      document.querySelectorAll(selector).forEach((node) => nodes.add(node));
    });

    const results = [];
    const seenIds = new Set();

    for (const node of nodes) {
      const meta = extractQuestionMeta(node, pageTitle);
      if (!meta || !meta.questionId || seenIds.has(meta.questionId)) {
        continue;
      }
      seenIds.add(meta.questionId);

      let answerText = "";
      let finalTypeCode = meta.questionTypeCode;
      let finalTypeName = meta.questionTypeName;
      
      // 添加调试日志
      logDebug("Type detection", { 
        questionId: meta.questionId, 
        initialTypeCode: finalTypeCode,
        hasChoices: meta.choices && meta.choices.length,
        domBasedType: meta.questionTypeCode
      });
      
      // 如果DOM识别出的是选择题但没有选项，则认为是填空题
      if ((finalTypeCode === 1 || finalTypeCode === 2) && (!meta.choices || meta.choices.length === 0)) {
        logDebug("Fallback to fill-in type due to no choices", { questionId: meta.questionId });
        finalTypeCode = FILL_IN_TYPE_CODE;
        finalTypeName = QUESTION_TYPE_NAME[FILL_IN_TYPE_CODE];
      }
      
      try {
        if (parentId) {
          const answerInfo = await fetchQuestionAnswer(meta.questionId, parentId);
          answerText = answerInfo.answer || "";
          if (answerInfo.typeCode) {
            finalTypeCode = answerInfo.typeCode;
            finalTypeName = QUESTION_TYPE_NAME[finalTypeCode] || finalTypeName;
            logDebug("API provided type code", { questionId: meta.questionId, typeCode: finalTypeCode });
          } else if ((!finalTypeCode || finalTypeCode === 1 || finalTypeCode === 2) && 
                     (!meta.choices || meta.choices.length === 0)) {
            // API未返回题型且DOM识别为选择题但没有选项时，设置为填空题
            logDebug("Fallback to fill-in type due to no choices and no API type", { questionId: meta.questionId });
            finalTypeCode = FILL_IN_TYPE_CODE;
            finalTypeName = QUESTION_TYPE_NAME[FILL_IN_TYPE_CODE];
          }
        }
      } catch (err) {
        logDebug("Failed to fetch answer", { questionId: meta.questionId, err });
      }

      results.push({
        ...meta,
        questionTypeCode: finalTypeCode,
        questionTypeName: finalTypeName,
        answerText
      });
    }

    return results;
  }

  function detectQuestionTypeCode(targetNode, typeLabel) {
    if (nodeHasBlankInputs(targetNode)) {
      return FILL_IN_TYPE_CODE;
    }

    const normalizedLabel = typeLabel && normalizeTypeLabel(typeLabel);
    if (normalizedLabel && TYPE_NAME_TO_CODE[normalizedLabel]) {
      return TYPE_NAME_TO_CODE[normalizedLabel];
    }

    if (typeLabel && TYPE_NAME_TO_CODE[typeLabel]) {
      return TYPE_NAME_TO_CODE[typeLabel];
    }

    const fromClass = extractTypeCodeFromClasses(targetNode);
    if (fromClass) {
      return fromClass;
    }

    return 0;
  }

  function extractTypeCodeFromClasses(node) {
    if (!node) {
      return 0;
    }

    const checkList = [node, node.querySelector && node.querySelector(".question-title-html")].filter(Boolean);
    const regex = /question-type-(\d+)/;

    for (const element of checkList) {
      const classAttr = element.getAttribute && element.getAttribute("class");
      if (!classAttr) {
        continue;
      }
      const match = classAttr.match(regex);
      if (match) {
        const code = Number(match[1]);
        if (!Number.isNaN(code)) {
          return code;
        }
      }
    }

    return 0;
  }

  function normalizeTypeLabel(label) {
    if (!label || typeof label !== "string") {
      return "";
    }
    return label
      .replace(/[（）()【】]/g, (ch) => ({ "（": "(", "）": ")", "【": "(", "】": ")" }[ch] || ch))
      .replace(/\([^)]*\)/g, "")
      .replace(/（[^）]*）/g, "")
      .trim();
  }

  function nodeHasBlankInputs(node) {
    if (!node || typeof node.querySelectorAll !== "function") {
      return false;
    }
    
    // 检查常见的填空题输入元素类名
    const inputs = node.querySelectorAll(".blank-input, .input-wrapper input, input[type='text']");
    if (inputs && inputs.length) {
      return true;
    }
    
    // 检查更广泛的节点，包括题目标题等
    const checkNodes = [node];
    if (node.querySelector) {
      const titleNode = node.querySelector(".question-title-html");
      if (titleNode) checkNodes.push(titleNode);
      
      const fillBlankNodes = node.querySelectorAll(".fill-blank");
      fillBlankNodes.forEach(n => checkNodes.push(n));
    }
    
    for (const checkNode of checkNodes) {
      const innerHTML = checkNode.innerHTML || "";
      if (looksLikeFillBlankHtml(innerHTML)) {
        return true;
      }
      
      // 检查是否有输入框元素
      if (checkNode.querySelectorAll && checkNode.querySelectorAll("input").length > 0) {
        return true;
      }
    }
    
    return false;
  }

  function looksLikeFillBlankHtml(html) {
    if (!html || typeof html !== "string") {
      return false;
    }
    const lower = html.toLowerCase();
    if (lower.includes("blank-input") || lower.includes("input-wrapper") || lower.includes("blankquestion")) {
      return true;
    }
    if (/<input[^>]*>/.test(lower)) {
      return true;
    }
    // 增强对填空题的识别，包括中文括号和下划线模式
    return /_{3,}/.test(html) || /\(\s*\)/.test(html) || /（\s*）/.test(html);
  }

  function hasFillBlankInputs(titleHtml) {
    return looksLikeFillBlankHtml(titleHtml);
  }

  function renderFillQuestionText(titleHtml, answers) {
    if (!titleHtml) {
      if (!answers || !answers.length) {
        return "";
      }
      return answers
        .map((ans) => (ans ? `{${ans}}` : "{___}"))
        .join(" ");
    }

    const container = document.createElement("div");
    container.innerHTML = titleHtml;
    const blanks = container.querySelectorAll("span.input-wrapper, input");
    blanks.forEach((node, idx) => {
      const ans = answers && answers[idx] ? answers[idx] : "";
      const replacement = document.createTextNode(ans ? `{${ans}}` : "{___}");
      node.parentNode && node.parentNode.replaceChild(replacement, node);
    });

    const raw = container.innerHTML;
    const text = htmlToText(raw);
    if (!blanks.length && answers && answers.length) {
      const extra = answers.map((ans) => (ans ? `{${ans}}` : "{___}")).join(" ");
      return `${text} ${extra}`.trim();
    }
    if (answers && answers.length > blanks.length) {
      const extra = answers.slice(blanks.length).map((ans) => (ans ? `{${ans}}` : "{___}"))
        .join(" ");
      return `${text} ${extra}`.trim();
    }
    return text;
  }

  function shouldTreatAsFillBlank(questionTypeCode, titleHtml, choices) {
    if (Number(questionTypeCode) === FILL_IN_TYPE_CODE) {
      return true;
    }

    const hasChoices = Array.isArray(choices) && choices.length > 0;
    if (!hasChoices) {
      return true;
    }

    return hasFillBlankInputs(titleHtml);
  }

  function summarizeSubQuestionAnswers(subList = []) {
    if (!Array.isArray(subList) || !subList.length) {
      return [];
    }
    const total = subList.length;
    return subList
      .map((sub, idx) => {
        const label = total > 1 ? `子题${idx + 1}` : `子题${idx + 1}`;
        const values = Array.isArray(sub.correctAnswerList)
          ? sub.correctAnswerList.map((item) => htmlToText(String(item))).filter(Boolean)
          : sub.answer
            ? [htmlToText(String(sub.answer))]
            : [];
        if (!values.length) {
          return null;
        }
        return `${label}: ${values.join(" | ")}`;
      })
      .filter(Boolean);
  }

  function collectAnswerValues(answerResp) {
    if (!answerResp || !answerResp.success || !answerResp.data) {
      return [];
    }

    const data = answerResp.data || {};
    const values = [];

    if (Array.isArray(data.correctAnswerList) && data.correctAnswerList.length) {
      data.correctAnswerList.forEach((item) => {
        const text = htmlToText(String(item));
        if (text) {
          values.push(text);
        }
      });
    } else if (typeof data.answer !== "undefined" && data.answer !== null) {
      const text = htmlToText(String(data.answer));
      if (text) {
        values.push(text);
      }
    }

    const subList = data.subQuestionAnswerDTOList;
    if (Array.isArray(subList) && subList.length) {
      const summarized = summarizeSubQuestionAnswers(subList);
      values.push(...summarized);
    }

    return values;
  }

  function extractQuestionMeta(node, pageTitle) {
    const wrapper = node.classList && node.classList.contains("question-wrapper")
      ? node
      : node.closest && node.closest(".question-wrapper");
    const questionWrapper = wrapper || (node.querySelector && node.querySelector(".question-wrapper"));

    const questionId = (() => {
      if (!questionWrapper) {
        const hiddenId = node.querySelector && node.querySelector("input[name='questionId']");
        if (hiddenId && hiddenId.value) {
          return hiddenId.value;
        }
        const dataId = node.getAttribute && node.getAttribute("data-question-id");
        return dataId || "";
      }
      if (questionWrapper.id) {
        return questionWrapper.id.replace(/^question/i, "");
      }
      return questionWrapper.getAttribute("data-id") || "";
    })();

    if (!questionId) {
      return null;
    }

    const typeNode =
      (node.querySelector && node.querySelector(".question-type-tag")) ||
      (node.querySelector && node.querySelector(".gray"));
    const typeLabelRaw = typeNode ? htmlToText(typeNode.textContent || "").replace(/\s/g, "") : "";
    const typeLabel = normalizeTypeLabel(typeLabelRaw);

    const titleNode =
      (node.querySelector && node.querySelector(".question-title")) ||
      (node.querySelector && node.querySelector(".richtext-container.question-title")) ||
      (node.querySelector && node.querySelector(".question-body")) ||
      (node.querySelector && node.querySelector(".title"));
    const titleHtml = titleNode ? titleNode.innerHTML : node.innerHTML || "";
    const titleText = htmlToText(titleHtml) || "(题干缺失)";

    const questionTypeCode = detectQuestionTypeCode(questionWrapper || node, typeLabel);
    const questionTypeName = QUESTION_TYPE_NAME[questionTypeCode] || typeLabelRaw || "未知题型";

    const choices = extractChoicesFromNode(node);

    return {
      pageTitle,
      questionId,
      questionTypeCode,
      questionTypeName,
      titleText,
      choices
    };
  }

  function extractChoicesFromNode(node) {
    const selectors = [
      ".choice-list li",
      ".choice-item",
      ".options li",
      ".question-option",
      ".option-item",
      "li.option",
      ".ul-radio li",
      "label"
    ];
    const results = [];
    const seen = new Set();
    let idx = 0;

    for (const selector of selectors) {
      const items = node.querySelectorAll ? node.querySelectorAll(selector) : [];
      if (!items.length) {
        continue;
      }
      items.forEach((item) => {
        const text = htmlToText(item.innerHTML || "");
        if (!text) {
          return;
        }
        const signature = text.slice(0, 120);
        if (seen.has(signature)) {
          return;
        }
        seen.add(signature);
        const label =
          htmlToText(
            (item.querySelector && item.querySelector(".option-prefix"))
              ? item.querySelector(".option-prefix").textContent || ""
              : (item.getAttribute && item.getAttribute("data-option")) || ""
          ) || String.fromCharCode(65 + idx);
        results.push({ label, text });
        idx += 1;
      });
      if (results.length) {
        break;
      }
    }

    return results;
  }

  async function fetchQuestionAnswer(questionId, parentId) {
    if (!questionId) {
      return { answer: "", typeCode: null };
    }
    const resp = await requestEndpoint("question_answer", {
      questionId,
      parentId
    });
    return {
      answer: extractAnswer(resp),
      typeCode: extractQuestionTypeFromAnswer(resp)
    };
  }

  function extractQuestionTypeFromAnswer(answerResp) {
    const data = answerResp && answerResp.data;
    if (!data || typeof data !== "object") {
      return null;
    }

    const candidates = [
      data.questionType,
      data.questiontype,
      data.type,
      data.questionTypeCode,
      data.questionDto && data.questionDto.questionType,
      data.questionDto && data.questionDto.type,
      data.question && data.question.questionType,
      data.question && data.question.type
    ];

    for (const candidate of candidates) {
      const num = Number(candidate);
      if (Number.isFinite(num) && num > 0) {
        return num;
      }
    }

    return null;
  }

  function getActivePageId() {
    const active = document.querySelector(".page-name.active");
    if (!active) {
      return "";
    }
    const li = active.closest("li[id]");
    if (li && li.id) {
      return li.id;
    }
    return active.getAttribute("data-id") || active.textContent || "";
  }

  function getActivePageTitle() {
    const active = document.querySelector(".page-name.active");
    if (!active) {
      return "未命名页面";
    }
    return htmlToText(active.textContent || "未命名页面") || "未命名页面";
  }

  function getCurrentParentId() {
    const active = document.querySelector(".page-name.active");
    if (!active) {
      return "";
    }
    const li = active.closest("li[id]");
    if (!li || !li.id) {
      return "";
    }
    return li.id.replace(/^page/i, "");
  }

  async function goToNextPage() {
    const nextBtn = document.querySelector(".next-page-btn.cursor");
    if (!nextBtn) {
      return false;
    }
    if (
      nextBtn.classList.contains("disabled") ||
      nextBtn.hasAttribute("disabled") ||
      nextBtn.getAttribute("aria-disabled") === "true"
    ) {
      return false;
    }
    nextBtn.click();
    logDebug("Clicked next page button");
    await delay(80);
    return true;
  }

  async function waitForPageChange(previousPageId) {
    const maxAttempts = 40;
    for (let i = 0; i < maxAttempts; i += 1) {
      await delay(250);
      const current = getActivePageId();
      if (current && current !== previousPageId) {
        logDebug("Page changed", { previousPageId, current });
        await delay(200);
        return;
      }
    }
    logDebug("Page did not change within timeout", previousPageId);
  }

  function buildQuestionBank(jsonData) {
    const result = [];
    if (!jsonData || !Array.isArray(jsonData.chapters)) {
      return result;
    }

    const isChoiceType = function (q) {
      const type = q.question_type;
      const inferredFill = Boolean(q.is_fill_question);
      if (inferredFill) {
        return false;
      }
      return type === 1 || type === 2 || type === 3;
    };
    const isJudgeType = function (q) {
      return q.question_type === 4;
    };
    const isBlankType = function (q) {
      return q.is_fill_question || q.question_type === 5 || q.question_type === 17;
    };
    const isQaType = function (q) {
      return q.question_type === 6;
    };

    for (const chapter of jsonData.chapters) {
      const units = Array.isArray(chapter.units) ? chapter.units : [];
      for (const unit of units) {
        const questions = Array.isArray(unit.questions) ? unit.questions : [];
        for (const q of questions) {
          const title = q.rendered_title || q.title || "";
          const rawAnswer = (q.answer || "").trim();
          const answerList = Array.isArray(q.answer_list) ? q.answer_list : [];

          if (isChoiceType(q)) {
            const options = Array.isArray(q.options)
              ? q.options.map((o) => o.text || "")
              : [];
            let ans = rawAnswer;
            if (ans) {
              ans = ans.replace(/\s*\|\s*/g, "");
              ans = ans.replace(/[^A-Za-z]/g, "");
              ans = ans.toUpperCase();
            }
            result.push({
              题型: "选择题",
              题干: title,
              选项: options,
              答案: ans || rawAnswer,
              解析: ""
            });
          } else if (isJudgeType(q)) {
            let ans = rawAnswer;
            if (/^(T|对|正确)/i.test(rawAnswer)) {
              ans = "正确";
            } else if (/^(F|错|错误)/i.test(rawAnswer)) {
              ans = "错误";
            }
            result.push({
              题型: "判断题",
              题干: title,
              答案: ans || rawAnswer,
              解析: ""
            });
          } else if (isBlankType(q)) {
            const parts = answerList.length
              ? answerList
              : rawAnswer
                ? rawAnswer.split(/[\|；;，,]+/).map((s) => s.trim()).filter(Boolean)
                : [];
            const answersInBraces = parts.length
              ? parts.map((a) => "{" + a + "}").join("")
              : "";
            result.push({
              题型: "填空题",
              题干: title + answersInBraces,
              答案: parts.join(" | ") || rawAnswer,
              解析: ""
            });
          } else if (isQaType(q)) {
            result.push({
              题型: "问答题",
              题干: title,
              答案: rawAnswer,
              解析: ""
            });
          }
        }
      }
    }

    return result;
  }

  function buildAutoMarkdown(pageResults) {
    const courseTitle = getCourseName();
    const lines = [];
    lines.push(`# ${courseTitle || "课件"} - 自动导出题目\n`);
    lines.push(`导出时间: ${new Date().toLocaleString()}\n`);

    let counter = 0;
    for (const page of pageResults) {
      lines.push(`## ${page.pageTitle || "未命名页面"}\n`);
      for (const question of page.questions) {
        counter += 1;
        lines.push(`### ${counter}. (${question.questionTypeName}) QID: ${question.questionId}\n`);
        lines.push(`**题干:**\n${question.titleText}\n`);
        if (question.choices && question.choices.length) {
          lines.push("**选项:**");
          question.choices.forEach((choice) => {
            lines.push(`- ${choice.label}. ${choice.text || "(无内容)"}`);
          });
          lines.push("");
        }
        lines.push(`**正确答案:**\n${question.answerText || "未获取到"}\n---\n`);
      }
    }

    return lines.join("\n");
  }

  function getCourseName() {
    const titleEl =
      document.querySelector(".course-title") ||
      document.querySelector(".course-name") ||
      document.querySelector(".class-name");
    if (titleEl) {
      const text = htmlToText(titleEl.textContent || "");
      if (text) {
        return text;
      }
    }
    const header = document.querySelector("title");
    return header ? htmlToText(header.textContent || "") : "课件";
  }

  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function extractIdsFromUrl() {
    const url = new URL(window.location.href);
    const courseId = url.searchParams.get("courseId") || url.searchParams.get("courseid");
    const classId = url.searchParams.get("classId") || url.searchParams.get("classid");
    return { courseId, classId };
  }

  function detectEnvironment(host) {
    if (host.includes("dgut.edu.cn")) {
      return "dgut";
    }
    return "default";
  }

  function sanitizeFilename(name) {
    return (name || "untitled")
      .replace(/[<>:"/\\|?*]/g, "_")
      .replace(/\s+/g, "_")
      .replace(/_+/g, "_")
      .slice(0, 120);
  }

  function htmlToText(html) {
    if (!html || typeof html !== "string") {
      return "";
    }
    const div = document.createElement("div");
    div.innerHTML = html;
    const text = div.textContent || div.innerText || "";
    return text.replace(/\u00A0/g, " ").trim();
  }

  function extractAnswer(answerResp) {
    if (!answerResp || !answerResp.success || !answerResp.data) {
      return "";
    }
    const data = answerResp.data;
    if (Array.isArray(data.correctAnswerList) && data.correctAnswerList.length) {
      return data.correctAnswerList
        .map((ans) => htmlToText(String(ans)))
        .filter(Boolean)
        .join(" | ");
    }
    if (typeof data.answer !== "undefined") {
      return htmlToText(String(data.answer));
    }
    if (Array.isArray(data.subQuestionAnswerDTOList) && data.subQuestionAnswerDTOList.length) {
      return data.subQuestionAnswerDTOList
        .map((sub, idx) => {
          const label = sub.sort || idx + 1;
          const ans = Array.isArray(sub.correctAnswerList)
            ? sub.correctAnswerList.map((item) => htmlToText(String(item))).join(" | ")
            : htmlToText(String(sub.correctAnswerList || ""));
          return `${label}: ${ans}`;
        })
        .join("; ");
    }
    return "";
  }

  function normalizeDirectory(raw) {
    if (!raw || typeof raw !== "object") {
      return { chapters: [] };
    }

    if (Array.isArray(raw.items) && raw.coursename) {
      const chapters = raw.items.map((item) => ({
        nodetitle: item.title,
        nodeid: item.nodeId || item.nodeid || item.id,
        items: item.children || item.items || []
      }));
      return { coursename: raw.coursename, chapters };
    }

    if (!Array.isArray(raw.chapters) && Array.isArray(raw.items)) {
      return {
        coursename: raw.coursename || raw.courseName || "",
        chapters: raw.items.map((item) => ({
          nodetitle: item.title,
          nodeid: item.nodeId || item.nodeid || item.id,
          items: item.items || item.children || []
        }))
      };
    }

    return raw;
  }

  function normalizeChapterContent(raw) {
    if (!raw || typeof raw !== "object") {
      return [];
    }

    if (Array.isArray(raw.wholepageItemDTOList)) {
      return raw.wholepageItemDTOList;
    }

    if (Array.isArray(raw.items)) {
      return raw.items.map((item) => ({
        wholepageDTOList: (item.coursepages || []).map((page) => ({
          contentType: page.contentType,
          id: page.relationid || page.id,
          content: page.title,
          coursepageDTOList: page.children || page.coursepages || []
        }))
      }));
    }

    if (Array.isArray(raw.coursepages)) {
      return raw.coursepages.map((page) => ({
        wholepageDTOList: [
          {
            contentType: page.contentType,
            id: page.relationid || page.id,
            content: page.title,
            coursepageDTOList: page.children || page.coursepages || []
          }
        ]
      }));
    }

    return [];
  }

  function normalizeQuestions(coursepage) {
    if (!coursepage) {
      return [];
    }

    if (Array.isArray(coursepage.questionDTOList)) {
      return coursepage.questionDTOList;
    }

    if (Array.isArray(coursepage.questions)) {
      return coursepage.questions;
    }

    if (Array.isArray(coursepage.children)) {
      return coursepage.children.flatMap((child) => normalizeQuestions(child));
    }

    return [];
  }

  async function requestEndpoint(key, payload) {
    const envOverrides = ENV_ENDPOINTS[ENV] && ENV_ENDPOINTS[ENV][key];
    const useEnvOnly = Array.isArray(envOverrides) && envOverrides.length > 0;
    const paths = useEnvOnly ? [...envOverrides] : [...(ENDPOINTS[key] || [])];

    let lastError = null;
    for (const descriptor of paths) {
      const { path, method = "POST" } = descriptor;
      const resolvedPath = typeof path === "function" ? path(payload || {}) : path;
      try {
        const resp = await fetchJson(`${API_BASE}${resolvedPath}`, payload, method);
        if (resp && (resp.success === true || resp.code === 200 || typeof resp === "object")) {
          return wrapResponse(resp);
        }
        lastError = new Error(`接口返回异常: ${JSON.stringify(resp)}`);
      } catch (err) {
        lastError = err;
      }
    }
    if (lastError) {
      throw lastError;
    }
    throw new Error(`未找到可用的接口路径: ${key}`);
  }

  async function fetchJson(url, payload, method) {
    const isGet = method === "GET";
    const fetchOptions = {
      method,
      credentials: "include",
      headers: {
        "Content-Type": "application/json;charset=UTF-8"
      }
    };

    const authToken = getAuthToken();
    if (authToken) {
      fetchOptions.headers["ua-authorization"] = authToken;
      fetchOptions.headers["Authorization"] = authToken;
    }

    if (isGet) {
      delete fetchOptions.headers["Content-Type"];
    } else {
      fetchOptions.body = JSON.stringify(payload || {});
    }

    const response = await fetch(url, fetchOptions);

    if (!response.ok) {
      if (response.status === 401 || response.status === 404) {
        console.warn(`[Ulearning Markdown Exporter] ${response.status} for ${url}`);
      }
      throw new Error(`HTTP ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  function getAuthToken() {
    const candidates = [];

    try {
      if (window.localStorage) {
        candidates.push(localStorage.getItem("authorization"));
        candidates.push(localStorage.getItem("ua-authorization"));
        candidates.push(localStorage.getItem("token"));
      }
      if (window.sessionStorage) {
        candidates.push(sessionStorage.getItem("authorization"));
        candidates.push(sessionStorage.getItem("ua-authorization"));
        candidates.push(sessionStorage.getItem("token"));
      }
    } catch (err) {
      console.warn("[Ulearning Markdown Exporter] Failed to access storage for token", err);
    }

    const cookie = document.cookie || "";
    const cookieMatches = cookie.match(/(?:AUTHORIZATION|token|ua-authorization|uaAuthorization)=([^;]+)/gi);
    if (cookieMatches) {
      cookieMatches.forEach((entry) => {
        const parts = entry.split("=");
        if (parts.length === 2) {
          candidates.push(parts[1]);
        }
      });
    }

    return candidates.find((item) => typeof item === "string" && item.trim().length > 0) || "";
  }

  function wrapResponse(resp) {
    if (typeof resp !== "object" || resp === null) {
      return { success: false, data: null };
    }
    if (typeof resp.success === "boolean") {
      return resp;
    }
    if (typeof resp.code === "number") {
      return {
        success: resp.code === 200,
        data: resp.data,
        message: resp.message || resp.msg || ""
      };
    }
    return {
      success: true,
      data: resp.data || resp
    };
  }

  async function downloadMarkdown(filename, content) {
    logDebug("Starting download", { filename, contentLength: content.length });

    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const blobUrl = URL.createObjectURL(blob);

    logDebug("Blob created", { blobUrl, blobSize: blob.size });

    logDebug("Using link download");
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    link.style.display = "none";
    document.body.appendChild(link);
    logDebug("Link created and appended");
    link.click();
    logDebug("Link clicked");

    await delay(100);

    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
    logDebug("Link removed and blob revoked");
  }

  async function downloadJson(filename, content) {
    logDebug("Starting JSON download", { filename, contentLength: content.length });

    const blob = new Blob([content], { type: "application/json;charset=utf-8" });
    const blobUrl = URL.createObjectURL(blob);

    logDebug("JSON Blob created", { blobUrl, blobSize: blob.size });

    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();

    await delay(100);

    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
    logDebug("JSON download completed");
  }

  function notify(message, silent) {
    if (typeof GM_notification === "function") {
      GM_notification({
        title: "Ulearning Markdown Exporter",
        text: message,
        silent: !!silent
      });
      return;
    }
    if (!silent) {
      alert(message);
    } else {
      console.log("[Ulearning Markdown Exporter]", message);
    }
  }
})();
