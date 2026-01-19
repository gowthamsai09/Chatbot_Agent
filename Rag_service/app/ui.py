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

<!-- TOKEN GATE  -->
<div id="tokenGate" class="hidden" style="max-width:600px;">
    <h2>Enter Hugging Face Token</h2>
    <input type="password" id="hfTokenInput" placeholder="hf_..." />
    <button onclick="saveToken()">Save Token</button>
    <p id="tokenError" style="color:red;"></p>
</div>

<!-- HOME -->
<div id="homeView" class="hidden">
    <h1>Personalized Knowledge Assistant</h1>

    <button class="nav-btn" onclick="showUploadView()">Upload File / URL</button>
    <button class="nav-btn" onclick="showAskView()">Ask Questions on Indexed Data</button>
    <button class="nav-btn" onclick="deleteToken()">Delete Token</button>
</div>

<!--  UPLOAD VIEW  -->
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

    <!-- Ask on same document -->
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

<!--  ASK VIEW  -->
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

<script>
/*  TOKEN  */

const TOKEN_KEY = "hf_token";

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function saveToken() {
    const token = document.getElementById("hfTokenInput").value.trim();
    if (!token.startsWith("hf_")) {
        document.getElementById("tokenError").innerText =
            "Invalid token. Must start with hf_.";
        return;
    }
    localStorage.setItem(TOKEN_KEY, token);
    location.reload();
}

function deleteToken() {
    localStorage.removeItem(TOKEN_KEY);
    location.reload();
}

/*  SESSION  */

const sessionId =
    localStorage.getItem("session_id") || crypto.randomUUID();
localStorage.setItem("session_id", sessionId);

/*  VIEW SWITCHING  */

function hideAll() {
    ["homeView", "uploadView", "askView"].forEach(id =>
        document.getElementById(id).classList.add("hidden")
    );
}

function goHome() {
    hideAll();
    document.getElementById("homeView").classList.remove("hidden");
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

/*  BOOT  */

document.addEventListener("DOMContentLoaded", () => {
    if (!getToken()) {
        document.getElementById("tokenGate").classList.remove("hidden");
    } else {
        document.getElementById("homeView").classList.remove("hidden");
    }
});

/*  UPLOAD  */

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

        if (!res.ok) {
            const err = await res.json();
            document.getElementById("uploadResult").innerText =
                err.detail || "Failed to ingest URL";
            return;
        }

        const data = await res.json();
        handleUploadSuccess(data);
    }
}


async function handleUploadSuccess(data) {
    document.getElementById("uploadResult").innerText =
        JSON.stringify(data, null, 2);

    // Use document_id directly from backend
    if (data.document_id) {
        uploadedDocumentId = data.document_id;
        document.getElementById("postUploadAsk").classList.remove("hidden");
    }
}


/*  ASK ON UPLOADED DOC  */

async function askOnUploadedDoc() {
    const query = document.getElementById("docQuery").value;

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            query,
            session_id: sessionId,
            hf_token: getToken(),
            document_id: uploadedDocumentId
        })
    });

    const data = await res.json();
    document.getElementById("docAnswer").innerText = data.answer || "";
}

/*  ASK (GLOBAL / DOCUMENT)  */


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

    const payload = {
        query: document.getElementById("queryText").value,
        session_id: sessionId,
        hf_token: getToken()
    };

    if (mode === "document") {
        payload.document_id = document.getElementById("documentList").value;
    }

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    document.getElementById("answer").innerText = data.answer || "";

    if (mode === "global") {
        document.getElementById("introspection").innerHTML = `
            <strong>Coverage:</strong> ${data.coverage ?? "N/A"}<br>
            <strong>Path taken:</strong> ${data.path_taken ?? "N/A"}
        `;
        document.getElementById("sources").innerText =
            (data.sources || []).join("\\n");
    }
}

function onUploadTypeChange() {
    const type = document.getElementById("uploadType").value;
    document.getElementById("uploadFile").classList.toggle("hidden", type === "url");
    document.getElementById("uploadUrl").classList.toggle("hidden", type === "file");
}
</script>

</body>
</html>
"""
