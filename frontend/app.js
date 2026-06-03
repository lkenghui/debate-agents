let eventSource = null;
let activeStreamEl = null;

const ROUND_LABELS = {
  pro:        { panel: "pro-round",  text: "Round 1 — Opening" },
  con:        { panel: "con-round",  text: "Round 1 — Opening" },
  pro_reb1:   { panel: "pro-round",  text: "Round 2 — Rebuttal" },
  con_reb1:   { panel: "con-round",  text: "Round 2 — Rebuttal" },
  pro_reb2:   { panel: "pro-round",  text: "Round 3 — Rebuttal" },
  con_reb2:   { panel: "con-round",  text: "Round 3 — Rebuttal" },
  pro_close:  { panel: "pro-round",  text: "Closing Statement" },
  con_close:  { panel: "con-round",  text: "Closing Statement" },
  judge:      { panel: null,         text: "" },
  factcheck:  { panel: null,         text: "" },
};

const AGENT_EL = {
  pro:       "pro-opening",
  con:       "con-opening",
  pro_reb1:  "pro-reb1",
  con_reb1:  "con-reb1",
  pro_reb2:  "pro-reb2",
  con_reb2:  "con-reb2",
  pro_close: "pro-close",
  con_close: "con-close",
};

const AGENT_SECTION = {
  pro_reb1:  "pro-reb1-section",
  con_reb1:  "con-reb1-section",
  pro_reb2:  "pro-reb2-section",
  con_reb2:  "con-reb2-section",
  pro_close: "pro-close-section",
  con_close: "con-close-section",
};

function setStreamTarget(el) {
  if (activeStreamEl) activeStreamEl.classList.remove("typing-cursor");
  activeStreamEl = el;
  if (el) el.classList.add("typing-cursor");
}

function setStatus(text) {
  document.getElementById("status-text").textContent = text;
}

function renderJudgeMarkdown(text) {
  const escaped = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped
    .replace(/^## (.+)$/gm, '<h3 class="judge-section">$1</h3>')
    .replace(/\n/g, "<br>");
}

function resetUI() {
  const textEls = ["pro-opening", "con-opening", "pro-reb1", "con-reb1",
                   "pro-reb2", "con-reb2", "pro-close", "con-close", "factcheck-text"];
  textEls.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = "";
  });
  document.getElementById("prelim-judge-text").innerHTML = "";
  document.getElementById("prelim-judge-text").dataset.raw = "";
  document.getElementById("final-judge-text").innerHTML = "";
  document.getElementById("final-judge-text").dataset.raw = "";

  const sections = ["pro-reb1-section", "con-reb1-section", "pro-reb2-section",
                    "con-reb2-section", "pro-close-section", "con-close-section"];
  sections.forEach(id => {
    document.getElementById(id).style.display = "none";
  });

  document.getElementById("prelim-judge-panel").style.display = "none";
  document.getElementById("factcheck-panel").style.display = "none";
  document.getElementById("final-judge-panel").style.display = "none";
  document.getElementById("share-bar").style.display = "none";
  document.getElementById("pro-round").textContent = "Opening Argument";
  document.getElementById("con-round").textContent = "Opening Argument";
  setStreamTarget(null);
}

function startDebate() {
  const topic = document.getElementById("topic-input").value.trim();
  if (!topic) return;
  const difficulty = document.getElementById("difficulty-select").value;

  if (eventSource) { eventSource.close(); eventSource = null; }

  resetUI();
  document.getElementById("debate-arena").style.display = "grid";
  document.getElementById("status-bar").style.display = "block";
  document.getElementById("debate-btn").disabled = true;
  setStatus("🟢 Pro agent is making their opening argument…");

  const url = `/api/debate?topic=${encodeURIComponent(topic)}&difficulty=${difficulty}`;
  eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    const { agent, chunk } = JSON.parse(e.data);

    // Update round label
    if (ROUND_LABELS[agent]?.panel) {
      document.getElementById(ROUND_LABELS[agent].panel).textContent = ROUND_LABELS[agent].text;
    }

    // Show section if needed
    if (AGENT_SECTION[agent]) {
      document.getElementById(AGENT_SECTION[agent]).style.display = "block";
    }

    if (agent === "prelim_judge") {
      document.getElementById("prelim-judge-panel").style.display = "block";
      setStreamTarget(document.getElementById("prelim-judge-text"));
      const raw = (document.getElementById("prelim-judge-text").dataset.raw || "") + chunk;
      document.getElementById("prelim-judge-text").dataset.raw = raw;
      document.getElementById("prelim-judge-text").innerHTML = renderJudgeMarkdown(raw);
      setStatus("⚖️ Judge is giving preliminary verdict…");

    } else if (agent === "final_judge") {
      document.getElementById("final-judge-panel").style.display = "block";
      setStreamTarget(document.getElementById("final-judge-text"));
      const raw = (document.getElementById("final-judge-text").dataset.raw || "") + chunk;
      document.getElementById("final-judge-text").dataset.raw = raw;
      document.getElementById("final-judge-text").innerHTML = renderJudgeMarkdown(raw);
      setStatus("🏆 Judge is delivering final verdict…");

    } else if (agent === "factcheck") {
      document.getElementById("factcheck-panel").style.display = "block";
      setStreamTarget(document.getElementById("factcheck-text"));
      document.getElementById("factcheck-text").textContent += chunk;
      setStatus("🔍 Fact-checker is reviewing claims…");

    } else if (agent === "error") {
      setStatus(`⚠️ ${chunk}`);
      setStreamTarget(null);
      document.getElementById("debate-btn").disabled = false;
      if (eventSource) { eventSource.close(); eventSource = null; }

    } else if (agent === "done") {
      setStreamTarget(null);
      document.getElementById("status-bar").style.display = "none";
      document.getElementById("share-bar").style.display = "block";
      document.getElementById("debate-btn").disabled = false;
      if (eventSource) { eventSource.close(); eventSource = null; }
      loadHistory();

    } else if (AGENT_EL[agent]) {
      const el = document.getElementById(AGENT_EL[agent]);
      setStreamTarget(el);
      el.textContent += chunk;

      const statusMap = {
        pro:       "🟢 Pro agent is arguing…",
        con:       "🔴 Con agent is rebutting…",
        pro_reb1:  "🟢 Pro agent is making their first rebuttal…",
        con_reb1:  "🔴 Con agent is making their first rebuttal…",
        pro_reb2:  "🟢 Pro agent is making their second rebuttal…",
        con_reb2:  "🔴 Con agent is making their second rebuttal…",
        pro_close: "🟢 Pro agent is giving their closing statement…",
        con_close: "🔴 Con agent is giving their closing statement…",
      };
      if (statusMap[agent]) setStatus(statusMap[agent]);
    }
  };

  eventSource.onerror = () => {
    setStatus("⚠️ Connection dropped. Please try again.");
    setStreamTarget(null);
    document.getElementById("debate-btn").disabled = false;
    if (eventSource) { eventSource.close(); eventSource = null; }
  };
}

