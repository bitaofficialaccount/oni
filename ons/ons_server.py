#!/usr/bin/env python3
# ONS - Orbit Name Servers (DNS for .orb domains)
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure
#
# Now powered by Supabase database backend!

import sys
import os
import json
import time
import logging
import argparse
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from p2p.protocol import *
from supabase_client import (
    resolve_domain as sb_resolve_domain,
    get_domain as sb_get_domain,
    list_domains as sb_list_domains,
    get_statistics as sb_get_statistics,
    SUPABASE_AVAILABLE,
)
from ons.registry import DomainRegistry

try:
    from aiohttp import web
except ImportError:
    print("ERROR: aiohttp module not found. Install with: pip3 install aiohttp")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ONI.ONS")


class ONSServer:
    """Orbit Name Server - DNS resolution for .orb domains.
    
    Uses Supabase as the primary database backend with local file fallback.
    """
    
    def __init__(self, host="0.0.0.0", port=ONS_PORT, data_dir=None):
        self.host = host
        self.port = port
        self.local_registry = DomainRegistry(data_dir)  # Local fallback
        self.app = web.Application()
        self.runner = None
        
        # Setup routes
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/resolve/{domain:.*}", self.handle_resolve)
        self.app.router.add_get("/lookup/{domain:.*}", self.handle_lookup)
        self.app.router.add_get("/domains", self.handle_list_domains)
        self.app.router.add_get("/stats", self.handle_stats)
    
    def _resolve(self, domain):
        """Resolve domain via Supabase first, fallback to local."""
        if SUPABASE_AVAILABLE:
            records = sb_resolve_domain(domain)
            if records:
                return records
        # Fallback to local registry
        return self.local_registry.resolve_domain(domain)
    
    def _get_domain(self, domain):
        """Get domain info via Supabase first, fallback to local."""
        if SUPABASE_AVAILABLE:
            info = sb_get_domain(domain)
            if info:
                return info
        return self.local_registry.get_domain(domain)
    
    def _list_domains(self):
        """List domains via Supabase first, fallback to local."""
        if SUPABASE_AVAILABLE:
            return sb_list_domains()
        return self.local_registry.list_domains()
    
    def _get_stats(self):
        """Get stats via Supabase first, fallback to local."""
        if SUPABASE_AVAILABLE:
            return sb_get_statistics()
        return self.local_registry.get_statistics()
    
    async def start(self):
        """Start the ONS server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        
        logger.info(f"ONS Server started on http://{self.host}:{self.port}")
        
        stats = self._get_stats()
        backend = "Supabase" if SUPABASE_AVAILABLE else "Local File"
</｜｜DSML｜｜parameter>
</｜｜DSML｜｜invoke>
        print(f"""
 ╔══════════════════════════════════════════╗
 ║      ONS - Orbit Name Servers Active     ║
 ╚══════════════════════════════════════════╝
    Address:  http://{self.host}:{self.port}
    Domains:  {stats['total_domains']} total ({stats['active_domains']} active)
    TLDs:     {', '.join(f'.{t}' for t in stats['tld_distribution'])}
    Protocol: ONS v1.0
    © 2026 Technic_ Dev
