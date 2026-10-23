/* Shared by every generated page. Bump the filename when changing this immutable asset. */
(() => {
  if (window.__gkAnalyticsStarted) return;
  window.__gkAnalyticsStarted = true;

  const config = {
    apiKey: "AIzaSyCkW3s7PcJM_UIq6Ub6IMIxRzzkuQGlfZ8",
    authDomain: "beforegoart.firebaseapp.com",
    projectId: "beforegoart",
    storageBucket: "beforegoart.firebasestorage.app",
    messagingSenderId: "448278310866",
    appId: "1:448278310866:web:6ec382056194132bfa620b",
    measurementId: "G-ZHCG565YKK"
  };
  let meta;
  try { meta = JSON.parse(document.querySelector('meta[name="gk-analytics"]').content); } catch { return; }
  const slug = (value) => /^[a-zA-Z0-9_.-]{1,80}$/.test(value || "") ? value : "";
  const path = location.pathname.replace(/index\.html$/, "");
  const campaign = new URLSearchParams();
  const query = new URLSearchParams(location.search);
  for (const key of ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_id", "ref"]) {
    const value = slug(query.get(key));
    if (value) campaign.set(key, value);
  }
  const pageLocation = location.origin + path + (campaign.size ? "?" + campaign : "");
  let referrer = "";
  try { referrer = new URL(document.referrer).origin + "/"; } catch {}
  const context = {
    site_platform: "web", tracking_version: "1", page_path: path,
    page_type: meta.page_type, page_app: meta.page_app,
    page_language: document.documentElement.lang || "en",
    page_location: pageLocation, page_referrer: referrer,
    source_ref: slug(query.get("ref")) || "none"
  };
  const debug = query.get("analytics_debug") === "1";
  // Preview/local visits stay out of production reports unless explicitly debugging.
  if (location.hostname !== "beforego.art" && !debug) return;
  let send = null;
  let queue = [];
  function track(name, params = {}) {
    const event = { ...context, ...params, ...(debug ? { debug_mode: true } : {}) };
    if (send) send(name, event);
    else if (queue.length < 100) queue.push([name, event]);
  }
  const controls = 'a[href],button,input[type="button"],input[type="submit"],[role="button"],summary';
  function sectionOf(el) {
    const section = el.closest('[data-track-section],header,footer,.hero,.end,.appcard,section,form,nav,article,main');
    if (!section) return "body";
    if (["HEADER", "FOOTER"].includes(section.tagName)) return section.tagName.toLowerCase();
    return slug(section.dataset.trackSection || section.id || section.classList[0]) || section.tagName.toLowerCase();
  }
  function controlParams(el) {
    // IDs and DOM positions are stable metadata; labels may contain tool input.
    return {
      section: sectionOf(el),
      control_id: slug(el.dataset.trackId || el.id) || el.tagName.toLowerCase() + "_" + Array.from(document.querySelectorAll(el.tagName === "DETAILS" ? "details" : controls)).indexOf(el),
      control_type: el.tagName.toLowerCase()
    };
  }
  function storeParams(el) {
    if (!el.matches('a[href]')) return null;
    let url;
    try { url = new URL(el.href); } catch { return null; }
    if (!["apps.apple.com", "itunes.apple.com"].includes(url.hostname)) return null;
    if (/\/developer\//.test(url.pathname)) return null;
    const appId = /\/id(\d+)(?:\/|$)/.exec(url.pathname)?.[1];
    if (!appId) return null; // A developer profile is an ordinary outbound link.
    return {
      app_store_id: appId,
      target_app: meta.apps[appId] || "competitor",
      store_campaign: slug(url.searchParams.get("ct")) || "none",
      store_country: /^\/([a-z]{2})\//.exec(url.pathname)?.[1] || "auto"
    };
  }
  function click(event) {
    if (event.type === "auxclick" && event.button !== 1) return;
    const el = event.target.closest?.(controls);
    if (!el || el.matches(':disabled,[aria-disabled="true"]')) return;
    const params = controlParams(el);
    const store = storeParams(el);
    if (store) {
      track(store.target_app === "competitor" ? "competitor_store_click" : "app_store_click", { ...params, ...store });
      return; // One click has exactly one semantic event.
    }
    if (el.tagName === "SUMMARY") return; // toggle records the resulting state.
    if (el.matches('a[href]')) {
      const url = new URL(el.href, location.href);
      const kind = el.closest(".lang-switch") ? "language_switch" :
        url.protocol === "mailto:" || url.protocol === "tel:" ? "contact_click" :
        url.origin !== location.origin ? "outbound_click" : "navigation_click";
      track(kind, {
        ...params,
        link_domain: ["http:", "https:"].includes(url.protocol) ? url.hostname : url.protocol.replace(":", ""),
        // Never collect query strings, fragments, email addresses or free-text share URLs.
        link_path: url.origin === location.origin ? url.pathname : "",
        target_language: slug(el.hreflang || el.lang) || "none"
      });
    } else track("button_click", params);
  }
  document.addEventListener("click", click, true);
  document.addEventListener("auxclick", click, true);
  document.addEventListener("toggle", (event) => {
    if (event.target.tagName !== "DETAILS") return;
    track("content_toggle", { ...controlParams(event.target), expanded: event.target.open });
  }, true);
  const started = new WeakSet();
  document.addEventListener("focusin", (event) => {
    const form = event.target.closest?.("form");
    if (!form || started.has(form)) return;
    started.add(form);
    track("form_start", { form_id: slug(form.id) || "form", section: sectionOf(form) });
  }, true);
  document.addEventListener("submit", (event) => {
    track("form_submit", { form_id: slug(event.target.id) || "form", section: sectionOf(event.target) });
  }, true);
  document.addEventListener("change", (event) => {
    const el = event.target;
    if (!el.matches('input,select,textarea')) return;
    // Only categorical control types; never values, checked state or field names.
    track("control_change", { section: sectionOf(el), control_type: el.type || el.tagName.toLowerCase() });
  }, true);
  const depths = new Set();
  let scrollPending = false;
  document.addEventListener("scroll", () => {
    if (scrollPending) return;
    scrollPending = true;
    requestAnimationFrame(() => {
      scrollPending = false;
      const height = document.documentElement.scrollHeight - innerHeight;
      if (height <= 0) return;
      const percent = Math.round(100 * scrollY / height);
      for (const depth of [25, 50, 75, 90]) {
        if (percent < depth || depths.has(depth)) continue;
        depths.add(depth);
        track("scroll_depth", { percent_scrolled: depth });
      }
    });
  }, { passive: true });
  if ("IntersectionObserver" in window) {
    const impressions = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.5) continue;
        impressions.unobserve(entry.target);
        track("app_store_impression", { ...controlParams(entry.target), ...storeParams(entry.target) });
      }
    }, { threshold: 0.5 });
    for (const el of document.querySelectorAll('a[href]')) {
      const store = storeParams(el);
      if (store && store.target_app !== "competitor") impressions.observe(el);
    }
  }
  track("page_view", { page_title: document.title });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) track("page_view", { page_title: document.title });
  });

  Promise.all([
    import("https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js"),
    import("https://www.gstatic.com/firebasejs/12.4.0/firebase-analytics.js")
  ]).then(async ([appSDK, analyticsSDK]) => {
    if (!await analyticsSDK.isSupported()) { queue = []; return; }
    const app = appSDK.getApps().find((app) => app.name === "goka-web") || appSDK.initializeApp(config, "goka-web");
    const analytics = analyticsSDK.initializeAnalytics(app, {
      config: { send_page_view: false, allow_google_signals: false, allow_ad_personalization_signals: false,
        page_location: pageLocation, page_referrer: referrer, ...context }
    });
    send = (name, params) => analyticsSDK.logEvent(analytics, name, params);
    // Page view precedes queued interactions, including visible store buttons.
    const events = queue;
    queue = [];
    events.filter(([name]) => name === "page_view").concat(events.filter(([name]) => name !== "page_view"))
      .forEach(([name, params]) => send(name, params));
  }).catch(() => { queue = []; }); // A blocked SDK must never interrupt navigation or tools.
})();
