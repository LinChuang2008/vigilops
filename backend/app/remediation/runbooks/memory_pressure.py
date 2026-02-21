"""
VigilOps 自动修复 Runbook - 内存压力缓解
VigilOps Automatic Remediation Runbook - Memory Pressure Relief

这是一个内存压力缓解脚本，用于处理内存使用率过高或即将发生 OOM 的告警。
This is a memory pressure relief script for handling high memory usage or impending OOM alerts.

适用场景 (Applicable Scenarios):
- 系统内存使用率超过 80% (System memory usage exceeds 80%)
- 收到 OOM (Out of Memory) 警告 (Received OOM warning)
- Swap 使用率异常升高 (Abnormal increase in swap usage)
- 应用程序内存泄漏导致的内存压力 (Memory pressure caused by application memory leaks)

缓解策略 (Relief Strategy):
1. 诊断优先：首先分析内存使用情况和主要消耗者
2. 安全释放：清理可安全释放的系统缓存
3. 非破坏性：不杀死进程，不影响正在运行的应用
4. 可恢复性：清理的缓存可以自动重建

技术原理 (Technical Principles):
- Page Cache 清理：释放文件系统缓存，不影响数据安全
- 缓存同步：确保脏页被写入磁盘后再清理
- 内存监控：通过系统工具识别内存使用模式

风险评估 (Risk Assessment):
- 风险等级：CONFIRM（需要确认）
- 原因：虽然操作相对安全，但涉及系统核心内存管理
- 影响：可能短暂影响系统性能（缓存重建）
- 可逆性：清理的缓存会在后续访问中自动重建

注意事项 (Important Notes):
- drop_caches 是安全操作，但会暂时影响 I/O 性能
- 此 Runbook 不会终止进程，如需更激进的内存回收需要人工介入
- 效果通常是临时的，需要配合应用层面的内存优化

预期效果 (Expected Results):
- 释放 100MB - 2GB 的系统缓存（取决于系统负载）
- 降低内存使用率 5-20%
- 为系统运行争取缓冲时间
- 提供内存使用诊断信息

作者：VigilOps Team
版本：v1.0
风险等级：MEDIUM
"""
from ..models import RiskLevel, RunbookDefinition, RunbookStep

RUNBOOK = RunbookDefinition(
    name="memory_pressure",
    description="Relieve memory pressure by clearing caches and identifying memory hogs",
    match_alert_types=["high_memory", "oom_warning", "memory_usage_high", "swap_usage_high"],
    match_keywords=["memory", "OOM", "out of memory", "swap", "ram"],
    risk_level=RiskLevel.CONFIRM,
    commands=[
        RunbookStep(description="Show current memory usage", command="free -h", timeout_seconds=10),
        RunbookStep(description="List top memory consumers", command="ps aux --sort=-%mem | head -10", timeout_seconds=10),
        RunbookStep(description="Sync filesystem buffers", command="sync", timeout_seconds=15),
        RunbookStep(description="Drop page cache (safe, recoverable)", command="echo 3 > /proc/sys/vm/drop_caches", timeout_seconds=10),
    ],
    verify_commands=[
        RunbookStep(description="Check memory after cleanup", command="free -h", timeout_seconds=10),
    ],
    cooldown_seconds=600,
)
