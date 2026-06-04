#!/usr/bin/env python3
# Orbit Browser - Standalone Desktop App for ONI Network
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure
#
# One-click ONI browser. Auto-starts nodes in the background.
# Uses Supabase as the universal cloud backbone (like the real internet).
# Anyone can see any hosted .orb site from anywhere.

import sys
import os
import json
import re
import time
import threading
import subprocess
import argparse
import urllib.parse
import urllib.request
import logging
from pathlib import Path
from http.client import HTTPConnection
from datetime import datetime

ONI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ONI_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ONI.Browser")

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

# Try to use Supabase as global cloud backbone
try:
    from supabase_client import (
        SUPABASE_AVAILABLE,
        resolve_domain as sb_resolve_domain,
        get_domain as sb_get_domain,
        get_site_file as sb_get_site_file,
        register_peer as sb_register_peer,
        get_active_peers as sb_get_active_peers,
        check_connection as sb_check_connection,
    )
    CLOUD_BACKEND_AVAILABLE = SUPABASE_AVAILABLE
except ImportError:
    CLOUD_BACKEND_AVAILABLE = False


class OrbitBrowserEngine:
    """Core browser engine. Auto-starts nodes, uses cloud backbone."""
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = ONI_ROOT / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.resolver = DNSResolver()
        self.current_url = None
        self.history = []
        self.history_index = -1
        
        # Background processes
        self.oni_node_process = None
        self.ons_process = None
        self.nodes_running = False
        
        # Bookmarks
        self.bookmarks_file = self.data_dir / "bookmarks.json"
        self.bookmarks = self._load_json(self.bookmarks_file, [])
        
        # History
        self.history_file = self.data_dir / "browser_history.json"
        self._load_history()
        
        # Cache
        self.cache_dir = self.data_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache = {}
        
        # Cloud status
        self.cloud_available = CLOUD_BACKEND_AVAILABLE
        
        logger.info("Orbit Browser Engine initialized")
        if self.cloud_available:
            logger.info("☁️ Universal cloud backbone ACTIVE (Supabase)")
        else:
            logger.warning("⚠️  No cloud backbone. Set up .env with Supabase credentials for universal access.")
        
        # Auto-start background nodes
        self._auto_start_nodes()
    
    def _load_json(self, path, default=None):
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except:
                pass
        return default or {}
    
    def _save_json(self, path, data):
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except:
            pass
    
    def _load_history(self):
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    self.history = json.load(f)
            except:
                pass
    
    def _save_history(self):
        try:
            self.history = self.history[-1000:]
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except:
            pass
    
    def _auto_start_nodes(self):
        """Auto-start ONI node and ONS server in background threads."""
        def start_oni():
            try:
                self.oni_node_process = subprocess.Popen(
                    [sys.executable, str(ONI_ROOT / "p2p" / "oni_node.py"),
                     "--host", "127.0.0.1", "--port", str(ONI_P2P_PORT)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(1.5)
                if self.oni_node_process.poll() is None:
                    self.nodes_running = True
                    logger.info("✅ ONI P2P node auto-started")
            except Exception as e:
                logger.warning(f"⚠️  Could not auto-start ONI node: {e}")
        
        def start_ons():
            try:
                self.ons_process = subprocess.Popen(
                    [sys.executable, str(ONI_ROOT / "ons" / "ons_server.py"),
                     "--port", str(ONS_PORT)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                time.sleep(1)
                logger.info("✅ ONS server auto-started")
            except Exception as e:
                logger.warning(f"⚠️  Could not auto-start ONS: {e}")
        
        # Start in background threads
        threading.Thread(target=start_oni, daemon=True).start()
        threading.Thread(target=start_ons, daemon=True).start()
    
    def navigate(self, url):
        """Navigate to an orb:// URL. Resolves globally via cloud backbone + P2P."""
        if not url:
            return self._generate_home_page()
        
        url = url.strip()
        if not url.startswith("orb://"):
            if "." in url or url.endswith(".orb"):
                url = f"orb://{url}"
            else:
                return self._generate_error_page("Invalid URL", 
                    f"'{url}' is not valid. Use orb://domain.orb")
        
        self.current_url = url
        
        # Add to history
        history_entry = {"url": url, "timestamp": time.time(), "date": datetime.now().isoformat()}
        self.history.append(history_entry)
        self.history_index = len(self.history) - 1
        self._save_history()
        
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        path = parsed.path or "/index.html"
        
        logger.info(f"Navigating to: {domain}{path}")
        
        # STEP 1: Try cloud backbone (Supabase) - the universal internet
        content = self._fetch_from_cloud(domain, path)
        if content:
            return content
        
        # STEP 2: Try local ONI node (P2P from other peers)
        content = self._fetch_from_oni_node(domain, path)
        if content:
            return content
        
        # STEP 3: Try to resolve domain and find hosting peer
        hosting_peer = self._find_hosting_peer(domain)
        if hosting_peer:
            content = self._fetch_from_peer(hosting_peer, domain, path)
            if content:
                return content
        
        # STEP 4: Check cache
        cache_key = f"{domain}{path}"
        if cache_key in self.memory_cache:
            cached = self.memory_cache[cache_key]
            if time.time() - cached["time"] < 300:
                return cached["content"]
        
        # STEP 5: Show domain info page if it exists but has no content yet
        domain_info = self._resolve_domain_global(domain)
        if domain_info:
            return self._generate_site_page(domain, path, domain_info)
        
        return self._generate_error_page("Domain Not Found",
            f"The domain '{domain}' is not registered anywhere on the ONI network.\n\n"
            f"Register it for FREE at the Orbit Domain Registrar (http://127.0.0.1:8080)\n"
            f"or in the ONI Manager app.")
    
    def _resolve_domain_global(self, domain):
        """Resolve domain globally - tries cloud first, then local."""
        # Try Supabase cloud backbone first (universal)
        if self.cloud_available:
            try:
                info = sb_get_domain(domain)
                if info:
                    return info
            except:
                pass
        
        # Try local ONS
        try:
            import urllib.request
            url = f"http://127.0.0.1:{ONS_PORT}/resolve/{domain}"
            with urllib.request.urlopen(url, timeout=3) as response:
                data = json.loads(response.read())
                if data.get("found"):
                    return data.get("records")
        except:
            pass
        
        # Try local resolver
        try:
            return self.resolver.resolve(domain)
        except:
            pass
        
        return None
    
    def _fetch_from_cloud(self, domain, path):
        """Fetch content from Supabase cloud backbone (universal storage)."""
        if not self.cloud_available:
            return None
        try:
            file_data = sb_get_site_file(domain, path)
            if file_data:
                content = file_data.get("content", "")
                if content:
                    logger.info(f"☁️ Fetched from cloud: {domain}{path}")
                    return content
        except:
            pass
        return None
    
    def _fetch_from_oni_node(self, domain, path):
        """Fetch from local ONI node."""
        try:
            conn = HTTPConnection("127.0.0.1", ONI_P2P_PORT, timeout=5)
            conn.request("GET", f"/content/{domain}{path}")
            response = conn.getresponse()
            if response.status == 200:
                content_type = response.getheader("Content-Type", CONTENT_TYPE_HTML)
                data = response.read()
                if content_type.startswith("text/"):
                    content = data.decode("utf-8", errors="replace")
                    cache_key = f"{domain}{path}"
                    self.memory_cache[cache_key] = {"content": content, "time": time.time()}
                    logger.info(f"🔗 Fetched from P2P node: {domain}{path}")
                    return content
            conn.close()
        except:
            pass
        return None
    
    def _find_hosting_peer(self, domain):
        """Find which peer is hosting a domain via cloud backbone."""
        if not self.cloud_available:
            return None
        try:
            peers = sb_get_active_peers()
            for peer in peers:
                hosted = peer.get("hosted_domains", [])
                if domain in hosted:
                    return {"host": peer.get("host"), "port": peer.get("port")}
        except:
            pass
        return None
    
    def _fetch_from_peer(self, peer_info, domain, path):
        """Fetch content from a specific peer."""
        host = peer_info.get("host")
        port = peer_info.get("port")
        if not host or not port:
            return None
        try:
            conn = HTTPConnection(host, port, timeout=10)
            conn.request("GET", f"/content/{domain}{path}")
            response = conn.getresponse()
            if response.status == 200:
                content_type = response.getheader("Content-Type", CONTENT_TYPE_HTML)
                data = response.read()
                if content_type.startswith("text/"):
                    content = data.decode("utf-8", errors="replace")
                    logger.info(f"🌍 Fetched from peer {host}:{port}: {domain}{path}")
                    return content
            conn.close()
        except:
            pass
        return None
    
    def get_bookmarked(self, url):
        for b in self.bookmarks:
            if b.get("url") == url:
                return True
        return False
    
    def add_bookmark(self, url, title=None):
        if not self.get_bookmarked(url):
            self.bookmarks.append({"url": url, "title": title or url, "added": time.time()})
            self._save_json(self.bookmarks_file, self.bookmarks)
            return True
        return False
    
    def remove_bookmark(self, url):
        self.bookmarks = [b for b in self.bookmarks if b.get("url") != url]
        self._save_json(self.bookmarks_file, self.bookmarks)
    
    def sync_with_other_device(self, peer_address):
        """Sync bookmarks with another browser instance."""
        try:
            url = f"http://{peer_address}/oni-sync"
            data = {"bookmarks": self.bookmarks, "device_id": None}
            req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                        headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                if "bookmarks" in result:
                    existing_urls = {b["url"] for b in self.bookmarks}
                    for bm in result["bookmarks"]:
                        if bm["url"] not in existing_urls:
                            self.bookmarks.append(bm)
                    self._save_json(self.bookmarks_file, self.bookmarks)
                return True, "Sync successful"
        except Exception as e:
            return False, f"Sync failed: {e}"
    
    def _generate_home_page(self):
        """Home page showing universal network status."""
        cloud_status = "🟢 Online" if self.cloud_available else "🔴 Offline (local only)"
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Orbit Browser - ONI Network</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0a0a1a; color:#e0e0ff; min-height:100vh; }}
.header {{ background:linear-gradient(135deg,#0d0d2b,#1a1a3a); border-bottom:2px solid #00ff88; padding:35px 20px; text-align:center; }}
.logo {{ font-size:2.5em; color:#00ffcc; font-weight:bold; letter-spacing:3px; }}
.tagline {{ color:#00ff88; font-size:1em; margin-top:8px; }}
.content {{ max-width:750px; margin:0 auto; padding:25px 20px; }}
.section {{ background:#111133; border:1px solid #333366; border-radius:12px; padding:22px; margin:15px 0; }}
.section h2 {{ color:#00ffcc; font-size:1.2em; margin-bottom:12px; border-bottom:1px solid #333366; padding-bottom:8px; }}
.section p {{ color:#8888aa; line-height:1.6; margin:6px 0; }}
.quick-links {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:12px 0; }}
.quick-link {{ background:#1a1a3a; border:1px solid #333366; border-radius:8px; padding:15px; text-align:center; cursor:pointer; }}
.quick-link:hover {{ border-color:#00ff88; }}
.quick-link .icon {{ font-size:1.8em; }}
.quick-link .name {{ color:#00ffcc; margin-top:6px; font-weight:bold; font-size:0.9em; }}
.badge {{ display:inline-block; background:#003366; color:#00ffcc; padding:3px 10px; border-radius:4px; font-size:0.8em; margin:2px; }}
.footer {{ text-align:center; padding:25px; color:#444; font-size:0.8em; }}
code {{ background:#000; color:#ffaa00; padding:2px 6px; border-radius:3px; }}
.status-dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; }}
</style></head>
<body>
<div class="header">
  <div class="logo">🌐 ORBIT</div>
  <div class="tagline">⚡ The ONI Network — Universal Decentralized Web</div>
</div>
<div class="content">
  <div class="section">
    <h2>🌍 Network Status</h2>
    <p><span class="status-dot" style="background:{'#00ff88' if self.cloud_available else '#ff4444'}"></span> Cloud Backbone: {cloud_status}</p>
    <p><span class="status-dot" style="background:{'#00ff88' if self.nodes_running else '#ffaa00'}"></span> P2P Node: {'Running' if self.nodes_running else 'Starting...'}</p>
    <p><span class="status-dot" style="background:#00ff88"></span> ONS Resolver: Active</p>
    <p style="margin-top:10px;color:#666;">Enter an <code>orb://</code> URL above to browse the decentralized web.</p>
  </div>
  <div class="section">
    <h2>🚀 Quick Navigation</h2>
    <div class="quick-links">
      <div class="quick-link"><div class="icon">👋</div><div class="name">helloworld.orb</div></div>
      <div class="quick-link"><div class="icon">📝</div><div class="name">myblog.orb</div></div>
      <div class="quick-link"><div class="icon">📖</div><div class="name">docs.orb</div></div>
      <div class="quick-link"><div class="icon">🌍</div><div class="name">Register Domain</div></div>
    </div>
  </div>
  <div class="section">
    <h2>📋 How It Works (Universal Internet)</h2>
    <p>1. <strong>Register</strong> a free .orb domain at <code>http://127.0.0.1:8080</code></p>
    <p>2. <strong>Host</strong> your website — it's stored on the cloud backbone AND your local node</p>
    <p>3. <strong>The whole world</strong> can visit <code>orb://yourdomain.orb</code> from any Orbit Browser</p>
    <p>4. Content syncs across the P2P network automatically</p>
  </div>
  <div class="section">
    <h2>🔗 Available TLDs</h2>
    <p><span class="badge">.orb</span> <span class="badge">.orb.be</span> <span class="badge">.orb.uk</span> <span class="badge">.orb.org</span> <span class="badge">.orb.fun</span> <span class="badge">.orb.dev</span> <span class="badge">.orb.io</span> <span class="badge">.orb.*</span></p>
  </div>
  <div class="footer">
    <p>Orbit Browser v1.0 | ONI Protocol | Orbital Network Infrastructure</p>
    <p>© 2026 Technic_ Dev | ONI: The People's Internet</p>
  </div>
</div>
</body>
</html>"""
    
    def _generate_error_page(self, title, message):
        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>{title} - Orbit Browser</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',system-ui,sans-serif; background:#0a0a1a; color:#e0e0ff; display:flex; justify-content:center; align-items:center; min-height:100vh; }}
.error {{ background:#111133; border:2px solid #ff4444; border-radius:12px; padding:40px; max-width:500px; text-align:center; }}
.error-icon {{ font-size:3em; margin-bottom:10px; }}
.error-title {{ font-size:1.5em; color:#ff8888; margin-bottom:10px; }}
.error-msg {{ color:#8888aa; line-height:1.5; margin-bottom:20px; white-space:pre-line; }}
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
.nav-btn {{ padding:8px 16px; border:1px solid #333366; border-radius:5px; background:#111133; color:#e0e0ff; cursor:pointer; }}
.nav-btn:hover {{ border-color:#00ff88; }}
.footer {{ text-align:center; padding:20px; color:#555; font-size:0.8em; }}
</style></head>
<body>
<div class="header">
  <div class="title">🌐 orb://{domain}{path}</div>
  <div class="subtitle">ONI Network — {domain}</div>
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
    <p style="color:#8888aa;margin-top:15px;">This domain is registered on the ONI decentralized network.</p>
  </div>
  <div class="info">
    <h3>📡 Universal Site Info</h3>
    <p><strong>Domain:</strong> {domain}</p>
    <p><strong>Path:</strong> {path}</p>
    <p><strong>Protocol:</strong> ONI v1.0 (Cloud + P2P)</p>
    <p><strong>Backbone:</strong> {'Supabase Cloud' if self.cloud_available else 'Local Only'}</p>
    <p style="margin-top:15px;">This site is registered on the ONI network. The owner needs to host it for content to appear.</p>
    <p style="margin-top:10px;"><code>oni node --host-domain {domain} /path/to/site</code></p>
  </div>
  <div class="footer">
    <p>Orbit Browser v1.0 | ONI Network © 2026 Technic_ Dev</p>
  </div>
</div>
</body>
</html>"""
    
    def cleanup(self):
        """Stop background nodes."""
        for proc in [self.oni_node_process, self.ons_process]:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except:
                    pass


class OrbitBrowserApp:
    """GUI Application - auto-starts nodes, uses universal cloud backbone."""
    
    def __init__(self, engine):
        self.engine = engine
        self.root = tk.Tk()
        self.root.title("Orbit Browser - ONI Network")
        self.root.geometry("1100x750")
        self.root.configure(bg="#0a0a1a")
        self.root.minsize(800, 500)
        
        self.root.tk_setPalette(
            background="#0a0a1a", foreground="#e0e0ff",
            activeBackground="#1a1a3a", activeForeground="#00ff88",
            highlightColor="#00ff88", highlightBackground="#00ff88",
        )
        
        self._setup_ui()
        
        # Show cloud backbone status in title after 2 seconds
        self.root.after(2000, self._show_connection_status)
    
    def _show_connection_status(self):
        if self.engine.cloud_available:
            self.status_label.config(text="☁️ Universal Cloud Backbone Active")
            self.protocol_label.config(text="ONI Cloud + P2P")
        else:
            self.status_label.config(text="⚠️ Local Only — Set up .env for cloud access")
    
    def _setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Menu
        menubar = tk.Menu(self.root, bg="#111133", fg="#e0e0ff", activebackground="#003366")
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Window", command=self.new_window)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_exit)
        
        bookmarks_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="Bookmarks", menu=bookmarks_menu)
        bookmarks_menu.add_command(label="Add Bookmark", command=self.add_bookmark)
        bookmarks_menu.add_command(label="Manage Bookmarks", command=self.show_bookmarks)
        
        tools_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="History", command=self.show_history)
        tools_menu.add_command(label="Sync Bookmarks", command=self.sync_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="Open Registrar", command=self.open_registrar)
        tools_menu.add_command(label="Open DevKit", command=self.open_devkit)
        
        help_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Nav bar
        nav_frame = tk.Frame(self.root, bg="#111133", height=45)
        nav_frame.pack(fill=tk.X, side=tk.TOP)
        nav_frame.pack_propagate(False)
        
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
        
        self.url_var = tk.StringVar(value="orb://")
        self.url_entry = tk.Entry(nav_frame, textvariable=self.url_var,
                                 font=("Courier New", 12),
                                 bg="#0a0a1a", fg="#00ffcc",
                                 insertbackground="#00ff88",
                                 relief=tk.FLAT, bd=10)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.url_entry.bind("<Return>", self.on_navigate)
        
        self.go_btn = tk.Button(nav_frame, text="Go →", font=("Courier New", 12),
                               bg="#00ff88", fg="#0a0a1a", relief=tk.FLAT,
                               command=self.on_navigate, cursor="hand2", padx=10)
        self.go_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        self.bookmark_btn = tk.Button(nav_frame, text="☆", font=("Courier New", 16),
                                     bg="#1a1a3a", fg="#8888aa", relief=tk.FLAT,
                                     command=self.toggle_bookmark, cursor="hand2", width=3)
        self.bookmark_btn.pack(side=tk.RIGHT, padx=2, pady=5)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg="#111133", height=28)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame, text="Starting nodes...",
                                    font=("Courier New", 9),
                                    bg="#111133", fg="#8888aa")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.protocol_label = tk.Label(status_frame, text="ONI Cloud + P2P",
                                      font=("Courier New", 9),
                                      bg="#111133", fg="#00ff88")
        self.protocol_label.pack(side=tk.RIGHT, padx=10)
        
        # Content area
        content_frame = tk.Frame(self.root, bg="#0a0a1a")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        self.content_text = scrolledtext.ScrolledText(
            content_frame, wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg="#0a0a1a", fg="#e0e0ff",
            insertbackground="#00ff88",
            relief=tk.FLAT, bd=0, padx=20, pady=20,
        )
        self.content_text.pack(fill=tk.BOTH, expand=True)
        self.content_text.bind("<Key>", lambda e: "break")
        
        self._setup_text_tags()
        self.show_home()
    
    def _setup_text_tags(self):
        tags = {"h1": 18, "h2": 14, "h3": 12, "link": 11, "code": 10, 
                "dim": 11, "accent": 11, "normal": 11, "error": 11}
        for tag, size in tags.items():
            self.content_text.tag_configure(tag, font=("Segoe UI", size))
        self.content_text.tag_configure("h1", font=("Courier New", 18, "bold"), foreground="#00ffcc")
        self.content_text.tag_configure("h2", font=("Courier New", 14, "bold"), foreground="#00ffaa")
        self.content_text.tag_configure("code", font=("Courier New", 10), foreground="#ffaa00", background="#000")
        self.content_text.tag_configure("link", foreground="#00ff88", underline=1)
        self.content_text.tag_configure("error", foreground="#ff4444")
        self.content_text.tag_configure("dim", foreground="#8888aa")
        self.content_text.tag_configure("accent", foreground="#00ff88", font=("Segoe UI", 11, "bold"))
    
    def _display_html(self, html_content):
        self.content_text.delete(1.0, tk.END)
        if not html_content:
            return
        text = self._html_to_text(html_content)
        self.content_text.insert(1.0, text)
        self.content_text.see(1.0)
    
    def _html_to_text(self, html):
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
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
        html = re.sub(r'<[^>]+>', '', html)
        html = html.replace('&nbsp;', ' ').replace('<', '<').replace('>', '>')
        html = html.replace('"', '"').replace('&#39;', "'").replace('&', '&')
        html = re.sub(r'\n{4,}', '\n\n\n', html)
        return html.strip()
    
    def show_home(self):
        content = self.engine._generate_home_page()
        self._display_html(content)
        self.url_var.set("orb://")
        self.status_label.config(text="Home — ONI Network Active")
        self._update_bookmark_btn()
    
    def on_navigate(self, event=None):
        url = self.url_var.get().strip()
        if url:
            self.navigate_to(url)
    
    def navigate_to(self, url):
        if not url.startswith("orb://"):
            if "." in url or url.endswith(".orb"):
                url = f"orb://{url}"
            elif url in ("about:home", "orb://"):
                self.show_home()
                return
        
        self.url_var.set(url)
        self.status_label.config(text=f"🌍 Resolving globally: {url}...")
        self.root.update()
        
        try:
            content = self.engine.navigate(url)
            if content:
                self._display_html(content)
                self.status_label.config(text=f"✅ {url}")
            else:
                self.status_label.config(text=f"❌ Failed: {url}")
        except Exception as e:
            self.status_label.config(text=f"Error: {e}")
        
        self._update_bookmark_btn()
    
    def go_back(self):
        if self.engine.history_index > 0:
            self.engine.history_index -= 1
            self.navigate_to(self.engine.history[self.engine.history_index]["url"])
    
    def go_forward(self):
        if self.engine.history_index < len(self.engine.history) - 1:
            self.engine.history_index += 1
            self.navigate_to(self.engine.history[self.engine.history_index]["url"])
    
    def refresh(self):
        url = self.url_var.get()
        if url and url != "orb://":
            self.navigate_to(url)
        else:
            self.show_home()
    
    def toggle_bookmark(self):
        url = self.url_var.get()
        if url and url != "orb://":
            if self.engine.get_bookmarked(url):
                self.engine.remove_bookmark(url)
                self.status_label.config(text="Bookmark removed")
            else:
                self.engine.add_bookmark(url)
                self.status_label.config(text="⭐ Bookmarked!")
            self._update_bookmark_btn()
    
    def _update_bookmark_btn(self):
        url = self.url_var.get()
        if self.engine.get_bookmarked(url):
            self.bookmark_btn.config(text="★", fg="#ffcc00")
        else:
            self.bookmark_btn.config(text="☆", fg="#8888aa")
    
    def add_bookmark(self):
        url = self.url_var.get()
        if url and url != "orb://":
            self.engine.add_bookmark(url)
            self._update_bookmark_btn()
            self.status_label.config(text="⭐ Bookmarked!")
    
    def show_bookmarks(self):
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
                            selectbackground="#003366", font=("Segoe UI", 10), height=15)
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        for bm in bookmarks:
            listbox.insert(tk.END, bm.get("title", bm.get("url", "")))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        def open_selected():
            sel = listbox.curselection()
            if sel:
                win.destroy()
                self.navigate_to(bookmarks[sel[0]]["url"])
        def delete_selected():
            sel = listbox.curselection()
            if sel:
                url = bookmarks[sel[0]]["url"]
                self.engine.remove_bookmark(url)
                listbox.delete(sel[0])
        btnf = tk.Frame(frame, bg="#1a1a3a")
        btnf.pack(fill=tk.X, pady=10)
        tk.Button(btnf, text="Open", font=("Courier New", 9), bg="#003366", fg="#00ffcc",
                 relief=tk.FLAT, command=open_selected, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btnf, text="Delete", font=("Courier New", 9), bg="#330000", fg="#ff4444",
                 relief=tk.FLAT, command=delete_selected, cursor="hand2").pack(side=tk.LEFT, padx=5)
    
    def show_history(self):
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
                            selectbackground="#003366", font=("Segoe UI", 9), height=18)
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        for entry in reversed(history[-100:]):
            listbox.insert(tk.END, f"[{entry.get('date','')[:19]}] {entry.get('url','')}")
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        def open_selected():
            sel = listbox.curselection()
            if sel:
                idx = len(history) - 1 - sel[0]
                win.destroy()
                self.navigate_to(history[idx]["url"])
        def clear_all():
            self.engine.history = []
            self.engine._save_history()
            listbox.delete(0, tk.END)
        btnf = tk.Frame(frame, bg="#1a1a3a")
        btnf.pack(fill=tk.X, pady=10)
        tk.Button(btnf, text="Open", font=("Courier New", 9), bg="#003366", fg="#00ffcc",
                 relief=tk.FLAT, command=open_selected, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btnf, text="Clear All", font=("Courier New", 9), bg="#330000", fg="#ff4444",
                 relief=tk.FLAT, command=clear_all, cursor="hand2").pack(side=tk.LEFT, padx=5)
    
    def sync_dialog(self):
        win = tk.Toplevel(self.root)
        win.title("Sync Bookmarks")
        win.geometry("450x200")
        win.configure(bg="#0a0a1a")
        frame = tk.Frame(win, bg="#1a1a3a", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(frame, text="Sync Bookmarks with Another Device",
                font=("Courier New", 14, "bold"), bg="#1a1a3a", fg="#00ffcc").pack(anchor=tk.W, pady=(0, 15))
        tk.Label(frame, text="Enter peer address (IP:port):",
                font=("Courier New", 10), bg="#1a1a3a", fg="#8888aa").pack(anchor=tk.W, pady=(0, 5))
        entry = tk.Entry(frame, width=30, font=("Courier New", 11),
                        bg="#0a0a1a", fg="#00ffcc", insertbackground="#00ff88")
        entry.pack(fill=tk.X, pady=5)
        result_label = tk.Label(frame, text="", bg="#1a1a3a", fg="#00ff88", font=("Courier New", 9))
        result_label.pack(pady=10)
        def do_sync():
            addr = entry.get().strip()
            if not addr:
                return
            result_label.config(text="Syncing...")
            win.update()
            success, msg = self.engine.sync_with_other_device(addr)
            result_label.config(text=f"{'✓' if success else '✗'} {msg}")
        tk.Button(frame, text="🔄 Sync Now", font=("Courier New", 10),
                 bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                 command=do_sync, cursor="hand2", padx=20, pady=5).pack()
    
    def open_registrar(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8080")
    
    def open_devkit(self):
        import webbrowser
        devkit_path = ONI_ROOT / "ONI_DevKit" / "index.html"
        if devkit_path.exists():
            webbrowser.open(f"file://{devkit_path}")
    
    def new_window(self):
        subprocess.Popen([sys.executable, __file__])
    
    def show_about(self):
        messagebox.showinfo("Orbit Browser",
                           "Orbit Browser v1.0\n"
                           "Part of the Orbital Network Infrastructure\n\n"
                           "🌐 The Universal Decentralized Web Browser\n\n"
                           "• Auto-starts P2P nodes in the background\n"
                           "• Uses Supabase cloud backbone for global access\n"
                           "• Browse any .orb site from anywhere\n"
                           "• Bookmarks & history management\n\n"
                           "© 2026 Technic_ Dev")
    
    def on_exit(self):
        self.engine.cleanup()
        self.root.quit()
    
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Orbit Browser - Universal ONI Browser")
    parser.add_argument("--url", default="orb://", help="URL to open on startup")
    args = parser.parse_args()
    
    engine = OrbitBrowserEngine()
    app = OrbitBrowserApp(engine)
    
    if args.url and args.url != "orb://":
        app.navigate_to(args.url)
    
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        engine.cleanup()


if __name__ == "__main__":
    main()