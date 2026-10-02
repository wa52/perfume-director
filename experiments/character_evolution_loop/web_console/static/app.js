const $ = (s) => document.querySelector(s);

let data = null;
let selected = null;
let characterId = null;
let pollTimer = null;

const labels = {
  canon: "Canon",
  ordinary: "普通感",
  office_worker: "上班族",
  restraint: "克制",
  identity_clarity: "身份清晰",
  overbeautification_control: "去美型化",
  context_fit: "语境匹配",
  character_specificity: "角色辨识",
  design_coherence: "设计一致",
};

const esc = (v) =>
  String(v ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

function toast(t) {
  const e = $("#toast");
  e.textContent = t;
  e.classList.remove("hidden");
  setTimeout(() => e.classList.add("hidden"), 2800);
}

function busy(title, message) {
  $("#busyTitle").textContent = title;
  $("#busyText").textContent = message;
  $("#busy").classList.remove("hidden");
}

function unbusy() {
  $("#busy").classList.add("hidden");
}

async function api(path, opt = {}) {
  const r = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opt,
  });
  const j = await r.json();
  if (!r.ok || j.status === "error") {
    throw new Error(j.message || `HTTP ${r.status}`);
  }
  return j;
}

const query = () =>
  characterId ? `?character_id=${encodeURIComponent(characterId)}` : "";

async function reload() {
  data = await api("/api/dashboard" + query());
  characterId = data.character_id;
  render();
}

function scoreKeys(candidate) {
  const scores = candidate?.scores || {};
  const preferred = ["canon"];
  if ("ordinary" in scores) preferred.push("ordinary");
  else if ("context_fit" in scores) preferred.push("context_fit");
  if ("identity_clarity" in scores) preferred.push("identity_clarity");
  for (const key of Object.keys(scores)) {
    if (!preferred.includes(key) && preferred.length < 3) preferred.push(key);
  }
  return preferred.slice(0, 3);
}

function render() {
  const s = data.state || {};
  const b = data.batch || {};
  const candidates = b.candidates || [];

  $("#versionBadge").textContent = `V${String(data.version || 0).padStart(2, "0")}`;
  $("#roundTitle").textContent = candidates.length
    ? `${data.character} · V${data.version} 候选`
    : `${data.character || "角色"} · 尚未生成`;

  $("#configBadge").textContent = data.config_ready
    ? "配置结构就绪"
    : "配置未就绪";
  $("#configBadge").className = `chip ${data.config_ready ? "ready" : ""}`;

  const job = data.active_job;
  $("#jobBadge").textContent = job ? `${job.kind} · ${job.status}` : "空闲";
  $("#jobBadge").className = `chip ${job ? "working" : "ready"}`;

  renderCharacters();
  $("#characterMeta").innerHTML =
    `<strong>${esc(data.character)}</strong>` +
    (s.identity_anchor ? "已有人类身份锚点" : "尚未人工确认身份");

  renderCanon(s);
  renderArtDirection(data.art_direction);
  renderConfig(data.config_state);
  renderCandidates(candidates);
  renderReview();
  renderTimeline(data.archived_versions || []);
  renderScenes(data.scene_validation || {});
  renderAnchor(s);

  $("#roundStats").innerHTML = [
    ["候选", candidates.length],
    ["A/B/C", (b.shortlist || []).length],
    ["Lock", Object.keys(s.locked || {}).length],
    [
      "Agent建议",
      (b.shortlist || []).filter((x) => x.director_advice).length,
    ],
  ]
    .map((x) => `<span class="metric">${x[0]}<b>${x[1]}</b></span>`)
    .join("");

  $("#emptyState").classList.toggle("hidden", candidates.length > 0);
  $("#candidateGrid").classList.toggle("hidden", candidates.length === 0);

  const blocked = !!data.active_job;
  $("#runBtn").disabled = !data.config_ready || blocked;
  $("#sceneBtn").disabled =
    !data.config_ready ||
    !data.scene_validation_enabled ||
    !s.identity_anchor ||
    blocked;
  $("#characterSelect").disabled = blocked;
}