function shareDebate() {
  const topic = document.getElementById("topic-input").value.trim();
  const sections = [
    ["DEBATE TOPIC", topic],
    ["PRO — Round 1 Opening",    document.getElementById("pro-opening")?.textContent],
    ["CON — Round 1 Opening",    document.getElementById("con-opening")?.textContent],
    ["PRO — Round 2 Rebuttal",   document.getElementById("pro-reb1")?.textContent],
    ["CON — Round 2 Rebuttal",   document.getElementById("con-reb1")?.textContent],
    ["PRO — Round 3 Rebuttal",   document.getElementById("pro-reb2")?.textContent],
    ["CON — Round 3 Rebuttal",   document.getElementById("con-reb2")?.textContent],
    ["PRO — Closing Statement",  document.getElementById("pro-close")?.textContent],
    ["CON — Closing Statement",  document.getElementById("con-close")?.textContent],
    ["PRELIMINARY VERDICT",       document.getElementById("prelim-judge-text")?.innerText],
    ["FACT-CHECKER'S REPORT",    document.getElementById("factcheck-text")?.textContent],
    ["FINAL VERDICT",            document.getElementById("final-judge-text")?.innerText],
  ];
  const text = sections
    .filter(([, c]) => c?.trim())
    .map(([label, content]) => `=== ${label} ===\n${content.trim()}`)
    .join("\n\n");

  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("share-btn");
    btn.textContent = "✅ Copied!";
    setTimeout(() => { btn.textContent = "📋 Copy Debate as Text"; }, 2000);
  });
}

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const debates = await res.json();
    const list = document.getElementById("history-list");
    if (!debates.length) {
      list.innerHTML = "<li class='history-empty'>No past debates yet.</li>";
      return;
    }
    list.innerHTML = debates.map(d => {
      const winnerClass = d.winner === "PRO" ? "winner-pro" : d.winner === "CON" ? "winner-con" : "";
      const winnerText = d.winner ? `<span class="${winnerClass}">${d.winner} won</span>` : "no verdict";
      const date = d.started_at ? d.started_at.slice(0, 10) : "";
      return `
        <li class="history-item" onclick="loadPastDebate(${d.id})">
          <span class="history-topic">${d.topic}</span>
          <span class="history-meta">${d.difficulty} · ${winnerText} · ${date}</span>
        </li>`;
    }).join("");
  } catch (e) {
    console.error("Failed to load history", e);
  }
}

async function loadPastDebate(id) {
  try {
    const res = await fetch(`/api/history/${id}`);
    const d = await res.json();

    resetUI();
    document.getElementById("topic-input").value = d.topic;
    document.getElementById("debate-arena").style.display = "grid";
    document.getElementById("status-bar").style.display = "none";

    const fill = (elId, text, sectionId) => {
      if (text) {
        if (sectionId) document.getElementById(sectionId).style.display = "block";
        document.getElementById(elId).textContent = text;
      }
    };

    fill("pro-opening", d.pro_opening);
    fill("con-opening", d.con_opening);
    fill("pro-reb1", d.pro_reb1, "pro-reb1-section");
    fill("con-reb1", d.con_reb1, "con-reb1-section");
    fill("pro-reb2", d.pro_reb2, "pro-reb2-section");
    fill("con-reb2", d.con_reb2, "con-reb2-section");
    fill("pro-close", d.pro_close, "pro-close-section");
    fill("con-close", d.con_close, "con-close-section");
    fill("factcheck-text", d.factcheck);

    if (d.prelim_judge) {
      document.getElementById("prelim-judge-panel").style.display = "block";
      document.getElementById("prelim-judge-text").dataset.raw = d.prelim_judge;
      document.getElementById("prelim-judge-text").innerHTML = renderJudgeMarkdown(d.prelim_judge);
    }
    if (d.factcheck) {
      document.getElementById("factcheck-panel").style.display = "block";
    }
    if (d.final_judge) {
      document.getElementById("final-judge-panel").style.display = "block";
      document.getElementById("final-judge-text").dataset.raw = d.final_judge;
      document.getElementById("final-judge-text").innerHTML = renderJudgeMarkdown(d.final_judge);
    }
    document.getElementById("share-bar").style.display = "block";
  } catch (e) {
    console.error("Failed to load past debate", e);
  }
}

// Enter to submit, Shift+Enter for newline
document.getElementById("topic-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    startDebate();
  }
});

// Load history on page load
loadHistory();
