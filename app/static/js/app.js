// AI Code Reviewer Frontend Logic
let currentReview = null;
let currentSamples = {};

// DOM Elements
const codeInput = document.getElementById("codeInput");
const languageSelect = document.getElementById("languageSelect");
const sampleSelect = document.getElementById("sampleSelect");
const fileUpload = document.getElementById("fileUpload");
const btnReview = document.getElementById("btnReview");
const btnReviewSpinner = document.getElementById("btnReviewSpinner");
const btnReviewText = document.getElementById("btnReviewText");
const activeFilterBadge = document.getElementById("activeFilterBadge");

// Settings Elements
const aiProviderSelect = document.getElementById("aiProviderSelect");
const apiKeyInput = document.getElementById("apiKeyInput");
const modelNameInput = document.getElementById("modelNameInput");
const ollamaUrlInput = document.getElementById("ollamaUrlInput");
const currentAiBadge = document.getElementById("currentAiBadge");

// Initialize on Load
document.addEventListener("DOMContentLoaded", async () => {
    loadSettings();
    await loadSamples();
    setupEventListeners();
    updateCursorInfo();
});

function loadSettings() {
    const savedProvider = localStorage.getItem("ai_provider") || "built-in";
    const savedApiKey = localStorage.getItem("ai_api_key") || "";
    const savedModel = localStorage.getItem("ai_model") || "";
    const savedOllama = localStorage.getItem("ai_ollama_url") || "http://localhost:11434";

    if (aiProviderSelect) aiProviderSelect.value = savedProvider;
    if (apiKeyInput) apiKeyInput.value = savedApiKey;
    if (modelNameInput) modelNameInput.value = savedModel;
    if (ollamaUrlInput) ollamaUrlInput.value = savedOllama;

    updateBadgeUI(savedProvider);
}

function saveSettings() {
    localStorage.setItem("ai_provider", aiProviderSelect.value);
    localStorage.setItem("ai_api_key", apiKeyInput.value);
    localStorage.setItem("ai_model", modelNameInput.value);
    localStorage.setItem("ai_ollama_url", ollamaUrlInput.value);
    updateBadgeUI(aiProviderSelect.value);
    closeModal("settingsModal");
}

function updateBadgeUI(provider) {
    if (!currentAiBadge) return;
    const providerNames = {
        "built-in": "Built-in Smart Engine",
        "gemini": "Google Gemini",
        "openai": "OpenAI",
        "ollama": "Ollama Local",
        "groq": "Groq AI"
    };
    currentAiBadge.textContent = providerNames[provider] || provider;
}

async function loadSamples() {
    try {
        const res = await fetch("/api/samples");
        if (res.ok) {
            currentSamples = await res.json();
            // Load Python by default
            if (currentSamples["python"] && !codeInput.value) {
                codeInput.value = currentSamples["python"];
                updateLineNumbers();
            }
        }
    } catch (e) {
        console.warn("Could not load samples:", e);
    }
}

