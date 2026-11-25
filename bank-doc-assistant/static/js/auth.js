/* ==========================================================================
   Verity - Authentication Client Script (Login & Registration)
   ========================================================================== */

function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input || !btn) return;
  const show = input.type === 'password';
  input.type = show ? 'text' : 'password';
  btn.textContent = show ? 'Hide' : 'Show';
  btn.setAttribute('aria-pressed', show ? 'true' : 'false');
}

function setAuthAlert(msg, type) {
  const el = document.getElementById('authAlert');
  if (!el) return;
  if (!msg) {
    el.className = 'auth-alert';
    el.textContent = '';
    return;
  }
  el.className = 'auth-alert ' + type;
  el.textContent = msg;
}

function setSubmitting(btnId, spinnerId, loading, labelText) {
  const btn = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  const label = btn ? btn.querySelector('.btn-label') : null;
  if (btn) btn.disabled = loading;
  if (spinner) spinner.style.display = loading ? 'inline-block' : 'none';
  if (label && labelText) label.textContent = labelText;
}

function openForgotModal() {
  const modal = document.getElementById('forgotModal');
  if (!modal) return;
  modal.classList.add('open');
  const msg = document.getElementById('forgotMsg');
  if (msg) {
    msg.textContent = '';
    msg.style.color = '';
  }
  const loginEmail = document.getElementById('loginEmail');
  const forgotEmail = document.getElementById('forgotEmail');
  if (loginEmail && forgotEmail && loginEmail.value.trim()) {
    forgotEmail.value = loginEmail.value.trim();
  }
}

function closeForgotModal() {
  const modal = document.getElementById('forgotModal');
  if (modal) modal.classList.remove('open');
}

async function submitForgotPassword(e) {
  e.preventDefault();
  const emailEl = document.getElementById('forgotEmail');
  const msgEl = document.getElementById('forgotMsg');
  const email = (emailEl ? emailEl.value : '').trim();
  if (!email || !email.includes('@')) {
    if (msgEl) {
      msgEl.textContent = 'Please enter a valid email address.';
      msgEl.style.color = 'var(--danger-text)';
    }
    return;
  }
  try {
    const res = await fetch('/api/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    const data = await res.json();
    if (msgEl) {
      msgEl.textContent = data.message || data.error || 'Request processed.';
      msgEl.style.color = res.ok ? 'var(--success-text)' : 'var(--danger-text)';
    }
  } catch (err) {
    if (msgEl) {
      msgEl.textContent = 'Network error: ' + err.message;
      msgEl.style.color = 'var(--danger-text)';
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    const params = new URLSearchParams(window.location.search);
    if (params.get('registered') === '1') {
      setAuthAlert('Account created successfully! Sign in with your email and password.', 'success');
    } else if (params.get('logged_out') === '1') {
      setAuthAlert('You have been signed out safely.', 'success');
    }

    loginForm.addEventListener('submit', async e => {
      e.preventDefault();
      setAuthAlert('', '');

      const emailInput = document.getElementById('loginEmail');
      const pwInput = document.getElementById('loginPassword');
      const rememberInput = document.getElementById('rememberMe');

      const email = (emailInput.value || '').trim();
      const password = pwInput.value || '';

      emailInput.classList.remove('invalid');
      pwInput.classList.remove('invalid');

      if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        emailInput.classList.add('invalid');
        setAuthAlert('Please enter a valid email address.', 'error');
        emailInput.focus();
        return;
      }
      if (!password) {
        pwInput.classList.add('invalid');
        setAuthAlert('Please enter your password.', 'error');
        pwInput.focus();
        return;
      }

      setSubmitting('loginBtn', 'loginSpinner', true, 'Signing in…');
      try {
        const res = await fetch('/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify({
            email,
            password,
            remember: Boolean(rememberInput && rememberInput.checked),
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          setAuthAlert(data.error || 'Invalid email or password.', 'error');
          setSubmitting('loginBtn', 'loginSpinner', false, 'Login');
          return;
        }
        window.location.href = data.redirect || '/dashboard';
      } catch (err) {
        setAuthAlert('Network error: ' + err.message, 'error');
        setSubmitting('loginBtn', 'loginSpinner', false, 'Login');
      }
    });
  }

  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', async e => {
      e.preventDefault();
      setAuthAlert('', '');

      const nameInput = document.getElementById('regName');
      const emailInput = document.getElementById('regEmail');
      const pwInput = document.getElementById('regPassword');
      const confirmInput = document.getElementById('regConfirmPassword');

      [nameInput, emailInput, pwInput, confirmInput].forEach(el => el && el.classList.remove('invalid'));

      const fullName = (nameInput.value || '').trim();
      const email = (emailInput.value || '').trim();
      const password = pwInput.value || '';
      const confirmPassword = confirmInput.value || '';

      if (fullName.length < 2) {
        nameInput.classList.add('invalid');
        setAuthAlert('Full name must be at least 2 characters.', 'error');
        nameInput.focus();
        return;
      }
      if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        emailInput.classList.add('invalid');
        setAuthAlert('Please enter a valid email address.', 'error');
        emailInput.focus();
        return;
      }
      if (password.length < 6) {
        pwInput.classList.add('invalid');
        setAuthAlert('Password must be at least 6 characters long.', 'error');
        pwInput.focus();
        return;
      }
      if (password !== confirmPassword) {
        confirmInput.classList.add('invalid');
        setAuthAlert('Passwords do not match.', 'error');
        confirmInput.focus();
        return;
      }

      setSubmitting('registerBtn', 'registerSpinner', true, 'Creating account…');
      try {
        const res = await fetch('/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
          body: JSON.stringify({
            full_name: fullName,
            email,
            password,
            confirm_password: confirmPassword,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          setAuthAlert(data.error || 'Could not create account.', 'error');
          setSubmitting('registerBtn', 'registerSpinner', false, 'Create Account');
          return;
        }
        window.location.href = data.redirect || '/login?registered=1';
      } catch (err) {
        setAuthAlert('Network error: ' + err.message, 'error');
        setSubmitting('registerBtn', 'registerSpinner', false, 'Create Account');
      }
    });
  }
});
