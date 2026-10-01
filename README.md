# Perfume Director — 最小闭环 v0.1

只做香水、luxury 一个风格、最多 20 张参考、最多渲染 3 版。没有 LoRA、向量数据库或 agent 框架。

流程：参考分析 → Design KB → Director 输出 PosterSpec → ComfyUI 合成 → Critic 看成品、商品和 3 张参考 → 校验修改 → 下一版。

## 四种风格预览与仓库运行

![四种风格](samples/jadore-four-directions/comparison.png)

已保存黑金奢华、奶油极简、酒红编辑风、清新植物风四种实际 ComfyUI 渲染样例。各目录包含 PosterSpec、背景和成品，商品使用同一张原图。这些是供选择方向的预览，不是独立视觉模型自动审核通过的最终广告。

仓库包含 20 张参考、SQLite 审美库、商品来源和四种样例；模型权重、ComfyUI 环境、缓存和本地配置不上传。参考和商品图片的权利归原权利人，来源记录随文件保留。

换机器后先安装 Python 依赖，准备现有 ComfyUI、ComfyUI-GGUF 及 workflow 中指定的模型，然后复制配置：

```powershell
python -m pip install -r requirements.txt
Copy-Item config.comfy.example.json config.local.json
Copy-Item extra_model_paths.example.yaml extra_model_paths.local.yaml
```

修改 `extra_model_paths.local.yaml` 中的插件路径；用 `start_comfy.ps1 -ComfyRoot <ComfyUI目录> -ModelsRoot <模型目录>` 指定本机路径。四风格样例由 Codex 在对话里担任 Director/Critic；独立视觉 API 的两轮实际案例见下方智谱接入记录。

重现单张样例（复用背景）：

```powershell
python guided_render.py --spec samples/jadore-four-directions/02-cream-minimal/PosterSpec.json --output runs/reproduce/cream.png --background samples/jadore-four-directions/02-cream-minimal/background.png
```

## 已准备好的审美库

已从公开网页挑选、下载并逐张查看 20 张香水商业参考，覆盖 11 个品牌。浏览 `references/gallery.html`，来源与选择理由见 `references/sources.md`。

`kb/design_kb.sqlite3` 是 SQLite 数据库，保存图片原始字节、SHA-256、尺寸、来源网页、图片链接、类型、入选理由和结构化审美标注。图片另有文件副本保存在 `references/luxury/`；`kb/luxury.json` 是兼容导出。Director 优先读取数据库，并按适配分选择 3 个不同品牌，避免全选同一品牌。

当前标注来自 Codex 实际看图后的视觉审阅（`analysis_origin=codex_visual_review`），商品面积比例是估计值，适配分为选图偏好；没有调用你的外部视觉模型。已将人物广告、场景广告、商品静物和完整广告分别标记，且注明第一版可借鉴的范围。执行 `index` 可用你的视觉 API 重新分析，同步更新数据库并导出 JSON。

参考文件版权仍属于原权利人，数据库保留来源，商业复用授权未核实。只用于研究设计语言，不将品牌文字和成品广告直接用作你的最终海报。

`collect_references.py` 保存候选下载记录；404、403、超时和证书错误未绕过。未成功下载的候选不进入正式库。`reference_store.py` 可将审阅后的 `references/curated.json` 重新导入；已存在记录保留后续视觉 API 分析。

## 先运行演示

首次真实运行已完成，见 `samples/guided/jadore-20260930/`：商品原图 + 真实 ComfyUI 背景/合成 + Codex 逐版看图修改，共 3 版。查看[三轮对比](samples/guided/jadore-20260930/comparison.png)、[审阅报告](samples/guided/jadore-20260930/REPORT.md)和[结果记录](samples/guided/jadore-20260930/result.json)，最终选 v3；这次是对话引导模式，不是独立视觉 API 自动循环。

本机启动入口：`./start_comfy.ps1`，API 为 `http://127.0.0.1:8190`。它复用现有 ComfyUI (1) Python/GGUF 插件和共享模型，运行输出保存在项目 `runtime/`。脚本含本机路径，换机器需修改参数和 `extra_model_paths.local.yaml`。

