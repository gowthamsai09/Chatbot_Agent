from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>RAG Knowledge Assistant</title>
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
        textarea, select {
            width: 100%;
            margin-top: 6px;
        }
        pre {
            background: #f2f2f2;
            padding: 10px;
            margin-top: 10px;

            white-space: pre-wrap;      /* Wrap long lines */
            word-wrap: break-word;      /* Break very long words */
            overflow-wrap: break-word;  /* Modern equivalent */
        }
    </style>
</head>

<body>

<h1>RAG + Agent Knowledge Assistant</h1>

<h3>1️ Index PDF Documents</h3>
<button type="button" onclick="ingest()">Index All PDFs</button>
<pre id="ingestResult"></pre>

<hr>

<h3>2️ What does this model know?</h3>
<button type="button" onclick="loadKnowledge()">Show Indexed Knowledge</button>
<pre id="knowledgeResult"></pre>

<hr>

<h3>3️ Ask a Question</h3>

<textarea id="queryText" rows="4" placeholder="Ask something..."></textarea>

<select id="domain">
    <option value="">All domains</option>
    <option value="foundations">Foundations</option>
    <option value="rag">RAG</option>
    <option value="agents">Agents</option>
</select>

<br><br>
<button type="button" onclick="ask()">Ask</button>

<h4>Answer</h4>
<pre id="answer"></pre>

<h4>Agent Introspection</h4>
<div id="introspection" style="
    background:#eef;
    padding:10px;
    margin-top:10px;
    border-radius:6px;
    font-family:monospace;
"></div>

<h4>Sources</h4>
<pre id="sources"></pre>

<script>
async function ingest() {
    console.log("Ingest clicked");
    const res = await fetch('/api/ingest/all', { method: 'POST' });
    const data = await res.json();
    document.getElementById('ingestResult').innerText =
        JSON.stringify(data, null, 2);
}

async function loadKnowledge() {
    console.log("Knowledge clicked");
    const res = await fetch('/api/knowledge');
    const data = await res.json();
    document.getElementById('knowledgeResult').innerText =
        JSON.stringify(data, null, 2);
}

async function ask() {
    console.log("Ask clicked");
    const query = document.getElementById('queryText').value;
    const domain = document.getElementById('domain').value;

    const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, domain })
    });

    const data = await res.json();

    document.getElementById("answer").innerText = data.answer;
    document.getElementById("introspection").innerHTML = `
    <strong>Coverage:</strong> ${data.coverage ?? "N/A"}<br>
    <strong>Path taken:</strong> ${data.path_taken ?? "N/A"}
    `;

    document.getElementById('sources').innerText =
        (data.sources || []).join('\\n');
}
</script>

</body>
</html>
"""