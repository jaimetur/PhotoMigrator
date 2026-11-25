import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lang import i18n  # noqa: E402

SAMPLE_PO = r'''
msgid ""
msgstr ""
"Language: es\n"

msgid "Sign in"
msgstr "Entrar"

msgid "{0} users"
msgstr "{0} usuarios"

msgid "Hi {0},"
msgstr "Hola {0}:"

msgid "your task <b>{0}</b> finished successfully."
msgstr "tu tarea <b>{0}</b> ha terminado bien."

msgid "Create a processed copy "
"of the folder."
msgstr "Crea una copia procesada "
"de la carpeta."

#, fuzzy
msgid "Run"
msgstr "Correr"

msgid "Say \"hello\""
msgstr "Di \"hola\""

msgid "Untranslated"
msgstr ""
'''


class TestLangI18n(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        Path(self.temp_dir.name, "es.po").write_text(SAMPLE_PO, encoding="utf-8")
        lang_dir_patch = patch.object(i18n, "LANG_DIR", Path(self.temp_dir.name))
        lang_dir_patch.start()
        self.addCleanup(lang_dir_patch.stop)
        i18n._load.cache_clear()
        self.addCleanup(i18n._load.cache_clear)
        self.addCleanup(self.temp_dir.cleanup)

    def test_parse_po_reads_multiline_and_escaped_entries_and_skips_fuzzy_and_empty_ones(self):
        entries = i18n.parse_po(SAMPLE_PO)
        self.assertEqual(entries["Create a processed copy of the folder."], "Crea una copia procesada de la carpeta.")
        self.assertEqual(entries['Say "hello"'], 'Di "hola"')
        self.assertNotIn("Run", entries)
        self.assertNotIn("Untranslated", entries)

    def test_translate_uses_exact_texts_patterns_and_falls_back_to_english(self):
        self.assertEqual(i18n.translate("  Sign in ", "es"), "  Entrar ")
        self.assertEqual(i18n.translate("3 users", "es-ES"), "3 usuarios")
        self.assertEqual(i18n.translate(": Sign in", "es"), ": Entrar")
        self.assertEqual(i18n.translate("Unknown text", "es"), "Unknown text")
        self.assertEqual(i18n.translate("Sign in", "en"), "Sign in")
        self.assertEqual(i18n.translate("Sign in", "xx"), "Sign in")

    def test_translate_html_keeps_tags_and_translates_each_block(self):
        markup = "<h1>Sign in</h1><p>Hi alex,</p><p>your task <b>Find Duplicates</b> finished successfully.</p>"
        self.assertEqual(
            i18n.translate_html(markup, "es"),
            "<h1>Entrar</h1><p>Hola alex:</p><p>tu tarea <b>Find Duplicates</b> ha terminado bien.</p>",
        )

    def test_language_detection(self):
        self.assertEqual(i18n.clean("pt-BR"), "pt")
        self.assertIsNone(i18n.clean("xx"))
        self.assertEqual(i18n.from_accept_language("xx-XX, de-CH;q=0.9, en;q=0.8"), "de")
        self.assertIsNone(i18n.from_accept_language(""))

    def test_project_catalogs_keep_placeholders_and_tags(self):
        i18n._load.cache_clear()
        with patch.object(i18n, "LANG_DIR", PROJECT_ROOT / "lang"):
            for code in i18n.LANGS:
                if code == i18n.DEFAULT:
                    continue
                path = PROJECT_ROOT / "lang" / f"{code}.po"
                if not path.exists():
                    continue
                for key, value in i18n.parse_po(path.read_text(encoding="utf-8")).items():
                    with self.subTest(lang=code, text=key[:60]):
                        self.assertEqual(sorted(i18n.re.findall(r"\{\d\}", key)), sorted(i18n.re.findall(r"\{\d\}", value)))
                        self.assertEqual(sorted(i18n.re.findall(r"</?\w+[^>]*>", key)), sorted(i18n.re.findall(r"</?\w+[^>]*>", value)))


if __name__ == "__main__":
    unittest.main()
