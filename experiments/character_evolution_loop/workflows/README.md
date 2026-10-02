# Character ComfyUI workflow

人物生成层不绑定具体模型。它读取 ComfyUI 导出的 **API format JSON**，只修改明确配置的 prompt 和 seed。

## 最快接入

仓库提供一个只使用 ComfyUI 标准节点的示例：

```text
workflows/character_portrait.api.example.json
```

复制为本地文件：

```text
workflows/character_portrait.api.json
```

然后把里面的：

```text
YOUR_CHECKPOINT.safetensors
```

改成你本机实际存在的 checkpoint。也可以完全换成你自己的 Qwen-Image / Flux / SDXL / LoRA / ControlNet 工作流，只要最终导出 API JSON。

## 节点映射

在 `config/character_v01.local.json` 中填写：

- `prompt_node`：正向文本 prompt 输入节点
- `prompt_input`：通常是 `text`
- `seed_node`：随机种子所在节点；没有独立 seed 时可设为 null
- `seed_input`：通常是 `seed` 或 `noise_seed`
- `output_node`：最终 SaveImage / PreviewImage 输出节点

示例 workflow 对应：

```json
{
  "prompt_node": "6",
  "prompt_input": "text",
  "seed_node": "3",
  "seed_input": "seed",
  "output_node": "9"
}
```

适配器不会猜测或修改 checkpoint、sampler、LoRA、ControlNet、自定义节点等其他参数。

## 为什么这样设计

Character Evolution Loop 只负责人物收敛逻辑：

```text
Canon/State
   ↓
Generation Prompt
   ↓
ComfyUI workflow
   ↓
8 candidates
   ↓
Vision Critic
   ↓
A / B / C
   ↓
Revision Patch
   ↓
V02
```

所以以后换生图模型，只换 workflow/config，不需要重写 Director、Critic、Memory 或 Canon。
