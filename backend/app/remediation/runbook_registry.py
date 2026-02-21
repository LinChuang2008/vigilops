"""
VigilOps 自动修复系统 - Runbook 注册中心
VigilOps Remediation System - Runbook Registry

这是自动修复系统的 Runbook 管理中心，负责注册、存储和匹配各种修复脚本。
This is the Runbook management center of the remediation system, responsible for 
registering, storing and matching various remediation scripts.

核心职责 (Core Responsibilities):
1. 统一管理所有可用的 Runbook 定义
2. 根据告警信息和 AI 诊断结果智能匹配最佳 Runbook  
3. 提供 Runbook 的注册、查询、列表等管理功能
4. 支持多种匹配策略：AI 推荐、类型匹配、关键词匹配

匹配策略 (Matching Strategies):
优先级从高到低：
1. AI 智能推荐：基于 AI 分析的精准推荐
2. 告警类型匹配：基于预定义的告警类型映射
3. 关键词匹配：基于告警内容的文本分析
4. 多候选评分：当有多个匹配时选择最佳候选

内置 Runbook (Built-in Runbooks):
- disk_cleanup: 磁盘空间清理
- service_restart: 服务重启修复  
- zombie_killer: 僵尸进程清理
- memory_pressure: 内存压力释放
- log_rotation: 日志轮转压缩
- connection_reset: 网络连接重置

设计理念 (Design Philosophy):
采用简单的字典结构而非复杂的插件系统，保持代码简洁和性能高效。
支持运行时动态注册新的 Runbook，便于扩展和测试。

作者：VigilOps Team
版本：v1.0  
"""
from __future__ import annotations

import logging

from .models import Diagnosis, RemediationAlert, RunbookDefinition

logger = logging.getLogger(__name__)

# 导入所有内置 Runbook 定义 (Import all built-in Runbook definitions)
from .runbooks.connection_reset import RUNBOOK as CONNECTION_RESET      # 网络连接重置 (Network connection reset)
from .runbooks.disk_cleanup import RUNBOOK as DISK_CLEANUP              # 磁盘空间清理 (Disk space cleanup)
from .runbooks.log_rotation import RUNBOOK as LOG_ROTATION              # 日志轮转压缩 (Log rotation and compression)
from .runbooks.memory_pressure import RUNBOOK as MEMORY_PRESSURE        # 内存压力释放 (Memory pressure relief)
from .runbooks.service_restart import RUNBOOK as SERVICE_RESTART        # 服务重启修复 (Service restart remediation)
from .runbooks.zombie_killer import RUNBOOK as ZOMBIE_KILLER            # 僵尸进程清理 (Zombie process cleanup)


