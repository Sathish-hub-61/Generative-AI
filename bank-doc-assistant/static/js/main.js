/* ==========================================================================
   Verity - Shared JavaScript (Theme & Settings)
   ========================================================================== */

// ===== Theme Management =====
function applyTheme(theme) {
  const isLight = theme === 'light';
  document.body.classList.toggle('light', isLight);
  
  const themeBtn = document.getElementById('themeBtn');
  if (themeBtn) {
    themeBtn.textContent = isLight ? '🌙' : '☀';
  }
  
  const mBtn = document.getElementById('modalThemeBtn');
  if (mBtn) {
    mBtn.textContent = isLight ? 'Switch to Dark' : 'Switch to Light';
  }
}

function toggleTheme() {
  const next = document.body.classList.contains('light') ? 'dark' : 'light';
  localStorage.setItem('verity_theme', next);
  applyTheme(next);
}

// Initialize theme immediately
applyTheme(localStorage.getItem('verity_theme') || 'dark');

// ===== Settings Modal Management =====
async function openSettings() {
  const modal = document.getElementById('settingsModal');
  if (!modal) return;
  modal.classList.add('open');
  
  const msgEl = document.getElementById('settingMsg');
  if (msgEl) msgEl.textContent = '';

  try {
    const res = await fetch('/api/settings');
    const s = await res.json();
    
    const keyEl = document.getElementById('setApiKey');
    if (keyEl) {
      keyEl.textContent = s.api_key_configured ? '✅ Configured' : '⚠ Not set (fallback)';
      keyEl.style.color = s.api_key_configured ? 'var(--success-text)' : 'var(--warning-text)';
    }
    
    const urlEl = document.getElementById('setBaseUrl');
    if (urlEl) urlEl.textContent = s.base_url || '-';
    
    const countEl = document.getElementById('setCacheCount');
    if (countEl) countEl.textContent = s.cached_entries ?? '0';
  } catch (e) {
    if (msgEl) msgEl.textContent = 'Could not load settings.';
  }
}

function closeSettings() {
  const modal = document.getElementById('settingsModal');
  if (modal) modal.classList.remove('open');
}

async function clearCache() {
  const msgEl = document.getElementById('settingMsg');
  try {
    const res = await fetch('/api/clear-cache', { method: 'POST' });
    const data = await res.json();
    
    const countEl = document.getElementById('setCacheCount');
    if (countEl) countEl.textContent = '0';
    if (msgEl) {
      msgEl.textContent = data.message || 'Cache cleared successfully.';
      msgEl.style.color = 'var(--success-text)';
    }
  } catch (e) {
    if (msgEl) {
      msgEl.textContent = 'Failed to clear cache.';
      msgEl.style.color = 'var(--danger-text)';
    }
  }
}
