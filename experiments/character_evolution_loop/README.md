# Character Evolution Loop — incubator v0.1

一个面向小说漫改的角色设计闭环。目标不是反复“抽卡”，而是让角色在 **原著证据 + 视觉导演 + 视觉审稿 + 长期记忆 + 人类反馈** 的约束下逐轮收敛。

## 核心链路

```text
Novel → Canon/RAG → Character Director → Image Generator
                         ↑                 ↓
Human Feedback ← Memory ← Revision Patch ← Visual Critic
                                      ↓
                               Scene Validation
```

v0.1 先实现最关键的收敛机制，不绑定任何模型供应商：

- `CanonProfile`：保存 hard facts、soft traits、禁止解释与证据指针。
- `CharacterState`：保存版本、锁定特征、可修改项、拒绝项、人工反馈与历史。
- `CharacterDirector`：Critic 只能产生小范围 Revision Patch，每轮默认最多改 3 项。
- `CharacterMemory`：JSON 长期记忆；锁定过的特征不会被后续 Agent 随意改回去。
- `CharacterEvolutionLoop`：候选生成 → 分项审稿 → 选优 → Patch → 状态持久化。
- `prompts.py`：Canon / Director / Critic / Scene Validator 的基础系统约束。

## 为什么先做这一层

真正容易让角色失控的不是“模型画得不够好”，而是：第 15 轮破坏第 3 轮已经确认的脸、Critic 每轮全量重写、用户意见没有进入长期状态、只看单头像而没有跨场景验收。v0.1 专门先把这些问题锁死。

## 运行测试

```bash
cd experiments/character_evolution_loop
python -m unittest discover -s tests -v
```

只依赖 Python 标准库。

## 下一阶段

1. 小说导入与分章切片，建立 Canon RAG，并强制每条人物事实带原文证据。
2. 接入视觉模型，让 Critic 输出结构化维度分数与最大偏差。
3. 接 ComfyUI / 其他生图 Provider，一轮生成 8 张、自动淘汰、保留 3 张候选。
4. 增加人物一致性与 Scene Validator：办公室、家庭关系、异常事件三类场景验收。
5. 做 Web Director Console：原著证据 / A-B-C 候选 / 锁定项 / 版本树 / 人工反馈在同一页完成。

> `examples/lu_xin_state.json` 只是根据当前讨论创建的初始状态模板，不包含未经核验的小说原文事实；真实 Canon 必须在小说文本导入后由证据检索生成。
