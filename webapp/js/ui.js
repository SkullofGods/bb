/* Мелкие помощники разметки */
(function (global) {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function el(html) {
    var t = document.createElement('template');
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  }

  function tiles(items) {
    return '<div class="grid g2">' + items.map(function (i) {
      return '<button class="tile accent-' + (i.accent || 'teal') + '" data-href="' + esc(i.href) + '">' +
        '<i>' + i.icon + '</i><b>' + esc(i.title) + '</b>' +
        (i.sub ? '<span>' + esc(i.sub) + '</span>' : '') + '</button>';
    }).join('') + '</div>';
  }

  function unitCard(e, group) {
    var img = e.img
      ? '<img src="' + esc(e.img) + '" alt="" loading="lazy">'
      : '<div class="ph">🏝️</div>';
    return '<button class="unit" data-href="#/p/' + esc(group) + '/' + esc(e.id) + '">' +
      img + '<b>' + esc(e.ru) + '</b><span>' + esc(e.en) + '</span></button>';
  }

  function unitGrid(list, group) {
    if (!list.length) return '<div class="empty"><i>🏝️</i>Пусто</div>';
    return '<div class="unit-grid">' + list.map(function (e) { return unitCard(e, group); }).join('') + '</div>';
  }

  function rowItem(o) {
    return '<button class="row" data-href="' + esc(o.href) + '">' +
      (o.img ? '<img src="' + esc(o.img) + '" alt="" loading="lazy">' : '') +
      '<span class="rt"><b>' + esc(o.title) + '</b>' +
      (o.sub ? '<span>' + esc(o.sub) + '</span>' : '') + '</span>' +
      '<span class="chev">›</span></button>';
  }

  function table(headers, rows, opts) {
    opts = opts || {};
    var h = '<div class="tablewrap"><table><thead><tr>' +
      headers.map(function (x) { return '<th>' + esc(x) + '</th>'; }).join('') +
      '</tr></thead><tbody>' +
      rows.map(function (r, i) {
        var cls = (opts.hl != null && opts.hl === i) ? ' class="hl"' : '';
        return '<tr' + cls + '>' + r.map(function (c) {
          return '<td class="num">' + esc(c) + '</td>';
        }).join('') + '</tr>';
      }).join('') +
      '</tbody></table></div>';
    return h;
  }

  function seg(items, active, attr) {
    return '<div class="seg">' + items.map(function (i) {
      return '<button ' + (attr || 'data-seg') + '="' + esc(i.v) + '"' +
        (i.v === active ? ' class="on"' : '') + '>' + esc(i.t) + '</button>';
    }).join('') + '</div>';
  }

  function secTitle(t, more) {
    return '<div class="sec-title"><span>' + esc(t) + '</span>' +
      (more ? '<span class="more" data-href="' + esc(more.href) + '">' + esc(more.title) + ' ›</span>' : '') +
      '</div>';
  }

  function chips(pairs) {
    return '<div class="chips">' + pairs.map(function (p) {
      return '<span class="chip">' + esc(p[0]) + ' <b>' + esc(p[1]) + '</b></span>';
    }).join('') + '</div>';
  }

  function accordion(title, bodyHtml, open) {
    return '<details class="acc"' + (open ? ' open' : '') + '><summary>' + esc(title) + '</summary>' +
      '<div class="acc-body">' + bodyHtml + '</div></details>';
  }

  function bullets(lines) {
    return '<ul>' + lines.map(function (l) { return '<li>' + esc(l) + '</li>'; }).join('') + '</ul>';
  }

  function num(v) {
    if (v == null) return '—';
    return String(v).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  /* Нижняя шторка */
  var sheetEl = null, sheetBody = null;
  function sheet(html) {
    sheetEl = sheetEl || document.getElementById('sheet');
    sheetBody = sheetBody || document.getElementById('sheet-body');
    sheetBody.innerHTML = html;
    sheetEl.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function closeSheet() {
    if (!sheetEl) return;
    sheetEl.hidden = true;
    document.body.style.overflow = '';
  }

  /* Просмотр картинки */
  function lightbox(src, cap) {
    var lb = document.getElementById('lightbox');
    var img = document.getElementById('lb-img');
    img.src = src;
    img.classList.remove('rot');
    lb.classList.remove('rotated');
    document.getElementById('lb-cap').textContent = cap || '';
    lb.hidden = false;
    document.body.style.overflow = 'hidden';
  }
  function rotateLightbox() {
    var lb = document.getElementById('lightbox');
    var img = document.getElementById('lb-img');
    var on = img.classList.toggle('rot');
    lb.classList.toggle('rotated', on);
  }
  function closeLightbox() {
    var lb = document.getElementById('lightbox');
    if (lb) { lb.hidden = true; document.getElementById('lb-img').src = ''; }
    document.body.style.overflow = '';
  }

  function haptic(kind) {
    try {
      var h = global.Telegram && global.Telegram.WebApp && global.Telegram.WebApp.HapticFeedback;
      if (!h) return;
      if (kind === 'sel') h.selectionChanged(); else h.impactOccurred(kind || 'light');
    } catch (e) { /* не критично */ }
  }

  global.UI = {
    esc: esc, el: el, tiles: tiles, unitGrid: unitGrid, unitCard: unitCard,
    rowItem: rowItem, table: table, seg: seg, secTitle: secTitle, chips: chips,
    accordion: accordion, bullets: bullets, num: num,
    sheet: sheet, closeSheet: closeSheet,
    lightbox: lightbox, closeLightbox: closeLightbox, rotateLightbox: rotateLightbox,
    haptic: haptic
  };
})(window);
