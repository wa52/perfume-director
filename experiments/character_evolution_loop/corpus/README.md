# 小说语料目录

这里不提交《从红月开始》整本正文。该作品仍是商业版权作品；本项目只保存来源元数据和导入工具。

## 本地导入

把你**合法获得**的小说文本放到：

```text
corpus/private/from-red-moon.txt
```

然后运行：

```bash
python ingest_novel.py corpus/private/from-red-moon.txt
```

默认输出：

```text
corpus/index/chapters.jsonl
corpus/index/manifest.json
```

这些目录已经被 `.gitignore` 排除，不会误提交正文。

v0.2 先支持 UTF-8 TXT；后续可加 EPUB/PDF 解析。正文导入后，Canon Agent 应只从本地索引中提取事实，并给每条事实保存章节、标题和 chunk id 作为证据指针。
