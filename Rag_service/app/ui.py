from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Personalized Knowledge Assistant</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
        }
        button {
            padding: 10px 16px;
            margin-top: 10px;
            cursor: pointer;
        }
        textarea, select, input {
            width: 100%;
            margin-top: 6px;
            padding: 6px;
        }
        pre {
            background: #f2f2f2;
            padding: 10px;
            margin-top: 10px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .hidden {
            display: none;
        }
        .nav-btn {
            margin-right: 10px;
        }
        hr {
            margin: 25px 0;
        }
        select,
        #uploadUrl {
            height: 36px;
            box-sizing: border-box;
        }
    </style>
</head>

<body>

<div id="tokenView">
    <h1>Setup Required</h1>
    <h3>Enter HuggingFace Token</h3>

    <input type="password" id="hfTokenInput" placeholder="hf_..." />

    <button onclick="saveTokenAndProceed()">Save Token</button>

    <p>OR</p>
    <button onclick="useEnvToken()">Use Server Token</button>

    <pre id="tokenMessage"></pre>
</div>

<!-- ================= HOME ================= -->
<div id="homeView" class="hidden">
    <h1>Personalized Knowledge Assistant</h1>
    <p id="tokenIndicator"></p>
    <button class="nav-btn" onclick="showUploadView()">Upload File / URL</button>
    <button class="nav-btn" onclick="showAskView()">Ask Questions on Indexed Data</button>
    <button class="nav-btn" onclick="showEvalView()">Run RAG Evaluation</button>
    <button onclick="deleteToken()">Delete Token</button>
</div>

<!-- ================= UPLOAD VIEW ================= -->
<div id="uploadView" class="hidden">
    <h2>Upload Document</h2>

    <select id="uploadType" onchange="onUploadTypeChange()">
        <option value="file">Upload File</option>
        <option value="url">Upload URL</option>
    </select>

    <input type="file" id="uploadFile" />
    <input
        type="text"
        id="uploadUrl"
        class="hidden"
        placeholder="https://example.com/page"
    />

    <select id="uploadDomain">
        <option value="general">General</option>
        <option value="foundations">Foundations</option>
        <option value="rag">RAG</option>
        <option value="agents">Agents</option>
    </select>

    <button onclick="upload()">Upload & Index</button>
    <pre id="uploadResult"></pre>

    <div id="postUploadAsk" class="hidden">
        <hr>
        <h3>Ask about this document</h3>
        <textarea id="docQuery" rows="4" placeholder="Ask something from this document..."></textarea>
        <button onclick="askOnUploadedDoc()">Ask</button>
        <pre id="docAnswer"></pre>
    </div>

    <hr>
    <button onclick="goHome()">Back to Home</button>
</div>

<!-- ================= ASK VIEW ================= -->
<div id="askView" class="hidden">
    <h2>Ask Questions on Indexed Data</h2>

    <select id="modeSelector" onchange="onModeChange()">
        <option value="global">Global Knowledge</option>
        <option value="document">Ask about a Document</option>
    </select>

    <div id="documentSelector" class="hidden">
        <h3>Select Document</h3>
        <select id="documentList"></select>
    </div>

    <textarea id="queryText" rows="4" placeholder="Ask something..."></textarea>
    <button onclick="ask()">Ask</button>

    <h4>Answer</h4>
    <pre id="answer"></pre>

    <div id="introspectionBlock">
        <h4>Agent Introspection</h4>
        <div id="introspection" style="
            background:#eef;
            padding:10px;
            border-radius:6px;
            font-family:monospace;
        "></div>

        <h4>Sources</h4>
        <pre id="sources"></pre>
    </div>

    <hr>
    <button onclick="goHome()">Back to Home</button>
</div>

<!-- ================= EVAL VIEW ================= -->
<div id="evalView" class="hidden">
    <h2>RAG Evaluation — Ragas Scores</h2>
    <p>Enter test questions below (one per line).
       The system will run your live pipeline on each
       question and return Ragas scores.</p>

    <textarea id="evalQuestions" rows="6"
        placeholder="How do I reset my SAP password?
            What is the SLA for P1 incidents?
            How do I raise a change request?">
    </textarea>

    <button onclick="runEval()">Run Evaluation</button>
    <pre id="evalResult"></pre>

    <hr>
    <button onclick="goHome()">Back to Home</button>
</div>

