/**
 * 中文语言包
 */
const zh = {
  // ========== 通用 ==========
  common: {
    confirm: '确认',
    cancel: '取消',
    save: '保存',
    delete: '删除',
    edit: '编辑',
    create: '创建',
    search: '搜索',
    reset: '重置',
    refresh: '刷新',
    loading: '加载中...',
    noData: '暂无数据',
    success: '操作成功',
    failed: '操作失败',
    back: '返回',
    export: '导出',
    import: '导入',
    enable: '启用',
    disable: '禁用',
    status: '状态',
    actions: '操作',
    name: '名称',
    description: '描述',
    type: '类型',
    time: '时间',
    detail: '详情',
    all: '全部',
    yes: '是',
    no: '否',
    total: '共 {{count}} 条',
    close: '关闭',
    submit: '提交',
    view: '查看',
    copy: '复制',
    copied: '已复制',
  },

  // ========== 登录页 ==========
  login: {
    title: 'VigilOps',
    subtitle: 'AI 智能运维监控平台',
    loginTab: '登录',
    registerTab: '注册',
    ldapTab: 'LDAP',
    email: '邮箱',
    emailPlaceholder: '邮箱',
    password: '密码',
    passwordPlaceholder: '密码',
    username: '用户名',
    usernamePlaceholder: '用户名',
    usernameOrEmail: '用户名或邮箱',
    loginButton: '登录',
    registerButton: '注册',
    ldapLogin: 'LDAP 登录',
    demoButton: '🚀 Demo 体验（只读账号，无需注册）',
    loginSuccess: '登录成功',
    loginFailed: '登录失败',
    registerSuccess: '注册成功',
    registerFailed: '注册失败',
    ldapLoginSuccess: 'LDAP登录成功',
    ldapLoginFailed: 'LDAP登录失败',
    oauthFailed: 'OAuth登录失败',
    oauthTitle: '或使用第三方账号登录',
    ldapNotAvailable: 'LDAP 认证未配置或不可用',
    validation: {
      emailRequired: '请输入邮箱',
      emailInvalid: '邮箱格式不正确',
      passwordRequired: '请输入密码',
      passwordMin: '密码至少6位',
      usernameRequired: '请输入用户名',
      usernameOrEmailRequired: '请输入用户名或邮箱',
    },
    features: {
      tagline: '为中小企业而生',
      aiAnalysis: 'AI 智能分析',
      aiAnalysisDesc: '基于 AI 的根因分析与运维洞察',
      autoRemediation: '自动修复',
      autoRemediationDesc: '内置 Runbook，告警触发自动修复',
      realTimeMonitoring: '实时监控',
      realTimeMonitoringDesc: 'WebSocket 实时推送，秒级感知',
      slaManagement: 'SLA 管理',
      slaManagementDesc: '可用性追踪与错误预算管理',
    },
    footer: {
      company: '琳创科技（LinChuang Technology）',
    },
  },

  // ========== 侧边栏菜单 ==========
  menu: {
    dashboard: '仪表盘',
    hosts: '服务器',
    services: '服务监控',
    topology: '拓扑图',
    topologyService: '服务拓扑',
    topologyServers: '多服务器',
    topologyServiceGroups: '服务组',
    logs: '日志管理',
    databases: '数据库监控',
    alerts: '告警中心',
    alertEscalation: '告警升级',
    onCall: '值班排期',
    remediation: '自动修复',
    sla: 'SLA 管理',
    aiAnalysis: 'AI 分析',
    reports: '运维报告',
    notificationChannels: '通知渠道',
    notificationTemplates: '通知模板',
    notificationLogs: '通知日志',
    users: '用户管理',
    auditLogs: '审计日志',
    settings: '系统设置',
    groupMonitoring: '监控',
    groupLogsAlerts: '日志与告警',
    groupAutomation: '自动化',
    groupAI: 'AI',
    groupNotifications: '通知',
    groupSystem: '系统',
  },

  // ========== 顶部栏 ==========
  header: {
    lightMode: '切换亮色模式',
    darkMode: '切换暗色模式',
    logout: '退出登录',
    language: '语言',
  },

  // ========== 仪表盘 ==========
  dashboard: {
    title: '仪表盘',
    totalHosts: '服务器总数',
    onlineHosts: '在线服务器',
    totalAlerts: '告警总数',
    firingAlerts: '活跃告警',
    avgCpu: '平均 CPU',
    avgMemory: '平均内存',
    healthScore: '健康评分',
    recentAlerts: '最近告警',
    resourceUsage: '资源使用',
    trend: '趋势',
    customize: '自定义布局',
    resetLayout: '重置布局',
    exportLayout: '导出布局',
    importLayout: '导入布局',
    settings: '仪表盘设置',
    logStats: '日志统计',
    serverOverview: '服务器概览',
  },

  // ========== 告警 ==========
  alerts: {
    title: '告警中心',
    alertList: '告警列表',
    alertRules: '告警规则',
    severity: '严重级别',
    status: '状态',
    source: '来源',
    message: '告警信息',
    triggeredAt: '触发时间',
    resolvedAt: '解决时间',
    acknowledged: '已确认',
    acknowledge: '确认',
    rootCause: 'AI 根因分析',
    rootCauseTitle: 'AI 根因分析',
    analyzing: '正在分析中...',
    confidence: '置信度',
    evidence: '证据',
    recommendations: '修复建议',
    analysisFailed: 'AI 分析失败',
    severityLevels: {
      critical: '严重',
      warning: '警告',
      info: '信息',
    },
    statusTypes: {
      firing: '触发中',
      resolved: '已解决',
      acknowledged: '已确认',
    },
    rules: {
      name: '规则名称',
      type: '规则类型',
      metric: '指标告警',
      logKeyword: '日志关键字告警',
      database: '数据库告警',
      condition: '条件',
      threshold: '阈值',
      enabled: '已启用',
      disabled: '已禁用',
      create: '创建规则',
      edit: '编辑规则',
      delete: '删除规则',
      silencePeriod: '静默时段',
    },
  },

  // ========== 服务器 ==========
  hosts: {
    title: '服务器列表',
    hostname: '主机名',
    ip: 'IP 地址',
    os: '操作系统',
    cpu: 'CPU 使用率',
    memory: '内存使用率',
    disk: '磁盘使用率',
    status: '状态',
    uptime: '运行时间',
    lastSeen: '最后上报',
    online: '在线',
    offline: '离线',
    detail: '服务器详情',
    metrics: '性能指标',
    processes: '进程列表',
  },

  // ========== 服务监控 ==========
  services: {
    title: '服务监控',
    serviceName: '服务名称',
    url: '监控地址',
    method: '请求方法',
    interval: '检查间隔',
    timeout: '超时时间',
    status: '状态',
    responseTime: '响应时间',
    uptime: '可用率',
    healthy: '健康',
    unhealthy: '异常',
    create: '添加服务',
  },

  // ========== 日志管理 ==========
  logs: {
    title: '日志管理',
    search: '搜索日志',
    level: '日志级别',
    source: '来源',
    timestamp: '时间',
    message: '日志内容',
    filter: '筛选',
    realtime: '实时',
    levels: {
      error: '错误',
      warn: '警告',
      info: '信息',
      debug: '调试',
    },
  },

  // ========== 数据库监控 ==========
  databases: {
    title: '数据库监控',
    name: '数据库名称',
    type: '类型',
    host: '主机',
    port: '端口',
    status: '状态',
    connections: '连接数',
    slowQueries: '慢查询',
    size: '数据量',
    detail: '数据库详情',
  },

  // ========== SLA 管理 ==========
  sla: {
    title: 'SLA 管理',
    serviceName: '服务名称',
    target: '目标 SLA',
    current: '当前 SLA',
    errorBudget: '错误预算',
    remaining: '剩余',
    consumed: '已消耗',
    period: '统计周期',
  },

  // ========== 自动修复 ==========
  remediation: {
    title: '自动修复',
    runbook: 'Runbook',
    trigger: '触发条件',
    lastRun: '最后执行',
    status: '状态',
    result: '执行结果',
    history: '执行历史',
    running: '执行中',
    success: '成功',
    failed: '失败',
    pending: '等待中',
  },

  // ========== AI 分析 ==========
  aiAnalysis: {
    title: 'AI 分析',
    analyze: '开始分析',
    result: '分析结果',
    history: '分析历史',
    prompt: '分析提示',
  },

  // ========== 运维报告 ==========
  reports: {
    title: '运维报告',
    generate: '生成报告',
    period: '报告周期',
    daily: '日报',
    weekly: '周报',
    monthly: '月报',
  },

  // ========== 通知 ==========
  notifications: {
    channels: '通知渠道',
    templates: '通知模板',
    logs: '通知日志',
    channelName: '渠道名称',
    channelType: '渠道类型',
    template: '模板',
    sent: '已发送',
    failed: '发送失败',
    pending: '待发送',
  },

  // ========== 用户管理 ==========
  users: {
    title: '用户管理',
    username: '用户名',
    email: '邮箱',
    role: '角色',
    status: '状态',
    createdAt: '创建时间',
    lastLogin: '最后登录',
    roles: {
      admin: '管理员',
      member: '成员',
      viewer: '只读',
    },
  },

  // ========== 审计日志 ==========
  auditLogs: {
    title: '审计日志',
    user: '操作用户',
    action: '操作类型',
    resource: '资源',
    timestamp: '操作时间',
    detail: '详细信息',
  },

  // ========== 告警升级 ==========
  alertEscalation: {
    title: '告警升级',
    policy: '升级策略',
    level: '升级级别',
    timeout: '超时时间',
    notifyTo: '通知人',
  },

  // ========== 值班排期 ==========
  onCall: {
    title: '值班排期',
    schedule: '排期',
    oncallPerson: '值班人',
    startTime: '开始时间',
    endTime: '结束时间',
    rotation: '轮转',
  },

  // ========== 系统设置 ==========
  settings: {
    title: '系统设置',
    general: '常规设置',
    agentTokens: 'Agent Token 管理',
    tokenName: 'Token 名称',
    tokenValue: 'Token 值',
    createToken: '创建 Token',
    revokeToken: '吊销 Token',
    active: '活跃',
    revoked: '已吊销',
    saveSuccess: '设置保存成功',
    saveFailed: '保存失败',
  },

  // ========== 拓扑图 ==========
  topology: {
    title: '拓扑图',
    serviceTopology: '服务拓扑',
    multiServer: '多服务器',
    serviceGroups: '服务组',
  },

  // ========== 通用状态组件 ==========
  state: {
    loading: '加载中...',
    error: {
      retry: '重新加载',
      network: {
        title: '网络连接异常',
        description: '无法连接到服务器，请检查网络连接后重试。',
      },
      permission: {
        title: '没有访问权限',
        description: '您没有权限访问此资源，请联系管理员。',
      },
      server: {
        title: '服务器错误',
        description: '服务器处理请求时出错，请稍后重试。',
      },
      notfound: {
        title: '资源不存在',
        description: '请求的资源不存在或已被删除。',
      },
      unknown: {
        title: '加载失败',
        description: '数据加载出错，请稍后重试。',
      },
    },
    empty: {
      start: '开始',
      dashboard: {
        title: '暂无监控数据',
        description: '还没有主机上报数据，请先添加主机并安装 Agent。',
        actionText: '添加主机',
      },
      servers: {
        title: '暂无服务器',
        description: '还没有服务器数据，请先添加主机并安装 Agent 开始监控。',
        actionText: '添加主机',
      },
      alerts: {
        title: '暂无告警',
        description: '当前没有任何告警，系统运行正常。您可以配置告警规则来监控关键指标。',
        actionText: '配置告警规则',
      },
      notifications: {
        title: '暂无通知记录',
        description: '还没有发送过通知。当告警触发时，系统会自动通过配置的渠道发送通知。',
        actionText: '配置通知渠道',
      },
      reports: {
        title: '暂无报告',
        description: '还没有生成过运维报告。您可以生成日报或周报来查看系统运行概况。',
        actionText: '生成报告',
      },
      topology: {
        title: '暂无拓扑数据',
        description: '还没有服务拓扑信息，请先添加服务并配置依赖关系。',
      },
      default: {
        title: '暂无数据',
        description: '当前没有数据。',
      },
    },
  },
};

export default zh;
