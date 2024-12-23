window.addEventListener('load', function() {
  // Load remaining icons after page load
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = '/static/tabler-icons.min.css';
  document.head.appendChild(link);
});