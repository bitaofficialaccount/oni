%global __python3 /usr/bin/python3

Name:           oni
Version:        1.0.0
Release:        1%{?dist}
Summary:        ONI - Orbit Browser & ONI Manager (Decentralized Web)

License:        MIT
URL:            https://github.com/bitaofficialaccount/oni
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools

Requires:       python3 >= 3.8
Requires:       python3-tkinter
Requires:       python3-websockets
Requires:       python3-flask
Requires:       python3-requests
Requires:       python3-aiohttp

%description
ONI (Orbital Network Infrastructure) is a decentralized peer-to-peer web
network that replaces traditional web infrastructure.

This package installs the core desktop applications:
- Orbit Browser: Desktop browser for orb:// protocol and .orb domains
- ONI Manager: Desktop GUI for managing nodes, domains, and hosting
- P2P Node & ONS Server: Networking layer (auto-starts in background)

Browse .orb websites, register free domains, host your own sites.
The People's Internet — Decentralized, Free, Open Source.

%package        dev
Summary:        ONI Developer Kit - Documentation, Docker, Dev Tools
Requires:       %{name} = %{version}-%{release}
Requires:       python3
Requires:       python3-tkinter

%description    dev
ONI developer package for building and hosting .orb websites.

Includes everything in 'oni' plus:
- ONI DevKit: Complete developer documentation (HTML)
- Docker support: Dockerfile + docker-compose.yml for self-hosting
- Domain linking tools: Link multiple .orb domains to one site
- ONI Registrar: Free .orb domain registration web app
- Example sites: Hello World & Blog .orb website templates
- API reference: REST endpoints for ONS, Nodes, and Registrar

For developers who want to build on the ONI decentralized web.

%prep
%setup -q

%build
# No build required - pure Python application

%install
# Create directory structure
install -d %{buildroot}%{_datadir}/oni/{apps,p2p,ons,data}
install -d %{buildroot}%{_datadir}/applications
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_mandir}/man1

# Core files
install -m 755 apps/orbit_browser_app.py %{buildroot}%{_datadir}/oni/apps/
install -m 755 apps/oni_manager.py %{buildroot}%{_datadir}/oni/apps/
install -m 644 p2p/oni_node.py %{buildroot}%{_datadir}/oni/p2p/
install -m 644 p2p/peer.py %{buildroot}%{_datadir}/oni/p2p/
install -m 644 p2p/protocol.py %{buildroot}%{_datadir}/oni/p2p/
install -m 644 ons/resolver.py %{buildroot}%{_datadir}/oni/ons/
install -m 644 ons/registry.py %{buildroot}%{_datadir}/oni/ons/
install -m 755 start_oni.py %{buildroot}%{_datadir}/oni/
install -m 644 supabase_client.py %{buildroot}%{_datadir}/oni/
install -m 644 supabase_schema.sql %{buildroot}%{_datadir}/oni/
install -m 644 .env.example %{buildroot}%{_datadir}/oni/
install -m 644 LICENSE %{buildroot}%{_datadir}/oni/
install -m 644 README.md %{buildroot}%{_datadir}/oni/

# Desktop entries
cat > %{buildroot}%{_datadir}/applications/orbit-browser.desktop << DESKTOP_EOF
[Desktop Entry]
Name=Orbit Browser
Comment=Browse the ONI decentralized web
Exec=python3 %{_datadir}/oni/apps/orbit_browser_app.py
Icon=orbit-browser
Terminal=false
Type=Application
Categories=Network;WebBrowser;
Keywords=oni;orbit;browser;web;decentralized;
StartupWMClass=OrbitBrowser
DESKTOP_EOF

cat > %{buildroot}%{_datadir}/applications/oni-manager.desktop << DESKTOP_EOF
[Desktop Entry]
Name=ONI Manager
Comment=Manage your ONI network nodes and domains
Exec=python3 %{_datadir}/oni/apps/oni_manager.py
Icon=oni-manager
Terminal=false
Type=Application
Categories=Network;Utility;
Keywords=oni;orbit;network;p2p;decentralized;
StartupWMClass=ONIManager
DESKTOP_EOF

# CLI command
cat > %{buildroot}%{_bindir}/oni << CLI_EOF
#!/bin/bash
ONI_DIR="%{_datadir}/oni"
PYTHON=\$(command -v python3 || command -v python)
case "\$1" in
    start)       shift; \$PYTHON "\$ONI_DIR/start_oni.py" "\$@" ;;
    node)        shift; \$PYTHON "\$ONI_DIR/p2p/oni_node.py" "\$@" ;;
    ons)         shift; \$PYTHON "\$ONI_DIR/ons/ons_server.py" "\$@" ;;
    registrar)   shift; \$PYTHON "\$ONI_DIR/orbit-registrar/registrar.py" "\$@" ;;
    browser)     shift; \$PYTHON "\$ONI_DIR/apps/orbit_browser_app.py" "\$@" ;;
    manager)     shift; \$PYTHON "\$ONI_DIR/apps/oni_manager.py" "\$@" ;;
    devkit)      cd "\$ONI_DIR/ONI_DevKit" && \$PYTHON -m http.server 9091 --bind 127.0.0.1 ;;
    help|--help|-h)
        echo "ONI - Orbital Network Infrastructure"
        echo "Usage: oni <command>"
        echo "Commands: start|node|ons|registrar|browser|manager|devkit" ;;
    *)           echo "Usage: oni <command> (start|node|ons|registrar|browser|manager|devkit)" ;;
