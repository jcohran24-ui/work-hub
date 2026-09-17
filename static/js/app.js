function openQuickActions() {
  const modal = document.getElementById('quickModal');
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
}
function closeQuickActions() {
  const modal = document.getElementById('quickModal');
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
}
function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2200);
}
function showNotConnected(name) {
  showToast(name + ' is ready for its app URL.');
}
function quickAction(action) {
  closeQuickActions();
  showToast(action + ' quick action placeholder created.');
}
document.addEventListener('click', (e) => {
  const modal = document.getElementById('quickModal');
  if (e.target === modal) closeQuickActions();
});
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/static/service-worker.js'));
}