function renderCharacters() {
  const e = $("#characterSelect");
  const old = e.value;
  e.innerHTML = (data.characters || [])
    .map(
      (x) =>
        `<option value="${esc(x.id)}">${esc(x.name)}${x.has_config ? "" : " · 未配置"}</option>`
    )
    .join("");
  e.value = characterId || old || data.default_character;
}

function renderCanon(s) {
  $("#canonLocks").innerHTML =
    Object.entries(s.locked || {})
      .map(
        ([k, v]) =>
          `<div class="lock"><small>${esc(k)}</small><b>${esc(v)}</b></div>`
      )
      .join("") || "<div class=meta>暂无锁定项</div>";

  $("#evidenceList").innerHTML =
    (data.evidence_groups || [])
      .map(
        (g) =>
          `<details class="evidence"><summary>${esc(g.feature)} · ${(g.refs || []).length} 条</summary>${(g.refs || [])
            .slice(0, 8)
            .map(
              (r) =>
                `<div class="ref"><b>${esc(r.chapter_title || r.chapter_id)}</b><br>${esc(r.chunk_id)} · lines ${esc(r.line_start)}–${esc(r.line_end)}</div>`
            )
            .join("")}</details>`
      )
      .join("") || "<div class=meta>暂无证据锚点</div>";
}

function renderArtDirection(a) {
  if (!a) {
    $("#artDirection").innerHTML =
      '<div class="meta">未配置作品级风格锁</div>';
    return;
  }
  const locks = Object.entries(a.locked_dimensions || {})
    .map(
      ([k, v]) =>
        `<div class="lock"><small>${esc(k)}</small><b>${esc(v)}</b></div>`
    )
    .join("");
  $("#artDirection").innerHTML =
    `<div class="meta"><strong style="font-size:13px">${esc(
      a.name || "Art Direction"
    )}</strong>` +
    (a.prompt_rules || [])
      .slice(0, 3)
      .map((x) => `<div>• ${esc(x)}</div>`)
      .join("") +
    "</div>" +
    locks;
}

function renderConfig(cfg) {
  $("#configDetails").innerHTML = (cfg?.checks || [])
    .map(
      (x) =>
        `<div class="config-check ${x.ok ? "ok" : "bad"}"><b>${
          x.ok ? "✓" : "!"
        } ${esc(x.name)}</b><span>${esc(x.detail)}</span></div>`
    )
    .join("");
}

