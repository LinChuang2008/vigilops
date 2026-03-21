"""
VigilOps Agent 命令行入口模块。

提供 CLI 命令：run（前台运行 Agent）和 check（验证配置文件）。
兼容 Linux / Windows / macOS。
"""
import asyncio
import logging
import os
import platform
import signal
import socket
import sys

import click

from vigilops_agent import __version__
from vigilops_agent.config import load_config

# 平台常量 / Platform constant
IS_WINDOWS = platform.system() == "Windows"


def _default_config_path() -> str:
    """返回当前平台的默认配置文件路径。
    Return the default config file path for the current platform.

    - Linux/macOS: /etc/vigilops/agent.yaml
    - Windows:     %PROGRAMDATA%\\vigilops\\agent.yaml  (通常为 C:\\ProgramData\\vigilops\\agent.yaml)
    """
    if IS_WINDOWS:
        program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        return os.path.join(program_data, "vigilops", "agent.yaml")
    return "/etc/vigilops/agent.yaml"


@click.group(invoke_without_command=True)
@click.option("--config", "-c", default=_default_config_path(), help="Config file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, config, verbose):
    """VigilOps Agent - 轻量级监控代理。"""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config
    ctx.obj["verbose"] = verbose

    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 未指定子命令时，显示基本信息
    if ctx.invoked_subcommand is None:
        click.echo(f"VigilOps Agent v{__version__}")
        click.echo(f"Config: {config}")
        click.echo("Use --help for available commands")


@cli.command()
@click.pass_context
def run(ctx):
    """以前台模式运行 Agent。"""
    logger = logging.getLogger("vigilops-agent")
    config_path = ctx.obj["config_path"]

    try:
        cfg = load_config(config_path)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # 校验必要配置
    if not cfg.server.token:
        click.echo("Error: No agent token configured. Set server.token in config or VIGILOPS_TOKEN env.", err=True)
        sys.exit(1)

    # 主机名未配置时自动获取
    if not cfg.host.name:
        cfg.host.name = socket.gethostname()

    logger.info(f"Starting VigilOps Agent v{__version__}")
    logger.info(f"Server: {cfg.server.url}")
    logger.info(f"Host: {cfg.host.name}")
    logger.info(f"Metrics interval: {cfg.metrics.interval}s")
    logger.info(f"Service checks: {len(cfg.services)} (manual)")
    logger.info(f"Log sources: {len(cfg.log_sources)} (manual)")
    logger.info(f"Docker auto-discovery: {'enabled' if cfg.discovery.docker else 'disabled'}")

    from vigilops_agent.reporter import AgentReporter

    reporter = AgentReporter(cfg)

    loop = asyncio.new_event_loop()

    # 注册信号处理，优雅关闭
    # Register signal handlers for graceful shutdown
    def _shutdown(sig, frame):
        logger.info(f"Received {signal.Signals(sig).name}, shutting down...")
        loop.stop()

    signal.signal(signal.SIGINT, _shutdown)
    # SIGTERM 在 Windows 上不可用 / SIGTERM is not available on Windows
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(reporter.start())
    except Exception:
        logger.exception("Agent crashed")
        sys.exit(1)


@cli.command()
@click.pass_context
def check(ctx):
    """验证配置文件是否正确。"""
    config_path = ctx.obj["config_path"]
    try:
        cfg = load_config(config_path)
        click.echo(f"✅ Config OK: {config_path}")
        click.echo(f"   Server: {cfg.server.url}")
        click.echo(f"   Host: {cfg.host.name or '(auto-detect)'}")
        click.echo(f"   Metrics interval: {cfg.metrics.interval}s")
        click.echo(f"   Services: {len(cfg.services)}")
        click.echo(f"   Log sources: {len(cfg.log_sources)}")
    except Exception as e:
        click.echo(f"❌ Config error: {e}", err=True)
        sys.exit(1)


def main():
    """CLI 入口函数。"""
    cli()


if __name__ == "__main__":
    main()