<script>
/* ================= SESSION ================= */

function generateSessionId() {
    return 'xxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

let sessionId = localStorage.getItem("session_id");

if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem("session_id", sessionId);
}

/* ================= VIEW SWITCHING ================= */

function hideAll() {
    // BUG FIX: evalView added here so it is properly hidden on every navigation
    ["tokenView", "homeView", "uploadView", "askView", "evalView"].forEach(id =>
        document.getElementById(id).classList.add("hidden")
    );
}

function goHome() {
    showHome();
}

function showUploadView() {
    hideAll();
    resetUploadState();
    document.getElementById("uploadView").classList.remove("hidden");
    onUploadTypeChange();
}

function showAskView() {
    hideAll();
    document.getElementById("askView").classList.remove("hidden");
    onModeChange();
}

function showEvalView() {
    hideAll();
    document.getElementById("evalView").classList.remove("hidden");
}

function showTokenView() {
    hideAll();
    document.getElementById("tokenView").classList.remove("hidden");
}

function showHome() {
    hideAll();
    document.getElementById("homeView").classList.remove("hidden");
}

/* ---------------- BOOT ---------------- */

function getToken() {
    return localStorage.getItem("hf_token") || "";
}

async function saveTokenAndProceed() {
    const token = document.getElementById("hfTokenInput").value.trim();

    if (!token) {
        document.getElementById("tokenMessage").innerText =
            "❌ Please enter a valid HuggingFace token";
        return;
    }

    document.getElementById("tokenMessage").innerText = "⏳ Saving token...";

    try {
        const res = await fetch("/api/set-token", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ hf_token: token })
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const data = await res.json();

        if (data.status === "success") {
            localStorage.setItem("hf_token", token);

            document.getElementById("tokenMessage").innerText =
                "✅ Token saved successfully!";

            setTimeout(showHome, 800);
        } else {
            document.getElementById("tokenMessage").innerText =
                "❌ " + (data.message || "Failed to save token");
        }

    } catch (err) {
        console.error("Token save error:", err);
        document.getElementById("tokenMessage").innerText =
            "❌ Network error: " + err.message;
    }
}

// Use server environment token pool
async function useEnvToken() {
    document.getElementById("tokenMessage").innerText = 
        "⏳ Configuring server token...";

    try {
        const res = await fetch("/api/set-token", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ hf_token: "" })  // Empty = use ENV pool
        });

        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const data = await res.json();

        if (data.status === "success") {
            localStorage.setItem("hf_token", "USE_ENV");
            
            document.getElementById("tokenMessage").innerText =
                "✅ Using server token pool";

            setTimeout(showHome, 800);
        } else {
            document.getElementById("tokenMessage").innerText =
                "❌ " + (data.message || "Failed to configure server token");
        }

    } catch (err) {
        console.error("Server token error:", err);
        document.getElementById("tokenMessage").innerText =
            "❌ Network error: " + err.message + 
            "\\n\\nMake sure HF_TOKEN_POOL is set in your environment variables.";
    }
}

function deleteToken() {
    localStorage.removeItem("hf_token");
    alert("Token deleted");
    showTokenView();
}

document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 App loaded");
    
    const token = getToken();
    console.log("📝 Token status:", token ? (token === "USE_ENV" ? "Using ENV" : "User token set") : "No token");

    if (token && token !== "") {
        console.log("✅ Token found, showing home");
        showHome();

        const indicator = document.getElementById("tokenIndicator");
        if (indicator) {
            const status = token === "USE_ENV" 
                ? "Token Status: Using Server Pool" 
                : "Token Status: User Token Connected";
            indicator.innerText = status;
            indicator.style.color = "#28a745";
        }
    } else {
        console.log("⚠️ No token, showing token view");
        showTokenView();
    }
});

/* ================= UPLOAD ================= */

let uploadedDocumentId = null;

function resetUploadState() {
    uploadedDocumentId = null;
    document.getElementById("uploadResult").innerText = "";
    document.getElementById("postUploadAsk").classList.add("hidden");
    document.getElementById("uploadFile").value = "";
    document.getElementById("uploadUrl").value = "";
    document.getElementById("docQuery").value = "";
    document.getElementById("docAnswer").innerText = "";
}

