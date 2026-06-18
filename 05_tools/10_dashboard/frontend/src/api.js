/**
 * API 封装模块
 * 所有后端 API 调用集中在这里，统一错误处理
 */

const BASE = '/api';

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };
  // Remove Content-Type for GET/HEAD requests
  if (!config.method || config.method === 'GET' || config.method === 'HEAD') {
    delete config.headers['Content-Type'];
  }
  try {
    const r = await fetch(url, config);
    if (!r.ok) {
      const text = await r.text().catch(() => '');
      throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
    }
    return await r.json();
  } catch (e) {
    if (e.name === 'AbortError') throw e;
    throw new Error(`API ${url}: ${e.message}`);
  }
}

// ── Matrix 账号 ──
export function getAccounts() {
  return request('/matrix/accounts');
}

export function getAccount(id) {
  return request(`/matrix/accounts/${encodeURIComponent(id)}`);
}

export function getHomepageInfo() {
  return request('/matrix/homepage-info');
}

// ── 养号执行 ──
export function nurtureStart(body) {
  return request('/matrix/nurture/start', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function nurtureStatus() {
  return request('/matrix/nurture/status');
}

export function nurtureResults(limit = 20) {
  return request(`/matrix/nurture/results?limit=${limit}`);
}

export function nurtureLog(runId) {
  return request(`/matrix/nurture/log/${encodeURIComponent(runId)}`);
}

export function nurtureCleanup(body = {}) {
  return request('/matrix/nurture/cleanup', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ── 信息采集 ──
export function collectHomepage(body = {}) {
  return request('/matrix/collect-homepage', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function collectStatus() {
  return request('/matrix/collect-homepage/status');
}

export function collectCancel() {
  return request('/matrix/collect-homepage/cancel', { method: 'POST' });
}

// ── 蓝图 ──
export function getBlueprints() {
  return request('/matrix/blueprints');
}

export function getAtomOps() {
  return request('/matrix/atom-ops');
}

// ── 任务 ──
export function taskRun(body) {
  return request('/matrix/task/run', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ── 统一操作 ──
export function opsRun(type, accounts, params = {}) {
  return request('/ops/run', {
    method: 'POST',
    body: JSON.stringify({ type, accounts, params }),
  });
}

// ── 联邦 ──
export function getMachines() {
  return request('/machines');
}

export function getMachineStatus(name) {
  return request(`/matrix/machine/${encodeURIComponent(name)}/status`);
}

export function fleetSync() {
  return request('/fleet/reconcile', { method: 'POST' });
}

// ── 健康检查 ──
export function health() {
  return request('/health');
}
