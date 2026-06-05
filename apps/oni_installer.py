#!/usr/bin/env python3
# ONI Installer - Cross-Platform GUI Installer
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure
#
# A friendly GUI installer that lets you choose what to install:
# - Orbit Browser (browse .orb websites)
# - ONI Manager (manage nodes & domains)
# - ONI DevKit (developer documentation & tools)
# - Docker support (self-hosting)
#
# Works on Linux, macOS, and Windows.

import sys
import os
import json
import subprocess
import threading
import webbrowser
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("ERROR: tkinter not available.")
    print("Linux:  sudo apt install python3-tk")
    print("Mac:    brew install python-tk")
    print("Windows: Reinstall Python and check 'tcl/tk'")
    sys.exit(1)

INSTALLER_VERSION = "1.0.0"
ONI_ROOT = Path(__file__).parent.parent

# Define components
COMPONENTS = {
    "browser": {
        "name": "Orbit Browser",
        "icon": "🌐",
        "desc": "Desktop browser for browsing .orb websites on the ONI decentralized network",
        "size": "~2 MB",
        "files": [
            "apps/orbit_browser_app.py",
            "p2p/oni_node.py", "p2p/peer.py", "p2p/protocol.py",
            "ons/resolver.py", "ons/registry.py",
            "start_oni.py", "supabase_client.py", ".env.example",
        ],
        "deps": ["websockets", "flask", "requests", "aiohttp"],
        "required": True,
    },
    "manager": {
        "name": "ONI Manager",
        "icon": "🚀",
        "desc": "Desktop app for managing ONI nodes, registering domains, and hosting websites",
        "size": "~2 MB",
        "files": [
            "apps/oni_manager.py",
        ],
        "deps": [],
        "required": False,
    },
    "devkit": {
        "name": "ONI DevKit",
        "icon": "📖",
        "desc": "Complete developer documentation, API reference, examples, and tutorials",
        "size": "~1 MB",
        "files": [
            "ONI_DevKit/index.html",
            "examples/helloworld.orb/index.html",
            "examples/myblog.orb/index.html",
        ],
        "deps": [],
        "required": False,
    },
    "registrar": {
        "name": "Domain Registrar",
        "icon": "🌍",
        "desc": "Web app for registering free .orb domains (requires ONI Manager)",
        "size": "~0.5 MB",
        "files": [
            "ons/ons_server.py",
            "orbit-registrar/registrar.py",
            "orbit-registrar/templates/",
            "orbit-registrar/static/",
        ],
        "deps": [],
        "required": False,
    },
    "docker": {
        "name": "Docker Support",
        "icon": "🐳",
        "desc": "Dockerfile and docker-compose.yml for self-hosting ONI 24/7",
        "size": "~0.1 MB",
        "files": [
            "Dockerfile", "docker-compose.yml",
        ],
        "deps": [],
        "required": False,
    },
}

# Desktop files
DESKTOP_FILES = {
    "browser": {
        "name": "Orbit Browser",
        "exec": "python3 /usr/share/oni/apps/orbit_browser_app.py",
        "icon": "orbit-browser",
        "categories": "Network;WebBrowser;",
        "comment": "Browse the ONI decentralized web",
    },
    "manager": {
        "name": "ONI Manager",
        "exec": "python3 /usr/share/oni/apps/oni_manager.py",
        "icon": "oni-manager",
        "categories": "Network;Utility;",
        "comment": "Manage your ONI network nodes and domains",
    },
}


