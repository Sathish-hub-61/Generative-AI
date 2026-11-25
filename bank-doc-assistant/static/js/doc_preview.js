/* ==========================================================================
   Verity - Original Document Preview Panel (Right 40% of AI Assistant)
   Supports PDF (PDF.js), DOCX (docx-preview), CSV/XLSX/XLS (SheetJS), and raw TXT/MD.
   ========================================================================== */

let _docMeta = null;
let _docRendered = false;
let _pdfDoc = null;
let _pdfScale = 1.0;
let _pdfRenderToken = 0;

let _workbook = null;
let _activeSheetName = null;
let _csvRawText = null;
let _csvViewMode = 'table';
const _SHEET_PAGE_SIZE = 300;

function _docEscape(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function _setPdfControlsVisible(visible) {
  const ctrl = document.getElementById('docPdfControls');
  if (ctrl) ctrl.style.display = visible ? 'flex' : 'none';
}

function _setCsvModeControlsVisible(visible) {
  const ctrl = document.getElementById('docCsvModeControls');
  if (ctrl) ctrl.style.display = visible ? 'flex' : 'none';
  const tBtn = document.getElementById('csvModeTableBtn');
  const rBtn = document.getElementById('csvModeRawBtn');
  if (tBtn) tBtn.classList.toggle('active', _csvViewMode === 'table');
  if (rBtn) rBtn.classList.toggle('active', _csvViewMode === 'raw');
}

function _updateZoomLabel() {
  const lbl = document.getElementById('docZoomPct');
  if (lbl) lbl.textContent = Math.round(_pdfScale * 100) + '%';
}

async function _renderPdfPages() {
  const viewportEl = document.getElementById('docPreviewBody');
  if (!viewportEl || !_pdfDoc) return;

  const token = ++_pdfRenderToken;
  const pagesHost = document.createElement('div');
  pagesHost.className = 'doc-pdf-pages';
  viewportEl.innerHTML = '';
  viewportEl.appendChild(pagesHost);

  const availWidth = Math.max(260, viewportEl.clientWidth - 28);
  const dpr = Math.min(window.devicePixelRatio || 1, 2);

  for (let pageNum = 1; pageNum <= _pdfDoc.numPages; pageNum++) {
    if (token !== _pdfRenderToken) return;
    const page = await _pdfDoc.getPage(pageNum);
    const baseVp = page.getViewport({ scale: 1 });
    const fitScale = availWidth / baseVp.width;
    const effectiveScale = fitScale * _pdfScale;
    const vp = page.getViewport({ scale: effectiveScale });

    const pageWrap = document.createElement('div');
    pageWrap.className = 'doc-pdf-page-wrap';

    const canvas = document.createElement('canvas');
    canvas.className = 'doc-pdf-canvas';
    canvas.width = Math.floor(vp.width * dpr);
    canvas.height = Math.floor(vp.height * dpr);
    canvas.style.width = Math.floor(vp.width) + 'px';
    canvas.style.height = Math.floor(vp.height) + 'px';

    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const badge = document.createElement('div');
    badge.className = 'doc-page-num';
    badge.textContent = `Page ${pageNum} of ${_pdfDoc.numPages}`;

    pageWrap.appendChild(canvas);
    pageWrap.appendChild(badge);
    pagesHost.appendChild(pageWrap);

    await page.render({ canvasContext: ctx, viewport: vp }).promise;
  }
}

function zoomDocPreview(delta) {
  if (!_pdfDoc) return;
  _pdfScale = Math.min(2.5, Math.max(0.5, Number((_pdfScale + delta).toFixed(2))));
  _updateZoomLabel();
  _renderPdfPages();
}

function resetDocZoom() {
  if (!_pdfDoc) return;
  _pdfScale = 1.0;
  _updateZoomLabel();
  _renderPdfPages();
}

function _renderSpreadsheetView(viewportEl) {
  if (!_workbook || !_activeSheetName) return;

  if (_csvRawText !== null && _csvViewMode === 'raw') {
    const pre = document.createElement('pre');
    pre.className = 'doc-raw-pre';
    pre.textContent = _csvRawText;
    viewportEl.innerHTML = '';
    viewportEl.appendChild(pre);
    return;
  }

  const sheet = _workbook.Sheets[_activeSheetName];
  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });

  viewportEl.innerHTML = '';

  // Sheet tabs if workbook has multiple sheets (e.g., XLSX/XLS)
  if (_workbook.SheetNames.length > 1) {
    const tabsBar = document.createElement('div');
    tabsBar.className = 'doc-sheet-tabs';
    _workbook.SheetNames.forEach(name => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'doc-sheet-tab' + (name === _activeSheetName ? ' active' : '');
      btn.textContent = name;
      btn.onclick = () => {
        _activeSheetName = name;
        _renderSpreadsheetView(viewportEl);
      };
      tabsBar.appendChild(btn);
    });
    viewportEl.appendChild(tabsBar);
  }

  if (!rows.length) {
    const empty = document.createElement('div');
    empty.className = 'doc-empty-state';
    empty.textContent = 'This sheet is empty.';
    viewportEl.appendChild(empty);
    return;
  }

  const maxCols = rows.reduce((m, r) => Math.max(m, r.length), 0);
  const headerRow = rows[0] || [];
  const dataRows = rows.slice(1);

  const infoBar = document.createElement('div');
  infoBar.className = 'doc-sheet-meta';
  viewportEl.appendChild(infoBar);

  const tableWrap = document.createElement('div');
  tableWrap.className = 'doc-table-wrap';
  const table = document.createElement('table');
  table.className = 'doc-sheet-table';

  const thead = document.createElement('thead');
  const headTr = document.createElement('tr');
  const idxTh = document.createElement('th');
  idxTh.textContent = '#';
  headTr.appendChild(idxTh);
  for (let c = 0; c < maxCols; c++) {
    const th = document.createElement('th');
    th.textContent = headerRow[c] !== undefined && headerRow[c] !== '' ? String(headerRow[c]) : `Col ${c + 1}`;
    headTr.appendChild(th);
  }
  thead.appendChild(headTr);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  table.appendChild(tbody);
  tableWrap.appendChild(table);
  viewportEl.appendChild(tableWrap);

  const loadBar = document.createElement('div');
  loadBar.className = 'doc-load-more-bar';
  viewportEl.appendChild(loadBar);

  let renderedCount = 0;

  function appendRows(limit) {
    const end = Math.min(dataRows.length, renderedCount + limit);
    const frag = document.createDocumentFragment();
    for (let i = renderedCount; i < end; i++) {
      const tr = document.createElement('tr');
      const numTd = document.createElement('td');
      numTd.className = 'doc-row-idx';
      numTd.textContent = String(i + 1);
      tr.appendChild(numTd);
      const r = dataRows[i] || [];
      for (let c = 0; c < maxCols; c++) {
        const td = document.createElement('td');
        td.textContent = r[c] !== undefined && r[c] !== null ? String(r[c]) : '';
        tr.appendChild(td);
      }
      frag.appendChild(tr);
    }
    tbody.appendChild(frag);
    renderedCount = end;
    infoBar.textContent = `Showing ${renderedCount.toLocaleString()} of ${dataRows.length.toLocaleString()} rows · ${maxCols} columns`;

    if (renderedCount < dataRows.length) {
      const remaining = dataRows.length - renderedCount;
      const step = Math.min(_SHEET_PAGE_SIZE, remaining);
      loadBar.innerHTML = '';
      const moreBtn = document.createElement('button');
      moreBtn.type = 'button';
      moreBtn.className = 'doc-ctrl-btn doc-load-more-btn';
      moreBtn.textContent = `Load ${step} more rows (${remaining.toLocaleString()} remaining)`;
      moreBtn.onclick = () => appendRows(_SHEET_PAGE_SIZE);
      loadBar.appendChild(moreBtn);
      loadBar.style.display = 'flex';
    } else {
      loadBar.style.display = 'none';
    }
  }

  appendRows(_SHEET_PAGE_SIZE);
}

