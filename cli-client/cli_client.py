#!/usr/bin/env python3
"""
CLI Task Management Client
A command-line interface for the MCP Task Management Server
"""

import requests
import json
import argparse
import sys
from typing import Dict, Any, List
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

class CLITaskClient:
    def __init__(self, mcp_url: str = "http://localhost:3002"):
        self.mcp_url = mcp_url
        self.console = Console()
    
    def call_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call an MCP tool via HTTP"""
        try:
            url = f"{self.mcp_url}/tools/{tool_name}"
            response = requests.post(url, json=parameters or {}, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            self.console.print("❌ [red]Cannot connect to MCP server. Is it running on port 3002?[/red]")
            sys.exit(1)
        except requests.exceptions.Timeout:
            self.console.print("❌ [red]Request timed out[/red]")
            sys.exit(1)
        except requests.RequestException as e:
            self.console.print(f"❌ [red]Request failed: {e}[/red]")
            sys.exit(1)
    
    def check_server_health(self) -> bool:
        """Check if the MCP server is healthy"""
        try:
            response = requests.get(f"{self.mcp_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                self.console.print("✅ [green]MCP Server is healthy[/green]")
                self.console.print(f"   Version: {health_data.get('version', 'Unknown')}")
                self.console.print(f"   Clients: {', '.join(health_data.get('clients', []))}")
                return True
        except:
            pass
        
        self.console.print("❌ [red]MCP Server is not responding[/red]")
        return False
    
    def display_tasks_table(self, tasks: List[Dict[str, Any]], title: str = "Tasks"):
        """Display tasks in a formatted table"""
        if not tasks:
            self.console.print("📭 [yellow]No tasks found[/yellow]")
            return
        
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("Status", style="cyan", no_wrap=True, width=8)
        table.add_column("Priority", style="yellow", no_wrap=True, width=10)
        table.add_column("Title", style="green", no_wrap=False)
        table.add_column("Description", style="white", no_wrap=False, max_width=30)
        table.add_column("ID", style="dim", no_wrap=True, width=12)
        
        for task in tasks:
            status = "✅ Done" if task.get('completed') else "⏳ Pending"
            priority = task.get('priority', 'medium').upper()
            title = task.get('title', 'No title')
            description = task.get('description', '')[:50] + '...' if len(task.get('description', '')) > 50 else task.get('description', '')
            task_id = task.get('id', 'Unknown')[:8] + '...' if task.get('id') else 'Unknown'
            
            # Color priority
            priority_style = {'HIGH': 'bold red', 'MEDIUM': 'bold yellow', 'LOW': 'bold green'}.get(priority, 'white')
            
            table.add_row(
                status,
                f"[{priority_style}]{priority}[/{priority_style}]",
                title,
                description,
                task_id
            )
        
        self.console.print(table)
    
    def cmd_list(self, args):
        """List all tasks"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(description="Fetching tasks...", total=None)
            result = self.call_tool('list_tasks')
            progress.update(task, completed=True)
        
        tasks = result.get('tasks', [])
        self.display_tasks_table(tasks, "📋 All Tasks")
        self.console.print(f"\n💡 [dim]{result.get('message', 'Tasks retrieved')}[/dim]")
    
    def cmd_create(self, args):
        """Create a new task"""
        title = args.title
        priority = args.priority or 'medium'
        description = args.description or ''
        
        if not title:
            title = Prompt.ask("📝 Enter task title")
        
        if not description and Confirm.ask("💬 Add a description?", default=False):
            description = Prompt.ask("📄 Enter description")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(description="Creating task...", total=None)
            result = self.call_tool('create_task', {
                'title': title,
                'description': description,
                'priority': priority
            })
            progress.update(task, completed=True)
        
        task_data = result.get('task', {})
        self.console.print("✅ [green]Task created successfully![/green]")
        self.console.print(f"   📋 Title: {task_data.get('title')}")
        self.console.print(f"   🔥 Priority: {task_data.get('priority', 'medium').upper()}")
        self.console.print(f"   🆔 ID: {task_data.get('id', 'Unknown')}")
    
    def cmd_search(self, args):
        """Search tasks"""
        query = args.query
        limit = args.limit or 10
        
        if not query:
            query = Prompt.ask("🔍 Enter search term")
        
        result = self.call_tool('search_tasks', {
            'query': query,
            'limit': limit
        })
        
        tasks = result.get('tasks', [])
        self.display_tasks_table(tasks, f"🔍 Search Results for '{query}'")
        self.console.print(f"\n💡 [dim]{result.get('message', 'Search completed')}[/dim]")
    
    def cmd_stats(self, args):
        """Show task statistics"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task(description="Calculating statistics...", total=None)
            stats_result = self.call_tool('get_task_stats')
            progress.update(task, completed=True)
        
        stats = stats_result.get('stats', {})
        
        # Create stats panel
        stats_text = f"""
📊 [bold cyan]Task Statistics[/bold cyan]
├── Total Tasks: [bold]{stats.get('total', 0)}[/bold]
├── Completed: [bold green]{stats.get('completed', 0)}[/bold green]
├── Pending: [bold yellow]{stats.get('pending', 0)}[/bold yellow]
├── High Priority: [bold red]{stats.get('highPriority', 0)}[/bold red]
├── Medium Priority: [bold yellow]{stats.get('mediumPriority', 0)}[/bold yellow]
└── Low Priority: [bold green]{stats.get('lowPriority', 0)}[/bold green]
        """
        
        self.console.print(Panel(stats_text.strip(), title="📈 Dashboard", border_style="blue"))

def main():
    parser = argparse.ArgumentParser(description="CLI Task Management Client")
    parser.add_argument('--server', default='http://localhost:3002', help='MCP server URL')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    subparsers.add_parser('list', help='List all tasks')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new task')
    create_parser.add_argument('title', nargs='?', help='Task title')
    create_parser.add_argument('--priority', choices=['low', 'medium', 'high'], default='medium', help='Task priority')
    create_parser.add_argument('--description', help='Task description')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search tasks')
    search_parser.add_argument('query', nargs='?', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum results')
    
    # Stats command
    subparsers.add_parser('stats', help='Show task statistics')
    
    # Health command
    subparsers.add_parser('health', help='Check server health')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    client = CLITaskClient(args.server)
    
    # Special handling for health command
    if args.command == 'health':
        client.check_server_health()
        return
    
    # Check server health before executing commands
    if not client.check_server_health():
        return
    
    # Execute the command
    command_methods = {
        'list': client.cmd_list,
        'create': client.cmd_create,
        'search': client.cmd_search,
        'stats': client.cmd_stats,
    }
    
    if args.command in command_methods:
        try:
            command_methods[args.command](args)
        except KeyboardInterrupt:
            client.console.print("\n❌ [yellow]Operation cancelled by user[/yellow]")
        except Exception as e:
            client.console.print(f"❌ [red]Error: {e}[/red]")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()