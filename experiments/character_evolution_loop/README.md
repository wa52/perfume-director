# Character Evolution Loop — incubator v0.6

一个面向小说漫改的角色设计闭环。目标不是反复“抽卡”，而是让角色在 **原著证据 + 自动审稿 + 人工选择 + 身份锚点 + 长期记忆 + 场景一致性验证** 下逐轮收敛。

## 当前完整链路

```text
Novel / Canon RAG
        ↓
passage-free Character Contract
        ↓
Character State V01
        ↓
ComfyUI → 8 candidates
        ↓
Vision Critic
        ↓
A / B / C shortlist
        ↓
Human Choice
        ↓
identity_anchor + feedback + locks + rejects
        ↓
Character State V02
        ↓
next ComfyUI round uses identity_anchor
        ↓
V03 / V04 / ...
        ↓
office + home + abnormal scene validation
```

## 自动排序不是最终决定

一轮生图结束后，程序会把 Critic 最好的三张标成 A/B/C，但这里只是：

```text
selection_status = PROVISIONAL_AUTO_RANKING
human_choice_required = true
```

**程序不会把自动第一名当成最终人物身份。**

只有执行人工选择后，所选图才会进入：

```text
state.identity_anchor
```

之后的下一轮生图、人物一致性和场景验证都以它为基准。

## 第一步：生成 8 张并得到 A/B/C

```powershell
cd experiments/character_evolution_loop

python run_character_round.py --config config/character_v01.local.json
```

第一次从 V01 开始；以后如果存在：

```text
runs/character_evolution/latest_state.json
```

会自动从最新的人类审阅状态继续，不会每次重新回到 V01。

输出：

```text
runs/character_evolution/<角色>/v002/candidate-*.png
runs/character_evolution/latest_batch.json
runs/character_evolution/latest_state.json
```

## 第二步：人工选择 A / B / C

例如你判断：

> B 最接近，但眼睛太锐，不要变成强者脸。

直接写入：

```powershell
python apply_human_choice.py \
  --choose B \
  --feedback "B最接近，但眼睛太锐，不要变成强者脸。" \
  --change "eyes=less sharp, neutral, ordinary gaze"
```

执行后：

- B 的实际图片路径成为 `identity_anchor`
- 反馈写入长期 `human_feedback`
- 本轮 history 改为人类最终选择
- B 的 Critic 修改建议与人工修改合并
- 自动生成下一轮 prompt

### 锁定满意特征

如果 B 的脸型已经满意：

```powershell
python apply_human_choice.py \
  --choose B \
  --lock "face_shape=keep-from-B"
```

以后 Director 不得再修改 `face_shape`。

### 永久拒绝某种设计

```powershell
python apply_human_choice.py \
  --choose B \
  --reject "aggressive_gaze" \
  --reject "fashionable_hair"
```

这些设计不会再作为后续 Revision Patch 目标。

> 带 Canon lock 违规的候选不能被提升为 identity anchor。比如未来如果出现与确定年龄/身份事实明显冲突的候选，人工选择入口也会阻止它进入正式状态。

## 第三步：下一轮真正沿用选中的身份

`ComfyUICharacterGenerator` 支持：

```json
{
  "reference_image_node": "你的参考图节点ID",
  "reference_image_input": "image"
}
```

只要你的 ComfyUI workflow 确实使用这个参考图节点（如 IPAdapter / InstantID / FaceID / 其它 identity-reference 链路），系统会：

1. 自动上传 `identity_anchor`
2. 把它写入参考图节点
3. 再修改 prompt / seed
4. 生成下一批 8 张

如果 workflow 没有参考图节点，仍能运行，但只能依赖 prompt/seed，身份稳定性会明显弱于 reference-aware workflow。

## 第四步：三场景一致性验证

固定验证三种场景：

### 1. Office

普通公司/办公室工作场景。

要求：

- 看起来仍是同一个人
- 保持普通上班族语境
- 不突然变成时尚精英或英雄构图

### 2. Home

家庭关系场景。

要求：

- 同一个身份
- 可以表情更柔和
- 保持克制、平静
- 不能把“平静”解释成没有感情

### 3. Abnormal

异常/高压事件。

要求：

- 可以紧张、警觉、动作改变
- 但不能换脸、换身体身份
- 不因为一个危险场景永久变成战士脸/反派脸

运行：

```powershell
python run_scene_validation.py --config config/character_v01.local.json
```

场景 workflow 必须实际消费身份参考图：

