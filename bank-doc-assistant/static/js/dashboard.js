/* ==========================================================================
   Verity - Dashboard JavaScript
   ========================================================================== */

let _currentResults = null;

// ===== Client-side File Downloads =====
function triggerDownload(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function exportCsv() {
  if (!_currentResults || !_currentResults.dictionary || !_currentResults.dictionary.length) return;
  const cols = ['Field', 'Observed type', 'Missing %', 'Distinct', 'Example values', 'Documented meaning', 'Source line', 'Status'];
  const esc = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
  const lines = [cols.map(esc).join(',')];
  _currentResults.dictionary.forEach(row => {
    lines.push(cols.map(c => esc(row[c])).join(','));
  });
  triggerDownload('data_dictionary.csv', lines.join('\r\n'), 'text/csv;charset=utf-8;');
}

function exportReport() {
  if (!_currentResults) return;
  const md = _currentResults.limitations_md || '# Limitations Report\n\nNo limitations detected.';
  triggerDownload('limitations_report.md', md, 'text/markdown;charset=utf-8;');
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function sendQuickQuery(text) {
  const input = document.getElementById('chatInput');
  if (!input) return;
  input.value = text;
  askAssistant();
}

async function askAssistant() {
  const input = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSendBtn');
  const box = document.getElementById('chatMessages');
  if (!input || !sendBtn || !box) return;

  const question = (input.value || '').trim();
  if (!question || !_currentResults) return;

  input.value = '';
  sendBtn.disabled = true;

  const userDiv = document.createElement('div');
  userDiv.className = 'msg msg-user';
  userDiv.textContent = question;
  box.appendChild(userDiv);

  const loadDiv = document.createElement('div');
  loadDiv.className = 'msg msg-ai';
  loadDiv.textContent = 'Analyzing dataset context…';
  box.appendChild(loadDiv);
  box.scrollTop = box.scrollHeight;

  try {
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        context: {
          summary: _currentResults.summary,
          dictionary: _currentResults.dictionary,
          findings: _currentResults.findings,
        },
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      loadDiv.textContent = data.error || 'Error answering query.';
    } else {
      loadDiv.innerHTML = escapeHtml(data.answer).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        + `<div class="msg-meta">Source: ${data.source || 'assistant'}</div>`;
    }
  } catch (e) {
    loadDiv.textContent = 'Network error: ' + e.message;
  } finally {
    sendBtn.disabled = false;
    box.scrollTop = box.scrollHeight;
  }
}

// ===== Initialize Dashboard =====
document.addEventListener('DOMContentLoaded', () => {
  const raw = sessionStorage.getItem('results');
  if (!raw) return;

  const R = JSON.parse(raw);
  _currentResults = R;

  const emptyState = document.getElementById('emptyState');
  if (emptyState) emptyState.style.display = 'none';

  const app = document.getElementById('app');
  if (!app) return;

  // ---- Header + Toolbar ----
  app.innerHTML = `
  <div class="dash-header">
    <div>
      <h2>Dashboard</h2>
      <div class="file-info">${R.summary.total_rows.toLocaleString()} rows · ${R.summary.total_fields} columns · API calls: ${R.summary.api_calls}</div>
    </div>
    <div class="toolbar">
      <button type="button" onclick="exportCsv()">↓ Export CSV</button>
      <button type="button" onclick="exportReport()">↓ Export Report</button>
      <button type="button" onclick="sessionStorage.clear();location.href='/'">🗑 Clear data</button>
    </div>
  </div>

  <!-- STAT CARDS -->
  <div class="stat-row">
    <div class="stat-card">
      <div class="label">Total Fields</div>
      <div class="value">${R.summary.total_fields}</div>
      <div class="meta">${R.summary.total_rows.toLocaleString()} rows in dataset</div>
    </div>
    <div class="stat-card">
      <div class="label">Documented</div>
      <div class="value" style="color:var(--success-text)">${R.summary.documented}</div>
      <div class="meta">Fields with documentation matched</div>
    </div>
    <div class="stat-card">
      <div class="label">Undocumented</div>
      <div class="value" style="color:var(--warning-text)">${R.summary.undocumented}</div>
      <div class="meta">Meaning not inferred (Code gate)</div>
    </div>
    <div class="stat-card">
      <div class="label">Issues Found</div>
      <div class="value" style="color:${R.summary.issues > 0 ? 'var(--danger-text)' : 'var(--text-primary)'}">${R.summary.issues}</div>
      <div class="meta">Across all quality rules</div>
    </div>
  </div>

  <!-- TABS -->
  <div class="tabs">
    <button class="tab-btn active" data-tab="dict">📋 Dictionary</button>
    <button class="tab-btn" data-tab="lim">⚠ Limitations</button>
    <button class="tab-btn" data-tab="guard">🛡 Guardrail Check</button>
    <button class="tab-btn" data-tab="ai">🤖 AI Assistant</button>
    <button class="tab-btn" data-tab="viz">📊 Visualizations</button>
  </div>

  <div class="tab-content active" id="tab-dict"></div>
  <div class="tab-content" id="tab-lim"></div>
  <div class="tab-content" id="tab-guard"></div>
  <div class="tab-content" id="tab-ai"></div>
  <div class="tab-content" id="tab-viz"></div>
  `;

  // ---- Tab 1: Dictionary Table ----
  let tableHtml = '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Type</th><th>Missing %</th><th>Distinct</th><th>Example Values</th><th>Documented Meaning</th><th>Source Line</th><th>Status</th></tr></thead><tbody>';
  R.dictionary.forEach(r => {
    const badge = r.Status === 'Documented'
      ? '<span class="badge badge-green">Documented</span>'
      : '<span class="badge badge-amber">Undocumented – not inferred</span>';
    tableHtml += '<tr>'
      + '<td style="color:var(--text-primary);font-weight:600">' + escapeHtml(r.Field) + '</td>'
      + '<td><span class="badge badge-blue">' + escapeHtml(r['Observed type']) + '</span></td>'
      + '<td>' + escapeHtml(r['Missing %']) + '</td>'
      + '<td>' + escapeHtml(r.Distinct) + '</td>'
      + '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis" title="' + escapeHtml(r['Example values']) + '">' + escapeHtml(r['Example values']) + '</td>'
      + '<td style="max-width:320px;line-height:1.5">' + escapeHtml(r['Documented meaning']) + '</td>'
      + '<td style="font-size:11px;color:var(--text-dim);max-width:220px;overflow:hidden;text-overflow:ellipsis" title="' + escapeHtml(r['Source line']) + '">' + escapeHtml(r['Source line']) + '</td>'
      + '<td>' + badge + '</td>'
      + '</tr>';
  });
  tableHtml += '</tbody></table></div>';

  if (R.unparsed_lines && R.unparsed_lines.length) {
    tableHtml += '<details style="margin-top:16px;font-size:13px;color:var(--text-muted)"><summary style="cursor:pointer;color:var(--primary-500);font-weight:600">Unparsed documentation lines (' + R.unparsed_lines.length + ')</summary><pre style="margin-top:8px;padding:14px;background:var(--bg-canvas);border:1px solid var(--border-subtle);border-radius:var(--radius-sm);overflow-x:auto;color:var(--text-secondary)">' + escapeHtml(R.unparsed_lines.join('\n')) + '</pre></details>';
  }
  document.getElementById('tab-dict').innerHTML = tableHtml;

  // ---- Tab 2: Limitations Findings ----
  let limHtml = '';
  if (!R.findings || R.findings.length === 0) {
    limHtml = '<div class="finding"><p style="color:var(--success-text)">No limitations detected.</p></div>';
  } else {
    R.findings.forEach((f, i) => {
      const sevClass = f.severity === 'high' ? 'sev-high' : f.severity === 'medium' ? 'sev-medium' : 'sev-low';
      limHtml += '<div class="finding">'
        + '<div class="finding-header"><span class="finding-title">' + (i + 1) + '. ' + escapeHtml(f.title) + '</span><span class="severity ' + sevClass + '">' + escapeHtml(f.severity) + '</span><span class="badge badge-gray">' + escapeHtml(f.rule_id) + '</span></div>'
        + '<details><summary>Evidence &amp; Measurements</summary><p>' + escapeHtml(f.evidence) + '</p></details>'
        + '</div>';
    });
  }
  document.getElementById('tab-lim').innerHTML = limHtml;

  // ---- Tab 3: Guardrail Check ----
  let guardHtml = '';
  if (R.violations && R.violations.length > 0) {
    R.violations.forEach(v => {
      let cls = 'guard-pass', icon = '✅';
      if (v.status === 'FAIL') { cls = 'guard-fail'; icon = '❌'; }
      else if (v.status === 'SKIP') { cls = 'guard-skip'; icon = '⏭'; }
      guardHtml += '<div class="guard-item ' + cls + '"><span class="guard-icon">' + icon + '</span><div><strong>' + escapeHtml(v.field) + '</strong> &nbsp;–&nbsp; ' + escapeHtml(v.check) + ': <span style="color:var(--text-muted)">' + escapeHtml(v.detail) + '</span></div></div>';
    });
  } else {
    guardHtml = '<p style="color:var(--success-text);padding:20px;font-weight:600">All guardrails passed successfully.</p>';
  }
  document.getElementById('tab-guard').innerHTML = guardHtml;

  // ---- Tab 4: AI Assistant (60% Chatbot / 40% Original Document Preview) ----
  document.getElementById('tab-ai').innerHTML = `
    <div class="ai-split-layout">
      <div class="ai-chat-panel">
        <div class="chat-box ai-chat-box">
          <div style="font-size:13px;color:var(--text-muted);line-height:1.5">
            Ask questions about this dataset's columns, statistics, or exact limitation locations. All responses are strictly grounded in observed data measurements and supplied documentation.
          </div>
          <div class="chat-chips">
            <button type="button" class="chip" onclick="sendQuickQuery('Summarize this dataset and its key limitations')">Summarize dataset &amp; limitations</button>
            <button type="button" class="chip" onclick="sendQuickQuery('Where do placeholder values and outliers occur in the dataset?')">Where do placeholders &amp; outliers occur?</button>
            <button type="button" class="chip" onclick="sendQuickQuery('Show min, max, and mean for all numeric columns')">Numeric column stats</button>
            <button type="button" class="chip" onclick="sendQuickQuery('Which columns are undocumented?')">Undocumented columns</button>
          </div>
          <div class="chat-messages" id="chatMessages">
            <div class="msg msg-ai">Hello! I have loaded the statistical profile, data dictionary, and ${R.summary.issues} limitation findings for your ${R.summary.total_rows.toLocaleString()}-row dataset. How can I assist you with this dataset?</div>
          </div>
          <div class="chat-input-row">
            <input type="text" id="chatInput" placeholder="Ask about any column, statistic, or limitation location..." onkeydown="if(event.key==='Enter')askAssistant()">
            <button type="button" class="chat-send" id="chatSendBtn" onclick="askAssistant()">Send</button>
          </div>
        </div>
      </div>

      <div class="ai-split-divider" aria-hidden="true"></div>

      <div class="ai-doc-panel">
        <div class="doc-preview-header">
          <div class="doc-title-group">
            <span class="doc-panel-label">Original Document</span>
            <div class="doc-file-meta">
              <span id="docPreviewFilename" class="doc-filename" title="">No document uploaded</span>
              <span id="docPreviewBadge" class="badge badge-blue" style="display:none"></span>
            </div>
          </div>
          <div class="doc-toolbar-actions">
            <div id="docPdfControls" class="doc-pdf-controls" style="display:none">
              <span id="docPageCount" class="doc-page-count"></span>
              <button type="button" class="doc-ctrl-btn" onclick="zoomDocPreview(-0.15)" title="Zoom out">−</button>
              <span id="docZoomPct" class="doc-zoom-pct">100%</span>
              <button type="button" class="doc-ctrl-btn" onclick="zoomDocPreview(0.15)" title="Zoom in">+</button>
              <button type="button" class="doc-ctrl-btn" onclick="resetDocZoom()" title="Reset zoom">Fit</button>
            </div>
            <div id="docCsvModeControls" class="doc-pdf-controls" style="display:none">
              <button type="button" class="doc-ctrl-btn active" id="csvModeTableBtn" onclick="setCsvViewMode('table')">Table</button>
              <button type="button" class="doc-ctrl-btn" id="csvModeRawBtn" onclick="setCsvViewMode('raw')">Raw</button>
            </div>
            <input type="file" id="docPreviewUploadInput" accept=".csv,.xlsx,.xls,.pdf,.docx,.txt,.md,.markdown" hidden onchange="handlePreviewFileUpload(this)">
            <button type="button" class="doc-upload-btn" onclick="document.getElementById('docPreviewUploadInput').click()" title="Upload CSV, XLSX, PDF, DOCX, TXT, or MD to preview">↑ Upload</button>
            <a id="docDownloadBtn" href="/api/document/download" class="doc-download-btn" style="display:none" download>↓ Download</a>
          </div>
        </div>
        <div id="docPreviewBody" class="doc-preview-body">
          <div class="doc-empty-state">Upload a document to preview it here.</div>
        </div>
      </div>
    </div>
  `;

  if (typeof initDocPreview === 'function') {
    initDocPreview(R);
  }

  // ---- Initialize Visualizations ----
  if (typeof initVisualizations === 'function') {
    initVisualizations(R);
  }

  // ---- Tab Switching ----
  function activateTab(tabName) {
    const btn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
    const target = document.getElementById('tab-' + tabName);
    if (!btn || !target) return;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    target.classList.add('active');
    if (tabName === 'viz' && typeof activateVisualizationsTab === 'function') {
      activateVisualizationsTab();
    }
    if (tabName === 'ai' && typeof activateDocPreviewTab === 'function') {
      activateDocPreviewTab();
    }
  }

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => activateTab(btn.dataset.tab));
  });

  if (window.location.hash === '#viz' || new URLSearchParams(window.location.search).get('tab') === 'viz') {
    activateTab('viz');
  }
});