function renderCandidates(list) {
  $("#candidateGrid").innerHTML = list
    .map((x, i) => {
      const keys = scoreKeys(x);
      return `<article class="card ${
        selected?.image_ref === x.image_ref ? "selected" : ""
      }" data-i="${i}">
        <div class="img">
          ${x.media_url ? `<img src="${esc(x.media_url)}">` : ""}
          <span class="badge rank">#${x.rank || i + 1}</span>
          ${x.label ? `<span class="badge abc">${esc(x.label)}</span>` : ""}
          ${x.director_advice ? '<span class="badge agent">AGENT</span>' : ""}
          ${(x.locked_violations || []).length ? '<span class="badge bad">LOCK 违规</span>' : ""}
        </div>
        <div class="body">
          <div class="card-title">
            <span>${x.label ? `候选 ${esc(x.label)}` : `候选 ${i + 1}`}</span>
            <span class="score">${esc(x.overall ?? "-")}</span>
          </div>
          ${keys
            .map(
              (k) =>
                `<div class="barrow"><span>${esc(labels[k] || k)}</span><div class="bar"><i style="width:${Math.max(
                  0,
                  Math.min(100, x.scores?.[k] || 0)
                )}%"></i></div><b>${esc(x.scores?.[k] ?? "-")}</b></div>`
            )
            .join("")}
        </div>
      </article>`;
    })
    .join("");

  document.querySelectorAll(".card").forEach((e) => {
    e.onclick = () => {
      selected = list[Number(e.dataset.i)];
      renderCandidates(list);
      renderReview();
    };
  });
}

function renderDirectorAdvice(candidate) {
  const box = $("#directorAdvice");
  const status = $("#directorStatus");

  if (!candidate) {
    status.textContent = "等待候选";
    status.className = "chip";
    box.innerHTML = "选择 A/B/C 后显示导演建议。";
    return;
  }

  const a = candidate.director_advice;
  if (!a) {
    status.textContent = candidate.label ? "暂无建议" : "仅 A/B/C";
    status.className = "chip";
    box.innerHTML = candidate.label
      ? "这一候选尚未得到 Director Agent 建议。"
      : "Director Agent 默认只分析 A/B/C，避免对全部 8 张增加不必要调用。";
    return;
  }

  const fallback = !!candidate.director_agent_error;
  status.textContent = fallback ? "规则兜底" : "Agent 已分析";
  status.className = `chip ${fallback ? "" : "ready"}`;

  const strengths = (a.strengths || [])
    .map((x) => `<li>${esc(x)}</li>`)
    .join("");
  const issues = [...(a.priority_issues || [])]
    .sort((x, y) => Number(x.priority || 99) - Number(y.priority || 99))
    .map(
      (x) =>
        `<div class="agent-issue"><b>P${esc(x.priority ?? "-")} · ${esc(
          x.feature || "overall"
        )}</b><span>${esc(x.diagnosis)}</span></div>`
    )
    .join("");
  const changes = [...(a.changes || [])]
    .sort((x, y) => Number(x.priority || 99) - Number(y.priority || 99))
    .map(
      (x, i) =>
        `<div class="agent-change">
          <div><b>${esc(x.feature)}</b> → ${esc(x.target)}</div>
          ${x.why ? `<small>${esc(x.why)}</small>` : ""}
          <button class="use-advice" data-i="${i}">采用此建议</button>
        </div>`
    )
    .join("");
  const keep = (a.keep || []).map((x) => `<span>${esc(x)}</span>`).join("");
  const frozen = (a.do_not_change || [])
    .map((x) => `<span>${esc(x)}</span>`)
    .join("");
  const notes = (a.evidence_notes || [])
    .map((x) => `<li>${esc(x)}</li>`)
    .join("");

  box.innerHTML = `
    ${fallback ? `<div class="agent-warning">LLM Director 调用失败，当前显示规则兜底建议：${esc(candidate.director_agent_error)}</div>` : ""}
    <div class="agent-summary">${esc(a.summary || "已生成下一轮导演建议。")}</div>
    ${strengths ? `<h4>保留优点</h4><ul>${strengths}</ul>` : ""}
    ${issues ? `<h4>优先问题</h4>${issues}` : ""}
    ${changes ? `<h4>下一轮修改</h4>${changes}` : ""}
    ${keep ? `<h4>KEEP</h4><div class="agent-tags keep">${keep}</div>` : ""}
    ${frozen ? `<h4>DO NOT CHANGE</h4><div class="agent-tags frozen">${frozen}</div>` : ""}
    ${a.next_round_goal ? `<h4>下一轮目标</h4><div class="agent-goal">${esc(a.next_round_goal)}</div>` : ""}
    ${notes ? `<h4>证据/人工反馈护栏</h4><ul>${notes}</ul>` : ""}
  `;

  document.querySelectorAll(".use-advice").forEach((button) => {
    button.onclick = (event) => {
      event.stopPropagation();
      const item = (a.changes || [])[Number(button.dataset.i)];
      if (!item) return;
      const feature = String(item.feature || "");
      const select = $("#changeFeature");
      if ([...select.options].some((x) => x.value === feature)) {
        select.value = feature;
      }
      $("#changeTarget").value = String(item.target || "");
      toast("已填入这条 Agent 建议，你可以继续修改");
    };
  });
}

function renderReview() {
  const s = data?.state || {};
  const mods = s.modifiable || [];

  $("#changeFeature").innerHTML =
    '<option value="">不指定</option>' +
    mods.map((x) => `<option value="${esc(x)}">${esc(x)}</option>`).join("");

  $("#lockFeatures").innerHTML = mods
    .map(
      (x) =>
        `<label class="check"><input type="checkbox" value="${esc(
          x
        )}">${esc(x)}</label>`
    )
    .join("");

  const ok = selected?.label && !(selected.locked_violations || []).length;
  $("#confirmChoiceBtn").disabled = !ok;
  $("#confirmContinueBtn").disabled = !ok;
  $("#selectedLabel").textContent = selected?.label
    ? `候选 ${selected.label}`
    : "未选择";

  renderDirectorAdvice(selected);

  if (!selected) {
    $("#selectedPreview").innerHTML = "点击中间候选图";
    $("#selectedScores").innerHTML = "";
    $("#selectedProblems").innerHTML = "";
    return;
  }

  $("#selectedPreview").innerHTML = selected.media_url
    ? `<img src="${esc(selected.media_url)}">`
    : "图片不可用";

  $("#selectedScores").innerHTML = Object.entries(selected.scores || {})
    .map(
      ([k, v]) =>
        `<div class="barrow"><span>${esc(
          labels[k] || k
        )}</span><div class="bar"><i style="width:${v}%"></i></div><b>${esc(
          v
        )}</b></div>`
    )
    .join("");

  $("#selectedProblems").innerHTML = [
    ...(selected.locked_violations || []).map((x) => `LOCK: ${x}`),
    ...(selected.problems || []),
  ]
    .map((x) => `<div class="problem">${esc(x)}</div>`)
    .join("");
}

