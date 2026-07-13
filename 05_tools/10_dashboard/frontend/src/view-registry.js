/**
 * view-registry.js — 已迁移视图注册表
 * 
 * 所有已完成 Vite 迁移的视图在此注册。
 * 注册后，switchView 会自动使用动态加载代替 inline 渲染。
 * 
 * 命名规则：视图名 = views/{name}.js 文件名（不含 .js）
 * 对应 inline.js 中 switchView() 的视图名
 */
import { registerMigrated } from './router.js';

const MIGRATED_VIEWS = [
  // ── 矩阵养号 ──
  'comment-workbench',
  'matrix-summary',
  'matrix-accounts',
  'matrix-nurture',
  'matrix-collect',
  'matrix-publish',
  'matrix-blueprints',
  'matrix-comment',
  'matrix-interact',
  'matrix-schedule',
  'matrix-corpus',
  'matrix-sms-proxy',
  'matrix-like',
  // 'matrix-login', // 已合并到信息采集
  'matrix-atom-ops',

  // ── 命令与任务 ──
  'matrix-commands',
  'ops-command',

  // ── 录制标注 ──
  'ops-recorder',

  // ── 视频工厂 ──
  'workflow',
  'capabilities',
  'characters',     // 角色列表
  'char-gen',       // 角色生成器

  // ── 内容抓取 ──
  'scrape',

  // ── 联邦管理 ──
  'fleet-sync',
  'fleet-reconcile',
  'fleet-exec',
  'machines',

  // ── 服务 ──
  'serve-mcp',
  'serve-dashboard',
  'serve-schedule',

  // ── 概览 ──
  'productions',
  'assets',
  'costs',

  // ── 其他 ──
  'timeline',       // 时间线（暂留观察）
];

// 注册所有已迁移视图
MIGRATED_VIEWS.forEach(registerMigrated);

export default MIGRATED_VIEWS;