class ONIInstaller:
    """GUI installer for ONI components."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ONI Installer - Orbital Network Infrastructure")
        self.root.geometry("720x620")
        self.root.configure(bg="#0a0a1a")
        self.root.resizable(False, False)
        
        # Dark theme
        self.root.tk_setPalette(
            background="#0a0a1a",
            foreground="#e0e0ff",
            activeBackground="#1a1a3a",
            activeForeground="#00ff88",
            highlightColor="#00ff88",
        )
        
        self.selections = {
            "browser": tk.BooleanVar(value=True),   # Always required
            "manager": tk.BooleanVar(value=True),
            "devkit": tk.BooleanVar(value=False),
            "registrar": tk.BooleanVar(value=False),
            "docker": tk.BooleanVar(value=False),
        }
        
        self.install_dir = tk.StringVar(value=str(Path.home() / "ONI"))
        self.install_progress = tk.StringVar(value="")
        
        self._build_ui()
    
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Header
        header = tk.Frame(self.root, bg="#111133", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header, text="🌐 ONI Installer", font=("Courier New", 20, "bold"),
                bg="#111133", fg="#00ffcc").place(x=30, y=15)
        tk.Label(header, text=f"v{INSTALLER_VERSION}  •  Orbital Network Infrastructure",
                font=("Courier New", 9), bg="#111133", fg="#8888aa").place(x=30, y=50)
        
        # Main frame
        main = tk.Frame(self.root, bg="#0a0a1a", padx=20, pady=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Component selection
        select_frame = tk.LabelFrame(main, text=" Choose Components to Install ",
                                    font=("Courier New", 11, "bold"),
                                    bg="#1a1a3a", fg="#00ffcc",
                                    padx=15, pady=10, bd=1, relief=tk.RAISED)
        select_frame.pack(fill=tk.X, pady=(0, 10))
        
        for key, comp in COMPONENTS.items():
            frame = tk.Frame(select_frame, bg="#1a1a3a")
            frame.pack(fill=tk.X, pady=4)
            
            var = self.selections[key]
            is_required = comp.get("required", False)
            
            cb = tk.Checkbutton(frame, text=f"{comp['icon']}  {comp['name']}",
                               variable=var,
                               bg="#1a1a3a", fg="#e0e0ff",
                               selectcolor="#0a0a1a",
                               font=("Segoe UI", 11, "bold"),
                               state="disabled" if is_required else "normal")
            cb.pack(side=tk.LEFT)
            
            tk.Label(frame, text=f"({comp['size']})", font=("Segoe UI", 8),
                    bg="#1a1a3a", fg="#555").pack(side=tk.LEFT, padx=5)
            
            if is_required:
                tk.Label(frame, text="(required)", font=("Segoe UI", 8),
                        bg="#1a1a3a", fg="#00ff88").pack(side=tk.LEFT, padx=5)
            
            tk.Label(frame, text=comp['desc'], font=("Segoe UI", 8),
                    bg="#1a1a3a", fg="#8888aa").pack(anchor=tk.W, padx=35)
        
        # Install directory
        dir_frame = tk.LabelFrame(main, text=" Install Location ",
                                 font=("Courier New", 10, "bold"),
                                 bg="#1a1a3a", fg="#00ffcc",
                                 padx=15, pady=8, bd=1, relief=tk.RAISED)
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        dir_entry = tk.Entry(dir_frame, textvariable=self.install_dir,
                            font=("Courier New", 10), bg="#0a0a1a", fg="#00ffcc",
                            insertbackground="#00ff88", relief=tk.FLAT, bd=8)
        dir_entry.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 8))
        
        tk.Button(dir_frame, text="Browse", font=("Courier New", 9),
                 bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                 command=self._browse_dir, cursor="hand2").pack(side=tk.RIGHT)
        
        # Action buttons
        btn_frame = tk.Frame(main, bg="#0a0a1a")
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.install_btn = tk.Button(btn_frame, text="📥 Install Selected",
                                    font=("Courier New", 13, "bold"),
                                    bg="#00ff88", fg="#0a0a1a", relief=tk.FLAT,
                                    command=self._start_install, cursor="hand2",
                                    padx=30, pady=10)
        self.install_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="✕ Cancel", font=("Courier New", 11),
                 bg="#330000", fg="#ff4444", relief=tk.FLAT,
                 command=self.root.quit, cursor="hand2", padx=20, pady=8).pack(side=tk.RIGHT, padx=5)
        
        # Progress area
        prog_frame = tk.LabelFrame(main, text=" Progress ",
                                   font=("Courier New", 10, "bold"),
                                   bg="#1a1a3a", fg="#00ffcc",
                                   padx=10, pady=5, bd=1, relief=tk.RAISED)
        prog_frame.pack(fill=tk.BOTH, expand=True)
        
        self.progress_bar = ttk.Progressbar(prog_frame, mode="indeterminate", length=600)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(
            prog_frame, wrap=tk.WORD,
            font=("Courier New", 9),
            bg="#0a0a1a", fg="#88ff88",
            insertbackground="#00ff88",
            relief=tk.FLAT, bd=1, height=8,
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Tags
        self.output_text.tag_configure("info", foreground="#e0e0ff")
        self.output_text.tag_configure("success", foreground="#00ff88")
        self.output_text.tag_configure("warning", foreground="#ffaa00")
        self.output_text.tag_configure("error", foreground="#ff4444")
        
        self._log("ONI Installer started. Select components and click Install.", "info")
        self._log(f"Install directory: {self.install_dir.get()}", "info")
    
    def _log(self, msg, tag="info"):
        self.output_text.insert(tk.END, f"> {msg}\n", tag)
        self.output_text.see(tk.END)
        self.root.update()
    
    def _browse_dir(self):
        from tkinter import filedialog
        d = filedialog.askdirectory(title="Select Install Directory")
        if d:
            self.install_dir.set(d)
    
    def _start_install(self):
        self.install_btn.config(state="disabled", text="⏳ Installing...")
        self.progress_bar.start()
        
        thread = threading.Thread(target=self._install, daemon=True)
        thread.start()
    
    def _install(self):
        install_dir = Path(self.install_dir.get())
        selected = [key for key, var in self.selections.items() if var.get()]
        
        try:
            # Step 1: Create directories
            self._log("\n📁 Creating directories...", "info")
            dirs = [
                install_dir, install_dir / "apps", install_dir / "p2p",
                install_dir / "ons", install_dir / "data",
                install_dir / "data/cache", install_dir / "data/domains",
                install_dir / "data/peers", install_dir / "data/logs",
            ]
            if "devkit" in selected:
                dirs.extend([install_dir / "ONI_DevKit", install_dir / "examples",
                           install_dir / "examples/helloworld.orb",
                           install_dir / "examples/myblog.orb"])
            if "registrar" in selected:
                dirs.extend([install_dir / "orbit-registrar",
                           install_dir / "orbit-registrar/templates",
                           install_dir / "orbit-registrar/static"])
            for d in dirs:
                d.mkdir(parents=True, exist_ok=True)
            self._log("✅ Directories created", "success")
            
            # Step 2: Copy source files
            self._log("\n📦 Copying source files...", "info")
            source_root = ONI_ROOT
            
            for key in selected:
                comp = COMPONENTS[key]
                for rel_path in comp["files"]:
                    src = source_root / rel_path
                    dst = install_dir / rel_path
                    
                    if src.is_dir():
                        import shutil
                        if dst.exists():
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    elif src.is_file():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        with open(src, "rb") as f:
                            content = f.read()
                        with open(dst, "wb") as f:
                            f.write(content)
                
                self._log(f"  ✓ {comp['icon']} {comp['name']} copied", "success")
            
            # Step 3: Install Python dependencies
            self._log("\n📦 Installing Python packages...", "info")
            deps_needed = set()
            for key in selected:
                deps_needed.update(COMPONENTS[key]["deps"])
            
            for dep in deps_needed:
                self._log(f"  Installing {dep}...", "info")
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", dep, "-q",
                         "--break-system-packages"],
                        capture_output=True, timeout=60
                    )
                    self._log(f"  ✓ {dep} installed", "success")
                except:
                    try:
                        subprocess.run(
                            [sys.executable, "-m", "pip", "install", dep, "--user", "-q"],
                            capture_output=True, timeout=60
                        )
                        self._log(f"  ✓ {dep} installed (user)", "success")
                    except:
                        self._log(f"  ⚠ Could not install {dep}", "warning")
            
            # Step 4: Create desktop entries (Linux)
            if sys.platform == "linux":
                self._log("\n🖥️  Creating desktop entries...", "info")
                apps_dir = Path.home() / ".local/share/applications"
                apps_dir.mkdir(parents=True, exist_ok=True)
                
                for key, info in DESKTOP_FILES.items():
                    if key in selected:
                        desktop_file = apps_dir / f"{key.replace('_', '-')}.desktop"
                        desktop_content = f"""[Desktop Entry]
