# ONI Protocol Definitions
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure

ONI_PROTOCOL_VERSION = "1.0.0"
ONI_PROTOCOL_NAME = "ONI"

# Message Types
MSG_PEER_DISCOVERY = "peer_discovery"
MSG_PEER_LIST = "peer_list"
MSG_PING = "ping"
MSG_PONG = "pong"
MSG_CONTENT_REQUEST = "content_request"
MSG_CONTENT_RESPONSE = "content_response"
MSG_DOMAIN_RESOLVE = "domain_resolve"
MSG_DOMAIN_RESPONSE = "domain_response"
MSG_DOMAIN_REGISTER = "domain_register"
MSG_DOMAIN_CONFIRM = "domain_confirm"
MSG_ERROR = "error"

# TLD Registry
ORB_TLDS = [
    "orb",
    "orb.be",
    "orb.uk",
    "orb.org",
    "orb.fun",
    "orb.dev",
    "orb.io",
]

# Default Ports
ONI_P2P_PORT = 6881
ONS_PORT = 5353
REGISTRAR_PORT = 8080
BROWSER_PORT = 9090

# Network constants
MAX_PEERS = 50
PEER_TIMEOUT = 300  # 5 minutes
CACHE_TTL = 3600  # 1 hour
REPLICATION_FACTOR = 3
BOOTSTRAP_NODES = [
    "bootstrap.oni.network",
]

# Content types
CONTENT_TYPE_HTML = "text/html"
CONTENT_TYPE_CSS = "text/css"
CONTENT_TYPE_JS = "application/javascript"
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_PNG = "image/png"
CONTENT_TYPE_JPG = "image/jpeg"
CONTENT_TYPE_GIF = "image/gif"
CONTENT_TYPE_SVG = "image/svg+xml"
CONTENT_TYPE_WOFF2 = "font/woff2"
CONTENT_TYPE_DEFAULT = "application/octet-stream"

CONTENT_TYPE_MAP = {
    ".html": CONTENT_TYPE_HTML,
    ".htm": CONTENT_TYPE_HTML,
    ".css": CONTENT_TYPE_CSS,
    ".js": CONTENT_TYPE_JS,
    ".json": CONTENT_TYPE_JSON,
    ".png": CONTENT_TYPE_PNG,
    ".jpg": CONTENT_TYPE_JPG,
    ".jpeg": CONTENT_TYPE_JPG,
    ".gif": CONTENT_TYPE_GIF,
    ".svg": CONTENT_TYPE_SVG,
    ".woff2": CONTENT_TYPE_WOFF2,
}

# Domain validation
def validate_domain(domain):
    """Validate a .orb domain name."""
    if not domain or not domain.endswith(".orb"):
        return False
    
    parts = domain.rstrip(".").split(".")
    if len(parts) < 2:
        return False
    
    name = parts[0]
    if not name or len(name) < 1 or len(name) > 63:
        return False
    
    import re
    if not re.match(r'^[a-zA-Z0-9-]+$', name):
        return False
    
    if name.startswith("-") or name.endswith("-"):
        return False
    
    return True

def parse_domain(domain):
    """Parse a .orb domain into its components."""
    if not validate_domain(domain):
        return None
    
    parts = domain.rstrip(".").lower().split(".")
    name = parts[0]
    # Check if it's a custom TLD like .orb.be, .orb.uk etc.
    if len(parts) >= 3:
        tld = ".".join(parts[1:])  # e.g. "orb.be"
    else:
        tld = parts[1]  # e.g. "orb"
    
    return {
        "name": name,
        "tld": tld,
        "full": f"{name}.{tld}"
    }