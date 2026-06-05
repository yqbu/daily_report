(() => {
  "use strict";

  const CONFIG = {
    browserEventEndpoint: "http://127.0.0.1:8765/api/events/browser",
    legacyAiPromptEndpoint: "http://127.0.0.1:8765/api/ai-prompt",
    fallbackToLegacyAiPromptEndpoint: true,
    authToken: "",
    collectCopy: false,
    minPromptLength: 2,
    minSearchLength: 1,
    minDwellSeconds: 8,
    dedupeWindowMs: 5000,
    maxPreviewLength: 300,
    maxPromptPreviewLength: 500,
    debug: false,
  };

  const state = {
    pageId: makeClientId("page"),
    enteredAt: Date.now(),
    lastUrl: location.href,
    lastSentHash: "",
    lastSentAt: 0,
    active: !document.hidden,
    sentEventKeys: new Map(),
  };

  function log(...args) {
    if (CONFIG.debug) {
      console.log("[DailyReportBrowserCollector]", ...args);
    }
  }

  function nowIso() {
    return new Date().toISOString();
  }

  function makeClientId(prefix) {
    const random = Math.random().toString(16).slice(2);
    return `${prefix}-${Date.now()}-${random}`;
  }

  function trimText(value, maxLength = CONFIG.maxPreviewLength) {
    return String(value || "")
      .replace(/\u0000/g, "")
      .replace(/\r\n?/g, "\n")
      .replace(/[ \t]+/g, " ")
      .replace(/\n{3,}/g, "\n\n")
      .trim()
      .slice(0, maxLength);
  }

  function normalizeUrl(value) {
    const text = String(value || "").trim();
    if (!/^https?:\/\//i.test(text)) return "";
    return text.slice(0, 2000);
  }

  function hostname() {
    return location.hostname.toLowerCase();
  }

  function shouldIgnorePage() {
    const protocol = location.protocol;
    if (protocol !== "http:" && protocol !== "https:") return true;
    const host = hostname();
    if (!host || host === "localhost" || host === "127.0.0.1" || host.endsWith(".local")) return true;
    if (/^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(location.hostname)) return true;
    return isSensitiveHost(host) || isSensitiveUrl(location.href);
  }

  function isSensitiveHost(host) {
    return [
      "bank",
      "pay",
      "checkout",
      "alipay",
      "paypal",
      "stripe",
      "login",
      "account",
      "password",
      "auth",
      "sso",
      "icloud",
      "mail",
      "gmail",
      "outlook",
    ].some((part) => host.includes(part));
  }

  function isSensitiveUrl(url) {
    const lower = String(url || "").toLowerCase();
    return [
      "token=",
      "access_token",
      "authorization",
      "password",
      "passwd",
      "secret",
      "apikey",
      "api_key",
      "cookie",
    ].some((part) => lower.includes(part));
  }

  function looksSensitiveText(text) {
    const sample = String(text || "").toLowerCase();
    return [
      "api key",
      "apikey",
      "api_key",
      "authorization:",
      "bearer ",
      "password",
      "passwd",
      "secret",
      "token",
      "cookie",
    ].some((part) => sample.includes(part));
  }

  function basePayload(eventType, extra = {}) {
    return {
      record_type: extra.record_type || recordTypeFromEventType(eventType),
      event_type: eventType,
      timestamp: nowIso(),
      url: normalizeUrl(location.href),
      title: trimText(document.title || "", 300),
      domain: hostname(),
      referrer: normalizeUrl(document.referrer),
      source: "edge_extension",
      client_event_id: makeClientId(eventType),
      payload: {
        page_id: state.pageId,
        path: location.pathname.slice(0, 300),
        sensitive_hint: isSensitiveUrl(location.href),
        ...extra.payload,
      },
      ...extra,
    };
  }

  function recordTypeFromEventType(eventType) {
    if (eventType === "ai_prompt_submit") return "ai_prompt";
    return eventType;
  }

  function headers() {
    const result = { "Content-Type": "application/json" };
    if (CONFIG.authToken) {
      result["X-Daily-Report-Token"] = CONFIG.authToken;
    }
    return result;
  }

  async function sendBrowserEvent(eventType, extra = {}, options = {}) {
    if (shouldIgnorePage()) return false;
    const payload = basePayload(eventType, extra);
    const dedupeKey = `${eventType}:${payload.url}:${payload.search_query || ""}:${payload.content_preview || ""}`;
    const lastAt = state.sentEventKeys.get(dedupeKey) || 0;
    if (Date.now() - lastAt < CONFIG.dedupeWindowMs) return false;
    state.sentEventKeys.set(dedupeKey, Date.now());
    if (state.sentEventKeys.size > 100) {
      state.sentEventKeys.clear();
    }

    try {
      const response = await fetch(CONFIG.browserEventEndpoint, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(payload),
        keepalive: Boolean(options.keepalive),
      });
      log("browser event posted", eventType, response.status);
      return response.ok;
    } catch (error) {
      log("browser event post failed", eventType, error);
      return false;
    }
  }

  function sendPageView(reason) {
    const searchInfo = detectSearchInfo(location.href);
    const eventType = searchInfo ? "search" : "page_view";
    void sendBrowserEvent(eventType, {
      search_engine: searchInfo?.engine,
      search_query: searchInfo?.query,
      payload: { reason },
    });
  }

  function flushDwell(eventType = "dwell_time", keepalive = false) {
    if (shouldIgnorePage()) return;
    const durationSec = Math.max(0, Math.round((Date.now() - state.enteredAt) / 1000));
    if (durationSec < CONFIG.minDwellSeconds && eventType === "dwell_time") return;
    void sendBrowserEvent(
      eventType,
      {
        duration_sec: durationSec,
        payload: { page_id: state.pageId },
      },
      { keepalive }
    );
  }

  function detectSearchInfo(urlText) {
    let parsed;
    try {
      parsed = new URL(urlText);
    } catch (_) {
      return null;
    }
    const host = parsed.hostname.toLowerCase();
    const path = parsed.pathname;
    const params = parsed.searchParams;
    const candidates = [
      { match: host.includes("google.") && path.startsWith("/search"), engine: "google", key: "q" },
      { match: host.includes("bing.com") && path.startsWith("/search"), engine: "bing", key: "q" },
      { match: host.includes("baidu.com") && path.startsWith("/s"), engine: "baidu", key: "wd" },
      { match: host.includes("duckduckgo.com"), engine: "duckduckgo", key: "q" },
      { match: host === "github.com" && path.startsWith("/search"), engine: "github", key: "q" },
      { match: host === "search.bilibili.com", engine: "bilibili", key: "keyword" },
    ];
    const found = candidates.find((item) => item.match);
    if (!found) return null;
    const query = trimText(params.get(found.key), 200);
    if (query.length < CONFIG.minSearchLength || looksSensitiveText(query)) return null;
    return { engine: found.engine, query };
  }

  function onVisibilityChange() {
    if (document.hidden) {
      if (state.active) {
        state.active = false;
        flushDwell("tab_inactive", true);
      }
      return;
    }
    state.active = true;
    state.enteredAt = Date.now();
    void sendBrowserEvent("tab_active");
  }

  function resetPageState(reason) {
    flushDwell("dwell_time", true);
    state.pageId = makeClientId("page");
    state.enteredAt = Date.now();
    state.lastUrl = location.href;
    sendPageView(reason);
  }

  function patchHistory() {
    for (const methodName of ["pushState", "replaceState"]) {
      const original = history[methodName];
      history[methodName] = function patchedHistoryMethod(...args) {
        const result = original.apply(this, args);
        window.setTimeout(() => {
          if (location.href !== state.lastUrl) {
            resetPageState(methodName);
          }
        }, 0);
        return result;
      };
    }
    window.addEventListener("popstate", () => {
      window.setTimeout(() => {
        if (location.href !== state.lastUrl) {
          resetPageState("popstate");
        }
      }, 0);
    });
  }

  function getPlatform() {
    const host = hostname();
    if (host.includes("deepseek")) return "DeepSeek";
    if (host.includes("chatgpt") || host.includes("openai")) return "ChatGPT";
    return "Unknown";
  }

  function isAiPage() {
    const host = hostname();
    return host.includes("chatgpt.com") || host.includes("chat.openai.com") || host.includes("chat.deepseek.com");
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
      if (el.type && String(el.type).toLowerCase() === "password") return "";
      return trimText(el.value || "", 2000);
    }
    return trimText(el.innerText || el.textContent || "", 2000);
  }

  function getTextboxCandidates() {
    const selectors = ["textarea", "#prompt-textarea", "[contenteditable='true']", "[role='textbox']", ".ProseMirror"];
    const seen = new Set();
    const candidates = [];
    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        if (seen.has(el)) continue;
        seen.add(el);
        if (isVisible(el)) candidates.push(el);
      }
    }
    return candidates;
  }

  function readCurrentPrompt() {
    if (!isAiPage()) return "";
    const active = document.activeElement;
    if (active) {
      const activeText = readEditableText(active);
      if (activeText.length >= CONFIG.minPromptLength) return activeText;
      const parent = active.closest?.("textarea, input, [contenteditable='true'], [role='textbox'], .ProseMirror");
      const parentText = readEditableText(parent);
      if (parentText.length >= CONFIG.minPromptLength) return parentText;
    }
    const candidates = getTextboxCandidates();
    for (const el of candidates.reverse()) {
      const text = readEditableText(el);
      if (text.length >= CONFIG.minPromptLength) return text;
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
    if (!isAiPage()) return false;
    if (event.key !== "Enter" || event.isComposing || event.shiftKey) return false;
    const target = event.target;
    return Boolean(target?.closest?.("textarea, input, [contenteditable='true'], [role='textbox'], .ProseMirror"));
  }

  function simpleHash(text) {
    let hash = 5381;
    for (let i = 0; i < text.length; i += 1) {
      hash = (hash << 5) + hash + text.charCodeAt(i);
      hash |= 0;
    }
    return String(hash >>> 0);
  }

  async function postPrompt(promptText, trigger) {
    const normalized = trimText(promptText, 8000);
    if (normalized.length < CONFIG.minPromptLength || looksSensitiveText(normalized)) return;
    const now = Date.now();
    const hash = simpleHash(normalized);
    if (hash === state.lastSentHash && now - state.lastSentAt < CONFIG.dedupeWindowMs) {
      return;
    }
    state.lastSentHash = hash;
    state.lastSentAt = now;

    const clientEventId = makeClientId("ai-prompt");
    const payload = {
      platform: getPlatform(),
      conversation_url: normalizeUrl(location.href),
      page_title: trimText(document.title || "", 300),
      prompt_text: normalized,
      submitted_at: nowIso(),
      client_event_id: clientEventId,
      source: "edge_extension",
      trigger,
    };
    const posted = await sendBrowserEvent("ai_prompt_submit", {
      record_type: "ai_prompt",
      title: payload.page_title,
      content_preview: trimText(normalized, CONFIG.maxPromptPreviewLength),
      client_event_id: `${clientEventId}-event`,
      payload: { trigger, platform: getPlatform() },
    });
    if (posted || !CONFIG.fallbackToLegacyAiPromptEndpoint) return;

    try {
      const response = await fetch(CONFIG.legacyAiPromptEndpoint, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(payload),
      });
      log("legacy AI prompt posted", response.status, trigger);
    } catch (error) {
      log("legacy AI prompt post failed", error);
    }
  }

  function capturePromptSoon(trigger) {
    const promptText = readCurrentPrompt();
    if (promptText) {
      void postPrompt(promptText, trigger);
    }
  }

  function onCopy() {
    if (!CONFIG.collectCopy || shouldIgnorePage()) return;
    const selection = window.getSelection?.();
    const text = trimText(selection?.toString?.() || "", CONFIG.maxPreviewLength);
    if (!text || looksSensitiveText(text)) return;
    void sendBrowserEvent("copy", {
      content_preview: text,
      payload: { length: text.length },
    });
  }

  if (!shouldIgnorePage()) {
    sendPageView("initial");
    patchHistory();
    document.addEventListener("visibilitychange", onVisibilityChange, true);
    window.addEventListener("focus", () => {
      state.active = true;
      state.enteredAt = Date.now();
      void sendBrowserEvent("tab_active");
    });
    window.addEventListener("blur", () => {
      if (state.active) {
        state.active = false;
        flushDwell("tab_inactive", true);
      }
    });
    window.addEventListener("pagehide", () => flushDwell("page_leave", true));
    window.addEventListener("beforeunload", () => flushDwell("page_leave", true));
    document.addEventListener("copy", onCopy, true);
  }

  document.addEventListener(
    "keydown",
    (event) => {
      if (shouldCaptureEnter(event)) {
        capturePromptSoon("keydown_enter");
      }
    },
    true
  );

  document.addEventListener(
    "click",
    (event) => {
      if (isAiPage() && looksLikeSendButton(event.target)) {
        capturePromptSoon("click_send_button");
      }
    },
    true
  );

  document.addEventListener(
    "submit",
    () => {
      if (isAiPage()) {
        capturePromptSoon("form_submit");
      }
    },
    true
  );

  log("loaded on", location.href);
})();
