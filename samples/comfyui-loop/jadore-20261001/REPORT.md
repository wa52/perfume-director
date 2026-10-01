# ComfyUI 界面完整闭环实测

在 ComfyUI 界面通过 Ctrl+O 导入 director-loop.ui.json，使用 LoadImage 上传已授权的 J’adore 透明 PNG，连接 IMAGE/MASK，点击运行。入口节点在 0.13 秒内提交后台任务并释放队列，后台独立视觉 API + 本地 ComfyUI 完成两轮。没有使用 CLI 启动这次任务，也没有手工改 Spec 或 Critic。

- V1：75 分，不通过；模型提出 shadow.offset_y 从 26 改为 0。
- V2：86 分，模型 PASS；界面出现选中版本、分数和最终海报链接。
- 已验证：模型收到 4/5 张输入图，返回记录真实存在；V1 patch 应用后精确等于 V2 Spec；成品 SHA-256 相符；ComfyUI 队列正常继续执行，没有自等待死锁。

[结果](result.json)，[V1 Critic](v1/Critic.json)，[V2 Critic](v2/Critic.json)。商品 product.png 是 LoadImage 的 IMAGE/MASK 恢复成 RGBA 后保存的输入。原 request 中保留原始 runtime 输入路径，仓库内另存副本供复现。

本次模型 PASS 不是商业画质保证。此测试验证 ComfyUI 入口和独立调度，并未实现四方向竞争、同步 IMAGE 输出或视频。图片通过已获授权的智谱 API 读取。

```powershell
python guided_render.py --spec samples/comfyui-loop/jadore-20261001/v2/PosterSpec.json --product samples/comfyui-loop/jadore-20261001/product.png --background samples/comfyui-loop/jadore-20261001/v2/background.png --output runs/reproduce/comfy-loop.png
```