function renderTimeline(versions) {
  $("#timeline").innerHTML =
    versions
      .map(
        (x) =>
          `<div class="ver">
            ${x.identity_anchor_media_url ? `<img src="${esc(x.identity_anchor_media_url)}">` : ""}
            <div>
              <b>V${esc(x.version)}</b><br>
              ${esc((x.human_feedback || []).slice(-1)[0] || "已归档")}
              <button class="rollback" data-v="${x.version}">回滚到此版</button>
            </div>
          </div>`
      )
      .join("") || "<div class=meta>还没有可回滚版本</div>";

  document.querySelectorAll(".rollback").forEach((b) => {
    b.onclick = () => rollback(Number(b.dataset.v));
  });
}

function renderScenes(s) {
  if (!data.scene_validation_enabled) {
    $("#sceneStatus").innerHTML = '<span class="chip">未配置</span>';
    $("#sceneGrid").innerHTML =
      '<div class="meta" style="grid-column:1/-1">当前角色还没有独立 Scene Profile，不会复用其他角色的场景模板。</div>';
    return;
  }
  if (!s.scene_results) {
    $("#sceneStatus").innerHTML = '<span class="chip">未验证</span>';
    $("#sceneGrid").innerHTML = ["office", "home", "abnormal"]
      .map((x) => `<div class="scene"><b>${x}</b><br>等待验证</div>`)
      .join("");
    return;
  }
  $("#sceneStatus").innerHTML = `<span class="chip ${
    s.pass ? "ready" : ""
  }">${s.pass ? "PASS" : "需继续"}</span>`;
  $("#sceneGrid").innerHTML = s.scene_results
    .map(
      (x) =>
        `<div class="scene"><b>${esc(x.scene_id)}</b><br>identity ${esc(
          x.identity_score ?? "-"
        )} · canon ${esc(x.canon_score ?? "-")}</div>`
    )
    .join("");
}

