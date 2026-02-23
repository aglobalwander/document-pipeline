# GitHub CLI + VS Code Integration Strategy

## Core Principle
**GitHub CLI (`gh`) for operations, VS Code for context**

## Tool Responsibilities

### GitHub CLI (Primary) ✅
All actual GitHub operations remain in terminal with `gh`:

```bash
# Pull Requests
gh pr create
gh pr list
gh pr merge
gh pr review

# Issues  
gh issue create
gh issue list
gh issue close

# Workflows
gh workflow run
gh run list
gh run watch

# Repos
gh repo clone
gh repo fork
gh repo sync
```

### VS Code Extensions (Secondary) 👁️

#### GitLens (Optional - Visual Context Only)
- **Use for:** Seeing blame inline while coding
- **NOT for:** Making commits or operations
- **Alternative:** `git blame` in terminal

#### GitHub Pull Request Extension (Optional - Visual Review)
- **Use for:** Reviewing PR diffs visually
- **NOT for:** Creating PRs (use `gh pr create`)
- **Alternative:** `gh pr view --web`

## Recommended Minimal Setup

If you want to stay CLI-focused, keep only:

### Essential VS Code Extensions
```json
{
  "recommendations": [
    // PHP Development (Essential)
    "bmewburn.vscode-intelephense-client",
    "xdebug.php-debug",
    
    // Database (Essential)
    "mtxr.sqltools",
    "mtxr.sqltools-driver-mysql",
    
    // Skip Git extensions - use gh CLI instead
    // "eamodio.gitlens",  // OPTIONAL
    // "github.vscode-pull-request-github",  // OPTIONAL
  ]
}
```

## Hybrid Workflows

### Creating a PR

#### CLI-Only (Recommended)
```bash
git add -A
git commit -m "feat: Add new feature"
git push origin feature-branch
gh pr create --title "Add new feature" --body "Description"
```

#### With VS Code Context
```bash
# See who wrote surrounding code (GitLens)
# Make your changes
git add -A
git commit -m "feat: Add new feature"
git push origin feature-branch
gh pr create  # Still use gh for creation
```

### Reviewing a PR

#### CLI-Only
```bash
gh pr view 123
gh pr diff 123
gh pr review 123 --approve
```

#### With VS Code Visual
```bash
gh pr checkout 123
code .  # Review changes visually in VS Code
gh pr review 123 --approve  # Still approve via CLI
```

## Decision Matrix

| Task | Use GitHub CLI | Use VS Code | Why |
|------|---------------|-------------|-----|
| Create PR | ✅ `gh pr create` | ❌ | CLI is faster, scriptable |
| Merge PR | ✅ `gh pr merge` | ❌ | CLI is authoritative |
| View blame | Optional | ✅ GitLens | Inline is convenient |
| Review PR diff | ✅ `gh pr diff` | Optional | Personal preference |
| Run workflows | ✅ `gh workflow run` | ❌ | CLI only option |
| Debug PHP | ❌ | ✅ Xdebug | Visual debugging better |
| Query database | Optional `ddev mysql` | ✅ SQLTools | Visual is easier |

## Your Specific Setup

Based on your preference for GitHub CLI:

### Keep These VS Code Extensions
- PHP IntelliSense (coding efficiency)
- SQLTools (visual database)
- Xdebug (debugging)
- Twig/Drupal support

### Make These Optional
- GitLens (only if you want inline blame)
- GitHub PR extension (only if you want visual PR review)
- Git Graph (only if you want visual branch history)

### Always Use CLI For
- All `gh` commands
- All `git` commands  
- All automation/scripts

## Example .vscode/settings.json for CLI-First Approach

```json
{
  // Disable GitLens features that duplicate gh CLI
  "gitlens.codeLens.enabled": false,
  "gitlens.currentLine.enabled": false,  // Or true if you want blame
  
  // Don't auto-fetch (use gh/git manually)
  "git.autofetch": false,
  
  // Focus on PHP/Database features
  "intelephense.environment.phpVersion": "8.4.0",
  "sqltools.connections": [...]
}
```

## Summary

**GitHub CLI remains your primary tool** for all Git/GitHub operations. VS Code extensions only add:
1. **Passive context** (blame info while coding)
2. **Language features** (PHP intelligence)
3. **Visual tools** (database browser, debugger)

They don't replace `gh` - they complement it where visual helps.