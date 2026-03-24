(function () {
    "use strict";

    const DEFAULT_ALLOWED_INLINE_HTML_TAGS = new Set([
        "a", "abbr", "b", "blockquote", "br", "code", "del", "details", "div", "em",
        "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "kbd", "li", "mark",
        "ol", "p", "pre", "s", "small", "span", "strong", "sub", "summary", "sup",
        "table", "tbody", "td", "th", "thead", "tr", "u", "ul"
    ]);

    function escapeHtml(text) {
        return String(text || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function splitTableRow(line) {
        const trimmed = String(line || "").trim().replace(/^\|/, "").replace(/\|$/, "");
        return trimmed.split("|").map((cell) => cell.trim());
    }

    function isTableDivider(line) {
        const cells = splitTableRow(line);
        if (!cells.length) return false;
        return cells.every((cell) => /^:?-{3,}:?$/.test(cell));
    }

    function defaultParseMdTarget(rawTarget) {
        const text = String(rawTarget || "").trim();
        const decoded = text
            .replace(/&quot;/gi, '"')
            .replace(/&#39;/gi, "'");
        const match = decoded.match(/^<?([^>\s]+)>?(?:\s+["'][^"']*["'])?$/);
        return match ? match[1] : decoded;
    }

    function defaultBuildHeadingIdFactory() {
        const headingIdCounter = new Map();
        return (rawHeadingText) => {
            const base = String(rawHeadingText || "")
                .replace(/<[^>]*>/g, " ")
                .replace(/`([^`]+)`/g, "$1")
                .replace(/\*\*([^*]+)\*\*/g, "$1")
                .replace(/\*([^*]+)\*/g, "$1")
                .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
                .replace(/&[a-z]+;/gi, " ")
                .toLowerCase()
                .replace(/[^a-z0-9\s-]/g, " ")
                .trim()
                .replace(/\s+/g, "-")
                .replace(/-+/g, "-");
            const safeBase = base || "section";
            const seen = headingIdCounter.get(safeBase) || 0;
            headingIdCounter.set(safeBase, seen + 1);
            return seen === 0 ? safeBase : `${safeBase}-${seen + 1}`;
        };
    }

    function defaultShouldSkipLine(line) {
        const value = String(line || "").trim();
        if (!value) return false;
        if (/back to main page/i.test(value) && /\[[^\]]+\]\([^)]+\)/.test(value)) return true;
        if (/planned roadmap for the following releases/i.test(value)) return true;
        if (/changelog for the past releases\+?/i.test(value)) return true;
        return false;
    }

    function preprocessLines(rawLines) {
        const lines = [];
        let skipNextTopSeparator = false;
        for (let i = 0; i < rawLines.length; i += 1) {
            const line = String(rawLines[i] || "");
            const trimmed = line.trim();
            const normalized = trimmed.toLowerCase();
            const isRoadmapLinkLine =
                normalized.includes("planned roadmap") &&
                normalized.includes("following releases");
            const isChangelogLinkLine =
                normalized.includes("changelog") &&
                normalized.includes("past releases");

            if (isRoadmapLinkLine || isChangelogLinkLine) {
                skipNextTopSeparator = true;
                continue;
            }
            if (skipNextTopSeparator && (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed))) {
                skipNextTopSeparator = false;
                continue;
            }
            if (trimmed) {
                skipNextTopSeparator = false;
            }
            lines.push(line);
        }
        return lines;
    }

    function createRenderer(options) {
        const opts = options || {};
        const resolveUrl = typeof opts.resolveUrl === "function"
            ? opts.resolveUrl
            : (url) => String(url || "");
        const shouldSkipLine = typeof opts.shouldSkipLine === "function"
            ? opts.shouldSkipLine
            : defaultShouldSkipLine;
        const parseMdTarget = typeof opts.parseMdTarget === "function"
            ? opts.parseMdTarget
            : defaultParseMdTarget;
        const allowedTags = opts.allowedInlineHtmlTags instanceof Set
            ? opts.allowedInlineHtmlTags
            : DEFAULT_ALLOWED_INLINE_HTML_TAGS;
        const includeHeadingIds = opts.includeHeadingIds !== false;

        const rewriteHtmlTagUrls = (htmlSnippet) => {
            let out = String(htmlSnippet || "");
            out = out.replace(/\s(src|href)=["']([^"']+)["']/gi, (_m, attr, url) => {
                const resolved = resolveUrl(url, attr.toLowerCase() === "src");
                return ` ${attr}="${escapeHtml(resolved)}"`;
            });
            return out;
        };

        const isAllowedInlineHtmlTag = (tagText) => {
            const match = String(tagText || "").match(/^<\/?\s*([a-zA-Z][\w-]*)\b[^>]*>$/);
            if (!match) return false;
            return allowedTags.has(String(match[1] || "").toLowerCase());
        };

        const renderInlineMarkdown = (text) => {
            const rawText = String(text || "");
            const htmlTokens = [];
            const tokenized = rawText.replace(/<\/?[a-zA-Z][^>]*>/g, (tag) => {
                if (!isAllowedInlineHtmlTag(tag)) return tag;
                const token = `@@HTMLTOKEN${htmlTokens.length}@@`;
                htmlTokens.push(rewriteHtmlTagUrls(tag));
                return token;
            });

            let html = escapeHtml(tokenized);
            html = html.replace(/\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)/g, (_m, alt, imgUrl, linkUrl) => {
                const resolvedLink = resolveUrl(linkUrl, false);
                const resolvedImg = resolveUrl(imgUrl, true);
                const isInternal = resolvedLink.startsWith("/") && !resolvedLink.startsWith("//");
                const targetAttrs = isInternal ? "" : ` target="_blank" rel="noopener noreferrer"`;
                return `<a href="${escapeHtml(resolvedLink)}"${targetAttrs}><img src="${escapeHtml(resolvedImg)}" alt="${escapeHtml(alt)}"></a>`;
            });

            html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (_m, alt, rawTarget) =>
                `<img src="${escapeHtml(resolveUrl(parseMdTarget(rawTarget), true))}" alt="${escapeHtml(alt)}">`
            );
            html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, label, rawTarget) => {
                const resolved = resolveUrl(parseMdTarget(rawTarget), false);
                const isInternal = resolved.startsWith("/") && !resolved.startsWith("//");
                const targetAttrs = isInternal ? "" : ` target="_blank" rel="noopener noreferrer"`;
                return `<a href="${escapeHtml(resolved)}"${targetAttrs}>${escapeHtml(label)}</a>`;
            });

            html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
            html = html.replace(/_\*\*([^*\n][\s\S]*?)\*\*_/g, "<em><strong>$1</strong></em>");
            html = html.replace(/\*\*_([^_\n][\s\S]*?)_\*\*/g, "<strong><em>$1</em></strong>");
            html = html.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
            html = html.replace(/__([^_\n]+)__/g, "<strong>$1</strong>");
            html = html.replace(/(^|[^\w])\*([^*\n]+)\*(?=[^\w]|$)/g, "$1<em>$2</em>");
            html = html.replace(/(^|[^\w])_([^_\n]+)_(?=[^\w]|$)/g, "$1<em>$2</em>");

            htmlTokens.forEach((tag, index) => {
                const token = `@@HTMLTOKEN${index}@@`;
                html = html.split(token).join(tag);
            });
            return html;
        };

        const buildHeadingId = defaultBuildHeadingIdFactory();
        const parseStandaloneHtmlImages = (line) => {
            const value = String(line || "").trim();
            if (!value) return [];
            const matches = value.match(/<img\b[^>]*>/gi) || [];
            if (!matches.length) return [];
            const onlyImagesAndSpaces = value.replace(/<img\b[^>]*>/gi, "").trim();
            return onlyImagesAndSpaces ? [] : matches;
        };
        const isBadgeImageTag = (imgTag) => /src=["']https?:\/\/img\.shields\.io\//i.test(String(imgTag || ""));
        const parseMarkdownBadgeLine = (line) => {
            const value = String(line || "").trim();
            const match = value.match(/^\[!\[([^\]]*)\]\((https?:\/\/img\.shields\.io\/[^)]+)\)\]\(([^)]+)\)\s*$/i);
            if (!match) return null;
            return {alt: match[1] || "", image: match[2] || "", link: match[3] || ""};
        };

        const render = (markdownText) => {
            const source = String(markdownText || "").replace(/\r\n/g, "\n");
            const rawLines = source.split("\n");
            const lines = preprocessLines(rawLines);
            const html = [];
            let paragraph = [];
            const listStack = [];
            let inCode = false;
            let codeLang = "";
            let codeLines = [];
            let codeFenceDelimiter = "";
            let codeFenceInQuote = false;

            const closeOneList = () => {
                const top = listStack.pop();
                if (!top) return;
                if (top.liOpen) html.push("</li>");
                html.push(top.type === "ol" ? "</ol>" : "</ul>");
            };
            const closeLists = () => {
                while (listStack.length) closeOneList();
            };
            const flushParagraph = () => {
                if (!paragraph.length) return;
                html.push(`<p>${paragraph.map(renderInlineMarkdown).join("<br>")}</p>`);
                paragraph = [];
            };

            for (let i = 0; i < lines.length; i += 1) {
                const rawLine = lines[i] || "";
                const trimmed = rawLine.trim();

                if (shouldSkipLine(trimmed)) {
                    flushParagraph();
                    closeLists();
                    continue;
                }

                if (inCode) {
                    let codeRawLine = rawLine;
                    if (codeFenceInQuote) {
                        const quoteMatch = rawLine.match(/^>\s?(.*)$/);
                        if (quoteMatch) codeRawLine = quoteMatch[1];
                    }
                    const codeTrimmed = codeRawLine.trim();
                    if (codeFenceDelimiter && codeTrimmed.startsWith(codeFenceDelimiter)) {
                        const langClass = codeLang ? ` class="language-${escapeHtml(codeLang)}"` : "";
                        html.push(`<pre><code${langClass}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
                        inCode = false;
                        codeLang = "";
                        codeLines = [];
                        codeFenceDelimiter = "";
                        codeFenceInQuote = false;
                    } else {
                        codeLines.push(codeRawLine);
                    }
                    continue;
                }

                let codeFenceText = trimmed;
                let codeFence = codeFenceText.match(/^(?:```|''')([\w-]+)?\s*$/);
                let openingFenceInQuote = false;
                if (!codeFence) {
                    const quoteMatch = rawLine.match(/^>\s?(.*)$/);
                    if (quoteMatch) {
                        codeFenceText = String(quoteMatch[1] || "").trim();
                        codeFence = codeFenceText.match(/^(?:```|''')([\w-]+)?\s*$/);
                        openingFenceInQuote = Boolean(codeFence);
                    }
                }
                if (codeFence) {
                    flushParagraph();
                    closeLists();
                    inCode = true;
                    codeLang = codeFence[1] || "";
                    codeLines = [];
                    codeFenceDelimiter = codeFenceText.startsWith("'''") ? "'''" : "```";
                    codeFenceInQuote = openingFenceInQuote;
                    continue;
                }

                if (!trimmed) {
                    flushParagraph();
                    closeLists();
                    continue;
                }

                if (/^<br\s*\/?>$/i.test(trimmed)) {
                    continue;
                }

                const markdownBadge = parseMarkdownBadgeLine(trimmed);
                if (markdownBadge) {
                    flushParagraph();
                    closeLists();
                    const badges = [markdownBadge];
                    let j = i + 1;
                    while (j < lines.length) {
                        const nextLine = String(lines[j] || "").trim();
                        if (!nextLine || shouldSkipLine(nextLine)) {
                            j += 1;
                            continue;
                        }
                        const nextBadge = parseMarkdownBadgeLine(nextLine);
                        if (!nextBadge) break;
                        badges.push(nextBadge);
                        j += 1;
                    }
                    const badgesHtml = badges.map((badge) => {
                        const href = escapeHtml(resolveUrl(badge.link, false));
                        const src = escapeHtml(resolveUrl(badge.image, true));
                        const alt = escapeHtml(badge.alt);
                        return `<a href="${href}" target="_blank" rel="noopener noreferrer"><img src="${src}" alt="${alt}"></a>`;
                    }).join("");
                    html.push(`<div class="html-badges">${badgesHtml}</div>`);
                    i = j - 1;
                    continue;
                }

                const inlineImages = parseStandaloneHtmlImages(trimmed);
                if (inlineImages.length > 0) {
                    flushParagraph();
                    closeLists();
                    const imageTags = inlineImages.map(rewriteHtmlTagUrls);
                    const allBadges = imageTags.every(isBadgeImageTag);
                    if (!allBadges) {
                        html.push(imageTags.join(""));
                        continue;
                    }
                    let j = i + 1;
                    while (j < lines.length) {
                        const nextLine = String(lines[j] || "").trim();
                        if (!nextLine || shouldSkipLine(nextLine)) {
                            j += 1;
                            continue;
                        }
                        const nextImages = parseStandaloneHtmlImages(nextLine);
                        if (!nextImages.length) break;
                        const rewritten = nextImages.map(rewriteHtmlTagUrls);
                        if (!rewritten.every(isBadgeImageTag)) break;
                        imageTags.push(...rewritten);
                        j += 1;
                    }
                    html.push(`<div class="html-badges">${imageTags.join("")}</div>`);
                    i = j - 1;
                    continue;
                }

                if (/^<[^>]+>/.test(trimmed)) {
                    flushParagraph();
                    closeLists();
                    html.push(rewriteHtmlTagUrls(rawLine));
                    continue;
                }

                const admonition = trimmed.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$/i);
                if (admonition) {
                    flushParagraph();
                    closeLists();
                    const kind = admonition[1].toLowerCase();
                    const content = [];
                    let j = i + 1;
                    while (j < lines.length && String(lines[j] || "").trim() !== "") {
                        content.push(String(lines[j] || "").trim());
                        j += 1;
                    }
                    const body = content.length ? `<p>${content.map(renderInlineMarkdown).join("<br>")}</p>` : "";
                    html.push(`<div class="admonition ${kind}"><div class="admonition-title">${admonition[1].toUpperCase()}</div>${body}</div>`);
                    i = j - 1;
                    continue;
                }

                if (rawLine.includes("|") && i + 1 < lines.length && isTableDivider(lines[i + 1])) {
                    flushParagraph();
                    closeLists();
                    const headerCells = splitTableRow(rawLine);
                    let j = i + 2;
                    const bodyRows = [];
                    while (j < lines.length && String(lines[j] || "").includes("|")) {
                        const rowCells = splitTableRow(lines[j]);
                        if (!rowCells.length) break;
                        bodyRows.push(rowCells);
                        j += 1;
                    }
                    const thead = `<thead><tr>${headerCells.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr></thead>`;
                    const tbodyRows = bodyRows.map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`).join("");
                    html.push(`<table>${thead}<tbody>${tbodyRows}</tbody></table>`);
                    i = j - 1;
                    continue;
                }

                const heading = trimmed.match(/^(#{1,6})\s+(.+)$/);
                if (heading) {
                    flushParagraph();
                    closeLists();
                    const level = heading[1].length;
                    if (includeHeadingIds) {
                        const headingId = buildHeadingId(heading[2]);
                        html.push(`<h${level} id="${escapeHtml(headingId)}">${renderInlineMarkdown(heading[2])}</h${level}>`);
                    } else {
                        html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
                    }
                    continue;
                }

                if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
                    flushParagraph();
                    closeLists();
                    if (html.length === 0) continue;
                    if (html[html.length - 1] === "<hr>") continue;
                    html.push("<hr>");
                    continue;
                }

                const quote = trimmed.match(/^>\s?(.*)$/);
                if (quote) {
                    flushParagraph();
                    closeLists();
                    const quotedLines = [String(quote[1] || "").trim()];
                    let j = i + 1;
                    while (j < lines.length) {
                        const next = String(lines[j] || "");
                        const match = next.trim().match(/^>\s?(.*)$/);
                        if (!match) break;
                        quotedLines.push(String(match[1] || "").trim());
                        j += 1;
                    }
                    const qAdmonition = quotedLines[0].match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$/i);
                    if (qAdmonition) {
                        const kind = qAdmonition[1].toLowerCase();
                        const bodyLines = quotedLines.slice(1).filter((line) => line !== "");
                        const body = bodyLines.length ? `<p>${bodyLines.map(renderInlineMarkdown).join("<br>")}</p>` : "";
                        html.push(`<div class="admonition ${kind}"><div class="admonition-title">${qAdmonition[1].toUpperCase()}</div>${body}</div>`);
                    } else {
                        html.push(`<blockquote><p>${quotedLines.map(renderInlineMarkdown).join("<br>")}</p></blockquote>`);
                    }
                    i = j - 1;
                    continue;
                }

                const listItem = rawLine.match(/^([ \t]*)([-*+]|\d+\.)\s+(.+)$/);
                if (listItem) {
                    flushParagraph();
                    const indentText = String(listItem[1] || "").replace(/\t/g, "    ");
                    const indent = indentText.length;
                    const marker = String(listItem[2] || "");
                    const content = String(listItem[3] || "");
                    const type = /^\d+\.$/.test(marker) ? "ol" : "ul";

                    while (listStack.length && indent < listStack[listStack.length - 1].indent) {
                        closeOneList();
                    }
                    if (listStack.length && indent === listStack[listStack.length - 1].indent) {
                        const top = listStack[listStack.length - 1];
                        if (top.type !== type) {
                            closeOneList();
                        } else if (top.liOpen) {
                            html.push("</li>");
                            top.liOpen = false;
                        }
                    }
                    if (!listStack.length || indent > listStack[listStack.length - 1].indent || listStack[listStack.length - 1].type !== type) {
                        html.push(type === "ol" ? "<ol>" : "<ul>");
                        listStack.push({type, indent, liOpen: false});
                    }

                    html.push(`<li>${renderInlineMarkdown(content)}`);
                    listStack[listStack.length - 1].liOpen = true;
                    continue;
                }

                paragraph.push(trimmed);
            }

            flushParagraph();
            closeLists();
            if (inCode) {
                const langClass = codeLang ? ` class="language-${escapeHtml(codeLang)}"` : "";
                html.push(`<pre><code${langClass}>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
            }
            return html.join("\n");
        };

        return {render, renderInline: renderInlineMarkdown};
    }

    window.MarkdownRenderer = {create: createRenderer, escapeHtml};
}());