function setupEventListeners() {
    // Language change - preserves user's code if they typed custom code!
    languageSelect.addEventListener("change", (e) => {
        const lang = e.target.value;
        const currentCode = codeInput.value.trim();
        const isKnownSample = Object.values(currentSamples).some(s => s.trim() === currentCode);
        
        // Only switch code to sample if editor is empty or currently holds a sample
        if (!currentCode || isKnownSample) {
            if (currentSamples[lang]) {
                sampleSelect.value = lang;
                codeInput.value = currentSamples[lang];
                updateLineNumbers();
            }
        }
    });

    // Sample selection
    sampleSelect.addEventListener("change", (e) => {
        const lang = e.target.value;
        if (currentSamples[lang]) {
            languageSelect.value = (lang === "c" || lang === "cpp") ? "cpp" : lang;
            codeInput.value = currentSamples[lang];
            updateLineNumbers();
            codeInput.scrollTop = 0;
            const lineNumContainer = document.getElementById("lineNumbers");
            if (lineNumContainer) lineNumContainer.scrollTop = 0;
        }
    });

    // Synchronize vertical scroll between editor and line numbers
    codeInput.addEventListener("scroll", () => {
        const lineNumContainer = document.getElementById("lineNumbers");
        if (lineNumContainer) {
            lineNumContainer.scrollTop = codeInput.scrollTop;
        }
    });

    // File Upload
    fileUpload.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append("file", file);
        formData.append("ai_provider", localStorage.getItem("ai_provider") || "built-in");
        formData.append("api_key", localStorage.getItem("ai_api_key") || "");
        formData.append("model_name", localStorage.getItem("ai_model") || "");
        formData.append("ollama_url", localStorage.getItem("ai_ollama_url") || "http://localhost:11434");

        setLoading(true);
        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });
            if (!res.ok) {
                const err = await res.json();
                alert(`Upload review error: ${err.detail || "Review failed"}`);
                return;
            }
            const data = await res.json();
            currentReview = data;
            codeInput.value = data.original_code;
            languageSelect.value = data.language;
            updateLineNumbers();
            renderReviewResults(data);
        } catch (err) {
            alert(`File upload failed: ${err.message}`);
        } finally {
            setLoading(false);
        }
    });

    // Code input tab key support & line tracking
    codeInput.addEventListener("keydown", (e) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const start = codeInput.selectionStart;
            const end = codeInput.selectionEnd;
            codeInput.value = codeInput.value.substring(0, start) + "    " + codeInput.value.substring(end);
            codeInput.selectionStart = codeInput.selectionEnd = start + 4;
        }
    });

    codeInput.addEventListener("input", () => {
        updateLineNumbers();
        updateCursorInfo();
    });

    codeInput.addEventListener("click", updateCursorInfo);
    codeInput.addEventListener("keyup", updateCursorInfo);

    // Run Review Button
    btnReview.addEventListener("click", runReview);
}

function updateLineNumbers() {
    const lines = (codeInput.value.match(/\n/g) || []).length + 1;
    const lineNumContainer = document.getElementById("lineNumbers");
    if (lineNumContainer) {
        let nums = "";
        for (let i = 1; i <= lines; i++) {
            nums += `${i}\n`;
        }
        lineNumContainer.textContent = nums;
    }
}

function updateCursorInfo() {
    const pos = codeInput.selectionStart;
    const lines = codeInput.value.substring(0, pos).split("\n");
    const currentLine = lines.length;
    const currentCol = lines[lines.length - 1].length + 1;
    const totalLines = codeInput.value.split("\n").length;
    
    const cursorIndicator = document.getElementById("cursorIndicator");
    if (cursorIndicator) {
        cursorIndicator.textContent = `Ln ${currentLine}, Col ${currentCol} | Total ${totalLines} lines`;
    }
}

