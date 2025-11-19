# CLIHelper 🤖

Simple llm-powered help for command-line errors. provides helpful suggestions based on recent terminal history.

## Installation
```bash
# Install using pipx (recommended)
pipx install git+https://github.com/RobGKN/clihelper

# Or using pip
pip install git+https://github.com/RobGKN/clihelper
```

## Setup

Prompts for an anthropic api key on first run.

## Usage

Simply pipe any command error to `clihelper`:
```bash
# Basic usage
ls --fake-flag 2>&1 | clihelper

# With additional context
find . -name "*.txt" 2>&1 | clihelper "trying to find all text files"

# Git example
git psh 2>&1 | clihelper
```

## Examples
```bash
$ ls --recursively 2>&1 | clihelper

==================================================
🤖 CLIHelper says:
==================================================
The issue is that ls doesn't have a --recursively flag. 
You're trying to list files recursively.

$ ls -R

The -R flag (uppercase R) is the correct option for recursive 
listing in ls. You can also use 'tree' for a nicer recursive view.
==================================================
```

## Requirements

- Python 3.6+
- Ubuntu/Linux with bash
- Anthropic API key

## License

MIT

