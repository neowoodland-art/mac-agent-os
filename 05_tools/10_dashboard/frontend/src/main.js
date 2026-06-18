/**
 * AgentOS Dashboard — Vite 入口
 * 
 * 职责：
 * - 样式热更新（CSS HMR）
 * - 加载全部内联 JS 逻辑（从 inline.js 导入）
 * - 暴露可复用组件到全局
 * - Patch switchView 支持已迁移视图（抑制内联加载器，走 dynamic import）
 * - 自动刷新状态栏
 */

import './style.css';

// ── 功能模块（按功能拆分的 inline 代码）──
import './modules/matrix_views.js';
import './modules/batch_exec.js';
import './modules/registration.js';
import './modules/account_selector.js';
import './modules/corpus.js';
import './modules/ops_router.js';
import './modules/recording.js';
import './modules/cmd_tasks.js';
import './modules/collect.js';
import './modules/nurture.js';
import './modules/schedule.js';
import './modules/settings.js';
import './modules/workflow.js';
import './modules/c2_remote.js';
import './modules/machine_bar.js';
import './modules/kb_management.js';

import { registerMigrated, loadMigratedView } from './router.js';

// ── 内联加载器 → 视图名称 映射（用于抑制内联代码的双重调用）──
const INLINE_LOADER_MAP = {
  'machines': 'loadMachines',
  'matrix-nurture': 'loadMatrixNurture',
  'matrix-collect': 'loadMatrixCollect',
  'matrix-comment': 'loadMatrixComment',
  'matrix-like': 'loadMatrixLike',
  'matrix-summary': 'loadMatrixSummary',
  'matrix-accounts': 'loadMatrixAccounts',
  'matrix-blueprints': 'loadMatrixBlueprints',
  'matrix-atom-ops': 'loadMatrixAtomOps',
  'matrix-schedule': 'loadMatrixSchedule',
  'matrix-corpus': 'loadCorpus',
  'matrix-login': 'loadMatrixLogin',
  'matrix-publish': 'loadMatrixPublish',
  'matrix-sms-proxy': 'loadSmsProxy',
  'ops-command': 'loadOpsCommand',
  'fleet-sync': 'loadFleetSync',
  'fleet-reconcile': 'loadFleetReconcile',
  'fleet-exec': 'loadFleetExec',
  'crawl-tasks': 'loadCrawlTasks',
  'crawl-sources': 'loadCrawlSources',
  'crawl-history': 'loadCrawlHistory',
  'ave-render': 'loadAveRender',
  'ave-script': 'loadAveScript',
  'ave-materials': 'loadAveMaterials',
  'ave-templates': 'loadAveTemplates',
  'serve-mcp': 'loadServeMCP',
  'serve-dashboard': 'loadServeDashboard',
  'serve-schedule': 'loadServeSchedule',
  'productions': 'loadProductions',
  'assets': 'loadAssets',
  'costs': 'loadCosts',
  'capabilities': 'loadCapabilities',
  'workflow': 'loadWorkflow',
};

const migratedViews = new Set();

function registerView(viewName) {
  migratedViews.add(viewName);
  registerMigrated(viewName);
}

// 注册所有已迁移视图
Object.keys(INLINE_LOADER_MAP).forEach(registerView);

// ── Patch switchView ──
function patchSwitchView() {
  if (typeof window.switchView !== 'function') {
    setTimeout(patchSwitchView, 50);
    return;
  }
  const origSwitchView = window.switchView;

  window.switchView = async function(view) {
    const isMigrated = migratedViews.has(view);
    let restoredLoader = null;

    if (isMigrated) {
      // 临时替换内联加载器为空函数
      const inlineFn = INLINE_LOADER_MAP[view];
      if (inlineFn && typeof window[inlineFn] === 'function') {
        restoredLoader = window[inlineFn];
        window[inlineFn] = async function() {};
      }
    }

    // 执行原版切换逻辑（显隐、高亮、侧边栏展开等）
    origSwitchView(view);

    // 恢复内联加载器
    if (restoredLoader) {
      window[INLINE_LOADER_MAP[view]] = restoredLoader;
    }

    // 已迁移视图：用动态 import 渲染
    if (isMigrated) {
      const container = document.getElementById('view-' + view);
      if (container) {
        await loadMigratedView(view, container);
      }
    }
  };
}

// ── 自动刷新 ──
function initAutoRefresh() {
  setInterval(async () => {
    try {
      if (typeof window.loadStats === 'function') window.loadStats();
      if (typeof window.loadMachineBar === 'function') window.loadMachineBar();
    } catch(e) { /* ignore refresh errors */ }
  }, 30000);
}

// ── 启动 ──
function boot() {
  patchSwitchView();
  initAutoRefresh();
  console.log('✅ Vite HMR active — all views migrated');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