Name={info['name']}
Comment={info['comment']}
Exec={info['exec']}
Icon={info['icon']}
Terminal=false
Type=Application
Categories={info['categories']}
Keywords=oni;orbit;network;p2p;
"""
                        with open(desktop_file, "w") as f:
                            f.write(desktop_content)
                        desktop_file.chmod(0o755)
                        self._log(f"  ✓ {info['name']} desktop entry created", "success")
                
                subprocess.run(["update-desktop-database", str(apps_dir)],
                             capture_output=True, timeout=10)
            
            # Step 5: Create CLI command
            self._log("\n🔧 Creating 'oni' CLI command...", "info")
            cli_dir = Path.home() / ".local/bin"
            cli_dir.mkdir(parents=True, exist_ok=True)
            
            cli_script = cli_dir / "oni"
            with open(cli_script, "w") as f:
                f.write(f"""#!/bin/bash
ONI_DIR="{install_dir}"
PYTHON=$(command -v python3 || command -v python)
case "$1" in
    start)       shift; $PYTHON "$ONI_DIR/start_oni.py" "$@" ;;
    node)        shift; $PYTHON "$ONI_DIR/p2p/oni_node.py" "$@" ;;
    ons)         shift; $PYTHON "$ONI_DIR/ons/ons_server.py" "$@" ;;
    registrar)   shift; $PYTHON "$ONI_DIR/orbit-registrar/registrar.py" "$@" ;;
    browser)     shift; $PYTHON "$ONI_DIR/apps/orbit_browser_app.py" "$@" ;;
    manager)     shift; $PYTHON "$ONI_DIR/apps/oni_manager.py" "$@" ;;
    devkit)      cd "$ONI_DIR/ONI_DevKit" && $PYTHON -m http.server 9091 --bind 127.0.0.1 ;;
    help|--help|-h)
        echo "ONI - Orbital Network Infrastructure"
        echo "Usage: oni <command>"
        echo "Commands: start|node|ons|registrar|browser|manager|devkit" ;;
    *)           echo "Usage: oni <command> (start|node|ons|registrar|browser|manager|devkit)" ;;
