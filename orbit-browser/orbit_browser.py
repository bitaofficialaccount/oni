#!/usr/bin/env python3
# Orbit Browser - ONI Network Browser
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure
#
# The Orbit Browser replaces traditional web browsing with the ONI protocol.
# It supports orb:// protocol, .orb domains, and displays content from the
# P2P network via WebRTC/WebSocket connections.

import sys
import os
import json
import time
import hashlib
import logging
import argparse
import threading
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from http.client import HTTPConnection

sys.path.insert(0, str(Path(__file__).parent.parent))

from p2p.protocol import *
from p2p.peer import Peer, PeerManager
from ons.registry import DomainRegistry

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ONI.Browser")

# Try to import GUI toolkit
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    logger.warning("Tkinter not available. Using CLI mode.")


class OrbitBrowser:
    """Orbit Browser - Browse the ONI network with orb:// protocol."""
    
    def __init__(self, ons_host="127.0.0.1", ons_port=ONS_PORT, oni_node_host="127.0.0.1", oni_node_port=ONI_P2P_PORT):
        self.ons_host = ons_host
        self.ons_port = ons_port
        self.oni_node_host = oni_node_host
        self.oni_node_port = oni_node_port
        self.current_url = None
        self.history = []
        self.registry = DomainRegistry()
        self.local_content = {}  # Cached from ONI nodes
        
        print(f"""
 ╔══════════════════════════════════════════╗
 ║         Orbit Browser v1.0               ║
 ║      Orbital Network Infrastructure        ║
 ╚══════════════════════════════════════════╝
    Protocol: orb:// (ONI Network)
    ONS:      http://{ons_host}:{ons_port}
    ONI Node: ws://{oni_node_host}:{oni_node_port}
    © 2026 Technic_ Dev
""")
    
    def navigate(self, url):
        """Navigate to a URL on the ONI network."""
        if not url.startswith("orb://"):
            # Try to add orb:// if missing
            if "." in url or url.endswith(".orb"):
                url = f"orb://{url}"
            else:
                logger.error(f"Invalid URL: {url}. Use orb:// format.")
                return None
        
        self.current_url = url
        self.history.append(url)
        
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        path = parsed.path or "/index.html"
        
        logger.info(f"Navigating to: orb://{domain}{path}")
        
        # Resolve domain via ONS
        records = self._resolve_domain(domain)
        if not records:
            # Try local registry
            local_info = self.registry.get_domain(domain)
            if local_info:
                records = local_info.get("records", {})
        
        if not records:
            content = self._generate_error_page(domain, "404 - Domain Not Found",
                f"The domain '{domain}' is not registered on the ONI network.")
            return self._render_content(content, domain)
        
        # Try to fetch content from local ONI node
        content = self._fetch_from_oni_node(domain, path)
        if content:
            return self._render_content(content, domain)
        
        # Generate a placeholder page
        content = self._generate_site_page(domain, path, records)
        return self._render_content(content, domain)
    
    def _resolve_domain(self, domain):
        """Resolve a .orb domain via ONS."""
        try:
            import urllib.request
            url = f"http://{self.ons_host}:{self.ons_port}/resolve/{domain}"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                if data.get("found"):
                    return data.get("records")
        except Exception as e:
            logger.warning(f"ONS resolve failed: {e}")
        return None
    
    def _fetch_from_oni_node(self, domain, path):
        """Fetch content from an ONI node via HTTP API."""
        # ONI nodes expose an HTTP API for content
        try:
            import urllib.request
            # Connect to the local ONI node's HTTP status endpoint
            conn = HTTPConnection(self.oni_node_host, self.oni_node_port)
            conn.request("GET", f"/content/{domain}{path}")
            response = conn.getresponse()
            if response.status == 200:
                content_type = response.getheader("Content-Type", CONTENT_TYPE_HTML)
                data = response.read()
                if content_type.startswith("text/"):
                    return data.decode("utf-8")
            conn.close()
        except:
            pass
        return None
    
    def _generate_error_page(self, domain, title, message):
        """Generate an error page."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Orbit Browser</title>
    <style>
        body {{ font-family: 'Courier New', monospace; background: #0a0a1a; color: #e0e0ff; 
               display: flex; justify-content: center; align-items: center; min-height: 100vh;
               margin: 0; padding: 20px; }}
        .error-box {{ background: #111133; border: 2px solid #ff4444; border-radius: 10px; 
                     padding: 40px; max-width: 500px; text-align: center; }}
        .error-code {{ font-size: 3em; color: #ff4444; margin-bottom: 10px; }}
        .error-title {{ font-size: 1.5em; color: #ff8888; margin-bottom: 10px; }}
        .error-message {{ color: #8888aa; margin-bottom: 20px; line-height: 1.5; }}
        .orb-badge {{ display: inline-block; background: #003366; color: #00ffcc; padding: 5px 15px; 
                     border-radius: 5px; font-size: 0.9em; }}
        .browser-bar {{ background: #1a1a3a; padding: 10px; border-radius: 5px; margin-bottom: 20px;
                       border: 1px solid #333366; }}
    </style>
</head>
<body>
    <div class="error-box">
        <div class="browser-bar">🌐 orb://{domain}</div>
        <div class="error-code">⚠️</div>
        <div class="error-title">{title}</div>
        <div class="error-message">{message}</div>
        <div class="orb-badge">ONI Network - .orb Domain</div>
        <p style="color:#555;margin-top:20px;font-size:0.8em;">
            Orbit Browser v1.0 — © 2026 Technic_ Dev
        </p>
    </div>
</body>
</html>"""
    
    def _generate_site_page(self, domain, path, records):
        """Generate a page for a known domain."""
        # Check if we have local content cached
        if domain in self.local_content:
            content_data = self.local_content[domain]
            file_path = path.lstrip("/")
            if file_path in content_data.get("files", {}):
                return content_data["files"][file_path].get("content", "")
        
        # Generate a dynamic page
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{domain} - Orbit Browser</title>
    <style>
        body {{ font-family: 'Courier New', monospace; background: #0a0a1a; color: #e0e0ff; 
               margin: 0; padding: 0; }}
        
        .browser-header {{ background: #111133; border-bottom: 2px solid #00ff88; padding: 15px 30px; }}
        .browser-title {{ font-size: 1.5em; color: #00ffcc; }}
        .browser-subtitle {{ color: #8888aa; font-size: 0.9em; }}
        
        .content {{ padding: 30px; max-width: 800px; margin: 0 auto; }}
        
        .domain-card {{ background: #1a1a3a; border: 1px solid #333366; border-radius: 10px; padding: 30px; 
                       margin: 30px 0; }}
        .domain-name {{ font-size: 2em; color: #00ff88; display: block; margin-bottom: 10px; }}
        .domain-tld {{ display: inline-block; background: #003366; color: #00ffcc; padding: 5px 15px; 
                      border-radius: 5px; font-size: 0.9em; }}
        
        .site-card {{ background: #1a1a3a; border: 1px solid #333366; border-radius: 10px; padding: 30px; 
                     text-align: center; margin: 20px 0; }}
        .site-icon {{ font-size: 3em; }}
        .site-name {{ font-size: 1.5em; color: #00ffcc; display: block; margin: 10px 0; }}
        
        .info {{ background: #111133; border: 1px solid #333366; border-radius: 10px; padding: 20px; 
                margin: 20px 0; }}
        .info h3 {{ color: #00ffaa; margin-bottom: 15px; }}
        .info p {{ color: #8888aa; line-height: 1.6; }}
        
        .nav-bar {{ display: flex; gap: 10px; margin-bottom: 20px; }}
        .nav-btn {{ padding: 8px 16px; border: 1px solid #333366; border-radius: 5px; 
                   background: #111133; color: #e0e0ff; cursor: pointer; text-decoration: none;
                   font-family: inherit; font-size: 0.9em; }}
        .nav-btn:hover {{ border-color: #00ff88; background: #1a1a3a; }}
        
        .footer {{ text-align: center; padding: 20px; color: #555; font-size: 0.8em; }}
        .oni-badge {{ display: inline-block; background: #003366; color: #00ffcc; padding: 3px 10px; 
                     border-radius: 3px; font-size: 0.85em; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="browser-header">
        <div class="browser-title">🌐 orb://{domain}{path}</div>
        <div class="browser-subtitle">ONI Network - Orbital Network Infrastructure</div>
    </div>
    
    <div class="content">
        <div class="nav-bar">
            <span class="nav-btn">← Back</span>
            <span class="nav-btn">→ Forward</span>
            <span class="nav-btn">🔄 Refresh</span>
            <span class="nav-btn">🏠 Home</span>
        </div>
        
        <div class="domain-card">
            <span class="domain-name">{domain}</span>
            <span class="domain-tld">.orb Domain</span>
            <p style="color:#8888aa;margin-top:15px;">
                This domain is registered on the ONI network.
            </p>
        </div>
        
        <div class="site-card">
            <div class="site-icon">🌍</div>
            <span class="site-name">{domain}</span>
            <p style="color:#8888aa;">This .orb site is hosted on the ONI P2P network.</p>
            <p style="color:#555;font-size:0.9em;">
                To build your site, create HTML5 files in your domain directory<br>
                and host them with <code style="background:#000;padding:2px 6px;border-radius:3px;color:#ffaa00;">python3 p2p/oni_node.py --host-domain {domain} /path/to/site</code>
            </p>
        </div>
        
        <div class="info">
            <h3>📡 ONI Network Information</h3>
            <p><strong>Domain:</strong> {domain}</p>
            <p><strong>Path:</strong> {path}</p>
            <p><strong>Protocol:</strong> ONI v1.0 (WebSocket/P2P)</p>
            <p><strong>DNS Records:</strong> {json.dumps(records, indent=2)}</p>
            <p><strong>Content:</strong> HTML5 • CSS3 • JavaScript</p>
            <p><strong>Node:</strong> Local ONI Node</p>
        </div>
        
        <div class="footer">
            <p>Orbit Browser v1.0 — Part of the Orbital Network Infrastructure (ONI)</p>
            <p>© 2026 Technic_ Dev</p>
            <span class="oni-badge">ONI: The People's Internet</span>
        </div>
    </div>
</body>
</html>"""
    
    def _render_content(self, content, domain):
        """Render content. In GUI mode shows in window, in CLI prints to console."""
        if GUI_AVAILABLE:
            return content  # Will be rendered by GUI
        else:
            print(f"\n{'='*60}")
            print(f"🌐 orb://{domain}")
            print(f"{'='*60}")
            print(content[:2000] + ("..." if len(content) > 2000 else ""))
            print(f"{'='*60}")
            return content
    
    def cache_local_content(self, domain, files):
        """Cache content from a local ONI node."""
        self.local_content[domain] = {
            "domain": domain,
            "files": files,
            "cached_since": time.time(),
        }
        logger.info(f"Cached content for {domain} ({len(files)} files)")


class OrbitBrowserGUI:
    """GUI version of the Orbit Browser using Tkinter."""
    
    def __init__(self, browser_engine):
        self.browser = browser_engine
        self.root = tk.Tk()
        self.root.title("Orbit Browser - ONI Network")
        self.root.geometry("1024x768")
        self.root.configure(bg="#0a0a1a")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the browser UI."""
        # Style
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure dark theme
        self.root.tk_setPalette(
            background="#0a0a1a",
            foreground="#e0e0ff",
            activeBackground="#1a1a3a",
            activeForeground="#00ff88",
            highlightColor="#00ff88",
            highlightBackground="#00ff88",
            selectColor="#00ff88",
            selectBackground="#003366",
        )
        
        # Navigation bar
        nav_frame = tk.Frame(self.root, bg="#111133", height=50)
        nav_frame.pack(fill=tk.X, side=tk.TOP)
        nav_frame.pack_propagate(False)
        
        # Back button
        self.back_btn = tk.Button(nav_frame, text="←", font=("Courier New", 14),
                                 bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT,
                                 command=self.go_back, cursor="hand2")
        self.back_btn.pack(side=tk.LEFT, padx=5, pady=8)
        
        # Forward button
        self.fwd_btn = tk.Button(nav_frame, text="→", font=("Courier New", 14),
                                bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT,
                                command=self.go_forward, cursor="hand2")
        self.fwd_btn.pack(side=tk.LEFT, padx=2, pady=8)
        
        # Refresh button
        self.refresh_btn = tk.Button(nav_frame, text="↻", font=("Courier New", 14),
                                    bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT,
                                    command=self.refresh_page, cursor="hand2")
        self.refresh_btn.pack(side=tk.LEFT, padx=2, pady=8)
        
        # URL bar
        self.url_var = tk.StringVar(value="orb://")
        self.url_entry = tk.Entry(nav_frame, textvariable=self.url_var,
                                 font=("Courier New", 12),
                                 bg="#0a0a1a", fg="#00ffcc",
                                 insertbackground="#00ff88",
                                 relief=tk.FLAT, bd=10)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.url_entry.bind("<Return>", self.on_navigate)
        
        # Go button
        self.go_btn = tk.Button(nav_frame, text="Go →", font=("Courier New", 12),
                               bg="#00ff88", fg="#0a0a1a", relief=tk.FLAT,
                               command=self.on_navigate, cursor="hand2")
        self.go_btn.pack(side=tk.RIGHT, padx=5, pady=8)
        
        # Status bar
        self.status_frame = tk.Frame(self.root, bg="#111133", height=30)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_frame, text="Ready",
                                    font=("Courier New", 9),
                                    bg="#111133", fg="#8888aa")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.protocol_label = tk.Label(self.status_frame, text="ONI v1.0",
                                      font=("Courier New", 9),
                                      bg="#111133", fg="#00ff88")
        self.protocol_label.pack(side=tk.RIGHT, padx=10)
        
        # Content area (HTML renderer using Text widget)
        content_frame = tk.Frame(self.root, bg="#0a0a1a")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.content_text = scrolledtext.ScrolledText(
            content_frame,
            wrap=tk.WORD,
            font=("Courier New", 11),
            bg="#0a0a1a",
            fg="#e0e0ff",
            insertbackground="#00ff88",
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=20,
            height=30,
        )
        self.content_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for basic styling
        self.content_text.tag_configure("heading1", font=("Courier New", 18, "bold"), foreground="#00ffcc")
        self.content_text.tag_configure("heading2", font=("Courier New", 14, "bold"), foreground="#00ffaa")
        self.content_text.tag_configure("link", foreground="#00ff88", underline=True)
        self.content_text.tag_configure("badge", foreground="#00ffcc", background="#003366")
        self.content_text.tag_configure("code", foreground="#ffaa00", background="#000000")
        self.content_text.tag_configure("error", foreground="#ff4444")
        self.content_text.tag_configure("dim", foreground="#8888aa")
        self.content_text.tag_configure("accent", foreground="#00ff88")
        
        # Home shortcut
        self.root.bind("<Control-h>", lambda e: self.navigate_to("orb://"))
        self.root.bind("<Control-l>", lambda e: self.url_entry.focus())
        self.root.bind("<Control-r>", lambda e: self.refresh_page())
        
        # Show home page
        self.show_home()
    
    def show_home(self):
        """Show the Orbit Browser home page."""
        home_content = f"""
        🌐 ORBIT BROWSER
        ═══════════════════════════════════════
        
        Welcome to the Orbit Browser
        The gateway to the ONI Network
        
        
        📡 QUICK NAVIGATION
        ───────────────────────────────────────
        
        → Enter an orb:// URL above and press Enter
        
        → Example: orb://helloworld.orb
        → Example: orb://myblog.orb
        → Example: orb://docs.orb
        
        
        🌍 FREE .orb DOMAINS
        ───────────────────────────────────────
        
        Register your free domain at the Orbit Domain Registrar:
        http://127.0.0.1:8080
        
        Available TLDs: .orb, .orb.be, .orb.uk, .orb.org, 
                       .orb.fun, .orb.dev, .orb.io, .orb.*
        
        
        🚀 QUICK START
        ───────────────────────────────────────
        
        1. Start ONS Server:   python3 ons/ons_server.py
        2. Start ONI Node:     python3 p2p/oni_node.py --host-domain helloworld.orb examples/helloworld.orb
        3. Start Registrar:    python3 orbit-registrar/registrar.py
        4. Launch Browser:     python3 orbit-browser/orbit_browser.py
        5. Visit orb://helloworld.orb
        
        
        ═══════════════════════════════════════
        Orbit Browser v1.0  |  ONI Protocol
        © 2026 Technic_ Dev
        """
        self._display_content(home_content)
        self.status_label.config(text="Home page loaded")
    
    def on_navigate(self, event=None):
        """Handle navigation event."""
        url = self.url_var.get().strip()
        if url:
            self.navigate_to(url)
    
    def navigate_to(self, url):
        """Navigate to a URL."""
        if not url.startswith("orb://"):
            url = f"orb://{url}"
        self.url_var.set(url)
        self.status_label.config(text=f"Loading {url}...")
        self.root.update()
        
        try:
            content = self.browser.navigate(url)
            if content:
                # Simplify HTML for display
                display_text = self._simplify_html(content)
                self._display_content(display_text)
                self.status_label.config(text=f"Loaded: {url}")
            else:
                self.status_label.config(text=f"Failed to load: {url}")
        except Exception as e:
            error = f"⚠️ ERROR: {str(e)}"
            self._display_content(f"\n\n\t{error}\n\n\tPlease check:\n\t- Is the ONS server running?\n\t- Is the ONI node active?\n\t- Is the domain registered?")
            self.status_label.config(text=f"Error: {e}")
    
    def _simplify_html(self, html):
        """Extract text from HTML for display."""
        import re
        
        # Remove script contents
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        # Remove style contents but keep them
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        
        # Replace common tags with text markers
        html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n\n═══ \1 ═══\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n\n─── \1 ───\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n\n--- \1 ---\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<br\s*/?>', '\n', html, flags=re.DOTALL)
        html = re.sub(r'<li[^>]*>(.*?)</li>', r'  • \1\n', html, flags=re.DOTALL)
        html = re.sub(r'<strong>(.*?)</strong>', r'*\1*', html)
        html = re.sub(r'<code>(.*?)</code>', r'`\1`', html)
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<div[^>]*>(.*?)</div>', r'\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', html, flags=re.DOTALL)
        html = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', html)
        
        # Remove remaining tags
        html = re.sub(r'<[^>]+>', '', html)
        
        # Decode HTML entities
        html = html.replace('&nbsp;', ' ').replace('<', '<').replace('>', '>')
        html = html.replace('"', '"').replace('&#39;', "'")
        html = html.replace('&', '&')
        
        # Clean up excessive whitespace
        html = re.sub(r'\n{3,}', '\n\n', html)
        
        return html.strip()
    
    def _display_content(self, text):
        """Display content in the browser window."""
        self.content_text.delete(1.0, tk.END)
        self.content_text.insert(1.0, text)
        self.content_text.see(1.0)  # Scroll to top
    
    def go_back(self):
        """Go back in history."""
        self.status_label.config(text="Back (not fully implemented in terminal mode)")
    
    def go_forward(self):
        """Go forward in history."""
        self.status_label.config(text="Forward (not fully implemented in terminal mode)")
    
    def refresh_page(self):
        """Refresh the current page."""
        url = self.url_var.get()
        if url:
            self.navigate_to(url)
    
    def run(self):
        """Run the browser GUI."""
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Orbit Browser - ONI Network Browser")
    parser.add_argument("--url", default="orb://", help="URL to navigate to on startup")
    parser.add_argument("--ons-host", default="127.0.0.1", help="ONS server host")
    parser.add_argument("--ons-port", type=int, default=ONS_PORT, help="ONS server port")
    parser.add_argument("--oni-host", default="127.0.0.1", help="ONI node host")
    parser.add_argument("--oni-port", type=int, default=ONI_P2P_PORT, help="ONI node port")
    parser.add_argument("--no-gui", action="store_true", help="Force CLI mode even if GUI available")
    
    args = parser.parse_args()
    
    # Create browser engine
    engine = OrbitBrowser(args.ons_host, args.ons_port, args.oni_host, args.oni_port)
    
    if GUI_AVAILABLE and not args.no_gui:
        # Launch GUI
        browser_gui = OrbitBrowserGUI(engine)
        
        if args.url and args.url != "orb://":
            browser_gui.navigate_to(args.url)
        
        browser_gui.run()
    else:
        # CLI mode
        if args.url and args.url != "orb://":
            engine.navigate(args.url)
        else:
            print("""
╔══════════════════════════════════════════╗
║         Orbit Browser (CLI Mode)         ║
║      Orbital Network Infrastructure      ║
╚══════════════════════════════════════════╝

Commands:
  navigate <url>  - Navigate to an orb:// URL
  home            - Show home page
  help            - Show this help
  quit            - Exit

Example:
  navigate orb://helloworld.orb
""")
            while True:
                try:
                    cmd = input("\norb> ").strip()
                    if cmd == "quit" or cmd == "exit":
                        break
                    elif cmd == "home":
                        print("\nUse: navigate orb:// (or a specific .orb domain)")
                    elif cmd.startswith("navigate "):
                        url = cmd[9:].strip()
                        engine.navigate(url)
                    else:
                        print(f"Unknown command: {cmd}")
                except (KeyboardInterrupt, EOFError):
                    break
                except Exception as e:
                    print(f"Error: {e}")


if __name__ == "__main__":
    main()