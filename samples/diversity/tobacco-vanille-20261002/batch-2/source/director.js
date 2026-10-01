import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const stages = { QUEUED: "准备中", CONCEPTS: "艺术总监正在探索四个新概念", DIRECTOR: "Director 正在准备独立方案", RENDER: "ComfyUI 正在渲染", CRITIC: "Critic 正在审阅", DIRECTION_FINISHED: "一个方向已完成", FINISHED: "完成", FAILED: "已停止" };
const statusLabels = {RUNNING:"生成中", COMPLETED:"四方向已完成，待选稿", PARTIAL:"部分方向未完成", PASS:"模型通过", NEEDS_REVIEW:"待人工确认", ERROR:"失败"};
const terminal = new Set(["PASS", "NEEDS_REVIEW", "ERROR", "COMPLETED", "PARTIAL"]);

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
            notice.textContent = "每次探索 4 个新概念 · 自由构图与材质 · 自动评审，未达标保留最佳版本";
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
            const gallery = document.createElement("div");
            gallery.style.cssText = "display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px";
            panel.append(notice, status, gallery, image, link);
            this.addDOMWidget("director_progress", "director_progress", panel, { serialize: false,
                getMinHeight: () => 640, getMaxHeight: () => 640 });
            this.setSize([520, 900]);
            this._directorGallery = gallery;
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
                    const lines = [`${stages[state.stage] || state.stage}${state.version ? ` · V${state.version}` : ""}`, `模式/模型：${state.mode === "codex_guided_style_redesign" ? "Codex 指导重做" : state.vision_model}`, `状态：${statusLabels[state.status] || state.status}`];
                    if (state.direction_index) lines.push(`方向 ${state.direction_index}/${state.direction_count}：${state.direction_name}`);
                    if (state.selected) lines.push(`选中 V${state.selected.version} · 模型评分 ${state.selected.score}/100`);
                    if (state.run_dir) lines.push(`记录：${state.run_dir}`);
                    if (state.error) lines.push(`错误：${state.error}。查看服务器日志与已保存记录。`);
                    status.textContent = lines.join("\n");
                    const galleryKey = JSON.stringify(state.directions || []);
                    if (this._galleryKey !== galleryKey) {
                        this._galleryKey = galleryKey;
                        gallery.replaceChildren();
                        for (const direction of state.directions || []) {
                            const card = document.createElement("div");
                            const label = document.createElement("div");
                            label.textContent = `${direction.name} · ${statusLabels[direction.status] || direction.status}${typeof direction.selected?.score === "number" ? ` · ${direction.selected.score}分` : ""}`;
                            label.style.cssText = "line-height:1.5;margin-bottom:5px";
                            card.append(label);
                            if (direction.selected?.review_error) label.textContent += ' · 评审中断，图片已保留';
                            if (direction.selected) {
                                const url = api.apiURL(`/perfume-director/jobs/${encodeURIComponent(id)}/preview?direction=${encodeURIComponent(direction.id)}`);
                                const anchor = document.createElement("a");
                                anchor.href = url; anchor.target = "_blank";
                                const thumbnail = document.createElement("img");
                                thumbnail.src = url; thumbnail.alt = direction.name;
                                thumbnail.style.cssText = "width:100%;height:170px;object-fit:contain";
                                anchor.append(thumbnail); card.append(anchor);
                            } else {
                                const error = document.createElement("div");
                                error.textContent = `该方向未完成：${direction.error || "等待中"}`;
                                card.append(error);
                            }
                            gallery.append(card);
                        }
                    }
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
                this._directorGallery.replaceChildren();
                this._galleryKey = null;
                this._directorImage.style.display = "none";
                this._directorLink.style.display = "none";
                this._watchDirector(message.perfume_job[0]);
            }
        };
        const originalConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            originalConfigure?.apply(this, arguments);
            this.setSize([Math.max(this.size[0], 520), Math.max(this.size[1], 900)]);
            if (this.properties?.perfume_job_id) this._watchDirector?.(this.properties.perfume_job_id);
        };
        const originalRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            clearTimeout(this._directorTimer);
            originalRemoved?.apply(this, arguments);
        };
    }
});
