# Character Evolution Loop — incubator v0.4

一个面向小说漫改的角色设计闭环。目标不是反复“抽卡”，而是让角色在 **原著证据 + 视觉导演 + 视觉审稿 + 长期记忆 + 人类反馈** 的约束下逐轮收敛。

## 当前真实链路

```text
Novel → Canon/RAG repository
          ↓
passage-free Character Contract
          ↓
Canon Adapter
          ↓
Character State V01
          ↓
CharacterGenerationPrompt
          ↓
ComfyUI API workflow
          ↓
8 candidates
          ↓
Vision Critic
          ↓
Acceptance Policy
          ↓
A / B / C shortlist
          ↓
Revision Patch
          ↓
Character State V02
```

## 已实现

### Canon / State

- `CanonProfile`：hard facts、soft traits、禁止解释与证据指针。
- `CharacterState`：版本、锁定项、可修改项、拒绝项、人工反馈与历史。
- Canon 与视觉评分分离：
  - `canon_constraints`
  - `design_targets`
  - `evidence_refs`
  - `canon_source`
  - `forbidden_interpretations`
- `canon_adapter.py`：读取 `character-canon-contract/1` 并合并到 Character State。
- Canon 与已有 lock 冲突时 fail fast，不静默覆盖。

### Generation

- `CharacterGenerationPrompt`：从 Canon/State 动态编译生成提示，不把陆辛写死在代码里。
- `ComfyUICharacterGenerator`：
  - 读取 API format workflow JSON
  - 只修改指定 prompt / seed
  - POST `/prompt`
  - 轮询 `/history/{prompt_id}`
  - 从 `/view` 下载真实输出图
  - 默认一轮生成 8 张不同 seed 候选
- 生图模型完全由 workflow 决定，可替换 Qwen-Image / Flux / SDXL / LoRA / ControlNet。

### Visual Critic

`OpenAICompatibleVisionCritic` 对每张候选图返回结构化评分：

- `canon`
- `ordinary`
- `office_worker`
- `restraint`
- `identity_clarity`
- `overbeautification_control`

并返回：

- problems
- 最多 3 项 change requests
- locked violations
- evidence alignment

Critic 不允许把“更帅”“更像主角”当默认加分项，也不能把单张生成图反向写成原著事实。

### Acceptance / A-B-C

默认门槛：

```text
overall >= 78
canon >= 85
identity_clarity >= 72
locked violations = 0
```

任何 locked violation 都会排在所有 lock-safe 候选之后，即使它其它分数很高。

每轮：

1. 生成 8 张。
2. 逐张 Critic。
3. 先淘汰 Canon / Lock 违规。
4. 按 Canon → overall → 最低维度排序。
5. 输出 A/B/C。
6. 选中最佳候选后只允许最多 3 项 Revision Patch。
7. 保存下一版 Character State。

## 《从红月开始》当前 V01

证据层来自独立仓库 `wa52/1-2203151F522`：

- 897 章
- 3893 chunks
- `canon/lu_xin.profile.json`
- `canon/lu_xin.character_contract.json`

本项目真实快照：

```text
examples/lu_xin_canon_contract.json
examples/lu_xin_state_v01.json
```

V01 Canon locks：

- `age = 23`
- `daily_role_context = company_office_worker`

软方向：

- 日常形象保持普通、低主角光环。
- 家庭异常场景偏克制、平静，但不能解释成“没有情感”。

仍允许视觉探索：

- face_shape
- hairstyle
- eyes
- body_proportions
- height
- clothing
- attractiveness
- posture

人工反馈仍保留：

> 日常状态首先应该像普通上班族，不要主动往帅或强者方向设计。

## 本机真实运行

进入目录：

```powershell
cd experiments/character_evolution_loop
```

复制配置：

```powershell
Copy-Item config/character_v01.example.json config/character_v01.local.json
Copy-Item workflows/character_portrait.api.example.json workflows/character_portrait.api.json
```

把 `workflows/character_portrait.api.json` 中的 checkpoint 或节点替换成你本机真实人物工作流，并确认 `config/character_v01.local.json` 中：

```json
{
  "prompt_node": "6",
  "seed_node": "3",
  "output_node": "9"
}
```

与实际 workflow 节点一致。

配置视觉模型：

```powershell
$env:CHARACTER_VISION_API_KEY = "你的 API Key"
```

然后运行：

```powershell
python run_character_round.py --config config/character_v01.local.json
```

默认生成：

```text
runs/character_evolution/<角色>/v002/candidate-01-....png
...
runs/character_evolution/<角色>/v002/candidate-08-....png
runs/character_evolution/latest_batch.json
runs/character_evolution/latest_state.json
```

`latest_batch.json` 中直接包含 A/B/C、各维度评分、违规项、下一轮 Patch 和选中的实际图片路径。

## 安全边界

- 原著全文不复制进 Character Evolution 仓库。
- API key 只走环境变量。
- `character_v01.local.json`、真实 workflow、runs 输出均已 gitignore。
- 未确认外貌保持 modifiable。
- 生图结果不能反向升级成 Canon。
- Director 不得修改 locked feature。
- Revision Patch 默认最多改 3 项。

## 验收

```powershell
python -m unittest discover -s tests -v
```

GitHub Actions 会在该分支和 PR 上执行同一套测试。

## 下一阶段

v0.4 已完成“代码层面的真实 Generator + Critic + A/B/C 闭环”。下一步是：

1. 用你本机 ComfyUI 的真实人物 workflow 跑第一批陆辛 8 张。
2. 查看实际 A/B/C。
3. 根据视觉结果调整 Critic rubric / Prompt，而不是先猜参数。
4. 加“用户选择 A/B/C”入口，让人工选择成为长期 Memory。
5. 增加办公室 / 家庭 / 异常事件三场景一致性验证。

> 当前仓库已经具备真实调用能力，但 GitHub Actions 无法访问你电脑的 `127.0.0.1:8190`，因此 CI 验证的是 API 协议、排序、约束和状态推进；第一次真实人物出图必须在运行 ComfyUI 的本机执行。
