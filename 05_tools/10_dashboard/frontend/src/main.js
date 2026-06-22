/**
 * AgentOS Dashboard — Vite 入口
 * 
 * 职责：
 * - 样式热更新（CSS HMR）
 * - 加载全部功能模块（switchView 补丁已内联到 matrix_views.js）
 */

import './style.css';

// ── 功能模块 ──
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

// ── 视图注册表（注册已迁移视图，供 switchView 路由用）──
import './view-registry.js';
