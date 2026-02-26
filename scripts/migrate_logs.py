#!/usr/bin/env python3
"""
日志数据迁移脚本 (Log Data Migration Script)

用于在不同日志后端之间迁移数据的命令行工具。
支持 PostgreSQL、ClickHouse、Loki 之间的数据迁移。

用法:
    python migrate_logs.py --source postgresql --target clickhouse
    python migrate_logs.py --source postgresql --target clickhouse --batch-size 5000
    python migrate_logs.py --source clickhouse --target postgresql --dry-run
    
特性:
- 批量处理，避免内存溢出
- 支持干运行模式预览迁移计划
- 实时进度显示
- 错误恢复和重试机制
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import async_session
from app.core.config import settings
from app.services.log_service import get_log_service
from app.core.log_backend import LogBackendType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_logs(
    source: str,
    target: str,
    batch_size: int = 1000,
    dry_run: bool = False,
    start_date: str = None,
    end_date: str = None
):
    """
    执行日志数据迁移
    
    Args:
        source: 源后端类型
        target: 目标后端类型
        batch_size: 批处理大小
        dry_run: 是否为干运行（仅显示统计，不实际迁移）
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    """
    logger.info(f"Starting log migration: {source} → {target}")
    logger.info(f"Batch size: {batch_size}, Dry run: {dry_run}")
    
    if start_date:
        logger.info(f"Date range: {start_date} to {end_date or 'now'}")
    
    async with async_session() as db:
        try:
            # 获取日志服务
            log_service = await get_log_service(db)
            
            if dry_run:
                logger.info("=== DRY RUN MODE - No actual data will be migrated ===")
                
                # 获取源后端统计信息
                from sqlalchemy import select, func
                from app.models.log_entry import LogEntry
                
                count_stmt = select(func.count(LogEntry.id))
                
                # 应用日期过滤
                if start_date:
                    start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
                    count_stmt = count_stmt.where(LogEntry.timestamp >= start_dt)
                if end_date:
                    end_dt = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
                    count_stmt = count_stmt.where(LogEntry.timestamp <= end_dt)
                
                result = await db.execute(count_stmt)
                total_count = result.scalar() or 0
                
                logger.info(f"Total logs to migrate: {total_count:,}")
                logger.info(f"Estimated batches: {(total_count + batch_size - 1) // batch_size}")
                logger.info(f"Estimated time: {total_count / batch_size * 0.1:.1f} seconds")
                
                # 检查目标后端健康状态
                health = await log_service.health_check()
                target_health = health.get("primary_backend", {}).get("healthy", False)
                
                if target_health:
                    logger.info("✓ Target backend is healthy")
                else:
                    logger.warning("✗ Target backend health check failed")
                    logger.warning("Migration might fail, check backend configuration")
                
                logger.info("=== DRY RUN COMPLETED ===")
                return
            
            # 执行实际迁移
            result = await log_service.migrate_data(
                source=source,
                target=target,
                batch_size=batch_size
            )
            
            if "error" in result:
                logger.error(f"Migration failed: {result['error']}")
                return False
            
            # 显示迁移结果
            logger.info("=== MIGRATION COMPLETED ===")
            logger.info(f"Total records: {result['total_count']:,}")
            logger.info(f"Migrated successfully: {result['migrated_count']:,}")
            logger.info(f"Errors: {result['error_count']:,}")
            logger.info(f"Success rate: {result['success_rate']:.2%}")
            
            return True
            
        except Exception as e:
            logger.exception(f"Migration failed: {e}")
            return False


async def validate_backend(backend_type: str) -> bool:
    """验证后端类型和连接"""
    valid_backends = [bt.value for bt in LogBackendType]
    
    if backend_type not in valid_backends:
        logger.error(f"Invalid backend type: {backend_type}")
        logger.error(f"Valid backends: {', '.join(valid_backends)}")
        return False
    
    # 测试连接
    try:
        async with async_session() as db:
            log_service = await get_log_service(db)
            health = await log_service.health_check()
            
            if backend_type == "postgresql":
                # PostgreSQL总是可用的
                return True
            elif backend_type == "clickhouse":
                backend_health = health.get("primary_backend", {})
                if backend_health.get("type") == "clickhouse":
                    return backend_health.get("healthy", False)
                else:
                    logger.error("ClickHouse not configured as primary backend")
                    return False
            elif backend_type == "loki":
                logger.error("Loki backend not implemented yet")
                return False
                
    except Exception as e:
        logger.error(f"Backend validation failed: {e}")
        return False
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Migrate logs between different backends",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate from PostgreSQL to ClickHouse
  python migrate_logs.py --source postgresql --target clickhouse
  
  # Dry run to check migration plan
  python migrate_logs.py --source postgresql --target clickhouse --dry-run
  
  # Migrate with custom batch size
  python migrate_logs.py --source postgresql --target clickhouse --batch-size 5000
  
  # Migrate logs from specific date range
  python migrate_logs.py --source postgresql --target clickhouse \\
                        --start-date 2024-01-01 --end-date 2024-01-31
                        
  # Migrate back from ClickHouse to PostgreSQL
  python migrate_logs.py --source clickhouse --target postgresql
        """
    )
    
    parser.add_argument(
        "--source", 
        required=True,
        choices=["postgresql", "clickhouse", "loki"],
        help="Source backend type"
    )
    
    parser.add_argument(
        "--target",
        required=True,
        choices=["postgresql", "clickhouse", "loki"],
        help="Target backend type"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for processing (default: 1000)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show migration plan without actual data transfer"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for migration (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str,
        help="End date for migration (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 验证参数
    if args.source == args.target:
        logger.error("Source and target backends cannot be the same")
        sys.exit(1)
    
    if args.batch_size < 100 or args.batch_size > 10000:
        logger.error("Batch size must be between 100 and 10000")
        sys.exit(1)
    
    # 验证日期格式
    if args.start_date:
        try:
            datetime.fromisoformat(args.start_date)
        except ValueError:
            logger.error("Invalid start date format. Use YYYY-MM-DD")
            sys.exit(1)
    
    if args.end_date:
        try:
            datetime.fromisoformat(args.end_date)
        except ValueError:
            logger.error("Invalid end date format. Use YYYY-MM-DD")
            sys.exit(1)
    
    # 执行迁移
    async def run_migration():
        # 验证后端
        logger.info("Validating backends...")
        
        if not await validate_backend(args.source):
            logger.error(f"Source backend validation failed: {args.source}")
            return False
            
        if not args.dry_run and not await validate_backend(args.target):
            logger.error(f"Target backend validation failed: {args.target}")
            return False
        
        logger.info("✓ Backend validation passed")
        
        # 执行迁移
        return await migrate_logs(
            source=args.source,
            target=args.target,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            start_date=args.start_date,
            end_date=args.end_date
        )
    
    # 运行异步迁移
    try:
        success = asyncio.run(run_migration())
        if success or args.dry_run:
            logger.info("Migration completed successfully")
            sys.exit(0)
        else:
            logger.error("Migration failed")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()