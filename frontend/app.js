"use strict";

const NODES = [
  ["voc", "用户洞察 JML"],
  ["think_tank", "超级智囊 AMI"],
  ["pm", "产品经理"],
  ["users", "用户替身"],
  ["expert", "行业专家"],
  ["decision", "决策官"],
  ["output", "产出 PR/FAQ"],
];

const $ = (id) => document.getElementById(id);
const pct = (x) => `${Math.round((x || 0) * 100)}%`;

function renderPipeline() {
  const el = $("pipeline");
  el.innerHTML = NODES.map(
    ([id, label]) => `<div class="chip" data-node="${id}"><span class="led"></span>${label}</div>`
  ).join("");
}

function setChip(node, state) {
  const c = document.querySelector(`.chip[data-node="${node}"]`);
  if (!c) return;
  if (state === "start") { c.classList.add("active"); c.classList.remove("done"); }
  if (state === "end") { c.classList.remove("active"); c.classList.add("done"); }
}

function resetChips() {
  document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active", "done"));
}

function run() {
  resetChips();
  $("runBtn").disabled = true;
  $("status").textContent = "运行中…";
  const brief = encodeURIComponent($("brief").value);
  const es = new EventSource(`api/stream?brief=${brief}`);
  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "trace") {
      const ev = msg.event;
      if (ev.kind === "start") setChip(ev.node, "start");
      if (ev.kind === "end") setChip(ev.node, "end");
      $("status").textContent = `节点：${ev.node} · ${ev.kind}`;
    } else if (msg.type === "result") {
      renderAll(msg.view);
      $("status").textContent = `完成 · ${msg.view.run_id} · ${msg.view.elapsed_seconds}s · provider=${msg.view.provider}`;
    } else if (msg.type === "error") {
      $("status").textContent = "错误：" + msg.message;
    } else if (msg.type === "done") {
      es.close();
      $("runBtn").disabled = false;
    }
  };
  es.onerror = () => { es.close(); $("runBtn").disabled = false; $("status").textContent = "连接结束"; };
}

function renderAll(v) {
  renderCompare(v.comparison);
  renderVoc(v.voc);
  renderMarket(v.market);
  renderConcept(v.concept);
  renderUsers(v.interviews);
  renderPrfaq(v.prfaq, v.concept_image_path);
  renderDecision(v.feasibility, v.decision, v.nps);
  renderRubric(v.rubric);
}

function renderCompare(c) {
  if (!c) return;
  const rows = [
    ["机会覆盖率", pct(c.arm_a.opportunity_coverage), pct(c.arm_b.opportunity_coverage)],
    ["命中真实痛点率", pct(c.arm_a.real_pain_hit_rate), pct(c.arm_b.real_pain_hit_rate)],
    ["证据引用数", c.arm_a.evidence_citations, c.arm_b.evidence_citations],
    ["已验证假设数", c.arm_a.validated_assumptions, c.arm_b.validated_assumptions],
    ["合成用户数", c.arm_a.distinct_personas_consulted, c.arm_b.distinct_personas_consulted],
    ["可行性风险识别", c.arm_a.feasibility_risks_identified, c.arm_b.feasibility_risks_identified],
    ["预测 NPS", c.arm_a.nps_prediction, c.arm_b.nps_prediction],
  ];
  $("compare").innerHTML =
    `<table><tr><th>维度</th><th>A 经验驱动</th><th>B AI 原生</th></tr>` +
    rows.map((r) => `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="delta-pos">${r[2]}</td></tr>`).join("") +
    `</table><p class="muted" style="margin-top:10px">${c.narrative}</p>`;
}

function renderVoc(voc) {
  if (!voc) return;
  const maxOpp = Math.max(...voc.opportunities.map((o) => o.opportunity_score), 1);
  $("voc").innerHTML =
    `<small>样本 ${voc.review_count} 条评论</small>` +
    `<table style="margin-top:8px"><tr><th>机会</th><th>机会分</th></tr>` +
    voc.opportunities.map((o) =>
      `<tr><td>${o.aspect}<div class="cite">${(o.evidence_ids||[]).join(", ")}</div></td>
       <td><div class="bar" style="width:${(o.opportunity_score / maxOpp) * 100}%"></div> ${o.opportunity_score}</td></tr>`
    ).join("") + `</table>`;
}

