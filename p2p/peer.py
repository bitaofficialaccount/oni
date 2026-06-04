# ONI Peer Management
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure

import json
import time
import hashlib
import threading
import asyncio
import logging
from .protocol import *

logger = logging.getLogger("ONI.Peer")


class Peer:
    """Represents a peer on the ONI network."""
    
    def __init__(self, peer_id, host, port, public_key=None):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.public_key = public_key
        self.last_seen = time.time()
        self.latency = 0
        self.capabilities = set()
        self.content_hosted = set()  # Domains hosted by this peer
    
    def is_alive(self, timeout=PEER_TIMEOUT):
        """Check if peer is still alive."""
        return (time.time() - self.last_seen) < timeout
    
    def to_dict(self):
        """Serialize peer to dictionary."""
        return {
            "peer_id": self.peer_id,
            "host": self.host,
            "port": self.port,
            "public_key": self.public_key,
            "last_seen": self.last_seen,
            "latency": self.latency,
            "capabilities": list(self.capabilities),
            "content_hosted": list(self.content_hosted),
        }
    
    @staticmethod
    def from_dict(data):
        """Deserialize peer from dictionary."""
        peer = Peer(
            data["peer_id"],
            data["host"],
            data["port"],
            data.get("public_key"),
        )
        peer.last_seen = data.get("last_seen", time.time())
        peer.latency = data.get("latency", 0)
        peer.capabilities = set(data.get("capabilities", []))
        peer.content_hosted = set(data.get("content_hosted", []))
        return peer
    
    def __repr__(self):
        return f"Peer({self.peer_id[:8]}...@{self.host}:{self.port})"


class PeerManager:
    """Manages peer connections on the ONI network."""
    
    def __init__(self, bootstrap_nodes=None):
        self.peers = {}  # peer_id -> Peer
        self.bootstrap_nodes = bootstrap_nodes or BOOTSTRAP_NODES
        self.lock = threading.Lock()
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread to clean up dead peers."""
        def cleanup():
            while True:
                time.sleep(60)
                self.remove_dead_peers()
        
        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()
    
    def add_peer(self, peer):
        """Add or update a peer in the network."""
        with self.lock:
            if peer.peer_id in self.peers:
                existing = self.peers[peer.peer_id]
                existing.last_seen = time.time()
                existing.latency = peer.latency
                existing.capabilities.update(peer.capabilities)
                existing.content_hosted.update(peer.content_hosted)
            else:
                self.peers[peer.peer_id] = peer
                logger.info(f"New peer added: {peer}")
            
            # Limit total peers
            if len(self.peers) > MAX_PEERS:
                # Remove oldest peer
                oldest = min(self.peers.values(), key=lambda p: p.last_seen)
                del self.peers[oldest.peer_id]
    
    def remove_peer(self, peer_id):
        """Remove a peer from the network."""
        with self.lock:
            if peer_id in self.peers:
                del self.peers[peer_id]
                logger.info(f"Peer removed: {peer_id[:8]}")
    
    def remove_dead_peers(self):
        """Remove peers that have timed out."""
        with self.lock:
            dead = [pid for pid, p in self.peers.items() if not p.is_alive()]
            for pid in dead:
                del self.peers[pid]
            if dead:
                logger.info(f"Removed {len(dead)} dead peers")
    
    def get_peer(self, peer_id):
        """Get a peer by ID."""
        with self.lock:
            return self.peers.get(peer_id)
    
    def get_alive_peers(self):
        """Get all alive peers."""
        with self.lock:
            return [p for p in self.peers.values() if p.is_alive()]
    
    def get_peers_for_content(self, domain):
        """Get peers that host a specific domain."""
        with self.lock:
            return [p for p in self.peers.values() 
                   if domain in p.content_hosted and p.is_alive()]
    
    def get_peer_list(self):
        """Get serializable list of peers for network exchange."""
        with self.lock:
            return [p.to_dict() for p in self.peers.values()[:20]]
    
    def get_peer_count(self):
        """Get total number of known peers."""
        with self.lock:
            return len(self.peers)
    
    def generate_peer_id(self, host, port):
        """Generate a unique peer ID from host and port."""
        data = f"{host}:{port}:{time.time()}".encode()
        return hashlib.sha256(data).hexdigest()