#!/usr/bin/env python3
# ONI Network Node
# Copyright (c) 2026 Technic_ Dev
# Part of the Orbital Network Infrastructure

import sys
import os
import json
import time
import logging
import argparse
import asyncio
import signal
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from p2p.protocol import *
from p2p.peer import Peer, PeerManager

# Try importing websockets
try:
    import websockets
except ImportError:
    print("ERROR: websockets module not found. Install with: pip3 install websockets")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ONI.Node")


class ONINode:
    """Main ONI network node implementing P2P communication."""
    
    def __init__(self, host="0.0.0.0", port=ONI_P2P_PORT, node_name=None):
        self.host = host
        self.port = port
        self.peer_manager = PeerManager()
        self.node_id = self.peer_manager.generate_peer_id(host, port)
        self.node_name = node_name or f"oni-node-{self.node_id[:8]}"
        self.content_store = {}  # domain -> content mapping
        self.running = False
        self.server = None
        
        logger.info(f"ONI Node initialized: {self.node_name}")
        logger.info(f"Node ID: {self.node_id}")
    
    async def start(self):
        """Start the ONI node."""
        self.running = True
        logger.info(f"Starting ONI node on {self.host}:{self.port}")
        
        try:
            self.server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
            )
            logger.info(f"ONI Node listening on ws://{self.host}:{self.port}")
            logger.info(f"Node ID: {self.node_id}")
            
            # Register ourself as a peer
            asyncio.create_task(self.announce_self())
            
            await self.server.wait_closed()
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
        finally:
            self.running = False
    
    async def announce_self(self):
        """Announce this node to the network periodically."""
        while self.running:
            # Create our own peer entry
            our_peer = Peer(
                self.node_id,
                self.host if self.host != "0.0.0.0" else "127.0.0.1",
                self.port,
            )
            our_peer.capabilities.add("hosting")
            our_peer.capabilities.add("resolver")
            our_peer.content_hosted.update(self.content_store.keys())
            self.peer_manager.add_peer(our_peer)
            
            await asyncio.sleep(30)
    
    async def handle_connection(self, websocket, path=None):
        """Handle incoming WebSocket connection."""
        peer_id = None
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    sender_id = data.get("sender_id")
                    
                    if not msg_type:
                        continue
                    
                    # Create peer entry on first contact
                    if sender_id and sender_id != self.node_id:
                        peer = Peer(sender_id, websocket.remote_address[0], 0)
                        self.peer_manager.add_peer(peer)
                        peer_id = sender_id
                    
                    # Handle different message types
                    handler = getattr(self, f"handle_{msg_type}", None)
                    if handler:
                        response = await handler(data, websocket)
                        if response:
                            await websocket.send(json.dumps(response))
                    else:
                        await websocket.send(json.dumps({
                            "type": MSG_ERROR,
                            "message": f"Unknown message type: {msg_type}"
                        }))
                        
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": MSG_ERROR,
                        "message": "Invalid JSON"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if peer_id:
                logger.info(f"Peer disconnected: {peer_id[:8]}")
    
    async def handle_ping(self, data, websocket):
        """Handle ping request."""
        return {
            "type": MSG_PONG,
            "sender_id": self.node_id,
            "timestamp": time.time(),
            "node_name": self.node_name,
            "peer_count": self.peer_manager.get_peer_count(),
            "content_count": len(self.content_store),
        }
    
    async def handle_peer_discovery(self, data, websocket):
        """Handle peer discovery request."""
        return {
            "type": MSG_PEER_LIST,
            "sender_id": self.node_id,
            "peers": self.peer_manager.get_peer_list(),
        }
    
    async def handle_content_request(self, data, websocket):
        """Handle content request for a domain."""
        domain = data.get("domain", "").lower()
        path = data.get("path", "/index.html")
        
        if domain in self.content_store:
            content = self.content_store[domain]
            file_path = path.lstrip("/")
            
            if file_path in content.get("files", {}):
                file_data = content["files"][file_path]
                return {
                    "type": MSG_CONTENT_RESPONSE,
                    "domain": domain,
                    "path": path,
                    "content": file_data.get("content", ""),
                    "content_type": file_data.get("content_type", CONTENT_TYPE_DEFAULT),
                    "status": 200,
                }
            # Try index.html as default
            if path == "/" and "index.html" in content.get("files", {}):
                file_data = content["files"]["index.html"]
                return {
                    "type": MSG_CONTENT_RESPONSE,
                    "domain": domain,
                    "path": "/index.html",
                    "content": file_data.get("content", ""),
                    "content_type": CONTENT_TYPE_HTML,
                    "status": 200,
                }
            
            return {
                "type": MSG_CONTENT_RESPONSE,
                "domain": domain,
                "path": path,
                "content": "<h1>404 - Page Not Found</h1><p>The requested page was not found on this node.</p>",
                "content_type": CONTENT_TYPE_HTML,
                "status": 404,
            }
        
        return {
            "type": MSG_CONTENT_RESPONSE,
            "domain": domain,
            "path": path,
            "content": "<h1>404 - Domain Not Found</h1><p>This domain is not hosted on this node.</p>",
            "content_type": CONTENT_TYPE_HTML,
            "status": 404,
        }
    
    async def handle_domain_resolve(self, data, websocket):
        """Handle domain resolution request."""
        domain = data.get("domain", "").lower()
        
        parsed = parse_domain(domain)
        if not parsed:
            return {
                "type": MSG_DOMAIN_RESPONSE,
                "domain": domain,
                "found": False,
                "error": "Invalid .orb domain",
            }
        
        # Check if we host this domain
        if domain in self.content_store:
            return {
                "type": MSG_DOMAIN_RESPONSE,
                "domain": domain,
                "found": True,
                "hosts": [{
                    "node_id": self.node_id,
                    "host": self.host,
                    "port": self.port,
                    "node_name": self.node_name,
                }],
            }
        
        # Check if any known peer hosts it
        peers = self.peer_manager.get_peers_for_content(domain)
        if peers:
            return {
                "type": MSG_DOMAIN_RESPONSE,
                "domain": domain,
                "found": True,
                "hosts": [{
                    "node_id": p.peer_id,
                    "host": p.host,
                    "port": p.port,
                } for p in peers[:3]],
            }
        
        return {
            "type": MSG_DOMAIN_RESPONSE,
            "domain": domain,
            "found": False,
        }
    
    def host_domain(self, domain, files):
        """Host a domain's content on this node."""
        domain = domain.lower()
        if not validate_domain(domain):
            logger.error(f"Invalid domain: {domain}")
            return False
        
        parsed = parse_domain(domain)
        self.content_store[domain] = {
            "domain": domain,
            "parsed": parsed,
            "files": files,
            "hosted_since": time.time(),
        }
        
        # Update our peer entry
        our_peer = Peer(self.node_id, self.host, self.port)
        our_peer.content_hosted.add(domain)
        self.peer_manager.add_peer(our_peer)
        
        logger.info(f"Now hosting: {domain} ({len(files)} files)")
        return True
    
    def host_directory(self, domain, directory_path):
        """Host an entire directory as a .orb website."""
        domain = domain.lower()
        base_path = Path(directory_path)
        
        if not base_path.exists():
            logger.error(f"Directory not found: {directory_path}")
            return False
        
        files = {}
        for file_path in base_path.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(base_path))
                ext = file_path.suffix.lower()
                content_type = CONTENT_TYPE_MAP.get(ext, CONTENT_TYPE_DEFAULT)
                
                try:
                    with open(file_path, "rb") as f:
                        content = f.read()
                    
                    # For text files, decode to string
                    if content_type.startswith("text/") or content_type == "application/javascript":
                        content = content.decode("utf-8", errors="replace")
                    else:
                        # Base64 encode binary files
                        import base64
                        content = base64.b64encode(content).decode("ascii")
                        content_type = content_type + ";base64"
                    
                    files[rel_path] = {
                        "content": content,
                        "content_type": content_type,
                    }
                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")
        
        return self.host_domain(domain, files)
    
    def stop(self):
        """Stop the ONI node."""
        self.running = False
        if self.server:
            self.server.close()
        logger.info("ONI Node stopped")


