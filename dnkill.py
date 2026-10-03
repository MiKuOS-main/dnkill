#!/usr/bin/env python3
import curses
import os
import signal
import sys
import time

try:
    import psutil
except ImportError:
    print("Error: 'psutil' module is required. Install it using 'pip install psutil'.")
    sys.exit(1)

DEATH_NOTE_ASCII = r"""
______ _____  ___ _____ _   _   _  _ _____ _____ _____ 
|  _  \  ___|/ _ \_   _| | | | | || |  _  |_   _|  ___|
| | | | |__ / /_\ \| | | |_| | | || | | | | | | | |___ 
| | | |  __||  _  || | |  _  | | || | | | | | | |  ___|
| |/ /| |___| | | || | | | | | \ \/ / \ \_/ / | | |___ 
|___/ \____/\_| |_/\_/ \_| |_/  \__/   \___/  \_/\____/
"""

RULES = [
    "1. The process whose name is written in this note shall die.",
    "2. This note will not take effect unless the writer has the PID/Name in mind.",
    "3. If the cause of death is written within 40 seconds, it will happen.",
    "4. If the cause of death is not specified, the process will simply die of SIGKILL."
]

def select_process_menu(stdscr):
    """Interactive process selection menu."""
    curses.curs_set(0)
    curses.use_default_colors()
    
    # Color Pairs
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_WHITE, -1)

    search_query = ""
    selected_idx = 0

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        # Display Rules / Header
        row = 1
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        for line in DEATH_NOTE_ASCII.strip().split("\n"):
            if row < max_y - 1:
                stdscr.addstr(row, 2, line[:max_x - 4])
                row += 1
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        row += 1
        stdscr.attron(curses.color_pair(3))
        stdscr.addstr(row, 2, "=== RULES OF THE DEATH NOTE ===")
        row += 1
        for rule in RULES:
            if row < max_y - 1:
                stdscr.addstr(row, 4, rule[:max_x - 6])
                row += 1
        stdscr.attroff(curses.color_pair(3))

        row += 1
        stdscr.addstr(row, 2, f"Search Target (Type to filter): [ {search_query} ]")
        row += 2

        # Filter Processes
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                pinfo = proc.info
                name = pinfo['name'] or ""
                pid_str = str(pinfo['pid'])
                if search_query.lower() in name.lower() or search_query in pid_str:
                    try:
                        pinfo['cpu_percent'] = proc.cpu_percent(interval=0.0)
                    except (psutil.NoSuchProcess, psutil.AccessDenied, RuntimeError):
                        pinfo['cpu_percent'] = 0.0
                    processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU usage descending (highest first)
        processes.sort(key=lambda x: x.get('cpu_percent', 0.0), reverse=True)

        # Clamp selection index
        if processes:
            selected_idx = max(0, min(selected_idx, len(processes) - 1))

        # Process Table Header
        header = f"{'PID':<10} {'USER':<18} {'CPU%':<8} {'PROCESS NAME':<30}"
        stdscr.addstr(row, 2, header[:max_x - 4], curses.A_UNDERLINE | curses.A_BOLD)
        row += 1

        # Render visible process list
        list_capacity = max_y - row - 2
        start_idx = max(0, selected_idx - list_capacity // 2)
        end_idx = min(len(processes), start_idx + list_capacity)

        for i in range(start_idx, end_idx):
            p = processes[i]
            cpu_pct = p.get('cpu_percent', 0.0)
            line = f"{p['pid']:<10} {(p['username'] or 'N/A'):<18} {cpu_pct:<8.1f} {p['name']:<30}"
            
            if i == selected_idx:
                stdscr.addstr(row, 2, line[:max_x - 4], curses.A_REVERSE | curses.color_pair(1))
            else:
                stdscr.addstr(row, 2, line[:max_x - 4], curses.color_pair(4))
            row += 1

        stdscr.addstr(max_y - 1, 2, "ARROWS: Navigate | TYPE: Filter | ENTER: Select Target | ESC/CTRL+C: Quit")
        stdscr.refresh()

        # Handle user input
        key = stdscr.getch()

        if key in (27, 3):  # ESC or Ctrl+C
            return None
        elif key in (curses.KEY_UP, ord('k')):
            selected_idx -= 1
        elif key in (curses.KEY_DOWN, ord('j')):
            selected_idx += 1
        elif key in (10, 13):  # ENTER
            if processes and 0 <= selected_idx < len(processes):
                return processes[selected_idx]
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            search_query = search_query[:-1]
            selected_idx = 0
        elif 32 <= key <= 126:
            search_query += chr(key)
            selected_idx = 0

def write_and_countdown(stdscr, proc_info):
    """Renders the ritual writing and 40-second countdown execution."""
    curses.curs_set(1)
    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()

    pid = proc_info['pid']
    name = proc_info['name']

    # Step 1: Write Name
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(2, 2, f"Target Locked: {name} (PID: {pid})")
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    stdscr.addstr(4, 2, "Specify Cause of Death (Signal Type):")
    stdscr.addstr(5, 4, "[1] Heart Attack (SIGKILL - hard termination)")
    stdscr.addstr(6, 4, "[2] Graceful Demise (SIGTERM - polite request)")
    stdscr.addstr(7, 2, "Selection [1/2] (Default: 1): ")
    stdscr.refresh()

    curses.echo()
    choice = stdscr.getstr(7, 32, 2).decode('utf-8').strip()
    curses.noecho()
    curses.curs_set(0)

    sig = signal.SIGKILL if choice != '2' else signal.SIGTERM
    cause_str = "Graceful Demise (SIGTERM)" if sig == signal.SIGTERM else "Heart Attack (SIGKILL)"

    stdscr.addstr(9, 2, f"Cause written: {cause_str}")
    stdscr.addstr(11, 2, "Writing name in Death Note...")
    stdscr.refresh()
    time.sleep(1.5)

    # Step 2: 40-Second Countdown Ritual
    countdown_seconds = 40
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        remaining = max(0.0, countdown_seconds - elapsed)

        stdscr.clear()
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(2, 2, "=== DEATH NOTE EXECUTION IN PROGRESS ===")
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

        stdscr.addstr(4, 2, f"Target Process : {name}")
        stdscr.addstr(5, 2, f"Target PID     : {pid}")
        stdscr.addstr(6, 2, f"Cause of Death : {cause_str}")

        stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        stdscr.addstr(8, 2, f"TIME UNTIL DEATH: {remaining:05.2f} SECONDS")
        stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

        # Draw a visual progress bar
        bar_width = min(50, max_x - 10)
        filled = int((1.0 - (remaining / countdown_seconds)) * bar_width)
        bar = "█" * filled + "-" * (bar_width - filled)
        stdscr.addstr(10, 2, f"[{bar}]")

        stdscr.addstr(12, 2, "Press [Q] or [Ctrl+C] to rip out the page and CANCEL execution.")
        stdscr.refresh()

        # Check if process is already dead beforehand
        if not psutil.pid_exists(pid):
            stdscr.addstr(14, 2, "Target has already ceased to exist naturally.", curses.color_pair(2))
            stdscr.refresh()
            time.sleep(2)
            break

        if remaining <= 0:
            break

        # Non-blocking input check
        stdscr.nodelay(True)
        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 3, 27):
            stdscr.nodelay(False)
            stdscr.addstr(14, 2, "Page ripped from notebook! Execution aborted.", curses.color_pair(2))
            stdscr.refresh()
            time.sleep(2)
            return

        time.sleep(0.05)

    stdscr.nodelay(False)

    # Step 3: Execute Termination
    try:
        os.kill(pid, sig)
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(14, 2, f"EXECUTION COMPLETE: {name} (PID {pid}) has been eliminated.")
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
    except ProcessLookupError:
        stdscr.addstr(14, 2, f"Process {pid} was not found (already terminated).", curses.color_pair(2))
    except PermissionError:
        stdscr.addstr(14, 2, f"PERMISSION DENIED: Could not eliminate {name}. Run with sudo.", curses.color_pair(1))
    except Exception as e:
        stdscr.addstr(14, 2, f"Error: {str(e)}", curses.color_pair(1))

    stdscr.addstr(16, 2, "Press any key to return to notebook...")
    stdscr.refresh()
    stdscr.getch()

def main(stdscr):
    while True:
        proc_info = select_process_menu(stdscr)
        if proc_info is None:
            break
        write_and_countdown(stdscr, proc_info)

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("Death Note closed.")
