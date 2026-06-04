#!/usr/bin/env python3
# Orbit Domain Registrar - Free .orb Domain Registration
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure

import sys
import os
import json
import time
import hashlib
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from p2p.protocol import *
from ons.registry import DomainRegistry
from supabase_client import (
    register_domain as sb_register_domain,
    get_domain as sb_get_domain,
    list_domains as sb_list_domains,
    get_statistics as sb_get_statistics,
    search_domains as sb_search_domains,
    SUPABASE_AVAILABLE,
)

try:
    from flask import Flask, render_template, request, jsonify, redirect, url_for, session
except ImportError:
    print("ERROR: Flask not found. Install with: pip3 install flask")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ONI.Registrar")

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# Will be set at startup
local_registry = None


def generate_owner_key():
    """Generate a unique owner key for domain ownership."""
    return hashlib.sha256(f"{time.time()}{os.urandom(32)}".encode()).hexdigest()


# ---- Supabase-fallback helpers ----

def _get_stats():
    if SUPABASE_AVAILABLE:
        return sb_get_statistics()
    return local_registry.get_statistics() if local_registry else {"total_domains": 0, "active_domains": 0, "tld_distribution": {}}

def _list_domains():
    if SUPABASE_AVAILABLE:
        domains_list = sb_list_domains()
        # Convert to dict format for templates
        domains_dict = {}
        for d in domains_list:
            domain_name = d.get("domain", "")
            domains_dict[domain_name] = {
                "owner": d.get("owner", "Unknown"),
                "tld": d.get("tld", "orb"),
                "status": d.get("status", "active"),
            }
        return domains_dict
    return local_registry.list_domains() if local_registry else {}

def _get_domain(domain):
    if SUPABASE_AVAILABLE:
        return sb_get_domain(domain)
    return local_registry.get_domain(domain) if local_registry else None

def _register_domain(domain, name, owner, owner_key, tld="orb", records=None):
    if SUPABASE_AVAILABLE:
        return sb_register_domain(domain, name, tld, owner, owner_key, records)
    return local_registry.register_domain(domain, owner, owner_key, tld, records)


