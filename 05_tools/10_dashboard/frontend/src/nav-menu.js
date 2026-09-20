/**
 * nav-menu.js — 侧边栏菜单「单点定义」
 *
 * ⚠️ 全项目菜单只在这里维护！新增/删除菜单项只改本文件。
 *
 * 背景（技术债修复 2026-09-20）：
 *   此前菜单在 3 个文件里各有一份硬编码拷贝（inline.js / navigation.js / modules/matrix_views.js），
 *   main.js 的 import 顺序决定谁生效（最后 import 的 matrix_views.js 覆盖前两个），
 *   导致"改了菜单却看不到"（曾加 api-config 时踩坑）。
 *   现在三处统一 import 本文件 → 改一处全生效。
 *
 * 视图命名：view 对应 views/{name}.js（已迁移视图，走 router.js 动态加载到 #view-dynamic）
 */

export const NAV_GROUPS = {
  '矩阵': { icon: '📱', items: [
    {view:'accounts-center', label:'👤 账号中心'},
    // {view:'matrix-sms-proxy', label:'🪪 短信与代理'}, // 已合并到账号中心展开栏
    // {view:'matrix-collect', label:'📡 信息采集'},      // 已合并到账号中心批量操作
    // {view:'matrix-corpus', label:'📚 语料库'},         // 暂未上菜单（视图已迁移）
    {view:'matrix-nurture', label:'🏃 养号执行'},
    {view:'matrix-publish', label:'📤 内容发布'},
    {view:'matrix-interact', label:'💬 评论互动'},
    {view:'matrix-dm', label:'💬 私信沟通'},
    {view:'matrix-live', label:'🔴 直播互动'},
    {view:'comment-workbench', label:'🎭 评论工作台'},
    {view:'matrix-blueprints', label:'📋 蓝图管理'},
    // {view:'matrix-login', label:'🔑 登录管理'}, // 已合并到信息采集
    {view:'matrix-schedule', label:'⏱ 定时任务'},
    {view:'ops-recorder', label:'🎬 录制标注'},
    {view:'ops-command', label:'🖥️ 联邦指挥台'},
  ]},

  '视频工厂': { icon: '🎬', items: [
    {view:'workflow',    label:'🔀 工作流'},
    {view:'capabilities',label:'⚡ 能力目录'},
    {view:'person-swap', label:'🔄 人物置换'},
    {view:'characters',  label:'🧑 角色列表'},
    {view:'char-gen',    label:'🎭 角色生成器'},
    {view:'productions', label:'📋 生产记录'},
    {view:'assets',      label:'📦 素材库'},
    {view:'costs',       label:'💰 费用分析'},
  ]},

  '内容抓取': { icon: '📡', items: [
    {view:'crawl-tasks',   label:'📥 抓取任务'},
    {view:'crawl-sources', label:'📋 源管理'},
    {view:'crawl-history', label:'📜 抓取历史'},
  ]},

  '联邦': { icon: '🖥️', items: [
    {view:'fleet-sync',      label:'一键同步'},
    {view:'fleet-reconcile', label:'对账检查'},
    {view:'fleet-exec',      label:'远程Shell'},
    // {view:'matrix-commands', label:'🎯 命令与任务'}, // 旧菜单里有，当前生效菜单未上；需要时取消注释
  ]},

  '服务': { icon: '⚙️', items: [
    {view:'api-config',      label:'🔑 API 配置'},
    {view:'serve-mcp',       label:'MCP状态'},
    {view:'serve-dashboard', label:'Dashboard日志'},
    {view:'serve-schedule',  label:'全局定时任务'},
    {view:'timeline',        label:'📈 时间线'},
  ]},
};
