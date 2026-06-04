#!/usr/bin/env python3
# ONI Supabase Client
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure
#
# This module connects the ONI network to Supabase as the database backend.
# Stores domains, sites, peers, and registry logs in Supabase PostgreSQL.

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("ONI.Supabase")

# Try to load environment variables from .env file
ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# Configuration from environment
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://xtkvikjbaymtmydgbmvd.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY",
    "sb_publishable_W0SItN9oQxPA8vA8rNBnBg_vzFClU5_"
)

try:
    from supabase import create_client, Client
    _supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    SUPABASE_AVAILABLE = True
except Exception as e:
    _supabase = None
    SUPABASE_AVAILABLE = False
    logger.warning(f"Supabase not available: {e}. Using local file storage.")


def get_client() -> Client:
    """Get the Supabase client instance."""
    if not SUPABASE_AVAILABLE:
        raise RuntimeError("Supabase is not available. Check your credentials.")
    return _supabase


# ===== DOMAIN OPERATIONS =====

def register_domain(domain: str, name: str, tld: str, owner: str = "Anonymous",
                   owner_key: str = None, records: dict = None) -> tuple:
    """Register a new .orb domain in Supabase."""
    if not owner_key:
        owner_key = hashlib.sha256(
            f"{domain}:{time.time()}:{os.urandom(32)}".encode()
        ).hexdigest()
    
    if not records:
        records = {"A": ["127.0.0.1"]}
    
    try:
        client = get_client()
        data = {
            "domain": domain,
            "name": name,
            "tld": tld,
            "owner": owner,
            "owner_key": owner_key,
            "status": "active",
            "records": json.dumps(records),
            "metadata": {},
        }
        
        result = client.table("domains").insert(data).execute()
        
        # Log the registration
        _log_action(domain, "register", owner_key)
        
        return True, "Domain registered successfully", owner_key
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            return False, "Domain already registered", None
        logger.error(f"Supabase registration failed: {e}")
        return False, f"Registration failed: {e}", None


def get_domain(domain: str) -> dict:
    """Get domain registration info from Supabase."""
    try:
        client = get_client()
        result = client.table("domains") \
            .select("*") \
            .eq("domain", domain.lower()) \
            .limit(1) \
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Supabase get_domain failed: {e}")
        return None


def resolve_domain(domain: str) -> dict:
    """Resolve a .orb domain to its DNS records."""
    info = get_domain(domain)
    if info and info.get("status") == "active":
        records = info.get("records")
        if isinstance(records, str):
            records = json.loads(records)
        return records
    return None


def list_domains(status: str = "active", limit: int = 100, offset: int = 0) -> list:
    """List all registered domains."""
    try:
        client = get_client()
        query = client.table("domains").select("*")
        
        if status:
            query = query.eq("status", status)
        
        result = query.order("registered_at", desc=True) \
                     .range(offset, offset + limit) \
                     .execute()
        
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Supabase list_domains failed: {e}")
        return []


def update_domain_records(domain: str, records: dict, owner_key: str) -> tuple:
    """Update DNS records for a domain (requires owner_key)."""
    try:
        client = get_client()
        # Verify ownership
        info = get_domain(domain)
        if not info:
            return False, "Domain not found"
        if info.get("owner_key") != owner_key:
            return False, "Not authorized - invalid owner key"
        
        result = client.table("domains") \
            .update({"records": json.dumps(records)}) \
            .eq("domain", domain.lower()) \
            .execute()
        
        _log_action(domain, "update", owner_key)
        return True, "Records updated successfully"
    except Exception as e:
        logger.error(f"Supabase update failed: {e}")
        return False, f"Update failed: {e}"


def delete_domain(domain: str, owner_key: str) -> tuple:
    """Delete a domain registration (requires owner_key)."""
    try:
        client = get_client()
        info = get_domain(domain)
        if not info:
            return False, "Domain not found"
        if info.get("owner_key") != owner_key:
            return False, "Not authorized - invalid owner key"
        
        client.table("domains") \
            .delete() \
            .eq("domain", domain.lower()) \
            .execute()
        
        _log_action(domain, "delete", owner_key)
        return True, "Domain deleted successfully"
    except Exception as e:
        logger.error(f"Supabase delete failed: {e}")
        return False, f"Delete failed: {e}"


def search_domains(query: str, limit: int = 20) -> list:
    """Search domains by name or owner."""
    try:
        client = get_client()
        # Supabase doesn't support full-text search easily, so we do prefix match
        result = client.table("domains") \
            .select("*") \
            .ilike("domain", f"{query}%") \
            .limit(limit) \
            .execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Supabase search failed: {e}")
        return []


