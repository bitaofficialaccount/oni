# 🌐 ONI - Orbital Network Infrastructure

**The Future of Decentralized Web — The People's Internet**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![One-Click Install](https://img.shields.io/badge/install-one--click-brightgreen)](install.sh)

ONI (Orbital Network Infrastructure) is a revolutionary peer-to-peer internet network that replaces traditional web infrastructure with a fully decentralized, open-source alternative. Powered by WebRTC, WebSockets, and P2P technology.

```
  ___  _   _ ___ 
 / _ \| \ | |_ _|
| | | |  \| || | 
| |_| | |\  || | 
 \___/|_| \_|___|
                  
Orbital Network Infrastructure v1.0
```

## 🚀 One-Click Install

```bash
curl -fsSL https://raw.githubusercontent.com/bitaofficialaccount/oni/main/install.sh | bash
```

This will install everything you need:
- **ONI Manager** — Desktop app for managing your network
- **Orbit Browser** — Desktop app for browsing the ONI network
- **ONI DevKit** — Complete developer documentation
- **Docker support** — docker-compose.yml for self-hosting
- **Desktop entries** — Apps appear in your system menu (Linux)

---

## 🖥️ Two Desktop Apps

### 🚀 **ONI Manager**
The central control panel for your ONI network. Start/stop nodes, register domains, host websites.

```bash
oni manager
```
- Dashboard with real-time status
- Start/stop ONI nodes, ONS server, and Registrar
- Register .orb domains (FREE!)
- Host websites from any directory
- View connected peers and sync status
- Activity log

### 🌐 **Orbit Browser**
The desktop browser for the ONI decentralized web.

```bash
oni browser
```
- Browse `orb://` websites on the ONI network
- Bookmarks and history management
- Sync bookmarks across devices
- Dark theme
- Keyboard shortcuts

---

## 🚦 Quick Start

### 1. Install ONI
```bash
curl -fsSL https://raw.githubusercontent.com/bitaofficialaccount/oni/main/install.sh | bash
```

### 2. Start the ONI Manager
```bash
oni manager
```
Click **▶ Start All** to launch all network components.

### 3. Register a Domain
Go to the **Domains** tab, enter a name (e.g., `mysite`), and pick a TLD.

### 4. Host a Website
Go to the **Hosting** tab, enter your domain, browse to your HTML directory, click **Host Website**.

### 5. Browse
Open the **Orbit Browser** and navigate to `orb://mysite.orb`

---

## 🔄 Sync Between Users

When two users both have ONI running, they automatically share:

- **Domain registrations** — Who owns which .orb domains
- **Website content** — Hosted sites are accessible to all users
- **Peer lists** — Who's currently online
- **Bookmarks/History** — Manually sync via Tools → Sync with Device

Users see the **same websites** and **same content** — just like a decentralized internet should work.

---

## 🐳 Docker Self-Hosting

For always-on hosting, run ONI with Docker:

```bash
# Install Docker (if not installed)
curl -fsSL https://get.docker.com | sh

# Clone and run
git clone https://github.com/bitaofficialaccount/oni.git /opt/oni
cd /opt/oni
docker-compose up -d
```

See the [ONI DevKit](ONI_DevKit/index.html) for complete Docker deployment guide.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Apps Layer                                │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  ONI Manager     │  │  Orbit Browser   │                  │
│  │  (Desktop App)   │  │  (Desktop App)   │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
└───────────┼──────────────────────┼──────────────────────────┘
            │                      │
┌───────────▼──────────────────────▼──────────────────────────┐
│                    Network Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ ONI Node │  │ ONS      │  │ Registrar│  │ P2P Sync │   │
│  │ (WebSock)│  │ Server   │  │ (Flask)  │  │ Engine   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    ONI P2P Network                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Peer 1   │↔│ Peer 2   │↔│ Peer 3   │↔│ Peer N   │   │
│  │ (Node)   │  │ (Node)   │  │ (Node)   │  │ (Node)   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 🌍 .orb Domains

| TLD | Purpose | Example |
|-----|---------|---------|
| `.orb` | Generic domains | `mysite.orb` |
| `.orb.be` | Belgium | `mijnsite.orb.be` |
| `.orb.uk` | United Kingdom | `mysite.orb.uk` |
| `.orb.org` | Organizations | `myorg.orb.org` |
| `.orb.fun` | Fun/personal | `myproject.orb.fun` |
| `.orb.dev` | Developers | `myapp.orb.dev` |
| `.orb.io` | Tech/Startups | `mystartup.orb.io` |
| `.orb.*` | Custom TLDs | `anything.orb.yourname` |

