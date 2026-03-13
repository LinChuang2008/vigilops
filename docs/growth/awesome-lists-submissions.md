# Awesome Lists PR Submissions

## 1. awesome-selfhosted

**Repo**: https://github.com/awesome-selfhosted/awesome-selfhosted

**Section**: `Monitoring`

**Entry to add** (alphabetical order within section):

```markdown
- [VigilOps](https://github.com/LinChuang2008/vigilops) - AI-powered infrastructure monitoring platform with auto-remediation. Features 6 built-in runbooks, AI root cause analysis, and MCP protocol integration. `Apache-2.0` `Docker`
```

**PR Title**: `Add VigilOps to Monitoring section`

**PR Body**:
```
## Description
Adding VigilOps, an open-source AI-powered monitoring platform.

## Checklist
- [x] Self-hosted / can be hosted on own infrastructure
- [x] Free / Open Source (Apache 2.0)
- [x] Has a working demo: https://demo.lchuangnet.com
- [x] English documentation
- [x] Active repository with recent commits

## What makes it unique
VigilOps is the first open-source monitoring platform that combines AI root cause analysis with automated remediation. It includes 6 production-ready runbooks and is the first to integrate MCP (Model Context Protocol) for AI agent connectivity.
```

---

## 2. awesome-monitoring

**Repo**: https://github.com/crazy-canux/awesome-monitoring (or similar)

**Section**: `Infrastructure Monitoring` or `AIOps`

**Entry**:
```markdown
- [VigilOps](https://github.com/LinChuang2008/vigilops) - Open-source AI-powered monitoring with auto-remediation runbooks and MCP integration.
```

---

## 3. awesome-mcp-servers

**Repo**: https://github.com/punkpeye/awesome-mcp-servers

**Section**: `Monitoring` or `DevOps`

**Entry**:
```markdown
- [VigilOps MCP Server](https://github.com/LinChuang2008/vigilops) - Production monitoring MCP server with 5 tools: server health, alert queries, log search, AI incident analysis, and service topology. Part of the VigilOps AI monitoring platform.
```

**PR Title**: `Add VigilOps MCP Server`

**PR Body**:
```
## Description
VigilOps includes a built-in MCP server that exposes 5 monitoring tools to AI assistants (Claude, Cursor, etc.):

- `get_servers_health` — Real-time server health status
- `get_alerts` — Query alerts by status, severity, host, time range
- `search_logs` — Search production logs
- `analyze_incident` — AI-powered root cause analysis
- `get_topology` — Service dependency map

This is the first open-source monitoring platform with native MCP support.

## Links
- Repository: https://github.com/LinChuang2008/vigilops
- Demo: https://demo.lchuangnet.com
- MCP docs: https://github.com/LinChuang2008/vigilops#mcp-integration--global-open-source-first
```

---

## Submission Steps

For each awesome-list:

1. Fork the target repository
2. Create a branch: `add-vigilops`
3. Add the entry in the appropriate section (maintain alphabetical order)
4. Commit and push
5. Create PR with the prepared title and body

```bash
# Example for awesome-selfhosted
gh repo fork awesome-selfhosted/awesome-selfhosted --clone
cd awesome-selfhosted
git checkout -b add-vigilops
# Edit README.md — add entry in Monitoring section
git add README.md
git commit -m "Add VigilOps to Monitoring section"
git push origin add-vigilops
gh pr create --title "Add VigilOps to Monitoring section" --body "..."
```
