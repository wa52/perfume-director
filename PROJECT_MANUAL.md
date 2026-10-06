# Product Art Director / perfume-director 详细项目说明书

> 仓库：`wa52/perfume-director`  
> 基线：main @ `3fdee64dd914e7da535ecf118b1f1280ddc32d19`  
> 项目定位：面向商品广告图与商业海报的 AI Art Director + ComfyUI 自动闭环  
> 本说明书依据当前 README、QUALITY_ALIGNMENT、COMMERCIAL_V2、工作流、参考库、测试与样例记录整理。

## 1. 项目目标

本项目的核心不是“调用一次生图模型生成一张海报”，而是建立一个可重复、可审核、可回退的商品广告创作闭环。

系统把商业视觉工作拆成多个相互制约的阶段：

```text
商品原图 / Brief
  -> 参考库检索与视觉分析
  -> Creative Director 生成多个广告概念
  -> 独立概念审核
  -> 文案生成与文案审核
  -> Art Director 输出 PosterSpec
  -> ComfyUI 生成背景 / 场景
  -> 2D 确定性商品合成
  -> Critic 看实际成品
  -> Commercial Gate
  -> 自动修复 / 重绘
  -> Final Independent Art Review
  -> PASS / NEEDS_REVIEW
```

项目当前已经从“香水海报”扩展到多品类商品，并把“程序测试通过”和“视觉商业质量通过”严格分开。

## 2. 支持范围

当前仓库覆盖的代表性商品类别包括：

- 香水
- 护肤 / 美妆
- 腕表 / 珠宝方向
- 鞋履
- 饮品
- 男装
- 女装

不同类别不强行使用同一套几何规则。比如横向鞋履不按高瓶比例验收，平铺腕表不强制竖立，悬挂服装也不会被要求出现虚构地面投影。

仓库内还维护多个服装子类型输入和工作流，以支持更细分的男装、女装结构。

## 3. 设计原则

### 3.1 商品真实性优先

商品主体不是重新生成，而是尽量保留原始商品 RGB、透明 Alpha、Logo、标签和轮廓。这样可以降低生成模型修改品牌文字、包装比例或瓶型的风险。

当前主流程要求透明商品 PNG；商品本身主要由确定性 2D 合成器处理，AI 负责背景、场景、创意和视觉判断。

### 3.2 生成与审核分离

Director 负责提出方案，Critic 和 Final Reviewer 负责否决。高分不能覆盖硬性失败项。

项目已经明确取消“模型给了一个高总分就算商业通过”的做法。商业 Gate 要求每个检查项都具有明确布尔结果和视觉证据。

### 3.3 参考驱动而不是纯 Prompt 驱动

仓库包含真实商业视觉参考、来源、哈希、逐图分析和 SQLite Design KB。

香水部分保留 100 张参考，并按不同设计语言、构图、光线、排版等建立结构化信息。多类别也有独立参考集合。参考不是简单拿来拼贴，而是用于 Director 和 Reviewer 学习设计语言、结构关系和视觉标准。

### 3.4 保留失败证据

项目不会为了“看起来成功”而覆盖失败记录。真实运行中出现的 403、格式错误、配色重复、几何碰撞、标签漂移、融合失败、Commercial Gate FAIL 等都会保留在样例和报告中。

这使项目更接近工程系统，而不是仅展示成功图片的 Demo。

## 4. 主要模块

### 4.1 `poster.py`

主流程入口。负责运行 Director、选择参考、生成 PosterSpec、调用渲染、调用 Critic、保存版本和结果。

### 4.2 `reference_store.py`

参考图与 Design KB 管理。负责参考图片、来源、结构化分析、分类关联和检索所需数据。

### 4.3 `concepts.py`

负责 Creative Concept 层。目标是在真正进入版式与坐标之前先决定广告主张和视觉概念，降低“四张图只是换颜色/换位置”的伪多样性。

### 4.4 `campaign_copy.py`

负责不同创意方向的广告文案生成与独立审核。用户明确锁定的文字不会被自动改写。

