#!/usr/bin/env python3
# ONI - Orbital Network Infrastructure Launcher
# Copyright (c) 2026 Technic_ Dev
#
# This script launches all ONI network components:
# - ONS Server (Orbit Name Servers)
# - ONI Network Node (P2P)
# - Orbit Domain Registrar
# - Orbit Browser

import sys
import os
import time
import subprocess
import signal
import threading
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# ASCII Art
LOGO = """
  ___  _   _ ___ 
 / _ \\| \\ | |_ _|
| | | |  \\| || | 
| |_| | |\\  || | 
 \\___/|_| \\_|___|
                 
Orbital Network Infrastructure v1.0
© 2026 Technic_ Dev
"""

COMPONENTS = [
    {
        "name": "ONS Server",
        "file": "ons/ons_server.py",
        "port": 5353,
        "desc": "Orbit Name Servers",
    },
    {
        "name": "ONI Node",
        "file": "p2p/oni_node.py",
        "port": 6881,
        "desc": "P2P Network Node",
    },
    {
        "name": "Domain Registrar",
        "file": "orbit-registrar/registrar.py",
        "port": 8080,
        "desc": "Free .orb Domain Registration",
    },
    {
        "name": "Orbit Browser",
        "file": "orbit-browser/orbit_browser.py",
        "port": 9090,
        "desc": "ONI Network Browser",
    },
]


def print_header():
    """Print the ONI header."""
    print(LOGO)
    print("=" * 60)
    print()


def check_dependencies():
    """Check if all required modules are installed."""
    missing = []
    try:
        import websockets
    except:
        missing.append("websockets")
    try:
        from aiohttp import web
    except:
        missing.append("aiohttp")
    try:
        import flask
    except:
        missing.append("flask")
    
    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        print(f"   Install with: pip3 install {' '.join(missing)}")
        print()
        return False
    return True


def start_component(component, args=""):
    """Start a component in a separate process."""
    filepath = PROJECT_ROOT / component["file"]
    if not filepath.exists():
        print(f"  ⚠️  {component['name']}: File not found at {filepath}")
        return None
    
    cmd = [sys.executable, str(filepath)]
    if args:
        cmd.extend(args.split())
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        return process
    except Exception as e:
        print(f"  ❌ Failed to start {component['name']}: {e}")
        return None


def launch_all():
    """Launch all ONI components."""
    print_header()
    
    if not check_dependencies():
        print("Install missing dependencies and try again.")
        return
    
    print("🚀 Starting ONI Network Components...\n")
    print("-" * 60)
    
    processes = {}
    
    for component in COMPONENTS:
        name = component["name"]
        port = component["port"]
        
        print(f"  ⏳ Starting {name} on port {port}...", end=" ", flush=True)
        
        if name == "ONI Node":
            # Host example domains
            args = f"--host-domain helloworld.orb examples/helloworld.orb --host-domain myblog.orb examples/myblog.orb"
        elif name == "ONS Server":
            args = ""
        elif name == "Domain Registrar":
            args = ""
        elif name == "Orbit Browser":
            args = "--url orb://helloworld.orb"
        else:
            args = ""
        
        process = start_component(component, args)
        
        if process:
            processes[name] = process
            print("✅")
        else:
            print("❌")
    
    print("-" * 60)
    print()
    
    if processes:
        print("🌐 ONI Network Status:\n")
        for name, proc in processes.items():
            status = "✅ Running" if proc and proc.poll() is None else "❌ Failed"
            print(f"  {name}: {status}")
        
        print(f"""
📡 ONI Network Active!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ONS Server:      http://127.0.0.1:5353
  ONI Node:        ws://127.0.0.1:6881
  Domain Registrar: http://127.0.0.1:8080
  Orbit Browser:   Launching...

📋 Quick Links:
  → Register a domain: http://127.0.0.1:8080
  → Browse ONI:        orb://helloworld.orb
  → View ONS:          http://127.0.0.1:5353

📝 Commands to run manually (if browser doesn't start):
  python3 orbit-browser/orbit_browser.py --url orb://helloworld.orb

Press Ctrl+C to stop all components...
""")
        
        # Try to open the registrar in browser
        try:
            webbrowser.open("http://127.0.0.1:8080")
        except:
            pass
        
        # Wait for Ctrl+C
        try:
            while True:
                time.sleep(1)
                # Check if any process died
                for name, proc in list(processes.items()):
                    if proc.poll() is not None:
                        print(f"  ⚠️  {name} process ended unexpectedly")
                        del processes[name]
                
                if not processes:
                    print("\n  ❌ All processes ended. Shutting down.")
                    break
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down ONI Network...")
        finally:
            for name, proc in processes.items():
                proc.terminate()
                proc.wait()
            print("✅ ONI Network stopped.")
    else:
        print("❌ No components could be started.")
        print("Check the error messages above and fix any issues.")


if __name__ == "__main__":
    launch_all()