function renderAnchor(s) {
  $("#anchorCard").innerHTML = s.identity_anchor
    ? `${
        data.identity_anchor_media_url
          ? `<img style="width:100%;border-radius:7px;margin-bottom:7px" src="${esc(
              data.identity_anchor_media_url
            )}">`
          : ""
      }<b>已锁定身份锚点</b><br>${esc(s.identity_anchor)}`
    : "尚未人工确认。自动 A/B/C 不会成为最终身份。";
}

function payload() {
  const locks = [
    ...document.querySelectorAll("#lockFeatures input:checked"),
  ].map((x) => x.value);
  const rejected = $("#rejectInput")
    .value.split(/[,，]/)
    .map((x) => x.trim())
    .filter(Boolean);
  const feature = $("#changeFeature").value;
  const target = $("#changeTarget").value.trim();

  return {
    character_id: characterId,
    label: selected.label,
    feedback: $("#feedbackInput").value.trim(),
    lock_features: locks,
    rejected,
    changes:
      feature && target ? [{ feature, target }] : [],
  };
}

async function confirm(next = false) {
  busy("正在写入人物记忆", `确认候选 ${selected.label} 为身份锚点`);
  try {
    data = await api("/api/choice", {
      method: "POST",
      body: JSON.stringify(payload()),
    });
    selected = null;
    render();
    toast("人工选择、Agent Patch 与反馈已写入 Memory");
    if (next) await runRound();
  } catch (e) {
    toast(e.message);
  } finally {
    unbusy();
  }
}

async function submitJob(kind) {
  try {
    const r = await api("/api/jobs", {
      method: "POST",
      body: JSON.stringify({ kind, character_id: characterId }),
    });
    toast((kind === "round" ? "人物迭代" : "三场景") + "任务已进入后台");
    pollJob(r.job.id);
  } catch (e) {
    toast(e.message);
  }
}

async function pollJob(id) {
  clearTimeout(pollTimer);
  try {
    const r = await api("/api/jobs/" + id);
    const j = r.job;
    $("#jobBadge").textContent = j.kind + " · " + j.status;
    if (j.status === "queued" || j.status === "running") {
      pollTimer = setTimeout(() => pollJob(id), 1000);
      return;
    }
    await reload();
    toast(
      j.status === "succeeded"
        ? "后台任务完成，Director Agent 建议已更新"
        : j.error || "任务失败"
    );
  } catch (e) {
    toast(e.message);
  }
}

async function runRound() {
  return submitJob("round");
}

async function runScenes() {
  return submitJob("scenes");
}

async function rollback(version) {
  if (
    !window.confirm(
      `确定回滚到 V${version}？当前 latest state 会被替换，但后续归档仍保留。`
    )
  ) {
    return;
  }
  busy("正在回滚", `恢复 V${version} 的 state / batch / scene`);
  try {
    data = await api("/api/rollback", {
      method: "POST",
      body: JSON.stringify({ character_id: characterId, version }),
    });
    selected = null;
    render();
    toast(`已回滚到 V${version}`);
  } catch (e) {
    toast(e.message);
  } finally {
    unbusy();
  }
}

async function configCheck() {
  busy(
    "正在检查配置",
    "检查 workflow、Vision Critic、Director Agent、API key，并尝试连接本机 ComfyUI"
  );
  try {
    const r = await api(
      "/api/config-check?character_id=" +
        encodeURIComponent(characterId) +
        "&connection=1"
    );
    data.config_state = r;
    data.config_ready = r.ready;
    render();
    toast(
      r.checks.every((x) => x.ok)
        ? "全部配置检查通过"
        : "配置检查完成，有项目需要处理"
    );
  } catch (e) {
    toast(e.message);
  } finally {
    unbusy();
  }
}

$("#refreshBtn").onclick = reload;
$("#runBtn").onclick = runRound;
$("#emptyRunBtn").onclick = runRound;
$("#sceneBtn").onclick = runScenes;
$("#confirmChoiceBtn").onclick = () => confirm(false);
$("#confirmContinueBtn").onclick = () => confirm(true);
$("#configCheckBtn").onclick = configCheck;
$("#characterSelect").onchange = async (event) => {
  characterId = event.target.value;
  selected = null;
  await reload();
};

reload()
  .then(() => {
    if (data.active_job) pollJob(data.active_job.id);
  })
  .catch((e) => toast(e.message));