### 4.5 `commercial.py` / `commercial_pilot.py`

Commercial V2 的核心。负责更严格的品牌、物理融合、排版、构图、创意一致性和最终商业审稿。

### 4.6 `quality.py`

质量规则与验收逻辑。

### 4.7 `harmonization.py` / `optimize_2d.py`

2D 融合与受控优化实验，包括线性光合成、源纹理光照、边缘修复、接触阴影、反光保护等。

### 4.8 `relighting.py` / `relight_pilot.py`

材质 / 重新布光实验分支。当前属于研究性能力，还没有自动替代主流程。

### 4.9 `categories.py`

不同商品类别的约束、行为和验收规则。

### 4.10 `comfy_node/`

ComfyUI 自定义节点与前端扩展。将完整 Director Loop 暴露到 ComfyUI UI 中。

### 4.11 `workflows/`

ComfyUI API / UI 工作流。包括完整 Director 入口工作流以及背景、合成、融合、实验性 relighting 等组件。

## 5. Design KB 与参考系统

### 5.1 数据内容

`kb/design_kb.sqlite3` 保存参考图片及其元数据，包括：

- 图片原始字节
- SHA-256
- 尺寸
- 来源网页
- 图片链接
- 类型
- 入选理由
- 结构化视觉分析

参考图同时保留文件形式，方便视觉复核。

### 5.2 参考选择

Director 不固定永远使用同几张参考。当前选择逻辑会考虑：

- 质量
- 渲染适配性
- 构图差异
- 字体 / 排版差异
- 光线差异
- 品牌来源分散
- 最近使用频率

同一批方向会尽量选择不同品牌与不同视觉结构的参考。

### 5.3 版权边界

参考图版权属于原权利人。仓库保留来源记录，但不能把参考作品直接当作可商业复用资产。它们主要用于研究视觉语言和建立审美标准。

## 6. Creative Director 层

项目后期把“创意”和“版式坐标”拆开。

先让视觉模型生成广告 proposition，再由独立 semantic reviewer 判断：

- 四个方向是否真的不同；
- 是否只是换色、换种子或换标题位置；
- 是否存在无法通过现有渲染器执行的创意；
- 是否违反商品类别和品牌事实；
- 是否产生虚构功效、虚构品牌陈述。

只有通过概念审核的方向才进入 Art Director 布局阶段。

如果概念审核失败，会允许有限次数修复；如果多次仍失败，可以保留为 held draft 诊断，但不能因为后续图片分数高就跳过这层否决。

## 7. 文案系统

每个方向可以生成独立广告文案。

文案审核重点包括：

- 品牌和商品名拼写
- 用户锁定文字不可被改写
- 不虚构价格、促销、新品、功效
- 标题 / 副标题长度满足实际渲染器限制
- 文案与当前创意 proposition 匹配
- 不把布局解释文字直接放到消费者海报上

语言默认跟随用户 Brief。

## 8. PosterSpec

Art Director 最终不是直接返回一张图片，而是输出结构化 PosterSpec。

PosterSpec 描述：

- 背景场景
- 商品位置与尺寸
- 标题
- 副标题
- Logo / 品牌文字
- 字体
- 字距
- 行距
- 对齐方式
- 装饰元素
- 阴影
- 文字安全区
- 商品与文字关系

这种设计让 Critic 可以提出结构化修复，而不是只能“再生成一次”。

## 9. ComfyUI 渲染

### 9.1 主职责

ComfyUI 主要负责：

- AI 背景 / 场景生成
- 工作流节点执行
- 与 ProductDirectorLoop 协调

商品主体仍尽量使用原图。

### 9.2 运行端口

仓库当前示例主要使用：

```text
http://127.0.0.1:8190
http://127.0.0.1:8191
```

具体使用哪个端口取决于启动脚本与配置。

### 9.3 工作流入口

完整 ComfyUI 闭环通常只需要：

```text
LoadImage（透明商品 PNG）
    ->
AI Art Director Loop（brief）
```

