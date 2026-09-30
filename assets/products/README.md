# 首次闭环测试商品

选择：Dior J'adore Eau de Parfum 单瓶商品图。

- 文件：`dior-jadore-retailer.png`
- 来源：[Mondo Parfum 商品页](https://mondo-parfum.de/Dior-J-adore-Eau-de-Parfum-100-ml/SW10238.2)
- 尺寸：1000 × 1250，RGBA PNG
- 已核验：透明通道范围 0–255，四角透明，商品边界框为 `(290,16,710,1236)`；已实际看图，单瓶、无包装盒、无额外广告文案。
- 下载原文件未经生成或修改，SHA-256 与来源记录见 `sources.json`。
- 瓶型为下载图片中的版本；参考库历史广告可能采用不同瓶型，生成时以本商品图为准。
- 适合先测试暖金色、深色背景的高级香水海报。

视觉 API 配置和 ComfyUI 节点就绪后，从项目根目录运行：

```powershell
python poster.py run --config config.json --product assets/products/dior-jadore-retailer.png --brief '为图中的香水设计一张高级品牌展示海报，保留瓶身、标签和商品身份，暖金色与深色背景，文字克制，不添加价格、促销或新品声明'
```

原图含透明留边；renderer 合成时自动忽略留边，以可见商品边界按纵横比放入商品容纳框，原文件不变。参考图只借鉴设计语言，不改变此瓶型。

版权属于原权利人，未核实商业复用授权；此处作为项目流程测试输入。
