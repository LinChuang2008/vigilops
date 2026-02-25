#!/usr/bin/env python3
"""
数据库迁移执行脚本 (Database Migration Execution Script)

手动执行数据库迁移文件，用于添加新的表结构和数据。
适用于需要执行特定 SQL 命令的迁移场景。

Execute database migration files manually for adding new table structures and data.
Suitable for migration scenarios that require executing specific SQL commands.
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent / "backend"))

from sqlalchemy import text
from app.core.database import engine

async def run_migration(migration_file: str):
    """
    执行指定的迁移文件 (Execute specified migration file)
    
    Args:
        migration_file: 迁移文件路径
    """
    print(f"执行迁移: {migration_file}")
    
    # 读取迁移文件内容
    migration_path = Path(__file__).parent / "backend" / "migrations" / migration_file
    if not migration_path.exists():
        print(f"错误: 迁移文件不存在 - {migration_path}")
        return False
    
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 按分号分割 SQL 语句
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    
    try:
        async with engine.begin() as conn:
            for statement in statements:
                if statement:
                    print(f"执行: {statement[:100]}...")
                    await conn.execute(text(statement))
        
        print(f"✅ 迁移 {migration_file} 执行成功")
        return True
        
    except Exception as e:
        print(f"❌ 迁移 {migration_file} 执行失败: {str(e)}")
        return False

async def main():
    """主函数 (Main function)"""
    migration_file = "021_alert_escalation.sql"
    
    print("开始执行数据库迁移...")
    print("=" * 50)
    
    success = await run_migration(migration_file)
    
    print("=" * 50)
    if success:
        print("🎉 所有迁移执行完成!")
    else:
        print("💥 迁移执行失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())