**All domains are FREE — no registration costs, no renewal fees.**

### 🔗 Domain Linking
Point multiple .orb domains to the same website content:
```bash
curl -X POST http://127.0.0.1:5353/link \
  -d '{"domain": "mysite.orb.dev", "target": "mysite.orb"}'
```

## 📁 Project Structure

```
ONI/
├── install.sh                  # One-click GitHub installer
├── Dockerfile                  # Docker image build
├── docker-compose.yml          # Multi-service Docker deployment
├── .gitignore                  # Git ignore rules
├── LICENSE                     # MIT License
├── README.md                   # This file
│
├── apps/                       # 📱 Desktop Applications
│   ├── oni_manager.py          # ONI Manager (node/domain management GUI)
│   └── orbit_browser_app.py    # Orbit Browser (standalone browser GUI)
│
├── ONI_DevKit/                 # 📖 Developer Documentation
│   └── index.html              # Complete developer guide
│
├── p2p/                        # 🔗 P2P Network Layer
│   ├── oni_node.py             # ONI network node
│   ├── peer.py                 # Peer management
│   └── protocol.py             # Network protocol definitions
│
├── ons/                        # 🧭 Orbit Name Servers
│   ├── ons_server.py           # ONS server
│   ├── resolver.py             # Domain resolver
│   └── registry.py             # Domain registry database
│
├── orbit-registrar/            # 📋 Domain Registration
│   ├── registrar.py            # Registrar web app
│   ├── templates/              # HTML templates
│   └── static/                 # CSS/JS assets
│
├── orbit-browser/              # 🌐 Legacy Orbit Browser
│   ├── orbit_browser.py        # Original browser (CLI + tkinter)
│   └── assets/                 # Browser assets
│
├── start_oni.py                # 🚀 Launcher for all components
├── supabase_client.py          # Supabase database client
├── supabase_schema.sql         # Database schema
│
├── data/                       # 📦 Runtime data (gitignored)
│   ├── cache/                  # Browser cache
│   ├── domains/                # Domain data
│   ├── peers/                  # Peer data
│   └── logs/                   # Activity logs
│
└── examples/                   # 📚 Example .orb websites
    ├── helloworld.orb/         # Hello World example
    ├── myblog.orb/             # Blog example
    └── docs/                   # Documentation site
```

## 📦 Included Components

| Component | Type | Description | How to Run |
|-----------|------|-------------|------------|
| 🚀 **ONI Manager** | Desktop App | Network management GUI | `oni manager` |
| 🌐 **Orbit Browser** | Desktop App | ONI network browser | `oni browser` |
| 📖 **ONI DevKit** | Documentation | Developer guide | `oni devkit` |
| 🔗 **ONI P2P Node** | Service | P2P networking | `oni node` |
| 🧭 **ONS Server** | Service | Domain resolution | `oni ons` |
| 📋 **Registrar** | Web App | Domain registration | `oni registrar` |
| 🐳 **Docker** | Deployment | Self-hosting | `docker-compose up -d` |

## 🔧 Requirements

- **Python 3.8+** (for desktop apps)
- **Docker** (optional, for self-hosting)
- **tkinter** (for GUI apps, install: `sudo apt install python3-tk`)
- Modern terminal/display

## 📡 CLI Commands

```bash
oni start       # Start all ONI components
oni node        # Start an ONI P2P node
oni ons         # Start the ONS server
oni registrar   # Start the domain registrar
oni browser     # Launch the Orbit Browser
oni manager     # Launch the ONI Manager
oni devkit      # Open the ONI Developer Kit
```

## 🛠️ Technical Details

### Network Protocol
- **Discovery**: Kademlia DHT for peer discovery
- **Transport**: WebSocket for P2P communication
- **Routing**: Content-addressed routing via distributed hash tables
- **Security**: Ed25519 cryptographic signatures
- **Sync**: Automatic peer-to-peer content synchronization

### ONS Protocol
- **Resolution**: Distributed DNS via DHT
- **Storage**: Replicated across multiple nodes
- **Caching**: TTL-based caching for performance
- **Domain Linking**: CNAME-like domain aliasing

## 📜 License

Copyright © 2026 Technic_ Dev. All rights reserved.

ONI is open source software. See `LICENSE` for details.

---

<p align="center">
  <strong>🌐 ONI: The People's Internet</strong><br>
  Decentralized • Free • Open Source
</p>