/* ==========================================================================
   Verity - Upload Page JavaScript
   ========================================================================== */

function setupDrop(dropId, inputId, infoId, nameId) {
  const drop = document.getElementById(dropId);
  const input = document.getElementById(inputId);
  const info = document.getElementById(infoId);
  const nameEl = document.getElementById(nameId);

  if (!drop || !input || !info || !nameEl) return;

  ['dragenter', 'dragover'].forEach(e => {
    drop.addEventListener(e, ev => {
      ev.preventDefault();
      drop.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(e => {
    drop.addEventListener(e, ev => {
      ev.preventDefault();
      drop.classList.remove('dragover');
    });
  });

  drop.addEventListener('drop', ev => {
    if (ev.dataTransfer.files && ev.dataTransfer.files.length) {
      input.files = ev.dataTransfer.files;
      showFile(input, info, nameEl);
    }
  });

  input.addEventListener('change', () => showFile(input, info, nameEl));
}

function showFile(input, info, nameEl) {
  if (input.files && input.files.length) {
    nameEl.textContent = '📄 ' + input.files[0].name + ' (' + formatSize(input.files[0].size) + ')';
    info.classList.add('show');
    hideStatus();
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function clearFile(type) {
  const input = document.getElementById(type + 'Input');
  const info = document.getElementById(type + 'Info');
  if (input) input.value = '';
  if (info) info.classList.remove('show');
}

function clearAll() {
  clearFile('csv');
  clearFile('doc');
  const targetCol = document.getElementById('targetCol');
  if (targetCol) targetCol.value = '';
  hideStatus();
}

function showStatus(msg, type) {
  const s = document.getElementById('statusBar');
  if (!s) return;
  s.className = 'status-bar ' + type;
  s.textContent = msg;
}

function hideStatus() {
  const s = document.getElementById('statusBar');
  if (!s) return;
  s.className = 'status-bar';
  s.textContent = '';
}

// Initialize Dropzone
document.addEventListener('DOMContentLoaded', () => {
  setupDrop('csvDrop', 'csvInput', 'csvInfo', 'csvName');
  setupDrop('docDrop', 'docInput', 'docInfo', 'docName');

  const form = document.getElementById('mainForm');
  if (!form) return;

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    const btn = document.getElementById('submitBtn');
    const spinner = document.getElementById('spinner');
    const csvInput = document.getElementById('csvInput');

    if (!csvInput.files || !csvInput.files.length) {
      showStatus('Please upload a CSV dataset to proceed.', 'error');
      return;
    }

    btn.disabled = true;
    if (spinner) spinner.style.display = 'inline-block';
    showStatus('Processing dataset & validating guardrails… This may take a moment.', 'info');

    const fd = new FormData(this);

    try {
      const resp = await fetch('/api/process', { method: 'POST', body: fd });
      const data = await resp.json();
      
      if (!resp.ok) {
        showStatus(data.error || 'Server processing error occurred.', 'error');
        return;
      }

      sessionStorage.setItem('results', JSON.stringify(data));
      window.location.href = '/dashboard';
    } catch (err) {
      showStatus('Network error: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      if (spinner) spinner.style.display = 'none';
    }
  });
});