""")
    
    async def handle_index(self, request):
        """Handle index request."""
        stats = self._get_stats()
        domains_raw = self._list_domains()
        
        # Convert Supabase list format to dict format for template
        domains = {}
        if isinstance(domains_raw, list):
            for d in domains_raw:
                domain_name = d.get("domain", "")
                domains[domain_name] = {
                    "owner": d.get("owner", "Unknown"),
                    "tld": d.get("tld", "orb"),
                    "status": d.get("status", "active"),
                }
        elif isinstance(domains_raw, dict):
            domains = domains_raw
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ONS - Orbit Name Servers</title>
    <style>
        body {{ font-family: 'Courier New', monospace; background: #0a0a1a; color: #00ff88; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ color: #00ffcc; border-bottom: 2px solid #00ff88; padding-bottom: 10px; }}
        h2 {{ color: #00ffaa; }}
        .stat {{ background: #1a1a3a; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        .domain {{ background: #111133; padding: 8px; margin: 5px 0; border-left: 3px solid #00ff88; }}
        .tld {{ display: inline-block; background: #003366; color: #00ffcc; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; }}
        a {{ color: #00ffaa; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .footer {{ margin-top: 30px; font-size: 0.8em; color: #666; text-align: center; }}
        .endpoints {{ background: #1a1a3a; padding: 15px; border-radius: 5px; }}
        code {{ background: #000; padding: 2px 6px; border-radius: 3px; color: #ffaa00; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 ONS - Orbit Name Servers</h1>
        <p>Distributed DNS system for .orb domains on the ONI network</p>
        
        <div class="stat">
            <h2>📊 Statistics</h2>
            <p><strong>Total Domains:</strong> {stats['total_domains']}</p>
            <p><strong>Active Domains:</strong> {stats['active_domains']}</p>
            <p><strong>TLD Distribution:</strong></p>
            <ul>
"""
        for tld, count in stats['tld_distribution'].items():
            html += f"                <li>.{tld}: {count} domains</li>\n"
        
        html += f"""            </ul>
        </div>
        
        <div class="stat">
            <h2>📋 Registered Domains</h2>
"""
        for domain, info in list(domains.items())[:20]:
            tld = info.get("tld", "orb")
            html += f"""            <div class="domain">
                <strong>{domain}</strong> <span class="tld">.{tld}</span>
                <br><small>Owner: {info.get('owner', 'Unknown')}</small>
                <br><small>Status: {info.get('status', 'unknown')}</small>
            </div>
"""
        
        html += f"""        </div>
        
        <div class="endpoints">
            <h2>🔗 API Endpoints</h2>
            <p><code>GET /resolve/<domain></code> - Resolve a .orb domain to its records</p>
            <p><code>GET /lookup/<domain></code> - Look up domain registration info</p>
            <p><code>GET /domains</code> - List all registered domains</p>
            <p><code>GET /stats</code> - Get server statistics</p>
        </div>
        
        <div class="footer">
            <p>Orbit Name Servers - Part of the Orbital Network Infrastructure (ONI)</p>
            <p>© 2026 Technic_ Dev</p>
        </div>
    </div>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")
    
    async def handle_resolve(self, request):
        """Handle domain resolution request."""
        domain = request.match_info.get("domain", "").lower()
        
        if not domain.endswith(".orb"):
            domain = domain + ".orb" if domain else ""
        
        if not domain:
            return web.json_response({"error": "No domain specified"}, status=400)
        
        records = self._resolve(domain)
        if records:
            return web.json_response({
                "domain": domain,
                "found": True,
                "records": records,
            })
        
        return web.json_response({
            "domain": domain,
            "found": False,
            "error": "Domain not found or inactive",
        }, status=404)
    
    async def handle_lookup(self, request):
        """Handle domain lookup request."""
        domain = request.match_info.get("domain", "").lower()
        
        if not domain.endswith(".orb"):
            domain = domain + ".orb" if domain else ""
        
        if not domain:
            return web.json_response({"error": "No domain specified"}, status=400)
        
        info = self._get_domain(domain)
        if info:
            # Don't expose owner key
            safe_info = {k: v for k, v in info.items() if k != "owner_key"}
            return web.json_response({
                "domain": domain,
                "found": True,
                "info": safe_info,
            })
        
        return web.json_response({
            "domain": domain,
            "found": False,
        }, status=404)
    
    async def handle_list_domains(self, request):
        """Handle domain listing request."""
        domains_raw = self._list_domains()
        
        # Normalize to dict format
        if isinstance(domains_raw, list):
            domains_dict = {}
            for d in domains_raw:
                domain_name = d.get("domain", "")
                domains_dict[domain_name] = {
                    "owner": d.get("owner", "Unknown"),
                    "tld": d.get("tld", "orb"),
                    "status": d.get("status", "active"),
                }
            return web.json_response({
                "count": len(domains_dict),
                "domains": domains_dict,
            })
        else:
            return web.json_response({
                "count": len(domains_raw),
                "domains": domains_raw,
            })
    
    async def handle_stats(self, request):
        """Handle statistics request."""
        return web.json_response(self._get_stats())
    
    async def stop(self):
        """Stop the ONS server."""
        if self.runner:
            await self.runner.cleanup()
        logger.info("ONS Server stopped")


async def main():
    parser = argparse.ArgumentParser(description="ONS - Orbit Name Servers")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=ONS_PORT, help="Port to listen on")
    parser.add_argument("--data-dir", help="Data directory for registry")
    
    args = parser.parse_args()
    
    server = ONSServer(args.host, args.port, args.data_dir)
    
    try:
        await server.start()
        # Keep running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down ONS Server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())