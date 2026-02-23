# VS Code + Terminal Hybrid Workflow

## Overview
This setup **enhances** (not replaces) your existing workflow by adding VS Code IDE capabilities while keeping all terminal commands functional.

## Quick Reference

### Database Access (Both Methods Work!)

#### Terminal (Still Works)
```bash
# DDEV MySQL
ddev mysql
ddev drush sqlq "SELECT * FROM node LIMIT 10"
ddev export-db > backup.sql

# Direct MySQL
mysql -h 127.0.0.1 -P 32784 -u db -pdb

# Backup scripts still work
./scripts/backup-to-external.sh
```

#### VS Code SQLTools
1. Open Command Palette (Cmd+Shift+P)
2. Type "SQLTools: Connect"
3. Select "Local Database"
4. Browse tables, run queries visually

### Git Operations (Both Methods Work!)

#### Terminal
```bash
git status
git add -A
git commit -m "message"
git push origin main
gh pr create
```

#### VS Code
- **GitLens**: See inline blame, history
- **Source Control**: Stage files visually (Cmd+Shift+G)
- **GitHub PR**: Create/review PRs in VS Code

### PHP Development

#### Terminal Debugging
```bash
ddev xdebug on
ddev drush ws --tail
```

#### VS Code Debugging
1. Set breakpoints by clicking line numbers
2. Press F5 to start debugging
3. Step through code visually

### Testing

#### Terminal
```bash
ddev phpunit tests/
vendor/bin/phpcs --standard=Drupal web/modules/custom/
```

#### VS Code
- **PHPUnit**: Click "Run Test" above test methods
- **PHP Sniffer**: Real-time feedback in editor

## When to Use What?

### Use Terminal For:
- **Automation/Scripts**: Cron jobs, CI/CD
- **Bulk Operations**: Mass updates, migrations
- **Remote Servers**: SSH operations
- **Quick Commands**: `drush cr`, `git status`

### Use VS Code For:
- **Interactive Development**: Writing code with IntelliSense
- **Debugging**: Breakpoints, step-through
- **Database Exploration**: Browse tables, test queries
- **Code Review**: GitLens blame, PR reviews

## Agent Integration

### For Claude/AI Agents

Your agents can now leverage VS Code extensions:

```bash
# Check if VS Code extension is available
if command -v code &> /dev/null && code --list-extensions | grep -q "bmewburn.vscode-intelephense-client"; then
    # Use VS Code for PHP intelligence
    code --goto "file.php:100"
else
    # Fall back to traditional methods
    grep -n "function" file.php
fi
```

### Updated Agent Commands

```yaml
# Old way (still works)
- command: "grep -r 'class Dashboard' ."
  
# New way (with VS Code)
- command: "code --goto 'DashboardController.php:45'"
- command: "code --diff file1.php file2.php"
```

## Portable Setup for Other Projects

### One-Line Install
```bash
# For any Drupal project
curl -sL https://raw.githubusercontent.com/your-repo/vscode-drupal/main/install.sh | bash
```

### Manual Copy
```bash
# Copy to another project
cp -r .vscode-portable /path/to/other/project/
cd /path/to/other/project/
./.vscode-portable/install-vscode-drupal.sh
```

### Custom Configuration
```bash
# Skip extension install (just configure)
./.vscode-portable/install-vscode-drupal.sh --skip-install

# Then manually adjust .vscode/settings.json
```

## Environment Variables

The installer detects and configures:
- PHP version and path
- DDEV status and ports
- Drupal version
- Database connections

## Troubleshooting

### Issue: Database connection fails
```bash
# Check DDEV port
ddev describe | grep "Host.*db"
# Update .vscode/settings.json with correct port
```

### Issue: PHP not found
```bash
# Find PHP path
which php
# Update settings.json: "php.validate.executablePath"
```

### Issue: Extensions not installing
```bash
# Install manually
code --install-extension bmewburn.vscode-intelephense-client
```

## Best Practices

1. **Keep Both Options**: Don't delete scripts, archive them
2. **Document Changes**: Update team docs when adding VS Code features
3. **Version Control**: Commit .vscode/ folder for team consistency
4. **Environment Specific**: Use .vscode/settings.local.json for personal settings

## Extension Capabilities

### What Each Extension Provides

| Extension | Terminal Alternative | VS Code Advantage |
|-----------|---------------------|-------------------|
| Intelephense | grep, ack | Real-time PHP intelligence |
| SQLTools | mysql, ddev mysql | Visual table browser |
| GitLens | git blame | Inline blame, hover info |
| PHP Debug | var_dump, dpm() | Breakpoints, step-through |
| TODO Tree | grep TODO | Workspace-wide TODO list |

## Migration Path

### Phase 1: Install & Test (Current)
- Install extensions
- Keep all scripts functional
- Document what works better in VS Code

### Phase 2: Team Adoption
- Share .vscode/ configuration
- Train team on VS Code features
- Maintain dual workflows

### Phase 3: Optimization
- Archive rarely-used scripts
- Update CI/CD to leverage VS Code where beneficial
- Standardize on best tool for each task

## Summary

**This is NOT a replacement** - it's an enhancement. All your terminal commands, scripts, and workflows continue to work. VS Code extensions simply add a visual, interactive layer when that's more efficient.

Terminal = Power & Automation
VS Code = Intelligence & Visualization
Together = Best of Both Worlds