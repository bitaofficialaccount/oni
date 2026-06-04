-- ONI - Orbital Network Infrastructure Supabase Schema
-- Copyright (c) 2026 Technic_ Dev
-- Run this SQL in your Supabase project SQL Editor

-- 1. DOMAINS TABLE
-- Stores all .orb domain registrations
CREATE TABLE IF NOT EXISTS public.domains (
    id BIGSERIAL PRIMARY KEY,
    domain TEXT UNIQUE NOT NULL,                    -- e.g. "mysite.orb", "myblog.orb.dev"
    name TEXT NOT NULL,                             -- e.g. "mysite"
    tld TEXT NOT NULL,                              -- e.g. "orb", "orb.dev", "orb.be"
    owner TEXT NOT NULL DEFAULT 'Anonymous',         -- Display name of owner
    owner_key TEXT NOT NULL,                         -- Cryptographic ownership key (hash)
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- DNS records stored as JSONB for flexibility
    records JSONB NOT NULL DEFAULT '{"A": ["127.0.0.1"]}'::jsonb,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- 2. SITES TABLE
-- Stores hosted .orb website content (optional, can also be hosted on ONI nodes)
CREATE TABLE IF NOT EXISTS public.sites (
    id BIGSERIAL PRIMARY KEY,
    domain_id BIGINT REFERENCES public.domains(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT '/index.html',        -- File path within the site
    content_type TEXT NOT NULL DEFAULT 'text/html',
    content TEXT NOT NULL,                           -- File content (base64 for binaries)
    size_bytes BIGINT DEFAULT 0,
    is_binary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(domain, path)
);

-- 3. USERS TABLE (via Supabase Auth)
-- We extend Supabase auth.users with ONI-specific profile data
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE,
    display_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    registered_domains INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. PEERS TABLE
-- Tracks ONI network peers (optional, for distributed registry)
CREATE TABLE IF NOT EXISTS public.peers (
    id BIGSERIAL PRIMARY KEY,
    peer_id TEXT UNIQUE NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 6881,
    node_name TEXT,
    public_key TEXT,
    capabilities TEXT[] DEFAULT '{}',
    hosted_domains TEXT[] DEFAULT '{}',
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. REGISTRY_LOG TABLE
-- Audit log for domain operations
CREATE TABLE IF NOT EXISTS public.registry_log (
    id BIGSERIAL PRIMARY KEY,
    domain TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('register', 'transfer', 'update', 'delete', 'renew')),
    owner_key_hash TEXT,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ===== INDEXES =====
CREATE INDEX IF NOT EXISTS idx_domains_tld ON public.domains(tld);
CREATE INDEX IF NOT EXISTS idx_domains_owner ON public.domains(owner);
CREATE INDEX IF NOT EXISTS idx_domains_status ON public.domains(status);
CREATE INDEX IF NOT EXISTS idx_domains_created ON public.domains(registered_at DESC);
CREATE INDEX IF NOT EXISTS idx_sites_domain ON public.sites(domain);
CREATE INDEX IF NOT EXISTS idx_peers_active ON public.peers(is_active);
CREATE INDEX IF NOT EXISTS idx_registry_log_domain ON public.registry_log(domain);
CREATE INDEX IF NOT EXISTS idx_registry_log_created ON public.registry_log(created_at DESC);

-- ===== ROW LEVEL SECURITY =====
ALTER TABLE public.domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.peers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.registry_log ENABLE ROW LEVEL SECURITY;

-- Public can read domains and sites
CREATE POLICY "Domains are publicly readable" ON public.domains
    FOR SELECT USING (true);

CREATE POLICY "Sites are publicly readable" ON public.sites
    FOR SELECT USING (true);

-- Only authenticated users can insert/update their domains
CREATE POLICY "Users can insert domains" ON public.domains
    FOR INSERT WITH CHECK (true);  -- Allow registration without auth (owner key is the auth)

CREATE POLICY "Users can update their domains" ON public.domains
    FOR UPDATE USING (true);  -- Verified via owner_key in application

-- Profiles: users can read all, update only their own
CREATE POLICY "Profiles are publicly readable" ON public.profiles
    FOR SELECT USING (true);

CREATE POLICY "Users can update their own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

-- ===== TRIGGER: update updated_at =====
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_domains_updated_at BEFORE UPDATE ON public.domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sites_updated_at BEFORE UPDATE ON public.sites
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===== SEED DATA: Default ONI domains =====
INSERT INTO public.domains (domain, name, tld, owner, owner_key, records) VALUES
    ('helloworld.orb', 'helloworld', 'orb', 'ONI System', 'oni_root_seed', '{"A": ["127.0.0.1"], "NS": ["ns1.oni.network"]}'::jsonb),
    ('myblog.orb', 'myblog', 'orb', 'ONI System', 'oni_root_seed', '{"A": ["127.0.0.1"], "NS": ["ns1.oni.network"]}'::jsonb),
    ('docs.orb', 'docs', 'orb', 'ONI System', 'oni_root_seed', '{"A": ["127.0.0.1"], "NS": ["ns1.oni.network"]}'::jsonb)
ON CONFLICT (domain) DO NOTHING;