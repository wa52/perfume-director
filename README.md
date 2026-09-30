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

修改 `extra_model_paths.local.yaml` 中的插件路径；用 `start_comfy.ps1 -ComfyRoot <ComfyUI目录> -ModelsRoot <模型目录>` 指定本机路径。独立 Director/Critic 需要另外配置视觉模型；当前样例由 Codex 在对话里担任 Director/Critic。

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

首次真实运行已完成，见 `runs/guided/jadore-20260930/`：商品原图 + 真实 ComfyUI 背景/合成 + Codex 逐版看图修改，共 3 版。打开 `comparison.png` 比较，最终选 v3；这次是对话引导模式，不是独立视觉 API 自动循环。

本机启动入口：`./start_comfy.ps1`，API 为 `http://127.0.0.1:8190`。它复用现有 ComfyUI (1) Python/GGUF 插件和共享模型，运行输出保存在项目 `runtime/`。脚本含本机路径，换机器需修改参数和 `extra_model_paths.local.yaml`。

```powershell
.\start_comfy.ps1
python guided_render.py --spec runs/guided/jadore-20260930/v3/PosterSpec.json --output runs/reproduce/poster.png --background runs/guided/jadore-20260930/v1/background.png
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

将 `comfy_node/__init__.py` 和项目根目录的 `poster.py` 复制到你的 ComfyUI 实际 `custom_nodes/perfume_director/` 目录，布局为：

```text
custom_nodes/perfume_director/
  __init__.py
  poster.py
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

种子固定，背景 prompt 修改时才增加 revision，背景种子为 base seed + revision。PASS 必须分数至少 80 且没有待处理问题/修改。最多 **3 次渲染，包括第一版**；未通过时选择最高评分版并标记 `NEEDS_REVIEW`，不会强行宣布成功。模型分数是自评，尚未经过人工标定。

每次运行保存 request、各版 PosterSpec、poster.png、Critic、最终 result。超时后 ComfyUI 任务可能还在队列中，程序不自动打断其他任务。成功案例暂只留档，尚不训练或统计 Style DNA。

## 验证

```powershell
python -m unittest discover -s tests -v
```

测试覆盖非法修改拒绝、修改原子性、背景 revision、PASS 约束、提前停止、三轮上限和最佳版本选择。真实视觉模型、真实 ComfyUI 和商品图需要完成一次实际运行后，才能验证画面是否改善。

协议参考：[ComfyUI server routes](https://docs.comfy.org/development/comfyui-server/comms_routes)、[Chat Completions API](https://developers.openai.com/api/reference/resources/chat)。
