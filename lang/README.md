# PhotoMigrator languages

The Web Interface is written in **English**, the source language. Every other language is a gettext catalog in this folder that translates from English:

| File | Content |
|---|---|
| `messages.pot` | Template with every English text of the Web Interface (pages, dialogs, statuses and emails). Do not translate it. |
| `<code>.po` | One catalog per language: `msgid` is the English text, `msgstr` its translation. |
| `i18n.js` | Translates the pages in the browser (texts, `title`, `placeholder`, `aria-label` and `alt`) and draws the language picker. |
| `i18n.py` | Reads the catalogs for the backend (page catalogs and emails) and lists the supported languages (`LANGS`). |

Supported languages: English (`en`), Español (`es`), Català (`ca`), Français (`fr`), Italiano (`it`), Deutsch (`de`), Português (`pt`), Nederlands (`nl`), 中文 (`zh`) and 日本語 (`ja`).

## Improve a translation

1. Open `lang/<code>.po` with any text editor or with a gettext editor such as [Poedit](https://poedit.net/).
2. Change the `msgstr` of the text. Keep exactly:
   - placeholders such as `{0}` and `{1}` (they are replaced by names, numbers or dates);
   - HTML tags such as `<b>` and `<br>`;
   - CLI flags (`--source`), paths, `Config.ini` keys, quoted values (`'list'`) and product names.
3. Open a pull request.

An empty `msgstr` (or an entry marked `#, fuzzy`) falls back to English.

## Add a language

1. Copy `messages.pot` to `lang/<code>.po` (two-letter ISO 639-1 code) and add `"Language: <code>\n"` to its header.
2. Translate the `msgstr` entries.
3. Add the language to `LANGS` in `lang/i18n.py`.

## Update the template after changing the interface

1. Start a local test Web Interface and collect its visible texts:
   `python tools/CollectUiTexts.py http://127.0.0.1:6078 ui_texts.json <admin user> <password>`
2. Rebuild `messages.pot` and add the new texts (untranslated) to every catalog:
   `python tools/UpdateTranslationTemplate.py --ui-texts ui_texts.json`

Code, commands, paths and logs are never translated: the pages mark them with `<code>`, `<pre>`, the `command` class or the `data-no-i18n` attribute.