esac
CLI_EOF
chmod 755 %{buildroot}%{_bindir}/oni

# Man page
cat > %{buildroot}%{_mandir}/man1/oni.1 << MAN_EOF
.TH ONI 1 "June 2026" "oni v1.0.0" "User Commands"
.SH NAME
oni \- Orbital Network Infrastructure command-line tool
.SH SYNOPSIS
.B oni
[\fICOMMAND\fR] [\fIOPTIONS\fR]
.SH DESCRIPTION
ONI (Orbital Network Infrastructure) is a decentralized peer-to-peer web network.
.SH COMMANDS
.TP
.B start
Start all ONI components (P2P node, ONS, Registrar)
.TP
.B node
Start an ONI P2P network node
.TP
.B ons
Start the ONS (Orbit Name Server) DNS server
.TP
.B registrar
Start the domain registration web app
.TP
.B browser
Launch the Orbit Browser desktop application
.TP
.B manager
Launch the ONI Manager desktop application
.TP
.B devkit
Open the ONI Developer Kit documentation
.SH FILES
.TP
.I /usr/share/oni/
ONI installation directory
.SH AUTHOR
Technic_ Dev
.SH COPYRIGHT
Copyright (C) 2026 Technic_ Dev. MIT License.
.SH SEE ALSO
.BR python3 (1), docker (1)
MAN_EOF

# DevKit files (oni-dev subpackage)
%if "%{name}" == "oni-dev" || 0%{?rhel} || 0%{?fedora}
install -d %{buildroot}%{_datadir}/oni/ONI_DevKit
install -d %{buildroot}%{_datadir}/oni/examples/helloworld.orb
install -d %{buildroot}%{_datadir}/oni/examples/myblog.orb
install -d %{buildroot}%{_datadir}/oni/orbit-registrar/templates
install -d %{buildroot}%{_datadir}/oni/orbit-registrar/static
install -d %{buildroot}%{_datadir}/oni/ons

install -m 644 ONI_DevKit/index.html %{buildroot}%{_datadir}/oni/ONI_DevKit/
install -m 644 examples/helloworld.orb/index.html %{buildroot}%{_datadir}/oni/examples/helloworld.orb/
install -m 644 examples/myblog.orb/index.html %{buildroot}%{_datadir}/oni/examples/myblog.orb/
install -m 644 Dockerfile %{buildroot}%{_datadir}/oni/
install -m 644 docker-compose.yml %{buildroot}%{_datadir}/oni/
install -m 755 install.sh %{buildroot}%{_datadir}/oni/
install -m 644 ons/ons_server.py %{buildroot}%{_datadir}/oni/ons/
install -m 755 orbit-registrar/registrar.py %{buildroot}%{_datadir}/oni/orbit-registrar/
install -m 644 orbit-registrar/templates/*.html %{buildroot}%{_datadir}/oni/orbit-registrar/templates/
install -m 644 orbit-registrar/static/style.css %{buildroot}%{_datadir}/oni/orbit-registrar/static/
%endif

%files
%license LICENSE
%doc README.md
%{_datadir}/oni/apps/orbit_browser_app.py
%{_datadir}/oni/apps/oni_manager.py
%{_datadir}/oni/p2p/oni_node.py
%{_datadir}/oni/p2p/peer.py
%{_datadir}/oni/p2p/protocol.py
%{_datadir}/oni/ons/resolver.py
%{_datadir}/oni/ons/registry.py
%{_datadir}/oni/start_oni.py
%{_datadir}/oni/supabase_client.py
%{_datadir}/oni/supabase_schema.sql
%{_datadir}/oni/.env.example
%{_datadir}/oni/LICENSE
%{_datadir}/oni/README.md
%{_datadir}/applications/orbit-browser.desktop
%{_datadir}/applications/oni-manager.desktop
%{_bindir}/oni
%{_mandir}/man1/oni.1*

%files dev
%license LICENSE
%{_datadir}/oni/ONI_DevKit/
%{_datadir}/oni/Dockerfile
%{_datadir}/oni/docker-compose.yml
%{_datadir}/oni/install.sh
%{_datadir}/oni/ons/ons_server.py
%{_datadir}/oni/orbit-registrar/
%{_datadir}/oni/examples/

%changelog
* Thu Jun 04 2026 Technic_ Dev <bitaofficialaccount@users.noreply.github.com> - 1.0.0-1
- Initial release of ONI - Orbital Network Infrastructure
- Two desktop apps: ONI Manager and Orbit Browser
- Auto-starts P2P nodes when browser opens
- Uses Supabase cloud backbone for universal access
- Free .orb domain registration and hosting
- Docker self-hosting support
- ONI DevKit developer documentation