@app.route("/")
def index():
    """Registrar home page."""
    stats = _get_stats()
    domains = _list_domains()
    
    return render_template("index.html",
        stats=stats,
        domains=list(domains.items())[:30],
        orb_tlds=ORB_TLDS,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new .orb domain."""
    if request.method == "POST":
        domain_name = request.form.get("domain_name", "").strip().lower()
        tld = request.form.get("tld", "orb").strip().lower()
        owner = request.form.get("owner", "").strip()
        
        # Validate domain name
        if not domain_name or not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', domain_name):
            return render_template("register.html", 
                error="Invalid domain name. Use only letters, numbers, and hyphens.",
                orb_tlds=ORB_TLDS)
        
        # Construct full domain
        if tld == "orb":
            full_domain = f"{domain_name}.orb"
        else:
            full_domain = f"{domain_name}.{tld}"
        
        if not validate_domain(full_domain):
            return render_template("register.html",
                error="Invalid domain format.",
                orb_tlds=ORB_TLDS)
        
        # Check if domain is available
        existing = _get_domain(full_domain)
        if existing:
            return render_template("register.html",
                error=f"Sorry, {full_domain} is already registered.",
                orb_tlds=ORB_TLDS)
        
        # Register the domain
        owner_key = generate_owner_key()
        # Extract name from full domain
        name_part = domain_name
        success, message = _register_domain(
            full_domain, name_part, owner or "Anonymous", owner_key, tld=tld
        )
        # _register_domain returns (success, message, owner_key) from Supabase
        # or (success, message) from local. Handle both.
        if isinstance(message, tuple):
            success, message, owner_key = message
        
        if success:
            # Store owner key in session
            session[f"key_{full_domain}"] = owner_key
            return render_template("success.html",
                domain=full_domain,
                owner_key=owner_key,
                tld=tld)
        else:
            return render_template("register.html",
                error=message,
                orb_tlds=ORB_TLDS)
    
    return render_template("register.html", orb_tlds=ORB_TLDS)


@app.route("/manage", methods=["GET", "POST"])
def manage():
    """Manage a registered domain."""
    domain_info = None
    message = None
    
    if request.method == "POST":
        domain = request.form.get("domain", "").strip().lower()
        owner_key = request.form.get("owner_key", "").strip()
        
        info = _get_domain(domain)
        if info and info.get("owner_key") == owner_key:
            registered_ts = info.get("registered_at") or info.get("registered") or 0
            if isinstance(registered_ts, str):
                from datetime import datetime
                try:
                    registered_ts = datetime.fromisoformat(registered_ts.replace('Z', '+00:00')).timestamp()
                except:
                    registered_ts = 0
            
            domain_info = {
                "domain": domain,
                "owner": info.get("owner"),
                "tld": info.get("tld"),
                "registered": time.ctime(registered_ts if isinstance(registered_ts, (int, float)) else 0),
                "status": info.get("status"),
                "records": info.get("records", {}),
                "owner_key": owner_key,
            }
        else:
            message = "Invalid domain or owner key"
    
    return render_template("manage.html", domain=domain_info, message=message)


@app.route("/api/register", methods=["POST"])
def api_register():
    """API endpoint for domain registration."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    domain_name = data.get("domain", "").strip().lower()
    tld = data.get("tld", "orb").strip().lower()
    owner = data.get("owner", "").strip()
    
    if tld == "orb":
        full_domain = f"{domain_name}.orb"
    else:
        full_domain = f"{domain_name}.{tld}"
    
    if not validate_domain(full_domain):
        return jsonify({"error": "Invalid domain"}), 400
    
    existing = _get_domain(full_domain)
    if existing:
        return jsonify({"error": "Domain already registered"}), 409
    
    owner_key = generate_owner_key()
    result = _register_domain(full_domain, domain_name, owner or "Anonymous", owner_key, tld=tld)
    
    # Handle both Supabase (3-tuple) and local (2-tuple) return formats
    if isinstance(result, tuple) and len(result) >= 2:
        success = result[0]
        message = result[1]
        if len(result) >= 3 and result[2]:
            owner_key = result[2]
    else:
        success, message = result
    
    if success:
        return jsonify({
            "success": True,
            "domain": full_domain,
            "owner_key": owner_key,
            "message": "Domain registered successfully"
        })
    
    return jsonify({"error": message}), 400


@app.route("/api/resolve/<path:domain>")
def api_resolve(domain):
    """API endpoint for domain resolution."""
    if not domain.endswith(".orb"):
        domain = domain + ".orb"
    
    # Resolve via Supabase first, fallback to local
    if SUPABASE_AVAILABLE:
        from supabase_client import resolve_domain as sb_resolve
        records = sb_resolve(domain)
    else:
        records = local_registry.resolve_domain(domain) if local_registry else None
    
    if records:
        return jsonify({"domain": domain, "found": True, "records": records})
    return jsonify({"domain": domain, "found": False}), 404


@app.route("/list")
def list_domains():
    """List all registered domains."""
    domains = _list_domains()
    return render_template("list.html", domains=domains, orb_tlds=ORB_TLDS)


def main():
    global local_registry
    
    parser = argparse.ArgumentParser(description="Orbit Domain Registrar")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=REGISTRAR_PORT, help="Port to listen on")
    parser.add_argument("--data-dir", help="Data directory for registry")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    local_registry = DomainRegistry(args.data_dir)
    stats = _get_stats()
    backend = "Supabase" if SUPABASE_AVAILABLE else "Local File"
    
    print(f"""
 ╔══════════════════════════════════════════╗
 ║    Orbit Domain Registrar Active         ║
 ║    Free .orb Domain Registration          ║
 ╚══════════════════════════════════════════╝
    Address:  http://{args.host}:{args.port}
    Backend:  {backend}
    Domains:  {stats['total_domains']} registered
    TLDs:     {', '.join(f'.orb' + (f'.{t}' if t != 'orb' else '') for t in ORB_TLDS[:5])}...
    Status:   Ready for registrations
    © 2026 Technic_ Dev
""")
    
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    import re
    main()
