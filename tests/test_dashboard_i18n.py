"""Tests for the dashboard translation cache (D16) and the D17 label change.

Covers scripts/dashboard_strings.py, scripts/dashboard-i18n.py and the
translation path in scripts/render-dashboard.py.

Run from the repository root:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
HELPER = SCRIPTS_DIR / "dashboard-i18n.py"
RENDERER = SCRIPTS_DIR / "render-dashboard.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS_DIR))
sys.dont_write_bytecode = True

strings = importlib.import_module("dashboard_strings")
render_mod = importlib.import_module("render-dashboard")


class KeyTest(unittest.TestCase):
    def test_key_is_the_first_16_hex_of_sha256(self):
        text = "Payment gateway integration"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        self.assertEqual(strings.translation_key(text), expected)
        self.assertEqual(len(strings.translation_key(text)), 16)

    def test_key_is_stable_and_distinct(self):
        self.assertEqual(
            strings.translation_key("abc"), strings.translation_key("abc")
        )
        self.assertNotEqual(
            strings.translation_key("abc"), strings.translation_key("abcd")
        )
        self.assertEqual(
            strings.translation_key("中文"), strings.translation_key("中文")
        )

    def test_translatable_field_set_is_shared_and_complete(self):
        item_list = json.loads(
            (FIXTURES / "english" / "00-current" / "item-list.json").read_text("utf-8")
        )
        archive = json.loads(
            (FIXTURES / "english" / "00-current" / "item-list-archive.json")
            .read_text("utf-8")
        )
        found = strings.iter_translatable(item_list, archive)
        originals = set(found.values())
        for text in (
            "Payment gateway integration and CSV export rework",
            "Payment gateway integration",
            "Define the payment DTO",
            "No sandbox account",
            "No sandbox account yet",
            "Finance to enable the sandbox merchant id",
            "Do you want full phone numbers in the CSV?",
            "Mask them as 138****1234",
            "Create the new tables",
        ):
            with self.subTest(text=text):
                self.assertIn(text, originals)
        for text in (
            "checkout-service refactor",
            "ITEM-003",
            "TASK-003-01",
            "in_progress",
            "one sandbox order succeeds",
            "migrations/001_init.sql",
            "20-working/ITEM-003",
        ):
            with self.subTest(text=text):
                self.assertNotIn(text, originals)

    def test_empty_strings_are_skipped(self):
        found = strings.iter_translatable(
            {"assignment": {"description": "  "}, "items": []}, {}
        )
        self.assertEqual(found, {})

    def test_helper_and_renderer_share_one_field_list(self):
        helper_src = HELPER.read_text(encoding="utf-8")
        renderer_src = RENDERER.read_text(encoding="utf-8")
        self.assertIn("dashboard_strings", helper_src)
        self.assertIn("dashboard_strings", renderer_src)
        self.assertEqual(strings.TASK_FIELDS, ("description", "notes"))
        self.assertEqual(
            strings.BLOCKER_FIELDS,
            ("summary", "question", "default_action", "waiting_on"),
        )


class CacheCliTest(unittest.TestCase):
    def project(self, fixture: str = "english") -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "project"
        shutil.copytree(FIXTURES / fixture, root)
        return root

    def helper(self, *args: str, expect: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, str(HELPER), *args], capture_output=True, text=True
        )
        self.assertEqual(
            result.returncode,
            expect,
            msg=f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        return result

    def cache_file(self, root: Path) -> Path:
        return root / "00-current" / "dashboard-translations.json"

    def write_payload(self, root: Path, payload: dict) -> Path:
        path = root / "payload.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_list_missing_returns_every_string_when_no_cache(self):
        root = self.project()
        result = self.helper("list-missing", str(root))
        payload = json.loads(result.stdout)
        self.assertEqual(payload["language"], "zh-CN")
        key = strings.translation_key("Payment gateway integration")
        self.assertIn(key, payload["missing"])
        self.assertEqual(payload["missing"][key], "Payment gateway integration")
        self.assertFalse(self.cache_file(root).exists())

    def test_list_missing_honours_language_flag_and_skips_cached(self):
        root = self.project()
        key = strings.translation_key("Payment gateway integration")
        strings.write_cache(self.cache_file(root), {key: "支付网关对接"}, "zh-CN")
        result = self.helper("list-missing", str(root), "--language", "ja")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["language"], "ja")
        self.assertNotIn(key, payload["missing"])
        self.assertIn(
            strings.translation_key("Order export to CSV"), payload["missing"]
        )

    def test_apply_merges_and_sorts_keys(self):
        root = self.project()
        payload = {
            strings.translation_key("Payment gateway integration"): "支付网关对接",
            strings.translation_key("Order export to CSV"): "订单导出 CSV",
        }
        self.helper("apply", str(root), str(self.write_payload(root, payload)))
        cache = json.loads(self.cache_file(root).read_text(encoding="utf-8"))
        self.assertEqual(cache["language"], "zh-CN")
        self.assertEqual(cache["entries"], payload)
        keys = list(cache["entries"])
        self.assertEqual(keys, sorted(keys))

    def test_apply_reads_stdin_and_prunes_stale_entries(self):
        root = self.project("mockup")
        stale_key = strings.translation_key("a string that is not in the data")
        strings.write_cache(self.cache_file(root), {stale_key: "过期"}, "zh-CN")
        payload = {strings.translation_key("支付网关对接"): "支付网关对接（新）"}
        result = subprocess.run(
            [sys.executable, str(HELPER), "apply", str(root), "-"],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        cache = json.loads(self.cache_file(root).read_text(encoding="utf-8"))
        self.assertNotIn(stale_key, cache["entries"])
        self.assertEqual(cache["entries"], payload)

    def test_apply_rejects_unknown_keys_and_leaves_the_cache_alone(self):
        root = self.project()
        good_key = strings.translation_key("Payment gateway integration")
        strings.write_cache(self.cache_file(root), {good_key: "支付网关对接"}, "zh-CN")
        before = self.cache_file(root).read_text(encoding="utf-8")
        payload = {"deadbeefdeadbeef": "no such string"}
        result = self.helper(
            "apply", str(root), str(self.write_payload(root, payload)), expect=1
        )
        self.assertIn("unknown key", result.stderr)
        self.assertEqual(self.cache_file(root).read_text(encoding="utf-8"), before)

    def test_apply_rejects_non_string_values(self):
        root = self.project()
        payload = {strings.translation_key("Order export to CSV"): 42}
        result = self.helper(
            "apply", str(root), str(self.write_payload(root, payload)), expect=1
        )
        self.assertIn("must be a string", result.stderr)
        self.assertFalse(self.cache_file(root).exists())

    def test_prune_drops_stale_entries_only(self):
        root = self.project()
        keep = strings.translation_key("Payment gateway integration")
        stale = strings.translation_key("gone from the data")
        strings.write_cache(
            self.cache_file(root), {keep: "支付网关对接", stale: "x"}, "zh-CN"
        )
        self.helper("prune", str(root))
        cache = json.loads(self.cache_file(root).read_text(encoding="utf-8"))
        self.assertEqual(cache["entries"], {keep: "支付网关对接"})

    def test_prune_without_cache_is_a_noop(self):
        root = self.project()
        result = self.helper("prune", str(root))
        self.assertIn("nothing to prune", result.stdout)
        self.assertFalse(self.cache_file(root).exists())

    def test_missing_item_list_is_an_error(self):
        root = self.project()
        (root / "00-current" / "item-list.json").unlink()
        result = self.helper("list-missing", str(root), expect=1)
        self.assertIn("missing required file", result.stderr)


class RendererTranslationTest(unittest.TestCase):
    def project(self, fixture: str = "english") -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "project"
        shutil.copytree(FIXTURES / fixture, root)
        return root

    def render(self, root: Path, expect: int = 0) -> subprocess.CompletedProcess:
        result = subprocess.run(
            [sys.executable, str(RENDERER), str(root)], capture_output=True, text=True
        )
        self.assertEqual(
            result.returncode,
            expect,
            msg=f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        return result

    def page(self, root: Path) -> str:
        return (root / "00-current" / "dashboard.html").read_text(encoding="utf-8")

    def translate(self, root: Path, mapping: dict) -> None:
        payload = {strings.translation_key(text): value for text, value in mapping.items()}
        strings.write_cache(
            root / "00-current" / "dashboard-translations.json", payload, "zh-CN"
        )

    def test_translation_is_shown_and_original_stays_in_title(self):
        root = self.project()
        original = "Payment gateway integration"
        self.translate(root, {original: "支付网关对接"})
        self.render(root)
        text = self.page(root)
        self.assertIn("支付网关对接", text)
        self.assertIn(f'title="{original}"', text)
        self.assertNotIn(f">{original}<", text)

    def test_missing_entries_fall_back_to_the_original(self):
        root = self.project()
        self.translate(root, {"Payment gateway integration": "支付网关对接"})
        self.render(root)
        text = self.page(root)
        self.assertIn("支付网关对接", text)
        self.assertIn("Order export to CSV", text)

    def test_blocker_and_activity_text_are_translated(self):
        root = self.project()
        self.translate(
            root,
            {
                "Do you want full phone numbers in the CSV?": "CSV 里要放完整手机号吗？",
                "Mask them as 138****1234": "脱敏为 138****1234",
                "Finance to enable the sandbox merchant id": "财务部开通沙箱商户号",
            },
        )
        self.render(root)
        text = self.page(root)
        self.assertIn("CSV 里要放完整手机号吗？", text)
        self.assertIn("脱敏为 138****1234", text)
        self.assertIn("财务部开通沙箱商户号", text)
        self.assertIn('title="Do you want full phone numbers in the CSV?"', text)
        self.assertIn("TASK-004-02 受阻：等你：CSV 里要放完整手机号吗？", text)

    def test_malformed_cache_warns_and_renders_originals(self):
        root = self.project()
        cache = root / "00-current" / "dashboard-translations.json"
        cache.write_text("{not json", encoding="utf-8")
        result = self.render(root)
        self.assertIn("ignoring translation cache", result.stderr)
        self.assertIn("Payment gateway integration", self.page(root))

    def test_malformed_cache_entries_warns_and_renders_originals(self):
        root = self.project()
        cache = root / "00-current" / "dashboard-translations.json"
        cache.write_text(
            json.dumps({"language": "zh-CN", "entries": ["nope"]}), encoding="utf-8"
        )
        result = self.render(root)
        self.assertIn("ignoring translation cache", result.stderr)
        self.assertIn("Payment gateway integration", self.page(root))

    def test_render_is_deterministic_with_a_cache(self):
        first = self.project()
        second = self.project()
        for root in (first, second):
            self.translate(root, {"Payment gateway integration": "支付网关对接"})
            self.render(root)
        self.assertEqual(self.page(first).encode(), self.page(second).encode())

    def test_cache_is_optional(self):
        root = self.project()
        result = self.render(root)
        self.assertEqual(result.stderr, "")
        self.assertFalse(
            (root / "00-current" / "dashboard-translations.json").exists()
        )

    def test_english_data_is_unchanged_by_rendering(self):
        root = self.project()
        before = (root / "00-current" / "item-list.json").read_bytes()
        self.translate(root, {"Payment gateway integration": "支付网关对接"})
        self.render(root)
        self.assertEqual(
            (root / "00-current" / "item-list.json").read_bytes(), before
        )

    def test_d17_labels_use_the_new_wording(self):
        root = self.project()
        self.render(root)
        text = self.page(root)
        self.assertIn("进行中事项", text)
        self.assertIn("已完成事项", text)
        self.assertIn("进行中和待办的事项", text)
        self.assertIn("已结束的事项", text)
        self.assertNotIn("进行中 item", text)
        self.assertNotIn("已完成 item", text)
        self.assertNotIn("待办的 Items", text)
        self.assertNotIn("已结束的 Items", text)
        label_values = [
            value for value in render_mod.LABELS.values() if isinstance(value, str)
        ]
        self.assertFalse([value for value in label_values if "item" in value.lower()])


if __name__ == "__main__":
    unittest.main()
