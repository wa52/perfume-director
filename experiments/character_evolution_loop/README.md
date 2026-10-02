# Character Evolution Loop — incubator v0.3

一个面向小说漫改的角色设计闭环。目标不是反复“抽卡”，而是让角色在 **原著证据 + 视觉导演 + 视觉审稿 + 长期记忆 + 人类反馈** 的约束下逐轮收敛。

## 核心链路

```text
Novel → Canon/RAG repository
          ↓
passage-free Character Contract
          ↓
Canon Adapter → Character State → Prompt Renderer → Image Generator
                                      ↑                    ↓
Human Feedback ← Memory ← Revision Patch ← Visual Critic
                                                   ↓
                                            Scene Validation
```

## 已实现

- `CanonProfile`：保存 hard facts、soft traits、禁止解释与证据指针。
- `CharacterState`：保存版本、锁定项、可修改项、拒绝项、人工反馈与历史。
- Canon 数据与视觉评分彻底分离：
  - `canon_constraints`
  - `design_targets`
  - `evidence_refs`
  - `canon_source`
  - `forbidden_interpretations`
- `CharacterDirector`：Critic 只能产生小范围 Revision Patch，每轮默认最多改 3 项。
- `CharacterMemory`：JSON 长期记忆；锁定特征不能被后续 Agent 随意改回去。
- `CharacterEvolutionLoop`：候选生成 → 分项审稿 → 选优 → Patch → 状态持久化。
- `CanonPromptRenderer`：硬事实、软方向、可编辑项、禁止误读、人工反馈、Revision Patch 分区输出。
- `canon_adapter.py`：读取 `character-canon-contract/1`，自动把原著证据合并进 Character State。

## 《从红月开始》当前接入状态

原著证据层由独立仓库 `wa52/1-2203151F522` 生成。该仓库从清洗后的全文构建：

- 897 个章节
- 3893 个 RAG chunks
- `canon/lu_xin.profile.json`
- `canon/lu_xin.character_contract.json`

Character Contract 不复制小说正文，只包含 Canon 约束与章节 / chunk / 行号证据锚点。

当前真实快照：

```text
examples/lu_xin_canon_contract.json
examples/lu_xin_state_v01.json
```

V01 当前锁定：

- `age = 23`
- `daily_role_context = company_office_worker`

软方向：

- 日常形象保持普通、低主角光环。
- 家庭异常场景表演偏克制、平静，但不能解释成“没有情感”。

仍未锁定、允许继续视觉探索：

- face shape
- hairstyle
- eyes
- body proportions
- height
- clothing
- attractiveness
- posture

同时保留人工反馈：日常首先像普通上班族，不主动往帅或强者方向设计。

## 重新导入 Contract

```bash
cd experiments/character_evolution_loop

python import_canon_contract.py \
  examples/lu_xin_canon_contract.json \
  --state examples/lu_xin_state.json \
  --output examples/lu_xin_state_v01.json
```

如果新的 Canon Contract 与已经锁定的 Character State 冲突，导入器会直接报错，不会静默覆盖。

## 验收

```bash
cd experiments/character_evolution_loop
python -m unittest discover -s tests -v
```

当前本地同构测试：8/8 PASS。

关键验收规则：

1. Canon locked fact 必须带 chapter / chunk / line evidence。
2. Canon 硬事实不能与视觉评分混在 `traits` 中。
3. 未核实外貌必须保持 modifiable。
4. Human feedback 导入 Canon 后仍必须保留。
5. Canon 与已有 lock 冲突时必须 fail fast。
6. Director 不得修改 locked feature。
7. 每轮 Revision Patch 默认最多修改 3 项。

## 下一阶段

1. 接 ComfyUI Generator：一轮生成 8 张。
2. 接真实视觉模型 Critic：按 ordinary / office-worker / restraint / canon / identity consistency 等维度评分。
3. 自动淘汰明显违背 Canon 或 locked features 的候选，只保留 A/B/C。
4. 用户选择 A/B/C 或写反馈后更新 Character Memory。
5. 做固定 Scene Validation：办公室、家庭关系、异常事件。
6. 再进入 V02 → V03 → … 的持续人物收敛。

> 原著全文只留在用户自己的合法语料环境；Character Evolution Loop 只需要 passage-free Contract 和证据锚点。
