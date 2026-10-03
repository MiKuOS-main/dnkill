# Death Note CLI

A terminal-based process killer inspired by Death Note, built with Python and curses.

## Features

- Interactive TUI for selecting processes
- Sorts processes by highest CPU usage
- Real-time search/filtering
- 40-second countdown with cancellation option
- Choose between graceful termination (SIGTERM) or hard kill (SIGKILL)

## Requirements

- Python 3.7+
- psutil

## Installation

```bash
pip install psutil
```

## Usage

```bash
python3 deathnote.py
```

Or:

```bash
python3 dnkill.py
```

Navigate with arrow keys/j/k, type to filter, Enter to select, Esc to quit. During countdown, press Q to cancel.
