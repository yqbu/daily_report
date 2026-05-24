(() => {
  "use strict";

  const CONFIG = {
    endpoint: "http://127.0.0.1:8765/api/ai-prompt",
    // 如果 Python 侧设置了 DAILY_REPORT_AI_PROMPT_TOKEN，这里也填同一个值。
    authToken: "",
    minPromptLength: 2,
    dedupeWindowMs: 5000,
    debug: false,
  };

  const state = {
    lastSentHash: "",
    lastSentAt: 0,
  };

  function log(...args) {
    if (CONFIG.debug) {
      console.log("[DailyReportPromptCollector]", ...args);
    }
  }

  function getPlatform() {
    const host = location.hostname.toLowerCase();
    if (host.includes("deepseek")) return "DeepSeek";
    if (host.includes("chatgpt") || host.includes("openai")) return "ChatGPT";
    return "Unknown";
  }

  function normalizeText(text) {
    return String(text || "")
      .replace(/\u0000/g, "")
      .replace(/\r\n?/g, "\n")
      .replace(/[ \t]+/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function simpleHash(text) {
    let hash = 5381;
    for (let i = 0; i < text.length; i += 1) {
      hash = ((hash << 5) + hash) + text.charCodeAt(i);
      hash |= 0;
    }
    return String(hash >>> 0);
  }

  function isVisible(el) {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  }

  function readEditableText(el) {
    if (!el) return "";

    const tagName = el.tagName ? el.tagName.toLowerCase() : "";
    if (tagName === "textarea" || tagName === "input") {
      return normalizeText(el.value || "");
    }

    return normalizeText(el.innerText || el.textContent || "");
  }

  function getTextboxCandidates() {
    const selectors = [
      "textarea",
      "#prompt-textarea",
      "[contenteditable='true']",
      "[role='textbox']",
      ".ProseMirror"
    ];

    const seen = new Set();
    const candidates = [];

    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        if (seen.has(el)) continue;
        seen.add(el);
        if (!isVisible(el)) continue;
        candidates.push(el);
      }
    }

    return candidates;
  }

  function readCurrentPrompt() {
    const active = document.activeElement;
    if (active) {
      const activeText = readEditableText(active);
      if (activeText.length >= CONFIG.minPromptLength) {
        return activeText;
      }

      const parentTextbox = active.closest?.("textarea, input, [contenteditable='true'], [role='textbox'], .ProseMirror");
      const parentText = readEditableText(parentTextbox);
      if (parentText.length >= CONFIG.minPromptLength) {
        return parentText;
      }
    }

    const candidates = getTextboxCandidates();
    // 发送框一般在页面下方，倒序更容易命中当前输入框。
    for (const el of candidates.reverse()) {
      const text = readEditableText(el);
      if (text.length >= CONFIG.minPromptLength) {
        return text;
      }
    }

    return "";
  }

  function looksLikeSendButton(target) {
    const button = target?.closest?.("button, [role='button']");
    if (!button) return false;

    const attrs = [
      button.getAttribute("aria-label"),
      button.getAttribute("title"),
      button.getAttribute("data-testid"),
      button.getAttribute("data-test-id"),
      button.id,
      button.className,
      button.innerText,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();

    if (!attrs) return false;

    return (
      attrs.includes("send") ||
      attrs.includes("submit") ||
      attrs.includes("发送") ||
      attrs.includes("送信") ||
      attrs.includes("arrow-up") ||
      attrs.includes("paper-airplane")
    );
  }

  function shouldCaptureEnter(event) {
    if (event.key !== "Enter") return false;
    if (event.isComposing) return false;
    // Shift+Enter 通常是换行。
    if (event.shiftKey) return false;

    const target = event.target;
    const textbox = target?.closest?.("textarea, input, [contenteditable='true'], [role='textbox'], .ProseMirror");
    return Boolean(textbox);
  }

  async function postPrompt(promptText, trigger) {
    const normalized = normalizeText(promptText);
    if (normalized.length < CONFIG.minPromptLength) return;

    const now = Date.now();
    const hash = simpleHash(normalized);
    if (hash === state.lastSentHash && now - state.lastSentAt < CONFIG.dedupeWindowMs) {
      log("duplicate ignored", trigger);
      return;
    }

    state.lastSentHash = hash;
    state.lastSentAt = now;

    const payload = {
      platform: getPlatform(),
      conversation_url: location.href,
      page_title: document.title || "",
      prompt_text: normalized,
      submitted_at: new Date().toISOString(),
      client_event_id: `${now}-${Math.random().toString(16).slice(2)}`,
      source: "edge_extension",
      trigger,
    };

    const headers = {
      "Content-Type": "application/json",
    };
    if (CONFIG.authToken) {
      headers["X-Daily-Report-Token"] = CONFIG.authToken;
    }

    try {
      const response = await fetch(CONFIG.endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });
      log("posted", response.status, trigger, normalized.slice(0, 80));
    } catch (error) {
      log("post failed", error);
    }
  }

  function captureSoon(trigger) {
    // keydown/click 捕获阶段触发时，页面还没来得及清空输入框，立即读取最稳。
    const promptText = readCurrentPrompt();
    if (promptText) {
      void postPrompt(promptText, trigger);
    }
  }

  document.addEventListener(
    "keydown",
    (event) => {
      if (shouldCaptureEnter(event)) {
        captureSoon("keydown_enter");
      }
    },
    true
  );

  document.addEventListener(
    "click",
    (event) => {
      if (looksLikeSendButton(event.target)) {
        captureSoon("click_send_button");
      }
    },
    true
  );

  document.addEventListener(
    "submit",
    () => {
      captureSoon("form_submit");
    },
    true
  );

  log("loaded on", location.href);
})();
