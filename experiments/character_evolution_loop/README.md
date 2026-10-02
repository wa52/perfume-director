# Character Evolution Loop — incubator v1.0

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

## v0.7：项目级导演台

这一版把单角色实验升级成可以长期使用的项目层：

- **多角色注册表**：`config/characters.example.json` 定义角色 id / 名称 / contract / base state / local config / run directory。
- **角色切换**：Web 顶部可以切换已注册角色；不同角色使用独立 run 目录，state / batch / scene 不串写。
- **后台任务队列**：生成下一轮与三场景验证通过 `job_id` 后台执行，页面每秒轮询状态，不再用一个长 HTTP 请求阻塞。
- **同角色互斥**：同一角色不能同时跑两个长任务；不同角色可以独立运行。
- **版本归档**：每轮生成前、生成后、人工确认后、场景验证后都会保存 `versions/vNNN/`。
- **版本回滚**：Web 版本卡可以恢复对应的 state / batch / scene；归档本身保留。
- **配置体检**：网页检查 contract/base state/local config、ComfyUI workflow、prompt/output/seed/reference 节点、Critic 模型/API key 环境变量，并可尝试连接 `/system_stats`。
- **前端语法验收**：CI 新增 `node --check web_console/static/app.js`。

本地多角色配置建议复制：

```powershell
Copy-Item config/characters.example.json config/characters.local.json
```

然后为新角色新增一项：

```json
{
  "id": "new_character",
  "name": "新角色",
  "contract": "examples/new_character_contract.json",
  "base_state": "examples/new_character_state_v01.json",
  "config": "config/new_character.local.json",
  "run_dir": "runs/characters/new_character"
}
```

网页仍然通过：

```text
http://127.0.0.1:8765
```

访问。角色切换、配置检查、生成任务、三场景任务、回滚都在同一页完成。

## v0.8：作品级风格锁 + 自动角色发现

### 作品级 Art Direction

`config/work_style.example.json` 定义整部作品共享的视觉语言，而不是某个角色的脸：

- 2D animation medium
- clean controlled linework
- restrained cel shading
- natural human proportions
- graphic rather than photorealistic material rendering
- character-readable medium / half-body default framing
- background supports acting instead of dominating it

同时明确拒绝默认漂移到：

- glossy mobile-game splash art
- generic Korean webtoon beauty template
- photorealistic skin
- excessive neon cyberpunk
- ordinary scenes rendered as hero posters

角色脸型、眼睛、发型、身材等仍属于 Character State 的可迭代空间。**作品风格锁和人物身份锁是两套不同约束。**

每个角色配置可以引用：

```json
{
  "art_direction_path": "config/work_style.example.json"
}
```

生成角色轮次和三场景验证都会自动带上同一套 Art Direction。

Web Director 左侧会显示当前作品级风格锁，配置体检也会检查它。

### 自动发现主要角色

原著 Canon 仓库 `wa52/1-2203151F522` 已增加：

```text
tools/discover_characters.py
tools/build_character_drafts.py
canon/character_discovery.json
canon/character_drafts.json
```

发现器不再使用简单汉字高频，而是先要求角色名称出现在“名字 → 说/问/看/点头/开口”等主体动作结构或自我介绍结构中，再统计跨章节覆盖。

当前全文自动产生 **13 个 Canon 待审角色草稿**，包括：

- 陆辛
- 陈菁
- 韩冰
- 白教授
- 壁虎
- 安博士
- 夏虫
- 老院长
- 秦燃
- 二号
- 苏先生
- 沈部长
- 高婷

这些条目只是 `CANON_REVIEW_REQUIRED` 草稿，**不会因为出现频率高就自动获得外貌、性格或进入生成器**。

每个草稿只有：

- 名称
- 候选类型（个人名 / 称谓 / 代号）
- 出现次数
- 跨章节数
- 主体动作证据次数
- 首次出现章节/chunk
- Canon Contract = null
- Base State = null
- registry_ready = false

下一步必须先为草稿建立证据绑定的 Canon Profile / Contract，才允许加入 Character Director 注册表。

## v0.9：陈菁 / 韩冰 / 壁虎进入人物迭代

Canon 仓库已为三名高频主要角色生成 evidence-bound Profile 与 passage-free Contract：

```text
canon/chen_jing.profile.json
canon/chen_jing.character_contract.json

canon/han_bing.profile.json
canon/han_bing.character_contract.json

canon/bi_hu.profile.json
canon/bi_hu.character_contract.json
```

这些 Contract 的策略与陆辛不同：

- 暂时 **0 个 hard visual locks**
- 只加入 1 个跨章节证据支持的 `recurring_work_context` soft constraint
- 年龄、脸型、发型、眼睛、身材、身高、服装、颜值、默认表情、默认姿势全部保持 unresolved
- appearance / clothing / demeanor 的词法证据只留作 Canon Review Candidate，不直接进入生成硬约束

这样可以开始探索人物形象，同时不会把“某个词在同一个 chunk 出现”误当成角色本人固定外貌。

Character Director 现在内置四个角色：

```text
陆辛
陈菁
韩冰
壁虎
```

新增角色分别拥有独立：

- Canon Contract
- V01 Character State
- run directory
- version archive
- identity anchor
- human feedback / locks / rejects

