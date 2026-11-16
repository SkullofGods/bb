/* Загрузка и кэш данных + общий поиск */
(function (global) {
  'use strict';

  var cache = Object.create(null);
  var pending = Object.create(null);

  function load(name) {
    if (cache[name]) return Promise.resolve(cache[name]);
    if (pending[name]) return pending[name];
    // Папка называется content, а не data: на хостинге папка data особая
    // (персистентный том), файлы приложения из неё не отдаются.
    pending[name] = fetch('content/' + name + '.json', { cache: 'no-cache' })
      .then(function (r) {
        if (!r.ok) throw new Error('Не удалось загрузить ' + name + ' (' + r.status + ')');
        return r.json();
      })
      .then(function (j) { cache[name] = j; delete pending[name]; return j; })
      .catch(function (e) { delete pending[name]; throw e; });
    return pending[name];
  }

  function loadAll(names) { return Promise.all(names.map(load)); }

  /* Разделы каталога: какие файлы и как называются */
  var CATALOG = [
    { key: 'troops',         title: 'Войска',             icon: '🪖', accent: 'teal' },
    { key: 'proto_troops',   title: 'Прототипы войск',    icon: '🧪', accent: 'purple' },
    { key: 'defenses',       title: 'Оборона',            icon: '🛡️', accent: 'red' },
    { key: 'proto_defenses', title: 'Оборонные прототипы', icon: '⚡', accent: 'blue' },
    { key: 'heroes',         title: 'Герои',              icon: '🎖️', accent: 'gold' },
    { key: 'buildings',      title: 'Постройки',          icon: '🏗️', accent: 'teal' },
    { key: 'gunboat',        title: 'Канонерка',          icon: '🚤', accent: 'blue' },
    { key: 'meta',           title: 'Справочник',         icon: '📚', accent: 'gold' }
  ];

  var ALL_KEYS = CATALOG.map(function (c) { return c.key; });

  function catalogOf(key) {
    for (var i = 0; i < CATALOG.length; i++) if (CATALOG[i].key === key) return CATALOG[i];
    return { key: key, title: key, icon: '•', accent: 'teal' };
  }

  function find(group, id) {
    var arr = cache[group];
    if (!arr) return null;
    for (var i = 0; i < arr.length; i++) if (arr[i].id === id) return arr[i];
    return null;
  }

  var index = null;

  function buildIndex() {
    if (index) return Promise.resolve(index);
    return loadAll(ALL_KEYS.concat(['ops', 'guide', 'bases'])).then(function () {
      index = [];
      ALL_KEYS.forEach(function (k) {
        (cache[k] || []).forEach(function (e) {
          index.push({
            kind: 'entry', group: k, id: e.id,
            title: e.ru, sub: e.en, extra: e.groupRu || '',
            img: e.img, href: '#/p/' + k + '/' + e.id
          });
        });
      });
      (cache.ops ? cache.ops.ops : []).forEach(function (o) {
        index.push({
          kind: 'op', title: o.ru, sub: 'Операция ' + o.n + ' · ' + o.en,
          extra: o.note || '', href: '#/op/' + o.n
        });
      });
      (cache.bases || []).forEach(function (b) {
        index.push({
          kind: 'base', title: b.name, sub: 'Силовая база операций',
          extra: 'база схема', href: '#/base/' + b.id
        });
      });
      (cache.guide ? cache.guide.articles : []).forEach(function (a) {
        index.push({
          kind: 'article', title: a.title, sub: a.sub,
          extra: (a.tags || []).join(' '), href: '#/guide/' + a.id
        });
      });
      return index;
    });
  }

  function norm(s) { return (s || '').toString().toLowerCase().replace(/ё/g, 'е'); }

  function search(q) {
    var n = norm(q).trim();
    if (!n || !index) return [];
    var parts = n.split(/\s+/);
    var out = [];
    for (var i = 0; i < index.length; i++) {
      var it = index[i];
      var hay = norm(it.title + ' ' + it.sub + ' ' + it.extra);
      var ok = true, score = 0;
      for (var p = 0; p < parts.length; p++) {
        var at = hay.indexOf(parts[p]);
        if (at < 0) { ok = false; break; }
        score += at === 0 ? 3 : (hay.indexOf(' ' + parts[p]) >= 0 ? 2 : 1);
      }
      if (ok) { it._s = score + (norm(it.title).indexOf(parts[0]) === 0 ? 5 : 0); out.push(it); }
    }
    out.sort(function (a, b) { return b._s - a._s; });
    return out.slice(0, 60);
  }

  global.DB = {
    load: load, loadAll: loadAll, cache: cache, find: find,
    CATALOG: CATALOG, ALL_KEYS: ALL_KEYS, catalogOf: catalogOf,
    buildIndex: buildIndex, search: search
  };
})(window);
