-- 017: Default notification templates seed data
-- 默认中文通知模板（幂等：按 name 判断是否已存在）

INSERT INTO notification_templates (name, channel_type, subject_template, body_template, is_default)
SELECT * FROM (VALUES
    (
        '告警触发通知'::VARCHAR,
        'all'::VARCHAR,
        '【VigilOps 告警】{severity}: {title}'::VARCHAR,
        '🚨 告警触发

📋 告警名称: {title}
⚠️ 严重级别: {severity}
🖥️ 主机: {host}
📊 当前值: {metric_value}
📏 阈值: {threshold}
🕐 触发时间: {fired_at}

📝 详情: {message}'::TEXT,
        TRUE
    ),
    (
        '告警恢复通知',
        'all',
        '【VigilOps 恢复】{title} 已恢复',
        '✅ 告警恢复

📋 告警名称: {title}
⚠️ 原严重级别: {severity}
🖥️ 主机: {host}
🕐 触发时间: {fired_at}
🕐 恢复时间: {resolved_at}
⏱️ 持续时长: {duration}

系统已恢复正常运行。',
        TRUE
    ),
    (
        '自动修复成功通知',
        'all',
        '【VigilOps 修复】{title} 自动修复成功',
        '🔧 自动修复成功

📋 关联告警: {title}
🖥️ 主机: {host}
📖 执行 Runbook: {runbook}
🕐 执行时间: {executed_at}
⏱️ 耗时: {duration}

✅ 修复操作已成功执行，系统恢复正常。',
        FALSE
    ),
    (
        '自动修复失败通知',
        'all',
        '【VigilOps 修复失败】{title} 自动修复失败',
        '❌ 自动修复失败

📋 关联告警: {title}
🖥️ 主机: {host}
📖 执行 Runbook: {runbook}
🕐 执行时间: {executed_at}
❗ 失败原因: {error}

⚠️ 请立即人工介入处理。',
        FALSE
    )
) AS v(name, channel_type, subject_template, body_template, is_default)
WHERE NOT EXISTS (SELECT 1 FROM notification_templates nt WHERE nt.name = v.name);
