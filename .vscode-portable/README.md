# Portable VS Code Setup for Data Analysis Projects

## What This Is
A portable, reusable VS Code configuration for Python data analysis that:
- ✅ **Optimized** for Python, Jupyter, and survey analysis workflows
- ✅ **Auto-detects** your Python environment and packages
- ✅ **Integrates** with GPT-4/AI analysis pipelines
- ✅ **Portable** to any data analysis project

## Quick Install

### For This Project
```bash
cd /Users/scottwilliams/Development/master_projects/data_analysis
./.vscode-portable/install-data-analysis.sh
```

### For Other Projects
```bash
# Copy the .vscode-portable folder
cp -r /path/to/this/project/.vscode-portable /path/to/other/project/
cd /path/to/other/project/
./.vscode-portable/install-data-analysis.sh
```

## What Gets Installed

### VS Code Extensions (30+ total)
- **Python Development**: Pylance, Black formatter, Flake8 linting
- **Data Science**: Jupyter notebooks, data viewers, CSV tools
- **Visualization**: Data preview, Excel viewer, Rainbow CSV
- **AI Integration**: GitHub Copilot, Continue AI assistant
- **Git**: GitLens, Git Graph, history visualization
- **Testing**: Python test adapters, coverage tools
- **Productivity**: TODO Tree, Error Lens, Bookmarks

### Configuration Files
- `.vscode/settings.json` - Optimized Python & data science settings
- `.vscode/extensions.json` - Curated extension recommendations
- `.vscode/launch.json` - Debug configurations for analysis scripts

## Features

### 1. Jupyter Notebook Integration
- **Interactive Development**: Run cells directly in VS Code
- **Variable Explorer**: Inspect dataframes and variables
- **Inline Plotting**: Matplotlib/Plotly visualization support
- **Export Options**: Convert to HTML, PDF, Python scripts

### 2. Data Analysis Workflows
- **CSV/Excel Support**: Direct viewing and editing
- **Pandas Integration**: IntelliSense for dataframe operations
- **Statistical Analysis**: NumPy, SciPy autocomplete
- **GPT-4 Integration**: AI-powered analysis pipelines

### 3. Python Development
- **Type Checking**: Pylance with type hints
- **Auto-formatting**: Black formatter on save
- **Linting**: Flake8 with custom rules
- **Testing**: Pytest integration with coverage

## Environment Detection

The installer automatically detects:
- ✅ Python version and interpreter path
- ✅ Virtual environment (.venv or venv)
- ✅ Installed packages (pandas, numpy, jupyter, etc.)
- ✅ Environment variables (.env file)

## Files in This Package

```
.vscode-portable/
├── README.md                    # This file
├── install-data-analysis.sh    # Main installer script
├── settings.json                # VSCode settings for data analysis
├── extensions.json              # Extension recommendations
└── launch.json                  # Debug configurations
```

## Customization

### Skip Extension Installation
```bash
# Just create configuration files
./.vscode-portable/install-data-analysis.sh --skip-install
```

### Custom Python Path
Edit `.vscode/settings.json`:
```json
"python.defaultInterpreterPath": "/path/to/your/python"
```

### Analysis Scripts Still Work!

All your existing scripts and notebooks continue to work:
```bash
python saved_scripts/main_likert.py
python saved_scripts/open_ended.py
jupyter notebook
./run_analysis.sh
```

## For Teams

1. Commit the `.vscode/` folder to share settings
2. Team members run the installer once
3. Everyone gets the same IDE experience

## Troubleshooting

### Python interpreter not found?
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Extensions not installing?
```bash
# Check VS Code CLI
which code
# Manual install
code --install-extension ms-python.python
code --install-extension ms-toolsai.jupyter
```

## Support

- **Documentation**: See `CLAUDE.md` for project-specific guidance
- **Notebooks**: Example notebooks in `notebooks/` directory
- **Scripts**: Analysis scripts in `saved_scripts/` directory

## Key Workflows

### Survey Analysis Pipeline
1. **Place data**: Drop CSV/XLSX files in `data/input/`
2. **Run Likert analysis**: Execute `notebooks/likert_analysis.ipynb`
3. **Analyze open-ended**: Execute `notebooks/open_ended_v4.ipynb`
4. **Generate summary**: Execute `notebooks/executive_summary.ipynb`
5. **View results**: Check `data/output/` for reports and visualizations

### Development Workflow
- **Terminal**: Batch processing, automation, data pipeline execution
- **VS Code**: Interactive analysis, debugging, notebook development
- **Jupyter**: Exploratory data analysis, visualization prototyping
- **GPT-4**: AI-powered insights, thematic analysis, report generation