/* MediQueue — Core JavaScript */

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.mq-flash').forEach(el => {
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(20px)';
      el.style.transition = 'all .4s';
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });
});

// Card number formatting
const cardInput = document.getElementById('cardNumber');
if (cardInput) {
  cardInput.addEventListener('input', e => {
    let v = e.target.value.replace(/\D/g,'').slice(0,16);
    e.target.value = v.match(/.{1,4}/g)?.join(' ') || v;
  });
}

// Expiry formatting
document.querySelectorAll('[name="card_expiry"]').forEach(el => {
  el.addEventListener('input', e => {
    let v = e.target.value.replace(/\D/g,'').slice(0,4);
    if (v.length > 2) v = v.slice(0,2) + '/' + v.slice(2);
    e.target.value = v;
  });
});

// File upload label update
document.querySelectorAll('input[type="file"]').forEach(input => {
  input.addEventListener('change', e => {
    const file   = e.target.files[0];
    const label  = input.previousElementSibling;
    if (file && label && label.classList.contains('mq-file-label')) {
      label.textContent = '✅ ' + file.name;
      label.style.color = '#2D9E6B';
    }
  });
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const target = document.querySelector(a.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// Confirm dangerous actions
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', e => {
    if (!confirm(el.dataset.confirm)) e.preventDefault();
  });
});