async function runReview() {
    const code = codeInput.value;
    if (!code.trim()) {
        alert("Please enter or upload some source code to review.");
        return;
    }

    setLoading(true);
    const payload = {
        code: code,
        language: languageSelect.value,
        filename: `code.${languageSelect.value}`,
        ai_provider: localStorage.getItem("ai_provider") || "built-in",
        api_key: localStorage.getItem("ai_api_key") || null,
        model_name: localStorage.getItem("ai_model") || null,
        ollama_url: localStorage.getItem("ai_ollama_url") || "http://localhost:11434",
        run_ai_deep_review: true
    };

    try {
        const res = await fetch("/api/review", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Review failed: ${err.detail || res.statusText}`);
            return;
        }

        const data = await res.json();
        currentReview = data;
        renderReviewResults(data);
    } catch (err) {
        alert(`Request failed: ${err.message}`);
    } finally {
        setLoading(false);
    }
}

function setLoading(isLoading) {
    if (isLoading) {
        btnReview.disabled = true;
        btnReviewSpinner.classList.remove("hidden");
        btnReviewText.textContent = "Analyzing Code...";
    } else {
        btnReview.disabled = false;
        btnReviewSpinner.classList.add("hidden");
        btnReviewText.textContent = "Run AI Review";
    }
}

function renderReviewResults(data) {
    // Show Results Container
    document.getElementById("emptyStatePanel").classList.add("hidden");
    document.getElementById("resultsPanel").classList.remove("hidden");

    // Quality Score & Grade
    const qs = data.quality_score;
    const scoreVal = document.getElementById("scoreValue");
    const gradeBadge = document.getElementById("gradeBadge");
    
    scoreVal.textContent = qs.overall_score;
    gradeBadge.textContent = `Grade ${qs.grade}`;

    // Grade colors
    gradeBadge.className = "px-3 py-1 rounded-full text-sm font-bold ";
    if (qs.grade.startsWith("A")) {
        gradeBadge.className += "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40";
    } else if (qs.grade === "B") {
        gradeBadge.className += "bg-blue-500/20 text-blue-400 border border-blue-500/40";
    } else if (qs.grade === "C") {
        gradeBadge.className += "bg-amber-500/20 text-amber-400 border border-amber-500/40";
    } else if (qs.grade === "D") {
        gradeBadge.className += "bg-orange-500/20 text-orange-400 border border-orange-500/40";
    } else {
        gradeBadge.className += "bg-rose-500/20 text-rose-400 border border-rose-500/40";
    }

    // Sub-scores
    document.getElementById("scoreSecurity").textContent = `${qs.security_score}%`;
    document.getElementById("scoreReliability").textContent = `${qs.reliability_score}%`;
    document.getElementById("scoreMaintainability").textContent = `${qs.maintainability_score}%`;
    document.getElementById("scorePerformance").textContent = `${qs.performance_score}%`;

    // Metrics
    const m = data.metrics;
    document.getElementById("metricComplexity").textContent = m.cyclomatic_complexity;
    document.getElementById("metricSloc").textContent = m.sloc;
    document.getElementById("metricMI").textContent = `${m.maintainability_index}`;
    document.getElementById("metricBugs").textContent = m.estimated_bugs;

    // Issue Counts & Filters
    const sev = data.issue_counts_by_severity;
    const cat = data.issue_counts_by_category || {};
    const syntaxCount = data.issues.filter(i => (i.category && i.category.toLowerCase().includes("syntax"))).length;

    document.getElementById("countAll").textContent = data.issues.length;
    const filterAllCount = document.getElementById("filterAllCount");
    if (filterAllCount) filterAllCount.textContent = data.issues.length;

    const countSyntaxEl = document.getElementById("countSyntax");
    if (countSyntaxEl) countSyntaxEl.textContent = syntaxCount;

    document.getElementById("countCritical").textContent = sev.Critical || 0;
    document.getElementById("countHigh").textContent = sev.High || 0;
    document.getElementById("countMedium").textContent = sev.Medium || 0;
    document.getElementById("countLow").textContent = sev.Low || 0;
    document.getElementById("execTimeBadge").textContent = `${data.execution_time_ms} ms`;

    // Toggle Syntax Alert Banner
    const syntaxBanner = document.getElementById("syntaxAlertBanner");
    const syntaxMsg = document.getElementById("syntaxAlertMessage");
    if (syntaxBanner) {
        if (syntaxCount > 0) {
            syntaxBanner.classList.remove("hidden");
            if (syntaxMsg) syntaxMsg.textContent = `${syntaxCount} syntax violation(s) detected. Code will fail compilation or execution until resolved.`;
        } else {
            syntaxBanner.classList.add("hidden");
        }
    }

    // Render Issues List
    renderIssuesList(data.issues);

    // Render Corrected Code
    document.getElementById("correctedCodeText").textContent = data.corrected_code;
    
    // Render Unified Diff
    renderUnifiedDiff(data.unified_diff);

    // Render AI Insights
    const aiContainer = document.getElementById("aiInsightsContainer");
    if (data.ai_insights) {
        aiContainer.innerHTML = formatMarkdown(data.ai_insights);
    } else {
        aiContainer.innerHTML = "<p class='text-slate-400'>No AI insights available.</p>";
    }
}

function renderIssuesList(issues, filterMode = "all") {
    const container = document.getElementById("issuesListContainer");
    container.innerHTML = "";

    let filtered = issues;
    if (filterMode === "syntax") {
        filtered = issues.filter(i => (i.category && i.category.toLowerCase().includes("syntax")));
    } else if (filterMode !== "all") {
        filtered = issues.filter(i => i.severity.toLowerCase() === filterMode.toLowerCase());
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="p-8 text-center bg-slate-900/50 rounded-lg border border-slate-800">
                <span class="text-3xl">🎉</span>
                <p class="text-slate-300 font-semibold mt-2">No matching issues found!</p>
                <p class="text-slate-500 text-xs">Code passes all checks in this category.</p>
            </div>
        `;
        return;
    }

    filtered.forEach(issue => {
        const card = document.createElement("div");
        card.className = "bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition rounded-lg p-4 space-y-2";
        
        const sevClass = `badge-${issue.severity.toLowerCase()}`;
        const lineText = issue.line_number ? `Line ${issue.line_number}` : "File Level";

        card.innerHTML = `
            <div class="flex items-start justify-between gap-2">
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="px-2 py-0.5 rounded text-xs font-semibold ${sevClass}">${issue.severity}</span>
                    <span class="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 border border-slate-700">${issue.category}</span>
                    <span class="text-xs text-slate-400 font-mono">${issue.rule_id}</span>
                </div>
                <span class="text-xs text-blue-400 font-mono bg-blue-950/40 px-2 py-0.5 rounded border border-blue-800/40 cursor-pointer" onclick="highlightLine(${issue.line_number})">
                    📍 ${lineText}
                </span>
            </div>
            <h4 class="font-semibold text-slate-100 text-sm">${issue.title}</h4>
            <p class="text-xs text-slate-400 leading-relaxed">${issue.description}</p>
            ${issue.code_snippet ? `<pre class="font-mono text-xs bg-black/40 text-slate-300 p-2.5 rounded border border-slate-800 overflow-x-auto"><code>${escapeHtml(issue.code_snippet)}</code></pre>` : ""}
            ${issue.suggestion ? `<div class="bg-blue-950/20 border-l-2 border-blue-500 p-2 text-xs text-blue-200">💡 <strong>Suggested Fix:</strong> ${issue.suggestion}</div>` : ""}
        `;
        container.appendChild(card);
    });
}

function filterIssues(severity) {
    if (!currentReview) return;
    renderIssuesList(currentReview.issues, severity);

    // Update active tab buttons
    document.querySelectorAll(".filter-btn").forEach(btn => {
        if (btn.dataset.filter === severity) {
            btn.classList.add("bg-blue-600", "text-white");
            btn.classList.remove("bg-slate-800", "text-slate-400");
        } else {
            btn.classList.remove("bg-blue-600", "text-white");
            btn.classList.add("bg-slate-800", "text-slate-400");
        }
    });
}

function renderUnifiedDiff(diffText) {
    const container = document.getElementById("unifiedDiffContainer");
    if (!diffText || diffText.trim() === "") {
        container.innerHTML = "<p class='text-slate-400 p-4'>No modifications needed. Code is optimal!</p>";
        return;
    }

    const lines = diffText.split("\n");
    let html = "<div class='font-mono text-xs'>";
    lines.forEach(line => {
        let cls = "text-slate-400";
        if (line.startsWith("+") && !line.startsWith("+++")) {
            cls = "diff-added px-1 rounded";
        } else if (line.startsWith("-") && !line.startsWith("---")) {
            cls = "diff-removed px-1 rounded";
        } else if (line.startsWith("@@")) {
            cls = "text-blue-400 font-bold";
        }
        html += `<div class="${cls}">${escapeHtml(line)}</div>`;
    });
    html += "</div>";
    container.innerHTML = html;
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.add("hidden"));
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("border-blue-500", "text-blue-400");
        btn.classList.add("border-transparent", "text-slate-400");
    });

    const targetTab = document.getElementById(tabId);
    if (targetTab) targetTab.classList.remove("hidden");

    const targetBtn = document.getElementById(`btn-${tabId}`);
    if (targetBtn) {
        targetBtn.classList.add("border-blue-500", "text-blue-400");
        targetBtn.classList.remove("border-transparent", "text-slate-400");
    }
}

