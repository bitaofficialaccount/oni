# ONS - Orbit Name Servers Registry
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure

import json
import time
import threading
import os
from pathlib import Path

REGISTRY_FILE = "ons_registry.json"

# Pre-registered default domains
DEFAULT_DOMAINS = {
    "helloworld.orb": {
        "owner": "ONI System",
        "owner_key": "oni_root",
        "tld": "orb",
        "registered": time.time(),
        "status": "active",
        "records": {
            "A": ["127.0.0.1"],
            "NS": ["ns1.oni.network"],
        },
    },
    "myblog.orb": {
        "owner": "ONI System",
        "owner_key": "oni_root",
        "tld": "orb",
        "registered": time.time(),
        "status": "active",
        "records": {
            "A": ["127.0.0.1"],
            "NS": ["ns1.oni.network"],
        },
    },
    "docs.orb": {
        "owner": "ONI System",
        "owner_key": "oni_root",
        "tld": "orb",
        "registered": time.time(),
        "status": "active",
        "records": {
            "A": ["127.0.0.1"],
            "NS": ["ns1.oni.network"],
        },
    },
}


class DomainRegistry:
    """Domain registry for .orb domains."""
    
    def __init__(self, data_dir=None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent / "data"
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.data_dir / REGISTRY_FILE
        self.domains = {}
        self.lock = threading.Lock()
        
        self._load()
    
    def _load(self):
        """Load registry from disk."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r") as f:
                    data = json.load(f)
                self.domains = data.get("domains", {})
                print(f"Loaded {len(self.domains)} domains from registry")
            except Exception as e:
                print(f"Failed to load registry: {e}")
                self.domains = dict(DEFAULT_DOMAINS)
        else:
            self.domains = dict(DEFAULT_DOMAINS)
            self._save()
    
    def _save(self):
        """Save registry to disk."""
        try:
            with open(self.registry_file, "w") as f:
                json.dump({"domains": self.domains, "updated": time.time()}, f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save registry: {e}")
            return False
    
    def register_domain(self, domain, owner, owner_key, tld="orb", records=None):
        """Register a new .orb domain."""
        with self.lock:
            domain = domain.lower()
            if domain in self.domains:
                return False, "Domain already registered"
            
            self.domains[domain] = {
                "owner": owner,
                "owner_key": owner_key,
                "tld": tld,
                "registered": time.time(),
                "status": "active",
                "records": records or {"A": ["127.0.0.1"]},
            }
            
            self._save()
            return True, "Domain registered successfully"
    
    def get_domain(self, domain):
        """Get domain registration info."""
        with self.lock:
            return self.domains.get(domain.lower())
    
    def resolve_domain(self, domain):
        """Resolve a .orb domain to its records."""
        with self.lock:
            domain = domain.lower()
            info = self.domains.get(domain)
            if info and info.get("status") == "active":
                return info.get("records", {})
            return None
    
    def list_domains(self, status="active"):
        """List all registered domains."""
        with self.lock:
            return {d: info for d, info in self.domains.items() 
                   if info.get("status") == status}
    
    def delete_domain(self, domain, owner_key):
        """Delete a domain registration."""
        with self.lock:
            domain = domain.lower()
            if domain not in self.domains:
                return False, "Domain not found"
            
            if self.domains[domain]["owner_key"] != owner_key:
                return False, "Not authorized"
            
            del self.domains[domain]
            self._save()
            return True, "Domain deleted successfully"
    
    def update_records(self, domain, records, owner_key):
        """Update DNS records for a domain."""
        with self.lock:
            domain = domain.lower()
            if domain not in self.domains:
                return False, "Domain not found"
            
            if self.domains[domain]["owner_key"] != owner_key:
                return False, "Not authorized"
            
            self.domains[domain]["records"] = records
            self.domains[domain]["updated"] = time.time()
            self._save()
            return True, "Records updated successfully"
    
    def get_statistics(self):
        """Get registry statistics."""
        with self.lock:
            total = len(self.domains)
            active = sum(1 for d in self.domains.values() if d.get("status") == "active")
            tlds = {}
            for d in self.domains.values():
                tld = d.get("tld", "unknown")
                tlds[tld] = tlds.get(tld, 0) + 1
            
            return {
                "total_domains": total,
                "active_domains": active,
                "tld_distribution": tlds,
            }