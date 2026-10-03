# 四类商品海报闭环

入口为 ComfyUI 的 `AI Art Director · 多类别四方向闭环`（ProductDirectorLoop）。四个可导入工作流：

| 文件 | 类别 | 首次测试商品 |
|---|---|---|
| skincare.ui.json | 护肤美妆 | 口红，先验证美妆；护肤罐/泵瓶待追加 |
| watches.ui.json | 腕表珠宝 | 腕表，珠宝待追加 |
| footwear.ui.json | 鞋履 | 运动鞋 |
| beverage.ui.json | 饮品 | 玻璃瓶可乐 |

上传真实透明 PNG，连接同一个 LoadImage 的 IMAGE 和 MASK。类别已经预选，brief 可只描述用途和禁止事项，详细生图提示由 Director 编写。节点返回任务编号，并在节点内显示草稿、进度和四方向选稿；它不是同步 IMAGE 输出节点。不要重复点击运行。

同一个核心引擎按类别使用独立参考池、近期方案记录和评审关注点。新类别不允许自动回退到香水参考或固定香水四模板。鞋履和低矮包装按实际轮廓占幅校验，保留商品拍摄角度与原始标签，不由 AI 重画商品。

运行和未通过审美验收是不同状态：COMPLETED 只表示四方向执行完成；NEEDS_REVIEW 表示预算耗尽仍有问题。PASS 需通过原有七维度门槛与确定性检查，仍须人工审核实际成品。单款示例不能证明整个类别稳定或达到商业交付水平。

参考记录：`references/categories/review.json`、`summary.json` 与 SQLite。仅接纳品牌可确认、类别匹配且模型选图分数至少75的候选；未通过候选及原因保留，图像 SHA 用于去重。原始图片版权属于原权利人，当前用途为设计研究和流程测试。

本机四类别测试服务在 `http://127.0.0.1:8191/`，工作流面板的“商品海报”目录。8190 为另一桌面实例。本项目重新启动时请明确端口：

```powershell
.\start_comfy.ps1 -Port 8191
python run_category_matrix.py --comfy-url http://127.0.0.1:8191 --tag my-categories
```

首次准备参考依赖 requirements-research.txt 和本机已配置的视觉 API：

```powershell
python prepare_category_kb.py
```

批量测试顺序为腕表→鞋履→饮品→美妆，每款规划四方向，并调用真实 Critic 修改。报告保存在 `samples/categories/<tag>/gallery.html`。当前 `categories-policy-20261003` 是正在运行的首轮验证，尚未完成四类验收；不要把该页的进度状态当作最终结论。

首批腕表的评审存在将空价格层误判为信息缺失、误报图形裁切的问题，因此保留草稿后中止并升级策略。新批次显式传递允许文案、故意留空层与每个图形的真实边界，不要求补充未授权价格来模仿参考。过程证据见 `samples/categories/watch-first-iteration/REPORT.md`。
