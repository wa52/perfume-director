# 接触阴影对照

同一腕表原图、同一PosterSpec和同一ComfyUI背景，只替换接触阴影绘制规则。原规则使用较宽的底部轮廓带，并将环境阴影的width_scale同时用于深色核心，因此出现画线般的突出黑边；新规则从实际轮廓最底两行取接触宽度，外围柔和阴影仍可单独加宽。

`comparison.jpg` 为同位置原尺寸局部对比，`before.jpg` / `after.jpg` 为完整海报。来源及Spec/背景SHA见evidence.json。未再次调用视觉评审，不是自动闭环的新版本，也不宣称商业PASS。
