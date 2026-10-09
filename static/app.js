const mode = document.body.dataset.mode;
const clock = document.getElementById('clock');
if (clock) {
  const update = () => { clock.textContent = new Date().toLocaleString('en-GB', { timeZone: 'Asia/Karachi' }) + ' PKT'; };
  update(); setInterval(update, 1000);
}
const preview = document.getElementById('note-preview');
if (preview) {
  const render = () => {
    let note;
    try { note = decodeURIComponent(location.hash.slice(1)); } catch { note = 'Invalid note encoding'; }
    // Deliberate vulnerable sink versus a text-only DOM update.
    if (mode === 'vulnerable') preview.innerHTML = note;
    else preview.textContent = note;
  };
  document.getElementById('preview-note').addEventListener('click', () => {
    location.hash = encodeURIComponent(document.getElementById('note-input').value);
    render();
  });
  window.addEventListener('hashchange', render); render();
}
