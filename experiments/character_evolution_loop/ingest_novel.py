from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


CHAPTER_RE = re.compile(
    r"(?m)^\s*(第[零〇一二三四五六七八九十百千万两\d]+章[^\n]*)\s*$"
)


@dataclass(slots=True)
class Chapter:
    chapter_id: str
    title: str
    text: str
    start_char: int
    end_char: int


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", raw, 0, 1, "unsupported text encoding")


def split_chapters(text: str) -> list[Chapter]:
    matches = list(CHAPTER_RE.finditer(text))
    if not matches:
        clean = text.strip()
        return [
            Chapter(
                chapter_id="ch-0001",
                title="全文",
                text=clean,
                start_char=0,
                end_char=len(text),
            )
        ] if clean else []

    chapters: list[Chapter] = []
    prefix = text[: matches[0].start()].strip()
    if prefix:
        chapters.append(
            Chapter(
                chapter_id="front-matter",
                title="章前内容",
                text=prefix,
                start_char=0,
                end_char=matches[0].start(),
            )
        )

    for idx, match in enumerate(matches, start=1):
        body_start = match.end()
        body_end = matches[idx].start() if idx < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        chapters.append(
            Chapter(
                chapter_id=f"ch-{idx:04d}",
                title=match.group(1).strip(),
                text=body,
                start_char=match.start(),
                end_char=body_end,
            )
        )
    return chapters


def sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_index(input_path: Path, output_dir: Path) -> tuple[Path, Path]:
    text = read_text(input_path)
    chapters = split_chapters(text)
    if not chapters:
        raise ValueError("input novel is empty")

    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "chapters.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as fh:
        for chapter in chapters:
            row = asdict(chapter)
            row["char_count"] = len(chapter.text)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "source_file": input_path.name,
        "source_sha256": sha256_bytes(input_path),
        "chapter_count": len(chapters),
        "character_count": len(text),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": "local-user-provided-or-legally-obtained-text",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return jsonl_path, manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a local chapter index from a legally obtained novel TXT."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("corpus/index"),
        help="Output directory; defaults to corpus/index",
    )
    args = parser.parse_args()
    jsonl_path, manifest_path = build_index(args.input, args.output)
    print(f"wrote {jsonl_path}")
    print(f"wrote {manifest_path}")


if __name__ == "__main__":
    main()