function applyCorrectedCode() {
    if (!currentReview || !currentReview.corrected_code) return;
    codeInput.value = currentReview.corrected_code;
    updateLineNumbers();
    alert("Corrected code has been applied to the editor!");
}

function copyCorrectedCode() {
    if (!currentReview || !currentReview.corrected_code) return;
    navigator.clipboard.writeText(currentReview.corrected_code);
    alert("Corrected code copied to clipboard!");
}

function downloadCorrectedCode() {
    if (!currentReview) return;
    const filename = `corrected_${currentReview.filename || "code.txt"}`;
    downloadFile(filename, currentReview.corrected_code);
}

function downloadMarkdownReport() {
    if (!currentReview) return;
    window.open(`/api/export/${currentReview.id}/markdown`, "_blank");
}

function highlightLine(lineNum) {
    if (!lineNum) return;
    const lines = codeInput.value.split("\n");
    let charCount = 0;
    for (let i = 0; i < lineNum - 1 && i < lines.length; i++) {
        charCount += lines[i].length + 1;
    }
    codeInput.focus();
    codeInput.setSelectionRange(charCount, charCount + (lines[lineNum - 1] ? lines[lineNum - 1].length : 0));
}

// Modal and Drawer Controls
function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove("hidden");
    if (modalId === "historyDrawer") loadHistory();
    if (modalId === "analyticsModal") loadAnalytics();
}