点击一次运行后，后台继续执行 Director、Render、Critic 和 Commercial Gate。

入口返回 job_id，以避免在 ComfyUI 单任务队列中同步等待自身渲染而形成死锁。

## 10. 2D 确定性合成

系统不让背景模型重新绘制商品。

2D compositor 负责：

- 透明商品图裁掉无效透明边
- 保持宽高比缩放
- 商品平移
- 商品 Alpha 合成
- 接触阴影
- 有条件的地面投影
- 文字
- 装饰线
- Logo 文字
- 安全区域检查

Commercial V2 会根据源图光线方向决定是否允许方向性投影。如果光线无法可靠判断，则禁用方向性阴影，而不是猜测。

当前这仍是 2D 近似，并不等于真实 3D 重光照。

## 11. Critic 与自动修改

Critic 会看到：

- 最终成品
- 原始商品图
- 当前参考图
- 商品实际边界
- 瓶底 / 接触位置
- 文字边界
- 当前 PosterSpec

它不仅给分，还要求输出：

- 根因
- 影响层
- 修改策略
- 是否存在硬性否决问题

允许的自动修复动作受到白名单约束，例如：

- 场景 prompt
- layout
- typography
- contact shadow
- bounded cast shadow

无法安全修复的材质重光照不会被伪装成“已经完成”。

## 12. Commercial Gate

当前统一最低阈值：

- Product Fidelity >= 95
- Physical Integration >= 88
- Typography >= 88
- Composition >= 88
- Brand Alignment >= 85
- Creative Coherence >= 88

同时需要通过证据型硬检查，包括：

- Logo
- 商品形状
- 是否正确落地 / 接触
- 边缘是否干净
- 光线是否一致
- 文字是否越界
- 文字是否碰撞
- 字体
- 品牌拼写
- 商品是否被裁断
- 其他显式商业检查

任何关键项为 false、证据为空、存在未解决 critique、存在危险几何，都可以直接否决。

因此“平均分很高”不能覆盖硬失败项。

## 13. Final Independent Art Review

Commercial Gate 后还有独立 Final Art Director。

它不继承前一个 Critic 的数值结论，而是重新看实际图片、商品原图和参考，判断作品属于：

- draft
- social_ad
- campaign_candidate

默认目标是 `campaign_candidate`。

如果最终 Reviewer 认为只是 generic draft，即使前面的数字 Gate 通过，最终仍不能释放为商业候选。

## 14. 多版本与迭代预算

每个创意方向可以配置 1～12 版等不同预算。

系统流程：

```text
V1
 -> Critic
 -> FAIL
 -> 结构化修复
 -> V2
 -> Critic
 -> ...
 -> PASS 或预算耗尽
```

预算耗尽仍未达标时，结果必须保留为 `NEEDS_REVIEW`，不能自动降标准。

## 15. 安装

建议 Python 3.10+。

安装项目依赖：

```powershell
python -m pip install -r requirements.txt
```

如果需要参考采集 / 研究工具：

```powershell
python -m pip install -r requirements-research.txt
```

准备本地配置：

```powershell
Copy-Item config.comfy.example.json config.local.json
Copy-Item extra_model_paths.example.yaml extra_model_paths.local.yaml
```

需要修改 ComfyUI、模型、插件和字体路径。

API Key 必须通过环境变量传入，不建议写入配置或仓库。

## 16. 启动 ComfyUI

推荐：

```powershell
.\start_comfy.ps1
```

必要时指定：

```powershell
.\start_comfy.ps1 -ComfyRoot <ComfyUI目录> -ModelsRoot <模型目录>
```

需要更新自定义节点时，可以在安全情况下重启。

脚本会尽量避免在已有队列或 Director 正运行时直接杀掉服务。

## 17. CLI 运行示例

单商品主流程示例：

```powershell
python poster.py run --config config.local.json --product assets/products/dior-jadore-retailer.png --brief "为商品制作高级品牌展示海报"
```

批量商品矩阵：