默认仍共用同一个本机 ComfyUI workflow 和作品级 Art Direction。

### 角色自适应 Visual Critic

陆辛继续使用专用评分：

```text
canon
ordinary
office_worker
restraint
identity_clarity
overbeautification_control
```

其他角色使用通用评分：

```text
canon
context_fit
identity_clarity
character_specificity
design_coherence
overbeautification_control
```

因此陈菁、韩冰、壁虎不会因为共用系统而被错误要求“普通上班族感”。

### Scene Profile 隔离

当前 office / home / abnormal 三场景是陆辛专用。

注册表现在有：

```json
{
  "scene_validation_enabled": true
}
```

只有陆辛开启。陈菁、韩冰、壁虎在建立各自 Scene Profile 前，Web 上的三场景验证按钮保持关闭，避免拿错角色模板验收。

### 本地注册表升级兼容

`characters.example.json` 现在提供内置角色；已有 `characters.local.json` 不再完全覆盖它，而是作为 override / extension 合并。

因此旧本地配置继续存在时，新内置角色也能自动出现，不需要手工重建整份注册表。

## v1.0：Director Agent 建议 → 可见 → 可采用 → 真正进入下一轮

之前的 `CharacterDirector` 主要是规则式 Patch 过滤器：它能限制最多修改 3 项、保护 Lock，但不会像一个真正的导演 Agent 那样给出完整的优化判断。

v1.0 增加 `OpenAICompatibleDirectorAgent`，形成：

```text
候选图
  ↓
Vision Critic
  ├─ 各维度分数
  ├─ 具体问题
  └─ 原始 change_requests
  ↓
Director Agent
  ├─ summary
  ├─ strengths
  ├─ priority_issues
  ├─ KEEP
  ├─ CHANGE（最多 3 项）
  ├─ DO NOT CHANGE
  ├─ next_round_goal
  └─ evidence / human-feedback guardrails
  ↓
Revision Patch
  ↓
下一轮 Prompt
```

### A / B / C 各有独立导演建议

为了控制调用成本，Director Agent 默认只对 shortlist A/B/C 运行。

Web 中选择 A、B 或 C 后，右侧会直接显示：

- 当前候选最值得保留什么
- 最大的 1–3 个偏差
- 下一轮具体改哪些视觉特征
- 每项为什么要改
- 哪些特征必须保持
- 哪些特征禁止回退
- 下一轮的单一目标

每条 `CHANGE` 都有“采用此建议”按钮，可以直接填入人工修改区，再由人继续调整。

### 人工反馈优先级

下一轮修改优先级明确为：

```text
Canon Lock
    >
Human explicit change / Lock / Reject
    >
Director Agent advice
    >
Vision Critic raw change_request
```

所以 Agent 负责提建议，人仍然做最终决定。

自然语言人工反馈也会持续写入 Character Memory，并进入后续 Prompt。

### Agent 失败不伪装成功

如果 Director LLM 调用失败：

- 当前生成轮不会整体报废
- 自动回退到规则式 CharacterDirector
- Web 明确显示“规则兜底”
- 保存真实错误信息到 `director_agent_error`
- 不会把规则建议伪装成 LLM Agent 输出

### 配置

默认情况下 Director Agent 直接复用 `critic` 的 OpenAI-compatible endpoint / model / API key，因此现有本地配置不需要增加新字段。

如需单独指定导演模型，可以加入：

```json
{
  "director": {
    "base_url": "https://YOUR_OPENAI_COMPATIBLE_ENDPOINT/v1",
    "model": "YOUR_TEXT_OR_VISION_MODEL",
    "api_key_env": "CHARACTER_VISION_API_KEY",
    "timeout_seconds": 120,
    "max_changes": 3
  }
}
```

配置体检会显示 `director_agent` 与 `director_api_key` 状态。

### Web Director

候选 A/B/C 现在会出现 `AGENT` 标记。

右侧新增：

```text
AGENT DIRECTOR
下一轮优化建议

导演判断
保留优点
优先问题
下一轮修改
KEEP
DO NOT CHANGE
下一轮目标
证据 / 人工反馈护栏
```

因此现在完整的人物养成循环已经变成：

```text
Generate 8
 → Vision Critic
 → A/B/C
 → Director Agent 给每张建议
 → 人查看图片 + Agent 建议
 → 人选 A/B/C
 → 可采用/修改 Agent 建议
 → Lock / Reject / Feedback
 → Character Memory
 → Revision Patch
 → 下一轮 8 张
```

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

v1.0 已补齐真正的 Director Agent 优化建议闭环。下一阶段重点：

1. 增加 **多轮改进评估**：比较 V02 → V03 后 Agent 建议是否真的让目标维度上升，而不是只给建议。
2. 给 Director Agent 增加 plateau / regression 判断：连续两轮不提升时自动改变探索策略。
3. 对陈菁、韩冰、壁虎的 appearance / clothing strongest evidence 做逐 chunk Canon Review。
4. 为每个角色建立独立 Scene Profile。
5. 增加角色版本分支：V04a / V04b，并比较哪条演化路线更好。
6. 建角色关系图与 alias resolution，继续扩展其余主要角色。

> 核心原则：自动模型负责提出和审稿，人负责确认角色是谁。一旦确认，系统要记住，而不是下一轮重新抽卡。