function setCsvViewMode(mode) {
  _csvViewMode = mode === 'raw' ? 'raw' : 'table';
  _setCsvModeControlsVisible(true);
  const viewportEl = document.getElementById('docPreviewBody');
  if (viewportEl && _workbook) {
    _renderSpreadsheetView(viewportEl);
  }
}

async function handlePreviewFileUpload(input) {
  if (!input || !input.files || !input.files.length) return;
  const file = input.files[0];
  const viewportEl = document.getElementById('docPreviewBody');
  if (viewportEl) {
    viewportEl.innerHTML = '<div class="doc-loading">Uploading original file for preview…</div>';
  }

  const fd = new FormData();
  fd.append('file', file);

  try {
    const res = await fetch('/api/document/upload', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin',
    });
    const data = await res.json();
    if (!res.ok) {
      if (viewportEl) {
        viewportEl.innerHTML = `<div class="doc-error-state">${_docEscape(data.error || 'Upload failed.')}</div>`;
      }
      return;
    }

    _docMeta = data;
    _docRendered = false;

    try {
      const raw = sessionStorage.getItem('results');
      if (raw) {
        const parsed = JSON.parse(raw);
        parsed.document = data;
        sessionStorage.setItem('results', JSON.stringify(parsed));
      }
    } catch (_) {}

    await renderDocumentPreview();
  } catch (err) {
    if (viewportEl) {
      viewportEl.innerHTML = `<div class="doc-error-state">Upload failed: ${_docEscape(err.message)}</div>`;
    }
  } finally {
    input.value = '';
  }
}

