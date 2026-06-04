# ONS Resolver - .orb Domain Resolution
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure

import json
import time
import logging
import threading
from pathlib import Path

logger = logging.getLogger("ONI.Resolver")


class ONSResolver:
    """Resolves .orb domains to their hosting information."""
    
    def __init__(self, registry=None):
        self.registry = registry
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.lock = threading.Lock()
    
    def resolve(self, domain):
        """Resolve a .orb domain to its records."""
        domain = domain.lower()
        
        # Check cache first
        with self.lock:
            if domain in self.cache:
                entry, timestamp = self.cache[domain]
                if time.time() - timestamp < self.cache_ttl:
                    return entry
        
        if self.registry:
            # Resolve from registry
            records = self.registry.resolve_domain(domain)
            
            # Cache the result
            with self.lock:
                self.cache[domain] = (records, time.time())
            
            return records
        
        return None
    
    def batch_resolve(self, domains):
        """Resolve multiple domains at once."""
        return {domain: self.resolve(domain) for domain in domains}
    
    def clear_cache(self, domain=None):
        """Clear the resolution cache."""
        with self.lock:
            if domain:
                self.cache.pop(domain, None)
            else:
                self.cache.clear()


class DNSResolver(ONSResolver):
    """Alias for ONSResolver - resolves .orb domains to their hosting information.
    This class exists for backward compatibility with code that imports DNSResolver."""
    pass