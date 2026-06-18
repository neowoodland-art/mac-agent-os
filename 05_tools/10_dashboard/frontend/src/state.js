/**
 * 全局状态管理
 * 替代原来的 _allAccounts, _nurtureAccounts 等全局变量
 */

class AppState {
  constructor() {
    this._accounts = [];
    this._hpIndex = {};
    this._collectedAt = '';
    this._listeners = {};
  }

  get accounts() { return this._accounts; }
  get hpIndex() { return this._hpIndex; }
  get collectedAt() { return this._collectedAt; }

  async loadAccounts() {
    if (this._accounts.length) return;
    const [r1, r2] = await Promise.all([
      fetch('/api/matrix/accounts'),
      fetch('/api/matrix/homepage-info').catch(() => ({ json: () => ({}) }))
    ]);
    const accts = await r1.json();
    const hpData = r2.json ? await r2.json() : { results: [] };
    this._accounts = Array.isArray(accts) ? accts.filter(a => a.enabled !== false) : [];
    this._hpIndex = {};
    (hpData.results || []).forEach(r => {
      if (r.identity_dir) this._hpIndex[r.identity_dir] = r;
      if (r.phone) this._hpIndex[r.phone] = r;
    });
    this._collectedAt = hpData.collected_at || '';
    return this._accounts;
  }

  getSelectedAccounts() {
    return Array.from(document.querySelectorAll('.as-cb:checked')).map(cb => ({
      id: cb.value,
      platform: cb.dataset.plat,
      blueprint: cb.dataset.bp,
      machine: cb.dataset.machine,
    }));
  }

  // 事件监听
  on(event, fn) {
    if (!this._listeners[event]) this._listeners[event] = [];
    this._listeners[event].push(fn);
  }

  emit(event, data) {
    (this._listeners[event] || []).forEach(fn => fn(data));
  }
}

export const state = new AppState();