esac
""")
            cli_script.chmod(0o755)
            self._log("✓ 'oni' CLI command created", "success")
            
            # Add to PATH if needed
            bashrc = Path.home() / ".bashrc"
            if bashrc.exists():
                content = bashrc.read_text()
                if "local/bin" not in content:
                    with open(bashrc, "a") as f:
                        f.write('\nexport PATH="$HOME/.local/bin:$PATH"\n')
                    self._log("✓ Added ~/.local/bin to PATH in .bashrc", "success")
            
            zshrc = Path.home() / ".zshrc"
            if zshrc.exists():
                content = zshrc.read_text()
                if "local/bin" not in content:
                    with open(zshrc, "a") as f:
                        f.write('\nexport PATH="$HOME/.local/bin:$PATH"\n')
                    self._log("✓ Added ~/.local/bin to PATH in .zshrc", "success")
            
            # Done!
            self.progress_bar.stop()
            self.progress_bar["value"] = 100
            
            self._log("\n" + "="*50, "success")
            self._log("✅ INSTALLATION COMPLETE!", "success")
            self._log("="*50, "success")
            self._log(f"\n📁 Installed to: {install_dir}", "info")
            
            installed = [COMPONENTS[k]["icon"] + " " + COMPONENTS[k]["name"] for k in selected]
            self._log(f"📦 Installed: {', '.join(installed)}", "info")
            
            self._log("\n🚀 Quick Start:", "info")
            if "browser" in selected:
                self._log("   oni browser    - Launch Orbit Browser", "accent")
            if "manager" in selected:
                self._log("   oni manager    - Launch ONI Manager", "accent")
            if "devkit" in selected:
                self._log("   oni devkit     - Open Developer Kit", "accent")
            
            self._log("\n📱 Or find 'Orbit Browser' and 'ONI Manager' in your app menu!", "info")
            self._log("\n🌐 ONI: The People's Internet", "info")
            
            self.install_btn.config(text="✅ Installed!", bg="#003300", fg="#00ff88")
            messagebox.showinfo("Installation Complete",
                               "ONI installed successfully!\n\n"
                               f"Location: {install_dir}\n"
                               f"Components: {', '.join(installed)}\n\n"
                               "Run 'oni browser' or find in your app menu.")
            
        except Exception as e:
            self.progress_bar.stop()
            self._log(f"\n❌ Installation failed: {e}", "error")
            self.install_btn.config(text="❌ Failed", bg="#330000", fg="#ff4444", state="normal")
    
    def run(self):
        self.root.mainloop()


def main():
    app = ONIInstaller()
    app.run()


if __name__ == "__main__":
    main()