```json
{
  "scene_comfyui": {
    "workflow_path": "workflows/character_scene.api.json",
    "reference_image_node": "10",
    "reference_image_input": "image"
  }
}
```

默认 Scene Acceptance：

```text
identity_consistency >= 82
canon >= 80
overall >= 80
regression_features = []
```

Vision Scene Validator 会同时看到：

```text
Image 1 = 人工选中的 identity anchor
Image 2 = office
Image 3 = home
Image 4 = abnormal
```

它判断的是“是不是同一个角色”，而不是要求四张图表情/姿势完全一样。

## Canon 与陆辛 V01

原著证据来自：

`wa52/1-2203151F522`

当前证据层：

- 897 章
- 3893 chunks
- `canon/lu_xin.profile.json`
- `canon/lu_xin.character_contract.json`

目前只锁：

- `age = 23`
- `daily_role_context = company_office_worker`

软方向：

- 普通、低主角光环
- 家庭异常场景下克制/平静

仍然是视觉探索空间：

- face_shape
- hairstyle
- eyes
- body_proportions
- height
- clothing
- attractiveness
- posture

所以系统不会假装小说已经明确写出了陆辛应该长哪张脸。

## ComfyUI 配置

人物初始 workflow 可以从：

```text
workflows/character_portrait.api.example.json
```

开始。

真实本地文件：

```text
workflows/character_portrait.api.json
workflows/character_scene.api.json
config/character_v01.local.json
runs/
```

都已经 gitignore，不会把本地模型配置、API key 或生成图片误提交。

## Critic 维度

每张候选：

- canon
- ordinary
- office_worker
- restraint
- identity_clarity
- overbeautification_control

默认候选 Acceptance：

```text
overall >= 78
canon >= 85
identity_clarity >= 72
locked violations = 0
```

任何 locked violation 都排在所有 lock-safe 候选后面。

## Web Director Console

v0.6 已把命令行闭环搬到同一个本地网页，不引入 Node/Next.js，直接使用 Python 标准库服务。

启动：

```powershell
cd experiments/character_evolution_loop
python -m web_console.server
```

浏览器打开：

```text
http://127.0.0.1:8765
```

页面布局：

```text
┌──────────────┬──────────────────────────────┬──────────────────┐
│ Canon 原著证据 │ 8 张候选 / A-B-C / 版本历史     │ Human Review     │
│ Locks        │ 当前轮 Critic 分数             │ 反馈 / Lock / Reject│
│ 章节锚点       │ 三场景一致性                   │ identity anchor   │
└──────────────┴──────────────────────────────┴──────────────────┘
```

网页可以直接完成：

- 显示全部 8 张候选，不只 A/B/C。
- A/B/C 只是自动推荐标记。
- 点击候选查看完整 Critic 分数与问题。
- 写自然语言反馈。
- 指定一项重点修改。
- 勾选并锁定满意的视觉特征。
- 输入永久拒绝的设计。
- 点击“确认所选角色”写入 Character Memory。
- 点击“确认并继续下一轮”直接生成下一版。
- 点击“三场景验证”执行 office / home / abnormal 一致性检查。
- 查看 V01 → V02 → V03 历史。

网页只暴露固定的 Character Evolution 操作，不接受任意 shell 命令。生成图片读取也限制在 `runs/character_evolution/` 下，避免路径穿越读取其它本机文件。

## 测试

```powershell
python -m unittest discover -s tests -v
```

GitHub Actions 使用同一套测试验证：

- Canon → Character State
- Memory / lock
- bounded Revision Patch
- ComfyUI prompt / seed / download
- identity anchor 上传与参考节点注入
- Vision Critic schema
- A/B/C 排序
- 人工选择与反馈
- Canon 冲突
- 三场景 Vision Validator
- 场景身份回归拒绝

## 下一阶段

v0.6 已完成 Web Director Console 的第一版。下一阶段重点转为真正的产品化：

1. 增加版本回滚：从 V05 一键回到任意人工确认版本。
2. 增加多人角色管理，不再只显示陆辛。
3. 在网页内配置 ComfyUI workflow / 节点映射并做连通性检查。
4. 增加生成任务状态流，不让长时间 ComfyUI 请求阻塞页面。
5. 给三场景结果显示真实场景图、回归特征和对比视图。
6. 最终把 Character Director 从 `perfume-director` incubator 迁出为独立项目。

> 核心原则：自动模型负责提出和审稿，人负责确认角色是谁。一旦确认，系统要记住，而不是下一轮重新抽卡。
