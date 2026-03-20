import os
import sys
import platform
import getpass
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.columns import Columns
    from rich.align import Align
    from rich.rule import Rule
    from rich import box
except ImportError:
    # Fallback if rich is not installed yet
    Console = None

class WelcomeDashboard:
    def __init__(self, version: str = "0.1.0"):
        self.version = version
        self.console = Console() if Console else None

    def _get_ascii_art(self) -> str:
        return """
      ___                       ___           ___           ___           ___     
     /  /\          ___        /  /\         /__/\         /  /\         /  /\    
    /  /::\        /  /\      /  /:/_        \  \:\       /  /:/_       /  /::\   
   /  /:/\:\      /  /:/     /  /:/ /\        \  \:\     /  /:/ /\     /  /:/\:\  
  /  /:/~/::\    /  /:/     /  /:/ /:/_   _____\__\:\   /  /:/ /:/_   /  /:/~/::\ 
 /__/:/ /:/\:\  /  /::\    /__/:/ /:/ /\ /__/::::::::\ /__/:/ /:/ /\ /__/:/ /:/\:\\
 \  \:\/:/__\/ /__/:/\:\   \  \:\/:/ /:/ \  \:\~~\~~\/ \  \:\/:/ /:/ \  \:\/:/__\/
  \  \::/      \__\/  \:\   \  \::/ /:/   \  \:\  ~~~   \  \::/ /:/   \  \::/     
   \  \:\           \  \:\   \  \:\/:/     \  \:\        \  \:\/:/     \  \:\     
    \  \:\           \__\/    \  \::/       \  \:\        \  \::/       \  \:\    
     \__\/                     \__\/         \__\/         \__\/         \__\/    
"""

    def render(self, status_data: Optional[Dict[str, Any]] = None):
        if not self.console:
            print(f"Atenea Context Engine - v{self.version}")
            print("Run 'atenea --help' for usage.")
            return

        # Header Info
        try:
            username = getpass.getuser()
            nodename = platform.node()
        except Exception:
            username = "user"
            nodename = "local"

        header_text = Text.assemble(
            (f"Version {self.version}", "bold cyan"),
            (" | ", "dim"),
            (f"{username}@{nodename}", "dim yellow")
        )
        self.console.print(header_text, justify="left")

        # ASCII Art
        ascii_art = Text(self._get_ascii_art(), style="bold magenta")
        self.console.print(Align.center(ascii_art))

        # Welcome Message
        welcome_title = Text("Get started with Atenea", style="bold underline blue")
        self.console.print(welcome_title)
        self.console.print()

        # Tips / Usage
        tips_table = Table.grid(padding=(0, 1))
        tips_table.add_column(style="yellow")
        tips_table.add_column()

        tips = [
            ("⚡", "Quick Start: [bold cyan]atenea index[/bold cyan] to index your current directory."),
            ("🔍", "Search: [bold cyan]atenea query \"your question\"[/bold cyan] to retrieve context."),
            ("⚙️", " Settings: [bold cyan]atenea config set-server <url>[/bold cyan] to change server URL."),
            ("🛠️", " MCP: [bold cyan]atenea serve[/bold cyan] to start the MCP server for IDEs."),
        ]

        for icon, tip in tips:
            tips_table.add_row(icon, tip)

        self.console.print(tips_table)
        self.console.print()

        # Status Section
        if status_data:
            engine_name = status_data.get("engine", "Unknown Engine")
            status = status_data.get("status", "Unknown")
            collections = status_data.get("collections", [])
            
            status_style = "green" if status == "healthy" else "red"
            
            status_panel_content = Text.assemble(
                ("Server: ", "bold"), (engine_name, "cyan"), "\n",
                ("Status: ", "bold"), (status.upper(), status_style), "\n",
                ("Codebases: ", "bold"), (", ".join(collections) if collections else "None", "dim")
            )
            
            self.console.print(Panel(
                status_panel_content,
                title="[bold]System Status[/bold]",
                border_style="dim",
                padding=(1, 2)
            ))
        else:
            self.console.print(Panel(
                "[bold red]Disconnected[/bold red] - Could not reach Atenea Server.",
                title="[bold]System Status[/bold]",
                border_style="red",
                padding=(1, 2)
            ))

        self.console.print(Rule(style="dim"))
        
        # Bottom Bar
        current_path = os.getcwd()
        bottom_bar = Table.grid(expand=True)
        bottom_bar.add_column(justify="left")
        bottom_bar.add_column(justify="right")
        
        bottom_bar.add_row(
            Text("? to show shortcuts", style="dim"),
            Text.assemble(
                ("[ATENEA]", "bold blue"),
                (f" {current_path}", "dim")
            )
        )
        self.console.print(bottom_bar)