function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add("hidden");
}

async function loadHistory() {
    const container = document.getElementById("historyListContainer");
    container.innerHTML = "<p class='text-slate-400 text-xs'>Loading history...</p>";
    try {
        const res = await fetch("/api/history");
        const data = await res.json();
        if (data.length === 0) {
            container.innerHTML = "<p class='text-slate-400 text-xs'>No past reviews recorded.</p>";
            return;
        }
        container.innerHTML = "";
        data.forEach(item => {
            const row = document.createElement("div");
            row.className = "p-3 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded flex items-center justify-between cursor-pointer";
            row.innerHTML = `
                <div onclick="loadPastReview('${item.id}')" class="flex-1">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-bold text-slate-200">${item.filename || "code"}</span>
                        <span class="text-xs text-blue-400 bg-blue-950 px-1.5 py-0.5 rounded font-mono">${item.language}</span>
                    </div>
                    <div class="text-[11px] text-slate-400 mt-1">
                        Score: <span class="font-bold text-white">${item.overall_score}%</span> (Grade ${item.grade}) • ${item.issues_count} issues • ${item.timestamp}
                    </div>
                </div>
                <button onclick="deletePastReview('${item.id}', event)" class="text-slate-500 hover:text-red-400 px-2 py-1 text-xs">🗑️</button>
            `;
            container.appendChild(row);
        });
    } catch (e) {
        container.innerHTML = `<p class='text-red-400 text-xs'>Failed to load history: ${e.message}</p>`;
    }
}

async function loadPastReview(reviewId) {
    try {
        const res = await fetch(`/api/history/${reviewId}`);
        if (!res.ok) throw new Error("Not found");
        const data = await res.json();
        currentReview = data;
        codeInput.value = data.original_code;
        languageSelect.value = data.language;
        updateLineNumbers();
        renderReviewResults(data);
        closeModal("historyDrawer");
    } catch (e) {
        alert("Failed to load review: " + e.message);
    }
}

async function deletePastReview(reviewId, event) {
    event.stopPropagation();
    if (!confirm("Are you sure you want to delete this review record?")) return;
    try {
        await fetch(`/api/history/${reviewId}`, { method: "DELETE" });
        loadHistory();
    } catch (e) {
        alert("Delete failed");
    }
}

async function loadAnalytics() {
    try {
        const res = await fetch("/api/analytics");
        const data = await res.json();
        const t = data.totals;
        document.getElementById("statTotalReviews").textContent = t.total_reviews || 0;
        document.getElementById("statAvgScore").textContent = `${Math.round(t.avg_score || 0)}%`;
        document.getElementById("statTotalIssues").textContent = t.total_issues || 0;
        document.getElementById("statCriticalIssues").textContent = t.total_critical || 0;
    } catch (e) {
        console.error("Analytics load failed:", e);
    }
}

// Helpers
function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatMarkdown(md) {
    if (!md) return "";
    if (typeof marked !== "undefined" && typeof marked.parse === "function") {
        try {
            return marked.parse(md);
        } catch (e) {
            console.warn("marked.parse error, using fallback:", e);
        }
    }
    return md
        .replace(/^### (.*$)/gim, '<h3 class="text-sm font-bold text-blue-400 mt-3 mb-1">$1</h3>')
        .replace(/^#### (.*$)/gim, '<h4 class="text-xs font-semibold text-slate-300 mt-2 mb-1">$1</h4>')
        .replace(/^\- (.*$)/gim, '<li class="ml-4 list-disc text-xs text-slate-300">$1</li>')
        .replace(/\*\*(.*?)\*\*/gim, '<strong class="text-white">$1</strong>')
        .replace(/`([^`]+)`/gim, '<code class="bg-black/40 text-blue-300 px-1 rounded text-[11px] font-mono">$1</code>')
        .replace(/\n/gim, '<br>');
}

function downloadFile(filename, content) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
