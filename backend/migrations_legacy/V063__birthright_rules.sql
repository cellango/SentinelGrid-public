-- Birthright rules (attribute-based) for automatic access profile assignment

CREATE TABLE IF NOT EXISTS birthright_rules (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id uuid NOT NULL,
    name text,
    attribute_key text NOT NULL,
    match_value text NOT NULL,
    access_profile_id uuid NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fk_birthright_rules_profile FOREIGN KEY (access_profile_id) REFERENCES access_profiles (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_birthright_rules_tenant ON birthright_rules (tenant_id);
CREATE INDEX IF NOT EXISTS idx_birthright_rules_attr ON birthright_rules (tenant_id, attribute_key);