async def main():
    parser = argparse.ArgumentParser(description="ONI Network Node")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=ONI_P2P_PORT, help="Port to listen on")
    parser.add_argument("--name", help="Node name")
    parser.add_argument("--host-domain", nargs=2, metavar=("DOMAIN", "DIR"),
                       help="Host a .orb domain from a directory")
    parser.add_argument("--standalone", action="store_true",
                       help="Run without connecting to other nodes")
    
    args = parser.parse_args()
    
    node = ONINode(args.host, args.port, args.name)
    
    # Host domains if specified
    if args.host_domain:
        domain, directory = args.host_domain
        node.host_directory(domain, directory)
    
    print(f"""
 ╔══════════════════════════════════════════╗
 ║         ONI Network Node Active          ║
 ║         Orbital Network Infrastructure   ║
 ╚══════════════════════════════════════════╝
    Node:     {node.node_name}
    ID:       {node.node_id[:16]}...
    Address:  ws://{args.host}:{args.port}
    Hosting:  {len(node.content_store)} domains
    Protocol: {ONI_PROTOCOL_NAME} v{ONI_PROTOCOL_VERSION}
    © 2026 Technic_ Dev
""")
    
    try:
        await node.start()
    except KeyboardInterrupt:
        print("\nShutting down ONI Node...")
        node.stop()


if __name__ == "__main__":
    asyncio.run(main())