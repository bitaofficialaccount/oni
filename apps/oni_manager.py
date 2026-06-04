#!/usr/bin/env python3
# ONI Manager - Desktop Application for managing ONI network
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure
#
# This is a standalone desktop app that manages:
# - Starting/stopping ONI nodes
# - Registering .orb domains
# - Hosting websites on the ONI network
# - Monitoring peers and network status
# - Syncing with other users

import sys
import os
import json
import time
import threading
import subprocess
import logging
import socket
from pathlib import Path

# Ensure we can import ONI modules
ONI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ONI_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ONI.Manager")

# Try to import GUI
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, filedialog
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    print("ERROR: tkinter not available. Install with: sudo apt install python3-tk")
    sys.exit(1)

# ONI imports
from p2p.protocol import *
from p2p.peer import Peer, PeerManager
from p2p.oni_node import ONINode
from ons.registry import DomainRegistry
from ons.resolver import DNSResolver


class ONIManager:
    """Core manager for ONI network operations."""
    
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = ONI_ROOT / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.domain_registry = DomainRegistry()
        self.peer_manager = PeerManager()
        self.resolver = DNSResolver()
        
        # State
        self.oni_node_process = None
        self.ons_process = None
        self.registrar_process = None
        self.node_running = False
        self.ons_running = False
        self.registrar_running = False
        
        # Configuration
        self.config_file = self.data_dir / "manager_config.json"
        self.config = self._load_config()
        
        # Local data
        self.hosted_domains = {}  # domain -> path
        self.known_peers = []
        self.sync_enabled = True
        
        logger.info("ONI Manager initialized")
    
    def _load_config(self):
        """Load manager configuration."""
        default_config = {
            "oni_node_port": ONI_P2P_PORT,
            "ons_port": ONS_PORT,
            "registrar_port": REGISTRAR_PORT,
            "auto_start_nodes": False,
            "sync_enabled": True,
            "sync_interval": 30,
            "last_sync": None,
        }
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    default_config.update(config)
            except:
                pass
        return default_config
    
    def _save_config(self):
        """Save manager configuration."""
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def start_oni_node(self, host="0.0.0.0", port=None):
        """Start an ONI P2P node."""
        if self.node_running:
            return False, "ONI node is already running"
        
        port = port or self.config.get("oni_node_port", ONI_P2P_PORT)
        
        try:
            self.oni_node_process = subprocess.Popen(
                [sys.executable, str(ONI_ROOT / "p2p" / "oni_node.py"),
                 "--host", host, "--port", str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            time.sleep(1)
            if self.oni_node_process.poll() is None:
                self.node_running = True
                logger.info(f"ONI node started on port {port}")
                return True, f"ONI node started on port {port}"
            else:
                return False, "ONI node failed to start"
        except Exception as e:
            return False, f"Error starting ONI node: {e}"
    
    def stop_oni_node(self):
        """Stop an ONI node."""
        if self.oni_node_process and self.oni_node_process.poll() is None:
            self.oni_node_process.terminate()
            self.oni_node_process.wait(timeout=5)
            self.node_running = False
            logger.info("ONI node stopped")
            return True, "ONI node stopped"
        return False, "No ONI node running"
    
    def start_ons_server(self, port=None):
        """Start the ONS server."""
        if self.ons_running:
            return False, "ONS server is already running"
        
        port = port or self.config.get("ons_port", ONS_PORT)
        
        try:
            self.ons_process = subprocess.Popen(
                [sys.executable, str(ONI_ROOT / "ons" / "ons_server.py"),
                 "--port", str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            time.sleep(1)
            if self.ons_process.poll() is None:
                self.ons_running = True
                logger.info(f"ONS server started on port {port}")
                return True, f"ONS server started on port {port}"
            else:
                return False, "ONS server failed to start"
        except Exception as e:
            return False, f"Error starting ONS server: {e}"
    
    def stop_ons_server(self):
        """Stop the ONS server."""
        if self.ons_process and self.ons_process.poll() is None:
            self.ons_process.terminate()
            self.ons_process.wait(timeout=5)
            self.ons_running = False
            logger.info("ONS server stopped")
            return True, "ONS server stopped"
        return False, "No ONS server running"
    
    def start_registrar(self, port=None):
        """Start the domain registrar."""
        if self.registrar_running:
            return False, "Registrar is already running"
        
        port = port or self.config.get("registrar_port", REGISTRAR_PORT)
        
        try:
            self.registrar_process = subprocess.Popen(
                [sys.executable, str(ONI_ROOT / "orbit-registrar" / "registrar.py"),
                 "--port", str(port)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            time.sleep(1)
            if self.registrar_process.poll() is None:
                self.registrar_running = True
                logger.info(f"Registrar started on port {port}")
                return True, f"Registrar started on port {port}"
            else:
                return False, "Registrar failed to start"
        except Exception as e:
            return False, f"Error starting registrar: {e}"
    
    def stop_registrar(self):
        """Stop the domain registrar."""
        if self.registrar_process and self.registrar_process.poll() is None:
            self.registrar_process.terminate()
            self.registrar_process.wait(timeout=5)
            self.registrar_running = False
            logger.info("Registrar stopped")
            return True, "Registrar stopped"
        return False, "No registrar running"
    
    def register_domain(self, domain_name, tld="orb"):
        """Register a .orb domain."""
        full_domain = f"{domain_name}.{tld}"
        try:
            result = self.domain_registry.register_domain(full_domain)
            if result:
                logger.info(f"Domain registered: {full_domain}")
                return True, f"Domain {full_domain} registered"
            return False, f"Domain {full_domain} could not be registered (may already exist)"
        except Exception as e:
            return False, f"Error registering domain: {e}"
    
    def host_website(self, domain, directory_path):
        """Host a website directory for a .orb domain."""
        path = Path(directory_path)
        if not path.exists():
            return False, f"Directory not found: {directory_path}"
        
        self.hosted_domains[domain] = str(path)
        
        # Launch ONI node hosting this domain
        try:
            proc = subprocess.Popen(
                [sys.executable, str(ONI_ROOT / "p2p" / "oni_node.py"),
                 "--host-domain", domain, str(path),
                 "--port", str(self.config.get("oni_node_port", ONI_P2P_PORT) + 1)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            time.sleep(1)
            if proc.poll() is None:
                logger.info(f"Hosting {domain} from {directory_path}")
                return True, f"Hosting {domain} from {directory_path}"
            return False, "Failed to start hosting node"
        except Exception as e:
            return False, f"Error hosting website: {e}"
    
    def sync_with_network(self):
        """Sync domains and peers with the ONI network."""
        if not self.sync_enabled:
            return False, "Sync is disabled"
        
        try:
            # Try to connect to the local ONS for peer list
            import urllib.request
            url = f"http://127.0.0.1:{self.config.get('ons_port', ONS_PORT)}/peers"
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read())
                if "peers" in data:
                    self.known_peers = data["peers"]
            
            # Sync domain registry
            self.domain_registry.sync_with_network()
            
            self.config["last_sync"] = time.time()
            self._save_config()
            logger.info(f"Sync complete: {len(self.known_peers)} peers")
            return True, f"Synced with {len(self.known_peers)} peers"
        except Exception as e:
            logger.warning(f"Sync failed: {e}")
            return False, f"Sync failed: {e}"
    
    def get_status(self):
        """Get overall system status."""
        return {
            "oni_node": self.node_running,
            "ons_server": self.ons_running,
            "registrar": self.registrar_running,
            "hosted_domains": len(self.hosted_domains),
            "known_peers": len(self.known_peers),
            "sync_enabled": self.sync_enabled,
            "last_sync": self.config.get("last_sync"),
        }
    
    def cleanup(self):
        """Clean up all processes."""
        self.stop_oni_node()
        self.stop_ons_server()
        self.stop_registrar()


class ONIManagerGUI:
    """GUI for the ONI Manager."""
    
    def __init__(self, manager):
        self.manager = manager
        self.root = tk.Tk()
        self.root.title("ONI Manager - Orbital Network Infrastructure")
        self.root.geometry("960x680")
        self.root.configure(bg="#0a0a1a")
        self.root.minsize(800, 600)
        
        # Set icon color scheme
        self.root.tk_setPalette(
            background="#0a0a1a",
            foreground="#e0e0ff",
            activeBackground="#1a1a3a",
            activeForeground="#00ff88",
            highlightColor="#00ff88",
            highlightBackground="#00ff88",
        )
        
        self._setup_ui()
        self._start_status_poller()
    
    def _setup_ui(self):
        """Build the GUI."""
        # Style
        style = ttk.Style()
        style.theme_use("clam")
        
        # --- Menu Bar ---
        menubar = tk.Menu(self.root, bg="#111133", fg="#e0e0ff", activebackground="#003366")
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        network_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="Network", menu=network_menu)
        network_menu.add_command(label="Start All Nodes", command=self.start_all)
        network_menu.add_command(label="Stop All Nodes", command=self.stop_all)
        network_menu.add_separator()
        network_menu.add_command(label="Sync Now", command=self.doSync)
        
        help_menu = tk.Menu(menubar, tearoff=0, bg="#111133", fg="#e0e0ff")
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About ONI", command=self.show_about)
        help_menu.add_command(label="Open DevKit", command=self.open_devkit)
        
        # --- Header ---
        header = tk.Frame(self.root, bg="#111133", height=70)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        
        title_label = tk.Label(header, text="ONI MANAGER",
                               font=("Courier New", 22, "bold"),
                               bg="#111133", fg="#00ffcc")
        title_label.pack(side=tk.LEFT, padx=20, pady=15)
        
        version_label = tk.Label(header, text="v1.0  •  Orbital Network Infrastructure",
                                font=("Courier New", 10),
                                bg="#111133", fg="#8888aa")
        version_label.pack(side=tk.LEFT, padx=5, pady=20)
        
        # Status indicator
        self.global_status = tk.Label(header, text="● STOPPED",
                                      font=("Courier New", 12, "bold"),
                                      bg="#111133", fg="#ff4444")
        self.global_status.pack(side=tk.RIGHT, padx=20, pady=20)
        
        # --- Main Content Area (Notebook with tabs) ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Style the notebook for dark theme
        style.configure("TNotebook", background="#0a0a1a", borderwidth=0)
        style.configure("TNotebook.Tab", background="#111133", foreground="#e0e0ff",
                       padding=[15, 5], font=("Courier New", 10))
        style.map("TNotebook.Tab", background=[("selected", "#1a1a3a")],
                 foreground=[("selected", "#00ffcc")])
        
        # Create tabs
        self._create_dashboard_tab()
        self._create_nodes_tab()
        self._create_domains_tab()
        self._create_hosting_tab()
        self._create_peers_tab()
        self._create_logs_tab()
    
    def _create_dashboard_tab(self):
        """Dashboard tab with overview."""
        frame = tk.Frame(self.notebook, bg="#0a0a1a")
        self.notebook.add(frame, text="  📊 Dashboard  ")
        
        # Status cards
        cards_frame = tk.Frame(frame, bg="#0a0a1a")
        cards_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Card data
        cards = [
            ("ONI Node", "node_card", self.manager.node_running),
            ("ONS Server", "ons_card", self.manager.ons_running),
            ("Registrar", "reg_card", self.manager.registrar_running),
            ("Domains", "dom_card", len(self.manager.hosted_domains)),
            ("Peers", "peer_card", len(self.manager.known_peers)),
            ("Sync", "sync_card", self.manager.sync_enabled),
        ]
        
        self.status_cards = {}
        row, col = 0, 0
        for name, key, value in cards:
            card = tk.Frame(cards_frame, bg="#1a1a3a", bd=1, relief=tk.RAISED,
                          highlightbackground="#333366", highlightthickness=1)
            card.grid(row=row // 3, column=col, padx=8, pady=8, sticky="nsew")
            cards_frame.grid_columnconfigure(col, weight=1)
            
            name_label = tk.Label(card, text=name, font=("Courier New", 9),
                                bg="#1a1a3a", fg="#8888aa")
            name_label.pack(pady=(15, 5))
            
            val_label = tk.Label(card, text=str(value), font=("Courier New", 20, "bold"),
                               bg="#1a1a3a", fg="#00ff88")
            val_label.pack(pady=(0, 15))
            
            self.status_cards[key] = val_label
            col += 1
            if col >= 3:
                row += 1
                col = 0
        
        # Quick actions
        actions_frame = tk.Frame(frame, bg="#0a0a1a")
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(actions_frame, text="QUICK ACTIONS", font=("Courier New", 11, "bold"),
                bg="#0a0a1a", fg="#00ffcc").pack(anchor=tk.W, pady=(0, 10))
        
        btn_frame = tk.Frame(actions_frame, bg="#0a0a1a")
        btn_frame.pack(fill=tk.X)
        
        self.btn_start_all = tk.Button(btn_frame, text="▶ Start All", font=("Courier New", 11),
                                      bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                                      command=self.start_all, cursor="hand2", padx=20, pady=8)
        self.btn_start_all.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop_all = tk.Button(btn_frame, text="■ Stop All", font=("Courier New", 11),
                                     bg="#330000", fg="#ff4444", relief=tk.FLAT,
                                     command=self.stop_all, cursor="hand2", padx=20, pady=8)
        self.btn_stop_all.pack(side=tk.LEFT, padx=5)
        
        self.btn_sync = tk.Button(btn_frame, text="🔄 Sync Network", font=("Courier New", 11),
                                 bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT,
                                 command=self.doSync, cursor="hand2", padx=20, pady=8)
        self.btn_sync.pack(side=tk.LEFT, padx=5)
        
        self.btn_host = tk.Button(btn_frame, text="📂 Host Website", font=("Courier New", 11),
                                 bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT,
                                 command=self.host_website_dialog, cursor="hand2", padx=20, pady=8)
        self.btn_host.pack(side=tk.LEFT, padx=5)
    
    def _create_nodes_tab(self):
        """Nodes tab for managing ONI node and ONS server."""
        frame = tk.Frame(self.notebook, bg="#0a0a1a")
        self.notebook.add(frame, text="  🚀 Nodes  ")
        
        # ONI Node section
        oni_frame = tk.LabelFrame(frame, text="ONI P2P Node", font=("Courier New", 11, "bold"),
                                 bg="#1a1a3a", fg="#00ffcc", padx=15, pady=15,
                                 bd=1, relief=tk.RAISED)
        oni_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(oni_frame, text="Status:", bg="#1a1a3a", fg="#8888aa").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.oni_status_label = tk.Label(oni_frame, text="● Stopped", fg="#ff4444", bg="#1a1a3a",
                                        font=("Courier New", 10, "bold"))
        self.oni_status_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        tk.Label(oni_frame, text="Port:", bg="#1a1a3a", fg="#8888aa").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.oni_port_entry = tk.Entry(oni_frame, width=10, bg="#0a0a1a", fg="#00ffcc",
                                      insertbackground="#00ff88")
        self.oni_port_entry.insert(0, str(self.manager.config.get("oni_node_port", ONI_P2P_PORT)))
        self.oni_port_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        btn_row = tk.Frame(oni_frame, bg="#1a1a3a")
        btn_row.grid(row=2, column=0, columnspan=2, pady=10)
        self.oni_start_btn = tk.Button(btn_row, text="▶ Start Node", font=("Courier New", 10),
                                      bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                                      command=self.start_oni_node, cursor="hand2")
        self.oni_start_btn.pack(side=tk.LEFT, padx=5)
        self.oni_stop_btn = tk.Button(btn_row, text="■ Stop Node", font=("Courier New", 10),
                                     bg="#330000", fg="#ff4444", relief=tk.FLAT,
                                     command=self.stop_oni_node, cursor="hand2")
        self.oni_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # ONS Server section
        ons_frame = tk.LabelFrame(frame, text="ONS DNS Server", font=("Courier New", 11, "bold"),
                                 bg="#1a1a3a", fg="#00ffcc", padx=15, pady=15,
                                 bd=1, relief=tk.RAISED)
        ons_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(ons_frame, text="Status:", bg="#1a1a3a", fg="#8888aa").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ons_status_label = tk.Label(ons_frame, text="● Stopped", fg="#ff4444", bg="#1a1a3a",
                                        font=("Courier New", 10, "bold"))
        self.ons_status_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        tk.Label(ons_frame, text="Port:", bg="#1a1a3a", fg="#8888aa").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.ons_port_entry = tk.Entry(ons_frame, width=10, bg="#0a0a1a", fg="#00ffcc",
                                      insertbackground="#00ff88")
        self.ons_port_entry.insert(0, str(self.manager.config.get("ons_port", ONS_PORT)))
        self.ons_port_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        btn_row2 = tk.Frame(ons_frame, bg="#1a1a3a")
        btn_row2.grid(row=2, column=0, columnspan=2, pady=10)
        self.ons_start_btn = tk.Button(btn_row2, text="▶ Start ONS", font=("Courier New", 10),
                                      bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                                      command=self.start_ons_server, cursor="hand2")
        self.ons_start_btn.pack(side=tk.LEFT, padx=5)
        self.ons_stop_btn = tk.Button(btn_row2, text="■ Stop ONS", font=("Courier New", 10),
                                     bg="#330000", fg="#ff4444", relief=tk.FLAT,
                                     command=self.stop_ons_server, cursor="hand2")
        self.ons_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Registrar section
        reg_frame = tk.LabelFrame(frame, text="Domain Registrar", font=("Courier New", 11, "bold"),
                                 bg="#1a1a3a", fg="#00ffcc", padx=15, pady=15,
                                 bd=1, relief=tk.RAISED)
        reg_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(reg_frame, text="Status:", bg="#1a1a3a", fg="#8888aa").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.reg_status_label = tk.Label(reg_frame, text="● Stopped", fg="#ff4444", bg="#1a1a3a",
                                        font=("Courier New", 10, "bold"))
        self.reg_status_label.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        tk.Label(reg_frame, text="Port:", bg="#1a1a3a", fg="#8888aa").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.reg_port_entry = tk.Entry(reg_frame, width=10, bg="#0a0a1a", fg="#00ffcc",
                                      insertbackground="#00ff88")
        self.reg_port_entry.insert(0, str(self.manager.config.get("registrar_port", REGISTRAR_PORT)))
        self.reg_port_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        btn_row3 = tk.Frame(reg_frame, bg="#1a1a3a")
        btn_row3.grid(row=2, column=0, columnspan=2, pady=10)
        self.reg_start_btn = tk.Button(btn_row3, text="▶ Start Registrar", font=("Courier New", 10),
                                      bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                                      command=self.start_registrar, cursor="hand2")
        self.reg_start_btn.pack(side=tk.LEFT, padx=5)
        self.reg_stop_btn = tk.Button(btn_row3, text="■ Stop Registrar", font=("Courier New", 10),
                                     bg="#330000", fg="#ff4444", relief=tk.FLAT,
                                     command=self.stop_registrar, cursor="hand2")
        self.reg_stop_btn.pack(side=tk.LEFT, padx=5)
    
    def _create_domains_tab(self):
        """Domain registration and management tab."""
        frame = tk.Frame(self.notebook, bg="#0a0a1a")
        self.notebook.add(frame, text="  🌍 Domains  ")
        
        # Register domain section
        reg_frame = tk.LabelFrame(frame, text="Register a .orb Domain", font=("Courier New", 11, "bold"),
                                 bg="#1a1a3a", fg="#00ffcc", padx=15, pady=15,
                                 bd=1, relief=tk.RAISED)
        reg_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(reg_frame, text="Domain Name:", bg="#1a1a3a", fg="#8888aa").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.domain_name_entry = tk.Entry(reg_frame, width=25, bg="#0a0a1a", fg="#00ffcc",
                                         insertbackground="#00ff88")
        self.domain_name_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        tk.Label(reg_frame, text="TLD:", bg="#1a1a3a", fg="#8888aa").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tld_var = tk.StringVar(value=".orb")
        tlds = [f".{t}" for t in ORB_TLDS]
        self.tld_combo = ttk.Combobox(reg_frame, textvariable=self.tld_var, values=tlds,
                                     width=15, state="readonly")
        self.tld_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        self.register_btn = tk.Button(reg_frame, text="🌐 Register Domain", font=("Courier New", 10),
                                     bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                                     command=self.register_domain, cursor="hand2", padx=15, pady=5)
        self.register_btn.grid(row=2, column=0, columnspan=2, pady=10)
        
        self.domain_result = tk.Label(reg_frame, text="", bg="#1a1a3a", fg="#00ff88",
                                     font=("Courier New", 9))
        self.domain_result.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Domain list
        list_frame = tk.LabelFrame(frame, text="My Registered Domains", font=("Courier New", 11, "bold"),
                                  bg="#1a1a3a", fg="#00ffcc", padx=15, pady=15,
                                  bd=1, relief=tk.RAISED)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        columns = ("domain", "tld", "status", "hosted")
        self.domains_tree = ttk.Treeview(list_frame, columns=columns, show="headings",
                                        height=8)
        self.domains_tree.heading("domain", text="Domain")
        self.domains_tree.heading("tld", text="TLD")
        self.domains_tree.heading("status", text="Status")
        self.domains_tree.heading("hosted", text="Hosted")
        
        self.domains_tree.column("domain", width=200)
        self.domains_tree.column("tld", width=100)
        self.domains_tree.column("status", width=100)
        self.domains_tree.column("hosted", width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.domains_tree.yview)
        self.domains_tree.configure(yscrollcommand=scrollbar.set)
        
        self.domains_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_hosting_tab(self):
        """Website hosting tab."""
        frame = tk.Frame(self.notebook, bg="#0a0a1a")
        self.notebook.add(frame, text="  📂 Hosting  ")
        
        # Host a website
        host_frame = tk.LabelFrame(frame, text="Host a Website on ONI", font=("Courier New", 11, "bold"),
                                  bg="#1a1a3a", fg="#00ffcc", padx=15, pady=15,
                                  bd=1, relief=tk.RAISED)
        host_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(host_frame, text="Domain:", bg="#1a1a3a", fg="#8888aa").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.host_domain_entry = tk.Entry(host_frame, width=30, bg="#0a0a1a", fg="#00ffcc",
                                         insertbackground="#00ff88")
        self.host_domain_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5, padx=5)
        
        tk.Label(host_frame, text="Directory:", bg="#1a1a3a", fg="#8888aa").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.host_dir_entry = tk.Entry(host_frame, width=30, bg="#0a0a1a", fg="#00ffcc",
                                      insertbackground="#00ff88")
        self.host_dir_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        browse_btn = tk.Button(host_frame, text="Browse...", font=("Courier New", 9),
                              bg="#1a1a3a", fg="#00ff88", relief=tk.FLAT,
                              command=self.browse_directory, cursor="hand2")
        browse_btn.grid(row=1, column=2, padx=5)
        
        self.host_btn = tk.Button(host_frame, text="🚀 Host Website", font=("Courier New", 10),
                                 bg="#003366", fg="#00ffcc", relief=tk.FLAT,
                                 command=self.host_website, cursor="hand2", padx=15, pady=5)
        self.host_btn.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.host_result = tk.Label(host_frame, text="", bg="#1a1a3a", fg="#00ff88",
                                   font=("Courier New", 9))
        self.host_result.grid(row=3, column=0, columnspan=3, pady=5)
        
        # Hosted sites list
        sites_frame = tk.LabelFrame(frame, text="Currently Hosted", font=("Courier New", 11, "bold"),
                                   bg="#1a1a3a", fg="#00ffcc", padx=15, pady=15,
                                   bd=1, relief=tk.RAISED)
        sites_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        columns = ("domain", "path", "status", "since")
        self.sites_tree = ttk.Treeview(sites_frame, columns=columns, show="headings", height=8)
        self.sites_tree.heading("domain", text="Domain")
        self.sites_tree.heading("path", text="Directory")
        self.sites_tree.heading("status", text="Status")
        self.sites_tree.heading("since", text="Hosted Since")
        
        self.sites_tree.column("domain", width=200)
        self.sites_tree.column("path", width=250)
        self.sites_tree.column("status", width=100)
        self.sites_tree.column("since", width=150)
        
        scrollbar = ttk.Scrollbar(sites_frame, orient=tk.VERTICAL, command=self.sites_tree.yview)
        self.sites_tree.configure(yscrollcommand=scrollbar.set)
        
        self.sites_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_peers_tab(self):
        """Peers tab."""
        frame = tk.Frame(self.notebook, bg="#0a0a1a")
        self.notebook.add(frame, text="  👥 Peers  ")
        
        peers_frame = tk.Frame(frame, bg="#1a1a3a", padx=15, pady=15)
        peers_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(peers_frame, text="Connected ONI Network Peers", font=("Courier New", 11, "bold"),
                bg="#1a1a3a", fg="#00ffcc").pack(anchor=tk.W, pady=(0, 10))
        
        # Instructions for sync
        info_text = """PEER SYNC INFORMATION:

When two users both have the Orbit Browser and ONI Manager running,
their systems will automatically synchronize if they're on the same network.

How peer sync works:
1. Each ONI node announces itself to the network
2. Nodes share their hosted domains and known peers
3. When User A visits User B's .orb domain, they get the same content
4. The ONS system resolves domains to the correct hosting node

To connect with another ONI user:
• Both must have ONI running (node + ONS)
• Register a domain and host your website
• Share your ONI node address with the other user
• Their browser will resolve your domain and fetch content

Synced data includes:
• Domain registrations (who owns what)
• Website content (hosted sites)
• Peer lists (who's online)
• DNS records (domain resolution)"""

        info_label = tk.Label(peers_frame, text=info_text, font=("Courier New", 9),
                             bg="#1a1a3a", fg="#8888aa", justify=tk.LEFT)
        info_label.pack(fill=tk.BOTH, expand=True)
    
    def _create_logs_tab(self):
        """Logs tab."""
        frame = tk.Frame(self.notebook, bg="#0a0a1a")
        self.notebook.add(frame, text="  📋 Logs  ")
        
        log_frame = tk.Frame(frame, bg="#0a0a1a")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(log_frame, text="ONI Manager Activity Log", font=("Courier New", 11, "bold"),
                bg="#0a0a1a", fg="#00ffcc").pack(anchor=tk.W, pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Courier New", 9),
            bg="#0a0a1a",
            fg="#e0e0ff",
            insertbackground="#00ff88",
            relief=tk.FLAT,
            bd=1,
            height=20,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Log tags
        self.log_text.tag_configure("info", foreground="#e0e0ff")
        self.log_text.tag_configure("success", foreground="#00ff88")
        self.log_text.tag_configure("warning", foreground="#ffaa00")
        self.log_text.tag_configure("error", foreground="#ff4444")
        
        clear_btn = tk.Button(log_frame, text="Clear Log", font=("Courier New", 9),
                             bg="#1a1a3a", fg="#8888aa", relief=tk.FLAT,
                             command=lambda: self.log_text.delete(1.0, tk.END), cursor="hand2")
        clear_btn.pack(anchor=tk.E, pady=5)
        
        self._log("ONI Manager started", "info")
    
    def _log(self, message, tag="info"):
        """Add a log entry."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n", tag)
        self.log_text.see(tk.END)
    
    def _start_status_poller(self):
        """Poll for status updates every 3 seconds."""
        def poll():
            while True:
                try:
                    # Update cards
                    status = self.manager.get_status()
                    for key, label in self.status_cards.items():
                        label.config(text=str(status.get(key.replace("_card", ""), "?")))
                    
                    # Update global status
                    if status.get("oni_node") or status.get("ons_server") or status.get("registrar"):
                        self.global_status.config(text="● RUNNING", fg="#00ff88")
                    else:
                        self.global_status.config(text="● STOPPED", fg="#ff4444")
                    
                    # Update node tab statuses
                    self.oni_status_label.config(
                        text="● Running" if status.get("oni_node") else "● Stopped",
                        fg="#00ff88" if status.get("oni_node") else "#ff4444"
                    )
                    self.ons_status_label.config(
                        text="● Running" if status.get("ons_server") else "● Stopped",
                        fg="#00ff88" if status.get("ons_server") else "#ff4444"
                    )
                    self.reg_status_label.config(
                        text="● Running" if status.get("registrar") else "● Stopped",
                        fg="#00ff88" if status.get("registrar") else "#ff4444"
                    )
                    
                    time.sleep(3)
                except:
                    time.sleep(3)
        
        thread = threading.Thread(target=poll, daemon=True)
        thread.start()
    
    # --- Action Handlers ---
    
    def start_all(self):
        """Start all nodes."""
        result = []
        r1, m1 = self.manager.start_oni_node()
        result.append(m1)
        if r1: self._log(m1, "success")
        else: self._log(m1, "warning")
        
        r2, m2 = self.manager.start_ons_server()
        result.append(m2)
        if r2: self._log(m2, "success")
        else: self._log(m2, "warning")
        
        r3, m3 = self.manager.start_registrar()
        result.append(m3)
        if r3: self._log(m3, "success")
        else: self._log(m3, "warning")
        
        messagebox.showinfo("Start All", "\n".join(result))
    
    def stop_all(self):
        """Stop all nodes."""
        self.manager.stop_oni_node()
        self._log("ONI node stopped", "info")
        self.manager.stop_ons_server()
        self._log("ONS server stopped", "info")
        self.manager.stop_registrar()
        self._log("Registrar stopped", "info")
        messagebox.showinfo("Stop All", "All nodes stopped")
    
    def start_oni_node(self):
        port = self.oni_port_entry.get()
        try:
            port = int(port)
        except:
            port = ONI_P2P_PORT
        r, m = self.manager.start_oni_node(port=port)
        self._log(m, "success" if r else "warning")
        if not r:
            messagebox.showwarning("ONI Node", m)
    
    def stop_oni_node(self):
        r, m = self.manager.stop_oni_node()
        self._log(m, "info")
    
    def start_ons_server(self):
        port = self.ons_port_entry.get()
        try:
            port = int(port)
        except:
            port = ONS_PORT
        r, m = self.manager.start_ons_server(port=port)
        self._log(m, "success" if r else "warning")
    
    def stop_ons_server(self):
        r, m = self.manager.stop_ons_server()
        self._log(m, "info")
    
    def start_registrar(self):
        port = self.reg_port_entry.get()
        try:
            port = int(port)
        except:
            port = REGISTRAR_PORT
        r, m = self.manager.start_registrar(port=port)
        self._log(m, "success" if r else "warning")
    
    def stop_registrar(self):
        r, m = self.manager.stop_registrar()
        self._log(m, "info")
    
    def doSync(self):
        self._log("Starting network sync...", "info")
        r, m = self.manager.sync_with_network()
        self._log(m, "success" if r else "warning")
    
    def register_domain(self):
        domain = self.domain_name_entry.get().strip()
        tld = self.tld_var.get().lstrip(".")
        if not domain:
            messagebox.showwarning("Register Domain", "Please enter a domain name")
            return
        
        r, m = self.manager.register_domain(domain, tld)
        self._log(m, "success" if r else "warning")
        self.domain_result.config(text=m)
        
        if r:
            self.domains_tree.insert("", tk.END, values=(f"{domain}.{tld}", f".{tld}", "Active", "No"))
    
    def browse_directory(self):
        directory = filedialog.askdirectory(title="Select website directory")
        if directory:
            self.host_dir_entry.delete(0, tk.END)
            self.host_dir_entry.insert(0, directory)
    
    def host_website(self):
        domain = self.host_domain_entry.get().strip()
        directory = self.host_dir_entry.get().strip()
        
        if not domain or not directory:
            messagebox.showwarning("Host Website", "Please enter both domain and directory")
            return
        
        r, m = self.manager.host_website(domain, directory)
        self._log(m, "success" if r else "warning")
        self.host_result.config(text=m)
        
        if r:
            self.sites_tree.insert("", tk.END, values=(domain, directory, "Active", time.strftime("%Y-%m-%d %H:%M")))
    
    def host_website_dialog(self):
        """Open the hosting tab from dashboard button."""
        self.notebook.select(3)  # Hosting tab index
    
    def show_settings(self):
        """Show settings dialog."""
        settings_win = tk.Toplevel(self.root)
        settings_win.title("ONI Manager Settings")
        settings_win.geometry("400x300")
        settings_win.configure(bg="#0a0a1a")
        
        frame = tk.Frame(settings_win, bg="#1a1a3a", padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(frame, text="Settings", font=("Courier New", 14, "bold"),
                bg="#1a1a3a", fg="#00ffcc").pack(anchor=tk.W, pady=(0, 15))
        
        # Auto-start
        self.auto_var = tk.BooleanVar(value=self.manager.config.get("auto_start_nodes", False))
        tk.Checkbutton(frame, text="Auto-start nodes on launch", variable=self.auto_var,
                      bg="#1a1a3a", fg="#e0e0ff", selectcolor="#0a0a1a",
                      command=self._save_settings).pack(anchor=tk.W, pady=5)
        
        # Sync enabled
        self.sync_var = tk.BooleanVar(value=self.manager.config.get("sync_enabled", True))
        tk.Checkbutton(frame, text="Enable network sync", variable=self.sync_var,
                      bg="#1a1a3a", fg="#e0e0ff", selectcolor="#0a0a1a",
                      command=self._save_settings).pack(anchor=tk.W, pady=5)
        
        tk.Label(frame, text=f"Data directory:", bg="#1a1a3a", fg="#8888aa",
                font=("Courier New", 9)).pack(anchor=tk.W, pady=(15, 5))
        tk.Label(frame, text=str(self.manager.data_dir), bg="#1a1a3a", fg="#555",
                font=("Courier New", 8)).pack(anchor=tk.W)
        
        tk.Label(frame, text=f"Node port: {self.manager.config.get('oni_node_port', ONI_P2P_PORT)}",
                bg="#1a1a3a", fg="#8888aa", font=("Courier New", 9)).pack(anchor=tk.W, pady=2)
        tk.Label(frame, text=f"ONS port: {self.manager.config.get('ons_port', ONS_PORT)}",
                bg="#1a1a3a", fg="#8888aa", font=("Courier New", 9)).pack(anchor=tk.W, pady=2)
        tk.Label(frame, text=f"Registrar port: {self.manager.config.get('registrar_port', REGISTRAR_PORT)}",
                bg="#1a1a3a", fg="#8888aa", font=("Courier New", 9)).pack(anchor=tk.W, pady=2)
    
    def _save_settings(self):
        """Save settings from dialog."""
        self.manager.config["auto_start_nodes"] = self.auto_var.get()
        self.manager.config["sync_enabled"] = self.sync_var.get()
        self.manager.sync_enabled = self.sync_var.get()
        self.manager._save_config()
        self._log("Settings saved", "info")
    
    def show_about(self):
        messagebox.showinfo("About ONI Manager",
                           "ONI Manager v1.0\n"
                           "Orbital Network Infrastructure\n\n"
                           "The People's Internet\n"
                           "Decentralized P2P Web\n\n"
                           "© 2026 Technic_ Dev")
    
    def open_devkit(self):
        """Open the ONI DevKit in browser."""
        import webbrowser
        devkit_path = ONI_ROOT / "ONI_DevKit" / "index.html"
        if devkit_path.exists():
            webbrowser.open(f"file://{devkit_path}")
        else:
            messagebox.showinfo("DevKit", "ONI DevKit not found. Run the installer first.")
    
    def run(self):
        """Run the GUI main loop."""
        self.root.mainloop()


def main():
    # Create manager
    data_dir = ONI_ROOT / "data"
    manager = ONIManager(data_dir)
    
    # Create and run GUI
    gui = ONIManagerGUI(manager)
    
    # Auto-start if configured
    if manager.config.get("auto_start_nodes"):
        manager.start_oni_node()
        manager.start_ons_server()
        manager.start_registrar()
    
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        manager.cleanup()


if __name__ == "__main__":
    main()