def get_statistics() -> dict:
    """Get registry statistics from Supabase."""
    try:
        client = get_client()
        
        # Get total count
        total = client.table("domains") \
            .select("id", count="exact") \
            .execute()
        
        # Get active count
        active = client.table("domains") \
            .select("id", count="exact") \
            .eq("status", "active") \
            .execute()
        
        # Get TLD distribution
        all_domains = client.table("domains") \
            .select("tld") \
            .execute()
        
        tld_dist = {}
        if all_domains.data:
            for d in all_domains.data:
                tld = d.get("tld", "unknown")
                tld_dist[tld] = tld_dist.get(tld, 0) + 1
        
        return {
            "total_domains": total.count if hasattr(total, 'count') else len(total.data or []),
            "active_domains": active.count if hasattr(active, 'count') else len(active.data or []),
            "tld_distribution": tld_dist,
        }
    except Exception as e:
        logger.error(f"Supabase stats failed: {e}")
        return {"total_domains": 0, "active_domains": 0, "tld_distribution": {}}


# ===== SITE CONTENT OPERATIONS =====

def upload_site_file(domain: str, path: str, content: str,
                    content_type: str = "text/html") -> tuple:
    """Upload a website file to Supabase."""
    try:
        client = get_client()
        size = len(content.encode("utf-8"))
        is_binary = not content_type.startswith("text/")
        
        data = {
            "domain": domain.lower(),
            "path": path,
            "content_type": content_type,
            "content": content,
            "size_bytes": size,
            "is_binary": is_binary,
        }
        
        # Upsert (insert or update)
        result = client.table("sites").upsert(
            data,
            on_conflict="domain,path"
        ).execute()
        
        return True, "File uploaded successfully"
    except Exception as e:
        logger.error(f"Supabase site upload failed: {e}")
        return False, f"Upload failed: {e}"


def get_site_file(domain: str, path: str = "/index.html") -> dict:
    """Get a website file from Supabase."""
    try:
        client = get_client()
        result = client.table("sites") \
            .select("*") \
            .eq("domain", domain.lower()) \
            .eq("path", path) \
            .limit(1) \
            .execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Supabase get_site_file failed: {e}")
        return None


# ===== PEER OPERATIONS =====

def register_peer(peer_id: str, host: str, port: int, node_name: str = None,
                 capabilities: list = None, hosted_domains: list = None) -> tuple:
    """Register or update a peer in the network."""
    try:
        client = get_client()
        data = {
            "peer_id": peer_id,
            "host": host,
            "port": port,
            "node_name": node_name or f"oni-node-{peer_id[:8]}",
            "capabilities": capabilities or [],
            "hosted_domains": hosted_domains or [],
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
        }
        
        result = client.table("peers").upsert(
            data,
            on_conflict="peer_id"
        ).execute()
        
        return True, "Peer registered"
    except Exception as e:
        logger.error(f"Supabase peer register failed: {e}")
        return False, str(e)


def get_active_peers(limit: int = 50) -> list:
    """Get active peers from the network."""
    try:
        client = get_client()
        result = client.table("peers") \
            .select("*") \
            .eq("is_active", True) \
            .order("last_seen", desc=True) \
            .limit(limit) \
            .execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Supabase get_peers failed: {e}")
        return []


# ===== INTERNAL HELPERS =====

def _log_action(domain: str, action: str, owner_key: str = None):
    """Log a registry action."""
    try:
        client = get_client()
        key_hash = hashlib.sha256(owner_key.encode()).hexdigest() if owner_key else None
        client.table("registry_log").insert({
            "domain": domain.lower(),
            "action": action,
            "owner_key_hash": key_hash,
            "details": {"timestamp": time.time()},
        }).execute()
    except:
        pass  # Don't fail main operation if logging fails


def check_connection() -> bool:
    """Check if Supabase connection is working."""
    try:
        client = get_client()
        result = client.table("domains").select("id", count="exact").limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Supabase connection check failed: {e}")
        return False


# Initialize: try to seed default domains on import
if SUPABASE_AVAILABLE:
    try:
        # Check if we need seed data
        existing = list_domains(limit=1)
        if not existing:
            logger.info("Seeding default .orb domains into Supabase...")
            register_domain("helloworld.orb", "helloworld", "orb",
                          "ONI System", "oni_root_seed",
                          {"A": ["127.0.0.1"], "NS": ["ns1.oni.network"]})
            register_domain("myblog.orb", "myblog", "orb",
                          "ONI System", "oni_root_seed",
                          {"A": ["127.0.0.1"], "NS": ["ns1.oni.network"]})
            register_domain("docs.orb", "docs", "orb",
                          "ONI System", "oni_root_seed",
                          {"A": ["127.0.0.1"], "NS": ["ns1.oni.network"]})
            logger.info("Default domains seeded.")
    except Exception as e:
        logger.warning(f"Seed data insertion skipped: {e}")

# Check connection at module load
if SUPABASE_AVAILABLE:
    if check_connection():
        logger.info(f"✅ ONI connected to Supabase: {SUPABASE_URL}")
    else:
        logger.warning("⚠️  Supabase connection failed. Check credentials.")