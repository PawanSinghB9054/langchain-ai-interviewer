const setupScreen = document.getElementById("setup-screen");
const chatScreen = document.getElementById("chat-screen");
const modeButtons = document.querySelectorAll(".mode-btn");
const pdfUploadGroup = document.getElementById("pdf-upload-group");
const startBtn = document.getElementById("start-btn");
const setupError = document.getElementById("setup-error");

const chatWindow = document.getElementById("chat-window");
const answerInput = document.getElementById("answer-input");
const sendBtn = document.getElementById("send-btn");
const loading = document.getElementById("loading");
const endBtn = document.getElementById("end-btn");
const chatTopic = document.getElementById("chat-topic");
const chatDiff = document.getElementById("chat-diff");

let currentMode = "normal";

// ===== PDF file name display =====
const pdfFileInput = document.getElementById("pdf-file");
const fileDropText = document.getElementById("file-drop-text");
if (pdfFileInput) {
  pdfFileInput.addEventListener("change", () => {
    if (pdfFileInput.files[0]) {
      fileDropText.textContent = "📄 " + pdfFileInput.files[0].name;
    } else {
      fileDropText.textContent = "Click to upload PDF";
    }
  });
}

// ===== Auto-resize textarea =====
answerInput.addEventListener("input", () => {
  answerInput.style.height = "auto";
  answerInput.style.height = Math.min(answerInput.scrollHeight, 120) + "px";
});

// ===== Mode toggle =====
modeButtons.forEach(btn => {
  btn.addEventListener("click", () => {
    modeButtons.forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode;
    pdfUploadGroup.style.display = currentMode === "pdf" ? "block" : "none";
  });
});

// ===== Start interview =====
startBtn.addEventListener("click", async () => {
  const topic = document.getElementById("topic").value.trim();
  const difficulty = document.getElementById("difficulty").value;
  setupError.textContent = "";

  if (!topic) {
    setupError.textContent = "Kripya topic dalein.";
    return;
  }

  const formData = new FormData();
  formData.append("mode", currentMode);
  formData.append("topic", topic);
  formData.append("difficulty", difficulty);

  if (currentMode === "pdf") {
    const pdfFile = document.getElementById("pdf-file").files[0];
    if (!pdfFile) {
      setupError.textContent = "Kripya PDF file upload karein.";
      return;
    }
    formData.append("pdf", pdfFile);
  }

  startBtn.disabled = true;
  startBtn.textContent = "Starting...";

  try {
    const res = await fetch("/api/start", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      setupError.textContent = data.error || "Kuch error aa gaya.";
      startBtn.disabled = false;
      startBtn.textContent = "Start Interview";
      return;
    }

    chatTopic.textContent = topic;
    chatDiff.textContent = difficulty;
    setupScreen.style.display = "none";
    chatScreen.style.display = "flex";

    addMessage(data.message, "ai");
  } catch (err) {
    setupError.textContent = "Server se connect nahi ho paya.";
  } finally {
    startBtn.disabled = false;
    startBtn.textContent = "Start Interview";
  }
});

// ===== Send answer =====
sendBtn.addEventListener("click", sendAnswer);
answerInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendAnswer();
  }
});

async function sendAnswer() {
  const ans = answerInput.value.trim();
  if (!ans) return;

  addMessage(ans, "user");
  answerInput.value = "";
  loading.style.display = "block";
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer: ans })
    });
    const data = await res.json();

    if (!res.ok) {
      addMessage("Error: " + (data.error || "Kuch galat ho gaya"), "ai");
    } else {
      addMessage(data.message, "ai");
    }
  } catch (err) {
    addMessage("Server se connect nahi ho paya.", "ai");
  } finally {
    loading.style.display = "none";
    sendBtn.disabled = false;
  }
}

// ===== End interview =====
endBtn.addEventListener("click", async () => {
  await fetch("/api/reset", { method: "POST" });
  chatWindow.innerHTML = "";
  chatScreen.style.display = "none";
  setupScreen.style.display = "block";
});

// ===== Helper: add message bubble =====
function addMessage(text, sender) {
  const div = document.createElement("div");
  div.className = `msg ${sender}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}