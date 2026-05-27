import os
import subprocess
import sys
import time


# ---------------------------------------------------------------------------
# STEP 1: Utility
# ---------------------------------------------------------------------------

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


# ---------------------------------------------------------------------------
# STEP 2: UI Header
# ---------------------------------------------------------------------------

def print_header():
    print("=" * 70)
    print("""
  ██████  ██    ██  █████  ███    ██ ████████     ██████  ██████  ███████
 ██    ██ ██    ██ ██   ██ ████   ██    ██        ██   ██ ██   ██ ██
 ██    ██ ██    ██ ███████ ██ ██  ██    ██        ██████  ██████  ███████
 ██ ▄▄ ██ ██    ██ ██   ██ ██  ██ ██    ██        ██      ██   ██      ██
  ██████   ██████  ██   ██ ██   ████    ██        ██      ██   ██ ███████
     ▀▀
    """)
    print("=" * 70)
    print("   AI QUANTITATIVE EXECUTION PIPELINE  —  TECH MAHINDRA RESEARCH")
    print("=" * 70)
    print()
    print("   PIPELINE STAGES:")
    print("   ─────────────────────────────────────────────────────────────")
    print("   [1]  DATA INGESTION       →  LangGraph Multi-Agent Engine")
    print("   [2]  ALPHA REASONING      →  AutoGen Investment Committee")
    print("   [3]  LIVE EXECUTION       →  Paper Trading Mark-to-Market")
    print("   [4]  STATISTICAL BACKTEST →  VectorBT Institutional Analysis")
    print("   ─────────────────────────────────────────────────────────────")
    print()


# ---------------------------------------------------------------------------
# STEP 3: Execution Wrapper
# ---------------------------------------------------------------------------

def run_stage(stage_name, script_name):
    print()
    print("┌" + "─" * 68 + "┐")
    print(f"│  [INITIALIZING]  {stage_name}...".ljust(69) + "│")
    print("└" + "─" * 68 + "┘")
    print()

    try:
        subprocess.run([sys.executable, script_name], check=True)
        print()
        print(f"  ✅  {stage_name} — COMPLETE")
        time.sleep(2)

    except subprocess.CalledProcessError as e:
        print()
        print("╔" + "═" * 68 + "╗")
        print(f"║  ❌  CRITICAL PIPELINE FAILURE                                    ║")
        print(f"║  Stage  : {stage_name}".ljust(69) + "║")
        print(f"║  Script : {script_name}".ljust(69) + "║")
        print(f"║  Code   : {e.returncode}".ljust(69) + "║")
        print(f"║  Halting pipeline — downstream stages will NOT execute.          ║")
        print("╚" + "═" * 68 + "╝")
        sys.exit(1)


# ---------------------------------------------------------------------------
# STEP 4: Main Pipeline
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    clear_screen()
    print_header()

    run_stage("STAGE 1: LangGraph Data Extraction",       "main.py")
    run_stage("STAGE 2: Llama-3 Investment Committee",    "investment_committee.py")
    run_stage("STAGE 3: Live Portfolio Mark-to-Market",   "execution_engine.py")
    run_stage("STAGE 4: VectorBT Institutional Backtest", "vectorbt_backtest.py")

    print()
    print("╔" + "═" * 68 + "╗")
    print("║                                                                    ║")
    print("║   ✅  [SYSTEM COMPLETE]                                            ║")
    print("║   End-to-end pipeline executed successfully.                       ║")
    print("║                                                                    ║")
    print("╚" + "═" * 68 + "╝")
    print()
