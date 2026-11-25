/* PhotoMigrator languages (browser side).
 * The pages are written in English. This script translates the visible texts (and the title, placeholder,
 * aria-label and alt attributes) with the catalog of the chosen language, window.PM_I18N = {"English": "translation"},
 * which /api/i18n/<lang>.js defines before this script runs. Texts are translated as they appear, so the page code
 * does not change. Texts with variable parts are patterns: "{0} users" -> "{0} usuarios".
 * Code, commands, paths and logs are never translated (code, pre, kbd, .command, [data-no-i18n] and editable fields).
 */
(function () {
  "use strict";
  var LANG = window.PM_LANG || "en";
  try { document.documentElement.lang = LANG; } catch (e) { /* ignore */ }
  var D = window.PM_I18N || {};
  window.pmT = function (s) { return s; };

  // Language pickers: every element with data-lang-picker gets a <select> with the supported languages.
  function setupPickers() {
    var langs = window.PM_LANGS || { en: "English" };
    document.querySelectorAll("[data-lang-picker]").forEach(function (host) {
      if (host.querySelector("select")) return;
      var select = document.createElement("select");
      select.className = "lang-picker";
      select.setAttribute("aria-label", "Language");
      select.setAttribute("data-no-i18n", "");
      Object.keys(langs).forEach(function (code) {
        var option = document.createElement("option");
        option.value = code;
        option.textContent = langs[code];
        if (code === LANG) option.selected = true;
        select.appendChild(option);
      });
      select.addEventListener("change", function () {
        fetch("/api/lang", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lang: select.value }) })
          .then(function () { window.location.reload(); })
          .catch(function () { window.location.reload(); });
      });
      host.appendChild(select);
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", setupPickers); else setupPickers();

  if (LANG === "en" || !Object.keys(D).length) return;

  var EDGE = /^([\s:·—–]*)([\s\S]*?)(\s*)$/;   // help texts may start with ": "
  var LETTER = /[A-Za-z]/;
  var SKIP = "code, pre, kbd, samp, script, style, textarea, .command, [data-no-i18n], [contenteditable=true]";
  var ATTRS = ["title", "placeholder", "aria-label", "alt"];

  var PAT = [];
  Object.keys(D).forEach(function (k) {
    if (k.indexOf("{0}") < 0) return;
    var nums = [];
    var src = k.replace(/[.*+?^$()|[\]\\]/g, "\\$&").replace(/\{(\d)\}/g, function (_, n) { nums.push(n); return "([\\s\\S]+?)"; });
    try { PAT.push({ re: new RegExp("^" + src + "$"), tr: D[k], nums: nums, len: k.length }); } catch (e) { /* ignore */ }
  });
  PAT.sort(function (a, b) { return b.len - a.len; });

  function core(s, depth) {
    if (Object.prototype.hasOwnProperty.call(D, s)) return D[s];
    for (var i = 0; i < PAT.length; i++) {
      var p = PAT[i], m = p.re.exec(s);
      if (!m) continue;
      return p.tr.replace(/\{(\d)\}/g, function (_, n) {
        var j = p.nums.indexOf(n), val = j >= 0 ? m[j + 1] : "";
        return depth < 2 ? T(val, depth + 1) : val;
      });
    }
    return null;
  }

  var cache = new Map();
  function T(text, depth) {
    depth = depth || 0;
    if (!text || !LETTER.test(text)) return text;
    var hit = cache.get(text);
    if (hit !== undefined) return hit;
    var m = EDGE.exec(text.replace(/[\s ]+/g, " ")), pre = m[1], c = m[2], suf = m[3];
    var r = core(c, depth);
    if (r == null && / [·|] /.test(c)) {   // "a · b": piece by piece
      var parts = c.split(/( [·|] )/), changed = false;
      for (var i = 0; i < parts.length; i += 2) { var t = T(parts[i], depth + 1); if (t !== parts[i]) { parts[i] = t; changed = true; } }
      if (changed) r = parts.join("");
    }
    if (r == null && depth < 2) {   // several sentences: sentence by sentence
      var sentences = c.split(/(?<=[.:!?])\s+(?=[A-Z("'`])/);
      if (sentences.length > 1) {
        var out = sentences.map(function (s) { return T(s, depth + 1); });
        if (out.some(function (s, i) { return s !== sentences[i]; })) r = out.join(" ");
      }
    }
    var result = r == null ? text : pre + r + suf;
    if (cache.size > 20000) cache.clear();
    cache.set(text, result);
    return result;
  }
  window.pmT = function (s) { return T(String(s == null ? "" : s)); };

  function skipped(el) { return !el || (el.closest && el.closest(SKIP)); }

  function translateNode(node) {
    if (node.nodeType === 3) {
      if (skipped(node.parentElement)) return;
      var v = node.nodeValue, t = T(v);
      if (t !== v) node.nodeValue = t;
      return;
    }
    if (node.nodeType !== 1 || skipped(node)) return;
    ATTRS.forEach(function (a) {
      var v = node.getAttribute(a);
      if (v) { var t = T(v); if (t !== v) node.setAttribute(a, t); }
    });
    if ((node.tagName === "INPUT" && /^(button|submit|reset)$/i.test(node.type)) && node.value) {
      var tv = T(node.value); if (tv !== node.value) node.value = tv;
    }
    var walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: function (n) { return n.nodeType === 1 && n.matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT; }
    });
    var n;
    while ((n = walker.nextNode())) {
      if (n.nodeType === 3) {
        var val = n.nodeValue, tr = T(val);
        if (tr !== val) n.nodeValue = tr;
      } else {
        ATTRS.forEach(function (a) {
          var av = n.getAttribute(a);
          if (av) { var at = T(av); if (at !== av) n.setAttribute(a, at); }
        });
      }
    }
  }

  var busy = false;
  var observer = new MutationObserver(function (records) {
    if (busy) return;
    busy = true;
    try {
      records.forEach(function (r) {
        if (r.type === "childList") r.addedNodes.forEach(translateNode);
        else if (r.type === "characterData") translateNode(r.target);
        else if (r.type === "attributes" && !skipped(r.target)) {
          var v = r.target.getAttribute(r.attributeName);
          if (v) { var t = T(v); if (t !== v) r.target.setAttribute(r.attributeName, t); }
        }
      });
    } finally { busy = false; }
  });

  function start() {
    translateNode(document.body);
    document.title = T(document.title);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ATTRS });
  }
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);

  // Dialogs created with window.alert / confirm / prompt.
  ["alert", "confirm", "prompt"].forEach(function (name) {
    var f = window[name];
    if (typeof f !== "function") return;
    window[name] = function (msg) { var a = Array.prototype.slice.call(arguments); a[0] = T(String(msg == null ? "" : msg)); return f.apply(window, a); };
  });
})();