```powershell
.\start_comfy.ps1
python guided_render.py --spec samples/guided/jadore-20260930/v3/PosterSpec.json --output runs/reproduce/poster.png --background samples/guided/jadore-20260930/v1/background.png
```

也可去掉 `--background`，按 Spec 重新生成 AI 背景。`config.local.json` 已配置本机渲染器；独立 Director/Critic 仍需填入视觉模型配置和 API 环境变量。

排查发现本机 `qwen_3_4b.safetensors` 内有 9 个非有限数值张量，会产生全黑背景；已绕开它，使用已有 `Qwen3-4B-UD-Q6_K_XL.gguf`，未下载新模型。细节与失败样本留在本轮 `diagnostics/`。新增文本条件、采样、解码数值校验与生成背景全黑检查。

商品合成现在会忽略原图的透明留边，并支持 `shadow.kind=contact` 的瓶底接触阴影和每个文字层的 `font` 字体路径。

在此目录运行（Python 3.10+）：

```powershell
python -m pip install -r requirements.txt
python poster.py demo
```

演示自动创建一个几何香水瓶示意图，以本地 Pillow 渲染 3 版。Critic 的修改和分数是**脚本预设**，只验证流程与文件留档，不代表视觉模型认为作品通过，也不证明审美提高。结果放在 `runs/demo/<id>/`。

## 直接在 ComfyUI 工作流运行闭环

已在界面点击运行并完成真实两轮：[实测报告](samples/comfyui-loop/jadore-20261001/REPORT.md)，V1 75 分未通过，自动改稿后 V2 86 分 PASS。本机工作流已另存为 `Perfume Director Loop`。

![ComfyUI 闭环入口](samples/comfyui-loop-ui.jpg)

加载 `workflows/director-loop.ui.json`，工作流只有两个入口节点：

`LoadImage（透明商品 PNG，IMAGE + MASK） → AI Art Director Loop（brief）`

首次安装/更新节点时运行 `./start_comfy.ps1 -Restart`，然后打开 `http://127.0.0.1:8190`，用 Ctrl+O 导入上述 JSON。在 LoadImage 上传商品，填写 brief，点击一次“运行”。节点显示 Director、Render、Critic 阶段以及最终 PASS/NEEDS_REVIEW、选中版本和成品预览。仍需现有 `config.local.json`、视觉 API 环境变量、参考数据库、ComfyUI 模型和字体。密钥不填写在工作流里。

这是整个闭环的入口，不是只有合成器。后台协调器运行原有 `poster.run`，自动向当前 ComfyUI 提交背景/合成工作流，最多三轮。入口节点立即返回 job_id，以释放 ComfyUI 单任务执行队列；若在同一个执行节点里等待自己排队的渲染，会造成死锁。节点 STRING 输出是任务 ID，最终海报由节点的后台预览显示，不作为同步 IMAGE 输出连接到 SaveImage。

视觉阶段的 ComfyUI 渲染队列可能暂时为空；以入口节点的终态为完成标志。每次手动点击运行会创建新任务，运行中禁止重复提交。刷新可恢复已保存工作流的 job_id 进度；重启服务器会中止未完成任务，需要重新运行。重启脚本只会停止 PID 与启动目录都匹配的本项目实例，并拒绝中断非空队列或正在运行的闭环。

任务状态保存在 `runtime/director-jobs/<id>/state.json`，完整运行仍保存在 `runs/live/<id>/`。预览接口只能读取对应运行目录内的 PNG，不允许任意文件路径。

## 独立视觉模型：智谱 GLM-4.6V

已完成真实独立运行：[案例报告](samples/live/jadore-20261001/REPORT.md)。开启推理的运行 V1 为 84 分但未通过，模型修改接触阴影后 V2 为 89 分并 PASS；完整 API 调用记录随样例保存。另保留三轮 NEEDS_REVIEW 和格式中止记录。这是单商品单方向验证，尚未实现四方向自动竞争。