```powershell
python test_product_matrix.py --tag my-test --rounds 2 --workers 2 --wait-for-100
python matrix_report.py --tag my-test
```

多类别商业资格测试：

```powershell
python run_category_matrix.py --comfy-url http://127.0.0.1:8191 --tag commercial-alignment-qualification-20261004 --manifest assets/products/alignment-products.json --categories perfume watches footwear beverage skincare menswear womenswear
```

## 18. 长时间运行

Windows 下仓库提供后台批量启动脚本：

```powershell
.\start_comfy.ps1
.\launch_matrix.ps1 -Tag my-test -Rounds 2 -Workers 1
```

批次状态保存在项目运行目录中。再次使用同名 tag 可以跳过已完成商品并继续中断批次。

但电脑关机、服务停止或外部 API 不可用仍会中断。

## 19. 测试

仓库已经有大量程序级测试，覆盖：

- 工作流分类
- Job 状态
- PosterSpec
- 多类别规则
- 商业 Gate
- 文案限制
- 参考选择
- 2D 合成
- 节点注册
- API 交互契约
- 运行状态恢复

README 和 QUALITY_ALIGNMENT 中的测试数量会随着提交变化。

需要特别注意：程序测试 PASS 只说明代码行为满足契约，不等于生成图片达到商业水准。

## 20. 当前真实商业质量状态

这是理解仓库最重要的一点。

当前代码层、工作流层和统一 Gate 已经比较完整，但仓库最新质量记录明确没有把所有结果包装成“商业通过”。

已记录的七类别资格测试中：

- 六个类别完成四个选择，共 24 张；
- menswear 在渲染前失败；
- 24 张选择中商业 Gate 通过数为 0；
- 所有工作流节点注册检查已通过；
- 说明系统链路工作，但视觉商业结果仍需要继续提高。

因此当前最准确的项目表述是：

**“商业级广告生成闭环与质量治理系统已经建立，真实多类别运行仍处于商业视觉质量攻关阶段。”**

而不是“已经稳定生成商业级广告”。

## 21. 已知限制

当前主要限制包括：

1. 2D 商品融合不是完整 3D / PBR 重光照；
2. 商品材质区、玻璃透射、反射重建仍有限；
3. 自动 relighting 实验仍存在标签漂移、接缝、阴影等问题；
4. 商品自动抠图不是主流程既有能力，最好提供透明 PNG；
5. 图形 Logo 还没有完全替代文字 Logo 方案；
6. 不同子品类需要对应真实样本验证，不能用口红代表整个护肤品类；
7. 腕表样本不等于珠宝验证；
8. 视觉模型 PASS 仍然是模型判断，不等于人类商业认证；
9. 参考图商业复用权利并未由系统自动解决；
10. API 拒绝、外部服务中断、ComfyUI 状态仍会影响长时间批处理。

## 22. 推荐使用场景

最适合：

- 电商商品主图升级
- 品牌 Social Ad
- 香水 / 美妆 / 饮品等产品视觉探索
- 多创意方向自动生成
- AI 设计 + 审核 + 自动修改研究
- ComfyUI 商品设计自动化
- 建立企业内部的视觉设计 Agent / 工作流

不适合在没有人工复核的情况下直接批量投放高价值品牌广告。

## 23. 后续商业化方向

要真正达到稳定商业交付，优先级应是：

```text
商品身份保护
  -> 更真实的物理融合 / relighting
  -> 排版质量
  -> 品牌一致性
  -> 创意多样性
  -> 多品类稳定性
  -> 人工商业审稿校准
  -> 批量 SLA / 成本 / 失败恢复
```

重点不应继续单纯增加模型或工作流数量，而应提升“真实图片一次通过率”和“失败可自动定位/修复率”。

---

这份说明书描述当前 GitHub 主分支实现。仓库 `README.md`、`QUALITY_ALIGNMENT.md`、`COMMERCIAL_V2.md`、各 `samples/**/REPORT.md` 和真实运行结果仍是项目当前能力与质量状态的最终依据。
