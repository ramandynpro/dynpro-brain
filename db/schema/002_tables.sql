CREATE TABLE IF NOT EXISTS person (
    person_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    current_role TEXT NOT NULL,
    home_location TEXT,
    timezone TEXT,
    summary TEXT,
    profile_last_updated_at TIMESTAMPTZ NOT NULL,
    profile_confidence NUMERIC(3,2) NOT NULL DEFAULT 0.50,
    source_provenance JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skill_evidence (
    evidence_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES person(person_id),
    skill_name TEXT NOT NULL,
    evidence_text TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    observed_at DATE,
    confidence NUMERIC(3,2) NOT NULL,
    embedding VECTOR(384),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assignment_project (
    project_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES person(person_id),
    project_name TEXT NOT NULL,
    client_name TEXT,
    domain TEXT,
    role_on_project TEXT,
    start_date DATE,
    end_date DATE,
    project_summary TEXT,
    confidence NUMERIC(3,2) NOT NULL,
    source_provenance JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS commercial_profile (
    commercial_profile_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL REFERENCES person(person_id),
    bill_rate_usd NUMERIC(10,2),
    cost_rate_usd NUMERIC(10,2),
    availability_percent INTEGER,
    availability_note TEXT,
    effective_from DATE,
    confidence NUMERIC(3,2) NOT NULL,
    source_provenance JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS relationship_edge (
    edge_id TEXT PRIMARY KEY,
    from_person_id TEXT NOT NULL REFERENCES person(person_id),
    to_person_id TEXT NOT NULL REFERENCES person(person_id),
    relationship_type TEXT NOT NULL,
    strength NUMERIC(3,2) NOT NULL,
    context_note TEXT,
    source_provenance JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_evidence_person_id ON skill_evidence(person_id);
CREATE INDEX IF NOT EXISTS idx_skill_evidence_skill_name ON skill_evidence(skill_name);
CREATE INDEX IF NOT EXISTS idx_skill_evidence_embedding ON skill_evidence USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_assignment_project_person_id ON assignment_project(person_id);
CREATE INDEX IF NOT EXISTS idx_assignment_project_domain ON assignment_project(domain);
CREATE INDEX IF NOT EXISTS idx_relationship_from_to ON relationship_edge(from_person_id, to_person_id);
