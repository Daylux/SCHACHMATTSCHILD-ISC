#!/usr/bin/env python3
"""
ISC_AI Banner – Zeigt das ISC_AI-Logo im Terminal.
Nutze: python -m ISC_AI_BANNER
"""
import shutil

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                    ISC_AI · DAYLUX LABS                      ║
║                                                              ║
║      ██╗███████╗ ██████╗        █████╗ ██╗                  ║
║      ██║██╔════╝██╔════╝       ██╔══██╗██║                  ║
║      ██║███████╗██║            ███████║██║                  ║
║      ██║╚════██║██║            ██╔══██║██║                  ║
║      ██║███████║╚██████╗       ██║  ██║██║                  ║
║      ╚═╝╚══════╝ ╚═════╝       ╚═╝  ╚═╝╚═╝                  ║
║                                                              ║
║  INTELLIGENT SWARM CONTROL — ARTIFICIAL INTELLIGENCE         ║
║  ⚔️  SCHACHMATTSCHILD – INTEGRATED SECURITY CORE             ║
║                                                              ║
║  Proprietary Technology · Patents Pending                    ║
║  © 2024-2026 Daylux Labs. All rights reserved.               ║
╚══════════════════════════════════════════════════════════════╝
"""


def show_banner():
    width = shutil.get_terminal_size().columns
    for line in BANNER.split("\n"):
        print(f"{line:^{width}}")


if __name__ == "__main__":
    show_banner()
