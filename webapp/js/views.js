/* Экраны приложения. Каждый вид возвращает промис {title, html, after?} */
(function (global) {
  'use strict';

  var esc = UI.esc, num = UI.num;

  /* ======================= ГЛАВНАЯ ======================= */

  function home() {
    return DB.loadAll(['ops', 'guide']).then(function (res) {
      var ops = res[0].ops, guide = res[1];
      var hard = ops.filter(function (o) { return o.slang; }).slice(-5).reverse();

      var html =
        '<div class="hero">' +
          '<span class="hero-badge">Boom Beach</span>' +
          '<h1>Справочник опергруппы</h1>' +
          '<p>Операции, войска, прототипы, оборона и калькулятор канонерки — всё в одном месте.</p>' +
        '</div>' +

        '<div class="searchbar" data-href="#/search">' +
          '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>' +
          '<input readonly placeholder="Найти юнит, оборонку, операцию…">' +
        '</div>' +

        UI.secTitle('Разделы') +
        UI.tiles([
          { icon: '⚔️', title: 'Операции', sub: '24 операции, интел, очки силы', href: '#/ops', accent: 'gold' },
          { icon: '🚤', title: 'Калькулятор', sub: 'Энергия канонерки и снос целей', href: '#/calc', accent: 'blue' },
          { icon: '🪖', title: 'Войска', sub: '13 юнитов по уровням', href: '#/cat/troops', accent: 'teal' },
          { icon: '🧪', title: 'Прототипы', sub: '20 прото-войск', href: '#/cat/proto_troops', accent: 'purple' },
          { icon: '🛡️', title: 'Оборона', sub: 'Что и в каком порядке сносить', href: '#/cat/defenses', accent: 'red' },
          { icon: '🗿', title: 'Статуи', sub: 'Бонусы идолов и шедевров', href: '#/statues', accent: 'gold' }
        ]) +

        UI.secTitle('Наши операции', { href: '#/ops', title: 'все' }) +
        hard.map(function (o) {
          return UI.rowItem({
            title: o.ru + (o.slang ? ' · ' + o.slang.split(',')[0] : ''),
            sub: '№' + o.n + ' · ' + o.bases + ' баз · ' + o.fp + ' очков силы',
            href: '#/ops?n=' + o.n
          });
        }).join('') +

        UI.secTitle('Гайды', { href: '#/more', title: 'ещё' }) +
        guide.articles.slice(0, 4).map(function (a) {
          return UI.rowItem({ title: a.icon + '  ' + a.title, sub: a.sub, href: '#/guide/' + a.id });
        }).join('') +

        '<div class="src tiny">Данные с англоязычной вики Boom Beach · схемы из чата опергруппы</div>';

      return { title: 'Опергруппа', html: html };
    });
  }

  /* ======================= ОПЕРАЦИИ ======================= */

  var opTfSize = localStorage.getItem('bb_tf') || '25';

  function ops(params) {
    return DB.loadAll(['ops', 'guide']).then(function (res) {
      var data = res[0];
      var tab = (params && params.tab) || 'list';

      var tabs = UI.seg([
        { v: 'list', t: 'Операции' },
        { v: 'rules', t: 'Как играть' },
        { v: 'order', t: 'Порядок атак' },
        { v: 'bases', t: 'Базы' },
        { v: 'sab', t: 'Саботаж' }
      ], tab, 'data-optab');

      var body = '';
      if (tab === 'list') {
        body =
          '<div class="sec-title" style="margin-top:14px"><span>Размер опергруппы</span></div>' +
          UI.seg([
            { v: '5', t: '5 игроков' }, { v: '10', t: '10' },
            { v: '25', t: '25' }, { v: '50', t: '50' }
          ], opTfSize, 'data-tf') +
          '<div class="tiny" style="margin:7px 2px 10px">Цена интела зависит от максимального размера группы, а не от числа тех, кто онлайн. ОС — очки силы, нажми на строку для подробностей.</div>' +
          '<div id="ops-table"></div>';
      } else if (tab === 'sab') {
        body =
          '<div class="card" style="margin-top:12px">' +
            '<p class="tiny" style="margin:0 0 10px">Офицер, соруководитель или лидер может за интел уничтожить случайное оборонительное здание на базе операции. Выбрать конкретное здание нельзя, каждый следующий саботаж дороже.</p>' +
            UI.table(['Саботаж', 'Интел', 'Всего интела'],
              data.sabotage.map(function (s) { return [s.n, s.cost, s.total]; })) +
          '</div>';
      } else {
        var wantId = tab === 'rules' ? 'op-flow' : (tab === 'bases' ? 'power-bases' : 'op-order');
        var art = res[1].articles.filter(function (a) { return a.id === wantId; })[0];
        body = '<div class="article" style="margin-top:12px">' + renderBlocks(art.blocks) + '</div>' +
          (tab === 'bases'
            ? UI.rowItem({ title: '🖼️ Схемы и скрины баз', sub: 'Архив из чата опергруппы', href: '#/gallery' })
            : '') +
          UI.rowItem({ title: '📋 Все гайды', sub: 'Связки войск, энергия, ошибки', href: '#/more' });
      }

      return {
        title: 'Операции',
        html: tabs + body,
        after: function (root) {
          if (tab === 'list') drawOpsTable(root, data.ops);
          root.querySelectorAll('[data-optab]').forEach(function (b) {
            b.onclick = function () { App.go('#/ops?tab=' + b.dataset.optab); };
          });
          root.querySelectorAll('[data-tf]').forEach(function (b) {
            b.onclick = function () {
              opTfSize = b.dataset.tf;
              localStorage.setItem('bb_tf', opTfSize);
              root.querySelectorAll('[data-tf]').forEach(function (x) { x.classList.toggle('on', x === b); });
              drawOpsTable(root, data.ops);
              UI.haptic('sel');
            };
          });
          if (params && params.n) {
            var o = data.ops.filter(function (x) { return String(x.n) === String(params.n); })[0];
            if (o) opSheet(o);
          }
        }
      };
    });
  }

  function drawOpsTable(root, list) {
    var box = root.querySelector('#ops-table');
    if (!box) return;
    var html = '<div class="tablewrap"><table class="ops"><thead><tr>' +
      ['Операция', 'Интел', 'ОС', 'Баз'].map(function (h) { return '<th>' + h + '</th>'; }).join('') +
      '</tr></thead><tbody>' +
      list.map(function (o) {
        return '<tr data-op="' + o.n + '">' +
          '<td class="opname"><b>' + o.n + '. ' + esc(o.ru) + '</b>' +
          '<span class="en">' + esc(o.en) +
          (o.slang ? ' · <span class="sl">' + esc(o.slang) + '</span>' : '') + '</span></td>' +
          '<td class="num">' + esc(o.intel[opTfSize]) + '</td>' +
          '<td class="num">' + esc(o.fp) + '</td>' +
          '<td class="num">' + esc(o.bases) + '</td></tr>';
      }).join('') + '</tbody></table></div>';
    box.innerHTML = html;
    box.querySelectorAll('[data-op]').forEach(function (tr) {
      tr.onclick = function () {
        var o = list.filter(function (x) { return String(x.n) === tr.dataset.op; })[0];
        if (o) { UI.haptic('light'); opSheet(o); }
      };
    });
  }

  function opSheet(o) {
    UI.sheet(
      '<h2 style="margin:4px 0 2px;font-size:20px;font-weight:900">' + esc(o.ru) + '</h2>' +
      '<div class="tiny" style="margin-bottom:10px">Операция №' + o.n + ' · ' + esc(o.en) +
      (o.slang ? ' · в чате: <span style="color:var(--gold)">' + esc(o.slang) + '</span>' : '') + '</div>' +
      (o.note ? '<p style="color:var(--muted);font-size:13.5px;margin:0 0 12px;line-height:1.5">' + esc(o.note) + '</p>' : '') +
      '<div class="statgrid">' +
        stat('Силовых баз', o.bases) +
        stat('Очки силы', o.fp) +
      '</div>' +
      '<div class="sec-title">Цена интела</div>' +
      UI.table(['ОПГ 5', 'ОПГ 10', 'ОПГ 25', 'ОПГ 50'],
        [[o.intel['5'], o.intel['10'], o.intel['25'], o.intel['50']]]) +
      '<div class="tiny" style="margin-top:12px">Операция длится 23 ч 55 мин. У каждого игрока одна атака. Урон по базам сохраняется между атаками.</div>'
    );
  }

  function stat(label, value) {
    return '<div class="stat"><span>' + esc(label) + '</span><b>' + esc(value) + '</b></div>';
  }

  /* ======================= КАТАЛОГ ======================= */

  function catalog(key) {
    var meta = DB.catalogOf(key);
    return DB.load(key).then(function (list) {
      var html = '';
      if (key === 'meta') {
        html = list.map(function (e) {
          return UI.rowItem({ title: e.ru, sub: e.en, img: e.img, href: '#/p/meta/' + e.id });
        }).join('');
      } else {
        html = UI.unitGrid(list, key);
      }
      var others = DB.CATALOG.filter(function (c) { return c.key !== key && c.key !== 'meta'; });
      html += UI.secTitle('Другие разделы') +
        '<div class="grid g2">' + others.map(function (c) {
          return '<button class="tile accent-' + c.accent + '" data-href="#/cat/' + c.key + '">' +
            '<i>' + c.icon + '</i><b>' + esc(c.title) + '</b></button>';
        }).join('') + '</div>';
      return { title: meta.title, html: html };
    });
  }

  /* ======================= КАРТОЧКА ======================= */

  function detail(group, id) {
    return DB.loadAll([group, 'ru_text']).then(function (res) {
      var list = res[0], ruText = res[1];
      var ru = ruText[group + ':' + id];
      var e = list.filter(function (x) { return x.id === id; })[0];
      if (!e) return { title: 'Не найдено', html: '<div class="empty"><i>🤷</i>Такой страницы нет</div>' };

      var lvls = e.levels;
      var maxL = lvls ? CALC.maxLevel(e) : 0;
      var startL = Math.min(maxL, 10) || 1;

      var infoKeys = Object.keys(e.info || {});
      var head =
        '<div class="detail-head">' +
          '<div class="art">' + (e.img ? '<img src="' + esc(e.img) + '" alt="">' : '🏝️') + '</div>' +
          '<div><h2>' + esc(e.ru) + '</h2>' +
          '<div class="en">' + esc(e.en) + '</div>' +
          (e.slang ? '<div class="sl">в чате: ' + esc(e.slang) + '</div>' : '') + '</div>' +
        '</div>';

      var ruHtml = '';
      if (ru) {
        ruHtml = '<div class="card ru-sum"><p>' + esc(ru.s) + '</p>' +
          ((ru.p && ru.p.length) || (ru.m && ru.m.length)
            ? '<div class="pm">' +
              (ru.p || []).map(function (x) { return '<div class="pm-i plus">' + esc(x) + '</div>'; }).join('') +
              (ru.m || []).map(function (x) { return '<div class="pm-i minus">' + esc(x) + '</div>'; }).join('') +
              '</div>' : '') +
          '</div>' +
          ((ru.u && ru.u.length)
            ? '<div class="card" style="margin-top:10px"><div class="card-h">Как играть</div>' +
              '<ul class="use">' + ru.u.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul></div>'
            : '');
      }

      var infoHtml = infoKeys.length
        ? '<div class="card" style="margin-top:10px"><dl class="kv">' + infoKeys.map(function (k) {
            return '<dt>' + esc(k) + '</dt><dd>' + esc(e.info[k]) + '</dd>';
          }).join('') + '</dl></div>'
        : '';

      var lvlHtml = '';
      if (lvls && lvls.rows.length) {
        lvlHtml =
          UI.secTitle('Характеристики по уровням') +
          '<div class="lvlpick">' +
            '<input type="range" id="lv" min="1" max="' + maxL + '" value="' + startL + '">' +
            '<span class="lv" id="lvv">Ур. ' + startL + '</span>' +
          '</div>' +
          '<div class="statgrid" id="lvstats"></div>' +
          UI.accordion('Полная таблица', UI.table(lvls.headers, lvls.rows), false);
      }

      var extrasHtml = (e.extras || []).map(function (t) {
        var name = t.title || guessTableName(t.headers);
        return UI.accordion(name, UI.table(t.headers, t.rows), false);
      }).join('');

      var textHtml = (e.text || []).map(function (s) {
        return UI.accordion(s.title, UI.bullets(s.lines), !ru && (s.title === 'Коротко' || s.title === 'Общая информация'));
      }).join('');

      var related = relatedLinks(group, e);

      var html = head + ruHtml + infoHtml + lvlHtml +
        (textHtml ? UI.secTitle(ru ? 'Подробно с вики (англ.)' : 'Описание и тактика') + textHtml : '') +
        (extrasHtml ? UI.secTitle('Другие таблицы') + extrasHtml : '') +
        related +
        '<div class="src"><a class="link" href="' + esc(e.wiki) + '" target="_blank" rel="noopener">Источник на вики ↗</a></div>';

      return {
        title: e.ru,
        html: html,
        after: function (root) {
          var range = root.querySelector('#lv');
          if (!range) return;
          function paint() {
            var l = parseInt(range.value, 10);
            root.querySelector('#lvv').textContent = 'Ур. ' + l;
            var row = null;
            for (var i = 0; i < lvls.rows.length; i++) {
              if (CALC.toNum(lvls.rows[i][0]) === l) { row = lvls.rows[i]; break; }
            }
            var box = root.querySelector('#lvstats');
            if (!row) { box.innerHTML = '<div class="tiny">Нет данных для этого уровня</div>'; return; }
            var cells = [];
            for (var c = 1; c < lvls.headers.length && cells.length < 8; c++) {
              var v = row[c];
              if (!v || v === 'N/A' || v === '-') continue;
              cells.push(stat(lvls.headers[c], v));
            }
            box.innerHTML = cells.join('');
          }
          range.oninput = paint;
          paint();
        }
      };
    });
  }

  function guessTableName(headers) {
    var h = headers.join(' ').toLowerCase();
    if (h.indexOf('энергия') >= 0) return 'Стоимость применений';
    if (h.indexOf('ранг') >= 0) return 'Боевые корабли: ранги';
    if (h.indexOf('статуи') >= 0) return 'Статуи';
    return 'Таблица';
  }

  function relatedLinks(group, e) {
    if (group === 'gunboat' && e.id !== 'gunboat') {
      return UI.secTitle('Пригодится') +
        UI.rowItem({ title: '🚤 Калькулятор канонерки', sub: 'Посчитать энергию и снос цели', href: '#/calc' });
    }
    if (group === 'defenses' || group === 'proto_defenses') {
      return UI.secTitle('Пригодится') +
        UI.rowItem({ title: '🚤 Сколько энергии на снос', sub: 'Открыть калькулятор с этой целью', href: '#/calc?target=' + group + ':' + e.id });
    }
    return '';
  }

  /* ======================= КАНОНЕРКА ======================= */

  function gunboat() {
    return DB.load('gunboat').then(function (list) {
      var gb = list.filter(function (x) { return x.id === 'gunboat'; })[0];
      var abil = list.filter(function (x) { return x.id !== 'gunboat'; });

      var html =
        '<div class="hero" style="background:linear-gradient(135deg,var(--blue-soft),var(--teal-soft))">' +
          '<span class="hero-badge">Канонерка</span>' +
          '<h1>Энергия решает</h1>' +
          '<p>Каждое следующее применение одной способности дороже предыдущего. Разрушенное здание возвращает 3 энергии.</p>' +
        '</div>' +
        UI.rowItem({ title: '🧮 Калькулятор канонерки', sub: 'Энергия, план атаки, снос цели', href: '#/calc' }) +
        UI.secTitle('Способности') +
        '<div class="ab-list">' + abil.map(function (a) {
          var c = CALC.abilityCost(a);
          return '<button class="ab" data-href="#/p/gunboat/' + a.id + '" style="cursor:pointer;text-align:left;font:inherit;color:inherit">' +
            (a.img ? '<img src="' + esc(a.img) + '" alt="">' : '') +
            '<span class="abn"><b>' + esc(a.ru) + '</b>' +
            '<span>старт ' + c.base + ' ⚡ · дальше +' + c.step + ' за применение</span></span>' +
            '<span class="chev">›</span></button>';
        }).join('') + '</div>' +
        (gb ? UI.secTitle('Сама канонерка') + UI.rowItem({ title: gb.ru, sub: 'Запас энергии по уровням', img: gb.img, href: '#/p/gunboat/gunboat' }) : '');

      return { title: 'Канонерка', html: html };
    });
  }

  /* ======================= КАЛЬКУЛЯТОР ======================= */

  function calcView(params) {
    return DB.loadAll(['gunboat', 'defenses', 'proto_defenses', 'buildings']).then(function (res) {
      var gunboats = res[0];
      var st = CALC.loadState();
      if (params && params.target) {
        var p = params.target.split(':');
        if (p.length === 2) { st.target = { group: p[0], id: p[1], lvl: st.target.lvl }; CALC.saveState(st); }
      }

      var gb = gunboats.filter(function (x) { return x.id === 'gunboat'; })[0];
      var gbMax = CALC.maxLevel(gb);

      var abilEntries = {};
      CALC.ABILS.forEach(function (a) {
        abilEntries[a.id] = gunboats.filter(function (x) { return x.id === a.id; })[0];
      });

      var targetGroups = [
        { key: 'defenses', t: 'Оборона' },
        { key: 'proto_defenses', t: 'Прототипы' },
        { key: 'buildings', t: 'Постройки' }
      ];

      function opts(n, sel, label) {
        var s = '';
        for (var i = 1; i <= n; i++) {
          s += '<option value="' + i + '"' + (i === sel ? ' selected' : '') + '>' + (label || '') + i + '</option>';
        }
        return s;
      }

      var html =
        '<div class="hero" style="background:linear-gradient(135deg,var(--blue-soft),transparent)">' +
          '<span class="hero-badge">Калькулятор</span>' +
          '<h1>Канонерка</h1>' +
          '<p>Сколько энергии у тебя есть, во что она превращается и хватит ли её на цель.</p>' +
        '</div>' +

        '<div class="card">' +
          '<div class="calc-row">' +
            '<div class="calc-field"><label>Уровень канонерки</label>' +
              '<select id="c-gb">' + opts(gbMax, st.gb) + '</select></div>' +
            '<div class="calc-field"><label>Бонус энергии, %</label>' +
              '<input type="number" id="c-eb" min="0" max="120" step="1" value="' + st.energyBonus + '"></div>' +
          '</div>' +
          '<div class="calc-field" style="margin-bottom:0"><label>Снесено зданий на базе (+3 ⚡ за каждое)</label>' +
            '<input type="number" id="c-dest" min="0" max="80" step="1" value="' + st.destroyed + '"></div>' +
        '</div>' +

        '<div class="result" id="c-res"></div>' +

        UI.secTitle('План применений') +
        '<div class="ab-list" id="c-plan"></div>' +

        UI.secTitle('Сколько нужно на цель') +
        '<div class="card">' +
          '<div class="calc-field"><label>Чем бьём</label>' +
            UI.seg([{ v: 'artillery', t: 'Артиллерия' }, { v: 'barrage', t: 'Обстрел' }], st.weapon, 'data-wp') +
          '</div>' +
          '<div class="calc-row">' +
            '<div class="calc-field"><label>Уровень оружия</label><select id="c-wl"></select></div>' +
            '<div class="calc-field"><label>Бонус урона, %</label>' +
              '<input type="number" id="c-db" min="0" max="200" step="1" value="' + st.dmgBonus + '"></div>' +
          '</div>' +
          '<div class="calc-field"><label>Цель</label>' +
            UI.seg(targetGroups.map(function (g) { return { v: g.key, t: g.t }; }), st.target.group, 'data-tg') +
          '</div>' +
          '<div class="calc-field"><label>Что сносим</label><select id="c-tgt"></select></div>' +
          '<div class="calc-row">' +
            '<div class="calc-field"><label>Уровень цели</label><select id="c-tl"></select></div>' +
            '<div class="calc-field"><label>Бонус прочности, %</label>' +
              '<input type="number" id="c-hb" min="0" max="200" step="1" value="' + st.hpBonus + '"></div>' +
          '</div>' +
          '<div id="c-target-res"></div>' +
        '</div>' +

        '<div class="note tip" style="margin-top:12px"><b>Как пользоваться</b>' +
        'Бонусы — это суммарные проценты от статуй, гравировок и эффектов. Если бонусов нет, оставь нули: расчёт будет по «голым» цифрам вики.</div>' +

        '<div class="src"><button class="chip" id="c-reset">Сбросить настройки</button></div>';

      return {
        title: 'Калькулятор',
        html: html,
        after: function (root) { wireCalc(root, st, gunboats, abilEntries, gb, res); }
      };
    });
  }

  function wireCalc(root, st, gunboats, abilEntries, gb, res) {
    var groupsData = { defenses: res[1], proto_defenses: res[2], buildings: res[3] };

    function save() { CALC.saveState(st); }

    function renderPlan() {
      var box = root.querySelector('#c-plan');
      box.innerHTML = CALC.ABILS.map(function (a) {
        var e = abilEntries[a.id];
        var c = CALC.abilityCost(e);
        var n = st.plan[a.id] || 0;
        var cost = CALC.costOf(n, c.base, c.step);
        var nextCost = c.base + c.step * n;
        return '<div class="ab">' +
          (e && e.img ? '<img src="' + esc(e.img) + '" alt="">' : '') +
          '<span class="abn"><b>' + esc(a.ru) + '</b>' +
          '<span>' + (n ? n + ' шт · ' + cost + ' ⚡ · следующее ' + nextCost + ' ⚡' : 'старт ' + c.base + ' ⚡, рост +' + c.step) + '</span></span>' +
          '<span class="stepper"><button data-dec="' + a.id + '">−</button>' +
          '<b>' + n + '</b><button data-inc="' + a.id + '">+</button></span>' +
          '</div>';
      }).join('');
      box.querySelectorAll('[data-inc]').forEach(function (b) {
        b.onclick = function () { st.plan[b.dataset.inc] = (st.plan[b.dataset.inc] || 0) + 1; save(); renderPlan(); renderEnergy(); UI.haptic('light'); };
      });
      box.querySelectorAll('[data-dec]').forEach(function (b) {
        b.onclick = function () { st.plan[b.dataset.dec] = Math.max(0, (st.plan[b.dataset.dec] || 0) - 1); save(); renderPlan(); renderEnergy(); UI.haptic('light'); };
      });
    }

    function totalEnergy() {
      return CALC.gunboatEnergy(gb, st.gb, st.energyBonus) + (st.destroyed || 0) * 3;
    }

    function spentEnergy() {
      var s = 0;
      CALC.ABILS.forEach(function (a) {
        var c = CALC.abilityCost(abilEntries[a.id]);
        s += CALC.costOf(st.plan[a.id] || 0, c.base, c.step);
      });
      return s;
    }

    function renderEnergy() {
      var tot = totalEnergy(), sp = spentEnergy(), left = tot - sp;
      var pct = tot > 0 ? Math.min(100, Math.round(sp / tot * 100)) : 0;
      var base = CALC.gunboatEnergy(gb, st.gb, 0);
      root.querySelector('#c-res').innerHTML =
        '<div class="tiny">Доступно энергии</div>' +
        '<div class="big">' + tot + ' ⚡</div>' +
        '<div class="energy-bar' + (left < 0 ? ' over' : '') + '"><i style="width:' + pct + '%"></i></div>' +
        '<div style="display:flex;justify-content:space-between;font-size:12px;color:var(--muted)">' +
          '<span>потрачено ' + sp + '</span>' +
          '<span style="color:' + (left < 0 ? 'var(--red)' : 'var(--teal)') + ';font-weight:700">' +
          (left < 0 ? 'не хватает ' + (-left) : 'остаток ' + left) + ' ⚡</span>' +
        '</div>' +
        '<div class="tiny" style="margin-top:8px">Канонерка ур. ' + st.gb + ': ' + base + ' ⚡' +
        (st.energyBonus ? ' + ' + st.energyBonus + '% статуй' : '') +
        (st.destroyed ? ' + ' + (st.destroyed * 3) + ' ⚡ со снесённых зданий' : '') + '</div>';
    }

    function fillWeaponLevels() {
      var e = abilEntries[st.weapon];
      var max = CALC.maxLevel(e);
      if (!st.lv[st.weapon]) st.lv[st.weapon] = Math.min(max, 15);
      st.lv[st.weapon] = Math.min(st.lv[st.weapon], max);
      var sel = root.querySelector('#c-wl');
      var s = '';
      for (var i = 1; i <= max; i++) s += '<option value="' + i + '"' + (i === st.lv[st.weapon] ? ' selected' : '') + '>Ур. ' + i + '</option>';
      sel.innerHTML = s;
    }

    function fillTargets() {
      var list = (groupsData[st.target.group] || []).filter(function (x) { return x.levels && x.levels.rows.length; });
      var sel = root.querySelector('#c-tgt');
      if (!list.filter(function (x) { return x.id === st.target.id; }).length && list.length) {
        st.target.id = list[0].id;
      }
      sel.innerHTML = list.map(function (x) {
        return '<option value="' + esc(x.id) + '"' + (x.id === st.target.id ? ' selected' : '') + '>' + esc(x.ru) + '</option>';
      }).join('');
      fillTargetLevels();
    }

    function currentTarget() {
      var list = groupsData[st.target.group] || [];
      return list.filter(function (x) { return x.id === st.target.id; })[0];
    }

    function fillTargetLevels() {
      var e = currentTarget();
      var max = e ? CALC.maxLevel(e) : 1;
      st.target.lvl = Math.min(st.target.lvl || 1, max);
      var sel = root.querySelector('#c-tl');
      var s = '';
      for (var i = 1; i <= max; i++) s += '<option value="' + i + '"' + (i === st.target.lvl ? ' selected' : '') + '>Ур. ' + i + '</option>';
      sel.innerHTML = s;
    }

    function renderTarget() {
      var e = currentTarget();
      var box = root.querySelector('#c-target-res');
      if (!e) { box.innerHTML = '<div class="tiny">Выбери цель</div>'; return; }
      var hp = CALC.targetHp(e, st.target.lvl, st.hpBonus);
      var dmg = CALC.weaponDamage(abilEntries[st.weapon], st.lv[st.weapon], st.dmgBonus, st.weapon);
      if (isNaN(hp) || isNaN(dmg) || dmg <= 0) {
        box.innerHTML = '<div class="tiny">Для этой пары нет данных в таблицах вики</div>';
        return;
      }
      var shots = Math.ceil(hp / dmg);
      var c = CALC.abilityCost(abilEntries[st.weapon]);
      var energy = CALC.costOf(shots, c.base, c.step);
      var tot = totalEnergy();
      var wname = st.weapon === 'barrage' ? 'обстрела' : 'артиллерии';
      box.innerHTML =
        '<div class="statgrid" style="margin-top:4px">' +
          stat('Прочность цели', num(hp)) +
          stat('Урон за применение', num(dmg)) +
          stat('Нужно ' + wname, shots + ' шт') +
          stat('Энергии', energy + ' ⚡') +
        '</div>' +
        '<div class="tiny" style="margin-top:8px">' +
          (energy <= tot
            ? 'Влезает: после сноса останется ' + (tot - energy) + ' ⚡ (если больше ничего не тратить).'
            : 'Не влезает: не хватает ' + (energy - tot) + ' ⚡. Попробуй другое оружие, уровень или снеси склады ради энергии.') +
          ' Урон по площади может задеть соседние постройки — тогда выстрелов понадобится меньше.' +
        '</div>' +
        '<div style="margin-top:10px">' +
          '<button class="chip" id="c-apply">Добавить ' + shots + ' в план</button>' +
        '</div>';
      var ap = box.querySelector('#c-apply');
      if (ap) ap.onclick = function () {
        st.plan[st.weapon] = (st.plan[st.weapon] || 0) + shots;
        save(); renderPlan(); renderEnergy(); UI.haptic('medium');
      };
    }

    function repaintAll() { renderEnergy(); renderTarget(); }

    root.querySelector('#c-gb').onchange = function (ev) { st.gb = +ev.target.value; save(); repaintAll(); };
    root.querySelector('#c-eb').oninput = function (ev) { st.energyBonus = +ev.target.value || 0; save(); repaintAll(); };
    root.querySelector('#c-dest').oninput = function (ev) { st.destroyed = +ev.target.value || 0; save(); repaintAll(); };
    root.querySelector('#c-db').oninput = function (ev) { st.dmgBonus = +ev.target.value || 0; save(); renderTarget(); };
    root.querySelector('#c-hb').oninput = function (ev) { st.hpBonus = +ev.target.value || 0; save(); renderTarget(); };
    root.querySelector('#c-wl').onchange = function (ev) { st.lv[st.weapon] = +ev.target.value; save(); renderTarget(); };
    root.querySelector('#c-tgt').onchange = function (ev) { st.target.id = ev.target.value; save(); fillTargetLevels(); renderTarget(); };
    root.querySelector('#c-tl').onchange = function (ev) { st.target.lvl = +ev.target.value; save(); renderTarget(); };

    root.querySelectorAll('[data-wp]').forEach(function (b) {
      b.onclick = function () {
        st.weapon = b.dataset.wp; save();
        root.querySelectorAll('[data-wp]').forEach(function (x) { x.classList.toggle('on', x === b); });
        fillWeaponLevels(); renderTarget(); UI.haptic('sel');
      };
    });
    root.querySelectorAll('[data-tg]').forEach(function (b) {
      b.onclick = function () {
        st.target.group = b.dataset.tg; save();
        root.querySelectorAll('[data-tg]').forEach(function (x) { x.classList.toggle('on', x === b); });
        fillTargets(); renderTarget(); UI.haptic('sel');
      };
    });
    root.querySelector('#c-reset').onclick = function () {
      localStorage.removeItem('bb_calc_v1');
      App.go('#/calc', true);
    };

    renderPlan();
    fillWeaponLevels();
    fillTargets();
    repaintAll();
  }

  /* ======================= СТАТУИ ======================= */

  function statues() {
    return DB.load('meta').then(function (list) {
      var st = list.filter(function (x) { return x.id === 'statue'; })[0];
      var ps = list.filter(function (x) { return x.id === 'power-stone'; })[0];
      if (!st) return { title: 'Статуи', html: '<div class="empty"><i>🗿</i>Нет данных</div>' };

      var bonusTable = (st.extras || []).filter(function (t) {
        return t.headers.join(' ').indexOf('Идол') >= 0;
      })[0];

      var RU = {
        'Life': 'Жизнь (зелёные)', 'Ice': 'Лёд (синие)',
        'Magma': 'Магма (красные)', 'Dark': 'Тьма (фиолетовые)'
      };
      var BON = {
        'Gold production increase': 'Добыча золота',
        'Wood , Stone or Iron production increase': 'Добыча дерева / камня / железа',
        'All Resources Production increase': 'Добыча всех ресурсов',
        'Building Health increase': 'Прочность построек',
        'Defensive Building Damage increase': 'Урон обороны',
        'Troop Health increase': 'Прочность войск',
        'Troop Damage increase': 'Урон войск',
        'Gunboat Energy increase': 'Энергия канонерки',
        'Resource Reward increase': 'Награда ресурсами',
        'Power Stone chance increase': 'Шанс камней силы'
      };

      var rows = bonusTable ? bonusTable.rows.map(function (r) {
        return [RU[r[0]] || r[0], BON[r[1]] || r[1], r[2], r[3], r[4]];
      }) : [];

      var html =
        '<div class="hero" style="background:linear-gradient(135deg,var(--purple-soft),var(--gold-soft))">' +
          '<span class="hero-badge">Артефакты</span><h1>Статуи</h1>' +
          '<p>Четыре стихии, три класса. Процент бонуса выпадает случайно — повлиять нельзя.</p>' +
        '</div>' +
        (rows.length ? UI.secTitle('Бонусы по классам') +
          UI.table(['Стихия', 'Бонус', 'Идол', 'Страж', 'Шедевр'], rows) : '') +
        UI.secTitle('Что важно для операций') +
        '<div class="card"><ul style="margin:0;padding-left:18px;color:var(--muted);font-size:13.5px;line-height:1.5">' +
          '<li><b style="color:var(--text)">Тьма → энергия канонерки</b> — больше арты и обстрелов за атаку.</li>' +
          '<li><b style="color:var(--text)">Магма → урон и прочность войск</b> — армия дольше живёт и быстрее сносит.</li>' +
          '<li><b style="color:var(--text)">Лёд</b> — только оборона своей базы, на атаку не влияет.</li>' +
          '<li><b style="color:var(--text)">Жизнь</b> — добыча ресурсов, на операции не влияет.</li>' +
        '</ul></div>' +
        (st.extras || []).filter(function (t) { return t.headers.join(' ').indexOf('Класс статуи') >= 0; })
          .map(function (t) { return UI.secTitle('Создание и разбор') + UI.table(t.headers, t.rows); }).join('') +
        UI.rowItem({ title: '🗿 Полная страница вики', sub: st.en, img: st.img, href: '#/p/meta/statue' }) +
        (ps ? UI.rowItem({ title: '💎 Камни силы', sub: ps.en, img: ps.img, href: '#/p/meta/power-stone' }) : '');

      return { title: 'Статуи', html: html };
    });
  }

  /* ======================= ГАЙДЫ ======================= */

  function renderBlocks(blocks) {
    return blocks.map(function (b) {
      if (b.t === 'h') return '<h3>' + esc(b.v) + '</h3>';
      if (b.t === 'p') return '<p>' + esc(b.v) + '</p>';
      if (b.t === 'ul') return '<ul>' + b.v.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>';
      if (b.t === 'ol') return '<ol>' + b.v.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ol>';
      if (b.t === 'tip') return '<div class="note tip"><b>Совет</b>' + esc(b.v) + '</div>';
      if (b.t === 'warn') return '<div class="note warn"><b>Важно</b>' + esc(b.v) + '</div>';
      if (b.t === 'table') return UI.table(b.h, b.r);
      return '';
    }).join('');
  }

  function guideArticle(id) {
    return DB.load('guide').then(function (g) {
      var a = g.articles.filter(function (x) { return x.id === id; })[0];
      if (!a) return { title: 'Гайд', html: '<div class="empty"><i>📄</i>Статья не найдена</div>' };
      return {
        title: a.title,
        html: '<div class="hero"><span class="hero-badge">' + esc((a.tags || [])[0] || 'гайд') + '</span>' +
          '<h1>' + esc(a.icon + ' ' + a.title) + '</h1><p>' + esc(a.sub || '') + '</p></div>' +
          '<div class="article">' + renderBlocks(a.blocks) + '</div>'
      };
    });
  }

  function slangView() {
    return DB.load('guide').then(function (g) {
      var html = '<div class="hero"><span class="hero-badge">словарь</span><h1>Сленг чата</h1>' +
        '<p>Как мы называем операции, войска и оборонки.</p></div>' +
        '<div class="card"><dl class="kv" style="grid-template-columns:auto 1fr;gap:10px 14px">' +
        g.slang.map(function (s) {
          return '<dt style="color:var(--gold);font-weight:700;white-space:nowrap">' + esc(s.w) + '</dt>' +
            '<dd style="text-align:left;font-weight:400;color:var(--muted)">' + esc(s.m) + '</dd>';
        }).join('') + '</dl></div>';
      return { title: 'Сленг', html: html };
    });
  }

  function faqView() {
    return DB.load('guide').then(function (g) {
      var html = '<div class="hero"><span class="hero-badge">вопросы</span><h1>FAQ</h1>' +
        '<p>Короткие ответы на то, что спрашивают чаще всего.</p></div>' +
        g.faq.map(function (f) {
          return UI.accordion(f.q, '<p style="color:var(--muted);margin:0;line-height:1.5">' + esc(f.a) + '</p>', false);
        }).join('');
      return { title: 'FAQ', html: html };
    });
  }

  /* ======================= ГАЛЕРЕЯ ======================= */

  var galFilter = { t: 'Все', q: '' };

  function gallery() {
    return DB.load('gallery').then(function (list) {
      var topics = ['Все'];
      list.forEach(function (i) { if (topics.indexOf(i.t) < 0) topics.push(i.t); });

      var html =
        '<div class="hero" style="background:linear-gradient(135deg,var(--gold-soft),transparent)">' +
          '<span class="hero-badge">архив</span><h1>Схемы и скрины</h1>' +
          '<p>' + list.length + ' игровых скриншотов из чата опергруппы: базы, операции, награды, события.</p>' +
        '</div>' +
        '<div class="searchbar" style="margin-bottom:10px">' +
          '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>' +
          '<input id="g-q" placeholder="Поиск по подписи или автору" value="' + esc(galFilter.q) + '">' +
        '</div>' +
        UI.seg(topics.map(function (t) { return { v: t, t: t }; }), galFilter.t, 'data-gt') +
        '<div id="g-count" class="tiny" style="margin:9px 2px"></div>' +
        '<div class="gal" id="g-grid"></div>';

      return {
        title: 'Схемы',
        html: html,
        after: function (root) {
          function draw() {
            var q = galFilter.q.toLowerCase();
            var f = list.filter(function (i) {
              if (galFilter.t !== 'Все' && i.t !== galFilter.t) return false;
              if (!q) return true;
              return (i.c + ' ' + i.a + ' ' + i.d).toLowerCase().indexOf(q) >= 0;
            });
            root.querySelector('#g-count').textContent = f.length + ' из ' + list.length;
            root.querySelector('#g-grid').innerHTML = f.slice(0, 400).map(function (i) {
              return '<button data-g="' + esc(i.f) + '"><img loading="lazy" src="img/gallery/t/' + esc(i.f) + '.webp" alt=""></button>';
            }).join('') || '<div class="empty"><i>🔍</i>Ничего не нашлось</div>';
            root.querySelectorAll('[data-g]').forEach(function (b) {
              b.onclick = function () {
                var it = list.filter(function (x) { return x.f === b.dataset.g; })[0];
                UI.lightbox('img/gallery/' + it.f + '.webp',
                  (it.c ? it.c + ' — ' : '') + it.a + ', ' + it.d);
              };
            });
          }
          root.querySelectorAll('[data-gt]').forEach(function (b) {
            b.onclick = function () {
              galFilter.t = b.dataset.gt;
              root.querySelectorAll('[data-gt]').forEach(function (x) { x.classList.toggle('on', x === b); });
              draw(); UI.haptic('sel');
            };
          });
          var q = root.querySelector('#g-q');
          q.oninput = function () { galFilter.q = q.value; draw(); };
          draw();
        }
      };
    });
  }

  /* ======================= ЕЩЁ ======================= */

  function more() {
    return DB.load('guide').then(function (g) {
      var html =
        UI.secTitle('Гайды') +
        g.articles.map(function (a) {
          return UI.rowItem({ title: a.icon + '  ' + a.title, sub: a.sub, href: '#/guide/' + a.id });
        }).join('') +

        UI.secTitle('Справочники') +
        UI.tiles([
          { icon: '🗿', title: 'Статуи', sub: 'Бонусы и классы', href: '#/statues', accent: 'purple' },
          { icon: '🎖️', title: 'Герои', sub: '5 героев', href: '#/cat/heroes', accent: 'gold' },
          { icon: '🏗️', title: 'Постройки', sub: 'Экономика и штаб', href: '#/cat/buildings', accent: 'teal' },
          { icon: '⚡', title: 'Прото-оборона', sub: '12 прототипов', href: '#/cat/proto_defenses', accent: 'blue' },
          { icon: '🗣️', title: 'Сленг чата', sub: 'Словарь', href: '#/slang', accent: 'gold' },
          { icon: '❓', title: 'FAQ', sub: 'Частые вопросы', href: '#/faq', accent: 'teal' },
          { icon: '🖼️', title: 'Схемы и скрины', sub: 'Архив из чата', href: '#/gallery', accent: 'red' },
          { icon: '📚', title: 'Вся вики', sub: 'Механики и события', href: '#/cat/meta', accent: 'blue' }
        ]) +

        '<div class="card" style="margin-top:16px">' +
          '<div class="tiny">Цифры взяты с англоязычной вики Boom Beach и могут отставать от последнего обновления игры. ' +
          'Русские названия — из русской вики, где они есть; остальные подписаны английским оригиналом. ' +
          'Скриншоты — из выгрузки чата опергруппы.</div>' +
        '</div>';
      return { title: 'Ещё', html: html };
    });
  }

  /* ======================= ПОИСК ======================= */

  function searchView(params) {
    return DB.buildIndex().then(function () {
      var q = (params && params.q) || '';
      var html =
        '<div class="searchbar" style="margin-bottom:12px">' +
          '<svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>' +
          '<input id="s-q" placeholder="Юнит, оборонка, операция, сленг…" value="' + esc(q) + '">' +
        '</div><div id="s-res"></div>';
      return {
        title: 'Поиск',
        html: html,
        after: function (root) {
          var inp = root.querySelector('#s-q');
          var box = root.querySelector('#s-res');
          function draw() {
            var r = DB.search(inp.value);
            if (!inp.value.trim()) {
              box.innerHTML = '<div class="empty"><i>🔎</i>Введи название: «базука», «порез», «шоковая», «дупло»…</div>';
              return;
            }
            if (!r.length) { box.innerHTML = '<div class="empty"><i>🤷</i>Ничего не нашлось</div>'; return; }
            box.innerHTML = r.map(function (i) {
              var tag = i.kind === 'op' ? '⚔️ ' : i.kind === 'article' ? '📋 ' : i.kind === 'slang' ? '🗣️ ' : '';
              return UI.rowItem({ title: tag + i.title, sub: i.sub, img: i.img, href: i.href });
            }).join('');
          }
          inp.oninput = draw;
          draw();
          setTimeout(function () { try { inp.focus(); } catch (e) {} }, 60);
        }
      };
    });
  }

  global.VIEWS = {
    home: home, ops: ops, catalog: catalog, detail: detail,
    gunboat: gunboat, calcView: calcView, statues: statues,
    guideArticle: guideArticle, slangView: slangView, faqView: faqView,
    gallery: gallery, more: more, searchView: searchView
  };
})(window);