function renderMarket(m) {
  if (!m) return;
  const comp = m.competitors.map((c) =>
    `<div class="kv"><span><b>${c.brand}</b> <small>(${c.review_count})</small></span>
     <span>${(c.weaknesses||[]).map((w) => `<span class="tag bad">${w}</span>`).join("") || "—"}</span></div>`
  ).join("");
  const ws = m.white_space.map((o) => `<span class="tag warn">${o.aspect}</span>`).join("");
  const tr = m.trends.map((t) => `<span class="tag good">${t.name}</span>`).join("");
  $("market").innerHTML = comp + `<h3>白空间机会</h3>${ws}<h3>趋势</h3>${tr}`;
}

function renderConcept(c) {
  if (!c) return;
  $("concept").innerHTML =
    `<b>${c.name}</b><p class="muted">${c.one_liner}</p>` +
    `<div class="kv"><span>目标用户</span><span>${c.target_segment}</span></div>` +
    `<h3>核心功能</h3>` + (c.key_features||[]).map((f) => `<span class="tag">${f}</span>`).join("") +
    `<h3>技术使能</h3>` + (c.tech_enablers||[]).map((f) => `<span class="tag good">${f}</span>`).join("");
}

function renderUsers(itvs) {
  if (!itvs) return;
  $("users").innerHTML = itvs.map((i) => {
    const cls = i.verdict === "would_buy" ? "good" : i.verdict === "would_not_buy" ? "bad" : "warn";
    return `<div class="kv"><span>${i.segment}</span>
      <span><span class="tag ${cls}">${i.verdict}</span> ${pct(i.acceptance)}</span></div>`;
  }).join("");
}

function renderPrfaq(f, img) {
  if (!f) return;
  const faq = (arr) => arr.map((q) =>
    `<div class="kv" style="display:block"><b>Q：${q.question}</b><div class="muted">A：${q.answer}
     <span class="cite">${(q.evidence_ids||[]).join(", ")}</span></div></div>`).join("");
  $("prfaq").innerHTML =
    `<h3>${f.headline}</h3><p><i>${f.subheading}</i></p><p>${f.summary}</p>` +
    (img ? `<img src="/${img.replace(/^.*assets\//,'assets/')}" style="max-width:100%;border-radius:10px;margin:8px 0"/>` : "") +
    `<h3>外部 FAQ</h3>${faq(f.external_faq)}<h3>内部 FAQ</h3>${faq(f.internal_faq)}`;
}

function renderDecision(fe, d, nps) {
  if (!d) return;
  $("decision").innerHTML =
    `<div class="verdict ${d.verdict}">${d.verdict}</div>` +
    `<div class="kv"><span>预测 NPS</span><span>${(nps ? nps.score : d.nps_prediction)}</span></div>` +
    `<div class="kv"><span>置信度</span><span>${d.confidence}</span></div>` +
    `<div class="kv"><span>可行性</span><span class="tag ${fe && fe.overall==='green'?'good':fe&&fe.overall==='red'?'bad':'warn'}">${fe ? fe.overall : '-'}</span></div>` +
    `<p class="muted">${d.rationale}</p>` +
    (fe ? `<h3>主要风险</h3>` + fe.risks.map((r) => `<div class="muted">· [${r.severity}] ${r.description}</div>`).join("") : "");
}

function renderRubric(r) {
  if (!r) return;
  const row = (k, val) => `<div class="kv"><span>${k}</span><span>${val}</span></div>`;
  $("rubric").innerHTML =
    row("groundedness", r.groundedness) + row("faithfulness", r.faithfulness) +
    row("citation_hit_rate", r.citation_hit_rate) + row("opportunity_coverage", r.opportunity_coverage) +
    row("persona_fidelity", r.persona_fidelity) + row("explainability", r.explainability) +
    `<div class="kv"><span><b>overall</b></span><span><b>${r.overall}</b></span></div>` +
    (r.notes && r.notes.length ? `<p class="tag warn">${r.notes.join("；")}</p>` : "");
}

renderPipeline();
$("runBtn").addEventListener("click", run);

// 截图/演示用：URL 带 ?auto=1 时自动运行一次
if (new URLSearchParams(location.search).get("auto") === "1") {
  window.addEventListener("load", () => setTimeout(run, 400));
}
