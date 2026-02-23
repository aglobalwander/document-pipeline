# Multi-Environment Management for VS Code

## Overview
Seamlessly switch between Conda, Micromamba, and system Python environments based on what you're working on.

## Available Environments

### Python Environments
1. **micromamba/drupal** - Default for general Python scripts
2. **conda/base (3.10.14)** - For migration scripts
3. **conda/ds-template (3.12.11)** - For data science/analysis
4. **conda/my-crawler (3.11.13)** - For web crawling/scraping

### PHP Environment
- **System PHP (8.4)** - For all Drupal development

## Quick Commands

### Switch Environment
```bash
# List all available environments
./.vscode-portable/switch-environment.sh list

# Switch to specific environment
./.vscode-portable/switch-environment.sh ds-template
./.vscode-portable/switch-environment.sh my-crawler
./.vscode-portable/switch-environment.sh base

# Auto-detect based on file
./.vscode-portable/switch-environment.sh auto scripts/analyze.py

# Check current environment
./.vscode-portable/switch-environment.sh current
```

### VS Code Integration

#### Method 1: Command Palette
1. Press `Cmd+Shift+P`
2. Type "Python: Select Interpreter"
3. Choose from list (now includes all your Conda envs)

#### Method 2: Status Bar
1. Click Python version in bottom status bar
2. Select environment from dropdown

#### Method 3: Automatic
Files are auto-associated with environments:
- `scripts/*.py` → base
- `analysis/*.py` → ds-template  
- `crawlers/*.py` → my-crawler
- `*.php` → PHP environment

## For Agents/LLMs

### Detect Current Environment
```bash
# Agents can check current environment
if [ -f .current_environment ]; then
    source .current_environment
    echo "Using Python: $PYTHON_PATH"
fi

# Or use the script
ENV=$(./.vscode-portable/switch-environment.sh current)
```

### Agent Usage Pattern
```python
import subprocess
import os

def get_correct_python():
    """Get the correct Python interpreter for current context"""
    if os.path.exists('.current_environment'):
        with open('.current_environment') as f:
            for line in f:
                if line.startswith('PYTHON_PATH='):
                    return line.split('=')[1].strip()
    return 'python3'  # fallback

# Use correct Python
python_path = get_correct_python()
subprocess.run([python_path, 'script.py'])
```

### Claude/Agent Commands
```bash
# Agent can switch environment before running code
./.vscode-portable/switch-environment.sh ds-template
python analysis/data_analysis.py

# Or auto-detect
./.vscode-portable/switch-environment.sh auto analysis/data_analysis.py
python analysis/data_analysis.py
```

## Environment Rules

### Auto-Detection Logic
| File Pattern | Environment | Python Version |
|-------------|-------------|----------------|
| `scripts/*.py` | base | 3.10.14 |
| `migration/*.py` | base | 3.10.14 |
| `analysis/*.py` | ds-template | 3.12.11 |
| `data-science/*.py` | ds-template | 3.12.11 |
| `crawlers/*.py` | my-crawler | 3.11.13 |
| `scrapers/*.py` | my-crawler | 3.11.13 |
| `*.py` (default) | drupal | micromamba |
| `*.php`, `*.module` | N/A | PHP 8.4 |

## VS Code Settings

The configuration automatically:
1. Detects all Conda environments
2. Allows quick switching via UI
3. Activates environment in terminal
4. Maintains separate configs per environment

## Portable to Other Repos

When copying to another repo:

1. **Copy the portable folder**
```bash
cp -r .vscode-portable /other/repo/
```

2. **Update environment paths if needed**
Edit `.vscode-portable/environment-config.json`

3. **Run installer**
```bash
cd /other/repo
./.vscode-portable/install-vscode-drupal.sh
```

## Terminal Integration

### Automatic Activation
When you open a terminal in VS Code:
- Correct environment auto-activates
- Shows environment name in prompt
- Uses right Python/pip

### Manual Terminal
```bash
# Activate Conda environment
conda activate ds-template

# Or Micromamba
micromamba activate drupal

# Verify
which python
python --version
```

## Best Practices

1. **Commit `.current_environment` to .gitignore**
```bash
echo ".current_environment" >> .gitignore
```

2. **Document environment requirements**
```bash
# Export environment
conda env export -n ds-template > environments/ds-template.yml
```

3. **Keep environments synced**
```bash
# Update all environments
conda update -n base conda
conda update -n ds-template --all
```

## Troubleshooting

### Can't find Conda environments?
```bash
# Find Conda installation
which conda
conda info --base

# Update paths in environment-config.json
```

### Environment not switching?
1. Reload VS Code window: `Cmd+R`
2. Check `.current_environment` file
3. Verify path exists: `ls -la ~/anaconda3/envs/`

### Multiple Python versions?
VS Code prioritizes in order:
1. Workspace setting (`.vscode/settings.json`)
2. User setting
3. System default

## Integration with PHP

PHP and Python can coexist:
- PHP files use PHP interpreter
- Python files use selected Python environment
- Both work simultaneously in same project

## Summary

This setup provides:
- ✅ Easy environment switching
- ✅ Auto-detection by file type
- ✅ Agent/LLM awareness
- ✅ Portable configuration
- ✅ Terminal integration
- ✅ VS Code UI integration