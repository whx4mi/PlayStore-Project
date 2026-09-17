(() => {
  const FALLBACK_IMAGE = './fallback-app.svg';

  function applyImageFallback(image) {
    if (!(image instanceof HTMLImageElement) || image.dataset.fallbackReady) return;
    image.dataset.fallbackReady = 'true';
    image.addEventListener('error', () => {
      if (image.dataset.fallbackApplied) return;
      image.dataset.fallbackApplied = 'true';
      image.classList.add('image-fallback');
      image.src = FALLBACK_IMAGE;
      if (!image.alt) image.alt = 'Imagem indisponível';
    });
  }

  function prepareInteractiveItem(item) {
    if (item.dataset.keyboardReady) return;
    item.dataset.keyboardReady = 'true';
    item.tabIndex = item.tabIndex >= 0 ? item.tabIndex : 0;
    item.setAttribute('role', 'button');
    item.addEventListener('keydown', event => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      item.click();
    });
  }

  function prepare(root = document) {
    root.querySelectorAll?.('img').forEach(applyImageFallback);
    root.querySelectorAll?.('.game, .card').forEach(prepareInteractiveItem);
  }

  function notify(message) {
    if (typeof window.showToast === 'function') window.showToast(message);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const toast = document.getElementById('toast');
    if (toast) {
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      toast.setAttribute('aria-atomic', 'true');
    }

    prepare();
    new MutationObserver(records => {
      records.forEach(record => record.addedNodes.forEach(node => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          if (node.matches?.('img')) applyImageFallback(node);
          prepare(node);
        }
      }));
    }).observe(document.body, { childList: true, subtree: true });

    window.addEventListener('offline', () => notify('Você está offline. Alguns conteúdos podem não carregar.'));
    window.addEventListener('online', () => notify('Conexão restabelecida.'));
  });

  window.storeRuntime = {
    async checkFile(url, timeout = 8000) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);
      try {
        const response = await fetch(url, {
          method: 'HEAD',
          cache: 'no-store',
          signal: controller.signal
        });
        if (!response.ok) throw new Error(`Arquivo indisponível (${response.status})`);
        return response;
      } finally {
        clearTimeout(timer);
      }
    }
  };
})();
