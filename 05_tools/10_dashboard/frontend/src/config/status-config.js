/**
 * 账号状态统一配置 — 单点维护，两处引用
 *
 * 使用方:
 *   - views/accounts-center.js  (账号中心)
 *   - components/account-selector.js  (统一账号选择器)
 *
 * 维护规则:
 *   新增/修改状态码时，只改此文件，两边自动同步。
 */

// ── 状态显示配置 ──
export const STATUS_CFG = {
  logged_in:       { color: '#22c55e', dot: '🟢', label: '已登录' },
  need_login:      { color: '#ef4444', dot: '🔴', label: '需重新登录' },
  no_cookie:       { color: '#8b8fa3', dot: '⚪', label: '无Cookie' },
  no_identity:     { color: '#8b8fa3', dot: '⚪', label: '未配置' },
  banned:          { color: '#000',    dot: '⚫', label: '已封号' },
  sms_skip:        { color: '#f97316', dot: '📱', label: '短信待验证' },
  running:         { color: '#3b82f6', dot: '🔵', label: '执行中' },
  disabled:        { color: '#d1d5db', dot: '⬜', label: '已禁用' },
  unknown:         { color: '#8b8fa3', dot: '⚪', label: '未知' },
};

// ── 状态排序优先级 ──
export const STATUS_ORDER = ['banned', 'need_login', 'sms_skip', 'no_cookie', 'running', 'disabled', 'unknown', 'logged_in'];
