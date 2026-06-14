# 归档脚本索引

> 归档时间: 2026-06-14
> 原路径: `scripts/` → `scripts/archive/`
> 归档原因: 这些脚本来自 Phase A/B 的测试和调试阶段, 当前系统已不再使用。
> 保留以备需要时参考或恢复。

---

## 归档列表

### 测试类 (19个)
| 文件 | 说明 |
|------|------|
| final_test.py | 最终测试 |
| full_test.py | 全量测试 |
| hybrid_test.py | 混合测试 |
| interactive_test.py | 交互测试 |
| step_by_step.py | 分步执行测试 |
| enter_video_test.py | 进入视频页测试 |
| find_and_send.py | 查找并发送测试 |
| find_send_btn.py | 查找发送按钮 |
| test_send.py | 发送测试 |
| test_sms_login.py | 短信登录测试 |
| calibrate_input.py | 输入校准测试 |
| click_and_type.py | 点击输入测试 |
| smart_input.py | 智能输入测试 |
| hybrid_input.py | 混合输入测试 |
| verify_calibrate.py | 校准验证 |
| comment_test_runner.py | 评论测试运行器 |
| search_like5.py | 搜索点赞5次测试 |
| final_chain.py | 最终链路测试 |
| comment_video.py | 视频评论测试 |

### 扫描/检测类 (8个)
| 文件 | 说明 |
|------|------|
| scan_all_inputs.py | 扫描所有输入框 |
| scan_flat.py | 平面扫描 |
| scan_login.py | 登录扫描 |
| scan_video_page.py | 视频页扫描 |
| diag_chrome.py | Chrome 诊断 |
| diag_douyin.py | 抖音诊断 |
| diag_fast.py | 快速诊断 |
| diag_window.py | 窗口诊断 |

### 评论相关 (5个)
| 文件 | 说明 |
|------|------|
| specific_comment.py | 指定评论 |
| robust_comment.py | 健壮评论 |
| comment_chain.py | 评论链 |
| auto_comment.py | 自动评论 |
| clipboard_comment.py | 剪贴板评论 |

### 工具类 (9个)
| 文件 | 说明 |
|------|------|
| init_db.py | 数据库初始化 |
| seed_db.py | 数据库种子数据 |
| gen_report.py | 生成报告 |
| fix_phone.py | 手机号修复 |
| browser_keepalive.py | 浏览器保活 |
| camoufox_server.py | Camoufox 服务端 |
| deep_scan.py | 深度扫描 |
| anchor_collector.py | 锚点采集器 |
| scanner_daemon.py | 扫描守护进程 |

### Shell 脚本 (6个)
| 文件 | 说明 |
|------|------|
| install_tianxing_vpn.sh | 安装天行 VPN |
| launch_chrome.sh | 启动 Chrome |
| nurture_daily.sh | 每日养号 |
| nurture_master.sh | 主控养号 |
| run_all.sh | 全部运行 |
| vpn_nurture.sh | VPN 养号 |

---

## 恢复方法

```bash
cd ~/workbuddy-agent-os/agent-sync/05_tools/07_matrix/scripts
mv archive/xxx.py .
```
