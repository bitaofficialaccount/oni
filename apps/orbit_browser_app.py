#!/usr/bin/env python3
# Orbit Browser - Standalone Desktop App for ONI Network
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure
#
# This is the standalone desktop application for browsing the ONI network.
# It supports:
# - orb:// protocol and .orb domain resolution
# - Syncing bookmarks, history, and tabs between devices
# - HTML content rendering with dark theme
# - Peer-to-peer content fetching

import sys
import os
import json
import re
import time
import html as html_mod
import threading
import argparse
import urllib.parse
import logging
from pathlib import Path
from http.client import HTTPConnection
from datetime import datetime

# Ensure we can import ONI modules
ONI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ONI_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ONI.Browser")

# Try to import GUI
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, simpledialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("ERROR: tkinter not available. Install with: sudo apt install python3-tk")
    sys.exit(1)

from p2p.protocol import *
from p2p.peer import Peer, PeerManager
from ons.resolver import DNSResolver


class OrbitBrowserEngine:
    """Core browser engine for the ONI network."""
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = ONI_ROOT / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.ons_host = "127.0.0.1"
        self.ons_port = ONS_PORT
        self.oni_host = "127.0.0.1"
        self.oni_port = ONI_P2P_PORT
        
        self.resolver = DNSResolver()
        self.current_url = None
        self.history = []
        self.history_index = -1
        
        # Bookmarks file
        self.bookmarks_file = self.data_dir / "bookmarks.json"
        self.bookmarks = self._load_bookmarks()
        
        # History file
        self.history_file = self.data_dir / "browser_history.json"
        self._load_history()
        
        # Sync data file
        self.sync_file = self.data_dir / "sync_data.json"
        self.sync_data = self._load_sync_data()
        
        # Cache
        self.cache = {}
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        logger.info("Orbit Browser Engine initialized")
    
    def _load_bookmarks(self):
        """Load bookmarks from file."""
        if self.bookmarks_file.exists():
            try:
                with open(self.bookmarks_file) as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_bookmarks(self):
        """Save bookmarks to file."""
        with open(self.bookmarks_file, "w") as f:
            json.dump(self.bookmarks, f, indent=2)
    
    def _load_history(self):
        """Load browsing history."""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    self.history = json.load(f)
            except:
                pass
    
    def _save_history(self):
        """Save browsing history."""
        try:
            # Keep last 1000 entries
            self.history = self.history[-1000:]
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except:
            pass
    
    def _load_sync_data(self):
        """Load sync data for cross-device sharing."""
        if self.sync_file.exists():
            try:
                with open(self.sync_file) as f:
                    return json.load(f)
            except:
                pass
        return {
            "bookmarks": [],
            "history": [],
            "last_sync": None,
            "device_id": None,
        }
    
    def _save_sync_data(self):
        """Save sync data."""
        self.sync_data["bookmarks"] = self.bookmarks
        self.sync_data["last_sync"] = time.time()
        with open(self.sync_file, "w") as f:
            json.dump(self.sync_data, f, indent=2)
    
    def navigate(self, url):
        """Navigate to an orb:// URL."""
        if not url:
            return self._generate_home_page()
        
        # Normalize URL
        url = url.strip()
        if not url.startswith("orb://"):
            if "." in url or url.endswith(".orb"):
                url = f"orb://{url}"
            else:
                return self._generate_error_page("Invalid URL", 
                    f"URL '{url}' is not valid. Use orb://domain.orb format.")
        
        self.current_url = url
        
        # Add to history
        history_entry = {
            "url": url,
            "timestamp": time.time(),
            "date": datetime.now().isoformat(),
        }
        self.history.append(history_entry)
        self.history_index = len(self.history) - 1
        self._save_history()
        
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        path = parsed.path or "/index.html"
        
        logger.info(f"Navigating to: {domain}{path}")
        
        # Try to resolve domain
        records = self._resolve_domain(domain)
        
        if records:
            # Try to fetch content from ONI node
            content = self._fetch_content(domain, path)
            if content:
                return content
        
        # Check cache
        cache_key = f"{domain}{path}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if time.time() - cached["time"] < 300:  # 5 min cache
                return cached["content"]
        
        # Generate a placeholder page
        return self._generate_site_page(domain, path, records)
    
    def _resolve_domain(self, domain):
        """Resolve a .orb domain."""
        try:
            import urllib.request
            url = f"http://{self.ons_host}:{self.ons_port}/resolve/{domain}"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                if data.get("found"):
                    return data.get("records")
        except:
            pass
        
        # Try local resolver
        try:
            result = self.resolver.resolve(domain)
            if result:
                return result
        except:
            pass
        
        return None
    
    def _fetch_content(self, domain, path):
        """Fetch content from an ONI node."""
        try:
            import urllib.request
            conn = HTTPConnection(self.oni_host, self.oni_port, timeout=5)
            conn.request("GET", f"/content/{domain}{path}")
            response = conn.getresponse()
            if response.status == 200:
                content_type = response.getheader("Content-Type", CONTENT_TYPE_HTML)
                data = response.read()
                if content_type.startswith("text/"):
                    content = data.decode("utf-8", errors="replace")
                    # Cache it
                    cache_key = f"{domain}{path}"
                    self.cache[cache_key] = {
                        "content": content,
                        "time": time.time(),
                    }
                    # Also save to disk cache
                    cache_file = self.cache_dir / f"{domain.replace('.', '_')}_{path.replace('/', '_')}.html"
                    try:
                        with open(cache_file, "w") as f:
                            f.write(content)
                    except:
                        pass
                    return content
            conn.close()
        except:
            pass
        return None
    
    def get_bookmarked(self, url):
        """Check if URL is bookmarked."""
        for b in self.bookmarks:
            if b.get("url") == url:
                return True
        return False
    
    def add_bookmark(self, url, title=None):
        """Add a bookmark."""
        if not self.get_bookmarked(url):
            self.bookmarks.append({
                "url": url,
                "title": title or url,
                "added": time.time(),
            })
            self._save_bookmarks()
            self._save_sync_data()
            return True
        return False
    
    def remove_bookmark(self, url):
        """Remove a bookmark."""
        self.bookmarks = [b for b in self.bookmarks if b.get("url") != url]
        self._save_bookmarks()
        self._save_sync_data()
    
    def sync_with_other_device(self, peer_address):
        """Sync bookmarks and history with another Orbit Browser instance."""
        try:
            import urllib.request
            url = f"http://{peer_address}/oni-sync"
            data = {
                "bookmarks": self.bookmarks,
                "history": self.history[-50:],  # Last 50 entries
                "device_id": self.sync_data.get("device_id"),
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                # Merge received bookmarks
                if "bookmarks" in result:
                    existing_urls = {b["url"] for b in self.bookmarks}
                    for bm in result["bookmarks"]:
                        if bm["url"] not in existing_urls:
                            self.bookmarks.append(bm)
                    self._save_bookmarks()
                return True, "Sync successful"
        except Exception as e:
            return False, f"Sync failed: {e}"
    
    def _generate_home_page(self):
        """Generate the browser home page."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Orbit Browser - ONI Network</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0a0a1a; color: #e0e0ff; 
               min-height: 100vh; }
        .header { background: linear-gradient(135deg, #0d0d2b 0%, #1a1a3a 100%); 
                  border-bottom: 2px solid #00ff88; padding: 40px 20px; text-align: center; }
        .logo { font-size: 3em; color: #00ffcc; font-weight: bold; letter-spacing: 4px; }
        .subtitle { color: #8888aa; font-size: 1.1em; margin-top: 10px; }
        .tagline { color: #00ff88; font-size: 0.9em; margin-top: 5px; }
        
        .content { max-width: 800px; margin: 0 auto; padding: 30px 20px; }
        
        .section { background: #111133; border: 1px solid #333366; border-radius: 12px; 
                   padding: 25px; margin: 20px 0; }
        .section h2 { color: #00ffcc; font-size: 1.3em; margin-bottom: 15px; 
                      border-bottom: 1px solid #333366; padding-bottom: 10px; }
        .section p { color: #8888aa; line-height: 1.6; margin: 8px 0; }
        
        .quick-links { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                       gap: 10px; margin: 15px 0; }
        .quick-link { background: #1a1a3a; border: 1px solid #333366; border-radius: 8px; 
                      padding: 15px; text-align: center; cursor: pointer; transition: all 0.2s; }
        .quick-link:hover { border-color: #00ff88; background: #1a1a4a; }
        .quick-link .icon { font-size: 2em; }
        .quick-link .name { color: #00ffcc; margin-top: 8px; font-weight: bold; }
        .quick-link .desc { color: #666; font-size: 0.85em; margin-top: 4px; }
        
        .badge { display: inline-block; background: #003366; color: #00ffcc; padding: 3px 10px; 
                 border-radius: 4px; font-size: 0.8em; margin: 2px; }
        .footer { text-align: center; padding: 30px; color: #444; font-size: 0.8em; }
        code { background: #000; color: #ffaa00; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; 
                      margin-right: 5px; }
        .status-dot.online { background: #00ff88; box-shadow: 0 0 8px #00ff88; }
        .status-dot.offline { background: #444; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🌐 ORBIT</div>
        <div class="subtitle">Decentralized Web Browser for the ONI Network</div>
        <div class="tagline">⚡ The People's Internet</div>
    </div>
    
    <div class="content">
        <div class="section">
            <h2>🚀 Quick Navigation</h2>
            <div class="quick-links">
                <div class="quick-link" onclick="navigate('orb://helloworld.orb')">
                    <div class="icon">👋</div>
                    <div class="name">Hello World</div>
                    <div class="desc">Example .orb site</div>
                </div>
                <div class="quick-link" onclick="navigate('orb://myblog.orb')">
                    <div class="icon">📝</div>
                    <div class="name">My Blog</div>
                    <div class="desc">Blog example</div>
                </div>
                <div class="quick-link" onclick="navigate('orb://docs.orb')">
                    <div class="icon">📖</div>
                    <div class="name">ONI Docs</div>
                    <div class="desc">Documentation</div>
                </div>
                <div class="quick-link" onclick="window.open('http://127.0.0.1:8080')">
                    <div class="icon">🌍</div>
                    <div class="name">Register Domain</div>
                    <div class="desc">Get free .orb</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📡 Network Status</h2>
            <p><span class="status-dot online"></span> ONI P2P Network — Connected</p>
            <p><span class="status-dot online"></span> ONS Resolver — Active</p>
            <p><span class="status-dot offline"></span> Remote Peers — Check connection</p>
            <p style="margin-top:15px;color:#666;">
                Enter an <code>orb://</code> URL in the address bar above to browse.
            </p>
        </div>
        
        <div class="section">
            <h2>📋 How to Use</h2>
            <p>1. <strong>Start ONI nodes</strong> — Run the ONI Manager app to start your nodes</p>
            <p>2. <strong>Register a domain</strong> — Get a free .orb domain at the Registrar</p>
            <p>3. <strong>Host a website</strong> — Point your domain to your website files</p>
            <p>4. <strong>Browse</strong> — Visit any .orb site by typing <code>orb://domain.orb</code></p>
            <p>5. <strong>Sync</strong> — Bookmarks and history sync across your devices</p>
        </div>
        
        <div class="section">
            <h2>🔗 Available TLDs</h2>
            <p>
                <span class="badge">.orb</span>
                <span class="badge">.orb.be</span>
                <span class="badge">.orb.uk</span>
                <span class="badge">.orb.org</span>
                <span class="badge">.orb.fun</span>
                <span class="badge">.orb.dev</span>
                <span class="badge">.orb.io</span>
                <span class="badge">.orb.*</span>
            </p>
        </div>
        
        <div class="footer">
            <p>Orbit Browser v1.0  |  ONI Protocol  |  Orbital Network Infrastructure</p>
            <p>© 2026 Technic_ Dev  |  ONI: The People's Internet</p>
        </div>
    </div>
</body>
</html>"""
    
    def _generate_error_page(self, title, message):
        """Generate an error page."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{title} - Orbit Browser</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0a0a1a; color:#e0e0ff;
        display:flex; justify-content:center; align-items:center; min-height:100vh; }}
.error {{ background:#111133; border:2px solid #ff4444; border-radius:12px; padding:40px;
          max-width:500px; text-align:center; }}
.error-icon {{ font-size:3em; margin-bottom:10px; }}
.error-title {{ font-size:1.5em; color:#ff8888; margin-bottom:10px; }}
.error-msg {{ color:#8888aa; line-height:1.5; margin-bottom:20px; }}
.badge {{ display:inline-block; background:#003366; color:#00ffcc; padding:5px 15px; border-radius:5px; }}
</style></head>
<body>
<div class="error">
  <div class="error-icon">⚠️</div>
  <div class="error-title">{title}</div>
  <div class="error-msg">{message}</div>
  <div class="badge">🌐 ONI Network</div>
</div>
</body>
</html>"""
    
    def _generate_site_page(self, domain, path, records=None):
        """Generate a page for a known domain."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{domain} - Orbit Browser</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0a0a1a; color:#e0e0ff; }}
.header {{ background:#111133; border-bottom:2px solid #00ff88; padding:20px 30px; }}
.title {{ font-size:1.5em; color:#00ffcc; }}
.subtitle {{ color:#8888aa; font-size:0.9em; }}
.content {{ max-width:800px; margin:0 auto; padding:30px; }}
.card {{ background:#1a1a3a; border:1px solid #333366; border-radius:10px; padding:30px; margin:20px 0; }}
.domain-name {{ font-size:2em; color:#00ff88; display:block; margin-bottom:10px; }}
.tld-badge {{ display:inline-block; background:#003366; color:#00ffcc; padding:5px 15px; border-radius:5px; }}
.info {{ background:#111133; border:1px solid #333366; border-radius:10px; padding:20px; margin:20px 0; }}
.info h3 {{ color:#00ffaa; margin-bottom:15px; }}
.info p {{ color:#8888aa; line-height:1.6; }}
.info code {{ background:#000; color:#ffaa00; padding:2px 6px; border-radius:3px; }}
.nav {{ display:flex; gap:10px; margin-bottom:20px; }}
.nav-btn {{ padding:8px 16px; border:1px solid #333366; border-radius:5px; background:#111133;
            color:#e0e0ff; text-decoration:none; font-size:0.9em; cursor:pointer; }}
.nav-btn:hover {{ border-color:#00ff88; }}
.footer {{ text-align:center; padding:20px; color:#555; font-size:0.8em; }}
code {{ background:#000; color:#ffaa00; padding:2px 6px; border-radius:3px; }}
</style></head>
<body>
<div class="header">
  <div class="title">🌐 orb://{domain}{path}</div>
  <div class="subtitle">ONI Network - {domain}</div>
</div>
<div class="content">
  <div class="nav">
    <span class="nav-btn">← Back</span>
    <span class="nav-btn">🔄 Refresh</span>
    <span class="nav-btn">🏠 Home</span>
  </div>
  
  <div class="card">
    <span class="domain-name">{domain}</span>
    <span class="tld-badge">.orb Domain</span>
    <p style="color:#8888aa;margin-top:15px;">
      This domain is registered on the ONI decentralized network.
    </p>
  </div>
  
  <div class="info">
    <h3>📡 Site Information</h3>
    <p><strong>Domain:</strong> {domain}</p>
    <p><strong>Path:</strong> {path}</p>
    <p><strong>Protocol:</strong> ONI v1.0</p>
    <p><strong>Network:</strong> P2P / WebSocket</p>
    <p style="margin-top:15px;">
      This site is hosted on the ONI network. To build your own, create HTML files 
      and host them with:
    </p>
    <p style="margin-top:10px;">
      <code>oni node --host-domain {domain} /path/to/site</code>
    </p>
  </div>
  
  <div class="footer">
    <p>Orbit Browser v1.0  |  ONI Network  © 2026 Technic_ Dev</p>
  </div>
</div>
</body>
</html>"""


class OrbitBrowserApp:
    """Standalone GUI application for the Orbit Browser."""
    
    def __init__(self, engine):
        self.engine = engine
        self.root = tk.Tk()
        self.root.title("Orbit Browser - ONI Network")
        self.root.geometry("1100x750")
        self.root.configure(bg="#0a0a1a")
        self.root.minsize(800, 500)
        
        # Dark theme
        self.root.tk_setPalette(
            background="#0a0a1a",
            foreground="#e0e0ff",
            activeBackground="#1a1a3a",
            activeForeground="#00ff88",
            highlightColor="#00ff88",
            highlightBackground="#00ff88",
        )
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Build the browser UI."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # --- Menu ---
        menubar = tk.Menu(self.root, bg="#111133", fg="#e0e0ff", activebackground="#003366")
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Window", command=self.new_window)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        bookmarks_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="Bookmarks", menu=bookmarks_menu)
        bookmarks_menu.add_command(label="Add Bookmark", command=self.add_bookmark)
        bookmarks_menu.add_command(label="Manage Bookmarks", command=self.show_bookmarks)
        bookmarks_menu.add_separator()
        self.bookmarks_menu_items = bookmarks_menu
        
        tools_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="History", command=self.show_history)
        tools_menu.add_command(label="Sync with Device", command=self.sync_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Open DevKit", command=self.open_devkit)
        
        help_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About Orbit Browser", command=self.show_about)
        
        # --- Navigation Bar ---
        nav_frame = tk.Frame(self.root, bg="#111133", height=45)
        nav_frame.pack(fill=tk.X, side=tk.TOP)
        nav_frame.pack_propagate(False)
        
        # Back/Forward
        self.back_btn = tk.Button(nav_frame, text="←", font=("Courier New", 14),
                                 bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT, 
                                 command=self.go_back, cursor="hand2", width=3)
        self.back_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        self.fwd_btn = tk.Button(nav_frame, text="→", font=("Courier New", 14),
                                bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT,
                                command=self.go_forward, cursor="hand2", width=3)
        self.fwd_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        self.refresh_btn = tk.Button(nav_frame, text="↻", font=("Courier New", 14),
                                    bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT,
                                    command=self.refresh, cursor="hand2", width=3)
        self.refresh_btn.pack(side=tk.LEFT, padx=2, pady=5)
        
        # URL bar
        self.url_var = tk.StringVar(value="orb://")
        self.url_entry = tk.Entry(nav_frame, textvariable=self.url_var,
                                 font=("Courier New", 12),
                                 bg="#0a0a1a", fg="#00ffcc",
                                 insertbackground="#00ff88",
                                 relief=tk.FLAT, bd=10)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.url_entry.bind("<Return>", self.on_navigate)
        self.url_entry.bind("<Control-l>", lambda e: self.url_entry.select_range(0, tk.END))
        
        # Go button
        self.go_btn = tk.Button(nav_frame, text="Go →", font=("Courier New", 12),
                               bg="#00ff88", fg="#0a0a1a", relief=tk.FLAT,
                               command=self.on_navigate, cursor="hand2", padx=10)
        self.go_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Bookmark button
        self.bookmark_btn = tk.Button(nav_frame, text="☆", font=("Courier New", 16),
                                     bg="#1a1a3a", fg="#8888aa", relief=tk.FLAT,
                                     command=self.toggle_bookmark, cursor="hand2", width=3)
        self.bookmark_btn.pack(side=tk.RIGHT, padx=2, pady=5)
        
        # --- Status Bar ---
        status_frame = tk.Frame(self.root, bg="#111133", height=28)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame, text="Ready",
                                    font=("Courier New", 9),
                                    bg="#111133", fg="#8888aa")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.protocol_label = tk.Label(status_frame, text="ONI v1.0 • .orb",
                                      font=("Courier New", 9),
                                      bg="#111133", fg="#00ff88")
        self.protocol_label.pack(side=tk.RIGHT, padx=10)
        
        self.sync_status = tk.Label(status_frame, text="●",
                                   font=("Courier New", 9),
                                   bg="#111133", fg="#444")
        self.sync_status.pack(side=tk.RIGHT, padx=5)
        
        # --- Content Area ---
        content_frame = tk.Frame(self.root, bg="#0a0a1a")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.content_text = scrolledtext.ScrolledText(
            content_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg="#0a0a1a",
            fg="#e0e0ff",
            insertbackground="#00ff88",
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=20,
        )
        self.content_text.pack(fill=tk.BOTH, expand=True)
        
        # Disable editing
        self.content_text.bind("<Key>", lambda e: "break")
        
        # Text tags for HTML-like rendering
        self._setup_text_tags()
        
        # Keyboard shortcuts
        self.root.bind("<Control-h>", lambda e: self.show_history())
        self.root.bind("<Control-d>", lambda e: self.add_bookmark())
        self.root.bind("<Control-r>", lambda e: self.refresh())
        
        # Load home page
        self.show_home()
    
    def _setup_text_tags(self):
        """Set up text tags for content rendering."""
        tags = {
            "h1": ("Courier New", 18, "bold"),
            "h2": ("Courier New", 14, "bold"),
            "h3": ("Courier New", 12, "bold"),
            "link": ("Segoe UI", 11, "underline"),
            "code": ("Courier New", 10, ""),
            "badge": ("Courier New", 9, ""),
            "error": ("Segoe UI", 11, ""),
            "dim": ("Segoe UI", 11, ""),
            "accent": ("Segoe UI", 11, "bold"),
            "normal": ("Segoe UI", 11, ""),
        }
        
        colors = {
            "h1": "#00ffcc",
            "h2": "#00ffaa",
            "h3": "#00ff88",
            "link": "#00ff88",
            "code": "#ffaa00",
            "badge": "#00ffcc",
            "error": "#ff4444",
            "dim": "#8888aa",
            "accent": "#00ff88",
            "normal": "#e0e0ff",
        }
        
        bg_colors = {
            "badge": "#003366",
            "code": "#000000",
        }
        
        for tag, font_info in tags.items():
            font_family, font_size, font_weight = font_info
            weight = "bold" if font_weight == "bold" else "normal"
            underline = 1 if font_weight == "underline" else 0
            
            config = {
                "font": (font_family, font_size, weight),
                "foreground": colors.get(tag, "#e0e0ff"),
                "underline": underline,
            }
            if tag in bg_colors:
                config["background"] = bg_colors[tag]
                config["lmargin1"] = 2
                config["lmargin2"] = 2
            
            self.content_text.tag_configure(tag, **config)
        
        # Spacing tags
        self.content_text.tag_configure("spacer", spacing=15)
        self.content_text.tag_configure("line", spacing=5)
    
    def _display_html(self, html_content):
        """Display HTML content in the text widget (simplified renderer)."""
        self.content_text.delete(1.0, tk.END)
        
        if not html_content:
            return
        
        # Strip HTML and display as formatted text
        text = self._html_to_text(html_content)
        self.content_text.insert(1.0, text)
        self.content_text.see(1.0)
    
    def _html_to_text(self, html):
        """Convert HTML to plain text with markers for styling."""
        import re
        
        # Remove scripts
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        
        # Replace tags with text markers
        html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n══ \1 ══\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n── \1 ──\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n--- \1 ---\n\n', html, flags=re.DOTALL)
        html = re.sub(r'<br\s*/?>', '\n', html)
        html = re.sub(r'<li[^>]*>(.*?)</li>', r'  • \1\n', html, flags=re.DOTALL)
        html = re.sub(r'<strong>(.*?)</strong>', r'*\1*', html)
        html = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', html)
        html = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<div[^>]*>(.*?)</div>', r'\1\n', html, flags=re.DOTALL)
        html = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', html, flags=re.DOTALL)
        html = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', html)
        
        # Remove remaining tags
        html = re.sub(r'<[^>]+>', '', html)
        
        # Decode entities
        html = html.replace('&nbsp;', ' ').replace('<', '<').replace('>', '>')
        html = html.replace('"', '"').replace('&#39;', "'").replace('&', '&')
        
        # Clean whitespace
        html = re.sub(r'\n{4,}', '\n\n\n', html)
        
        return html.strip()
    
    def show_home(self):
        """Show the home page."""
        content = self.engine._generate_home_page()
        self._display_html(content)
        self.url_var.set("orb://")
        self.status_label.config(text="Home")
        self._update_bookmark_btn()
    
    def on_navigate(self, event=None):
        """Handle navigation from URL bar."""
        url = self.url_var.get().strip()
        if url:
            self.navigate_to(url)
    
    def navigate_to(self, url):
        """Navigate to a URL."""
        if not url.startswith("orb://"):
            if "." in url or url.endswith(".orb"):
                url = f"orb://{url}"
            elif url == "about:home" or url == "orb://":
                self.show_home()
                return
        
        self.url_var.set(url)
        self.status_label.config(text=f"Loading {url}...")
        self.root.update()
        
        try:
            content = self.engine.navigate(url)
            if content:
                self._display_html(content)
                self.status_label.config(text=f"Loaded: {url}")
            else:
                self.status_label.config(text=f"Failed: {url}")
                self._display_html(self.engine._generate_error_page(
                    "Navigation Failed",
                    f"Could not load {url}. Check that ONI nodes are running."
                ))
        except Exception as e:
            self.status_label.config(text=f"Error: {e}")
            self._display_html(self.engine._generate_error_page(
                "Error", str(e)
            ))
        
        self._update_bookmark_btn()
    
    def go_back(self):
        """Go back in history."""
        if self.engine.history_index > 0:
            self.engine.history_index -= 1
            entry = self.engine.history[self.engine.history_index]
            self.navigate_to(entry["url"])
    
    def go_forward(self):
        """Go forward in history."""
        if self.engine.history_index < len(self.engine.history) - 1:
            self.engine.history_index += 1
            entry = self.engine.history[self.engine.history_index]
            self.navigate_to(entry["url"])
    
    def refresh(self):
        """Refresh current page."""
        url = self.url_var.get()
        if url and url != "orb://":
            self.navigate_to(url)
        else:
            self.show_home()
    
    def toggle_bookmark(self):
        """Toggle bookmark for current URL."""
        url = self.url_var.get()
        if url and url != "orb://":
            if self.engine.get_bookmarked(url):
                self.engine.remove_bookmark(url)
                self.status_label.config(text="Bookmark removed")
            else:
                self.engine.add_bookmark(url)
                self.status_label.config(text="Bookmark added")
            self._update_bookmark_btn()
    
    def _update_bookmark_btn(self):
        """Update bookmark button appearance."""
        url = self.url_var.get()
        if self.engine.get_bookmarked(url):
            self.bookmark_btn.config(text="★", fg="#ffcc00")
        else:
            self.bookmark_btn.config(text="☆", fg="#8888aa")
    
    def add_bookmark(self):
        """Add current page as bookmark."""
        url = self.url_var.get()
        if url and url != "orb://":
            self.engine.add_bookmark(url)
            self._update_bookmark_btn()
            self.status_label.config(text="Bookmarked!")
        else:
            messagebox.showinfo("Bookmark", "Navigate to a page first")
    
    def show_bookmarks(self):
        """Show bookmarks dialog."""
        bookmarks = self.engine.bookmarks
        if not bookmarks:
            messagebox.showinfo("Bookmarks", "No bookmarks yet.")
            return
        
        win = tk.Toplevel(self.root)
        win.title("Bookmarks")
        win.geometry("500x400")
        win.configure(bg="#0a0a1a")
        
        frame = tk.Frame(win, bg="#1a1a3a", padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(frame, text="Your Bookmarks", font=("Courier New", 14, "bold"),
                bg="#1a1a3a", fg="#00ffcc").pack(anchor=tk.W, pady=(0, 10))
        
        listbox = tk.Listbox(frame, bg="#0a0a1a", fg="#e0e0ff",
                            selectbackground="#003366", font=("Segoe UI", 10),
                            height=15)
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        for bm in bookmarks:
            title = bm.get("title", bm.get("url", "Unknown"))
            listbox.insert(tk.END, f"{title}")
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def open_selected():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                url = bookmarks[idx].get("url")
                win.destroy()
                self.navigate_to(url)
        
        def delete_selected():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                url = bookmarks[idx].get("url")
                self.engine.remove_bookmark(url)
                listbox.delete(idx)
        
        btn_frame = tk.Frame(frame, bg="#1a1a3a")
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="Open", font=("Courier New", 9),
                 bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                 command=open_selected, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", font=("Courier New", 9),
                 bg="#330000", fg="#ff4444", relief=tk.FLAT,
                 command=delete_selected, cursor="hand2").pack(side=tk.LEFT, padx=5)
    
    def show_history(self):
        """Show browsing history."""
        history = self.engine.history
        if not history:
            messagebox.showinfo("History", "No history yet.")
            return
        
        win = tk.Toplevel(self.root)
        win.title("History")
        win.geometry("600x450")
        win.configure(bg="#0a0a1a")
        
        frame = tk.Frame(win, bg="#1a1a3a", padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(frame, text="Browsing History", font=("Courier New", 14, "bold"),
                bg="#1a1a3a", fg="#00ffcc").pack(anchor=tk.W, pady=(0, 10))
        
        listbox = tk.Listbox(frame, bg="#0a0a1a", fg="#e0e0ff",
                            selectbackground="#003366", font=("Segoe UI", 9),
                            height=18)
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        for entry in reversed(history[-100:]):
            url = entry.get("url", "")
            date = entry.get("date", "")[:19]
            listbox.insert(tk.END, f"[{date}] {url}")
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def open_selected():
            selection = listbox.curselection()
            if selection:
                idx = len(history) - 1 - selection[0]
                entry = history[idx]
                win.destroy()
                self.navigate_to(entry["url"])
        
        def clear_history():
            self.engine.history = []
            self.engine._save_history()
            listbox.delete(0, tk.END)
        
        btn_frame = tk.Frame(frame, bg="#1a1a3a")
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="Open", font=("Courier New", 9),
                 bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                 command=open_selected, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear All", font=("Courier New", 9),
                 bg="#330000", fg="#ff4444", relief=tk.FLAT,
                 command=clear_history, cursor="hand2").pack(side=tk.LEFT, padx=5)
    
    def sync_dialog(self):
        """Show sync dialog for cross-device sync."""
        win = tk.Toplevel(self.root)
        win.title("Sync with Device")
        win.geometry("450x200")
        win.configure(bg="#0a0a1a")
        
        frame = tk.Frame(win, bg="#1a1a3a", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(frame, text="Sync Bookmarks & History", font=("Courier New", 14, "bold"),
                bg="#1a1a3a", fg="#00ffcc").pack(anchor=tk.W, pady=(0, 15))
        
        tk.Label(frame, text="Enter peer address (IP:port):", font=("Courier New", 10),
                bg="#1a1a3a", fg="#8888aa").pack(anchor=tk.W, pady=(0, 5))
        
        entry = tk.Entry(frame, width=30, font=("Courier New", 11),
                        bg="#0a0a1a", fg="#00ffcc", insertbackground="#00ff88")
        entry.pack(fill=tk.X, pady=5)
        entry.insert(0, "192.168.")
        
        result_label = tk.Label(frame, text="", bg="#1a1a3a", fg="#00ff88",
                               font=("Courier New", 9))
        result_label.pack(pady=10)
        
        def do_sync():
            addr = entry.get().strip()
            if not addr:
                return
            result_label.config(text="Syncing...")
            win.update()
            
            success, msg = self.engine.sync_with_other_device(addr)
            if success:
                result_label.config(text=f"✓ {msg}")
                self.sync_status.config(fg="#00ff88")
            else:
                result_label.config(text=f"✗ {msg}")
        
        tk.Button(frame, text="🔄 Sync Now", font=("Courier New", 10),
                 bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                 command=do_sync, cursor="hand2", padx=20, pady=5).pack()
    
    def new_window(self):
        """Open a new browser window."""
        import subprocess
        subprocess.Popen([sys.executable, __file__])
    
    def open_devkit(self):
        """Open the ONI DevKit."""
        import webbrowser
        devkit_path = ONI_ROOT / "ONI_DevKit" / "index.html"
        if devkit_path.exists():
            webbrowser.open(f"file://{devkit_path}")
        else:
            messagebox.showinfo("DevKit", "ONI DevKit not found.")
    
    def show_about(self):
        messagebox.showinfo("About Orbit Browser",
                           "Orbit Browser v1.0\n"
                           "Part of the Orbital Network Infrastructure\n\n"
                           "Browse the decentralized P2P web\n"
                           "with .orb domains and the ONI protocol.\n\n"
                           "Features:\n"
                           "• orb:// protocol support\n"
                           "• Bookmark sync across devices\n"
                           "• Browsing history\n"
                           "• Dark theme\n\n"
                           "© 2026 Technic_ Dev")
    
    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Orbit Browser - Standalone App")
    parser.add_argument("--url", default="orb://", help="URL to open on startup")
    parser.add_argument("--data-dir", help="Data directory for bookmarks/history")
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir) if args.data_dir else None
    engine = OrbitBrowserEngine(data_dir)
    app = OrbitBrowserApp(engine)
    
    if args.url and args.url != "orb://":
        app.navigate_to(args.url)
    
    app.run()


if __name__ == "__main__":
    main()