class RunbookRegistry:
    """Runbook 注册中心 (Runbook Registry)
    
    这是 VigilOps 自动修复系统的核心组件之一，负责管理所有可用的修复脚本。
    This is one of the core components of VigilOps remediation system, responsible for 
    managing all available remediation scripts.
    
    架构设计 (Architecture Design):
    采用注册表模式 (Registry Pattern) 管理 Runbook 的生命周期：
    - 初始化时自动注册所有内置 Runbook
    - 支持运行时动态注册新的 Runbook
    - 提供统一的查询和匹配接口
    - 维护 name -> RunbookDefinition 的映射关系
    
    匹配算法 (Matching Algorithm):
    实现多层次的智能匹配策略：
    1. AI 推荐优先：信任 AI 的专业判断
    2. 精确类型匹配：基于预定义的告警类型
    3. 模糊关键词匹配：基于文本内容分析
    4. 评分排序：多候选时选择最佳匹配
    
    扩展性 (Extensibility):
    - 支持外部 Runbook 的动态注册
    - 匹配策略可以独立修改和优化
    - 不依赖复杂的插件系统，保持简洁
    
    性能考虑 (Performance Considerations):
    - 使用字典存储实现 O(1) 查询时间复杂度
    - 匹配过程避免复杂的正则表达式
    - 延迟加载不必要的计算操作
    """

    def __init__(self) -> None:
        """初始化 Runbook 注册中心 (Initialize Runbook Registry)
        
        创建空的注册表并自动注册所有内置的 Runbook。
        Create empty registry and automatically register all built-in Runbooks.
        
        初始化过程 (Initialization Process):
        1. 创建空的 Runbook 字典存储
        2. 调用 _register_defaults() 注册所有内置 Runbook
        3. 记录注册成功的 Runbook 数量到日志
        """
        self._runbooks: dict[str, RunbookDefinition] = {}  # Runbook 名称到定义的映射 (Name to definition mapping)
        self._register_defaults()  # 注册所有内置 Runbook (Register all built-in Runbooks)

    def _register_defaults(self) -> None:
        """注册所有内置 Runbook (Register All Built-in Runbooks)
        
        批量注册 VigilOps 系统内置的 6 个标准修复脚本。
        Batch register 6 standard remediation scripts built into VigilOps system.
        
        内置 Runbook 清单 (Built-in Runbook List):
        - DISK_CLEANUP: 磁盘空间不足时的清理操作
        - SERVICE_RESTART: 服务异常时的重启修复
        - ZOMBIE_KILLER: 清理系统中的僵尸进程  
        - MEMORY_PRESSURE: 内存使用率过高时的释放操作
        - LOG_ROTATION: 日志文件过大时的轮转压缩
        - CONNECTION_RESET: 网络连接异常时的重置操作
        """
        # 按功能重要性排序的内置 Runbook 列表 (Built-in Runbooks sorted by functional importance)
        for runbook in [
            DISK_CLEANUP,      # 磁盘清理 - 最常见的问题
            SERVICE_RESTART,   # 服务重启 - 通用修复手段
            ZOMBIE_KILLER,     # 进程清理 - 系统健康维护
            MEMORY_PRESSURE,   # 内存管理 - 性能优化
            LOG_ROTATION,      # 日志管理 - 存储优化
            CONNECTION_RESET,  # 网络修复 - 连接问题处理
        ]:
            self.register(runbook)  # 逐个注册到注册表 (Register one by one to registry)

    def register(self, runbook: RunbookDefinition) -> None:
        """注册单个 Runbook (Register Single Runbook)
        
        将一个 Runbook 定义添加到注册表中，支持动态注册和覆盖已有定义。
        Add a Runbook definition to the registry, supporting dynamic registration 
        and overriding existing definitions.
        
        Args:
            runbook: 要注册的 Runbook 定义 (Runbook definition to register)
            
        行为说明 (Behavior Description):
        - 如果名称已存在，新定义会覆盖旧定义
        - 注册成功后会记录调试日志
        - 支持运行时动态添加新的修复脚本
        
        使用场景 (Use Cases):
        - 系统启动时批量注册内置 Runbook
        - 运行时添加自定义修复脚本
        - 更新现有 Runbook 的定义
        - 测试时注册临时的 Mock Runbook
        """
        self._runbooks[runbook.name] = runbook  # 添加到注册表 (Add to registry)
        logger.debug("Registered runbook: %s", runbook.name)  # 记录注册日志 (Log registration)

    def get(self, name: str) -> RunbookDefinition | None:
        """根据名称获取 Runbook (Get Runbook by Name)
        
        Args:
            name: Runbook 名称 (Runbook name)
            
        Returns:
            RunbookDefinition | None: 找到则返回定义，否则返回 None
            
        时间复杂度 (Time Complexity): O(1)
        """
        return self._runbooks.get(name)

    def list_all(self) -> list[RunbookDefinition]:
        """获取所有已注册的 Runbook 列表 (Get List of All Registered Runbooks)
        
        Returns:
            list[RunbookDefinition]: 所有 Runbook 定义的列表副本
            
        注意 (Note):
        返回列表的副本以防止外部修改影响注册表内部状态
        """
        return list(self._runbooks.values())  # 返回副本防止外部修改 (Return copy to prevent external modification)

    def match(self, alert: RemediationAlert, diagnosis: Diagnosis) -> RunbookDefinition | None:
        """智能匹配最佳 Runbook (Intelligently Match Best Runbook)
        
        这是注册中心的核心方法，负责根据告警信息和 AI 诊断结果选择最合适的修复脚本。
        This is the core method of the registry, responsible for selecting the most 
        appropriate remediation script based on alert information and AI diagnosis.
        
        匹配策略优先级 (Matching Strategy Priority):
        1. AI 智能推荐 (AI Recommendation): 
           - 最高优先级，信任 AI 的专业判断
           - 如果 AI 推荐的 Runbook 存在且可用，直接返回
           
        2. 告警类型精确匹配 (Alert Type Exact Match):
           - 基于预定义的告警类型映射表
           - 如果只有一个匹配，直接返回
           - 如果有多个匹配，进入关键词评分环节
           
        3. 关键词模糊匹配 (Keyword Fuzzy Match):
           - 分析告警消息和类型中的关键词
           - 计算每个 Runbook 的关键词匹配分数
           - 返回得分最高的 Runbook
        
        Args:
            alert: 告警信息，包含类型、消息、主机等 (Alert info with type, message, host etc.)
            diagnosis: AI 诊断结果，包含推荐的 Runbook (AI diagnosis with recommended Runbook)
            
        Returns:
            RunbookDefinition | None: 匹配的 Runbook，无匹配时返回 None
            
        日志记录 (Logging):
        记录匹配过程和结果，便于调试和监控匹配效果
        
        性能优化 (Performance Optimization):
        采用短路求值，找到匹配后立即返回，避免不必要的计算
        """
        # 策略 1: AI 智能推荐优先 (Strategy 1: AI recommendation takes priority)
        if diagnosis.suggested_runbook:
            runbook = self._runbooks.get(diagnosis.suggested_runbook)
            if runbook:
                logger.info("Matched runbook '%s' via AI suggestion", runbook.name)
                return runbook  # AI 推荐且存在，直接返回 (AI recommended and exists, return directly)
            # AI 推荐的 Runbook 不存在，记录警告并继续其他策略 (AI suggested runbook doesn't exist, log warning and continue)
            logger.warning("AI suggested unknown runbook: %s", diagnosis.suggested_runbook)

        # 策略 2: 告警类型精确匹配 (Strategy 2: Alert type exact match)
        type_matches = [
            rb for rb in self._runbooks.values()
            if alert.alert_type in rb.match_alert_types  # 检查告警类型是否在 Runbook 的匹配列表中
        ]
        
        if len(type_matches) == 1:
            # 唯一匹配：直接返回 (Unique match: return directly)
            logger.info("Matched runbook '%s' via alert type", type_matches[0].name)
            return type_matches[0]
            
        if len(type_matches) > 1:
            # 多个匹配：使用关键词评分选择最佳 (Multiple matches: use keyword scoring for best selection)
            return self._best_keyword_match(alert, type_matches)

        # 策略 3: 关键词模糊匹配作为后备方案 (Strategy 3: Keyword fuzzy match as fallback)
        all_matches = self._keyword_match_all(alert)
        if all_matches:
            # 找到关键词匹配，返回第一个（已按评分排序） (Found keyword match, return first one - already sorted by score)
            logger.info("Matched runbook '%s' via keyword fallback", all_matches[0].name)
            return all_matches[0]

        # 所有策略都无法匹配，记录警告并返回空值 (All strategies failed to match, log warning and return None)
        logger.warning("No runbook matched for alert: %s", alert.alert_type)
        return None

    def _best_keyword_match(
        self, alert: RemediationAlert, candidates: list[RunbookDefinition]
    ) -> RunbookDefinition:
        """从候选 Runbook 中选择关键词匹配度最高的 (Select Runbook with Highest Keyword Match from Candidates)
        
        当有多个 Runbook 都匹配告警类型时，使用关键词评分算法选择最佳候选。
        When multiple Runbooks match the alert type, use keyword scoring algorithm to select best candidate.
        
        评分算法 (Scoring Algorithm):
        1. 提取告警消息和类型的文本内容
        2. 将文本转换为小写进行大小写不敏感匹配
        3. 计算每个候选 Runbook 的关键词命中数
        4. 按得分降序排序，返回得分最高的 Runbook
        
        Args:
            alert: 告警信息 (Alert information)
            candidates: 候选 Runbook 列表 (Candidate Runbook list)
            
        Returns:
            RunbookDefinition: 得分最高的 Runbook
            
        时间复杂度 (Time Complexity): O(n*m*k) 
        其中 n=候选数，m=平均关键词数，k=文本长度
        """
        # 构建告警的文本内容用于关键词匹配 (Build alert text content for keyword matching)
        alert_text = f"{alert.message} {alert.alert_type}".lower()

        def score(rb: RunbookDefinition) -> int:
            """计算 Runbook 的关键词匹配得分 (Calculate keyword match score for Runbook)
            
            得分规则：每匹配一个关键词得 1 分，总分越高越优先
            Scoring rule: 1 point per matched keyword, higher total score takes priority
            """
            return sum(1 for kw in rb.match_keywords if kw.lower() in alert_text)

        # 按得分降序排序，返回最佳匹配 (Sort by score in descending order, return best match)
        return sorted(candidates, key=score, reverse=True)[0]

    def _keyword_match_all(self, alert: RemediationAlert) -> list[RunbookDefinition]:
        """获取所有关键词匹配的 Runbook 列表 (Get List of All Keyword-Matched Runbooks)
        
        当告警类型无法精确匹配时，使用关键词进行模糊匹配。
        When alert type cannot be exactly matched, use keywords for fuzzy matching.
        
        匹配逻辑 (Matching Logic):
        1. 遍历所有注册的 Runbook
        2. 检查告警文本是否包含 Runbook 的任一关键词
        3. 一旦找到匹配关键词就将 Runbook 加入结果列表
        4. 返回所有匹配的 Runbook（未排序）
        
        Args:
            alert: 告警信息 (Alert information)
            
        Returns:
            list[RunbookDefinition]: 所有关键词匹配的 Runbook 列表
            
        注意 (Note):
        返回的列表未按优先级排序，调用方需要自行处理排序逻辑
        """
        # 构建小写的告警文本用于大小写不敏感匹配 (Build lowercase alert text for case-insensitive matching)
        alert_text = f"{alert.message} {alert.alert_type}".lower()
        
        matches = []  # 存储匹配的 Runbook 列表 (Store matched Runbook list)
        
        # 遍历所有注册的 Runbook (Iterate through all registered Runbooks)
        for runbook in self._runbooks.values():
            # 检查该 Runbook 的所有关键词 (Check all keywords of this Runbook)
            for keyword in runbook.match_keywords:
                if keyword.lower() in alert_text:  # 关键词匹配成功 (Keyword match successful)
                    matches.append(runbook)
                    break  # 找到一个匹配就足够了，避免重复添加 (One match is enough, avoid duplicate addition)
                    
        return matches  # 返回所有匹配的 Runbook (Return all matched Runbooks)
