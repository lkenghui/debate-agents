let eventSource = null;

function setStatus(text) {
  document.getElementById("status-text").textContent = text;
}

function startDebate() {
  const topic = document.getElementById("topic-input").value.trim();
  if (!topic) return;

  // Close any existing stream
  if (eventSource) { eventSource.close(); eventSource = null; }

  // Reset UI
  document.getElementById("pro-opening").textContent = "";
  document.getElementById("con-opening").textContent = "";
  document.getElementById("pro-closing-text").textContent = "";
  document.getElementById("con-closing-text").textContent = "";
  document.getElementById("judge-text").textContent = "";
  document.getElementById("pro-closing").style.display = "none";
  document.getElementById("con-closing").style.display = "none";
  document.getElementById("judge-panel").style.display = "none";
  document.getElementById("pro-round").textContent = "Opening Argument";
  document.getElementById("con-round").textContent = "Opening Argument";

  document.getElementById("debate-arena").style.display = "grid";
  document.getElementById("status-bar").style.display = "block";
  document.getElementById("debate-btn").disabled = true;
  setStatus("🟢 Pro agent is making their opening argument…");

  eventSource = new EventSource(`/api/debate?topic=${encodeURIComponent(topic)}`);

  eventSource.onmessage = (e) => {
    const { agent, chunk } = JSON.parse(e.data);

    if (agent === "pro") {
      document.getElementById("pro-opening").textContent += chunk;
      setStatus("🟢 Pro agent is arguing…");
    } else if (agent === "con") {
      document.getElementById("con-opening").textContent += chunk;
      setStatus("🔴 Con agent is rebutting…");
    } else if (agent === "pro_close") {
      document.getElementById("pro-closing").style.display = "block";
      document.getElementById("pro-closing-text").textContent += chunk;
      setStatus("🟢 Pro agent is making their closing statement…");
    } else if (agent === "con_close") {
      document.getElementById("con-closing").style.display = "block";
      document.getElementById("con-closing-text").textContent += chunk;
      setStatus("🔴 Con agent is making their closing statement…");
    } else if (agent === "judge") {
      document.getElementById("judge-panel").style.display = "block";
      document.getElementById("judge-text").textContent += chunk;
      setStatus("⚖️ Judge is deliberating…");
    } else if (agent === "done") {
      eventSource.close();
      eventSource = null;
      document.getElementById("status-bar").style.display = "none";
      document.getElementById("debate-btn").disabled = false;
    }
  };

  eventSource.onerror = () => {
    setStatus("⚠️ Connection error. Please try again.");
    document.getElementById("debate-btn").disabled = false;
    if (eventSource) { eventSource.close(); eventSource = null; }
  };
}

// Allow Enter key to start debate
document.getElementById("topic-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") startDebate();
});