async function renderDocumentPreview() {
  const viewportEl = document.getElementById('docPreviewBody');
  const nameEl = document.getElementById('docPreviewFilename');
  const badgeEl = document.getElementById('docPreviewBadge');
  const dlBtn = document.getElementById('docDownloadBtn');
  if (!viewportEl) return;

  _workbook = null;
  _activeSheetName = null;
  _csvRawText = null;
  _setPdfControlsVisible(false);
  _setCsvModeControlsVisible(false);

  if (!_docMeta || !_docMeta.has_document) {
    if (nameEl) {
      nameEl.textContent = 'No document uploaded';
      nameEl.title = '';
    }
    if (badgeEl) badgeEl.style.display = 'none';
    if (dlBtn) dlBtn.style.display = 'none';
    viewportEl.innerHTML = '<div class="doc-empty-state">Upload a document to preview it here.</div>';
    _docRendered = true;
    return;
  }

  const ext = (_docMeta.ext || '').toLowerCase();
  if (nameEl) {
    nameEl.textContent = _docMeta.filename || 'Uploaded Document';
    nameEl.title = _docMeta.filename || '';
  }
  if (badgeEl) {
    badgeEl.style.display = 'inline-flex';
    badgeEl.textContent = ext.replace('.', '').toUpperCase() || 'FILE';
  }
  if (dlBtn) {
    dlBtn.style.display = 'inline-flex';
    dlBtn.setAttribute('href', '/api/document/download');
    dlBtn.setAttribute('download', _docMeta.filename || 'document');
  }

  viewportEl.innerHTML = '<div class="doc-loading">Loading original document preview…</div>';

  try {
    if (ext === '.pdf') {
      if (typeof pdfjsLib === 'undefined') {
        throw new Error('PDF.js viewer library failed to load.');
      }
      pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/vendor/pdf.worker.min.js';
      const loadingTask = pdfjsLib.getDocument({ url: '/api/document/file', withCredentials: true });
      _pdfDoc = await loadingTask.promise;
      _pdfScale = 1.0;
      _updateZoomLabel();
      const pageCountEl = document.getElementById('docPageCount');
      if (pageCountEl) pageCountEl.textContent = `${_pdfDoc.numPages} ${_pdfDoc.numPages === 1 ? 'page' : 'pages'}`;
      _setPdfControlsVisible(true);
      await _renderPdfPages();
    } else if (ext === '.docx') {
      if (typeof window.docx === 'undefined' || typeof window.JSZip === 'undefined') {
        throw new Error('DOCX preview library failed to load.');
      }
      const res = await fetch('/api/document/file', { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Could not fetch uploaded DOCX file.');
      const buf = await res.arrayBuffer();
      const host = document.createElement('div');
      host.className = 'doc-docx-host';
      viewportEl.innerHTML = '';
      viewportEl.appendChild(host);
      await window.docx.renderAsync(buf, host, null, {
        className: 'docx',
        inWrapper: true,
        ignoreWidth: false,
        ignoreHeight: false,
        ignoreFonts: false,
        breakPages: true,
        renderHeaders: true,
        renderFooters: true,
        useBase64URL: true,
      });
    } else if (ext === '.xlsx' || ext === '.xls') {
      if (typeof XLSX === 'undefined') {
        throw new Error('SheetJS library failed to load.');
      }
      const res = await fetch('/api/document/file', { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Could not fetch uploaded Excel file.');
      const buf = await res.arrayBuffer();
      _workbook = XLSX.read(buf, { type: 'array' });
      _activeSheetName = _workbook.SheetNames[0];
      _csvRawText = null;
      _renderSpreadsheetView(viewportEl);
    } else if (ext === '.csv') {
      if (typeof XLSX === 'undefined') {
        throw new Error('SheetJS library failed to load.');
      }
      const res = await fetch('/api/document/file', { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Could not fetch uploaded CSV file.');
      const rawText = await res.text();
      _csvRawText = rawText;
      _csvViewMode = 'table';
      _workbook = XLSX.read(rawText, { type: 'string' });
      _activeSheetName = _workbook.SheetNames[0];
      _setCsvModeControlsVisible(true);
      _renderSpreadsheetView(viewportEl);
    } else if (ext === '.txt' || ext === '.md' || ext === '.markdown') {
      const res = await fetch('/api/document/file', { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Could not fetch uploaded text document.');
      const rawText = await res.text();
      const pre = document.createElement('pre');
      pre.className = 'doc-raw-pre';
      pre.textContent = rawText;
      viewportEl.innerHTML = '';
      viewportEl.appendChild(pre);
    } else {
      viewportEl.innerHTML = `<div class="doc-empty-state">Preview is not supported for ${_docEscape(ext || 'this file type')}. Use the Download button above to open the original file.</div>`;
    }
    _docRendered = true;
  } catch (err) {
    viewportEl.innerHTML = `<div class="doc-error-state">Unable to render preview: ${_docEscape(err.message)}</div>`;
  }
}

function activateDocPreviewTab() {
  if (!_docRendered) {
    renderDocumentPreview();
  }
}

async function initDocPreview(results) {
  _docRendered = false;
  _pdfDoc = null;
  _docMeta = (results && results.document) ? results.document : null;

  if (!_docMeta) {
    try {
      const res = await fetch('/api/document/meta', { credentials: 'same-origin' });
      if (res.ok) _docMeta = await res.json();
    } catch (_) {}
  }

  const tabAi = document.getElementById('tab-ai');
  if (tabAi && tabAi.classList.contains('active')) {
    renderDocumentPreview();
  }
}
