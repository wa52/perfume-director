# Character ComfyUI workflow

把你在 ComfyUI 中测试通过的人物生图工作流导出为 **API format JSON**，保存为：

```
workflows/character_portrait.api.json
```

然后在 `config/character_v01.local.json` 中填写三个节点映射：

- `prompt_node`：正向文本 prompt 输入节点
- `seed_node`：随机种子输入节点；如果工作流没有独立 seed 节点可设为 null
- `output_node`：最终 SaveImage / PreviewImage 输出节点

适配器只修改配置明确指定的 prompt 与 seed，不猜测 checkpoint、sampler、LoRA、ControlNet 或自定义节点。

这样可以替换 Qwen-Image / Flux / SDXL / 其他人物模型而不改 Character Evolution Loop。

> example config 中的节点 ID 只是示例，不代表你的实际 workflow。必须用你导出的 API workflow 中真实节点 ID。
