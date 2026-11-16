/* Калькулятор канонерки: энергия, цена способностей, сколько нужно на снос цели */
(function (global) {
  'use strict';

  var ABILS = [
    { id: 'artillery',   ru: 'Артиллерия',       short: 'Арта' },
    { id: 'barrage',     ru: 'Обстрел',          short: 'Обстрел' },
    { id: 'shock-bomb',  ru: 'Шоковый снаряд',   short: 'Шок' },
    { id: 'smoke-screen',ru: 'Дымовая завеса',   short: 'Дым' },
    { id: 'flare',       ru: 'Сигнальная ракета',short: 'Флара' },
    { id: 'medkit',      ru: 'Аптечка',          short: 'Аптечка' },
    { id: 'critters',    ru: 'Криттеры',         short: 'Криттеры' }
  ];

  var KEY = 'bb_calc_v1';

  function defaults() {
    return {
      gb: 20, energyBonus: 0, dmgBonus: 0, hpBonus: 0, destroyed: 0,
      plan: { artillery: 4, barrage: 1, 'shock-bomb': 0, 'smoke-screen': 0, flare: 0, medkit: 0, critters: 0 },
      lv: { artillery: 20, barrage: 18 },
      target: { group: 'defenses', id: 'boom-cannon', lvl: 10 },
      weapon: 'artillery'
    };
  }

  function loadState() {
    try {
      var s = JSON.parse(UI.store.get(KEY, 'null'));
      if (!s || typeof s !== 'object') return defaults();
      var d = defaults();
      Object.keys(d).forEach(function (k) { if (s[k] == null) s[k] = d[k]; });
      ['plan', 'lv', 'target'].forEach(function (k) {
        s[k] = Object.assign({}, d[k], s[k] || {});
      });
      return s;
    } catch (e) { return defaults(); }
  }

  function saveState(s) {
    UI.store.set(KEY, JSON.stringify(s));
  }

  /* --- доступ к таблицам вики --- */

  function colIndex(headers, names) {
    for (var n = 0; n < names.length; n++) {
      for (var i = 0; i < headers.length; i++) {
        if (headers[i].toLowerCase().indexOf(names[n].toLowerCase()) >= 0) return i;
      }
    }
    return -1;
  }

  function toNum(v) {
    if (v == null) return NaN;
    var s = String(v).replace(/[\s,   ]/g, '').replace(/[^\d.\-]/g, '');
    var n = parseFloat(s);
    return isNaN(n) ? NaN : n;
  }

  /** Значение колонки для уровня lvl у сущности e */
  function statAt(e, lvl, names) {
    if (!e || !e.levels) return NaN;
    var ci = colIndex(e.levels.headers, names);
    if (ci < 0) return NaN;
    var rows = e.levels.rows;
    for (var i = 0; i < rows.length; i++) {
      if (toNum(rows[i][0]) === lvl) return toNum(rows[i][ci]);
    }
    return NaN;
  }

  function maxLevel(e) {
    if (!e || !e.levels) return 1;
    var m = 1;
    e.levels.rows.forEach(function (r) {
      var n = toNum(r[0]);
      if (!isNaN(n) && n > m) m = n;
    });
    return m;
  }

  /** Базовая цена и шаг роста способности из info-таблицы */
  function abilityCost(e) {
    var base = NaN, step = NaN;
    if (e && e.info) {
      Object.keys(e.info).forEach(function (k) {
        if (/стоимость|usage cost/i.test(k)) base = toNum(e.info[k]);
        if (/рост цены|cost increase/i.test(k)) step = toNum(e.info[k]);
      });
    }
    return { base: isNaN(base) ? 0 : base, step: isNaN(step) ? 0 : step };
  }

  /** Энергия за n применений: n*base + step*(0+1+...+(n-1)) */
  function costOf(n, base, step) {
    if (n <= 0) return 0;
    return n * base + step * (n * (n - 1)) / 2;
  }

  /** Сколько применений влезет в бюджет энергии */
  function fitsIn(budget, base, step) {
    var n = 0;
    while (costOf(n + 1, base, step) <= budget) n++;
    return n;
  }

  function gunboatEnergy(gbEntry, level, bonusPct) {
    var base = statAt(gbEntry, level, ['Запас энергии', 'Energy Capacity']);
    if (isNaN(base)) base = 0;
    return Math.floor(base * (1 + (bonusPct || 0) / 100));
  }

  /** Урон выбранного оружия на его уровне, с учётом бонуса */
  function weaponDamage(entry, level, bonusPct, weapon) {
    var names = weapon === 'barrage'
      ? ['Суммарный урон', 'Total Damage']
      : ['Урон', 'Damage'];
    var d = statAt(entry, level, names);
    if (isNaN(d)) return NaN;
    return Math.round(d * (1 + (bonusPct || 0) / 100));
  }

  function targetHp(entry, level, hpBonusPct) {
    var hp = statAt(entry, level, ['Прочность', 'Hitpoints', 'Health']);
    if (isNaN(hp)) return NaN;
    return Math.round(hp * (1 + (hpBonusPct || 0) / 100));
  }

  global.CALC = {
    ABILS: ABILS,
    loadState: loadState, saveState: saveState, defaults: defaults,
    statAt: statAt, maxLevel: maxLevel, abilityCost: abilityCost,
    costOf: costOf, fitsIn: fitsIn, gunboatEnergy: gunboatEnergy,
    weaponDamage: weaponDamage, targetHp: targetHp, toNum: toNum, colIndex: colIndex
  };
})(window);