async function upload() {
    const type = document.getElementById("uploadType").value;
    const domain = document.getElementById("uploadDomain").value;

    if (type === "file") {
        const fileInput = document.getElementById("uploadFile");
        if (!fileInput.files.length) {
            alert("Select a file");
            return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        formData.append("domain", domain);

        const res = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        const data = await res.json();
        handleUploadSuccess(data);

    } else {
        const url = document.getElementById("uploadUrl").value.trim();
        if (!url) {
            alert("Enter a URL");
            return;
        }

        const res = await fetch("/api/upload/url", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, domain })
        });

        const data = await res.json();
        handleUploadSuccess(data);
    }
}

function handleUploadSuccess(data) {
    document.getElementById("uploadResult").innerText =
        JSON.stringify(data, null, 2);

    if (data.document_id) {
        uploadedDocumentId = data.document_id;
        document.getElementById("postUploadAsk").classList.remove("hidden");
    }
}

/* ================= ASK ON UPLOADED DOC ================= */

async function askOnUploadedDoc() {
    const query = document.getElementById("docQuery").value;

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            query,
            session_id: sessionId,
            document_id: uploadedDocumentId
        })
    });

    const data = await res.json();
    document.getElementById("docAnswer").innerText = data.answer || "";
}

/* ================= ASK (GLOBAL / DOCUMENT) ================= */

async function loadDocuments() {
    const res = await fetch("/api/knowledge");
    const data = await res.json();

    const select = document.getElementById("documentList");
    select.innerHTML = "";

    const documents = data.documents || {};

    if (Object.keys(documents).length === 0) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.innerText = "No documents indexed";
        select.appendChild(opt);
        return;
    }

    for (const [id, name] of Object.entries(documents)) {
        const opt = document.createElement("option");
        opt.value = id;
        opt.innerText = name;
        select.appendChild(opt);
    }
}

function onModeChange() {
    const mode = document.getElementById("modeSelector").value;
    document.getElementById("documentSelector").classList.add("hidden");
    document.getElementById("introspectionBlock").classList.remove("hidden");

    if (mode === "document") {
        document.getElementById("documentSelector").classList.remove("hidden");
        document.getElementById("introspectionBlock").classList.add("hidden");
        loadDocuments();
    }
}

async function ask() {
    const mode = document.getElementById("modeSelector").value;
    let token = getToken();
    if (token === "USE_ENV") token = "";
    const payload = {
        query: document.getElementById("queryText").value,
        session_id: sessionId,
        hf_token: token
    };

    if (mode === "document") {
        payload.document_id =
            document.getElementById("documentList").value;
    }

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    document.getElementById("answer").innerText = data.answer || "";

    if (mode === "global") {
        document.getElementById("introspection").innerHTML =
        "<strong>Coverage:</strong> " + (data.coverage || "N/A") + "<br>" +
        "<strong>Path taken:</strong> " + (data.path_taken || "N/A");
        
        document.getElementById("sources").innerText =
            (data.sources || []).join("\\n");
    }
}

/* ---------------- EVAL ---------------- */

async function runEval() {
    const raw = document.getElementById("evalQuestions").value;

    const questions = raw
        .split("\\n")
        .map(q => q.trim())
        .filter(q => q.length > 0);

    if (questions.length === 0) {
        alert("Enter at least one question.");
        return;
    }

    document.getElementById("evalResult").innerText =
        "Running evaluation... this may take 1-2 minutes.";

    let token = getToken();

    // If user selected ENV mode, send empty string
    if (token === "USE_ENV") {
        token = "";
    }

    const res = await fetch("/api/eval", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            test_questions: questions,
            session_id: sessionId,
            hf_token: token
        })
    });

    const data = await res.json();
    const output =(
    "Ragas Evaluation Results\\n" +
    "========================\\n" +
    "Questions evaluated : " + data.num_questions + "\\n" +
    "Faithfulness        : " + data.faithfulness + " (target > 0.85)\\n" +
    "Answer Relevancy    : " + data.answer_relevancy + " (target > 0.80)\\n" +
    "Overall status      : " + data.status).trim();

    document.getElementById("evalResult").innerText = output;
}

/* ---------------- UPLOAD TYPE TOGGLE ---------------- */

function onUploadTypeChange() {
    const type = document.getElementById("uploadType").value;
    document.getElementById("uploadFile").classList.toggle("hidden", type === "url");
    document.getElementById("uploadUrl").classList.toggle("hidden", type === "file");
}
</script>

</body>
</html>
"""