import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const stages = { QUEUED: "准备中", DIRECTOR: "Director 正在看商品与参考", RENDER: "ComfyUI 正在渲染", CRITIC: "Critic 正在审阅", FINISHED: "完成", FAILED: "已停止" };
const terminal = new Set(["PASS", "NEEDS_REVIEW", "ERROR"]);

app.registerExtension({
    name: "PerfumeDirector.Loop",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "PerfumeDirectorLoop") return;
        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            originalCreated?.apply(this, arguments);
            const panel = document.createElement("div");
            panel.style.cssText = "padding:12px;box-sizing:border-box;color:var(--input-text,#eee);background:var(--comfy-input-bg,#252525);font:13px sans-serif;overflow:auto;height:100%;";
            const notice = document.createElement("div");
            notice.textContent = "运行一次开始闭环 · 最多 3 轮 · 图片发送到已配置的视觉 API";
            notice.style.cssText = "opacity:.7;line-height:1.6;margin-bottom:10px";
            const status = document.createElement("div");
            status.textContent = "上传透明 PNG，连接 IMAGE 与 MASK，填写 brief 后点击运行。";
            status.style.cssText = "white-space:pre-wrap;line-height:1.6";
            const image = document.createElement("img");
            image.style.cssText = "display:none;width:100%;max-height:220px;object-fit:contain;margin-top:10px";
            const link = document.createElement("a");
            link.textContent = "打开最终海报";
            link.target = "_blank";
            link.style.cssText = "display:none;color:#b7d4f0;margin-top:8px";
            panel.append(notice, status, image, link);
            this.addDOMWidget("director_progress", "director_progress", panel, { serialize: false,
                getMinHeight: () => 500, getMaxHeight: () => 500 });
            this.setSize([440, 760]);
            this._directorStatus = status;
            this._directorImage = image;
            this._directorLink = link;
            this._watchDirector = async (id) => {
                clearTimeout(this._directorTimer);
                this.properties ||= {};
                this.properties.perfume_job_id = id;
                try {
                    const response = await api.fetchApi(`/perfume-director/jobs/${encodeURIComponent(id)}`);
                    if (!response.ok) throw new Error("任务不存在或服务已重启，请重新运行。");
                    const state = await response.json();
                    const lines = [`${stages[state.stage] || state.stage}${state.version ? ` · V${state.version}` : ""}`, `模型：${state.vision_model}`, `状态：${state.status}`];
                    if (state.selected) lines.push(`选中 V${state.selected.version} · 模型评分 ${state.selected.score}/100`);
                    if (state.run_dir) lines.push(`记录：${state.run_dir}`);
                    if (state.error) lines.push(`错误：${state.error}。查看服务器日志与已保存记录。`);
                    status.textContent = lines.join("\n");
                    if (state.selected) {
                        const url = api.apiURL(`/perfume-director/jobs/${encodeURIComponent(id)}/preview`);
                        image.src = url;
                        image.style.display = "block";
                        link.href = url;
                        link.style.display = "block";
                    }
                    if (!terminal.has(state.status)) this._directorTimer = setTimeout(() => this._watchDirector(id), 2000);
                } catch (error) {
                    status.textContent = error.message;
                }
            };
        };
        const originalExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            originalExecuted?.apply(this, arguments);
            if (message.perfume_job?.[0]) {
                this._directorImage.style.display = "none";
                this._directorLink.style.display = "none";
                this._watchDirector(message.perfume_job[0]);
            }
        };
        const originalConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            originalConfigure?.apply(this, arguments);
            this.setSize([Math.max(this.size[0], 440), Math.max(this.size[1], 760)]);
            if (this.properties?.perfume_job_id) this._watchDirector?.(this.properties.perfume_job_id);
        };
        const originalRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            clearTimeout(this._directorTimer);
            originalRemoved?.apply(this, arguments);
        };
    }
});
