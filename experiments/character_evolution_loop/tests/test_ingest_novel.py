import tempfile
import unittest
from pathlib import Path

from ingest_novel import build_index, split_chapters


class NovelIngestTests(unittest.TestCase):
    def test_split_chinese_chapters(self):
        text = "前言\n第一章 普通的一天\n内容A\n第二章 红月\n内容B\n"
        chapters = split_chapters(text)
        self.assertEqual(chapters[0].chapter_id, "front-matter")
        self.assertEqual(chapters[1].title, "第一章 普通的一天")
        self.assertEqual(chapters[1].text, "内容A")
        self.assertEqual(chapters[2].text, "内容B")

    def test_single_document_fallback(self):
        chapters = split_chapters("没有标准章节标题的文本")
        self.assertEqual(len(chapters), 1)
        self.assertEqual(chapters[0].title, "全文")

    def test_build_index_writes_jsonl_and_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            novel = root / "novel.txt"
            novel.write_text("第一章 A\n正文\n第二章 B\n正文2", encoding="utf-8")
            jsonl_path, manifest_path = build_index(novel, root / "index")
            self.assertTrue(jsonl_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertEqual(len(jsonl_path.read_text(encoding="utf-8").splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
