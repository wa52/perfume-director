# Character Evolution Loop — incubator v0.2

一个面向小说漫改的角色设计闭环。目标不是反复“抽卡”，而是让角色在 **原著证据 + 视觉导演 + 视觉审稿 + 长期记忆 + 人类反馈** 的约束下逐轮收敛。

## 核心链路

```text
Novel → Local Corpus → Canon/RAG → Character Director → Image Generator
                                      ↑                 ↓
Human Feedback ← Memory ← Revision Patch ← Visual Critic
                                                   ↓
                                            Scene Validation
```

## v0.1 已实现的收敛机制

- `CanonProfile`：保存 hard facts、soft traits、禁止解释与证据指针。
- `CharacterState`：保存版本、锁定特征、可修改项、拒绝项、人工反馈与历史。
- `CharacterDirector`：Critic 只能产生小范围 Revision Patch，每轮默认最多改 3 项。
- `CharacterMemory`：JSON 长期记忆；锁定过的特征不会被后续 Agent 随意改回去。
- `CharacterEvolutionLoop`：候选生成 → 分项审稿 → 选优 → Patch → 状态持久化。
- `prompts.py`：Canon / Director / Critic / Scene Validator 的基础系统约束。

## v0.2 小说语料导入

《从红月开始》仍是商业版权作品，所以公开仓库不提交从网络抓取的整本正文。项目保存官方来源元数据，并提供本地导入管线。

把你合法获得的 TXT 放到：

```text
corpus/private/from-red-moon.txt
```

运行：

```bash
python ingest_novel.py corpus/private/from-red-moon.txt
```

会生成：

```text
corpus/index/chapters.jsonl
corpus/index/manifest.json
```

`corpus/private/` 和 `corpus/index/` 默认都被 `.gitignore` 排除，避免把小说正文或由正文生成的大段索引误提交到公开 GitHub。

`sources/manifest.json` 记录起点中文网和 WebNovel 的官方来源入口。后续 Canon RAG 只从本地索引读取正文，每条人物事实必须回写章节、chunk 和证据位置。

## 为什么先做这一层

真正容易让角色失控的不是“模型画得不够好”，而是：第 15 轮破坏第 3 轮已经确认的脸、Critic 每轮全量重写、用户意见没有进入长期状态、只看单头像而没有跨场景验收。v0.1 专门先把这些问题锁死；v0.2 再把原著证据入口接上。

## 运行测试

```bash
cd experiments/character_evolution_loop
python -m unittest discover -s tests -v
```

只依赖 Python 标准库。

## 下一阶段

1. 在 `chapters.jsonl` 上实现 chunking + BM25/向量检索 + 角色证据提取，生成可审计 Canon Profile。
2. 接入视觉模型，让 Critic 输出结构化维度分数与最大偏差。
3. 接 ComfyUI / 其他生图 Provider，一轮生成 8 张、自动淘汰、保留 3 张候选。
4. 增加人物一致性与 Scene Validator：办公室、家庭关系、异常事件三类场景验收。
5. 做 Web Director Console：原著证据 / A-B-C 候选 / 锁定项 / 版本树 / 人工反馈在同一页完成。

> `examples/lu_xin_state.json` 只是根据当前讨论创建的初始状态模板，不包含未经核验的小说原文事实；真实 Canon 必须在小说文本导入后由证据检索生成。
