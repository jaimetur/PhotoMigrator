/* PhotoMigrator cloud service: "My tasks", the new task wizard and the task page (uploads, quote, payment,
 * progress and download). Texts are in English; lang/i18n.js translates them as they appear. */
(function () {
  "use strict";
  const root = document.getElementById("service-root");
  if (!root) return;

  const KIND_META = {
    takeout_to_cloud: { title: "Takeout → my cloud", text: "Clean my Takeout and upload it to my photo service.", icon: "cloud", tone: "svc-teal" },
    process_takeout: { title: "Fix my Takeout", text: "Process it and let me download the result.", icon: "download", tone: "svc-blue" },
    cloud_to_cloud: { title: "Cloud → cloud", text: "Move my library from one service to another.", icon: "migrate", tone: "svc-violet" },
  };
  const STATUS_META = {
    draft: ["Waiting for your data", "violet"], analyzing: ["Checking", "blue"], quoted: ["Quote ready", "amber"],
    awaiting_payment: ["Waiting for payment", "amber"], queued: ["In the queue", "indigo"], preparing: ["Starting", "teal"],
    running: ["Running", "teal"], packaging: ["Preparing the download", "teal"], awaiting_download_payment: ["Ready · pay to download", "amber"],
    ready: ["Ready to download", "blue"], completed: ["Completed", "green"], failed: ["Failed", "red"],
    canceled: ["Canceled", "grey"], expired: ["Expired", "grey"], rejected: ["Too large", "red"],
  };
  const FINAL = new Set(["completed", "failed", "canceled", "expired", "rejected"]);
  const params = new URLSearchParams(window.location.search);
  let info = null;
  let pollTimer = null;
  let uploadQueue = Promise.resolve();
  const uploadProgress = {};

  // ---------------------------------------------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------------------------------------------
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === false) return;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "html") node.innerHTML = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    });
    children.flat().forEach((child) => {
      if (child === null || child === undefined || child === false) return;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    });
    return node;
  }
  const icon = (name) => el("span", { class: "svc-ico", html: typeof iconSvg === "function" ? iconSvg(name) : "" });
  const t = (text) => (typeof window.pmT === "function" ? window.pmT(text) : text);

  function formatBytes(size) {
    let value = Math.max(0, Number(size) || 0);
    const units = ["B", "KB", "MB", "GB", "TB"];
    let index = 0;
    while (value >= 1000 && index < units.length - 1) { value /= 1000; index += 1; }
    return `${index < 2 ? Math.round(value) : value.toFixed(1)} ${units[index]}`;
  }
  function formatPrice(cents) {
    return `${(Number(cents || 0) / 100).toFixed(2)} €`;
  }
  function formatWhen(iso) {
    if (!iso) return "-";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return String(iso);
    return date.toLocaleString(window.PM_LANG || undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }
  function formatDuration(seconds) {
    const total = Number(seconds || 0);
    if (total < 3600) {
      const minutes = Math.max(5, Math.ceil(total / 300) * 5);
      return minutes >= 60 ? "About 1 hour" : `About ${minutes} minutes`;
    }
    const hours = Math.ceil(total / 3600);
    if (hours === 1) return "About 1 hour";
    return hours < 48 ? `About ${hours} hours` : `About ${Math.ceil(hours / 24)} days`;
  }
  function estimatePrice(bytes) {
    if (!info) return "";
    const gb = bytes / 1e9;
    return formatPrice(Math.max(info.price_min_cents, Math.ceil(gb * info.price_per_gb_cents)));
  }
  function statusPill(status) {
    const meta = STATUS_META[status] || [status, "grey"];
    return el("span", { class: `svc-pill svc-pill--${meta[1]}`, text: meta[0] });
  }
  function label(service) {
    return (info && info.labels && info.labels[service]) || service;
  }
  async function api(url, options = {}) {
    const response = await apiFetch(url, options);
    return response.status === 204 ? {} : response.json();
  }
  function postJson(url, body) {
    return api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  }
  function go(query) {
    const url = new URL(window.location.href);
    url.search = "";
    Object.entries(query || {}).forEach(([key, value]) => url.searchParams.set(key, value));
    window.history.pushState({}, "", url);
    route();
  }
  function notice(text, tone = "info") {
    return el("div", { class: `svc-notice svc-notice--${tone}` }, icon(tone === "error" ? "alert" : "info"), el("p", { text }));
  }
  function hero(title, subtitle, back, extra) {
    return el("section", { class: "svc-hero" },
      el("div", { class: "svc-hero__text" },
        back ? el("a", { href: "#", class: "svc-hero__back", text: "← My tasks", onclick: (event) => { event.preventDefault(); go({}); } }) : null,
        el("h1", { text: title }),
        subtitle ? el("p", { text: subtitle }) : null),
      extra || null);
  }
  function stopPolling() {
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
  }

  // ---------------------------------------------------------------------------------------------------------------
  // My tasks
  // ---------------------------------------------------------------------------------------------------------------
  function taskAction(task) {
    switch (task.status) {
      case "draft": return task.input_mode === "upload" ? "Continue upload" : "Continue";
      case "quoted": return task.billable ? "Review and pay" : "Review and start";
      case "awaiting_payment": return "Pay";
      case "awaiting_download_payment": return "Pay and download";
      case "ready": return "Download";
      case "running": case "preparing": return "Follow it";
      default: return "Details";
    }
  }
  function taskDetail(task) {
    switch (task.status) {
      case "draft": {
        const files = task.input_files || [];
        if (task.error) return task.error;
        if (!files.length) return task.input_mode === "upload" ? "Add your Takeout files" : "Choose the folder with your Takeout";
        const done = files.filter((f) => f.complete).length;
        return `${done} of ${files.length} files uploaded`;
      }
      case "quoted": return `Price ${task.price} · starts about ${formatWhen(task.eta_start_at)}`;
      case "queued": return `Number ${task.queue_position || 1} in the queue · starts about ${formatWhen(task.eta_start_at)}`;
      case "running": case "preparing": case "packaging": return task.status_detail || "Working on it";
      case "ready": case "awaiting_download_payment": return `Deleted on ${formatWhen(task.download_expires_at)}`;
      case "failed": return task.refunded_at ? `${task.error} · refunded` : task.error;
      case "completed": return `Data and credentials deleted on ${formatWhen(task.purged_at || task.finished_at)}`;
      case "rejected": return task.error;
      default: return task.purged_at ? `Data deleted on ${formatWhen(task.purged_at)}` : "";
    }
  }
  async function renderList() {
    const data = await api("/api/service/tasks");
    const tasks = data.tasks || [];
    root.innerHTML = "";
    root.appendChild(hero("Cloud service", "We run your migration or Takeout processing on our server. You pay only for tasks that work.", false,
      el("button", { type: "button", class: "svc-btn svc-btn--light", onclick: () => go({ new: "1" }) }, icon("plus"), "New task")));
    const facts = el("div", { class: "svc-facts" });
    if (info.billing_applies) facts.appendChild(el("span", { class: "svc-fact" }, icon("check"), `${formatPrice(info.price_min_cents)} minimum · ${info.price_per_gb_cents} cents per GB`));
    else facts.appendChild(el("span", { class: "svc-fact" }, icon("check"), "Free for your account"));
    facts.appendChild(el("span", { class: "svc-fact" }, icon("check"), "Full refund if a task fails"));
    facts.appendChild(el("span", { class: "svc-fact" }, icon("check"), "Data and credentials deleted when it ends"));
    root.appendChild(facts);
    if (!tasks.length) {
      root.appendChild(el("section", { class: "svc-card svc-empty" },
        el("h2", { text: "No tasks yet" }),
        el("p", { text: "Create a task to migrate a Takeout to your photo service, fix a Takeout or move a library between services." }),
        el("button", { type: "button", class: "svc-btn svc-btn--primary", onclick: () => go({ new: "1" }) }, icon("plus"), "New task")));
      return;
    }
    const list = el("section", { class: "svc-card svc-list" });
    tasks.forEach((task) => {
      const files = task.input_files || [];
      const total = files.reduce((sum, f) => sum + (f.size || 0), 0);
      const received = files.reduce((sum, f) => sum + (f.received || 0), 0);
      const showBar = task.status === "draft" && total > 0;
      const meta = KIND_META[task.kind] || KIND_META.takeout_to_cloud;
      const primary = ["quoted", "awaiting_payment", "awaiting_download_payment", "ready"].includes(task.status);
      list.appendChild(el("div", { class: "svc-row" },
        el("span", { class: `svc-row__icon ${meta.tone}` }, icon(meta.icon)),
        el("div", { class: "svc-row__main" },
          el("div", { class: "svc-row__title", text: task.label }),
          el("div", { class: "svc-row__meta", text: [task.size_bytes ? formatBytes(task.size_bytes) : "", task.amount_paid_cents ? `paid ${formatPrice(task.amount_paid_cents)}` : "", formatWhen(task.created_at)].filter(Boolean).join(" · ") })),
        statusPill(task.status),
        el("div", { class: "svc-row__detail" },
          showBar ? el("div", { class: "svc-bar" }, el("span", { style: `width:${Math.round((received / total) * 100)}%` })) : null,
          el("span", { text: taskDetail(task) || "" })),
        el("div", { class: "svc-row__action" },
          el("button", { type: "button", class: `svc-btn ${primary ? "svc-btn--primary" : "svc-btn--ghost"}`, onclick: () => go({ task: task.id }) }, taskAction(task)))));
    });
    root.appendChild(list);
    if (tasks.some((task) => !FINAL.has(task.status))) pollTimer = setTimeout(route, 15000);
  }

  // ---------------------------------------------------------------------------------------------------------------
  // New task wizard
  // ---------------------------------------------------------------------------------------------------------------
  function renderWizard() {
    const state = { kind: "takeout_to_cloud", takeout_type: "google", input_mode: "upload", source_service: "synology", target_service: "immich",
      source: { mode: "custom", account_id: 1, values: {} }, target: { mode: "custom", account_id: 1, values: {} }, accept_terms: false };
    root.innerHTML = "";
    root.appendChild(hero("New task", "", true));
    const layout = el("div", { class: "svc-layout" });
    const main = el("div", { class: "svc-main" });
    const side = el("aside", { class: "svc-side" });
    layout.append(main, side);
    root.appendChild(layout);
    const error = el("div", { class: "svc-error hidden", role: "alert" });

    function step(number, title, extra) {
      const card = el("section", { class: "svc-card" });
      card.appendChild(el("div", { class: "svc-step" }, el("span", { class: "svc-step__num", text: String(number) }), el("h2", { text: title }), extra || null));
      return card;
    }
    function segmented(options, value, onPick, labelText) {
      const group = el("div", { class: "svc-seg", role: "radiogroup", "aria-label": labelText });
      options.forEach(([key, text]) => {
        group.appendChild(el("button", { type: "button", role: "radio", "aria-checked": key === value ? "true" : "false", class: key === value ? "is-active" : "", onclick: () => onPick(key) }, text));
      });
      return group;
    }
    function credentialsBlock(role, service) {
      const choice = state[role];
      const fields = (info.credential_fields && info.credential_fields[service]) || [];
      const box = el("div", { class: "svc-creds" });
      const modes = el("div", { class: "svc-creds__modes" });
      [["saved", "Use my saved account"], ["custom", "Enter them for this task only"]].forEach(([mode, text]) => {
        const id = `svc-${role}-${mode}`;
        modes.appendChild(el("label", { class: `svc-radio${choice.mode === mode ? " is-active" : ""}`, for: id },
          el("input", { type: "radio", id, name: `svc-${role}-mode`, checked: choice.mode === mode, onchange: () => { choice.mode = mode; draw(); } }), text));
      });
      box.appendChild(modes);
      if (choice.mode === "saved") {
        const select = el("select", { class: "field__input", "aria-label": "Account", onchange: (event) => { choice.account_id = Number(event.target.value); } });
        [1, 2, 3].forEach((id) => select.appendChild(el("option", { value: String(id), selected: choice.account_id === id }, `Account ${id}`)));
        box.appendChild(el("label", { class: "svc-field" }, el("span", { text: "Account of Settings > Service credentials" }), select));
        box.appendChild(el("p", { class: "svc-hint", text: "A copy is encrypted for this task only and deleted when it ends. Your saved account is not changed." }));
      } else {
        const grid = el("div", { class: "svc-fields" });
        fields.forEach((field) => {
          const input = el("input", { class: "field__input", type: field.secret ? "password" : "text", autocomplete: "off", "data-lpignore": "true",
            value: choice.values[field.key] || field.default || "", placeholder: field.key === "URL" ? "https://" : "",
            oninput: (event) => { choice.values[field.key] = event.target.value; } });
          if (field.default && !choice.values[field.key]) choice.values[field.key] = field.default;
          grid.appendChild(el("label", { class: "svc-field" }, el("span", { text: field.label + (field.required ? "" : " (optional)") }), input));
        });
        box.appendChild(grid);
      }
      const tips = {
        immich: "Tip: create an API key just for this task in Immich (Account settings → API keys) and delete it when the task ends.",
        nextcloud: "Tip: use an app password (Personal settings → Security) and revoke it when the task ends.",
        synology: "Tip: use an account without two-step verification, ideally one created only for this task.",
        "google-photos": "Use the client ID, client secret and refresh token of your own Google OAuth client (see the Google Photos help).",
      };
      if (tips[service]) box.appendChild(el("p", { class: "svc-tip", text: tips[service] }));
      if (service !== "google-photos" && service) box.appendChild(el("p", { class: "svc-hint", text: "The server must be reachable from the internet." }));
      return box;
    }
    function serviceChips(services, value, onPick, labelText) {
      const group = el("div", { class: "svc-chips", role: "radiogroup", "aria-label": labelText });
      services.forEach((service) => group.appendChild(el("button", { type: "button", role: "radio", "aria-checked": service === value ? "true" : "false", class: service === value ? "is-active" : "", onclick: () => onPick(service) }, label(service))));
      return group;
    }

    function draw() {
      main.innerHTML = "";
      side.innerHTML = "";
      const kinds = step(1, "What do you want to do?");
      const kindGrid = el("div", { class: "svc-kinds" });
      Object.entries(KIND_META).forEach(([key, meta]) => {
        kindGrid.appendChild(el("button", { type: "button", class: `svc-kind ${meta.tone}${state.kind === key ? " is-active" : ""}`, "aria-pressed": state.kind === key ? "true" : "false", onclick: () => { state.kind = key; draw(); } },
          el("span", { class: "svc-kind__text" }, el("span", { class: "svc-kind__title", text: meta.title }), el("span", { class: "svc-kind__line" }), el("span", { class: "svc-kind__desc", text: meta.text })),
          icon(meta.icon)));
      });
      kinds.appendChild(kindGrid);
      main.appendChild(kinds);

      let number = 2;
      if (state.kind === "cloud_to_cloud") {
        const source = step(number++, "Source");
        source.appendChild(serviceChips(info.source_services, state.source_service, (service) => { state.source_service = service; state.source.values = {}; draw(); }, "Source service"));
        source.appendChild(credentialsBlock("source", state.source_service));
        main.appendChild(source);
      } else {
        const data = step(number++, "Your Takeout", segmented([["google", "Google Takeout"], ["icloud", "iCloud Takeout"]], state.takeout_type, (value) => { state.takeout_type = value; draw(); }, "Takeout type"));
        const modes = [["upload", "Upload from this browser"]];
        if (info.importers.dropbox) modes.push(["dropbox", "Import from Dropbox"]);
        if (info.importers.onedrive) modes.push(["onedrive", "Import from OneDrive"]);
        const modeGroup = el("div", { class: "svc-modes" });
        modes.forEach(([mode, text]) => {
          const id = `svc-input-${mode}`;
          modeGroup.appendChild(el("label", { class: `svc-radio${state.input_mode === mode ? " is-active" : ""}`, for: id },
            el("input", { type: "radio", id, name: "svc-input", checked: state.input_mode === mode, onchange: () => { state.input_mode = mode; draw(); } }), text));
        });
        data.appendChild(modeGroup);
        data.appendChild(el("p", { class: "svc-hint", text: state.input_mode === "upload"
          ? "You add the files in the next step. Uploads resume if the connection drops, so you can close the page and continue later."
          : "Read-only access. In Google Takeout choose “Add to Dropbox” or “Add to OneDrive”, then connect it in the next step." }));
        main.appendChild(data);
      }
      if (state.kind !== "process_takeout") {
        const destination = step(number++, "Destination");
        destination.appendChild(serviceChips(info.target_services, state.target_service, (service) => { state.target_service = service; state.target.values = {}; draw(); }, "Destination service"));
        destination.appendChild(credentialsBlock("target", state.target_service));
        main.appendChild(destination);
      }

      const summary = el("section", { class: "svc-card" }, el("h2", { text: "Summary" }));
      const routeText = state.kind === "process_takeout" ? `${label(state.takeout_type)} → ${label("download")}`
        : state.kind === "cloud_to_cloud" ? `${label(state.source_service)} → ${label(state.target_service)}` : `${label(state.takeout_type)} → ${label(state.target_service)}`;
      summary.appendChild(el("div", { class: "svc-sum" }, el("span", { text: "Task" }), el("b", { text: routeText })));
      summary.appendChild(el("div", { class: "svc-sum" }, el("span", { text: "Price" }), el("b", { text: info.billing_applies ? `${formatPrice(info.price_min_cents)} minimum + ${info.price_per_gb_cents} cents per GB` : "Free for your account" })));
      summary.appendChild(el("p", { class: "svc-hint", text: "The exact price comes with the quote, after we measure the data and test the destination with a tiny upload. Nothing is charged until you accept it." }));
      const termsId = "svc-terms";
      summary.appendChild(el("label", { class: "svc-terms", for: termsId },
        el("input", { type: "checkbox", id: termsId, checked: state.accept_terms, onchange: (event) => { state.accept_terms = event.target.checked; } }),
        el("span", {}, "I accept the ", el("a", { href: "/terms", target: "_blank", rel: "noopener", text: "terms of service" }), " and the ", el("a", { href: "/privacy", target: "_blank", rel: "noopener", text: "privacy policy" }), ".")));
      summary.appendChild(error);
      const submit = el("button", { type: "button", class: "svc-btn svc-btn--primary svc-btn--block" }, state.kind === "cloud_to_cloud" ? "Check and get a quote" : "Continue");
      submit.addEventListener("click", async () => {
        error.classList.add("hidden");
        if (!state.accept_terms) {
          error.textContent = t("Accept the terms of service and the privacy policy to continue.");
          error.classList.remove("hidden");
          return;
        }
        submit.disabled = true;
        try {
          const body = { kind: state.kind, takeout_type: state.takeout_type, input_mode: state.input_mode, accept_terms: true,
            source_service: state.kind === "cloud_to_cloud" ? state.source_service : "",
            target_service: state.kind === "process_takeout" ? "" : state.target_service,
            source: state.kind === "cloud_to_cloud" ? state.source : null,
            target: state.kind === "process_takeout" ? null : state.target };
          const created = await postJson("/api/service/tasks", body);
          if (state.kind === "cloud_to_cloud") await postJson(`/api/service/tasks/${created.task.id}/analyze`);
          go({ task: created.task.id });
        } catch (exc) {
          error.textContent = String(exc.message || exc);
          error.classList.remove("hidden");
          submit.disabled = false;
        }
      });
      summary.appendChild(submit);
      side.appendChild(summary);
      side.appendChild(protectionCard());
    }
    draw();
  }

  function protectionCard() {
    return el("section", { class: "svc-card svc-protect" },
      el("h2", {}, icon("shield"), "How we protect your data"),
      el("ul", {},
        el("li", { text: "Credentials encrypted with a key for this task only" }),
        el("li", { text: "Files and credentials deleted when it ends" }),
        el("li", { text: "No other user or person can see them" }),
        el("li", { text: "We never delete anything in your source" })));
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Uploads (resumable, one file at a time, chunks of up to 64 MB)
  // ---------------------------------------------------------------------------------------------------------------
  const CHUNK = 64 * 1024 * 1024;
  function queueUpload(taskId, file, onProgress) {
    uploadQueue = uploadQueue.then(() => uploadFile(taskId, file, onProgress)).catch((exc) => onProgress(file.name, null, String(exc.message || exc)));
    return uploadQueue;
  }
  async function uploadFile(taskId, file, onProgress) {
    const started = await postJson(`/api/service/tasks/${taskId}/uploads`, { name: file.name, size: file.size });
    const upload = started.upload;
    let offset = upload.received || 0;
    const chunkSize = Math.min(CHUNK, started.chunk_max_bytes || CHUNK);
    onProgress(upload.name, offset / file.size);
    while (offset < file.size) {
      const chunk = file.slice(offset, Math.min(file.size, offset + chunkSize));
      let response;
      for (let attempt = 1; attempt <= 5; attempt += 1) {
        try {
          response = await fetch(`/api/service/tasks/${taskId}/uploads/${upload.id}?offset=${offset}`, { method: "PUT", body: chunk, headers: { "Content-Type": "application/octet-stream" } });
          break;
        } catch (exc) {
          if (attempt === 5) throw exc;
          await new Promise((resolve) => setTimeout(resolve, attempt * 3000));
        }
      }
      if (response.status === 409) {
        const data = await response.json().catch(() => ({}));
        try { offset = JSON.parse(data.detail).offset; } catch (_error) { throw new Error("The upload could not continue. Add the file again."); }
        continue;
      }
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `HTTP ${response.status}`);
      }
      const data = await response.json();
      offset = data.upload.received;
      onProgress(upload.name, offset / file.size);
    }
  }

  // ---------------------------------------------------------------------------------------------------------------
  // Task page
  // ---------------------------------------------------------------------------------------------------------------
  function dataCard(task) {
    const card = el("section", { class: "svc-card" }, el("h2", { text: task.input_mode === "upload" ? "Upload your Takeout files" : "Choose your Takeout folder" }));
    if (task.input_mode === "upload") {
      const zone = el("div", { class: "svc-drop" });
      const listBox = el("div", { class: "svc-files" });
      const files = task.input_files || [];
      const rows = {};
      function rowFor(name, size, fraction, complete, id) {
        const bar = el("span", { style: `width:${Math.round((fraction || 0) * 100)}%` });
        const state = el("span", { class: "svc-files__state", text: complete ? t("Uploaded") : `${Math.round((fraction || 0) * 100)}%` });
        const remove = id ? el("button", { type: "button", class: "svc-x", "aria-label": `Remove ${name}`, onclick: async () => {
          await api(`/api/service/tasks/${task.id}/uploads/${id}`, { method: "DELETE" });
          route();
        } }, "×") : el("span");
        const row = el("div", { class: "svc-files__row" },
          el("div", { class: "svc-files__name" }, el("span", { class: "svc-files__file", "data-no-i18n": "", text: name }), el("div", { class: "svc-bar" }, bar)),
          el("span", { class: "svc-files__size", text: formatBytes(size) }), state, remove);
        rows[name] = { bar, state };
        return row;
      }
      files.forEach((f) => listBox.appendChild(rowFor(f.name, f.size, f.size ? (f.complete ? 1 : (f.received || 0) / f.size) : 0, f.complete, f.id)));
      Object.entries(uploadProgress).forEach(([name, value]) => {
        if (rows[name] && value.fraction !== null) {
          rows[name].bar.style.width = `${Math.round(value.fraction * 100)}%`;
          rows[name].state.textContent = value.fraction >= 1 ? t("Uploaded") : `${Math.round(value.fraction * 100)}%`;
        }
      });
      const picker = el("input", { type: "file", multiple: true, accept: ".zip", class: "hidden" });
      const onProgress = (name, fraction, failure) => {
        uploadProgress[name] = { fraction };
        const row = rows[name];
        if (failure) {
          alertBox.textContent = `${name}: ${failure}`;
          alertBox.classList.remove("hidden");
          return;
        }
        if (!row) { route(); return; }
        row.bar.style.width = `${Math.round(fraction * 100)}%`;
        row.state.textContent = fraction >= 1 ? t("Uploaded") : `${Math.round(fraction * 100)}%`;
        if (fraction >= 1) setTimeout(route, 300);
      };
      const alertBox = el("div", { class: "svc-error hidden", role: "alert" });
      const addFiles = (fileList) => {
        Array.from(fileList || []).forEach((file) => {
          if (!rows[file.name]) listBox.appendChild(rowFor(file.name, file.size, 0, false, ""));
          queueUpload(task.id, file, onProgress);
        });
      };
      picker.addEventListener("change", () => addFiles(picker.files));
      zone.addEventListener("dragover", (event) => { event.preventDefault(); zone.classList.add("is-over"); });
      zone.addEventListener("dragleave", () => zone.classList.remove("is-over"));
      zone.addEventListener("drop", (event) => { event.preventDefault(); zone.classList.remove("is-over"); addFiles(event.dataTransfer.files); });
      zone.append(
        el("div", { class: "svc-drop__head" }, icon("upload"), el("b", { text: "Drop your Takeout ZIP files here" }), el("span", { class: "svc-hint", text: "Uploads resume if the connection drops: add the same file again to continue." })),
        listBox,
        el("button", { type: "button", class: "svc-btn svc-btn--ghost", onclick: () => picker.click() }, icon("plus"), "Add Takeout files"),
        picker, alertBox);
      card.appendChild(zone);
      const maxInput = formatBytes((info.max_input_bytes || {})[task.kind] || 0);
      card.appendChild(el("p", { class: "svc-hint", text: `Up to ${maxInput} in total.` }));
    } else {
      const provider = task.input_mode === "dropbox" ? "Dropbox" : "OneDrive";
      const connectedNow = params.get("connected");
      const browser = el("div", { class: "svc-remote" });
      card.appendChild(el("p", { class: "svc-hint", text: `Connect ${provider} with read-only access and choose the folder where Takeout saved the files.` }));
      card.appendChild(el("a", { class: "svc-btn svc-btn--ghost", href: `/api/service/oauth/${task.input_mode}/start?task=${task.id}` }, icon("link"), `Connect ${provider}`));
      if (connectedNow === "0") card.appendChild(notice(`${provider} was not connected. Try again.`, "error"));
      if (task.remote_path) card.appendChild(notice(`Chosen folder: ${task.remote_path}`));
      card.appendChild(browser);
      async function openFolder(path) {
        browser.innerHTML = "";
        try {
          const data = await api(`/api/service/tasks/${task.id}/remote?path=${encodeURIComponent(path)}`);
          const archives = data.entries.filter((entry) => entry.archive);
          browser.appendChild(el("div", { class: "svc-remote__bar" },
            el("code", { "data-no-i18n": "", text: path || "/" }),
            path ? el("button", { type: "button", class: "svc-btn svc-btn--ghost svc-btn--small", onclick: () => openFolder(path.split("/").slice(0, -1).join("/")) }, "Up") : null,
            el("button", { type: "button", class: "svc-btn svc-btn--primary svc-btn--small", disabled: !archives.length, onclick: async () => {
              await postJson(`/api/service/tasks/${task.id}/remote/select`, { path: path || "/" });
              route();
            } }, archives.length ? `Use this folder (${archives.length} files)` : "No Takeout files here")));
          data.entries.forEach((entry) => {
            browser.appendChild(el("button", { type: "button", class: "svc-remote__item", disabled: !entry.is_folder, onclick: () => entry.is_folder && openFolder(entry.path) },
              icon(entry.is_folder ? "folder" : "file"), el("span", { "data-no-i18n": "", text: entry.name }), entry.is_folder ? null : el("span", { class: "svc-hint", text: formatBytes(entry.size) })));
          });
        } catch (exc) {
          browser.appendChild(el("p", { class: "svc-hint", text: String(exc.message || exc) }));
        }
      }
      if (connectedNow === "1" || task.remote_path) openFolder(task.remote_path && task.remote_path !== "/" ? task.remote_path : "");
    }
    const ready = task.input_mode === "upload"
      ? (task.input_files || []).length > 0 && (task.input_files || []).every((f) => f.complete)
      : Boolean(task.remote_path);
    const check = el("button", { type: "button", class: "svc-btn svc-btn--primary", disabled: !ready, onclick: async () => {
      check.disabled = true;
      try { await postJson(`/api/service/tasks/${task.id}/analyze`); route(); } catch (exc) { check.disabled = false; window.alert(String(exc.message || exc)); }
    } }, "Check and get a quote");
    card.appendChild(el("div", { class: "svc-actions" }, check, cancelButton(task)));
    return card;
  }

  function stat(labelText, value, sub, tone) {
    return el("div", { class: `svc-stat${tone ? ` svc-stat--${tone}` : ""}` }, el("span", { class: "svc-stat__label", text: labelText }), el("b", { text: value }), sub ? el("span", { class: "svc-hint", text: sub }) : null);
  }

  async function startPayment(task, path) {
    const data = await postJson(path);
    if (data.checkout_url) window.location.href = data.checkout_url;
    else route();
  }

  function cancelButton(task) {
    const running = ["preparing", "running", "packaging"].includes(task.status);
    const done = ["ready", "awaiting_download_payment"].includes(task.status);
    const text = running ? "Stop" : done ? "Delete now" : "Cancel and delete";
    return el("button", { type: "button", class: "svc-btn svc-btn--danger", onclick: async () => {
      const warning = running ? "Stop this task and delete its data? A task that has started is not refunded."
        : task.amount_paid_cents ? "Cancel this task and delete its data? You get the full amount back." : "Delete this task and its data?";
      if (!window.confirm(t(warning))) return;
      await postJson(`/api/service/tasks/${task.id}/cancel`);
      route();
    } }, text);
  }

  function statusCard(task) {
    const card = el("section", { class: "svc-card" });
    const s = task.status;
    if (s === "draft" && task.kind === "cloud_to_cloud") {
      const retry = el("button", { type: "button", class: "svc-btn svc-btn--primary", onclick: async () => {
        retry.disabled = true;
        try { await postJson(`/api/service/tasks/${task.id}/analyze`); route(); } catch (exc) { retry.disabled = false; window.alert(String(exc.message || exc)); }
      } }, "Check again");
      card.append(el("h2", { text: "Check the accounts" }),
        el("p", { class: "svc-hint", text: "Fix the problem shown above and check again, or delete the task and create it again with other credentials." }),
        el("div", { class: "svc-actions" }, retry, cancelButton(task)));
      return card;
    }
    if (s === "draft") return dataCard(task);
    if (s === "analyzing") {
      card.append(el("h2", { text: "Checking your task" }), el("div", { class: "svc-spinner" }),
        el("p", { class: "svc-hint", text: "We measure your data and test the destination with a tiny upload that we delete right away. It takes a few minutes." }));
      return card;
    }
    if (s === "quoted" || s === "awaiting_payment") {
      card.appendChild(el("h2", { text: "Your quote" }));
      card.appendChild(el("div", { class: "svc-stats" },
        stat("Data to move", formatBytes(task.size_bytes)),
        stat(task.billable ? "Price · VAT incl." : "Price", task.billable ? task.price : t("Free for your account"), "", "amber"),
        stat("Estimated start", formatWhen(task.eta_start_at)),
        stat("Duration", formatDuration(task.eta_seconds))));
      const checks = el("div", { class: "svc-checks" });
      checks.appendChild(el("span", {}, icon("check"), `Data measured: ${formatBytes(task.size_bytes)}`));
      if (task.media_count) checks.appendChild(el("span", {}, icon("check"), `Photos and videos found: ${task.media_count}`));
      if (task.target_service) checks.appendChild(el("span", {}, icon("check"), `${label(task.target_service)} can receive uploads`));
      card.appendChild(checks);
      const payText = task.kind === "process_takeout" ? (task.billable ? "Start (you pay when it is ready)" : "Start")
        : task.billable ? `Pay ${task.price} and start` : "Start";
      card.appendChild(el("div", { class: "svc-actions" },
        el("button", { type: "button", class: "svc-btn svc-btn--primary", onclick: (event) => { event.currentTarget.disabled = true; startPayment(task, `/api/service/tasks/${task.id}/accept`).catch((exc) => window.alert(exc.message)); } }, payText),
        cancelButton(task),
        el("span", { class: "svc-hint", text: task.billable && task.kind !== "process_takeout" ? `Secure payment with Stripe. Valid for ${info.quote_days} days. If the task fails you get the full amount back.` : `Valid for ${info.quote_days} days.` })));
      if (params.get("checkout") === "canceled") card.appendChild(notice("The payment was canceled. You can pay whenever you are ready.", "info"));
      return card;
    }
    if (s === "queued") {
      card.append(el("h2", { text: "In the queue" }),
        el("div", { class: "svc-stats" }, stat("Position", String(task.queue_position || 1)), stat("Estimated start", formatWhen(task.eta_start_at)), stat("Duration", formatDuration(task.eta_seconds))),
        ...(task.status_detail ? [notice(task.status_detail)] : []),
        el("p", { class: "svc-hint", text: "We email you when it starts and when it ends. You can cancel it until then with a full refund." }),
        el("div", { class: "svc-actions" }, cancelButton(task)));
      return card;
    }
    if (s === "preparing" || s === "running" || s === "packaging") {
      card.append(el("h2", { text: s === "packaging" ? "Preparing your download" : "Running" }),
        el("div", { class: "svc-spinner" }),
        el("p", { text: task.status_detail || "PhotoMigrator is working on your task." }),
        el("p", { class: "svc-hint", text: "Follow the live dashboard and the log in Activity. A task that has started is not refunded if you stop it." }),
        el("div", { class: "svc-actions" },
          s === "packaging" ? null : el("a", { class: "svc-btn svc-btn--primary", href: "/output?manual_navigation=1" }, icon("activity"), "Open in Activity"),
          cancelButton(task)));
      return card;
    }
    if (s === "awaiting_download_payment") {
      card.append(el("h2", { text: "Your processed Takeout is ready" }),
        el("div", { class: "svc-stats" }, stat("Result", formatBytes(task.result_bytes)), stat("Price · VAT incl.", task.price, "", "amber"), stat("Deleted on", formatWhen(task.download_expires_at))),
        el("div", { class: "svc-actions" },
          el("button", { type: "button", class: "svc-btn svc-btn--primary", onclick: (event) => { event.currentTarget.disabled = true; startPayment(task, `/api/service/tasks/${task.id}/pay`).catch((exc) => window.alert(exc.message)); } }, "Pay and download"),
          cancelButton(task)));
      return card;
    }
    if (s === "ready") {
      card.append(el("h2", { text: "Download" }),
        el("p", { class: "svc-hint", text: `Deleted on ${formatWhen(task.download_expires_at)}. Downloads resume if they stop; use “Copy link” for a download manager.` }));
      (task.downloads || []).forEach((part) => {
        const url = new URL(part.url, window.location.origin).toString();
        card.appendChild(el("div", { class: "svc-part" },
          icon("archive"), el("span", { class: "svc-part__name", "data-no-i18n": "", text: part.name }), el("span", { class: "svc-hint", text: formatBytes(part.size) }),
          el("button", { type: "button", class: "svc-btn svc-btn--ghost svc-btn--small", onclick: async (event) => { await navigator.clipboard.writeText(url); event.currentTarget.textContent = t("Copied"); } }, "Copy link"),
          el("a", { class: "svc-btn svc-btn--primary svc-btn--small", href: part.url, download: part.name }, icon("download"), "Download")));
      });
      card.appendChild(el("div", { class: "svc-actions" }, cancelButton(task)));
      return card;
    }
    const title = { completed: "Completed", failed: "The task failed", canceled: "Canceled", expired: "Expired", rejected: "The task is too large" }[s] || s;
    card.append(el("h2", { text: title }));
    if (task.error) card.appendChild(notice(task.error, s === "failed" || s === "rejected" ? "error" : "info"));
    if (task.refunded_at) card.appendChild(notice(`${formatPrice(task.amount_paid_cents)} refunded on ${formatWhen(task.refunded_at)}.`));
    if (task.purged_at) card.appendChild(notice(`Data and credentials deleted from our server on ${formatWhen(task.purged_at)}.`));
    return card;
  }

  const EVENT_TEXT = {
    created: "Task created. Terms of service accepted.", storage_connected: "Storage connected (read-only).",
    analysis_failed: "The check failed.", target_checked: "Destination checked: it can receive uploads.", quoted: "Quote sent to your email.",
    checkout_created: "Payment page opened.", paid: "Payment received.", queued: "Added to the queue.", requeued: "Queued again after a server restart.",
    input_downloaded: "Takeout files imported.", input_checked: "Takeout files checked.", started: "Task started.", completed: "Task completed.", result_ready: "Download ready.",
    failed: "Task failed.", refunded: "Payment refunded.", canceled: "Task canceled.", expired: "Expired.", rejected: "Rejected: too large.",
    data_deleted: "Data and credentials deleted from our server.", refund_failed: "The refund failed; we will review it.",
  };

  async function renderTask(taskId) {
    if (params.get("checkout") === "success" && params.get("session_id")) {
      try { await api(`/api/service/tasks/${taskId}/checkout/confirm?session_id=${encodeURIComponent(params.get("session_id"))}`); } catch (_error) { /* the webhook confirms it */ }
    }
    const data = await api(`/api/service/tasks/${taskId}`);
    const task = data.task;
    root.innerHTML = "";
    root.appendChild(hero(task.label, task.size_bytes ? formatBytes(task.size_bytes) : "", true, statusPill(task.status)));
    const layout = el("div", { class: "svc-layout" });
    const main = el("div", { class: "svc-main" });
    const side = el("aside", { class: "svc-side" });
    if (task.error && task.status === "draft") main.appendChild(notice(task.error, "error"));
    main.appendChild(statusCard(task));
    const history = el("section", { class: "svc-card" }, el("h2", { text: "History" }));
    (task.events || []).forEach((event) => {
      history.appendChild(el("div", { class: `svc-event svc-event--${event.event}` },
        el("span", { class: "svc-event__dot" }), el("span", { class: "svc-hint", text: formatWhen(event.created_at) }),
        el("span", { text: EVENT_TEXT[event.event] || event.event })));
    });
    main.appendChild(history);
    side.appendChild(protectionCard());
    layout.append(main, side);
    root.appendChild(layout);
    const polling = { analyzing: 4000, queued: 20000, preparing: 8000, running: 15000, packaging: 15000, awaiting_payment: 8000 };
    if (polling[task.status]) pollTimer = setTimeout(route, polling[task.status]);
  }

  async function route() {
    stopPolling();
    const query = new URLSearchParams(window.location.search);
    params.forEach((_value, key) => params.delete(key));
    query.forEach((value, key) => params.set(key, value));
    try {
      if (!info) info = await api("/api/service/info");
      if (!info.enabled) {
        root.innerHTML = "";
        root.appendChild(notice("The cloud service is not enabled on this server."));
        return;
      }
      if (params.get("task")) await renderTask(params.get("task"));
      else if (params.get("new")) renderWizard();
      else await renderList();
    } catch (exc) {
      root.innerHTML = "";
      root.appendChild(notice(String(exc.message || exc), "error"));
    }
  }
  window.addEventListener("popstate", route);
  route();
})();