配置示例：`config.zhipu.example.json`。通过 [智谱官方 Chat Completions 接口](https://docs.bigmodel.cn/api-reference/模型-api/对话补全) 发送多张图片，Director 收到商品图和 3 张参考，Critic 收到成品、原商品图和同样的 3 张参考。图片会发送到 `open.bigmodel.cn`，并产生账号对应的 API 用量。

```powershell
Copy-Item config.zhipu.example.json config.local.json
$env:ZHIPU_API_KEY = '你的智谱 API key'
.\start_comfy.ps1
python poster.py run --config config.local.json --product assets/products/dior-jadore-retailer.png --brief "为 Dior J’adore 做一张高级品牌展示海报，标题 J’ADORE，品牌 DIOR，副标题 EAU DE PARFUM，无价格、新品或促销声明。"
```

密钥只从环境变量读取，不写入配置、日志或仓库。此示例开启 `thinking`，最多输出 8192 tokens，每次调用超时 240 秒。其他兼容接口可替换 URL、模型和环境变量名，`vision_options` 只允许推理/采样选项，不能覆盖 messages、model 或鉴权。

每次真实运行保存在 `runs/live/<id>/`。`Director-call.json` 和各版 `Critic-call.json` 保存实际返回的模型名、响应 ID、图片哈希、用量、耗时及结构化输出；不保存密钥或请求图片的 base64。单层 `answer` 包装可解包，但仍须通过原有 Spec/Critic 校验；截断响应会拒绝。`result.json` 保存版本、成品哈希和 `standalone_vision_api_used`。对比图工具只读取结果，不改写来源或评审结论：

```powershell
python build_review.py runs/live/<id>
```

Critic 额外收到合成器实际计算的商品边界、瓶底 y 和文字边界，辅助它提出具体坐标修改。这些几何数据不会自动替它作出审美判断。模型的 PASS 是模型评审结果，不是商业质量保证；失败或三轮未通过仍需人工复核。

## 接入真实视觉模型

```powershell
Copy-Item config.example.json config.json
$env:VISION_API_KEY = '你的 API key'
```

在 `config.json` 设置 `vision_model` 和 `vision_base_url`，需要支持图片输入和 JSON object 输出的 Chat Completions 接口。密钥只从环境变量读取。配置中的字体是 Windows 微软雅黑，可替换为本机合法可用的字体文件。

将自己认可的真实商业作品放入 `references/luxury/`，目标 20 张，至少 3 张，支持 PNG/JPEG/WebP。保留来源和选择理由到 `references/sources.md`。程序不会自动搜图，不会把生成的示意图伪装成优秀参考。

```powershell
python poster.py index --config config.json
```

逐张分析保存到 `kb/luxury.json`。v0.1 按香水适配分排序，取前 3 张供 Director/Critic 使用；暂不实现语义检索。重新 index 会重新分析，产生模型 API 费用。

## 安装 ComfyUI 合成节点

推荐使用 `start_comfy.ps1` 安装并启动；它会复制所有节点文件、前端扩展和本机 project.json。手动安装需复制 `comfy_node/` 的内容，加上根目录的 `poster.py`、`reference_store.py`、`check_background.py`，并创建 `project.json`（内容为 `{"project_root":"项目绝对路径"}`）。布局为：

```text
custom_nodes/perfume_director/
  __init__.py
  poster.py
  reference_store.py
  check_background.py
  jobs.py
  project.json
  web/director.js
```

ComfyUI 的 Python 环境需要 Pillow（以及 ComfyUI 已使用的 numpy/torch）。重启 ComfyUI 后，节点名为 `PerfumePosterSpecRender`。项目附带 `workflows/composite.api.json`，这是 API 格式，由 CLI 提交。

合成器按照 Spec 绘制背景、商品透明蒙版投影或接触阴影、商品、装饰线、Logo 文字、标题、副标题、价格。商品图保持原样，不重新生成商品。v0.1 需要你提供**已经抠好的透明 PNG**，尚未接入自动抠图。Logo 暂时是文字，尚不支持图形 Logo。

```powershell
python poster.py run --config config.json --product assets/perfume.png --brief '给这个香水做一张高级新品海报'
```

默认纯色背景，足以验证控制和真实 Critic 链路。也可以通过 `--background assets/background.png` 使用已准备的背景。设置 `background_workflow` 时，以 AI workflow 为准。

## 接入现有 Qwen 背景 workflow

从 ComfyUI 导出 **API 格式** workflow，保存到 `workflows/background.api.json`。不要把画布 UI 格式 JSON 当作 API JSON。按实际节点 ID 配置下列字段，节点编号示例仅说明格式：

```json
{
  "background_workflow": "workflows/background.api.json",
  "background_bindings": {
    "prompt": {"node": "6", "input": "text"},
    "seed": {"node": "3", "input": "seed"},
    "width": {"node": "5", "input": "width"},
    "height": {"node": "5", "input": "height"}
  },
  "background_output_node": "9"
}
```

合并这些字段到完整 `config.json`。从项目目录启动命令，使相对 workflow 路径正确。输出节点必须返回保存图片信息，例如 SaveImage；一旦背景配置错误会直接报错，不会偷偷用纯色图替代。背景 prompt 不应包含文字和商品，最终位置、文字和商品大小由 Spec 合成节点执行。

`lighting`、`palette` 是 Director 的设计意图；目前灯光须体现在 `background.prompt` 中，合成节点不会重打商品灯光。这里尚未包含 Qwen 模型文件和可直接运行的 Qwen 背景 workflow，需要以你实际安装的模型/节点为准。

## Spec 和 Critic 协议

完整模板见 `examples/PosterSpec.json`。坐标以像素为单位；商品 `x/y` 为中心、`width/height` 为忽略透明留边、保持纵横比的容纳框；文字 `x/y` 为左上角。层顺序由 `layers` 显式控制，背景必须最先、阴影必须先于商品。超出画布的商品框和文字会被拒绝。

Critic 返回 `pass`、0–100 的 `score`、`problems` 和 `changes`。修改只允许白名单字段和 `set/add/multiply`，不执行模型生成的代码。修改一次性验证，越界/非法修改直接报错，保留已产生的版本，不静默截断参数。例子：

```json
{"pass": false, "score": 72, "problems": [{"type":"typography","problem":"标题权重太高"}], "changes": [{"path":"title.size","op":"multiply","value":0.82}]}
```

种子固定，背景 prompt 修改时才增加 revision，背景首次种子为 base seed + revision；质量重试使用明确记录的 seed offset。独立视觉评审 PASS 必须七项均不低于 80、均分至少 85，且没有待处理问题/修改。最多 **3 次渲染，包括第一版**；未通过时选择最高评分版并标记 `NEEDS_REVIEW`，不会强行宣布成功。模型分数是自评，尚未经过人工标定。

每次运行保存 request、各版 PosterSpec、poster.png、Critic、最终 result。超时后 ComfyUI 任务可能还在队列中，程序不自动打断其他任务。成功案例暂只留档，尚不训练或统计 Style DNA。

## 验证

```powershell
python -m unittest discover -s tests -v
```

18 项测试覆盖后台调度非阻塞、重复提交保护、重启状态恢复、预览路径边界，以及多图请求、视觉调用留档、截断拒绝、answer 包装兼容、几何辅助及非法修改拒绝、修改原子性、背景 revision、PASS 约束、提前停止、三轮上限和最佳版本选择。真实 ComfyUI + 商品原图的对话引导三轮案例已随仓库保存；独立视觉 API 的自动 Director/Critic 已新增一个两轮 PASS 案例和一个三轮 NEEDS_REVIEW 案例，详见 samples/live。

协议参考：[ComfyUI server routes](https://docs.comfy.org/development/comfyui-server/comms_routes)、[Chat Completions API](https://developers.openai.com/api/reference/resources/chat)。

### 审美评审修正（2026-10-01）

旧案例两轮只修改阴影位置，75→86 分不能证明设计已达到商业水平；模型 PASS 仅是模型判断。新版 Critic 对商品保真、构图、字体、背景、物理融合、参考质量差距、创意一致性七项分别评分；程序使用七项平均值作为总分，平均至少 85 且每项至少 80、无未解决问题才能 PASS。保留模型原总分为 reported_score。缺少维度或非法评分会拒绝，不补造评分。Director 默认强调商品主视觉、克制背景和文字关系。阈值仍不能代替人的最终审美判断。

重做样例：[暖白 J’adore 海报与真实评审记录](samples/rework/jadore-20261001/REPORT.md)。这是 Codex 指导的重做，状态为 NEEDS_REVIEW，不能宣称独立 Director 已成功。后续评审附上一版和真实文字/商品重叠计算；非法修改保留最后有效海报。当前共 21 项测试通过。

### 每次四个独立风格

ComfyUI 中每次运行 `PerfumeDirectorLoop` 默认依次生成黑金奢华、奶油极简、酒红编辑风、清新植物风。四个方向分别规划构图、字体、材质、灯光，并独立执行 Director→ComfyUI→Critic，每方向最多 3 轮，不是共享图片换颜色。实际风格差异仍需看结果验收。商品与用户批准的文案保持一致，风格偏好由四方向要求覆盖。每方向使用不同 seed offset。

节点以 2×2 卡片显示各方向的成品、分数和 PASS/NEEDS_REVIEW；点击图片打开对应文件。`COMPLETED` 表示四个方向已跑完，不代表全部通过审美评审。一个方向失败继续其余方向，部分失败为 `PARTIAL`，全失败为 `ERROR`。批次记录保存到 `runs/batches/`，每个方向各自保留原始运行目录。旧工作流刷新即可使用新版节点，或重新导入 `workflows/director-loop.ui.json` 获得更大的四图面板。

CLI 同样支持：
```powershell
python poster.py four --config config.local.json --product assets/products/dior-jadore-retailer.png --brief "四种风格的香水品牌海报，无价格或促销声明"
```

四方向串行使用同一台 ComfyUI，耗时和 API 用量比单方向增加；仍只允许一个批次运行。配置可用 `max_rounds: 1..3` 控制各方向轮数，默认 3；没有配置则无需修改。Director 输出非法 Spec 时只允许一次带错误信息的模型修复，仍非法则该方向失败，保留记录，不伪造成功。

四个方向使用人工整理的不同起始网格供 Director 细化，而非四次重复同一个示例；最终仍以实际海报检查风格与完成度。当前 25 项测试通过。

最新全自动实跑：[四方向自动任务原图、原始评审和失败记录](samples/automatic-four/jadore-20261001/REPORT.md)。通过真实 ComfyUI 节点提交，无人工改 Spec 或成品。四个方向都有生成图，批次最终为 PARTIAL，未产生有效 PASS；黑金评审自相矛盾、奶油 V2 评审断连，酒红和植物未通过。该案例不能用来证明稳定商业设计质量。


### 稳定性保护

- 临时断连、超时、429 和 5xx 最多重试三次，401 等配置错误立即停止。每次请求记录耗时、返回模型、用量和尝试记录，不记录密钥。
- 矛盾的 PASS（仍有问题或修改）保守降为未通过；缺失评审维度会要求模型重新看图一次，仍无有效评审则保留海报并标记未评审，不补造分数。
- 四方向先检查实际商品、文字与安全边距；不安全的初始布局恢复该方向安全网格并保存原始/执行 Spec。Critic 危险修改保持原子拒绝，并最多要求一次安全修复。
- AI 背景检查常量图、白边与方向色系。失败最多重新生成两次；仍失败采用显式标记的程序备用背景，禁止因此记为 PASS。此检查只防明显错误，不判断商业审美。
- 文字与实际背景的平均对比度不足时，Director 执行前调整字色，保存修改记录；不改文案和商品。背景本身与商品的光线融合仍需要看图验收。

默认智谱示例使用 GLM-4.6V、关闭深度思考、低随机性与 1280 像素多图输入。可在 config.local.json 调整；运行后仍须检查四张图，COMPLETED 不等于商业质量通过。Background-audit.json 标明生成尝试、备用背景和文字调整；Layout-preflight.json 保存初始布局保护记录。
