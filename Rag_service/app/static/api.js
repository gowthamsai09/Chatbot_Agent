"use strict";

/*  session  */

function generateSessionId() {
    return 'xxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Initialise or restore session across page loads
let sessionId = localStorage.getItem('session_id');
if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem('session_id', sessionId);
}

/*  token helpers  */

function getStoredToken() {
    return localStorage.getItem('hf_token') || '';
}

function resolveTokenForApi() {
    const t = getStoredToken();
    return t === 'USE_ENV' ? '' : t;
}

/* TOKEN ENDPOINTS */

/**
 * POST /api/set-token
 * Sends the user-supplied HF token (or empty string for server pool) to the backend.
 * @param {string} token  — raw token string; empty string = use server pool
 * @returns {Promise<{status:string, message:string}>}
 */
async function apiSetToken(token) {
    const res = await fetch('/api/set-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hf_token: token }),
    });

    if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }

    return res.json();
}

/* UPLOAD ENDPOINTS */

/**
 * POST /api/upload  (multipart/form-data)
 * Ingests a file (PDF / DOCX / TXT).
 * @param {File}   file
 * @param {string} domain
 * @returns {Promise<object>}
 */
async function apiUploadFile(file, domain) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('domain', domain);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 60_000); // 60 s timeout

    try {
        const res = await fetch('/api/upload', {
            method: 'POST',
            body: formData,
            signal: controller.signal,
        });
        clearTimeout(timer);

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || err.message || `HTTP ${res.status}`);
        }

        return res.json();
    } catch (err) {
        clearTimeout(timer);
        throw err;
    }
}

/**
 * POST /api/upload/url
 * Ingests a web page by URL.
 * @param {string} url
 * @param {string} domain
 * @returns {Promise<object>}
 */
async function apiUploadUrl(url, domain) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 30_000); // 30 s timeout

    try {
        const res = await fetch('/api/upload/url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, domain }),
            signal: controller.signal,
        });
        clearTimeout(timer);

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || err.message || `HTTP ${res.status}`);
        }

        return res.json();
    } catch (err) {
        clearTimeout(timer);
        throw err;
    }
}

/* KNOWLEDGE / DOCUMENTS */

/**
 * GET /api/knowledge
 * Returns indexed documents and domains.
 * @returns {Promise<{documents: Object<string,string>, domains: string[]}>}
 */
async function apiGetKnowledge() {
    const res = await fetch('/api/knowledge');

    if (!res.ok) {
        throw new Error(`Failed to load knowledge base: HTTP ${res.status}`);
    }

    return res.json();
}

/* QUERY ENDPOINT */

/**
 * POST /api/query
 * Sends a question to the RAG / agent pipeline.
 * @param {string}      query
 * @param {string|null} documentId   — null = global mode
 * @returns {Promise<{answer:string, sources:string[], coverage:string, path_taken:string}>}
 */
async function apiQuery(query, documentId = null) {
    const payload = {
        query,
        session_id: sessionId,
        hf_token: resolveTokenForApi(),
    };

    if (documentId) {
        payload.document_id = documentId;
    }

    const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || `HTTP ${res.status}`);
    }

    return res.json();
}

/* EVAL ENDPOINTS */

/**
 * POST /api/eval/start
 * Kicks off an async evaluation job.
 * @param {string[]} questions
 * @returns {Promise<{job_id:string}>}
 */
async function apiEvalStart(questions) {
    const res = await fetch('/api/eval/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            test_questions: questions,
            session_id: sessionId,
            hf_token: resolveTokenForApi(),
        }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.message || `HTTP ${res.status}`);
    }

    return res.json();
}

/**
 * GET /api/eval/status/:job_id
 * Polls for eval job status.
 * @param {string} jobId
 * @returns {Promise<{status:string, result:object|null}>}
 */
async function apiEvalStatus(jobId) {
    const res = await fetch(`/api/eval/status/${jobId}`);

    if (!res.ok) {
        throw new Error(`Poll failed: HTTP ${res.status}`);
    }

    return res.json();
}

/**
 * Polls eval status every `intervalMs` ms until complete/failed/timeout.
 * Calls `onUpdate(data)` on each poll tick.
 * Returns a promise that resolves with the final result object.
 *
 * @param {string}   jobId
 * @param {Function} onUpdate       — called with raw status object each tick
 * @param {number}   intervalMs     — default 3000
 * @param {number}   maxWaitMs      — hard ceiling before giving up (default 130 s)
 * @returns {Promise<object>}        — final status data
 */
async function pollEvalUntilDone(jobId, onUpdate, intervalMs = 3000, maxWaitMs = 130_000) {
    const deadline = Date.now() + maxWaitMs;

    return new Promise((resolve, reject) => {
        const timer = setInterval(async () => {
            try {
                const data = await apiEvalStatus(jobId);
                onUpdate(data);

                const terminal = ['completed', 'failed', 'timeout', 'not_found'];
                if (terminal.includes(data.status)) {
                    clearInterval(timer);
                    resolve(data);
                    return;
                }

                if (Date.now() > deadline) {
                    clearInterval(timer);
                    reject(new Error('Evaluation polling timed out on client side'));
                }
            } catch (err) {
                clearInterval(timer);
                reject(err);
            }
        }, intervalMs);
    });
}
