/* Роутер, вкладки и связка с Telegram */
(function (global) {
  'use strict';

  var tg = global.Telegram && global.Telegram.WebApp ? global.Telegram.WebApp : null;
  var view = document.getElementById('view');
  var titleEl = document.getElementById('topbar-title');
  var backBtn = document.getElementById('btn-back');
  var tabbar = document.getElementById('tabbar');

  var TABS = [
    { id: 'home', icon: '<svg viewBox="0 0 24 24"><path d="M4 11.5L12 4l8 7.5"/><path d="M6.5 10.5V20h11v-9.5"/></svg>', title: 'Главная', href: '#/' },
    { id: 'ops', icon: '<svg viewBox="0 0 24 24"><path d="M5 4l11.5 11.5"/><path d="M19 4L7.5 15.5"/><path d="M16.5 15.5L19.5 18.5"/><path d="M7.5 15.5L4.5 18.5"/><path d="M18 19.5l1.5-1.5"/><path d="M6 19.5L4.5 18"/></svg>', title: 'Операции', href: '#/ops' },
    { id: 'cat', icon: '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="7" height="7" rx="1.8"/><rect x="13" y="4" width="7" height="7" rx="1.8"/><rect x="4" y="13" width="7" height="7" rx="1.8"/><rect x="13" y="13" width="7" height="7" rx="1.8"/></svg>', title: 'Каталог', href: '#/cat/troops' },
    { id: 'gb', icon: '<svg viewBox="0 0 24 24"><path d="M3.5 14.5h17l-2.5 4.5H6z"/><path d="M12 14.5V5"/><path d="M12 6.5l5 4.5h-5"/></svg>', title: 'Канонерка', href: '#/gb' },
    { id: 'more', icon: '<svg viewBox="0 0 24 24"><path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h16"/></svg>', title: 'Ещё', href: '#/more' }
  ];

  var ROOT_HASHES = TABS.map(function (t) { return t.href; });
  var scrollMem = Object.create(null);
  var current = '';

  function renderTabs(active) {
    tabbar.innerHTML = TABS.map(function (t) {
      return '<button class="tab' + (t.id === active ? ' on' : '') + '" data-tab="' + t.id + '">' +
        '<i>' + t.icon + '</i><span>' + t.title + '</span></button>';
    }).join('');
    tabbar.querySelectorAll('[data-tab]').forEach(function (b) {
      b.onclick = function () {
        var t = TABS.filter(function (x) { return x.id === b.dataset.tab; })[0];
        UI.haptic('sel');
        go(t.href);
      };
    });
  }

  function parse(hash) {
    hash = (hash || '#/').replace(/^#/, '');
    var qi = hash.indexOf('?');
    var params = {};
    if (qi >= 0) {
      hash.slice(qi + 1).split('&').forEach(function (kv) {
        var p = kv.split('=');
        if (p[0]) params[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || '');
      });
      hash = hash.slice(0, qi);
    }
    var parts = hash.split('/').filter(Boolean);
    return { parts: parts, params: params };
  }

  function resolve(route) {
    var p = route.parts, q = route.params;
    if (!p.length || p[0] === 'home') return { tab: 'home', run: VIEWS.home };
    switch (p[0]) {
      case 'ops': return { tab: 'ops', run: function () { return VIEWS.ops(q); } };
      case 'op': return { tab: 'ops', run: function () { return VIEWS.operation(p[1]); } };
      case 'bases': return { tab: 'ops', run: VIEWS.bases };
      case 'base': return { tab: 'ops', run: function () { return VIEWS.base(p[1]); } };
      case 'cat': return { tab: 'cat', run: function () { return VIEWS.catalog(p[1] || 'troops'); } };
      case 'p': return { tab: null, run: function () { return VIEWS.detail(p[1], p[2]); } };
      case 'gb': return { tab: 'gb', run: VIEWS.gunboat };
      case 'calc': return { tab: 'gb', run: function () { return VIEWS.calcView(q); } };
      case 'statues': return { tab: 'more', run: VIEWS.statues };
      case 'guide': return { tab: 'more', run: function () { return VIEWS.guideArticle(p[1]); } };
      case 'faq': return { tab: 'more', run: VIEWS.faqView };
      case 'more': return { tab: 'more', run: VIEWS.more };
      case 'ai': return { tab: null, run: VIEWS.ai };
      case 'updates': return { tab: 'more', run: VIEWS.updates };
      case 'search': return { tab: null, run: function () { return VIEWS.searchView(q); } };
      default: return { tab: 'home', run: VIEWS.home };
    }
  }

  function render() {
    var hash = location.hash || '#/';
    if (current && current !== hash) scrollMem[current] = window.scrollY;
    current = hash;

    var route = parse(hash);
    var r = resolve(route);

    renderTabs(r.tab);
    var isRoot = ROOT_HASHES.indexOf(hash) >= 0 || hash === '#/' || hash === '';
    backBtn.classList.toggle('off', isRoot);
    if (tg && tg.BackButton) {
      try { isRoot ? tg.BackButton.hide() : tg.BackButton.show(); } catch (e) { /* старый клиент */ }
    }

    view.innerHTML = '<div class="skel"></div><div class="skel"></div><div class="skel"></div>';

    Promise.resolve()
      .then(r.run)
      .then(function (out) {
        if (location.hash !== hash && !(hash === '#/' && !location.hash)) return;
        titleEl.textContent = out.title || 'Опергруппа';
        view.innerHTML = out.html;
        if (out.after) out.after(view);
        var y = scrollMem[hash];
        window.scrollTo(0, y != null ? y : 0);
      })
      .catch(function (err) {
        view.innerHTML = '<div class="empty"><i>⚠️</i>' + UI.esc(err && err.message ? err.message : 'Ошибка загрузки') +
          '<div style="margin-top:12px"><button class="chip" onclick="location.reload()">Обновить</button></div></div>';
      });
  }

  function go(href, replace) {
    if (replace) {
      location.replace(href);
      render();
    } else if (location.hash === href) {
      render();
    } else {
      location.hash = href;
    }
  }

  function back() {
    var lb = document.getElementById('lightbox');
    var sh = document.getElementById('sheet');
    if (lb && !lb.hidden) { UI.closeLightbox(); return; }
    if (sh && !sh.hidden) { UI.closeSheet(); return; }
    if (history.length > 1) history.back();
    else go('#/');
  }

  /* делегирование: любой элемент с data-href ведёт по маршруту */
  document.addEventListener('click', function (ev) {
    var t = ev.target.closest('[data-href]');
    if (t) {
      ev.preventDefault();
      UI.haptic('light');
      var href = t.dataset.href;
      // маршрут приложения начинается с #, всё остальное — обычная ссылка
      if (href.charAt(0) === '#') go(href);
      else location.href = href;
      return;
    }
    if (ev.target.closest('[data-close]')) { UI.closeSheet(); return; }
    if (ev.target.closest('#lb-rot')) { UI.rotateLightbox(); return; }
    if (ev.target.closest('#lb-close') || ev.target.id === 'lightbox') { UI.closeLightbox(); return; }
  });

  backBtn.onclick = back;
  document.getElementById('btn-search').onclick = function () {
    UI.haptic('light');
    go('#/search');
  };

  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') { UI.closeSheet(); UI.closeLightbox(); }
  });

  window.addEventListener('hashchange', render);

  /* --- Telegram --- */
  /* вне Telegram SDK всегда отдаёт light — тогда слушаем системную тему */
  var inTelegram = !!(tg && tg.platform && tg.platform !== 'unknown');

  function applyTheme() {
    var scheme = (inTelegram && tg.colorScheme) ||
      (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    document.documentElement.dataset.theme = scheme === 'light' ? 'light' : 'dark';
    var meta = document.querySelector('meta[name=theme-color]');
    if (meta) meta.content = scheme === 'light' ? '#eef1f2' : '#101418';
  }

  if (tg) {
    try {
      tg.ready();
      tg.expand();
      if (tg.disableVerticalSwipes) tg.disableVerticalSwipes();
      if (tg.setHeaderColor) tg.setHeaderColor(tg.colorScheme === 'light' ? '#eef1f2' : '#101418');
      tg.onEvent('themeChanged', applyTheme);
      tg.onEvent('backButtonClicked', back);
    } catch (e) { /* открыто вне Telegram */ }
  }
  applyTheme();
  // addEventListener у matchMedia появился не везде: в старых webview
  // (в том числе внутри Telegram) есть только addListener
  try {
    var mq = matchMedia('(prefers-color-scheme: light)');
    if (mq.addEventListener) mq.addEventListener('change', applyTheme);
    else if (mq.addListener) mq.addListener(applyTheme);
  } catch (e) { /* тема просто не будет переключаться на лету */ }

  global.App = { go: go, back: back, render: render };

  if (!location.hash) location.replace('#/');
  render();
  DB.buildIndex().catch(function () { /* поиск подтянется позже */ });
})(window);
