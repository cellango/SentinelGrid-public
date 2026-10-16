--
-- PostgreSQL database dump
--

-- stripped \restrict marker (psql meta command not needed for Flyway)

-- Dumped from database version 16.11 (Debian 16.11-1.pgdg12+1)
-- Dumped by pg_dump version 16.11 (Debian 16.11-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: audit; Type: SCHEMA; Schema: -; Owner: sg
--

CREATE SCHEMA audit;


ALTER SCHEMA audit OWNER TO sg;

--
-- Name: llm_training; Type: SCHEMA; Schema: -; Owner: sg
--

CREATE SCHEMA llm_training;


ALTER SCHEMA llm_training OWNER TO sg;

--
-- Name: orchestration; Type: SCHEMA; Schema: -; Owner: sg
--

CREATE SCHEMA orchestration;


ALTER SCHEMA orchestration OWNER TO sg;

--
-- Name: reporting; Type: SCHEMA; Schema: -; Owner: sg
--

CREATE SCHEMA reporting;


ALTER SCHEMA reporting OWNER TO sg;

--
-- Name: security_ops; Type: SCHEMA; Schema: -; Owner: sg
--

CREATE SCHEMA security_ops;


ALTER SCHEMA security_ops OWNER TO sg;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: check_realm_capacity(); Type: FUNCTION; Schema: public; Owner: sg
--

CREATE FUNCTION public.check_realm_capacity() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_max_tenants INT;
    v_current_count INT;
    v_realm_type VARCHAR(50);
BEGIN
    -- Get realm info
    SELECT max_tenants, tenant_count, realm_type 
    INTO v_max_tenants, v_current_count, v_realm_type
    FROM realms 
    WHERE realm_name = NEW.realm_name;
    
    -- Only check capacity for multi-tenant realms
    IF v_realm_type = 'multi_tenant' AND v_max_tenants IS NOT NULL THEN
        IF v_current_count >= v_max_tenants THEN
            RAISE EXCEPTION 'Realm % is at capacity (% / %)', 
                NEW.realm_name, v_current_count, v_max_tenants;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.check_realm_capacity() OWNER TO sg;

--
-- Name: check_vault_quota(uuid, text); Type: FUNCTION; Schema: public; Owner: sg
--

CREATE FUNCTION public.check_vault_quota(p_tenant_id uuid, p_operation text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_quota_secrets INT;
    v_quota_used INT;
    v_quota_encryption INT;
    v_quota_encryption_used INT;
BEGIN
    -- Get quota limits and current usage
    SELECT 
        quota_secrets,
        quota_secrets_used,
        quota_encryption_ops,
        quota_encryption_used
    INTO 
        v_quota_secrets,
        v_quota_used,
        v_quota_encryption,
        v_quota_encryption_used
    FROM vault_tenants
    WHERE tenant_id = p_tenant_id;
    
    -- Check if tenant exists
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    
    -- Check quota based on operation type
    IF p_operation = 'create_secret' THEN
        RETURN v_quota_used < v_quota_secrets;
    ELSIF p_operation IN ('encrypt', 'decrypt') THEN
        RETURN v_quota_encryption_used < v_quota_encryption;
    ELSE
        -- For other operations, allow by default (no quota limit)
        RETURN true;
    END IF;
END;
$$;


ALTER FUNCTION public.check_vault_quota(p_tenant_id uuid, p_operation text) OWNER TO sg;

--
-- Name: update_agent_keepalive(); Type: FUNCTION; Schema: public; Owner: sg
--

CREATE FUNCTION public.update_agent_keepalive() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Update endpoint_agents last_keepalive when new event arrives
    UPDATE endpoint_agents
    SET 
        last_keepalive = NEW.timestamp,
        status = CASE 
            WHEN status = 'pending' THEN 'active'
            WHEN status = 'disconnected' THEN 'active'
            ELSE status
        END,
        updated_at = NOW()
    WHERE id = NEW.agent_id;
    
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_agent_keepalive() OWNER TO sg;

--
-- Name: FUNCTION update_agent_keepalive(); Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON FUNCTION public.update_agent_keepalive() IS 'Automatically updates agent last_keepalive and status when events arrive';


--
-- Name: update_ai_provider_credentials_updated_at(); Type: FUNCTION; Schema: public; Owner: sg
--

CREATE FUNCTION public.update_ai_provider_credentials_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_ai_provider_credentials_updated_at() OWNER TO sg;

--
-- Name: update_customer_counts(); Type: FUNCTION; Schema: public; Owner: sg
--

CREATE FUNCTION public.update_customer_counts() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Update user count for customer
        UPDATE customers 
        SET user_count = (
            SELECT COUNT(*) 
            FROM tenants 
            WHERE customer_id = NEW.customer_id
        ),
        updated_at = now()
        WHERE id = NEW.customer_id;
        
        -- Update org count if organization is set
        IF NEW.organization_id IS NOT NULL THEN
            UPDATE customers 
            SET org_count = (
                SELECT COUNT(DISTINCT organization_id) 
                FROM tenants 
                WHERE customer_id = NEW.customer_id 
                AND organization_id IS NOT NULL
            ),
            updated_at = now()
            WHERE id = NEW.customer_id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE customers 
        SET user_count = (
            SELECT COUNT(*) 
            FROM tenants 
            WHERE customer_id = OLD.customer_id
        ),
        org_count = (
            SELECT COUNT(DISTINCT organization_id) 
            FROM tenants 
            WHERE customer_id = OLD.customer_id 
            AND organization_id IS NOT NULL
        ),
        updated_at = now()
        WHERE id = OLD.customer_id;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_customer_counts() OWNER TO sg;

--
-- Name: update_realm_tenant_count(); Type: FUNCTION; Schema: public; Owner: sg
--

CREATE FUNCTION public.update_realm_tenant_count() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE realms 
        SET tenant_count = tenant_count + 1,
            updated_at = now()
        WHERE realm_name = NEW.realm_name;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE realms 
        SET tenant_count = tenant_count - 1,
            updated_at = now()
        WHERE realm_name = OLD.realm_name;
    ELSIF TG_OP = 'UPDATE' AND OLD.realm_name IS DISTINCT FROM NEW.realm_name THEN
        -- Tenant moved to different realm
        UPDATE realms 
        SET tenant_count = tenant_count - 1,
            updated_at = now()
        WHERE realm_name = OLD.realm_name;
        
        UPDATE realms 
        SET tenant_count = tenant_count + 1,
            updated_at = now()
        WHERE realm_name = NEW.realm_name;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_realm_tenant_count() OWNER TO sg;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: sg
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO sg;

--
-- Name: update_vault_quota_usage(); Type: FUNCTION; Schema: public; Owner: sg
--

CREATE FUNCTION public.update_vault_quota_usage() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.operation = 'create_secret' AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_secrets_used = quota_secrets_used + 1,
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'INSERT' AND NEW.operation = 'delete_secret' AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_secrets_used = GREATEST(quota_secrets_used - 1, 0),
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'INSERT' AND NEW.operation IN ('encrypt', 'decrypt') AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_encryption_used = quota_encryption_used + 1,
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'INSERT' AND NEW.operation = 'generate_db_credentials' AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_db_credentials_used = quota_db_credentials_used + 1,
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'INSERT' AND NEW.operation = 'issue_certificate' AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_certificates_used = quota_certificates_used + 1,
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    END IF;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_vault_quota_usage() OWNER TO sg;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_log_statistics; Type: TABLE; Schema: audit; Owner: sg
--

CREATE TABLE audit.audit_log_statistics (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    period_start timestamp with time zone NOT NULL,
    period_end timestamp with time zone NOT NULL,
    total_events bigint DEFAULT 0,
    successful_events bigint DEFAULT 0,
    failed_events bigint DEFAULT 0,
    auth_events bigint DEFAULT 0,
    iam_events bigint DEFAULT 0,
    config_events bigint DEFAULT 0,
    data_events bigint DEFAULT 0,
    compliance_events bigint DEFAULT 0,
    unique_actors integer DEFAULT 0,
    generated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE audit.audit_log_statistics OWNER TO sg;

--
-- Name: TABLE audit_log_statistics; Type: COMMENT; Schema: audit; Owner: sg
--

COMMENT ON TABLE audit.audit_log_statistics IS 'Aggregated audit statistics for compliance reporting';


--
-- Name: audit_retention_policies; Type: TABLE; Schema: audit; Owner: sg
--

CREATE TABLE audit.audit_retention_policies (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid,
    policy_name character varying(255) NOT NULL,
    hot_retention_days integer DEFAULT 90,
    cold_retention_days integer DEFAULT 365,
    total_retention_days integer DEFAULT 2555,
    archive_enabled boolean DEFAULT false,
    archive_location text,
    requires_immutability boolean DEFAULT true,
    requires_encryption boolean DEFAULT true,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE audit.audit_retention_policies OWNER TO sg;

--
-- Name: TABLE audit_retention_policies; Type: COMMENT; Schema: audit; Owner: sg
--

COMMENT ON TABLE audit.audit_retention_policies IS 'Audit log retention policies per tenant';


--
-- Name: platform_audit_logs; Type: TABLE; Schema: audit; Owner: sg
--

CREATE TABLE audit.platform_audit_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    actor_user_id text NOT NULL,
    actor_email character varying(255),
    actor_roles text[],
    action character varying(100) NOT NULL,
    action_category character varying(50),
    resource_type character varying(100),
    resource_id text,
    resource_name text,
    before_state jsonb,
    after_state jsonb,
    changes jsonb,
    ip_address inet,
    user_agent text,
    request_id text,
    session_id text,
    success boolean DEFAULT true,
    error_message text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE audit.platform_audit_logs OWNER TO sg;

--
-- Name: TABLE platform_audit_logs; Type: COMMENT; Schema: audit; Owner: sg
--

COMMENT ON TABLE audit.platform_audit_logs IS 'Complete audit trail for all platform operations (SOC 2, NIST, HIPAA compliance)';


--
-- Name: COLUMN platform_audit_logs.before_state; Type: COMMENT; Schema: audit; Owner: sg
--

COMMENT ON COLUMN audit.platform_audit_logs.before_state IS 'State before action (for rollback and forensics)';


--
-- Name: COLUMN platform_audit_logs.after_state; Type: COMMENT; Schema: audit; Owner: sg
--

COMMENT ON COLUMN audit.platform_audit_logs.after_state IS 'State after action (for audit trail)';


--
-- Name: COLUMN platform_audit_logs.changes; Type: COMMENT; Schema: audit; Owner: sg
--

COMMENT ON COLUMN audit.platform_audit_logs.changes IS 'Specific fields that changed (for efficient auditing)';


--
-- Name: runs; Type: TABLE; Schema: llm_training; Owner: sg
--

CREATE TABLE llm_training.runs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    status text NOT NULL,
    model_name text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE llm_training.runs OWNER TO sg;

--
-- Name: scanner_registry; Type: TABLE; Schema: orchestration; Owner: sg
--

CREATE TABLE orchestration.scanner_registry (
    id text NOT NULL,
    name text NOT NULL,
    version text,
    image_digest text,
    parser text NOT NULL,
    default_limits jsonb DEFAULT '{}'::jsonb,
    metadata jsonb DEFAULT '{}'::jsonb,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE orchestration.scanner_registry OWNER TO sg;

--
-- Name: scans; Type: TABLE; Schema: orchestration; Owner: sg
--

CREATE TABLE orchestration.scans (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    scanner_id text,
    target_ref text,
    status text DEFAULT 'queued'::text NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    error text,
    raw_artifact_url text,
    summary jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE orchestration.scans OWNER TO sg;

--
-- Name: access_profile_entitlements; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.access_profile_entitlements (
    access_profile_id uuid NOT NULL,
    entitlement_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.access_profile_entitlements OWNER TO sg;

--
-- Name: TABLE access_profile_entitlements; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.access_profile_entitlements IS 'Many-to-many relationship between access profiles and entitlements';


--
-- Name: access_profiles; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.access_profiles (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    is_default boolean DEFAULT false,
    is_system boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_birthright boolean DEFAULT false NOT NULL,
    scope text DEFAULT 'all_users'::text
);


ALTER TABLE public.access_profiles OWNER TO sg;

--
-- Name: TABLE access_profiles; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.access_profiles IS 'Bundles of entitlements (e.g., "Standard Employee", "Developer")';


--
-- Name: COLUMN access_profiles.is_default; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.access_profiles.is_default IS 'Default profile assigned to new users';


--
-- Name: COLUMN access_profiles.is_system; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.access_profiles.is_system IS 'System profile that cannot be deleted';


--
-- Name: COLUMN access_profiles.is_birthright; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.access_profiles.is_birthright IS 'True when the profile is a birthright (baseline) access bundle';


--
-- Name: COLUMN access_profiles.scope; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.access_profiles.scope IS 'Scope for birthright assignment (e.g., all_users, department=Sales)';


--
-- Name: access_requests; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.access_requests (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    requested_by text NOT NULL,
    entitlement_id uuid NOT NULL,
    reason text NOT NULL,
    duration_days integer,
    status character varying(50) DEFAULT 'pending'::character varying,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    resolved_by text,
    resolution_notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    requested_for uuid,
    resource_type character varying(100) DEFAULT 'resource'::character varying NOT NULL,
    resource_id character varying(255) DEFAULT '*'::character varying NOT NULL,
    action character varying(50) DEFAULT 'read'::character varying NOT NULL,
    justification text DEFAULT ''::text NOT NULL,
    reviewer_id uuid,
    reviewed_at timestamp with time zone,
    review_comments text,
    expires_at timestamp with time zone
);


ALTER TABLE public.access_requests OWNER TO sg;

--
-- Name: TABLE access_requests; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.access_requests IS 'Self-service access requests from users';


--
-- Name: COLUMN access_requests.duration_days; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.access_requests.duration_days IS 'Temporary access duration (NULL = permanent)';


--
-- Name: access_review_campaigns; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.access_review_campaigns (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    campaign_type character varying(50) NOT NULL,
    scope jsonb,
    status character varying(50) DEFAULT 'draft'::character varying,
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    created_by text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.access_review_campaigns OWNER TO sg;

--
-- Name: TABLE access_review_campaigns; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.access_review_campaigns IS 'Access review campaigns for SOC 2 CC6.x compliance';


--
-- Name: COLUMN access_review_campaigns.campaign_type; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.access_review_campaigns.campaign_type IS 'Type: admin_review, app_access_review, role_review, all_access_review';


--
-- Name: COLUMN access_review_campaigns.scope; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.access_review_campaigns.scope IS 'JSON defining which users/roles/apps to include in review';


--
-- Name: access_review_decisions; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.access_review_decisions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    review_item_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    reviewer_user_id text NOT NULL,
    reviewer_email character varying(255),
    decision character varying(50) NOT NULL,
    justification text NOT NULL,
    ip_address inet,
    user_agent text,
    decided_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.access_review_decisions OWNER TO sg;

--
-- Name: TABLE access_review_decisions; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.access_review_decisions IS 'Audit trail of review decisions for compliance';


--
-- Name: access_review_items; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.access_review_items (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    campaign_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    reviewer_user_id text NOT NULL,
    reviewer_email character varying(255),
    reviewer_name character varying(255),
    subject_user_id text NOT NULL,
    subject_email character varying(255),
    subject_name character varying(255),
    entitlement_id uuid,
    app_id uuid,
    access_type character varying(100),
    access_name character varying(255),
    access_description text,
    decision character varying(50) DEFAULT 'pending'::character varying,
    justification text,
    reviewed_at timestamp with time zone,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.access_review_items OWNER TO sg;

--
-- Name: TABLE access_review_items; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.access_review_items IS 'Individual access items to be reviewed in campaigns';


--
-- Name: COLUMN access_review_items.decision; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.access_review_items.decision IS 'Review decision: pending, approved, revoked, escalated';


--
-- Name: access_review_statistics; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.access_review_statistics (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    campaign_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    total_items integer DEFAULT 0,
    items_reviewed integer DEFAULT 0,
    items_approved integer DEFAULT 0,
    items_revoked integer DEFAULT 0,
    items_escalated integer DEFAULT 0,
    items_pending integer DEFAULT 0,
    average_review_time_seconds integer,
    completion_percentage numeric(5,2),
    on_time_completion boolean,
    calculated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.access_review_statistics OWNER TO sg;

--
-- Name: TABLE access_review_statistics; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.access_review_statistics IS 'Campaign completion statistics for reporting';


--
-- Name: adapter_training_jobs; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.adapter_training_jobs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    job_id character varying(100) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    training_config jsonb NOT NULL,
    data_snapshot_id uuid,
    base_model_name character varying(100) NOT NULL,
    base_model_version character varying(20) NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    error_message text,
    metrics jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT valid_job_status CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('running'::character varying)::text, ('completed'::character varying)::text, ('failed'::character varying)::text, ('cancelled'::character varying)::text])))
);


ALTER TABLE public.adapter_training_jobs OWNER TO sg;

--
-- Name: TABLE adapter_training_jobs; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.adapter_training_jobs IS 'Training job tracking and status';


--
-- Name: COLUMN adapter_training_jobs.status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.adapter_training_jobs.status IS 'pending: queued, running: training, completed: success, failed: error, cancelled: aborted';


--
-- Name: adapter_version_history; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.adapter_version_history (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    adapter_version character varying(20) NOT NULL,
    adapter_path text NOT NULL,
    base_model_name character varying(100) NOT NULL,
    base_model_version character varying(20) NOT NULL,
    training_data_count integer,
    training_config jsonb,
    performance_metrics jsonb,
    status character varying(20) NOT NULL,
    trained_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.adapter_version_history OWNER TO sg;

--
-- Name: TABLE adapter_version_history; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.adapter_version_history IS 'Version history for adapters, enabling rollback';


--
-- Name: agent_bootstrap_tokens; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.agent_bootstrap_tokens (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    agent_id character varying(255),
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    created_by uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.agent_bootstrap_tokens OWNER TO sg;

--
-- Name: TABLE agent_bootstrap_tokens; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.agent_bootstrap_tokens IS 'One-time tokens for agent certificate enrollment';


--
-- Name: agent_versions; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.agent_versions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_type character varying(50) NOT NULL,
    upstream_tool character varying(50) NOT NULL,
    upstream_version character varying(50) NOT NULL,
    version character varying(50) NOT NULL,
    release_date date NOT NULL,
    download_urls jsonb NOT NULL,
    checksums jsonb NOT NULL,
    changelog text,
    is_latest boolean DEFAULT false,
    is_deprecated boolean DEFAULT false,
    end_of_life_date date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    os_compatibility jsonb DEFAULT '[]'::jsonb NOT NULL,
    status character varying(20) DEFAULT 'stable'::character varying NOT NULL,
    release_notes text,
    is_security_update boolean DEFAULT false
);


ALTER TABLE public.agent_versions OWNER TO sg;

--
-- Name: TABLE agent_versions; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.agent_versions IS 'Manages agent version information and download URLs';


--
-- Name: COLUMN agent_versions.download_urls; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.agent_versions.download_urls IS 'JSON object with platform keys (linux_rpm, linux_deb, windows, macos) and URL values';


--
-- Name: COLUMN agent_versions.checksums; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.agent_versions.checksums IS 'JSON object with platform keys and SHA256 checksum values';


--
-- Name: ai_apps; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.ai_apps (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    environment character varying(50) NOT NULL,
    description text,
    allowed_models text[],
    allow_external_providers boolean DEFAULT true,
    max_context_tokens integer DEFAULT 100000,
    api_key_hash character varying(255),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT ai_apps_environment_check CHECK (((environment)::text = ANY (ARRAY[('dev'::character varying)::text, ('staging'::character varying)::text, ('prod'::character varying)::text])))
);


ALTER TABLE public.ai_apps OWNER TO sg;

--
-- Name: TABLE ai_apps; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.ai_apps IS 'Registered AI applications using SentinelGridAIShield';


--
-- Name: ai_events; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.ai_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    ai_app_id uuid,
    user_id character varying(255),
    provider character varying(100),
    model character varying(255),
    has_pii boolean DEFAULT false,
    has_secrets boolean DEFAULT false,
    prompt_injection_suspected boolean DEFAULT false,
    policy_decision character varying(50),
    tokens_in integer DEFAULT 0,
    tokens_out integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT ai_events_policy_decision_check CHECK (((policy_decision)::text = ANY (ARRAY[('allowed'::character varying)::text, ('blocked'::character varying)::text, ('modified'::character varying)::text])))
);


ALTER TABLE public.ai_events OWNER TO sg;

--
-- Name: TABLE ai_events; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.ai_events IS 'Summary of AI events (full data in OpenSearch sg-ai-events-*)';


--
-- Name: ai_policies; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.ai_policies (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    ai_app_id uuid,
    block_pii_outbound boolean DEFAULT false,
    block_secrets_outbound boolean DEFAULT true,
    block_external_llms boolean DEFAULT false,
    block_jailbreak_patterns boolean DEFAULT true,
    require_approval_for_high_risk_tools boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.ai_policies OWNER TO sg;

--
-- Name: TABLE ai_policies; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.ai_policies IS 'Security policies for AI applications';


--
-- Name: COLUMN ai_policies.ai_app_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ai_policies.ai_app_id IS 'NULL means this is the org-wide default policy';


--
-- Name: ai_provider_credentials; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.ai_provider_credentials (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    org_id uuid NOT NULL,
    provider character varying(50) NOT NULL,
    deployment_model character varying(20) NOT NULL,
    access_method character varying(30) NOT NULL,
    vault_type character varying(20),
    vault_secret_path text,
    iam_role_arn text,
    vault_region character varying(50),
    proxy_endpoint_url text,
    proxy_auth_token_hash text,
    gateway_key_fingerprint text,
    emergency_key_fingerprint text,
    emergency_key_last_detected timestamp without time zone,
    is_active boolean DEFAULT true,
    last_validated timestamp without time zone,
    validation_error text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    created_by character varying(255),
    CONSTRAINT valid_access_method CHECK (((access_method)::text = ANY (ARRAY[('vault-delegation'::character varying)::text, ('customer-proxy'::character varying)::text, ('dual-key'::character varying)::text]))),
    CONSTRAINT valid_deployment_model CHECK (((deployment_model)::text = ANY (ARRAY[('self-hosted'::character varying)::text, ('saas'::character varying)::text]))),
    CONSTRAINT valid_provider CHECK (((provider)::text = ANY (ARRAY[('openai'::character varying)::text, ('anthropic'::character varying)::text, ('azure-openai'::character varying)::text, ('local'::character varying)::text]))),
    CONSTRAINT valid_vault_type CHECK (((vault_type IS NULL) OR ((vault_type)::text = ANY (ARRAY[('aws-secrets'::character varying)::text, ('azure-keyvault'::character varying)::text, ('hashicorp-vault'::character varying)::text]))))
);


ALTER TABLE public.ai_provider_credentials OWNER TO sg;

--
-- Name: TABLE ai_provider_credentials; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.ai_provider_credentials IS 'Configuration for accessing customer-controlled AI provider API keys. Keys are NEVER stored here - only references to customer vaults.';


--
-- Name: COLUMN ai_provider_credentials.deployment_model; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ai_provider_credentials.deployment_model IS 'Whether gateway runs in customer infra (self-hosted) or SentinelGrid infra (saas)';


--
-- Name: COLUMN ai_provider_credentials.access_method; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ai_provider_credentials.access_method IS 'How gateway accesses the key: vault-delegation (cross-account IAM), customer-proxy (customer-hosted sidecar), or dual-key (separate keys)';


--
-- Name: COLUMN ai_provider_credentials.iam_role_arn; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ai_provider_credentials.iam_role_arn IS 'AWS IAM role ARN or Azure service principal ID that gateway assumes to read secret';


--
-- Name: COLUMN ai_provider_credentials.gateway_key_fingerprint; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ai_provider_credentials.gateway_key_fingerprint IS 'First 8 chars SHA-256 hash of gateway key for identification (not security)';


--
-- Name: COLUMN ai_provider_credentials.emergency_key_last_detected; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ai_provider_credentials.emergency_key_last_detected IS 'Timestamp when emergency key usage was detected (triggers alert)';


--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.api_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id uuid,
    name character varying(255) NOT NULL,
    key_hash character varying(255) NOT NULL,
    scopes jsonb,
    rate_limit_per_minute integer DEFAULT 60,
    rate_limit_per_hour integer DEFAULT 1000,
    expires_at timestamp without time zone,
    last_used_at timestamp without time zone,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.api_keys OWNER TO sg;

--
-- Name: TABLE api_keys; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.api_keys IS 'API keys for programmatic access';


--
-- Name: app_catalog; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.app_catalog (
    id uuid NOT NULL,
    name text NOT NULL,
    display_name text NOT NULL,
    description text,
    app_type text,
    protocol text,
    category text,
    icon_url text,
    required_fields jsonb DEFAULT '[]'::jsonb,
    optional_fields jsonb DEFAULT '[]'::jsonb,
    default_config jsonb DEFAULT '{}'::jsonb,
    setup_guide text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.app_catalog OWNER TO sg;

--
-- Name: TABLE app_catalog; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.app_catalog IS 'Prebuilt app templates for SSO setup';


--
-- Name: approvals; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.approvals (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    access_request_id uuid NOT NULL,
    approver_id text NOT NULL,
    approver_type character varying(50) NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    notes text,
    approved_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.approvals OWNER TO sg;

--
-- Name: TABLE approvals; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.approvals IS 'Approval workflow for access requests';


--
-- Name: COLUMN approvals.approver_type; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.approvals.approver_type IS 'Type of approver: manager, app_owner, admin';


--
-- Name: apps; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.apps (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    app_type character varying(100) NOT NULL,
    icon_url text,
    is_active boolean DEFAULT true,
    config jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.apps OWNER TO sg;

--
-- Name: TABLE apps; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.apps IS 'Integrated applications (SentinelGrid, GitHub, AWS, Jira, etc.)';


--
-- Name: assets; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.assets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    asset_id text DEFAULT public.uuid_generate_v4(),
    asset_type text NOT NULL,
    name text,
    hostname text,
    ip_address text,
    mac_address text,
    manufacturer text,
    model text,
    serial_number text,
    hardware_specs jsonb,
    operating_system text,
    os_version text,
    installed_software jsonb,
    installed_patches jsonb,
    network_segment text,
    vlan text,
    firewall_rules jsonb,
    owner text,
    location text,
    department text,
    vulnerabilities jsonb,
    compliance_status text,
    last_scan_date timestamp with time zone,
    source text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    user_id text,
    external_id text,
    metadata jsonb DEFAULT '{}'::jsonb,
    last_seen_at timestamp with time zone
);


ALTER TABLE public.assets OWNER TO sg;

--
-- Name: TABLE assets; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.assets IS 'CMDB asset inventory (hardware, software, network)';


--
-- Name: audit_log_statistics; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.audit_log_statistics AS
 SELECT id,
    tenant_id,
    realm_name,
    period_start,
    period_end,
    total_events,
    successful_events,
    failed_events,
    auth_events,
    iam_events,
    config_events,
    data_events,
    compliance_events,
    unique_actors,
    generated_at
   FROM audit.audit_log_statistics;


ALTER VIEW public.audit_log_statistics OWNER TO sg;

--
-- Name: audit_retention_policies; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.audit_retention_policies AS
 SELECT id,
    tenant_id,
    policy_name,
    hot_retention_days,
    cold_retention_days,
    total_retention_days,
    archive_enabled,
    archive_location,
    requires_immutability,
    requires_encryption,
    is_active,
    created_at,
    updated_at
   FROM audit.audit_retention_policies;


ALTER VIEW public.audit_retention_policies OWNER TO sg;

--
-- Name: birthright_rules; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.birthright_rules (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    name text,
    attribute_key text NOT NULL,
    match_value text NOT NULL,
    access_profile_id uuid NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.birthright_rules OWNER TO sg;

--
-- Name: ca_authorities; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.ca_authorities (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    type character varying(50) NOT NULL,
    config jsonb NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id uuid,
    ca_name character varying(255),
    certificate_profile character varying(100),
    enrollment_protocols jsonb
);


ALTER TABLE public.ca_authorities OWNER TO sg;

--
-- Name: TABLE ca_authorities; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.ca_authorities IS 'Certificate Authority backends (step-ca, AWS ACM Private CA, etc.)';


--
-- Name: COLUMN ca_authorities.tenant_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ca_authorities.tenant_id IS 'Tenant ID for per-tenant CA isolation. NULL = shared CA for all tenants.';


--
-- Name: COLUMN ca_authorities.ca_name; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ca_authorities.ca_name IS 'CA name in EJBCA (e.g., SentinelGrid-Issuing-CA)';


--
-- Name: COLUMN ca_authorities.certificate_profile; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ca_authorities.certificate_profile IS 'Certificate profile name in EJBCA (e.g., service-tls)';


--
-- Name: COLUMN ca_authorities.enrollment_protocols; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.ca_authorities.enrollment_protocols IS 'Array of supported enrollment protocols: acme, scep, est';


--
-- Name: certificate_requests; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.certificate_requests (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    certificate_id uuid,
    tenant_id uuid,
    requestor_type character varying(50) NOT NULL,
    requestor_id character varying(255),
    csr_pem text,
    dns_names text[] DEFAULT ARRAY[]::text[],
    ip_addresses inet[] DEFAULT ARRAY[]::inet[],
    ttl_hours integer,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.certificate_requests OWNER TO sg;

--
-- Name: TABLE certificate_requests; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.certificate_requests IS 'Certificate enrollment requests for audit and tracking';


--
-- Name: certificates; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.certificates (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    serial_number character varying(255) NOT NULL,
    tenant_id uuid,
    subject_cn character varying(255) NOT NULL,
    dns_names text[] DEFAULT ARRAY[]::text[],
    ip_addresses inet[] DEFAULT ARRAY[]::inet[],
    spki_fingerprint character varying(255),
    usage character varying(50) NOT NULL,
    service_type character varying(100),
    agent_id character varying(255),
    ca_authority_id uuid NOT NULL,
    issued_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    revocation_reason character varying(100),
    status character varying(50) DEFAULT 'issued'::character varying NOT NULL,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.certificates OWNER TO sg;

--
-- Name: TABLE certificates; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.certificates IS 'Issued X.509 certificates with metadata';


--
-- Name: chat_messages; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.chat_messages (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    session_id uuid NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.chat_messages OWNER TO sg;

--
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.chat_sessions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    created_by_user_id text NOT NULL,
    context_type text,
    context_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.chat_sessions OWNER TO sg;

--
-- Name: compliance_controls; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.compliance_controls (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    framework_id uuid NOT NULL,
    control_id character varying(100) NOT NULL,
    control_name character varying(500) NOT NULL,
    control_description text,
    control_category character varying(100),
    parent_control_id uuid,
    is_applicable boolean DEFAULT true,
    priority character varying(50),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.compliance_controls OWNER TO sg;

--
-- Name: TABLE compliance_controls; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.compliance_controls IS 'Individual controls from each framework';


--
-- Name: compliance_frameworks; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.compliance_frameworks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    framework_code character varying(50) NOT NULL,
    framework_name character varying(255) NOT NULL,
    version character varying(50),
    description text,
    official_url text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.compliance_frameworks OWNER TO sg;

--
-- Name: TABLE compliance_frameworks; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.compliance_frameworks IS 'Supported compliance frameworks (SOC 2, NIST CSF, HIPAA, PCI DSS, CMMC)';


--
-- Name: connected_apps; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.connected_apps (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    catalog_app_id uuid,
    client_id character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255),
    protocol character varying(50) NOT NULL,
    config jsonb NOT NULL,
    is_active boolean DEFAULT true,
    connected_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    connected_by uuid,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.connected_apps OWNER TO sg;

--
-- Name: TABLE connected_apps; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.connected_apps IS 'Apps connected by tenants';


--
-- Name: control_mappings; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.control_mappings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    control_id uuid NOT NULL,
    sentinelgrid_feature character varying(255) NOT NULL,
    feature_description text,
    coverage_level character varying(50) DEFAULT 'partial'::character varying,
    implementation_notes text,
    evidence_sources text[],
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.control_mappings OWNER TO sg;

--
-- Name: TABLE control_mappings; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.control_mappings IS 'Mapping of SentinelGrid features to compliance controls';


--
-- Name: customer_cloud_accounts; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.customer_cloud_accounts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    cloud_provider character varying(50) NOT NULL,
    account_id character varying(255) NOT NULL,
    account_name character varying(255),
    integration_method character varying(50),
    monitor_role_arn character varying(512),
    external_id character varying(255),
    service_principal_id character varying(255),
    service_principal_secret_encrypted text,
    status character varying(50) DEFAULT 'pending'::character varying,
    connected_at timestamp with time zone,
    last_sync_at timestamp with time zone,
    last_scan_at timestamp with time zone,
    error_message text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    version_policy character varying(20) DEFAULT 'latest'::character varying,
    pinned_version character varying(100)
);


ALTER TABLE public.customer_cloud_accounts OWNER TO sg;

--
-- Name: TABLE customer_cloud_accounts; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.customer_cloud_accounts IS 'Stores multi-cloud account connections (AWS, Azure, GCP)';


--
-- Name: COLUMN customer_cloud_accounts.monitor_role_arn; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customer_cloud_accounts.monitor_role_arn IS 'AWS IAM Role ARN for cross-account access';


--
-- Name: COLUMN customer_cloud_accounts.external_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customer_cloud_accounts.external_id IS 'External ID for AWS cross-account role assumption';


--
-- Name: customer_endpoint_agents; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.customer_endpoint_agents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    agent_id character varying(255) NOT NULL,
    agent_type character varying(50) NOT NULL,
    hostname character varying(255),
    ip_address inet,
    os_type character varying(50),
    os_version character varying(100),
    os_arch character varying(50),
    agent_version character varying(50),
    registration_token character varying(255),
    status character varying(50) DEFAULT 'pending'::character varying,
    registered_at timestamp with time zone,
    last_seen_at timestamp with time zone,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.customer_endpoint_agents OWNER TO sg;

--
-- Name: TABLE customer_endpoint_agents; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.customer_endpoint_agents IS 'Tracks registered endpoint protection agents';


--
-- Name: COLUMN customer_endpoint_agents.agent_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customer_endpoint_agents.agent_id IS 'Unique agent identifier from Wazuh or other agent system';


--
-- Name: customer_git_providers; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.customer_git_providers (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    provider character varying(50) NOT NULL,
    provider_type character varying(50),
    organization_name character varying(255),
    access_token_encrypted text,
    webhook_url text,
    webhook_secret_encrypted text,
    status character varying(50) DEFAULT 'pending'::character varying,
    connected_at timestamp with time zone,
    last_sync_at timestamp with time zone,
    error_message text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.customer_git_providers OWNER TO sg;

--
-- Name: TABLE customer_git_providers; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.customer_git_providers IS 'Stores Git provider connection configurations';


--
-- Name: customer_idp_config; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.customer_idp_config (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    idp_type character varying(50) NOT NULL,
    config_json jsonb NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    connected_at timestamp with time zone,
    last_sync_at timestamp with time zone,
    error_message text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.customer_idp_config OWNER TO sg;

--
-- Name: TABLE customer_idp_config; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.customer_idp_config IS 'Stores identity provider connection configurations for customers';


--
-- Name: COLUMN customer_idp_config.config_json; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customer_idp_config.config_json IS 'Encrypted JSON containing OAuth tokens, client IDs/secrets, etc.';


--
-- Name: customers; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.customers (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(255) NOT NULL,
    has_dedicated_realm boolean DEFAULT false NOT NULL,
    realm_name character varying(255),
    pricing_tier character varying(50) NOT NULL,
    user_count integer DEFAULT 0 NOT NULL,
    org_count integer DEFAULT 0 NOT NULL,
    compliance_required boolean DEFAULT false NOT NULL,
    region character varying(50) DEFAULT 'us'::character varying NOT NULL,
    employee_count integer,
    industry character varying(100),
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    signup_completed boolean DEFAULT false,
    package_name character varying(50),
    user_band character varying(20),
    payment_status text DEFAULT 'pending'::text,
    billing_period text,
    stripe_customer_id text,
    stripe_subscription_id text,
    stripe_payment_method_id text,
    subscription_start_date timestamp with time zone,
    subscription_end_date timestamp with time zone,
    last_payment_date timestamp with time zone,
    next_payment_date timestamp with time zone,
    payment_amount_cents integer,
    currency text DEFAULT 'usd'::text,
    plan_tier character varying(50) DEFAULT 'protect'::character varying NOT NULL,
    CONSTRAINT customers_plan_tier_check CHECK (((plan_tier)::text = ANY (ARRAY[('protect'::character varying)::text, ('protect_defend'::character varying)::text, ('protect_defend_comply'::character varying)::text]))),
    CONSTRAINT customers_pricing_tier_check CHECK (((pricing_tier)::text = ANY (ARRAY[('free'::character varying)::text, ('starter'::character varying)::text, ('professional'::character varying)::text, ('enterprise'::character varying)::text]))),
    CONSTRAINT customers_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('suspended'::character varying)::text, ('churned'::character varying)::text])))
);


ALTER TABLE public.customers OWNER TO sg;

--
-- Name: TABLE customers; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.customers IS 'Represents a customer/company that may have multiple organizations';


--
-- Name: COLUMN customers.has_dedicated_realm; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customers.has_dedicated_realm IS 'True if customer has dedicated realm (enterprise tier or auto-upgraded)';


--
-- Name: COLUMN customers.compliance_required; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customers.compliance_required IS 'True if compliance requirements mandate dedicated realm';


--
-- Name: COLUMN customers.signup_completed; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customers.signup_completed IS 'Whether the customer has completed all signup wizard steps. If FALSE, user should be redirected to signup page to complete setup.';


--
-- Name: COLUMN customers.package_name; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customers.package_name IS 'Package name: protect or protect_comply';


--
-- Name: COLUMN customers.user_band; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.customers.user_band IS 'User band: 1-25, 26-50, 51-100, 101-250, 250+';


--
-- Name: realms; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.realms (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    realm_name character varying(255) NOT NULL,
    realm_type character varying(50) NOT NULL,
    region character varying(50) NOT NULL,
    shard_number integer,
    tenant_count integer DEFAULT 0 NOT NULL,
    max_tenants integer,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    keycloak_realm_id character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT realms_realm_type_check CHECK (((realm_type)::text = ANY (ARRAY[('platform_admin'::character varying)::text, ('multi_tenant'::character varying)::text, ('enterprise'::character varying)::text]))),
    CONSTRAINT realms_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('full'::character varying)::text, ('maintenance'::character varying)::text, ('deprecated'::character varying)::text])))
);


ALTER TABLE public.realms OWNER TO sg;

--
-- Name: TABLE realms; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.realms IS 'Tracks Keycloak realms (platform admin, multi-tenant, and enterprise)';


--
-- Name: COLUMN realms.realm_type; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.realms.realm_type IS 'Type: platform_admin (sg-admin), multi_tenant (sg-mt-*), enterprise (sg-ent-*)';


--
-- Name: COLUMN realms.shard_number; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.realms.shard_number IS 'Shard number for multi-tenant realms (e.g., sg-mt-us-1 = shard 1)';


--
-- Name: COLUMN realms.max_tenants; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.realms.max_tenants IS 'Maximum tenants for multi-tenant realms (NULL = unlimited for enterprise)';


--
-- Name: customer_summary; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.customer_summary AS
 SELECT c.id,
    c.name,
    c.slug,
    c.pricing_tier,
    c.has_dedicated_realm,
    c.realm_name,
    r.realm_type,
    c.user_count,
    c.org_count,
    c.region,
    c.compliance_required,
    c.status,
    c.created_at
   FROM (public.customers c
     LEFT JOIN public.realms r ON (((c.realm_name)::text = (r.realm_name)::text)));


ALTER VIEW public.customer_summary OWNER TO sg;

--
-- Name: cybersecurity_knowledge_base; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.cybersecurity_knowledge_base (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid,
    category character varying(50) NOT NULL,
    subcategory character varying(50),
    title text NOT NULL,
    content text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb,
    source_url text,
    framework_version character varying(20),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cybersecurity_knowledge_base OWNER TO sg;

--
-- Name: TABLE cybersecurity_knowledge_base; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.cybersecurity_knowledge_base IS 'Vector embeddings for RAG - NIST, MITRE, OWASP, CIS, CVE, and SOC playbooks. NULL tenant_id = shared knowledge, UUID = tenant-specific';


--
-- Name: data_migration_history; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.data_migration_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    migration_version character varying(20) NOT NULL,
    migration_name text NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    error_message text,
    records_loaded integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.data_migration_history OWNER TO sg;

--
-- Name: TABLE data_migration_history; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.data_migration_history IS 'Tracks data migrations that require Python scripts (e.g., generating embeddings)';


--
-- Name: COLUMN data_migration_history.migration_version; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.data_migration_history.migration_version IS 'Flyway migration version (e.g., V1.1)';


--
-- Name: COLUMN data_migration_history.status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.data_migration_history.status IS 'Migration status: pending, running, completed, failed';


--
-- Name: devices; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.devices (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    device_id text NOT NULL,
    device_type text,
    status text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.devices OWNER TO sg;

--
-- Name: endpoint_agent_events; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.endpoint_agent_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    event_type character varying(50) NOT NULL,
    severity character varying(20),
    rule_id character varying(50),
    rule_level integer,
    rule_description text,
    raw_event jsonb,
    "timestamp" timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    event_hash character varying(64),
    CONSTRAINT endpoint_agent_events_event_type_check CHECK (((event_type)::text = ANY (ARRAY[('alert'::character varying)::text, ('vulnerability'::character varying)::text, ('fim'::character varying)::text, ('rootcheck'::character varying)::text, ('sca'::character varying)::text, ('syscollector'::character varying)::text, ('other'::character varying)::text]))),
    CONSTRAINT endpoint_agent_events_severity_check CHECK (((severity)::text = ANY (ARRAY[('info'::character varying)::text, ('low'::character varying)::text, ('medium'::character varying)::text, ('high'::character varying)::text, ('critical'::character varying)::text])))
);


ALTER TABLE public.endpoint_agent_events OWNER TO sg;

--
-- Name: TABLE endpoint_agent_events; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.endpoint_agent_events IS 'Cached endpoint agent events for quick access without querying OpenSearch SIEM';


--
-- Name: COLUMN endpoint_agent_events.tenant_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agent_events.tenant_id IS 'Globally unique tenant ID for multi-tenant isolation';


--
-- Name: COLUMN endpoint_agent_events.event_type; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agent_events.event_type IS 'Event type: alert (security alert), vulnerability (CVE), fim (file integrity), rootcheck (policy check), sca (compliance), syscollector (inventory)';


--
-- Name: COLUMN endpoint_agent_events.severity; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agent_events.severity IS 'Event severity based on rule level mapping';


--
-- Name: COLUMN endpoint_agent_events.rule_level; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agent_events.rule_level IS 'Wazuh rule level: 0-15 (higher = more severe)';


--
-- Name: COLUMN endpoint_agent_events.event_hash; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agent_events.event_hash IS 'Hash for deduplication - prevents storing same event multiple times';


--
-- Name: endpoint_agents; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.endpoint_agents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    wazuh_agent_id character varying(10) NOT NULL,
    agent_name character varying(255) NOT NULL,
    ip_address inet,
    os_platform character varying(100),
    os_version character varying(100),
    agent_version character varying(50) DEFAULT '4.8.0'::character varying,
    registration_date timestamp with time zone DEFAULT now() NOT NULL,
    last_keepalive timestamp with time zone,
    status character varying(20) DEFAULT 'pending'::character varying,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT endpoint_agents_status_check CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('active'::character varying)::text, ('disconnected'::character varying)::text, ('removed'::character varying)::text])))
);


ALTER TABLE public.endpoint_agents OWNER TO sg;

--
-- Name: TABLE endpoint_agents; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.endpoint_agents IS 'SentinelGrid Endpoint Protection agents (Wazuh-based) with multi-tenant isolation';


--
-- Name: COLUMN endpoint_agents.tenant_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agents.tenant_id IS 'Globally unique tenant ID - used for Wazuh agent labels and event isolation';


--
-- Name: COLUMN endpoint_agents.wazuh_agent_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agents.wazuh_agent_id IS 'Wazuh Manager internal agent ID (e.g., 001, 002, 003)';


--
-- Name: COLUMN endpoint_agents.agent_version; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agents.agent_version IS 'Wazuh agent version (e.g., 4.8.0)';


--
-- Name: COLUMN endpoint_agents.last_keepalive; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agents.last_keepalive IS 'Last time agent sent keepalive message to manager';


--
-- Name: COLUMN endpoint_agents.status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.endpoint_agents.status IS 'Agent connection status: pending (registered but not connected), active (connected), disconnected (>15min offline), removed (deleted)';


--
-- Name: entitlement_mappings; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.entitlement_mappings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    entitlement_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    keycloak_group_id text,
    keycloak_group_name text,
    keycloak_role_name text,
    keycloak_client_id text,
    provisioning_config jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.entitlement_mappings OWNER TO sg;

--
-- Name: TABLE entitlement_mappings; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.entitlement_mappings IS 'Maps entitlements to Keycloak groups/roles and external provisioning';


--
-- Name: COLUMN entitlement_mappings.provisioning_config; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.entitlement_mappings.provisioning_config IS 'External provisioning config (e.g., GitHub API calls)';


--
-- Name: entitlements; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.entitlements (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    app_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    entitlement_type character varying(100) NOT NULL,
    is_privileged boolean DEFAULT false,
    requires_mfa boolean DEFAULT false,
    risk_level character varying(50) DEFAULT 'low'::character varying,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.entitlements OWNER TO sg;

--
-- Name: TABLE entitlements; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.entitlements IS 'Logical permissions/roles that map to Keycloak groups/roles';


--
-- Name: COLUMN entitlements.is_privileged; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.entitlements.is_privileged IS 'Requires approval for privileged roles';


--
-- Name: COLUMN entitlements.risk_level; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.entitlements.risk_level IS 'Risk level: low, medium, high, critical';


--
-- Name: evidence_collection_tasks; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.evidence_collection_tasks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    package_id uuid,
    task_name character varying(255) NOT NULL,
    task_type character varying(100),
    control_ids uuid[],
    status character varying(50) DEFAULT 'pending'::character varying,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    evidence_items_created uuid[],
    error_message text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.evidence_collection_tasks OWNER TO sg;

--
-- Name: TABLE evidence_collection_tasks; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.evidence_collection_tasks IS 'Automated evidence collection tasks';


--
-- Name: evidence_items; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.evidence_items (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    package_id uuid,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    control_id uuid,
    evidence_type character varying(100) NOT NULL,
    evidence_title character varying(500) NOT NULL,
    evidence_description text,
    file_path text,
    file_format character varying(50),
    file_size_bytes bigint,
    file_hash character varying(64),
    source_system character varying(100),
    source_reference text,
    collected_at timestamp with time zone DEFAULT now(),
    collected_by text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.evidence_items OWNER TO sg;

--
-- Name: TABLE evidence_items; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.evidence_items IS 'Individual evidence items (reports, logs, screenshots, configs)';


--
-- Name: COLUMN evidence_items.file_hash; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.evidence_items.file_hash IS 'SHA-256 hash for evidence integrity verification';


--
-- Name: evidence_packages; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.evidence_packages (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    package_name character varying(255) NOT NULL,
    framework_id uuid,
    report_period_start date NOT NULL,
    report_period_end date NOT NULL,
    created_by text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    status character varying(50) DEFAULT 'collecting'::character varying,
    export_format character varying(50),
    file_path text,
    file_size_bytes bigint,
    description text,
    metadata jsonb,
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.evidence_packages OWNER TO sg;

--
-- Name: TABLE evidence_packages; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.evidence_packages IS 'Evidence packages for compliance audits';


--
-- Name: COLUMN evidence_packages.export_format; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.evidence_packages.export_format IS 'Export format: pdf (single PDF), zip (multiple files)';


--
-- Name: findings; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.findings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    source_tool text NOT NULL,
    asset_id uuid,
    asset_type text,
    severity text,
    category text,
    title text NOT NULL,
    description text,
    remediation text,
    evidence jsonb DEFAULT '{}'::jsonb,
    raw_payload jsonb,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    scanner_id text,
    scan_id uuid,
    fingerprint text,
    tags jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.findings OWNER TO sg;

--
-- Name: fix_group_assets; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.fix_group_assets (
    fix_group_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    asset_ref text NOT NULL,
    asset_type character varying(64),
    environment character varying(32)
);


ALTER TABLE public.fix_group_assets OWNER TO sg;

--
-- Name: fix_group_cves; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.fix_group_cves (
    fix_group_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    cve_id text NOT NULL
);


ALTER TABLE public.fix_group_cves OWNER TO sg;

--
-- Name: fix_groups; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.fix_groups (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    scan_id uuid,
    type character varying(64) NOT NULL,
    description text,
    fixed_in_target text,
    priority character varying(16),
    sla_due timestamp with time zone,
    status character varying(32) DEFAULT 'open'::character varying,
    owning_team_id text,
    ai_guidance jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ticket_id text,
    ticket_status character varying(32)
);


ALTER TABLE public.fix_groups OWNER TO sg;

--
-- Name: generated_reports; Type: TABLE; Schema: reporting; Owner: sg
--

CREATE TABLE reporting.generated_reports (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    report_type character varying(100) NOT NULL,
    report_name character varying(500) NOT NULL,
    report_period_start date,
    report_period_end date,
    generated_at timestamp with time zone DEFAULT now(),
    generated_by text,
    file_path_pdf text,
    file_path_csv text,
    file_size_bytes bigint,
    status character varying(50) DEFAULT 'generating'::character varying,
    error_message text,
    llm_ingested boolean DEFAULT false,
    llm_document_id text,
    llm_ingested_at timestamp with time zone,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE reporting.generated_reports OWNER TO sg;

--
-- Name: TABLE generated_reports; Type: COMMENT; Schema: reporting; Owner: sg
--

COMMENT ON TABLE reporting.generated_reports IS 'Stored compliance reports with tenant isolation and LLM integration';


--
-- Name: COLUMN generated_reports.report_name; Type: COMMENT; Schema: reporting; Owner: sg
--

COMMENT ON COLUMN reporting.generated_reports.report_name IS 'Date-stamped filename: ReportType_YYYY-MM-DD_TenantName';


--
-- Name: generated_reports; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.generated_reports AS
 SELECT id,
    tenant_id,
    realm_name,
    report_type,
    report_name,
    report_period_start,
    report_period_end,
    generated_at,
    generated_by,
    file_path_pdf,
    file_path_csv,
    file_size_bytes,
    status,
    error_message,
    llm_ingested,
    llm_document_id,
    llm_ingested_at,
    metadata,
    created_at,
    updated_at
   FROM reporting.generated_reports;


ALTER VIEW public.generated_reports OWNER TO sg;

--
-- Name: git_repositories; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.git_repositories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    git_provider_id uuid,
    repo_name character varying(255) NOT NULL,
    repo_url text NOT NULL,
    repo_id character varying(255),
    is_public boolean DEFAULT false,
    default_branch character varying(100),
    branch_protection_enabled boolean DEFAULT false,
    code_review_required boolean DEFAULT false,
    last_scan_at timestamp with time zone,
    scan_status character varying(50),
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.git_repositories OWNER TO sg;

--
-- Name: TABLE git_repositories; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.git_repositories IS 'Inventory of customer Git repositories';


--
-- Name: git_security_findings; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.git_security_findings (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    repo_id uuid,
    finding_type character varying(50) NOT NULL,
    severity character varying(50) NOT NULL,
    title text NOT NULL,
    description text,
    file_path text,
    line_number integer,
    commit_sha character varying(40),
    commit_message text,
    author_email character varying(255),
    scanner_tool character varying(50),
    scanner_rule_id character varying(255),
    status character varying(50) DEFAULT 'open'::character varying,
    resolved_at timestamp with time zone,
    resolved_by uuid,
    remediation_notes text,
    detected_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.git_security_findings OWNER TO sg;

--
-- Name: TABLE git_security_findings; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.git_security_findings IS 'Security findings from Git repository scanning';


--
-- Name: git_security_scans; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.git_security_scans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    repo_id uuid NOT NULL,
    scan_types jsonb NOT NULL,
    branch character varying(255) NOT NULL,
    status character varying(50) DEFAULT 'queued'::character varying,
    findings_count integer DEFAULT 0,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    error text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.git_security_scans OWNER TO sg;

--
-- Name: TABLE git_security_scans; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.git_security_scans IS 'Tracks Git repository security scan jobs';


--
-- Name: COLUMN git_security_scans.scan_types; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.git_security_scans.scan_types IS 'JSON array of scan types: ["secrets", "dependencies", "code"]';


--
-- Name: hardened_images; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.hardened_images (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    os_type character varying(50) NOT NULL,
    os_version character varying(50),
    cis_level integer NOT NULL,
    cloud_provider character varying(50) NOT NULL,
    region character varying(50) NOT NULL,
    image_id character varying(255) NOT NULL,
    image_name character varying(255),
    build_date date NOT NULL,
    agent_version character varying(50),
    checksum character varying(255),
    download_url text,
    is_public boolean DEFAULT true,
    is_latest boolean DEFAULT false,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    version character varying(100) NOT NULL,
    scan_status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    scan_date timestamp with time zone,
    scan_results jsonb,
    vulnerability_count jsonb DEFAULT '{"low": 0, "high": 0, "medium": 0, "critical": 0}'::jsonb,
    status character varying(20) DEFAULT 'ready'::character varying NOT NULL,
    hardening_level character varying(50),
    hardening_script_version character varying(50),
    build_number integer,
    customer_accounts jsonb DEFAULT '[]'::jsonb,
    parent_image_version character varying(100),
    release_notes text,
    changelog text,
    CONSTRAINT check_scan_status_for_distribution CHECK (((((status)::text = 'ready'::text) AND ((scan_status)::text = 'passed'::text)) OR ((status)::text <> 'ready'::text)))
);


ALTER TABLE public.hardened_images OWNER TO sg;

--
-- Name: TABLE hardened_images; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.hardened_images IS 'Registry of CIS-hardened OS images available to customers';


--
-- Name: COLUMN hardened_images.is_latest; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.hardened_images.is_latest IS 'True for the most recent build of this OS/CIS level/region combination';


--
-- Name: iam_audit_log; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.iam_audit_log (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    action character varying(100) NOT NULL,
    actor_user_id text,
    actor_email character varying(255),
    target_user_id text,
    target_entitlement_id uuid,
    target_access_request_id uuid,
    details jsonb,
    ip_address inet,
    user_agent text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.iam_audit_log OWNER TO sg;

--
-- Name: TABLE iam_audit_log; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.iam_audit_log IS 'Audit log for all IAM operations';


--
-- Name: iam_findings; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.iam_findings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    identity_id uuid,
    finding_type character varying(100) NOT NULL,
    severity character varying(50) NOT NULL,
    description text NOT NULL,
    recommendation text,
    status character varying(50) DEFAULT 'open'::character varying NOT NULL,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    nist_control_id character varying(100),
    remediation_plan jsonb,
    remediation_status character varying(50) DEFAULT 'open'::character varying,
    remediated_at timestamp with time zone,
    remediated_by uuid,
    soc2_criteria jsonb
);


ALTER TABLE public.iam_findings OWNER TO sg;

--
-- Name: COLUMN iam_findings.nist_control_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.iam_findings.nist_control_id IS 'NIST SP 800-53 control ID associated with this finding';


--
-- Name: COLUMN iam_findings.remediation_plan; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.iam_findings.remediation_plan IS 'Structured remediation plan (steps, actions, playbook references)';


--
-- Name: COLUMN iam_findings.remediation_status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.iam_findings.remediation_status IS 'Status of remediation: open, in_progress, resolved, failed';


--
-- Name: COLUMN iam_findings.remediated_at; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.iam_findings.remediated_at IS 'Timestamp when remediation was completed';


--
-- Name: COLUMN iam_findings.remediated_by; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.iam_findings.remediated_by IS 'User ID who executed the remediation';


--
-- Name: image_customer_sharing; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.image_customer_sharing (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    image_id uuid NOT NULL,
    customer_account_id uuid NOT NULL,
    shared_at timestamp with time zone DEFAULT now() NOT NULL,
    share_status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    error_message text
);


ALTER TABLE public.image_customer_sharing OWNER TO sg;

--
-- Name: image_version_history; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.image_version_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    image_id uuid NOT NULL,
    parent_image_id uuid,
    version_from character varying(100),
    version_to character varying(100),
    change_type character varying(50),
    change_description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.image_version_history OWNER TO sg;

--
-- Name: integrations; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.integrations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    type text NOT NULL,
    name text NOT NULL,
    config jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.integrations OWNER TO sg;

--
-- Name: jml_workflow_steps; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.jml_workflow_steps (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    workflow_id uuid NOT NULL,
    step_name character varying(100) NOT NULL,
    step_type character varying(100) NOT NULL,
    step_order integer NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    duration_seconds integer,
    result_data jsonb,
    error_message text,
    retry_count integer DEFAULT 0,
    max_retries integer DEFAULT 3,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.jml_workflow_steps OWNER TO sg;

--
-- Name: TABLE jml_workflow_steps; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.jml_workflow_steps IS 'Detailed step tracking for JML workflows';


--
-- Name: jml_workflows; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.jml_workflows (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    workflow_type character varying(50) NOT NULL,
    subject_user_id text,
    target_email character varying(255) NOT NULL,
    target_name character varying(255),
    target_profile_id uuid,
    status character varying(50) DEFAULT 'pending'::character varying,
    initiated_by text NOT NULL,
    initiated_at timestamp with time zone DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    steps jsonb,
    result_user_id text,
    error_message text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.jml_workflows OWNER TO sg;

--
-- Name: TABLE jml_workflows; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.jml_workflows IS 'Joiner/Mover/Leaver workflows for user lifecycle management';


--
-- Name: COLUMN jml_workflows.workflow_type; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.jml_workflows.workflow_type IS 'Type: joiner (onboarding), mover (role change), leaver (offboarding)';


--
-- Name: COLUMN jml_workflows.steps; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.jml_workflows.steps IS 'JSON array of workflow steps configuration';


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.jobs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid,
    job_type text NOT NULL,
    status text DEFAULT 'queued'::text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb,
    attempts integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 5 NOT NULL,
    next_run_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    error text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.jobs OWNER TO sg;

--
-- Name: leads; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.leads (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email character varying(255) NOT NULL,
    company_name character varying(255) NOT NULL,
    first_name character varying(100),
    last_name character varying(100),
    password_hash character varying(255),
    user_count integer NOT NULL,
    user_band character varying(20),
    compliance_required boolean DEFAULT false,
    package_name character varying(50),
    estimated_price_cents integer,
    stripe_session_id character varying(255),
    status character varying(50) DEFAULT 'pending'::character varying,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    expires_at timestamp with time zone,
    converted_at timestamp with time zone,
    converted_to_tenant_id uuid,
    converted_to_customer_id uuid
);


ALTER TABLE public.leads OWNER TO sg;

--
-- Name: TABLE leads; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.leads IS 'Stores incomplete signups as leads before account creation';


--
-- Name: COLUMN leads.password_hash; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.leads.password_hash IS 'Hashed password stored securely, used when creating account after payment';


--
-- Name: COLUMN leads.status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.leads.status IS 'pending: just created, payment_started: checkout initiated, converted: account created, expired: cleanup candidate';


--
-- Name: COLUMN leads.expires_at; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.leads.expires_at IS 'Leads expire after 30 days if not converted';


--
-- Name: mfa_compliance_violations; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.mfa_compliance_violations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    user_id text NOT NULL,
    user_email character varying(255),
    policy_id uuid,
    violation_type character varying(100),
    violation_description text,
    status character varying(50) DEFAULT 'open'::character varying,
    resolved_at timestamp with time zone,
    resolution_notes text,
    notified_at timestamp with time zone,
    notification_count integer DEFAULT 0,
    detected_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.mfa_compliance_violations OWNER TO sg;

--
-- Name: TABLE mfa_compliance_violations; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.mfa_compliance_violations IS 'MFA compliance violations for alerting and reporting';


--
-- Name: mfa_enforcement_policies; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.mfa_enforcement_policies (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    policy_name character varying(255) NOT NULL,
    description text,
    enforcement_scope character varying(50) NOT NULL,
    target_roles text[],
    target_users text[],
    enforcement_type character varying(50) DEFAULT 'required'::character varying,
    grace_period_days integer DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.mfa_enforcement_policies OWNER TO sg;

--
-- Name: TABLE mfa_enforcement_policies; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.mfa_enforcement_policies IS 'MFA enforcement policies for SOC 2 CC6.6 compliance';


--
-- Name: COLUMN mfa_enforcement_policies.enforcement_type; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.mfa_enforcement_policies.enforcement_type IS 'Enforcement level: required, recommended, optional';


--
-- Name: model_inference_logs; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.model_inference_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    task_type text NOT NULL,
    input_ref_type text,
    input_ref_id uuid,
    model_name text NOT NULL,
    model_version text NOT NULL,
    adapter_version text,
    prompt_tokens integer,
    output_tokens integer,
    latency_ms integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.model_inference_logs OWNER TO sg;

--
-- Name: onboarding_progress; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.onboarding_progress (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    customer_id uuid NOT NULL,
    step_idp_completed boolean DEFAULT false,
    step_idp_completed_at timestamp with time zone,
    step_cloud_completed boolean DEFAULT false,
    step_cloud_completed_at timestamp with time zone,
    step_endpoint_completed boolean DEFAULT false,
    step_endpoint_completed_at timestamp with time zone,
    step_git_completed boolean DEFAULT false,
    step_git_completed_at timestamp with time zone,
    onboarding_completed boolean DEFAULT false,
    onboarding_completed_at timestamp with time zone,
    last_accessed_step integer DEFAULT 1,
    dismissed_banner boolean DEFAULT false,
    dismissed_banner_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    step_appsec_completed boolean DEFAULT false,
    step_ai_completed boolean DEFAULT false,
    step_ticketing_completed boolean DEFAULT false,
    services_selected jsonb,
    appsec_config jsonb,
    ai_config jsonb,
    ticketing_config jsonb,
    appsec_health jsonb,
    ai_health jsonb,
    ticketing_health jsonb,
    cloud_health jsonb,
    access_profile_ready boolean DEFAULT false,
    birthright_ready boolean DEFAULT false
);


ALTER TABLE public.onboarding_progress OWNER TO sg;

--
-- Name: TABLE onboarding_progress; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.onboarding_progress IS 'Tracks customer onboarding wizard progress';


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.organizations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    customer_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(255) NOT NULL,
    realm_name character varying(255) NOT NULL,
    keycloak_org_id character varying(255),
    keycloak_group_id character varying(255),
    parent_org_id uuid,
    org_type character varying(50) DEFAULT 'business_unit'::character varying NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT organizations_org_type_check CHECK (((org_type)::text = ANY (ARRAY[('subsidiary'::character varying)::text, ('business_unit'::character varying)::text, ('department'::character varying)::text, ('team'::character varying)::text]))),
    CONSTRAINT organizations_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('inactive'::character varying)::text])))
);


ALTER TABLE public.organizations OWNER TO sg;

--
-- Name: TABLE organizations; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.organizations IS 'Enterprise organizations (subsidiaries, departments) within a customer';


--
-- Name: COLUMN organizations.keycloak_org_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.organizations.keycloak_org_id IS 'Keycloak Organizations API ID (KC 25+)';


--
-- Name: COLUMN organizations.keycloak_group_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.organizations.keycloak_group_id IS 'Fallback: Keycloak group ID if not using Organizations feature';


--
-- Name: phishing_observables; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.phishing_observables (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    phishing_report_id uuid NOT NULL,
    observable_type text NOT NULL,
    observable_value text NOT NULL,
    observable_context text,
    threat_intel jsonb,
    reputation_score integer,
    is_malicious boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.phishing_observables OWNER TO sg;

--
-- Name: TABLE phishing_observables; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.phishing_observables IS 'Indicators of compromise extracted from phishing emails';


--
-- Name: phishing_reports; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.phishing_reports (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    message_id text NOT NULL,
    subject text,
    from_address text NOT NULL,
    to_address text NOT NULL,
    reply_to text,
    received_date timestamp with time zone NOT NULL,
    reported_by text,
    raw_email text NOT NULL,
    html_body text,
    text_body text,
    attachments jsonb,
    classification text,
    classification_confidence numeric(5,2),
    classified_by text,
    classified_at timestamp with time zone,
    ai_analysis jsonb,
    ai_summary text,
    ai_recommended_actions jsonb,
    mitre_tactics jsonb,
    mitre_techniques jsonb,
    nist_controls jsonb,
    status text DEFAULT 'new'::text NOT NULL,
    severity text,
    assigned_to text,
    ticket_id uuid,
    incident_id uuid,
    similar_emails jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.phishing_reports OWNER TO sg;

--
-- Name: TABLE phishing_reports; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.phishing_reports IS 'Phishing email reports submitted by users';


--
-- Name: COLUMN phishing_reports.message_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.phishing_reports.message_id IS 'RFC 822 Message-ID header value';


--
-- Name: COLUMN phishing_reports.reported_by; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.phishing_reports.reported_by IS 'Email address of the user who reported the phishing email';


--
-- Name: COLUMN phishing_reports.raw_email; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.phishing_reports.raw_email IS 'Full RFC 822 email content';


--
-- Name: COLUMN phishing_reports.classification; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.phishing_reports.classification IS 'AI or analyst classification: phishing, benign, suspicious, or pending';


--
-- Name: COLUMN phishing_reports.ai_analysis; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.phishing_reports.ai_analysis IS 'Complete AI analysis response including reasoning and recommendations';


--
-- Name: platform_audit_logs; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.platform_audit_logs AS
 SELECT id,
    tenant_id,
    realm_name,
    "timestamp",
    actor_user_id,
    actor_email,
    actor_roles,
    action,
    action_category,
    resource_type,
    resource_id,
    resource_name,
    before_state,
    after_state,
    changes,
    ip_address,
    user_agent,
    request_id,
    session_id,
    success,
    error_message,
    metadata,
    created_at
   FROM audit.platform_audit_logs;


ALTER VIEW public.platform_audit_logs OWNER TO sg;

--
-- Name: playbook_analyzers; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.playbook_analyzers (
    id uuid NOT NULL,
    playbook_id uuid NOT NULL,
    node_id character varying(255) NOT NULL,
    analyzer_id character varying(255) NOT NULL,
    observable_node_id character varying(255) NOT NULL,
    parameters json,
    created_at timestamp without time zone
);


ALTER TABLE public.playbook_analyzers OWNER TO sg;

--
-- Name: playbook_execution_audit; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.playbook_execution_audit (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    execution_id uuid NOT NULL,
    incident_id uuid NOT NULL,
    playbook_id uuid NOT NULL,
    playbook_version text,
    node_id text,
    node_type text,
    started_at timestamp with time zone NOT NULL,
    completed_at timestamp with time zone,
    status text NOT NULL,
    input_data jsonb,
    output_data jsonb,
    error_message text,
    execution_order integer,
    created_by text
);


ALTER TABLE public.playbook_execution_audit OWNER TO sg;

--
-- Name: TABLE playbook_execution_audit; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.playbook_execution_audit IS 'Detailed audit of every playbook node execution';


--
-- Name: playbook_executions; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.playbook_executions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    playbook_id uuid NOT NULL,
    target_type text NOT NULL,
    target_id uuid NOT NULL,
    status text NOT NULL,
    workflow_exec_id text,
    triggered_by text NOT NULL,
    approval_status text DEFAULT 'pending'::text NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    result_summary text,
    logs jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    alert_id uuid,
    trigger_rule_id uuid,
    CONSTRAINT ck_playbook_executions_approval_status CHECK ((approval_status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text])))
);


ALTER TABLE public.playbook_executions OWNER TO sg;

--
-- Name: COLUMN playbook_executions.triggered_by; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbook_executions.triggered_by IS 'How this playbook was triggered: manual, rule, alert, scheduled';


--
-- Name: COLUMN playbook_executions.alert_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbook_executions.alert_id IS 'Alert that triggered this playbook execution (if applicable)';


--
-- Name: COLUMN playbook_executions.trigger_rule_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbook_executions.trigger_rule_id IS 'Playbook that triggered this execution (for cascading playbooks)';


--
-- Name: playbook_observables; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.playbook_observables (
    id uuid NOT NULL,
    playbook_id uuid NOT NULL,
    node_id character varying(255) NOT NULL,
    data_type character varying(50) NOT NULL,
    extraction_path text,
    tags text[],
    mark_as_ioc boolean,
    created_at timestamp without time zone
);


ALTER TABLE public.playbook_observables OWNER TO sg;

--
-- Name: playbooks; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.playbooks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    key text NOT NULL,
    name text NOT NULL,
    description text,
    target_type text NOT NULL,
    severity_filter jsonb,
    category_filter jsonb,
    workflow_ref text NOT NULL,
    requires_approval boolean DEFAULT true NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    trigger_conditions jsonb,
    auto_trigger_enabled boolean DEFAULT false,
    trigger_priority integer DEFAULT 0,
    playbook_key character varying(255),
    is_builtin boolean DEFAULT false,
    severity_default character varying(50),
    applicable_sources text[] DEFAULT ARRAY[]::text[],
    triggers text[] DEFAULT ARRAY[]::text[],
    prerequisites text[] DEFAULT ARRAY[]::text[],
    artifacts_required text[] DEFAULT ARRAY[]::text[],
    phases jsonb,
    cis_controls text[] DEFAULT ARRAY[]::text[],
    is_template boolean DEFAULT false,
    template_key text,
    category character varying(50),
    version character varying(50) DEFAULT '1.0.0'::character varying,
    workflow jsonb DEFAULT '{"edges": [], "nodes": []}'::jsonb,
    timeout_seconds integer DEFAULT 3600,
    retry_policy jsonb,
    on_failure character varying(50) DEFAULT 'fail'::character varying,
    tags text[] DEFAULT ARRAY[]::text[],
    nist_controls text[] DEFAULT ARRAY[]::text[],
    mitre_tactics text[] DEFAULT ARRAY[]::text[],
    mitre_techniques text[] DEFAULT ARRAY[]::text[],
    n8n_workflow_id character varying(255),
    n8n_webhook_url text,
    created_by uuid,
    soc2_criteria text[] DEFAULT ARRAY[]::text[]
);


ALTER TABLE public.playbooks OWNER TO sg;

--
-- Name: COLUMN playbooks.key; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.key IS 'Unique identifier for built-in playbooks (e.g., PHISH-USER-REPORTED-v1)';


--
-- Name: COLUMN playbooks.trigger_conditions; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.trigger_conditions IS 'Alert criteria for automatic playbook triggering (e.g., severity, category, source)';


--
-- Name: COLUMN playbooks.auto_trigger_enabled; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.auto_trigger_enabled IS 'Whether this playbook should be automatically triggered when conditions match';


--
-- Name: COLUMN playbooks.trigger_priority; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.trigger_priority IS 'Priority for trigger evaluation (higher = evaluated first)';


--
-- Name: COLUMN playbooks.playbook_key; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.playbook_key IS 'Unique identifier for built-in playbooks (e.g., PHISH-USER-REPORTED-v1)';


--
-- Name: COLUMN playbooks.is_builtin; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.is_builtin IS 'True for SentinelGrid built-in playbooks that cannot be deleted (but can be cloned)';


--
-- Name: COLUMN playbooks.severity_default; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.severity_default IS 'Default severity level for incidents handled by this playbook';


--
-- Name: COLUMN playbooks.applicable_sources; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.applicable_sources IS 'List of data sources this playbook applies to (e.g., email, siem, edr)';


--
-- Name: COLUMN playbooks.triggers; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.triggers IS 'List of trigger conditions that activate this playbook';


--
-- Name: COLUMN playbooks.prerequisites; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.prerequisites IS 'List of prerequisites required to use this playbook';


--
-- Name: COLUMN playbooks.artifacts_required; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.artifacts_required IS 'List of artifacts required for this playbook';


--
-- Name: COLUMN playbooks.phases; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.phases IS 'NIST IR phases structure with steps (Detection & Analysis, Containment, etc.)';


--
-- Name: COLUMN playbooks.cis_controls; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.cis_controls IS 'CIS Controls mapped to this playbook';


--
-- Name: COLUMN playbooks.soc2_criteria; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.playbooks.soc2_criteria IS 'SOC 2 Common Criteria mapped to this playbook (e.g., {CC6.1,CC7.1}).';


--
-- Name: policies; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.policies (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    policy_type character varying(100) NOT NULL,
    scope character varying(100) DEFAULT 'tenant'::character varying NOT NULL,
    scope_id uuid,
    policy_data jsonb NOT NULL,
    is_active boolean DEFAULT true,
    priority integer DEFAULT 100,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by text,
    is_template boolean DEFAULT false,
    approval_required boolean DEFAULT false,
    approval_status text DEFAULT 'approved'::text,
    CONSTRAINT ck_policies_approval_status CHECK ((approval_status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text])))
);


ALTER TABLE public.policies OWNER TO sg;

--
-- Name: TABLE policies; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.policies IS 'Tenant-specific policy instances (sign-on, access, approval, SoD)';


--
-- Name: COLUMN policies.scope; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.policies.scope IS 'Policy scope: tenant (global), app (per-app), entitlement (per-entitlement)';


--
-- Name: COLUMN policies.policy_data; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.policies.policy_data IS 'Policy DSL JSON with conditions and actions';


--
-- Name: COLUMN policies.priority; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.policies.priority IS 'Lower number = higher priority (evaluated first)';


--
-- Name: policy_conflicts; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.policy_conflicts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    policy_id_1 uuid NOT NULL,
    policy_id_2 uuid NOT NULL,
    conflict_type character varying(100) NOT NULL,
    description text,
    severity character varying(50) DEFAULT 'medium'::character varying,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    resolved_by text
);


ALTER TABLE public.policy_conflicts OWNER TO sg;

--
-- Name: TABLE policy_conflicts; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.policy_conflicts IS 'Detected conflicts between policies';


--
-- Name: policy_evaluations; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.policy_evaluations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    policy_id uuid NOT NULL,
    evaluation_type character varying(100) NOT NULL,
    context jsonb NOT NULL,
    result character varying(50) NOT NULL,
    matched_rules jsonb,
    actions_taken jsonb,
    evaluated_at timestamp with time zone DEFAULT now() NOT NULL,
    decision_trace jsonb
);


ALTER TABLE public.policy_evaluations OWNER TO sg;

--
-- Name: TABLE policy_evaluations; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.policy_evaluations IS 'Audit log of policy evaluations';


--
-- Name: COLUMN policy_evaluations.context; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.policy_evaluations.context IS 'Evaluation context: {user_id, resource, ip, country, risk_score, etc.}';


--
-- Name: COLUMN policy_evaluations.matched_rules; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.policy_evaluations.matched_rules IS 'Array of rule IDs that matched during evaluation';


--
-- Name: policy_rules; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.policy_rules (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    policy_id uuid NOT NULL,
    rule_id character varying(255) NOT NULL,
    name character varying(255),
    description text,
    conditions jsonb NOT NULL,
    actions jsonb NOT NULL,
    priority integer DEFAULT 100,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.policy_rules OWNER TO sg;

--
-- Name: TABLE policy_rules; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.policy_rules IS 'Individual rules within policies (for indexing and analysis)';


--
-- Name: COLUMN policy_rules.conditions; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.policy_rules.conditions IS 'Array of condition objects: [{type, op, value}, ...]';


--
-- Name: COLUMN policy_rules.actions; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.policy_rules.actions IS 'Array of action objects: [{type, value, params}, ...]';


--
-- Name: policy_templates; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.policy_templates (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    policy_type character varying(100) NOT NULL,
    template_data jsonb NOT NULL,
    is_system boolean DEFAULT false,
    category character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_id uuid
);


ALTER TABLE public.policy_templates OWNER TO sg;

--
-- Name: TABLE policy_templates; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.policy_templates IS 'Pre-built policy templates for common scenarios';


--
-- Name: posture_findings; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.posture_findings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    cloud_account_id uuid,
    scan_id uuid,
    check_id character varying(255),
    title character varying(500) NOT NULL,
    description text NOT NULL,
    severity character varying(50) NOT NULL,
    resource_id character varying(500),
    service character varying(100),
    category character varying(100),
    framework character varying(100),
    remediation text,
    status character varying(50) DEFAULT 'open'::character varying NOT NULL,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    nist_control_id character varying(100),
    remediation_plan jsonb,
    remediation_status character varying(50) DEFAULT 'open'::character varying,
    remediated_at timestamp with time zone,
    remediated_by uuid,
    soc2_criteria jsonb
);


ALTER TABLE public.posture_findings OWNER TO sg;

--
-- Name: COLUMN posture_findings.nist_control_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.posture_findings.nist_control_id IS 'NIST SP 800-53 control ID associated with this finding';


--
-- Name: COLUMN posture_findings.remediation_plan; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.posture_findings.remediation_plan IS 'Structured remediation plan (steps, actions, playbook references)';


--
-- Name: COLUMN posture_findings.remediation_status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.posture_findings.remediation_status IS 'Status of remediation: open, in_progress, resolved, failed';


--
-- Name: COLUMN posture_findings.remediated_at; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.posture_findings.remediated_at IS 'Timestamp when remediation was completed';


--
-- Name: COLUMN posture_findings.remediated_by; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.posture_findings.remediated_by IS 'User ID who executed the remediation';


--
-- Name: privileged_access_approvals; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.privileged_access_approvals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    request_id uuid NOT NULL,
    approver_id uuid NOT NULL,
    status character varying(50) DEFAULT 'pending'::character varying,
    comments text,
    approved_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.privileged_access_approvals OWNER TO sg;

--
-- Name: TABLE privileged_access_approvals; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.privileged_access_approvals IS 'Approval workflow for privileged access';


--
-- Name: privileged_access_requests; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.privileged_access_requests (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    requested_by uuid NOT NULL,
    resource_type character varying(100) NOT NULL,
    resource_id character varying(255) NOT NULL,
    resource_name character varying(255),
    reason text NOT NULL,
    duration_hours integer DEFAULT 1,
    status character varying(50) DEFAULT 'pending'::character varying,
    requested_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    approved_at timestamp without time zone,
    approved_by uuid,
    rejected_at timestamp without time zone,
    rejected_by uuid,
    rejection_reason text,
    expires_at timestamp without time zone,
    revoked_at timestamp without time zone,
    revoked_by uuid,
    metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.privileged_access_requests OWNER TO sg;

--
-- Name: TABLE privileged_access_requests; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.privileged_access_requests IS 'Privileged access requests with approval workflow';


--
-- Name: realm_audit_log; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.realm_audit_log (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    realm_name character varying(255) NOT NULL,
    customer_id uuid,
    organization_id uuid,
    action character varying(100) NOT NULL,
    actor_user_id text,
    actor_email character varying(255),
    details jsonb,
    ip_address inet,
    user_agent text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.realm_audit_log OWNER TO sg;

--
-- Name: TABLE realm_audit_log; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.realm_audit_log IS 'Audit log for all realm-related security events';


--
-- Name: COLUMN realm_audit_log.action; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.realm_audit_log.action IS 'Action type: create, update, delete, user_login, user_logout, user_signup, token_refresh';


--
-- Name: realm_capacity_history; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.realm_capacity_history (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    realm_name character varying(255) NOT NULL,
    tenant_count integer NOT NULL,
    user_count integer NOT NULL,
    utilization_percent numeric(5,2),
    recorded_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.realm_capacity_history OWNER TO sg;

--
-- Name: TABLE realm_capacity_history; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.realm_capacity_history IS 'Historical tracking of realm capacity for analytics';


--
-- Name: realm_status; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.realm_status AS
 SELECT id,
    realm_name,
    realm_type,
    region,
    shard_number,
    tenant_count,
    max_tenants,
        CASE
            WHEN (max_tenants IS NULL) THEN NULL::numeric
            ELSE round((((tenant_count)::numeric / (max_tenants)::numeric) * (100)::numeric), 2)
        END AS utilization_percent,
    status,
    created_at,
    updated_at
   FROM public.realms r;


ALTER VIEW public.realm_status OWNER TO sg;

--
-- Name: remediation_metadata; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.remediation_metadata (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    finding_id uuid NOT NULL,
    finding_type character varying(50) NOT NULL,
    playbook_execution_id uuid,
    remediation_plan jsonb,
    status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.remediation_metadata OWNER TO sg;

--
-- Name: TABLE remediation_metadata; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.remediation_metadata IS 'Metadata for remediation actions - links findings to playbook executions (metadata only, no duplication)';


--
-- Name: report_access_log; Type: TABLE; Schema: reporting; Owner: sg
--

CREATE TABLE reporting.report_access_log (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    report_id uuid,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    user_id text NOT NULL,
    user_email character varying(255),
    access_type character varying(50) NOT NULL,
    accessed_at timestamp with time zone DEFAULT now(),
    ip_address inet,
    metadata jsonb
);


ALTER TABLE reporting.report_access_log OWNER TO sg;

--
-- Name: TABLE report_access_log; Type: COMMENT; Schema: reporting; Owner: sg
--

COMMENT ON TABLE reporting.report_access_log IS 'Audit log for report viewing and downloading (compliance requirement)';


--
-- Name: report_access_log; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.report_access_log AS
 SELECT id,
    report_id,
    tenant_id,
    realm_name,
    user_id,
    user_email,
    access_type,
    accessed_at,
    ip_address,
    metadata
   FROM reporting.report_access_log;


ALTER VIEW public.report_access_log OWNER TO sg;

--
-- Name: report_llm_documents; Type: TABLE; Schema: reporting; Owner: sg
--

CREATE TABLE reporting.report_llm_documents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    report_id uuid,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    chunk_index integer DEFAULT 0,
    content_preview text,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE reporting.report_llm_documents OWNER TO sg;

--
-- Name: TABLE report_llm_documents; Type: COMMENT; Schema: reporting; Owner: sg
--

COMMENT ON TABLE reporting.report_llm_documents IS 'Vector DB document references for report Q&A with tenant isolation';


--
-- Name: report_llm_documents; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.report_llm_documents AS
 SELECT id,
    report_id,
    tenant_id,
    realm_name,
    chunk_index,
    content_preview,
    created_at
   FROM reporting.report_llm_documents;


ALTER VIEW public.report_llm_documents OWNER TO sg;

--
-- Name: report_schedules; Type: TABLE; Schema: reporting; Owner: sg
--

CREATE TABLE reporting.report_schedules (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    report_type character varying(100) NOT NULL,
    schedule_name character varying(255),
    cron_expression character varying(100),
    timezone character varying(50) DEFAULT 'UTC'::character varying,
    recipients text[],
    is_active boolean DEFAULT true,
    last_run_at timestamp with time zone,
    next_run_at timestamp with time zone,
    last_run_status character varying(50),
    last_report_id uuid,
    created_by text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE reporting.report_schedules OWNER TO sg;

--
-- Name: TABLE report_schedules; Type: COMMENT; Schema: reporting; Owner: sg
--

COMMENT ON TABLE reporting.report_schedules IS 'Automated report generation schedules per tenant';


--
-- Name: COLUMN report_schedules.cron_expression; Type: COMMENT; Schema: reporting; Owner: sg
--

COMMENT ON COLUMN reporting.report_schedules.cron_expression IS 'Cron expression for scheduling (e.g., 0 9 * * MON)';


--
-- Name: report_schedules; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.report_schedules AS
 SELECT id,
    tenant_id,
    realm_name,
    report_type,
    schedule_name,
    cron_expression,
    timezone,
    recipients,
    is_active,
    last_run_at,
    next_run_at,
    last_run_status,
    last_report_id,
    created_by,
    created_at,
    updated_at
   FROM reporting.report_schedules;


ALTER VIEW public.report_schedules OWNER TO sg;

--
-- Name: report_shares; Type: TABLE; Schema: reporting; Owner: sg
--

CREATE TABLE reporting.report_shares (
    id character varying NOT NULL,
    report_id character varying NOT NULL,
    tenant_id character varying NOT NULL,
    share_token character varying NOT NULL,
    expires_at timestamp without time zone,
    password_hash character varying,
    access_count integer DEFAULT 0,
    last_accessed_at timestamp without time zone,
    created_by character varying,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE reporting.report_shares OWNER TO sg;

--
-- Name: report_shares; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.report_shares AS
 SELECT id,
    report_id,
    tenant_id,
    share_token,
    expires_at,
    password_hash,
    access_count,
    last_accessed_at,
    created_by,
    created_at
   FROM reporting.report_shares;


ALTER VIEW public.report_shares OWNER TO sg;

--
-- Name: report_templates; Type: TABLE; Schema: reporting; Owner: sg
--

CREATE TABLE reporting.report_templates (
    id character varying NOT NULL,
    tenant_id character varying,
    name character varying NOT NULL,
    description text,
    type character varying NOT NULL,
    sections json NOT NULL,
    data_queries json,
    schedule json,
    required_roles json,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE reporting.report_templates OWNER TO sg;

--
-- Name: report_templates; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.report_templates AS
 SELECT id,
    tenant_id,
    name,
    description,
    type,
    sections,
    data_queries,
    schedule,
    required_roles,
    created_at,
    updated_at
   FROM reporting.report_templates;


ALTER VIEW public.report_templates OWNER TO sg;

--
-- Name: reports; Type: TABLE; Schema: reporting; Owner: sg
--

CREATE TABLE reporting.reports (
    id character varying NOT NULL,
    tenant_id character varying NOT NULL,
    template_id character varying,
    name character varying NOT NULL,
    format character varying NOT NULL,
    status character varying NOT NULL,
    generated_at timestamp without time zone DEFAULT now(),
    generated_by character varying,
    date_range_start timestamp without time zone,
    date_range_end timestamp without time zone,
    file_path character varying,
    file_size_bytes integer,
    download_url character varying,
    sections json,
    metadata json,
    error_message text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE reporting.reports OWNER TO sg;

--
-- Name: reports; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.reports AS
 SELECT id,
    tenant_id,
    template_id,
    name,
    format,
    status,
    generated_at,
    generated_by,
    date_range_start,
    date_range_end,
    file_path,
    file_size_bytes,
    download_url,
    sections,
    metadata,
    error_message,
    created_at,
    updated_at
   FROM reporting.reports;


ALTER VIEW public.reports OWNER TO sg;

--
-- Name: scans; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.scans (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    scanner_id character varying(128),
    target_ref text,
    status character varying(32) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    summary jsonb,
    raw_artifact_url text
);


ALTER TABLE public.scans OWNER TO sg;

--
-- Name: secrets; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.secrets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    secret_type character varying(50) NOT NULL,
    encrypted_value text NOT NULL,
    vault_path character varying(500),
    access_control jsonb,
    rotation_policy jsonb,
    last_rotated_at timestamp without time zone,
    next_rotation_at timestamp without time zone,
    created_by uuid,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.secrets OWNER TO sg;

--
-- Name: TABLE secrets; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.secrets IS 'Shared secrets and credentials (encrypted)';


--
-- Name: security_event_embeddings; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.security_event_embeddings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    source text NOT NULL,
    agent_id text,
    host_id text,
    os_id_ref text NOT NULL,
    "timestamp" timestamp with time zone NOT NULL,
    summary text NOT NULL,
    fields jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    embedding public.vector(384)
);


ALTER TABLE public.security_event_embeddings OWNER TO sg;

--
-- Name: tenant_control_status; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.tenant_control_status (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    control_id uuid NOT NULL,
    implementation_status character varying(50) DEFAULT 'not_implemented'::character varying,
    implementation_percentage integer DEFAULT 0,
    evidence_collected boolean DEFAULT false,
    evidence_ids uuid[],
    last_assessed_at timestamp with time zone,
    assessed_by text,
    assessment_notes text,
    gaps_identified text[],
    action_items text[],
    target_completion_date date,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.tenant_control_status OWNER TO sg;

--
-- Name: TABLE tenant_control_status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.tenant_control_status IS 'Per-tenant implementation status of compliance controls';


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.tenants (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    slug text NOT NULL,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    realm_name character varying(255),
    customer_id uuid,
    organization_id uuid,
    pricing_tier character varying(50),
    realm_strategy character varying(50),
    keycloak_org_id character varying(255),
    keycloak_group_id character varying(255),
    region character varying(50) DEFAULT 'us'::character varying,
    incident_management_mode text DEFAULT 'saas_managed'::text NOT NULL,
    services_selected jsonb,
    ticketing_provider text DEFAULT 'internal'::text,
    ticketing_project text,
    package_name character varying(50),
    plan_tier character varying(50) DEFAULT 'protect'::character varying NOT NULL,
    CONSTRAINT tenants_plan_tier_check CHECK (((plan_tier)::text = ANY (ARRAY[('protect'::character varying)::text, ('protect_defend'::character varying)::text, ('protect_defend_comply'::character varying)::text]))),
    CONSTRAINT tenants_realm_strategy_check CHECK (((realm_strategy)::text = ANY (ARRAY[('shared'::character varying)::text, ('dedicated'::character varying)::text])))
);


ALTER TABLE public.tenants OWNER TO sg;

--
-- Name: COLUMN tenants.incident_management_mode; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenants.incident_management_mode IS 'Incident handling mode: saas_managed or customer_managed';


--
-- Name: COLUMN tenants.services_selected; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenants.services_selected IS 'Selected services/add-ons captured during signup';


--
-- Name: COLUMN tenants.ticketing_provider; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenants.ticketing_provider IS 'Ticketing system preference: internal, jira, servicenow';


--
-- Name: COLUMN tenants.ticketing_project; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenants.ticketing_project IS 'Project/key/queue identifier for the chosen ticketing system';


--
-- Name: COLUMN tenants.package_name; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenants.package_name IS 'Package name: protect or protect_comply';


--
-- Name: tenant_details; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.tenant_details AS
 SELECT t.id AS tenant_id,
    t.name AS tenant_name,
    t.slug AS tenant_slug,
    t.realm_name,
    t.region,
    c.id AS customer_id,
    c.name AS customer_name,
    c.pricing_tier,
    o.id AS organization_id,
    o.name AS organization_name,
    o.org_type,
    r.realm_type,
    t.status,
    t.created_at
   FROM (((public.tenants t
     LEFT JOIN public.customers c ON ((t.customer_id = c.id)))
     LEFT JOIN public.organizations o ON ((t.organization_id = o.id)))
     LEFT JOIN public.realms r ON (((t.realm_name)::text = (r.realm_name)::text)));


ALTER VIEW public.tenant_details OWNER TO sg;

--
-- Name: tenant_detection_monitors; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.tenant_detection_monitors (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    rule_id uuid NOT NULL,
    rule_version text NOT NULL,
    opensearch_monitor_id text NOT NULL,
    opensearch_destination_id text,
    is_enabled boolean DEFAULT true,
    custom_config jsonb,
    deployed_at timestamp with time zone DEFAULT now(),
    last_updated timestamp with time zone DEFAULT now(),
    approval_status text DEFAULT 'approved'::text,
    CONSTRAINT ck_tenant_detection_monitors_approval_status CHECK ((approval_status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text])))
);


ALTER TABLE public.tenant_detection_monitors OWNER TO sg;

--
-- Name: TABLE tenant_detection_monitors; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.tenant_detection_monitors IS 'Tracks which monitors are deployed to which tenants';


--
-- Name: COLUMN tenant_detection_monitors.opensearch_monitor_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenant_detection_monitors.opensearch_monitor_id IS 'Monitor ID from OpenSearch Alerting API';


--
-- Name: tenant_model_adapters; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.tenant_model_adapters (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    adapter_version character varying(20) DEFAULT 'v1'::character varying NOT NULL,
    adapter_path text NOT NULL,
    base_model_name character varying(100) NOT NULL,
    base_model_version character varying(20) NOT NULL,
    training_data_count integer DEFAULT 0,
    training_config jsonb,
    trained_at timestamp with time zone,
    performance_metrics jsonb,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT valid_status CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('training'::character varying)::text, ('failed'::character varying)::text, ('deprecated'::character varying)::text])))
);


ALTER TABLE public.tenant_model_adapters OWNER TO sg;

--
-- Name: TABLE tenant_model_adapters; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.tenant_model_adapters IS 'Metadata for per-tenant LoRA adapters';


--
-- Name: COLUMN tenant_model_adapters.status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenant_model_adapters.status IS 'active: current adapter, training: being trained, failed: training failed, deprecated: old version';


--
-- Name: tenant_provisioning_log; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.tenant_provisioning_log (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid,
    customer_id uuid,
    event_type character varying(50) NOT NULL,
    realm_name character varying(255),
    details jsonb,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by character varying(255),
    CONSTRAINT tenant_provisioning_log_event_type_check CHECK (((event_type)::text = ANY (ARRAY[('provision_start'::character varying)::text, ('provision_success'::character varying)::text, ('provision_failure'::character varying)::text, ('realm_assigned'::character varying)::text, ('org_created'::character varying)::text, ('user_created'::character varying)::text])))
);


ALTER TABLE public.tenant_provisioning_log OWNER TO sg;

--
-- Name: TABLE tenant_provisioning_log; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.tenant_provisioning_log IS 'Audit log for tenant provisioning events';


--
-- Name: tenant_training_data; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.tenant_training_data (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    module character varying(50) NOT NULL,
    data_type character varying(50) NOT NULL,
    raw_data jsonb NOT NULL,
    processed_data jsonb,
    tags text[] DEFAULT '{}'::text[],
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tenant_training_data OWNER TO sg;

--
-- Name: TABLE tenant_training_data; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.tenant_training_data IS 'Stores raw and processed training data per tenant, isolated by tenant_id';


--
-- Name: COLUMN tenant_training_data.data_type; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenant_training_data.data_type IS 'Type: qa_pair, incident, log, document, policy, playbook, alert, query';


--
-- Name: COLUMN tenant_training_data.processed_data; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.tenant_training_data.processed_data IS 'Preprocessed data ready for training (e.g., formatted Q&A pairs)';


--
-- Name: tool_registry; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.tool_registry (
    id text NOT NULL,
    name text NOT NULL,
    category text NOT NULL,
    job_types text[] DEFAULT '{}'::text[] NOT NULL,
    image text NOT NULL,
    command_template jsonb NOT NULL,
    parser_key text NOT NULL,
    severity_map jsonb DEFAULT '{}'::jsonb,
    tags text[] DEFAULT '{}'::text[],
    status text DEFAULT 'active'::text NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tool_registry OWNER TO sg;

--
-- Name: training_data_snapshots; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.training_data_snapshots (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    snapshot_name character varying(200),
    module character varying(50),
    data_type character varying(50),
    filter_criteria jsonb,
    sample_count integer,
    export_path text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.training_data_snapshots OWNER TO sg;

--
-- Name: TABLE training_data_snapshots; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.training_data_snapshots IS 'Snapshots of training data for reproducibility';


--
-- Name: user_entitlements; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.user_entitlements (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    user_id text NOT NULL,
    entitlement_id uuid NOT NULL,
    granted_by text,
    granted_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone,
    status character varying(50) DEFAULT 'active'::character varying,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_entitlements OWNER TO sg;

--
-- Name: TABLE user_entitlements; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.user_entitlements IS 'Current entitlement assignments to users';


--
-- Name: COLUMN user_entitlements.expires_at; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.user_entitlements.expires_at IS 'Optional expiration date for temporary access';


--
-- Name: user_lifecycle_schedule; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.user_lifecycle_schedule (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    user_id text NOT NULL,
    activate_at timestamp with time zone,
    deactivate_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_lifecycle_schedule OWNER TO sg;

--
-- Name: user_mfa_status; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.user_mfa_status (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    user_id text NOT NULL,
    user_email character varying(255),
    user_name character varying(255),
    mfa_enabled boolean DEFAULT false,
    mfa_methods text[],
    mfa_configured_at timestamp with time zone,
    enforcement_status character varying(50) DEFAULT 'non_compliant'::character varying,
    applicable_policy_id uuid,
    grace_period_expires_at timestamp with time zone,
    exemption_reason text,
    exempted_by text,
    last_checked_at timestamp with time zone DEFAULT now(),
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.user_mfa_status OWNER TO sg;

--
-- Name: TABLE user_mfa_status; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.user_mfa_status IS 'Cached MFA status for users (synced from Keycloak)';


--
-- Name: user_tenants; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.user_tenants (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id text NOT NULL,
    tenant_id uuid NOT NULL,
    organization_id uuid,
    customer_id uuid NOT NULL,
    realm_name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_tenants OWNER TO sg;

--
-- Name: TABLE user_tenants; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.user_tenants IS 'Mapping between Keycloak users and tenants with realm association';


--
-- Name: COLUMN user_tenants.realm_name; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.user_tenants.realm_name IS 'Keycloak realm where user exists';


--
-- Name: vault_access_grants; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.vault_access_grants (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id character varying(255) NOT NULL,
    tenant_id uuid NOT NULL,
    access_level character varying(50) NOT NULL,
    can_access_customer boolean DEFAULT false NOT NULL,
    can_access_org boolean DEFAULT false NOT NULL,
    can_access_tenant boolean DEFAULT true NOT NULL,
    can_create_secrets boolean DEFAULT false NOT NULL,
    can_read_secrets boolean DEFAULT true NOT NULL,
    can_update_secrets boolean DEFAULT false NOT NULL,
    can_delete_secrets boolean DEFAULT false NOT NULL,
    can_use_encryption boolean DEFAULT false NOT NULL,
    can_generate_db_creds boolean DEFAULT false NOT NULL,
    can_issue_certificates boolean DEFAULT false NOT NULL,
    can_manage_policies boolean DEFAULT false NOT NULL,
    granted_by character varying(255),
    granted_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vault_access_grants_access_level_check CHECK (((access_level)::text = ANY (ARRAY[('admin'::character varying)::text, ('write'::character varying)::text, ('read'::character varying)::text])))
);


ALTER TABLE public.vault_access_grants OWNER TO sg;

--
-- Name: TABLE vault_access_grants; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.vault_access_grants IS 'Granular access control for Vault operations';


--
-- Name: vault_audit_log; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.vault_audit_log (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid,
    organization_id uuid,
    customer_id uuid,
    user_id character varying(255),
    operation character varying(100) NOT NULL,
    vault_path character varying(500) NOT NULL,
    scope character varying(50) NOT NULL,
    success boolean NOT NULL,
    error_message text,
    duration_ms integer,
    ip_address inet,
    user_agent text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vault_audit_log_scope_check CHECK (((scope)::text = ANY (ARRAY[('tenant'::character varying)::text, ('org'::character varying)::text, ('customer'::character varying)::text, ('platform'::character varying)::text])))
);


ALTER TABLE public.vault_audit_log OWNER TO sg;

--
-- Name: TABLE vault_audit_log; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.vault_audit_log IS 'Comprehensive audit log for all Vault operations';


--
-- Name: vault_customers; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.vault_customers (
    customer_id uuid NOT NULL,
    vault_path character varying(255) NOT NULL,
    vault_policy_name character varying(255) NOT NULL,
    vault_entity_id character varying(255) NOT NULL,
    kv_enabled boolean DEFAULT true NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vault_customers_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('suspended'::character varying)::text, ('disabled'::character varying)::text])))
);


ALTER TABLE public.vault_customers OWNER TO sg;

--
-- Name: TABLE vault_customers; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.vault_customers IS 'Customer-level Vault configuration and quotas';


--
-- Name: vault_organizations; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.vault_organizations (
    organization_id uuid NOT NULL,
    customer_id uuid NOT NULL,
    vault_path character varying(255) NOT NULL,
    vault_policy_name character varying(255) NOT NULL,
    vault_entity_id character varying(255) NOT NULL,
    kv_enabled boolean DEFAULT true NOT NULL,
    transit_enabled boolean DEFAULT false NOT NULL,
    database_enabled boolean DEFAULT false NOT NULL,
    pki_enabled boolean DEFAULT false NOT NULL,
    quota_secrets integer DEFAULT 5000 NOT NULL,
    quota_secrets_used integer DEFAULT 0 NOT NULL,
    quota_encryption_ops integer DEFAULT 500000 NOT NULL,
    quota_encryption_used integer DEFAULT 0 NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vault_organizations_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('suspended'::character varying)::text, ('disabled'::character varying)::text])))
);


ALTER TABLE public.vault_organizations OWNER TO sg;

--
-- Name: TABLE vault_organizations; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.vault_organizations IS 'Organization-level Vault configuration and quotas';


--
-- Name: vault_tenants; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.vault_tenants (
    tenant_id uuid NOT NULL,
    customer_id uuid,
    organization_id uuid,
    vault_path character varying(255) NOT NULL,
    vault_policy_name character varying(255) NOT NULL,
    vault_entity_id character varying(255) NOT NULL,
    vault_token_accessor character varying(255),
    kv_enabled boolean DEFAULT true NOT NULL,
    transit_enabled boolean DEFAULT false NOT NULL,
    database_enabled boolean DEFAULT false NOT NULL,
    pki_enabled boolean DEFAULT false NOT NULL,
    quota_secrets integer DEFAULT 1000 NOT NULL,
    quota_secrets_used integer DEFAULT 0 NOT NULL,
    quota_encryption_ops integer DEFAULT 100000 NOT NULL,
    quota_encryption_used integer DEFAULT 0 NOT NULL,
    quota_db_credentials integer DEFAULT 100 NOT NULL,
    quota_db_credentials_used integer DEFAULT 0 NOT NULL,
    quota_certificates integer DEFAULT 100 NOT NULL,
    quota_certificates_used integer DEFAULT 0 NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT vault_tenants_status_check CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('suspended'::character varying)::text, ('disabled'::character varying)::text])))
);


ALTER TABLE public.vault_tenants OWNER TO sg;

--
-- Name: TABLE vault_tenants; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.vault_tenants IS 'Tenant-level Vault configuration - THE isolation boundary';


--
-- Name: COLUMN vault_tenants.vault_path; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.vault_tenants.vault_path IS 'Vault path prefix: tenants/{uuid}';


--
-- Name: COLUMN vault_tenants.vault_policy_name; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.vault_tenants.vault_policy_name IS 'Tenant-specific policy name';


--
-- Name: COLUMN vault_tenants.vault_entity_id; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.vault_tenants.vault_entity_id IS 'Vault entity ID for token generation';


--
-- Name: COLUMN vault_tenants.vault_token_accessor; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.vault_tenants.vault_token_accessor IS 'Token accessor for revocation';


--
-- Name: vault_tenant_status; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.vault_tenant_status AS
 SELECT vt.tenant_id,
    t.name AS tenant_name,
    t.slug AS tenant_slug,
    o.name AS organization_name,
    c.name AS customer_name,
    vt.vault_path,
    vt.kv_enabled,
    vt.transit_enabled,
    vt.database_enabled,
    vt.pki_enabled,
    vt.quota_secrets,
    vt.quota_secrets_used,
    round((((vt.quota_secrets_used)::numeric / (vt.quota_secrets)::numeric) * (100)::numeric), 2) AS secrets_utilization_percent,
    vt.quota_encryption_ops,
    vt.quota_encryption_used,
    vt.status,
    vt.created_at
   FROM (((public.vault_tenants vt
     JOIN public.tenants t ON ((vt.tenant_id = t.id)))
     LEFT JOIN public.organizations o ON ((vt.organization_id = o.id)))
     LEFT JOIN public.customers c ON ((vt.customer_id = c.id)));


ALTER VIEW public.vault_tenant_status OWNER TO sg;

--
-- Name: vault_usage_by_customer; Type: VIEW; Schema: public; Owner: sg
--

CREATE VIEW public.vault_usage_by_customer AS
 SELECT c.id AS customer_id,
    c.name AS customer_name,
    c.pricing_tier,
    count(DISTINCT vt.tenant_id) AS tenants_with_vault,
    sum(vt.quota_secrets_used) AS total_secrets,
    sum(vt.quota_encryption_used) AS total_encryption_ops,
    sum(vt.quota_certificates_used) AS total_certificates
   FROM (public.customers c
     LEFT JOIN public.vault_tenants vt ON ((vt.customer_id = c.id)))
  WHERE ((vt.status)::text = 'active'::text)
  GROUP BY c.id, c.name, c.pricing_tier;


ALTER VIEW public.vault_usage_by_customer OWNER TO sg;

--
-- Name: vault_usage_history; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.vault_usage_history (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid,
    organization_id uuid,
    customer_id uuid,
    secrets_count integer DEFAULT 0 NOT NULL,
    encryption_operations integer DEFAULT 0 NOT NULL,
    decryption_operations integer DEFAULT 0 NOT NULL,
    db_credentials_generated integer DEFAULT 0 NOT NULL,
    certificates_issued integer DEFAULT 0 NOT NULL,
    period_start timestamp with time zone NOT NULL,
    period_end timestamp with time zone NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.vault_usage_history OWNER TO sg;

--
-- Name: TABLE vault_usage_history; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.vault_usage_history IS 'Historical Vault usage for analytics and billing';


--
-- Name: version_compatibility; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.version_compatibility (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    agent_version character varying(50) NOT NULL,
    image_version character varying(50) NOT NULL,
    compatibility_status character varying(20) DEFAULT 'untested'::character varying NOT NULL,
    tested_date timestamp with time zone,
    test_results jsonb,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.version_compatibility OWNER TO sg;

--
-- Name: vulnerabilities; Type: TABLE; Schema: public; Owner: sg
--

CREATE TABLE public.vulnerabilities (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    cve_id text NOT NULL,
    title text NOT NULL,
    description text,
    cvss_score numeric(5,2),
    cvss_severity text,
    affected_products jsonb,
    exploit_available boolean DEFAULT false,
    exploit_maturity text,
    patch_available boolean DEFAULT false,
    remediation_steps jsonb,
    patches jsonb,
    workarounds jsonb,
    nist_controls jsonb,
    mitre_techniques jsonb,
    published_date timestamp with time zone,
    last_modified_date timestamp with time zone,
    source text DEFAULT 'nvd'::text,
    raw_data jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    cvss_vector text
);


ALTER TABLE public.vulnerabilities OWNER TO sg;

--
-- Name: TABLE vulnerabilities; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TABLE public.vulnerabilities IS 'CVE vulnerability database with exploit details and remediation';


--
-- Name: COLUMN vulnerabilities.cvss_vector; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON COLUMN public.vulnerabilities.cvss_vector IS 'CVSS vector string (e.g., CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)';


--
-- Name: alert_ai_analysis; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.alert_ai_analysis (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    alert_id uuid NOT NULL,
    model_name text NOT NULL,
    model_version text NOT NULL,
    adapter_version text,
    ai_severity text NOT NULL,
    ai_category text NOT NULL,
    ai_confidence numeric(5,2),
    rationale text NOT NULL,
    recommended_actions jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE security_ops.alert_ai_analysis OWNER TO sg;

--
-- Name: alert_playbook_triggers; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.alert_playbook_triggers (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    alert_id uuid NOT NULL,
    playbook_id uuid NOT NULL,
    playbook_execution_id uuid,
    trigger_reason text,
    evaluated_at timestamp with time zone DEFAULT now() NOT NULL,
    triggered_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE security_ops.alert_playbook_triggers OWNER TO sg;

--
-- Name: TABLE alert_playbook_triggers; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.alert_playbook_triggers IS 'Metadata tracking which playbooks were triggered by which alerts (metadata only, no duplication)';


--
-- Name: alert_triage_feedback; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.alert_triage_feedback (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    alert_id uuid NOT NULL,
    ai_analysis_id uuid NOT NULL,
    ai_severity text NOT NULL,
    ai_category text NOT NULL,
    human_severity text NOT NULL,
    human_category text NOT NULL,
    disposition text NOT NULL,
    comment text,
    created_by_user_id text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE security_ops.alert_triage_feedback OWNER TO sg;

--
-- Name: alerts; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.alerts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    source text NOT NULL,
    external_id text NOT NULL,
    title text NOT NULL,
    description text,
    raw_severity text,
    status text DEFAULT 'open'::text NOT NULL,
    detection_time timestamp with time zone NOT NULL,
    asset_id text,
    user_identifier text,
    raw_payload jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    nist_controls jsonb,
    mitre_tactics jsonb,
    mitre_techniques jsonb,
    cve_ids text[],
    exploit_indicators jsonb
);


ALTER TABLE security_ops.alerts OWNER TO sg;

--
-- Name: TABLE alerts; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.alerts IS 'Security alerts from SIEM, detection rules, and security tools';


--
-- Name: COLUMN alerts.nist_controls; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.alerts.nist_controls IS 'Array of NIST SP 800-53 control mappings: [{"control_id": "IR-4", "title": "Incident Response Planning", "relevance": "..."}]';


--
-- Name: COLUMN alerts.mitre_tactics; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.alerts.mitre_tactics IS 'Array of MITRE ATT&CK tactic mappings: [{"tactic_id": "TA0001", "name": "Initial Access", ...}]';


--
-- Name: COLUMN alerts.mitre_techniques; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.alerts.mitre_techniques IS 'Array of MITRE ATT&CK technique mappings: [{"technique_id": "T1078", "name": "Valid Accounts", ...}]';


--
-- Name: COLUMN alerts.cve_ids; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.alerts.cve_ids IS 'Array of CVE IDs associated with this alert: ["CVE-2024-1234", "CVE-2024-5678"]';


--
-- Name: COLUMN alerts.exploit_indicators; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.alerts.exploit_indicators IS 'Indicators that this alert exploits a vulnerability: {"exploit_type": "...", "indicators": [...]}';


--
-- Name: detection_bindings; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.detection_bindings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    detection_rule_id uuid NOT NULL,
    detection_rule_version_id uuid,
    params_override jsonb DEFAULT '{}'::jsonb,
    is_enabled boolean DEFAULT true NOT NULL,
    rollout_status text DEFAULT 'published'::text,
    destination_id text,
    scope text DEFAULT 'sg'::text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE security_ops.detection_bindings OWNER TO sg;

--
-- Name: detection_deduplication; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.detection_deduplication (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    rule_id uuid NOT NULL,
    dedup_key text NOT NULL,
    dedup_fields jsonb NOT NULL,
    first_seen timestamp with time zone DEFAULT now() NOT NULL,
    last_seen timestamp with time zone DEFAULT now() NOT NULL,
    occurrence_count integer DEFAULT 1 NOT NULL,
    incident_id uuid,
    last_detection_event_id text,
    status text DEFAULT 'active'::text NOT NULL,
    suppressed_until timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE security_ops.detection_deduplication OWNER TO sg;

--
-- Name: TABLE detection_deduplication; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.detection_deduplication IS 'Tracks duplicate detection patterns to prevent alert fatigue';


--
-- Name: COLUMN detection_deduplication.dedup_key; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.detection_deduplication.dedup_key IS 'SHA-256 hash of group_by fields for quick lookup';


--
-- Name: COLUMN detection_deduplication.dedup_fields; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.detection_deduplication.dedup_fields IS 'JSON of fields used for grouping (user.id, source.ip, etc.)';


--
-- Name: detection_playbook_mappings; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.detection_playbook_mappings (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    rule_id uuid,
    alert_type text NOT NULL,
    playbook_id uuid,
    playbook_key text,
    auto_execute boolean DEFAULT false,
    requires_approval boolean DEFAULT true,
    severity_threshold text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


ALTER TABLE security_ops.detection_playbook_mappings OWNER TO sg;

--
-- Name: TABLE detection_playbook_mappings; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.detection_playbook_mappings IS 'Maps alert types to playbooks for automated response';


--
-- Name: COLUMN detection_playbook_mappings.auto_execute; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.detection_playbook_mappings.auto_execute IS 'If true, playbook runs automatically without approval';


--
-- Name: detection_rule_executions; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.detection_rule_executions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    rule_id uuid NOT NULL,
    rule_version text NOT NULL,
    fired_at timestamp with time zone NOT NULL,
    match_count integer NOT NULL,
    detection_event_ids text[],
    incident_ids uuid[],
    execution_time_ms integer,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE security_ops.detection_rule_executions OWNER TO sg;

--
-- Name: TABLE detection_rule_executions; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.detection_rule_executions IS 'Audit trail of detection rule firings';


--
-- Name: detection_rule_versions; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.detection_rule_versions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    rule_id uuid NOT NULL,
    version text NOT NULL,
    index_pattern text NOT NULL,
    query jsonb NOT NULL,
    trigger_condition jsonb NOT NULL,
    severity text NOT NULL,
    action_config jsonb NOT NULL,
    metadata jsonb,
    changelog text,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    created_by text,
    graph_json jsonb,
    is_template boolean DEFAULT false,
    query_template_id text,
    query_template_version text
);


ALTER TABLE security_ops.detection_rule_versions OWNER TO sg;

--
-- Name: TABLE detection_rule_versions; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.detection_rule_versions IS 'Complete version history of detection rules';


--
-- Name: COLUMN detection_rule_versions.query; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.detection_rule_versions.query IS 'OpenSearch Query DSL as JSON';


--
-- Name: COLUMN detection_rule_versions.trigger_condition; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.detection_rule_versions.trigger_condition IS 'Conditions to trigger alert (threshold, aggregations)';


--
-- Name: detection_rules; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.detection_rules (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    rule_key text NOT NULL,
    name text NOT NULL,
    description text,
    category text NOT NULL,
    current_version text NOT NULL,
    is_builtin boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    created_by text,
    updated_at timestamp with time zone DEFAULT now(),
    approval_required boolean DEFAULT false,
    tenant_id uuid
);


ALTER TABLE security_ops.detection_rules OWNER TO sg;

--
-- Name: TABLE detection_rules; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.detection_rules IS 'Catalog of all detection rules with semantic versioning';


--
-- Name: COLUMN detection_rules.rule_key; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.detection_rules.rule_key IS 'Unique identifier like SG-DET-001';


--
-- Name: detection_suppression_events; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.detection_suppression_events (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    dedup_id uuid,
    suppression_rule_id uuid,
    detection_event_id text NOT NULL,
    alert_type text NOT NULL,
    suppressed_at timestamp with time zone DEFAULT now() NOT NULL,
    reason text NOT NULL,
    dedup_key text,
    metadata jsonb
);


ALTER TABLE security_ops.detection_suppression_events OWNER TO sg;

--
-- Name: TABLE detection_suppression_events; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.detection_suppression_events IS 'Audit log of suppressed detection events';


--
-- Name: detection_suppression_rules; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.detection_suppression_rules (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    rule_id uuid,
    name text NOT NULL,
    description text,
    enabled boolean DEFAULT true,
    alert_types text[],
    time_window_minutes integer DEFAULT 60 NOT NULL,
    max_occurrences integer DEFAULT 1 NOT NULL,
    group_by_fields text[] NOT NULL,
    escalate_after_count integer,
    escalate_if_severity text[],
    suppress_during_maintenance boolean DEFAULT false,
    maintenance_schedule jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by text
);


ALTER TABLE security_ops.detection_suppression_rules OWNER TO sg;

--
-- Name: TABLE detection_suppression_rules; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.detection_suppression_rules IS 'Configurable rules for when to suppress alerts';


--
-- Name: COLUMN detection_suppression_rules.group_by_fields; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.detection_suppression_rules.group_by_fields IS 'Fields to group by for deduplication (e.g., ["user.id", "source.ip"])';


--
-- Name: COLUMN detection_suppression_rules.escalate_after_count; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.detection_suppression_rules.escalate_after_count IS 'Create incident after N duplicates (null = never escalate)';


--
-- Name: incident_actions; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.incident_actions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_id uuid NOT NULL,
    action_type text NOT NULL,
    target_entity_type text,
    target_entity_id text,
    target_entity_name text,
    action_taken_by text NOT NULL,
    action_source text NOT NULL,
    playbook_execution_id uuid,
    nist_phase text,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    before_state jsonb,
    after_state jsonb,
    success boolean DEFAULT true,
    error_message text,
    rollback_possible boolean DEFAULT false,
    rollback_procedure text,
    evidence_collected jsonb
);


ALTER TABLE security_ops.incident_actions OWNER TO sg;

--
-- Name: TABLE incident_actions; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.incident_actions IS 'All actions taken during incident response';


--
-- Name: COLUMN incident_actions.rollback_procedure; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incident_actions.rollback_procedure IS 'Instructions to reverse this action';


--
-- Name: incident_ai_summaries; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.incident_ai_summaries (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    incident_id uuid NOT NULL,
    model_name text NOT NULL,
    model_version text NOT NULL,
    adapter_version text,
    summary_type text NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by text DEFAULT 'model'::text NOT NULL
);


ALTER TABLE security_ops.incident_ai_summaries OWNER TO sg;

--
-- Name: incident_alerts; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.incident_alerts (
    incident_id uuid NOT NULL,
    alert_id uuid NOT NULL
);


ALTER TABLE security_ops.incident_alerts OWNER TO sg;

--
-- Name: incident_evidence; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.incident_evidence (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_id uuid NOT NULL,
    evidence_type text NOT NULL,
    evidence_location text NOT NULL,
    collected_at timestamp with time zone DEFAULT now() NOT NULL,
    collected_by text NOT NULL,
    collection_method text,
    hash_sha256 text,
    size_bytes bigint,
    metadata jsonb,
    chain_of_custody jsonb
);


ALTER TABLE security_ops.incident_evidence OWNER TO sg;

--
-- Name: TABLE incident_evidence; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.incident_evidence IS 'Forensic evidence with chain of custody';


--
-- Name: COLUMN incident_evidence.chain_of_custody; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incident_evidence.chain_of_custody IS 'Who handled evidence and when';


--
-- Name: incident_lifecycle; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.incident_lifecycle (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_id uuid NOT NULL,
    detection_event_id text,
    rule_id uuid,
    rule_version text,
    alert_raw_payload jsonb,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE security_ops.incident_lifecycle OWNER TO sg;

--
-- Name: TABLE incident_lifecycle; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.incident_lifecycle IS 'Complete lineage from detection rule to incident';


--
-- Name: COLUMN incident_lifecycle.detection_event_id; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incident_lifecycle.detection_event_id IS 'Links to detection event in OpenSearch';


--
-- Name: incident_observables; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.incident_observables (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_id uuid NOT NULL,
    observable_type text NOT NULL,
    observable_value text NOT NULL,
    source text NOT NULL,
    extracted_at timestamp with time zone DEFAULT now() NOT NULL,
    extracted_by text,
    confidence real,
    is_malicious boolean,
    threat_intel_enrichment jsonb,
    tags text[],
    first_seen timestamp with time zone,
    last_seen timestamp with time zone
);


ALTER TABLE security_ops.incident_observables OWNER TO sg;

--
-- Name: TABLE incident_observables; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.incident_observables IS 'IOCs with provenance tracking';


--
-- Name: COLUMN incident_observables.source; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incident_observables.source IS 'Provenance: where did this IOC come from?';


--
-- Name: incident_timeline; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.incident_timeline (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    incident_id uuid NOT NULL,
    "timestamp" timestamp with time zone DEFAULT now() NOT NULL,
    event_type text NOT NULL,
    actor_type text NOT NULL,
    actor_id text,
    nist_phase text,
    nist_status text,
    action text NOT NULL,
    description text,
    metadata jsonb,
    playbook_execution_id uuid,
    related_entity_type text,
    related_entity_id text,
    before_state jsonb,
    after_state jsonb,
    execution_time_ms integer,
    success boolean DEFAULT true,
    error_message text
);


ALTER TABLE security_ops.incident_timeline OWNER TO sg;

--
-- Name: TABLE incident_timeline; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.incident_timeline IS 'Microsecond-precision timeline of all actions';


--
-- Name: COLUMN incident_timeline.before_state; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incident_timeline.before_state IS 'State snapshot before action for forensics';


--
-- Name: COLUMN incident_timeline.after_state; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incident_timeline.after_state IS 'State snapshot after action for forensics';


--
-- Name: incidents; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.incidents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    source text DEFAULT 'thehive'::text NOT NULL,
    external_id text NOT NULL,
    title text NOT NULL,
    status text NOT NULL,
    severity text,
    raw_payload jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    nist_controls jsonb,
    mitre_tactics jsonb,
    mitre_techniques jsonb,
    cve_ids text[],
    exploit_indicators jsonb,
    ticket_id uuid,
    external_ticket_id text,
    external_ticket_provider text,
    detection_rule_version_id uuid,
    playbook_version_id uuid
);


ALTER TABLE security_ops.incidents OWNER TO sg;

--
-- Name: COLUMN incidents.nist_controls; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incidents.nist_controls IS 'Array of NIST SP 800-53 control mappings';


--
-- Name: COLUMN incidents.mitre_tactics; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incidents.mitre_tactics IS 'Array of MITRE ATT&CK tactic mappings';


--
-- Name: COLUMN incidents.mitre_techniques; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incidents.mitre_techniques IS 'Array of MITRE ATT&CK technique mappings';


--
-- Name: COLUMN incidents.cve_ids; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incidents.cve_ids IS 'Array of CVE IDs associated with this incident';


--
-- Name: COLUMN incidents.exploit_indicators; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incidents.exploit_indicators IS 'Indicators that this incident exploits a vulnerability';


--
-- Name: COLUMN incidents.ticket_id; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incidents.ticket_id IS 'Internal ticket record linked to incident';


--
-- Name: COLUMN incidents.external_ticket_id; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incidents.external_ticket_id IS 'External ticket id (e.g., Zammad case id)';


--
-- Name: COLUMN incidents.external_ticket_provider; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.incidents.external_ticket_provider IS 'External provider name (zammad/thehive/etc.)';


--
-- Name: playbooks; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.playbooks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    key text NOT NULL,
    name text NOT NULL,
    description text,
    target_type text NOT NULL,
    severity_filter jsonb,
    category_filter jsonb,
    workflow_ref text NOT NULL,
    requires_approval boolean DEFAULT true NOT NULL,
    is_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    trigger_conditions jsonb,
    auto_trigger_enabled boolean DEFAULT false,
    trigger_priority integer DEFAULT 0,
    playbook_key character varying(255),
    is_builtin boolean DEFAULT false,
    severity_default character varying(50),
    applicable_sources text[] DEFAULT ARRAY[]::text[],
    triggers text[] DEFAULT ARRAY[]::text[],
    prerequisites text[] DEFAULT ARRAY[]::text[],
    artifacts_required text[] DEFAULT ARRAY[]::text[],
    phases jsonb,
    cis_controls text[] DEFAULT ARRAY[]::text[],
    is_template boolean DEFAULT false,
    template_key text,
    category character varying(50),
    version character varying(50) DEFAULT '1.0.0'::character varying,
    workflow jsonb DEFAULT '{"edges": [], "nodes": []}'::jsonb,
    timeout_seconds integer DEFAULT 3600,
    retry_policy jsonb,
    on_failure character varying(50) DEFAULT 'fail'::character varying,
    soc2_criteria text[] DEFAULT ARRAY[]::text[]
);


ALTER TABLE security_ops.playbooks OWNER TO sg;

--
-- Name: TABLE playbooks; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.playbooks IS 'Catalog of incident response playbooks (per-tenant, with sg_admin as shared source)';


--
-- Name: COLUMN playbooks.soc2_criteria; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.playbooks.soc2_criteria IS 'SOC 2 Common Criteria mapped to this playbook (e.g., {CC6.1,CC7.1}).';


--
-- Name: ticket_ai_enrichments; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.ticket_ai_enrichments (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    ticket_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    enrichment_type text NOT NULL,
    status text NOT NULL,
    iam_enrichment jsonb,
    vulnerability_enrichment jsonb,
    cmdb_enrichment jsonb,
    network_enrichment jsonb,
    framework_enrichment jsonb,
    model_name text,
    model_version text,
    confidence_score numeric(5,2),
    reasoning text,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE security_ops.ticket_ai_enrichments OWNER TO sg;

--
-- Name: TABLE ticket_ai_enrichments; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.ticket_ai_enrichments IS 'AI enrichment results for tickets across IAM, vulnerability, CMDB, network, and framework domains';


--
-- Name: COLUMN ticket_ai_enrichments.iam_enrichment; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.ticket_ai_enrichments.iam_enrichment IS 'IAM tab data: users, supervisors, groups, permissions, access history';


--
-- Name: COLUMN ticket_ai_enrichments.vulnerability_enrichment; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.ticket_ai_enrichments.vulnerability_enrichment IS 'Vulnerability tab data: CVEs, exploit details, remediation steps, patches';


--
-- Name: COLUMN ticket_ai_enrichments.cmdb_enrichment; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.ticket_ai_enrichments.cmdb_enrichment IS 'CMDB tab data: assets, hardware/software inventory, network info';


--
-- Name: COLUMN ticket_ai_enrichments.network_enrichment; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.ticket_ai_enrichments.network_enrichment IS 'Network tab data: IPs, domains, connections, firewall rules';


--
-- Name: COLUMN ticket_ai_enrichments.framework_enrichment; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.ticket_ai_enrichments.framework_enrichment IS 'Framework mappings: NIST controls, MITRE tactics/techniques';


--
-- Name: ticket_alerts; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.ticket_alerts (
    ticket_id uuid NOT NULL,
    alert_id uuid NOT NULL
);


ALTER TABLE security_ops.ticket_alerts OWNER TO sg;

--
-- Name: TABLE ticket_alerts; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.ticket_alerts IS 'Many-to-many relationship between tickets and alerts';


--
-- Name: ticket_vulnerabilities; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.ticket_vulnerabilities (
    ticket_id uuid NOT NULL,
    vulnerability_id uuid NOT NULL
);


ALTER TABLE security_ops.ticket_vulnerabilities OWNER TO sg;

--
-- Name: TABLE ticket_vulnerabilities; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.ticket_vulnerabilities IS 'Many-to-many relationship between tickets and vulnerabilities';


--
-- Name: tickets; Type: TABLE; Schema: security_ops; Owner: sg
--

CREATE TABLE security_ops.tickets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    external_id text,
    source text DEFAULT 'thehive'::text NOT NULL,
    title text NOT NULL,
    description text,
    status text NOT NULL,
    severity text,
    priority text,
    category text,
    nist_controls jsonb,
    mitre_tactics jsonb,
    mitre_techniques jsonb,
    cve_ids text[],
    exploit_indicators jsonb,
    iam_data jsonb,
    vm_data jsonb,
    cmdb_data jsonb,
    network_data jsonb,
    timeline_data jsonb,
    ai_enrichment_status text DEFAULT 'pending'::text,
    ai_enrichment_summary text,
    ai_enrichment_timestamp timestamp with time zone,
    assigned_to text,
    created_by text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    tenant_slug text,
    external_vendor_id text
);


ALTER TABLE security_ops.tickets OWNER TO sg;

--
-- Name: TABLE tickets; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON TABLE security_ops.tickets IS 'Enhanced ticket/incident management with tab-based data structure';


--
-- Name: COLUMN tickets.tenant_slug; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.tickets.tenant_slug IS 'Tenant slug used for SG-branded ticket identifiers';


--
-- Name: COLUMN tickets.external_vendor_id; Type: COMMENT; Schema: security_ops; Owner: sg
--

COMMENT ON COLUMN security_ops.tickets.external_vendor_id IS 'Underlying provider ticket id (hidden from end users)';


--
-- Name: audit_log_statistics audit_log_statistics_pkey; Type: CONSTRAINT; Schema: audit; Owner: sg
--

ALTER TABLE ONLY audit.audit_log_statistics
    ADD CONSTRAINT audit_log_statistics_pkey PRIMARY KEY (id);


--
-- Name: audit_log_statistics audit_log_statistics_tenant_id_realm_name_period_start_peri_key; Type: CONSTRAINT; Schema: audit; Owner: sg
--

ALTER TABLE ONLY audit.audit_log_statistics
    ADD CONSTRAINT audit_log_statistics_tenant_id_realm_name_period_start_peri_key UNIQUE (tenant_id, realm_name, period_start, period_end);


--
-- Name: audit_retention_policies audit_retention_policies_pkey; Type: CONSTRAINT; Schema: audit; Owner: sg
--

ALTER TABLE ONLY audit.audit_retention_policies
    ADD CONSTRAINT audit_retention_policies_pkey PRIMARY KEY (id);


--
-- Name: audit_retention_policies audit_retention_policies_tenant_id_policy_name_key; Type: CONSTRAINT; Schema: audit; Owner: sg
--

ALTER TABLE ONLY audit.audit_retention_policies
    ADD CONSTRAINT audit_retention_policies_tenant_id_policy_name_key UNIQUE (tenant_id, policy_name);


--
-- Name: platform_audit_logs platform_audit_logs_pkey; Type: CONSTRAINT; Schema: audit; Owner: sg
--

ALTER TABLE ONLY audit.platform_audit_logs
    ADD CONSTRAINT platform_audit_logs_pkey PRIMARY KEY (id);


--
-- Name: runs runs_pkey; Type: CONSTRAINT; Schema: llm_training; Owner: sg
--

ALTER TABLE ONLY llm_training.runs
    ADD CONSTRAINT runs_pkey PRIMARY KEY (id);


--
-- Name: scanner_registry scanner_registry_pkey; Type: CONSTRAINT; Schema: orchestration; Owner: sg
--

ALTER TABLE ONLY orchestration.scanner_registry
    ADD CONSTRAINT scanner_registry_pkey PRIMARY KEY (id);


--
-- Name: scans scans_pkey; Type: CONSTRAINT; Schema: orchestration; Owner: sg
--

ALTER TABLE ONLY orchestration.scans
    ADD CONSTRAINT scans_pkey PRIMARY KEY (id);


--
-- Name: access_profile_entitlements access_profile_entitlements_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_profile_entitlements
    ADD CONSTRAINT access_profile_entitlements_pkey PRIMARY KEY (access_profile_id, entitlement_id);


--
-- Name: access_profiles access_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_profiles
    ADD CONSTRAINT access_profiles_pkey PRIMARY KEY (id);


--
-- Name: access_profiles access_profiles_tenant_id_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_profiles
    ADD CONSTRAINT access_profiles_tenant_id_name_key UNIQUE (tenant_id, name);


--
-- Name: access_requests access_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_requests
    ADD CONSTRAINT access_requests_pkey PRIMARY KEY (id);


--
-- Name: access_review_campaigns access_review_campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_campaigns
    ADD CONSTRAINT access_review_campaigns_pkey PRIMARY KEY (id);


--
-- Name: access_review_campaigns access_review_campaigns_tenant_id_realm_name_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_campaigns
    ADD CONSTRAINT access_review_campaigns_tenant_id_realm_name_name_key UNIQUE (tenant_id, realm_name, name);


--
-- Name: access_review_decisions access_review_decisions_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_decisions
    ADD CONSTRAINT access_review_decisions_pkey PRIMARY KEY (id);


--
-- Name: access_review_items access_review_items_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_items
    ADD CONSTRAINT access_review_items_pkey PRIMARY KEY (id);


--
-- Name: access_review_statistics access_review_statistics_campaign_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_statistics
    ADD CONSTRAINT access_review_statistics_campaign_id_key UNIQUE (campaign_id);


--
-- Name: access_review_statistics access_review_statistics_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_statistics
    ADD CONSTRAINT access_review_statistics_pkey PRIMARY KEY (id);


--
-- Name: adapter_training_jobs adapter_training_jobs_job_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.adapter_training_jobs
    ADD CONSTRAINT adapter_training_jobs_job_id_key UNIQUE (job_id);


--
-- Name: adapter_training_jobs adapter_training_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.adapter_training_jobs
    ADD CONSTRAINT adapter_training_jobs_pkey PRIMARY KEY (id);


--
-- Name: adapter_version_history adapter_version_history_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.adapter_version_history
    ADD CONSTRAINT adapter_version_history_pkey PRIMARY KEY (id);


--
-- Name: agent_bootstrap_tokens agent_bootstrap_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.agent_bootstrap_tokens
    ADD CONSTRAINT agent_bootstrap_tokens_pkey PRIMARY KEY (id);


--
-- Name: agent_bootstrap_tokens agent_bootstrap_tokens_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.agent_bootstrap_tokens
    ADD CONSTRAINT agent_bootstrap_tokens_token_hash_key UNIQUE (token_hash);


--
-- Name: agent_versions agent_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.agent_versions
    ADD CONSTRAINT agent_versions_pkey PRIMARY KEY (id);


--
-- Name: ai_apps ai_apps_org_id_name_environment_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ai_apps
    ADD CONSTRAINT ai_apps_org_id_name_environment_key UNIQUE (org_id, name, environment);


--
-- Name: ai_apps ai_apps_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ai_apps
    ADD CONSTRAINT ai_apps_pkey PRIMARY KEY (id);


--
-- Name: ai_events ai_events_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ai_events
    ADD CONSTRAINT ai_events_pkey PRIMARY KEY (id);


--
-- Name: ai_policies ai_policies_org_id_ai_app_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ai_policies
    ADD CONSTRAINT ai_policies_org_id_ai_app_id_key UNIQUE (org_id, ai_app_id);


--
-- Name: ai_policies ai_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ai_policies
    ADD CONSTRAINT ai_policies_pkey PRIMARY KEY (id);


--
-- Name: ai_provider_credentials ai_provider_credentials_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ai_provider_credentials
    ADD CONSTRAINT ai_provider_credentials_pkey PRIMARY KEY (id);


--
-- Name: api_keys api_keys_key_hash_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_key_hash_key UNIQUE (key_hash);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: app_catalog app_catalog_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.app_catalog
    ADD CONSTRAINT app_catalog_name_key UNIQUE (name);


--
-- Name: app_catalog app_catalog_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.app_catalog
    ADD CONSTRAINT app_catalog_pkey PRIMARY KEY (id);


--
-- Name: approvals approvals_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_pkey PRIMARY KEY (id);


--
-- Name: apps apps_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.apps
    ADD CONSTRAINT apps_pkey PRIMARY KEY (id);


--
-- Name: apps apps_tenant_id_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.apps
    ADD CONSTRAINT apps_tenant_id_name_key UNIQUE (tenant_id, name);


--
-- Name: assets assets_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);


--
-- Name: birthright_rules birthright_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.birthright_rules
    ADD CONSTRAINT birthright_rules_pkey PRIMARY KEY (id);


--
-- Name: ca_authorities ca_authorities_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ca_authorities
    ADD CONSTRAINT ca_authorities_name_key UNIQUE (name);


--
-- Name: ca_authorities ca_authorities_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ca_authorities
    ADD CONSTRAINT ca_authorities_pkey PRIMARY KEY (id);


--
-- Name: certificate_requests certificate_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.certificate_requests
    ADD CONSTRAINT certificate_requests_pkey PRIMARY KEY (id);


--
-- Name: certificates certificates_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_pkey PRIMARY KEY (id);


--
-- Name: certificates certificates_serial_number_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_serial_number_key UNIQUE (serial_number);


--
-- Name: chat_messages chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_pkey PRIMARY KEY (id);


--
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);


--
-- Name: compliance_controls compliance_controls_framework_id_control_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.compliance_controls
    ADD CONSTRAINT compliance_controls_framework_id_control_id_key UNIQUE (framework_id, control_id);


--
-- Name: compliance_controls compliance_controls_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.compliance_controls
    ADD CONSTRAINT compliance_controls_pkey PRIMARY KEY (id);


--
-- Name: compliance_frameworks compliance_frameworks_framework_code_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.compliance_frameworks
    ADD CONSTRAINT compliance_frameworks_framework_code_key UNIQUE (framework_code);


--
-- Name: compliance_frameworks compliance_frameworks_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.compliance_frameworks
    ADD CONSTRAINT compliance_frameworks_pkey PRIMARY KEY (id);


--
-- Name: connected_apps connected_apps_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.connected_apps
    ADD CONSTRAINT connected_apps_pkey PRIMARY KEY (id);


--
-- Name: connected_apps connected_apps_tenant_id_client_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.connected_apps
    ADD CONSTRAINT connected_apps_tenant_id_client_id_key UNIQUE (tenant_id, client_id);


--
-- Name: control_mappings control_mappings_control_id_sentinelgrid_feature_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.control_mappings
    ADD CONSTRAINT control_mappings_control_id_sentinelgrid_feature_key UNIQUE (control_id, sentinelgrid_feature);


--
-- Name: control_mappings control_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.control_mappings
    ADD CONSTRAINT control_mappings_pkey PRIMARY KEY (id);


--
-- Name: customer_cloud_accounts customer_cloud_accounts_customer_id_cloud_provider_account__key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customer_cloud_accounts
    ADD CONSTRAINT customer_cloud_accounts_customer_id_cloud_provider_account__key UNIQUE (customer_id, cloud_provider, account_id);


--
-- Name: customer_cloud_accounts customer_cloud_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customer_cloud_accounts
    ADD CONSTRAINT customer_cloud_accounts_pkey PRIMARY KEY (id);


--
-- Name: customer_endpoint_agents customer_endpoint_agents_customer_id_agent_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customer_endpoint_agents
    ADD CONSTRAINT customer_endpoint_agents_customer_id_agent_id_key UNIQUE (customer_id, agent_id);


--
-- Name: customer_endpoint_agents customer_endpoint_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customer_endpoint_agents
    ADD CONSTRAINT customer_endpoint_agents_pkey PRIMARY KEY (id);


--
-- Name: customer_git_providers customer_git_providers_customer_id_provider_organization_na_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customer_git_providers
    ADD CONSTRAINT customer_git_providers_customer_id_provider_organization_na_key UNIQUE (customer_id, provider, organization_name);


--
-- Name: customer_git_providers customer_git_providers_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customer_git_providers
    ADD CONSTRAINT customer_git_providers_pkey PRIMARY KEY (id);


--
-- Name: customer_idp_config customer_idp_config_customer_id_idp_type_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customer_idp_config
    ADD CONSTRAINT customer_idp_config_customer_id_idp_type_key UNIQUE (customer_id, idp_type);


--
-- Name: customer_idp_config customer_idp_config_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customer_idp_config
    ADD CONSTRAINT customer_idp_config_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: customers customers_slug_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_slug_key UNIQUE (slug);


--
-- Name: cybersecurity_knowledge_base cybersecurity_knowledge_base_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.cybersecurity_knowledge_base
    ADD CONSTRAINT cybersecurity_knowledge_base_pkey PRIMARY KEY (id);


--
-- Name: data_migration_history data_migration_history_migration_version_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.data_migration_history
    ADD CONSTRAINT data_migration_history_migration_version_key UNIQUE (migration_version);


--
-- Name: data_migration_history data_migration_history_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.data_migration_history
    ADD CONSTRAINT data_migration_history_pkey PRIMARY KEY (id);


--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);


--
-- Name: endpoint_agent_events endpoint_agent_events_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.endpoint_agent_events
    ADD CONSTRAINT endpoint_agent_events_pkey PRIMARY KEY (id);


--
-- Name: endpoint_agents endpoint_agents_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.endpoint_agents
    ADD CONSTRAINT endpoint_agents_pkey PRIMARY KEY (id);


--
-- Name: endpoint_agents endpoint_agents_tenant_id_wazuh_agent_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.endpoint_agents
    ADD CONSTRAINT endpoint_agents_tenant_id_wazuh_agent_id_key UNIQUE (tenant_id, wazuh_agent_id);


--
-- Name: endpoint_agents endpoint_agents_wazuh_agent_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.endpoint_agents
    ADD CONSTRAINT endpoint_agents_wazuh_agent_id_key UNIQUE (wazuh_agent_id);


--
-- Name: entitlement_mappings entitlement_mappings_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.entitlement_mappings
    ADD CONSTRAINT entitlement_mappings_pkey PRIMARY KEY (id);


--
-- Name: entitlements entitlements_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.entitlements
    ADD CONSTRAINT entitlements_pkey PRIMARY KEY (id);


--
-- Name: entitlements entitlements_tenant_id_app_id_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.entitlements
    ADD CONSTRAINT entitlements_tenant_id_app_id_name_key UNIQUE (tenant_id, app_id, name);


--
-- Name: evidence_collection_tasks evidence_collection_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.evidence_collection_tasks
    ADD CONSTRAINT evidence_collection_tasks_pkey PRIMARY KEY (id);


--
-- Name: evidence_items evidence_items_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.evidence_items
    ADD CONSTRAINT evidence_items_pkey PRIMARY KEY (id);


--
-- Name: evidence_packages evidence_packages_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.evidence_packages
    ADD CONSTRAINT evidence_packages_pkey PRIMARY KEY (id);


--
-- Name: findings findings_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT findings_pkey PRIMARY KEY (id);


--
-- Name: fix_group_assets fix_group_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.fix_group_assets
    ADD CONSTRAINT fix_group_assets_pkey PRIMARY KEY (fix_group_id, asset_ref);


--
-- Name: fix_group_cves fix_group_cves_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.fix_group_cves
    ADD CONSTRAINT fix_group_cves_pkey PRIMARY KEY (fix_group_id, cve_id);


--
-- Name: fix_groups fix_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.fix_groups
    ADD CONSTRAINT fix_groups_pkey PRIMARY KEY (id);


--
-- Name: git_repositories git_repositories_customer_id_git_provider_id_repo_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.git_repositories
    ADD CONSTRAINT git_repositories_customer_id_git_provider_id_repo_name_key UNIQUE (customer_id, git_provider_id, repo_name);


--
-- Name: git_repositories git_repositories_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.git_repositories
    ADD CONSTRAINT git_repositories_pkey PRIMARY KEY (id);


--
-- Name: git_security_findings git_security_findings_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.git_security_findings
    ADD CONSTRAINT git_security_findings_pkey PRIMARY KEY (id);


--
-- Name: git_security_scans git_security_scans_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.git_security_scans
    ADD CONSTRAINT git_security_scans_pkey PRIMARY KEY (id);


--
-- Name: hardened_images hardened_images_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.hardened_images
    ADD CONSTRAINT hardened_images_pkey PRIMARY KEY (id);


--
-- Name: iam_audit_log iam_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.iam_audit_log
    ADD CONSTRAINT iam_audit_log_pkey PRIMARY KEY (id);


--
-- Name: iam_findings iam_findings_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.iam_findings
    ADD CONSTRAINT iam_findings_pkey PRIMARY KEY (id);


--
-- Name: image_customer_sharing image_customer_sharing_image_id_customer_account_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.image_customer_sharing
    ADD CONSTRAINT image_customer_sharing_image_id_customer_account_id_key UNIQUE (image_id, customer_account_id);


--
-- Name: image_customer_sharing image_customer_sharing_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.image_customer_sharing
    ADD CONSTRAINT image_customer_sharing_pkey PRIMARY KEY (id);


--
-- Name: image_version_history image_version_history_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.image_version_history
    ADD CONSTRAINT image_version_history_pkey PRIMARY KEY (id);


--
-- Name: integrations integrations_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.integrations
    ADD CONSTRAINT integrations_pkey PRIMARY KEY (id);


--
-- Name: jml_workflow_steps jml_workflow_steps_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.jml_workflow_steps
    ADD CONSTRAINT jml_workflow_steps_pkey PRIMARY KEY (id);


--
-- Name: jml_workflows jml_workflows_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.jml_workflows
    ADD CONSTRAINT jml_workflows_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: leads leads_email_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_email_key UNIQUE (email);


--
-- Name: leads leads_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_pkey PRIMARY KEY (id);


--
-- Name: mfa_compliance_violations mfa_compliance_violations_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.mfa_compliance_violations
    ADD CONSTRAINT mfa_compliance_violations_pkey PRIMARY KEY (id);


--
-- Name: mfa_enforcement_policies mfa_enforcement_policies_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.mfa_enforcement_policies
    ADD CONSTRAINT mfa_enforcement_policies_pkey PRIMARY KEY (id);


--
-- Name: mfa_enforcement_policies mfa_enforcement_policies_tenant_id_realm_name_policy_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.mfa_enforcement_policies
    ADD CONSTRAINT mfa_enforcement_policies_tenant_id_realm_name_policy_name_key UNIQUE (tenant_id, realm_name, policy_name);


--
-- Name: model_inference_logs model_inference_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.model_inference_logs
    ADD CONSTRAINT model_inference_logs_pkey PRIMARY KEY (id);


--
-- Name: onboarding_progress onboarding_progress_customer_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.onboarding_progress
    ADD CONSTRAINT onboarding_progress_customer_id_key UNIQUE (customer_id);


--
-- Name: onboarding_progress onboarding_progress_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.onboarding_progress
    ADD CONSTRAINT onboarding_progress_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_customer_id_slug_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_customer_id_slug_key UNIQUE (customer_id, slug);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: phishing_observables phishing_observables_phishing_report_id_observable_type_obs_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.phishing_observables
    ADD CONSTRAINT phishing_observables_phishing_report_id_observable_type_obs_key UNIQUE (phishing_report_id, observable_type, observable_value);


--
-- Name: phishing_observables phishing_observables_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.phishing_observables
    ADD CONSTRAINT phishing_observables_pkey PRIMARY KEY (id);


--
-- Name: phishing_reports phishing_reports_message_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.phishing_reports
    ADD CONSTRAINT phishing_reports_message_id_key UNIQUE (message_id);


--
-- Name: phishing_reports phishing_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.phishing_reports
    ADD CONSTRAINT phishing_reports_pkey PRIMARY KEY (id);


--
-- Name: playbook_analyzers playbook_analyzers_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_analyzers
    ADD CONSTRAINT playbook_analyzers_pkey PRIMARY KEY (id);


--
-- Name: playbook_execution_audit playbook_execution_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_execution_audit
    ADD CONSTRAINT playbook_execution_audit_pkey PRIMARY KEY (id);


--
-- Name: playbook_executions playbook_executions_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_executions
    ADD CONSTRAINT playbook_executions_pkey PRIMARY KEY (id);


--
-- Name: playbook_observables playbook_observables_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_observables
    ADD CONSTRAINT playbook_observables_pkey PRIMARY KEY (id);


--
-- Name: playbooks playbooks_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbooks
    ADD CONSTRAINT playbooks_pkey PRIMARY KEY (id);


--
-- Name: policies policies_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policies
    ADD CONSTRAINT policies_pkey PRIMARY KEY (id);


--
-- Name: policies policies_tenant_id_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policies
    ADD CONSTRAINT policies_tenant_id_name_key UNIQUE (tenant_id, name);


--
-- Name: policy_conflicts policy_conflicts_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_conflicts
    ADD CONSTRAINT policy_conflicts_pkey PRIMARY KEY (id);


--
-- Name: policy_evaluations policy_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_evaluations
    ADD CONSTRAINT policy_evaluations_pkey PRIMARY KEY (id);


--
-- Name: policy_rules policy_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_rules
    ADD CONSTRAINT policy_rules_pkey PRIMARY KEY (id);


--
-- Name: policy_templates policy_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_templates
    ADD CONSTRAINT policy_templates_pkey PRIMARY KEY (id);


--
-- Name: posture_findings posture_findings_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.posture_findings
    ADD CONSTRAINT posture_findings_pkey PRIMARY KEY (id);


--
-- Name: privileged_access_approvals privileged_access_approvals_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.privileged_access_approvals
    ADD CONSTRAINT privileged_access_approvals_pkey PRIMARY KEY (id);


--
-- Name: privileged_access_requests privileged_access_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.privileged_access_requests
    ADD CONSTRAINT privileged_access_requests_pkey PRIMARY KEY (id);


--
-- Name: realm_audit_log realm_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.realm_audit_log
    ADD CONSTRAINT realm_audit_log_pkey PRIMARY KEY (id);


--
-- Name: realm_capacity_history realm_capacity_history_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.realm_capacity_history
    ADD CONSTRAINT realm_capacity_history_pkey PRIMARY KEY (id);


--
-- Name: realms realms_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.realms
    ADD CONSTRAINT realms_pkey PRIMARY KEY (id);


--
-- Name: realms realms_realm_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.realms
    ADD CONSTRAINT realms_realm_name_key UNIQUE (realm_name);


--
-- Name: realms realms_region_realm_type_shard_number_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.realms
    ADD CONSTRAINT realms_region_realm_type_shard_number_key UNIQUE (region, realm_type, shard_number);


--
-- Name: remediation_metadata remediation_metadata_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.remediation_metadata
    ADD CONSTRAINT remediation_metadata_pkey PRIMARY KEY (id);


--
-- Name: scans scans_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.scans
    ADD CONSTRAINT scans_pkey PRIMARY KEY (id);


--
-- Name: secrets secrets_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.secrets
    ADD CONSTRAINT secrets_pkey PRIMARY KEY (id);


--
-- Name: secrets secrets_tenant_id_name_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.secrets
    ADD CONSTRAINT secrets_tenant_id_name_key UNIQUE (tenant_id, name);


--
-- Name: security_event_embeddings security_event_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.security_event_embeddings
    ADD CONSTRAINT security_event_embeddings_pkey PRIMARY KEY (id);


--
-- Name: tenant_control_status tenant_control_status_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_control_status
    ADD CONSTRAINT tenant_control_status_pkey PRIMARY KEY (id);


--
-- Name: tenant_control_status tenant_control_status_tenant_id_realm_name_control_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_control_status
    ADD CONSTRAINT tenant_control_status_tenant_id_realm_name_control_id_key UNIQUE (tenant_id, realm_name, control_id);


--
-- Name: tenant_detection_monitors tenant_detection_monitors_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_detection_monitors
    ADD CONSTRAINT tenant_detection_monitors_pkey PRIMARY KEY (id);


--
-- Name: tenant_detection_monitors tenant_detection_monitors_tenant_id_rule_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_detection_monitors
    ADD CONSTRAINT tenant_detection_monitors_tenant_id_rule_id_key UNIQUE (tenant_id, rule_id);


--
-- Name: tenant_model_adapters tenant_model_adapters_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_model_adapters
    ADD CONSTRAINT tenant_model_adapters_pkey PRIMARY KEY (id);


--
-- Name: tenant_model_adapters tenant_model_adapters_tenant_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_model_adapters
    ADD CONSTRAINT tenant_model_adapters_tenant_id_key UNIQUE (tenant_id);


--
-- Name: tenant_provisioning_log tenant_provisioning_log_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_provisioning_log
    ADD CONSTRAINT tenant_provisioning_log_pkey PRIMARY KEY (id);


--
-- Name: tenant_training_data tenant_training_data_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_training_data
    ADD CONSTRAINT tenant_training_data_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_slug_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_slug_key UNIQUE (slug);


--
-- Name: tool_registry tool_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tool_registry
    ADD CONSTRAINT tool_registry_pkey PRIMARY KEY (id);


--
-- Name: training_data_snapshots training_data_snapshots_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.training_data_snapshots
    ADD CONSTRAINT training_data_snapshots_pkey PRIMARY KEY (id);


--
-- Name: assets unique_asset_per_tenant; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT unique_asset_per_tenant UNIQUE (tenant_id, asset_id);


--
-- Name: vulnerabilities unique_cve_per_tenant; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vulnerabilities
    ADD CONSTRAINT unique_cve_per_tenant UNIQUE (tenant_id, cve_id);


--
-- Name: user_entitlements user_entitlements_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.user_entitlements
    ADD CONSTRAINT user_entitlements_pkey PRIMARY KEY (id);


--
-- Name: user_lifecycle_schedule user_lifecycle_schedule_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.user_lifecycle_schedule
    ADD CONSTRAINT user_lifecycle_schedule_pkey PRIMARY KEY (id);


--
-- Name: user_mfa_status user_mfa_status_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.user_mfa_status
    ADD CONSTRAINT user_mfa_status_pkey PRIMARY KEY (id);


--
-- Name: user_mfa_status user_mfa_status_tenant_id_realm_name_user_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.user_mfa_status
    ADD CONSTRAINT user_mfa_status_tenant_id_realm_name_user_id_key UNIQUE (tenant_id, realm_name, user_id);


--
-- Name: user_tenants user_tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.user_tenants
    ADD CONSTRAINT user_tenants_pkey PRIMARY KEY (id);


--
-- Name: user_tenants user_tenants_user_id_tenant_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.user_tenants
    ADD CONSTRAINT user_tenants_user_id_tenant_id_key UNIQUE (user_id, tenant_id);


--
-- Name: vault_access_grants vault_access_grants_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_access_grants
    ADD CONSTRAINT vault_access_grants_pkey PRIMARY KEY (id);


--
-- Name: vault_audit_log vault_audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_audit_log
    ADD CONSTRAINT vault_audit_log_pkey PRIMARY KEY (id);


--
-- Name: vault_customers vault_customers_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_customers
    ADD CONSTRAINT vault_customers_pkey PRIMARY KEY (customer_id);


--
-- Name: vault_customers vault_customers_vault_entity_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_customers
    ADD CONSTRAINT vault_customers_vault_entity_id_key UNIQUE (vault_entity_id);


--
-- Name: vault_customers vault_customers_vault_path_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_customers
    ADD CONSTRAINT vault_customers_vault_path_key UNIQUE (vault_path);


--
-- Name: vault_organizations vault_organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_organizations
    ADD CONSTRAINT vault_organizations_pkey PRIMARY KEY (organization_id);


--
-- Name: vault_organizations vault_organizations_vault_entity_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_organizations
    ADD CONSTRAINT vault_organizations_vault_entity_id_key UNIQUE (vault_entity_id);


--
-- Name: vault_organizations vault_organizations_vault_path_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_organizations
    ADD CONSTRAINT vault_organizations_vault_path_key UNIQUE (vault_path);


--
-- Name: vault_tenants vault_tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_tenants
    ADD CONSTRAINT vault_tenants_pkey PRIMARY KEY (tenant_id);


--
-- Name: vault_tenants vault_tenants_vault_entity_id_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_tenants
    ADD CONSTRAINT vault_tenants_vault_entity_id_key UNIQUE (vault_entity_id);


--
-- Name: vault_tenants vault_tenants_vault_path_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_tenants
    ADD CONSTRAINT vault_tenants_vault_path_key UNIQUE (vault_path);


--
-- Name: vault_usage_history vault_usage_history_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_usage_history
    ADD CONSTRAINT vault_usage_history_pkey PRIMARY KEY (id);


--
-- Name: version_compatibility version_compatibility_agent_version_image_version_key; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.version_compatibility
    ADD CONSTRAINT version_compatibility_agent_version_image_version_key UNIQUE (agent_version, image_version);


--
-- Name: version_compatibility version_compatibility_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.version_compatibility
    ADD CONSTRAINT version_compatibility_pkey PRIMARY KEY (id);


--
-- Name: vulnerabilities vulnerabilities_pkey; Type: CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vulnerabilities
    ADD CONSTRAINT vulnerabilities_pkey PRIMARY KEY (id);


--
-- Name: generated_reports generated_reports_pkey; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.generated_reports
    ADD CONSTRAINT generated_reports_pkey PRIMARY KEY (id);


--
-- Name: generated_reports generated_reports_tenant_id_realm_name_report_type_report_n_key; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.generated_reports
    ADD CONSTRAINT generated_reports_tenant_id_realm_name_report_type_report_n_key UNIQUE (tenant_id, realm_name, report_type, report_name);


--
-- Name: report_access_log report_access_log_pkey; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_access_log
    ADD CONSTRAINT report_access_log_pkey PRIMARY KEY (id);


--
-- Name: report_llm_documents report_llm_documents_pkey; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_llm_documents
    ADD CONSTRAINT report_llm_documents_pkey PRIMARY KEY (id);


--
-- Name: report_llm_documents report_llm_documents_report_id_chunk_index_key; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_llm_documents
    ADD CONSTRAINT report_llm_documents_report_id_chunk_index_key UNIQUE (report_id, chunk_index);


--
-- Name: report_schedules report_schedules_pkey; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_schedules
    ADD CONSTRAINT report_schedules_pkey PRIMARY KEY (id);


--
-- Name: report_schedules report_schedules_tenant_id_realm_name_report_type_schedule__key; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_schedules
    ADD CONSTRAINT report_schedules_tenant_id_realm_name_report_type_schedule__key UNIQUE (tenant_id, realm_name, report_type, schedule_name);


--
-- Name: report_shares report_shares_pkey; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_shares
    ADD CONSTRAINT report_shares_pkey PRIMARY KEY (id);


--
-- Name: report_shares report_shares_share_token_key; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_shares
    ADD CONSTRAINT report_shares_share_token_key UNIQUE (share_token);


--
-- Name: report_templates report_templates_pkey; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_templates
    ADD CONSTRAINT report_templates_pkey PRIMARY KEY (id);


--
-- Name: reports reports_pkey; Type: CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: alert_ai_analysis alert_ai_analysis_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.alert_ai_analysis
    ADD CONSTRAINT alert_ai_analysis_pkey PRIMARY KEY (id);


--
-- Name: alert_playbook_triggers alert_playbook_triggers_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.alert_playbook_triggers
    ADD CONSTRAINT alert_playbook_triggers_pkey PRIMARY KEY (id);


--
-- Name: alert_triage_feedback alert_triage_feedback_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.alert_triage_feedback
    ADD CONSTRAINT alert_triage_feedback_pkey PRIMARY KEY (id);


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: detection_bindings detection_bindings_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_bindings
    ADD CONSTRAINT detection_bindings_pkey PRIMARY KEY (id);


--
-- Name: detection_bindings detection_bindings_tenant_id_detection_rule_id_key; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_bindings
    ADD CONSTRAINT detection_bindings_tenant_id_detection_rule_id_key UNIQUE (tenant_id, detection_rule_id);


--
-- Name: detection_deduplication detection_deduplication_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_deduplication
    ADD CONSTRAINT detection_deduplication_pkey PRIMARY KEY (id);


--
-- Name: detection_playbook_mappings detection_playbook_mappings_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_playbook_mappings
    ADD CONSTRAINT detection_playbook_mappings_pkey PRIMARY KEY (id);


--
-- Name: detection_playbook_mappings detection_playbook_mappings_tenant_id_alert_type_key; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_playbook_mappings
    ADD CONSTRAINT detection_playbook_mappings_tenant_id_alert_type_key UNIQUE (tenant_id, alert_type);


--
-- Name: detection_playbook_mappings detection_playbook_mappings_tenant_id_rule_id_key; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_playbook_mappings
    ADD CONSTRAINT detection_playbook_mappings_tenant_id_rule_id_key UNIQUE (tenant_id, rule_id);


--
-- Name: detection_rule_executions detection_rule_executions_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_rule_executions
    ADD CONSTRAINT detection_rule_executions_pkey PRIMARY KEY (id);


--
-- Name: detection_rule_versions detection_rule_versions_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_rule_versions
    ADD CONSTRAINT detection_rule_versions_pkey PRIMARY KEY (id);


--
-- Name: detection_rule_versions detection_rule_versions_rule_id_version_key; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_rule_versions
    ADD CONSTRAINT detection_rule_versions_rule_id_version_key UNIQUE (rule_id, version);


--
-- Name: detection_rules detection_rules_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_rules
    ADD CONSTRAINT detection_rules_pkey PRIMARY KEY (id);


--
-- Name: detection_rules detection_rules_rule_key_tenant_uniq; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_rules
    ADD CONSTRAINT detection_rules_rule_key_tenant_uniq UNIQUE (rule_key, tenant_id);


--
-- Name: detection_suppression_events detection_suppression_events_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_suppression_events
    ADD CONSTRAINT detection_suppression_events_pkey PRIMARY KEY (id);


--
-- Name: detection_suppression_rules detection_suppression_rules_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_suppression_rules
    ADD CONSTRAINT detection_suppression_rules_pkey PRIMARY KEY (id);


--
-- Name: incident_actions incident_actions_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_actions
    ADD CONSTRAINT incident_actions_pkey PRIMARY KEY (id);


--
-- Name: incident_ai_summaries incident_ai_summaries_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_ai_summaries
    ADD CONSTRAINT incident_ai_summaries_pkey PRIMARY KEY (id);


--
-- Name: incident_alerts incident_alerts_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_alerts
    ADD CONSTRAINT incident_alerts_pkey PRIMARY KEY (incident_id, alert_id);


--
-- Name: incident_evidence incident_evidence_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_evidence
    ADD CONSTRAINT incident_evidence_pkey PRIMARY KEY (id);


--
-- Name: incident_lifecycle incident_lifecycle_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_lifecycle
    ADD CONSTRAINT incident_lifecycle_pkey PRIMARY KEY (id);


--
-- Name: incident_observables incident_observables_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_observables
    ADD CONSTRAINT incident_observables_pkey PRIMARY KEY (id);


--
-- Name: incident_timeline incident_timeline_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_timeline
    ADD CONSTRAINT incident_timeline_pkey PRIMARY KEY (id);


--
-- Name: incidents incidents_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incidents
    ADD CONSTRAINT incidents_pkey PRIMARY KEY (id);


--
-- Name: playbooks playbooks_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.playbooks
    ADD CONSTRAINT playbooks_pkey PRIMARY KEY (id);


--
-- Name: ticket_ai_enrichments ticket_ai_enrichments_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.ticket_ai_enrichments
    ADD CONSTRAINT ticket_ai_enrichments_pkey PRIMARY KEY (id);


--
-- Name: ticket_alerts ticket_alerts_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.ticket_alerts
    ADD CONSTRAINT ticket_alerts_pkey PRIMARY KEY (ticket_id, alert_id);


--
-- Name: ticket_vulnerabilities ticket_vulnerabilities_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.ticket_vulnerabilities
    ADD CONSTRAINT ticket_vulnerabilities_pkey PRIMARY KEY (ticket_id, vulnerability_id);


--
-- Name: tickets tickets_pkey; Type: CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY (id);


--
-- Name: idx_audit_stats_tenant_period; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_audit_stats_tenant_period ON audit.audit_log_statistics USING btree (tenant_id, period_start DESC);


--
-- Name: idx_platform_audit_action; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_action ON audit.platform_audit_logs USING btree (action);


--
-- Name: idx_platform_audit_actor; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_actor ON audit.platform_audit_logs USING btree (actor_user_id);


--
-- Name: idx_platform_audit_actor_timestamp; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_actor_timestamp ON audit.platform_audit_logs USING btree (actor_user_id, "timestamp" DESC);


--
-- Name: idx_platform_audit_category; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_category ON audit.platform_audit_logs USING btree (action_category);


--
-- Name: idx_platform_audit_resource; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_resource ON audit.platform_audit_logs USING btree (resource_type, resource_id);


--
-- Name: idx_platform_audit_success; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_success ON audit.platform_audit_logs USING btree (success);


--
-- Name: idx_platform_audit_tenant_realm; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_tenant_realm ON audit.platform_audit_logs USING btree (tenant_id, realm_name);


--
-- Name: idx_platform_audit_tenant_timestamp; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_tenant_timestamp ON audit.platform_audit_logs USING btree (tenant_id, "timestamp" DESC);


--
-- Name: idx_platform_audit_timestamp; Type: INDEX; Schema: audit; Owner: sg
--

CREATE INDEX idx_platform_audit_timestamp ON audit.platform_audit_logs USING btree ("timestamp" DESC);


--
-- Name: idx_scanner_registry_active; Type: INDEX; Schema: orchestration; Owner: sg
--

CREATE INDEX idx_scanner_registry_active ON orchestration.scanner_registry USING btree (active);


--
-- Name: idx_scanner_registry_name_version; Type: INDEX; Schema: orchestration; Owner: sg
--

CREATE INDEX idx_scanner_registry_name_version ON orchestration.scanner_registry USING btree (name, version);


--
-- Name: idx_scans_scanner; Type: INDEX; Schema: orchestration; Owner: sg
--

CREATE INDEX idx_scans_scanner ON orchestration.scans USING btree (scanner_id);


--
-- Name: idx_scans_status; Type: INDEX; Schema: orchestration; Owner: sg
--

CREATE INDEX idx_scans_status ON orchestration.scans USING btree (status);


--
-- Name: idx_scans_tenant; Type: INDEX; Schema: orchestration; Owner: sg
--

CREATE INDEX idx_scans_tenant ON orchestration.scans USING btree (tenant_id);


--
-- Name: idx_access_profiles_birthright; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_profiles_birthright ON public.access_profiles USING btree (is_birthright);


--
-- Name: idx_access_profiles_default; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_profiles_default ON public.access_profiles USING btree (is_default);


--
-- Name: idx_access_profiles_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_profiles_tenant ON public.access_profiles USING btree (tenant_id);


--
-- Name: idx_access_requests_entitlement; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_requests_entitlement ON public.access_requests USING btree (entitlement_id);


--
-- Name: idx_access_requests_requested_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_requests_requested_at ON public.access_requests USING btree (requested_at);


--
-- Name: idx_access_requests_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_requests_status ON public.access_requests USING btree (status);


--
-- Name: idx_access_requests_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_requests_tenant ON public.access_requests USING btree (tenant_id);


--
-- Name: idx_access_requests_user; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_requests_user ON public.access_requests USING btree (requested_by);


--
-- Name: idx_access_review_campaigns_dates; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_campaigns_dates ON public.access_review_campaigns USING btree (start_date, end_date);


--
-- Name: idx_access_review_campaigns_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_campaigns_status ON public.access_review_campaigns USING btree (status);


--
-- Name: idx_access_review_campaigns_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_campaigns_tenant_realm ON public.access_review_campaigns USING btree (tenant_id, realm_name);


--
-- Name: idx_access_review_campaigns_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_campaigns_type ON public.access_review_campaigns USING btree (campaign_type);


--
-- Name: idx_access_review_decisions_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_decisions_at ON public.access_review_decisions USING btree (decided_at DESC);


--
-- Name: idx_access_review_decisions_item; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_decisions_item ON public.access_review_decisions USING btree (review_item_id);


--
-- Name: idx_access_review_decisions_reviewer; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_decisions_reviewer ON public.access_review_decisions USING btree (reviewer_user_id);


--
-- Name: idx_access_review_decisions_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_decisions_tenant_realm ON public.access_review_decisions USING btree (tenant_id, realm_name);


--
-- Name: idx_access_review_items_campaign; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_items_campaign ON public.access_review_items USING btree (campaign_id);


--
-- Name: idx_access_review_items_decision; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_items_decision ON public.access_review_items USING btree (decision);


--
-- Name: idx_access_review_items_entitlement; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_items_entitlement ON public.access_review_items USING btree (entitlement_id);


--
-- Name: idx_access_review_items_reviewer; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_items_reviewer ON public.access_review_items USING btree (reviewer_user_id);


--
-- Name: idx_access_review_items_subject; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_items_subject ON public.access_review_items USING btree (subject_user_id);


--
-- Name: idx_access_review_items_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_items_tenant_realm ON public.access_review_items USING btree (tenant_id, realm_name);


--
-- Name: idx_access_review_stats_campaign; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_stats_campaign ON public.access_review_statistics USING btree (campaign_id);


--
-- Name: idx_access_review_stats_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_access_review_stats_tenant_realm ON public.access_review_statistics USING btree (tenant_id, realm_name);


--
-- Name: idx_adapters_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_adapters_status ON public.tenant_model_adapters USING btree (status);


--
-- Name: idx_adapters_tenant_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_adapters_tenant_status ON public.tenant_model_adapters USING btree (tenant_id, status);


--
-- Name: idx_agent_bootstrap_tokens_expires_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_agent_bootstrap_tokens_expires_at ON public.agent_bootstrap_tokens USING btree (expires_at);


--
-- Name: idx_agent_bootstrap_tokens_tenant_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_agent_bootstrap_tokens_tenant_id ON public.agent_bootstrap_tokens USING btree (tenant_id);


--
-- Name: idx_agent_bootstrap_tokens_token_hash; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_agent_bootstrap_tokens_token_hash ON public.agent_bootstrap_tokens USING btree (token_hash);


--
-- Name: idx_agent_versions_agent_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_agent_versions_agent_type ON public.agent_versions USING btree (agent_type);


--
-- Name: idx_agent_versions_latest; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_agent_versions_latest ON public.agent_versions USING btree (agent_type, is_latest) WHERE (is_latest = true);


--
-- Name: idx_agent_versions_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_agent_versions_status ON public.agent_versions USING btree (status);


--
-- Name: idx_agent_versions_type_latest; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_agent_versions_type_latest ON public.agent_versions USING btree (agent_type, is_latest) WHERE (is_latest = true);


--
-- Name: idx_agent_versions_upstream; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_agent_versions_upstream ON public.agent_versions USING btree (upstream_tool, upstream_version);


--
-- Name: idx_ai_apps_created; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_apps_created ON public.ai_apps USING btree (created_at DESC);


--
-- Name: idx_ai_apps_org; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_apps_org ON public.ai_apps USING btree (org_id);


--
-- Name: idx_ai_events_app_created; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_events_app_created ON public.ai_events USING btree (ai_app_id, created_at DESC);


--
-- Name: idx_ai_events_has_pii; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_events_has_pii ON public.ai_events USING btree (has_pii) WHERE (has_pii = true);


--
-- Name: idx_ai_events_has_secrets; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_events_has_secrets ON public.ai_events USING btree (has_secrets) WHERE (has_secrets = true);


--
-- Name: idx_ai_events_injection; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_events_injection ON public.ai_events USING btree (prompt_injection_suspected) WHERE (prompt_injection_suspected = true);


--
-- Name: idx_ai_events_org_created; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_events_org_created ON public.ai_events USING btree (org_id, created_at DESC);


--
-- Name: idx_ai_events_policy_decision; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_events_policy_decision ON public.ai_events USING btree (policy_decision);


--
-- Name: idx_ai_policies_app; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_policies_app ON public.ai_policies USING btree (ai_app_id);


--
-- Name: idx_ai_policies_org; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ai_policies_org ON public.ai_policies USING btree (org_id);


--
-- Name: idx_api_keys_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_api_keys_active ON public.api_keys USING btree (is_active);


--
-- Name: idx_api_keys_hash; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_api_keys_hash ON public.api_keys USING btree (key_hash);


--
-- Name: idx_api_keys_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_api_keys_tenant ON public.api_keys USING btree (tenant_id);


--
-- Name: idx_api_keys_user; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_api_keys_user ON public.api_keys USING btree (user_id);


--
-- Name: idx_app_catalog_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_app_catalog_active ON public.app_catalog USING btree (is_active);


--
-- Name: idx_app_catalog_category; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_app_catalog_category ON public.app_catalog USING btree (category);


--
-- Name: idx_app_catalog_name; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_app_catalog_name ON public.app_catalog USING btree (name);


--
-- Name: idx_approvals_approver; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_approvals_approver ON public.approvals USING btree (approver_id);


--
-- Name: idx_approvals_request; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_approvals_request ON public.approvals USING btree (access_request_id);


--
-- Name: idx_approvals_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_approvals_status ON public.approvals USING btree (status);


--
-- Name: idx_apps_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_apps_active ON public.apps USING btree (is_active);


--
-- Name: idx_apps_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_apps_tenant ON public.apps USING btree (tenant_id);


--
-- Name: idx_apps_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_apps_type ON public.apps USING btree (app_type);


--
-- Name: idx_assets_asset_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_assets_asset_id ON public.assets USING btree (asset_id);


--
-- Name: idx_assets_external_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_assets_external_id ON public.assets USING btree (external_id);


--
-- Name: idx_assets_hostname; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_assets_hostname ON public.assets USING btree (hostname);


--
-- Name: idx_assets_ip; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_assets_ip ON public.assets USING btree (ip_address);


--
-- Name: idx_assets_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_assets_tenant ON public.assets USING btree (tenant_id);


--
-- Name: idx_assets_tenant_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_assets_tenant_type ON public.assets USING btree (tenant_id, asset_type);


--
-- Name: idx_assets_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_assets_type ON public.assets USING btree (asset_type);


--
-- Name: idx_birthright_rules_attr; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_birthright_rules_attr ON public.birthright_rules USING btree (tenant_id, attribute_key);


--
-- Name: idx_birthright_rules_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_birthright_rules_tenant ON public.birthright_rules USING btree (tenant_id);


--
-- Name: idx_ca_authorities_name; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ca_authorities_name ON public.ca_authorities USING btree (name);


--
-- Name: idx_ca_authorities_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ca_authorities_status ON public.ca_authorities USING btree (status);


--
-- Name: idx_ca_authorities_tenant_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ca_authorities_tenant_id ON public.ca_authorities USING btree (tenant_id);


--
-- Name: idx_ca_authorities_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_ca_authorities_type ON public.ca_authorities USING btree (type);


--
-- Name: idx_certificate_requests_certificate_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificate_requests_certificate_id ON public.certificate_requests USING btree (certificate_id);


--
-- Name: idx_certificate_requests_requestor; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificate_requests_requestor ON public.certificate_requests USING btree (requestor_type, requestor_id);


--
-- Name: idx_certificate_requests_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificate_requests_status ON public.certificate_requests USING btree (status);


--
-- Name: idx_certificate_requests_tenant_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificate_requests_tenant_id ON public.certificate_requests USING btree (tenant_id);


--
-- Name: idx_certificates_agent_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_agent_id ON public.certificates USING btree (agent_id);


--
-- Name: idx_certificates_ca_authority_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_ca_authority_id ON public.certificates USING btree (ca_authority_id);


--
-- Name: idx_certificates_expires_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_expires_at ON public.certificates USING btree (expires_at);


--
-- Name: idx_certificates_serial_number; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_serial_number ON public.certificates USING btree (serial_number);


--
-- Name: idx_certificates_service_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_service_type ON public.certificates USING btree (service_type);


--
-- Name: idx_certificates_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_status ON public.certificates USING btree (status);


--
-- Name: idx_certificates_subject_cn; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_subject_cn ON public.certificates USING btree (subject_cn);


--
-- Name: idx_certificates_tenant_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_tenant_id ON public.certificates USING btree (tenant_id);


--
-- Name: idx_certificates_usage; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_certificates_usage ON public.certificates USING btree (usage);


--
-- Name: idx_compliance_controls_category; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_compliance_controls_category ON public.compliance_controls USING btree (control_category);


--
-- Name: idx_compliance_controls_framework; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_compliance_controls_framework ON public.compliance_controls USING btree (framework_id);


--
-- Name: idx_compliance_controls_parent; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_compliance_controls_parent ON public.compliance_controls USING btree (parent_control_id);


--
-- Name: idx_compliance_controls_priority; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_compliance_controls_priority ON public.compliance_controls USING btree (priority);


--
-- Name: idx_connected_apps_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_connected_apps_active ON public.connected_apps USING btree (is_active);


--
-- Name: idx_connected_apps_catalog; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_connected_apps_catalog ON public.connected_apps USING btree (catalog_app_id);


--
-- Name: idx_connected_apps_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_connected_apps_tenant ON public.connected_apps USING btree (tenant_id);


--
-- Name: idx_control_mappings_control; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_control_mappings_control ON public.control_mappings USING btree (control_id);


--
-- Name: idx_control_mappings_coverage; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_control_mappings_coverage ON public.control_mappings USING btree (coverage_level);


--
-- Name: idx_control_mappings_feature; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_control_mappings_feature ON public.control_mappings USING btree (sentinelgrid_feature);


--
-- Name: idx_customer_cloud_accounts_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_cloud_accounts_customer_id ON public.customer_cloud_accounts USING btree (customer_id);


--
-- Name: idx_customer_cloud_accounts_provider; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_cloud_accounts_provider ON public.customer_cloud_accounts USING btree (cloud_provider);


--
-- Name: idx_customer_cloud_accounts_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_cloud_accounts_status ON public.customer_cloud_accounts USING btree (status);


--
-- Name: idx_customer_endpoint_agents_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_endpoint_agents_customer_id ON public.customer_endpoint_agents USING btree (customer_id);


--
-- Name: idx_customer_endpoint_agents_last_seen; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_endpoint_agents_last_seen ON public.customer_endpoint_agents USING btree (last_seen_at);


--
-- Name: idx_customer_endpoint_agents_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_endpoint_agents_status ON public.customer_endpoint_agents USING btree (status);


--
-- Name: idx_customer_git_providers_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_git_providers_customer_id ON public.customer_git_providers USING btree (customer_id);


--
-- Name: idx_customer_git_providers_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_git_providers_status ON public.customer_git_providers USING btree (status);


--
-- Name: idx_customer_idp_config_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_idp_config_customer_id ON public.customer_idp_config USING btree (customer_id);


--
-- Name: idx_customer_idp_config_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customer_idp_config_status ON public.customer_idp_config USING btree (status);


--
-- Name: idx_customers_package_name; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_package_name ON public.customers USING btree (package_name);


--
-- Name: idx_customers_payment_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_payment_status ON public.customers USING btree (payment_status);


--
-- Name: idx_customers_pricing_tier; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_pricing_tier ON public.customers USING btree (pricing_tier);


--
-- Name: idx_customers_realm_name; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_realm_name ON public.customers USING btree (realm_name);


--
-- Name: idx_customers_region; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_region ON public.customers USING btree (region);


--
-- Name: idx_customers_signup_completed; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_signup_completed ON public.customers USING btree (signup_completed);


--
-- Name: idx_customers_slug; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_slug ON public.customers USING btree (slug);


--
-- Name: idx_customers_stripe_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_stripe_customer_id ON public.customers USING btree (stripe_customer_id);


--
-- Name: idx_customers_user_band; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_customers_user_band ON public.customers USING btree (user_band);


--
-- Name: idx_cyber_kb_category_subcategory; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_cyber_kb_category_subcategory ON public.cybersecurity_knowledge_base USING btree (category, subcategory);


--
-- Name: idx_cyber_kb_tenant_category; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_cyber_kb_tenant_category ON public.cybersecurity_knowledge_base USING btree (tenant_id, category);


--
-- Name: idx_devices_unique; Type: INDEX; Schema: public; Owner: sg
--

CREATE UNIQUE INDEX idx_devices_unique ON public.devices USING btree (tenant_id, device_id);


--
-- Name: idx_endpoint_agents_keepalive; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_agents_keepalive ON public.endpoint_agents USING btree (last_keepalive DESC);


--
-- Name: idx_endpoint_agents_name; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_agents_name ON public.endpoint_agents USING btree (agent_name);


--
-- Name: idx_endpoint_agents_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_agents_status ON public.endpoint_agents USING btree (tenant_id, status);


--
-- Name: idx_endpoint_agents_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_agents_tenant ON public.endpoint_agents USING btree (tenant_id);


--
-- Name: idx_endpoint_agents_wazuh_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_agents_wazuh_id ON public.endpoint_agents USING btree (wazuh_agent_id);


--
-- Name: idx_endpoint_events_agent; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_events_agent ON public.endpoint_agent_events USING btree (agent_id, "timestamp" DESC);


--
-- Name: idx_endpoint_events_hash; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_events_hash ON public.endpoint_agent_events USING btree (event_hash);


--
-- Name: idx_endpoint_events_rule; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_events_rule ON public.endpoint_agent_events USING btree (rule_id);


--
-- Name: idx_endpoint_events_severity; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_events_severity ON public.endpoint_agent_events USING btree (tenant_id, severity, "timestamp" DESC);


--
-- Name: idx_endpoint_events_tenant_time; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_events_tenant_time ON public.endpoint_agent_events USING btree (tenant_id, "timestamp" DESC);


--
-- Name: idx_endpoint_events_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_endpoint_events_type ON public.endpoint_agent_events USING btree (event_type, severity);


--
-- Name: idx_entitlement_mappings_entitlement; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_entitlement_mappings_entitlement ON public.entitlement_mappings USING btree (entitlement_id);


--
-- Name: idx_entitlement_mappings_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_entitlement_mappings_realm ON public.entitlement_mappings USING btree (realm_name);


--
-- Name: idx_entitlement_mappings_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_entitlement_mappings_tenant ON public.entitlement_mappings USING btree (tenant_id);


--
-- Name: idx_entitlements_app; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_entitlements_app ON public.entitlements USING btree (app_id);


--
-- Name: idx_entitlements_privileged; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_entitlements_privileged ON public.entitlements USING btree (is_privileged);


--
-- Name: idx_entitlements_risk; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_entitlements_risk ON public.entitlements USING btree (risk_level);


--
-- Name: idx_entitlements_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_entitlements_tenant ON public.entitlements USING btree (tenant_id);


--
-- Name: idx_evidence_items_collected; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_items_collected ON public.evidence_items USING btree (collected_at DESC);


--
-- Name: idx_evidence_items_control; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_items_control ON public.evidence_items USING btree (control_id);


--
-- Name: idx_evidence_items_package; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_items_package ON public.evidence_items USING btree (package_id);


--
-- Name: idx_evidence_items_source; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_items_source ON public.evidence_items USING btree (source_system);


--
-- Name: idx_evidence_items_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_items_tenant_realm ON public.evidence_items USING btree (tenant_id, realm_name);


--
-- Name: idx_evidence_items_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_items_type ON public.evidence_items USING btree (evidence_type);


--
-- Name: idx_evidence_packages_framework; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_packages_framework ON public.evidence_packages USING btree (framework_id);


--
-- Name: idx_evidence_packages_period; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_packages_period ON public.evidence_packages USING btree (report_period_start, report_period_end);


--
-- Name: idx_evidence_packages_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_packages_status ON public.evidence_packages USING btree (status);


--
-- Name: idx_evidence_packages_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_packages_tenant_realm ON public.evidence_packages USING btree (tenant_id, realm_name);


--
-- Name: idx_evidence_tasks_package; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_tasks_package ON public.evidence_collection_tasks USING btree (package_id);


--
-- Name: idx_evidence_tasks_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_tasks_status ON public.evidence_collection_tasks USING btree (status);


--
-- Name: idx_evidence_tasks_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_tasks_tenant_realm ON public.evidence_collection_tasks USING btree (tenant_id, realm_name);


--
-- Name: idx_evidence_tasks_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_evidence_tasks_type ON public.evidence_collection_tasks USING btree (task_type);


--
-- Name: idx_findings_asset; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_findings_asset ON public.findings USING btree (asset_id);


--
-- Name: idx_findings_category; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_findings_category ON public.findings USING btree (category);


--
-- Name: idx_findings_detected_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_findings_detected_at ON public.findings USING btree (detected_at);


--
-- Name: idx_findings_fingerprint; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_findings_fingerprint ON public.findings USING btree (fingerprint);


--
-- Name: idx_findings_scan_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_findings_scan_id ON public.findings USING btree (scan_id);


--
-- Name: idx_findings_scanner_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_findings_scanner_id ON public.findings USING btree (scanner_id);


--
-- Name: idx_findings_severity; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_findings_severity ON public.findings USING btree (severity);


--
-- Name: idx_findings_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_findings_tenant ON public.findings USING btree (tenant_id);


--
-- Name: idx_fix_group_assets_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_fix_group_assets_tenant ON public.fix_group_assets USING btree (tenant_id);


--
-- Name: idx_fix_group_assets_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_fix_group_assets_type ON public.fix_group_assets USING btree (asset_type);


--
-- Name: idx_fix_group_cves_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_fix_group_cves_tenant ON public.fix_group_cves USING btree (tenant_id);


--
-- Name: idx_fix_groups_priority; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_fix_groups_priority ON public.fix_groups USING btree (priority);


--
-- Name: idx_fix_groups_scan; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_fix_groups_scan ON public.fix_groups USING btree (scan_id);


--
-- Name: idx_fix_groups_sla; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_fix_groups_sla ON public.fix_groups USING btree (sla_due);


--
-- Name: idx_fix_groups_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_fix_groups_status ON public.fix_groups USING btree (status);


--
-- Name: idx_fix_groups_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_fix_groups_tenant ON public.fix_groups USING btree (tenant_id);


--
-- Name: idx_git_repositories_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_repositories_customer_id ON public.git_repositories USING btree (customer_id);


--
-- Name: idx_git_repositories_git_provider_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_repositories_git_provider_id ON public.git_repositories USING btree (git_provider_id);


--
-- Name: idx_git_repositories_scan_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_repositories_scan_status ON public.git_repositories USING btree (scan_status);


--
-- Name: idx_git_security_findings_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_findings_customer_id ON public.git_security_findings USING btree (customer_id);


--
-- Name: idx_git_security_findings_detected_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_findings_detected_at ON public.git_security_findings USING btree (detected_at);


--
-- Name: idx_git_security_findings_repo_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_findings_repo_id ON public.git_security_findings USING btree (repo_id);


--
-- Name: idx_git_security_findings_severity; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_findings_severity ON public.git_security_findings USING btree (severity);


--
-- Name: idx_git_security_findings_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_findings_status ON public.git_security_findings USING btree (status);


--
-- Name: idx_git_security_findings_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_findings_type ON public.git_security_findings USING btree (finding_type);


--
-- Name: idx_git_security_scans_created_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_scans_created_at ON public.git_security_scans USING btree (created_at);


--
-- Name: idx_git_security_scans_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_scans_customer_id ON public.git_security_scans USING btree (customer_id);


--
-- Name: idx_git_security_scans_repo_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_scans_repo_id ON public.git_security_scans USING btree (repo_id);


--
-- Name: idx_git_security_scans_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_git_security_scans_status ON public.git_security_scans USING btree (status);


--
-- Name: idx_hardened_images_agent_version; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_hardened_images_agent_version ON public.hardened_images USING btree (agent_version);


--
-- Name: idx_hardened_images_cloud_provider; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_hardened_images_cloud_provider ON public.hardened_images USING btree (cloud_provider);


--
-- Name: idx_hardened_images_latest; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_hardened_images_latest ON public.hardened_images USING btree (os_type, cis_level, cloud_provider, region, is_latest) WHERE (is_latest = true);


--
-- Name: idx_hardened_images_os_cloud; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_hardened_images_os_cloud ON public.hardened_images USING btree (os_type, os_version, cloud_provider);


--
-- Name: idx_hardened_images_os_flavor; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_hardened_images_os_flavor ON public.hardened_images USING btree (os_type);


--
-- Name: idx_hardened_images_region; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_hardened_images_region ON public.hardened_images USING btree (region);


--
-- Name: idx_hardened_images_scan_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_hardened_images_scan_status ON public.hardened_images USING btree (scan_status) WHERE ((scan_status)::text = 'passed'::text);


--
-- Name: idx_hardened_images_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_hardened_images_status ON public.hardened_images USING btree (status);


--
-- Name: idx_iam_audit_action; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_audit_action ON public.iam_audit_log USING btree (action);


--
-- Name: idx_iam_audit_actor; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_audit_actor ON public.iam_audit_log USING btree (actor_user_id);


--
-- Name: idx_iam_audit_created; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_audit_created ON public.iam_audit_log USING btree (created_at);


--
-- Name: idx_iam_audit_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_audit_realm ON public.iam_audit_log USING btree (realm_name);


--
-- Name: idx_iam_audit_target_user; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_audit_target_user ON public.iam_audit_log USING btree (target_user_id);


--
-- Name: idx_iam_audit_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_audit_tenant ON public.iam_audit_log USING btree (tenant_id);


--
-- Name: idx_iam_findings_nist_control; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_findings_nist_control ON public.iam_findings USING btree (tenant_id, nist_control_id) WHERE (nist_control_id IS NOT NULL);


--
-- Name: idx_iam_findings_remediation; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_findings_remediation ON public.iam_findings USING btree (tenant_id, remediation_status);


--
-- Name: idx_iam_findings_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_iam_findings_status ON public.iam_findings USING btree (tenant_id, status);


--
-- Name: idx_image_customer_sharing_account; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_image_customer_sharing_account ON public.image_customer_sharing USING btree (customer_account_id);


--
-- Name: idx_image_customer_sharing_image; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_image_customer_sharing_image ON public.image_customer_sharing USING btree (image_id);


--
-- Name: idx_image_customer_sharing_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_image_customer_sharing_status ON public.image_customer_sharing USING btree (share_status);


--
-- Name: idx_image_version_history_image; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_image_version_history_image ON public.image_version_history USING btree (image_id);


--
-- Name: idx_image_version_history_parent; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_image_version_history_parent ON public.image_version_history USING btree (parent_image_id);


--
-- Name: idx_integrations_tenant_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_integrations_tenant_id ON public.integrations USING btree (tenant_id);


--
-- Name: idx_jml_steps_order; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_steps_order ON public.jml_workflow_steps USING btree (workflow_id, step_order);


--
-- Name: idx_jml_steps_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_steps_status ON public.jml_workflow_steps USING btree (status);


--
-- Name: idx_jml_steps_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_steps_type ON public.jml_workflow_steps USING btree (step_type);


--
-- Name: idx_jml_steps_workflow; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_steps_workflow ON public.jml_workflow_steps USING btree (workflow_id);


--
-- Name: idx_jml_workflows_initiated_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_workflows_initiated_at ON public.jml_workflows USING btree (initiated_at DESC);


--
-- Name: idx_jml_workflows_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_workflows_status ON public.jml_workflows USING btree (status);


--
-- Name: idx_jml_workflows_subject; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_workflows_subject ON public.jml_workflows USING btree (subject_user_id);


--
-- Name: idx_jml_workflows_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_workflows_tenant_realm ON public.jml_workflows USING btree (tenant_id, realm_name);


--
-- Name: idx_jml_workflows_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jml_workflows_type ON public.jml_workflows USING btree (workflow_type);


--
-- Name: idx_jobs_job_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jobs_job_type ON public.jobs USING btree (job_type);


--
-- Name: idx_jobs_status_next_run; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jobs_status_next_run ON public.jobs USING btree (status, next_run_at);


--
-- Name: idx_jobs_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_jobs_tenant ON public.jobs USING btree (tenant_id);


--
-- Name: idx_leads_email; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_leads_email ON public.leads USING btree (email);


--
-- Name: idx_leads_expires_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_leads_expires_at ON public.leads USING btree (expires_at);


--
-- Name: idx_leads_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_leads_status ON public.leads USING btree (status);


--
-- Name: idx_leads_stripe_session; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_leads_stripe_session ON public.leads USING btree (stripe_session_id);


--
-- Name: idx_mfa_policies_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_mfa_policies_active ON public.mfa_enforcement_policies USING btree (is_active);


--
-- Name: idx_mfa_policies_scope; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_mfa_policies_scope ON public.mfa_enforcement_policies USING btree (enforcement_scope);


--
-- Name: idx_mfa_policies_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_mfa_policies_tenant_realm ON public.mfa_enforcement_policies USING btree (tenant_id, realm_name);


--
-- Name: idx_mfa_violations_detected; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_mfa_violations_detected ON public.mfa_compliance_violations USING btree (detected_at DESC);


--
-- Name: idx_mfa_violations_policy; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_mfa_violations_policy ON public.mfa_compliance_violations USING btree (policy_id);


--
-- Name: idx_mfa_violations_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_mfa_violations_status ON public.mfa_compliance_violations USING btree (status);


--
-- Name: idx_mfa_violations_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_mfa_violations_tenant_realm ON public.mfa_compliance_violations USING btree (tenant_id, realm_name);


--
-- Name: idx_mfa_violations_user; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_mfa_violations_user ON public.mfa_compliance_violations USING btree (user_id);


--
-- Name: idx_onboarding_progress_completed; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_onboarding_progress_completed ON public.onboarding_progress USING btree (onboarding_completed);


--
-- Name: idx_onboarding_progress_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_onboarding_progress_customer_id ON public.onboarding_progress USING btree (customer_id);


--
-- Name: idx_organizations_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_organizations_customer_id ON public.organizations USING btree (customer_id);


--
-- Name: idx_organizations_keycloak_org_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_organizations_keycloak_org_id ON public.organizations USING btree (keycloak_org_id) WHERE (keycloak_org_id IS NOT NULL);


--
-- Name: idx_organizations_parent_org_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_organizations_parent_org_id ON public.organizations USING btree (parent_org_id) WHERE (parent_org_id IS NOT NULL);


--
-- Name: idx_organizations_realm_name; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_organizations_realm_name ON public.organizations USING btree (realm_name);


--
-- Name: idx_pb_audit_execution; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_pb_audit_execution ON public.playbook_execution_audit USING btree (execution_id, execution_order);


--
-- Name: idx_pb_audit_incident; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_pb_audit_incident ON public.playbook_execution_audit USING btree (incident_id, started_at DESC);


--
-- Name: idx_phishing_observables_is_malicious; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_observables_is_malicious ON public.phishing_observables USING btree (is_malicious) WHERE (is_malicious = true);


--
-- Name: idx_phishing_observables_report_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_observables_report_id ON public.phishing_observables USING btree (phishing_report_id);


--
-- Name: idx_phishing_observables_tenant_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_observables_tenant_id ON public.phishing_observables USING btree (tenant_id);


--
-- Name: idx_phishing_observables_type_value; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_observables_type_value ON public.phishing_observables USING btree (observable_type, observable_value);


--
-- Name: idx_phishing_reports_classification; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_classification ON public.phishing_reports USING btree (classification);


--
-- Name: idx_phishing_reports_created_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_created_at ON public.phishing_reports USING btree (created_at DESC);


--
-- Name: idx_phishing_reports_incident_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_incident_id ON public.phishing_reports USING btree (incident_id);


--
-- Name: idx_phishing_reports_message_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_message_id ON public.phishing_reports USING btree (message_id);


--
-- Name: idx_phishing_reports_mitre_tactics; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_mitre_tactics ON public.phishing_reports USING gin (mitre_tactics);


--
-- Name: idx_phishing_reports_mitre_techniques; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_mitre_techniques ON public.phishing_reports USING gin (mitre_techniques);


--
-- Name: idx_phishing_reports_nist_controls; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_nist_controls ON public.phishing_reports USING gin (nist_controls);


--
-- Name: idx_phishing_reports_reported_by; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_reported_by ON public.phishing_reports USING btree (reported_by);


--
-- Name: idx_phishing_reports_similar_emails; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_similar_emails ON public.phishing_reports USING gin (similar_emails);


--
-- Name: idx_phishing_reports_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_status ON public.phishing_reports USING btree (status);


--
-- Name: idx_phishing_reports_tenant_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_tenant_id ON public.phishing_reports USING btree (tenant_id);


--
-- Name: idx_phishing_reports_ticket_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_phishing_reports_ticket_id ON public.phishing_reports USING btree (ticket_id);


--
-- Name: idx_playbook_analyzers_playbook; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbook_analyzers_playbook ON public.playbook_analyzers USING btree (playbook_id);


--
-- Name: idx_playbook_executions_alert; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbook_executions_alert ON public.playbook_executions USING btree (alert_id) WHERE (alert_id IS NOT NULL);


--
-- Name: idx_playbook_executions_triggered_by; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbook_executions_triggered_by ON public.playbook_executions USING btree (tenant_id, triggered_by);


--
-- Name: idx_playbook_observables_playbook; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbook_observables_playbook ON public.playbook_observables USING btree (playbook_id);


--
-- Name: idx_playbooks_auto_trigger; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbooks_auto_trigger ON public.playbooks USING btree (tenant_id, auto_trigger_enabled) WHERE (auto_trigger_enabled = true);


--
-- Name: idx_playbooks_builtin_key_unique; Type: INDEX; Schema: public; Owner: sg
--

CREATE UNIQUE INDEX idx_playbooks_builtin_key_unique ON public.playbooks USING btree (playbook_key) WHERE (is_builtin = true);


--
-- Name: idx_playbooks_category_filter; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbooks_category_filter ON public.playbooks USING gin (category_filter);


--
-- Name: idx_playbooks_is_builtin; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbooks_is_builtin ON public.playbooks USING btree (is_builtin);


--
-- Name: idx_playbooks_key; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbooks_key ON public.playbooks USING btree (key);


--
-- Name: idx_playbooks_playbook_key; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbooks_playbook_key ON public.playbooks USING btree (playbook_key);


--
-- Name: idx_playbooks_soc2_criteria; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbooks_soc2_criteria ON public.playbooks USING gin (soc2_criteria);


--
-- Name: idx_playbooks_trigger_priority; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_playbooks_trigger_priority ON public.playbooks USING btree (tenant_id, trigger_priority DESC) WHERE (auto_trigger_enabled = true);


--
-- Name: idx_policies_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policies_active ON public.policies USING btree (is_active);


--
-- Name: idx_policies_priority; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policies_priority ON public.policies USING btree (priority);


--
-- Name: idx_policies_scope; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policies_scope ON public.policies USING btree (scope, scope_id);


--
-- Name: idx_policies_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policies_tenant ON public.policies USING btree (tenant_id);


--
-- Name: idx_policies_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policies_type ON public.policies USING btree (policy_type);


--
-- Name: idx_policy_conflicts_policy1; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_conflicts_policy1 ON public.policy_conflicts USING btree (policy_id_1);


--
-- Name: idx_policy_conflicts_policy2; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_conflicts_policy2 ON public.policy_conflicts USING btree (policy_id_2);


--
-- Name: idx_policy_conflicts_resolved; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_conflicts_resolved ON public.policy_conflicts USING btree (resolved_at);


--
-- Name: idx_policy_conflicts_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_conflicts_tenant ON public.policy_conflicts USING btree (tenant_id);


--
-- Name: idx_policy_evaluations_evaluated_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_evaluations_evaluated_at ON public.policy_evaluations USING btree (evaluated_at);


--
-- Name: idx_policy_evaluations_policy; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_evaluations_policy ON public.policy_evaluations USING btree (policy_id);


--
-- Name: idx_policy_evaluations_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_evaluations_tenant ON public.policy_evaluations USING btree (tenant_id);


--
-- Name: idx_policy_evaluations_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_evaluations_type ON public.policy_evaluations USING btree (evaluation_type);


--
-- Name: idx_policy_rules_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_rules_active ON public.policy_rules USING btree (is_active);


--
-- Name: idx_policy_rules_policy; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_rules_policy ON public.policy_rules USING btree (policy_id);


--
-- Name: idx_policy_templates_category; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_templates_category ON public.policy_templates USING btree (category);


--
-- Name: idx_policy_templates_tenant_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_templates_tenant_type ON public.policy_templates USING btree (tenant_id, policy_type);


--
-- Name: idx_policy_templates_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_policy_templates_type ON public.policy_templates USING btree (policy_type);


--
-- Name: idx_posture_findings_nist_control; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_posture_findings_nist_control ON public.posture_findings USING btree (tenant_id, nist_control_id) WHERE (nist_control_id IS NOT NULL);


--
-- Name: idx_posture_findings_remediation; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_posture_findings_remediation ON public.posture_findings USING btree (tenant_id, remediation_status);


--
-- Name: idx_posture_findings_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_posture_findings_status ON public.posture_findings USING btree (tenant_id, status);


--
-- Name: idx_privileged_access_approvals_approver; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_privileged_access_approvals_approver ON public.privileged_access_approvals USING btree (approver_id);


--
-- Name: idx_privileged_access_approvals_request; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_privileged_access_approvals_request ON public.privileged_access_approvals USING btree (request_id);


--
-- Name: idx_privileged_access_expires_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_privileged_access_expires_at ON public.privileged_access_requests USING btree (expires_at);


--
-- Name: idx_privileged_access_requested_by; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_privileged_access_requested_by ON public.privileged_access_requests USING btree (requested_by);


--
-- Name: idx_privileged_access_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_privileged_access_status ON public.privileged_access_requests USING btree (status);


--
-- Name: idx_privileged_access_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_privileged_access_tenant ON public.privileged_access_requests USING btree (tenant_id);


--
-- Name: idx_profile_entitlements_entitlement; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_profile_entitlements_entitlement ON public.access_profile_entitlements USING btree (entitlement_id);


--
-- Name: idx_profile_entitlements_profile; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_profile_entitlements_profile ON public.access_profile_entitlements USING btree (access_profile_id);


--
-- Name: idx_provider_creds_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_provider_creds_active ON public.ai_provider_credentials USING btree (org_id, is_active) WHERE (is_active = true);


--
-- Name: idx_provider_creds_org; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_provider_creds_org ON public.ai_provider_credentials USING btree (org_id, provider);


--
-- Name: idx_provider_creds_validation; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_provider_creds_validation ON public.ai_provider_credentials USING btree (last_validated) WHERE (is_active = true);


--
-- Name: idx_realm_audit_action; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realm_audit_action ON public.realm_audit_log USING btree (action);


--
-- Name: idx_realm_audit_actor; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realm_audit_actor ON public.realm_audit_log USING btree (actor_user_id);


--
-- Name: idx_realm_audit_created; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realm_audit_created ON public.realm_audit_log USING btree (created_at);


--
-- Name: idx_realm_audit_customer; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realm_audit_customer ON public.realm_audit_log USING btree (customer_id);


--
-- Name: idx_realm_audit_org; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realm_audit_org ON public.realm_audit_log USING btree (organization_id);


--
-- Name: idx_realm_audit_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realm_audit_realm ON public.realm_audit_log USING btree (realm_name);


--
-- Name: idx_realm_capacity_history_realm_time; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realm_capacity_history_realm_time ON public.realm_capacity_history USING btree (realm_name, recorded_at DESC);


--
-- Name: idx_realms_region_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realms_region_type ON public.realms USING btree (region, realm_type, status);


--
-- Name: idx_realms_tenant_count; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_realms_tenant_count ON public.realms USING btree (tenant_count) WHERE ((realm_type)::text = 'multi_tenant'::text);


--
-- Name: idx_remediation_metadata_execution; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_remediation_metadata_execution ON public.remediation_metadata USING btree (playbook_execution_id) WHERE (playbook_execution_id IS NOT NULL);


--
-- Name: idx_remediation_metadata_finding; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_remediation_metadata_finding ON public.remediation_metadata USING btree (finding_id, finding_type);


--
-- Name: idx_remediation_metadata_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_remediation_metadata_status ON public.remediation_metadata USING btree (tenant_id, status);


--
-- Name: idx_scans_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_scans_status ON public.scans USING btree (status);


--
-- Name: idx_scans_tenant_created_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_scans_tenant_created_at ON public.scans USING btree (tenant_id, created_at DESC);


--
-- Name: idx_secrets_next_rotation; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_secrets_next_rotation ON public.secrets USING btree (next_rotation_at);


--
-- Name: idx_secrets_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_secrets_tenant ON public.secrets USING btree (tenant_id);


--
-- Name: idx_secrets_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_secrets_type ON public.secrets USING btree (secret_type);


--
-- Name: idx_security_event_embeddings_tenant_source; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_security_event_embeddings_tenant_source ON public.security_event_embeddings USING btree (tenant_id, source);


--
-- Name: idx_security_event_embeddings_unique; Type: INDEX; Schema: public; Owner: sg
--

CREATE UNIQUE INDEX idx_security_event_embeddings_unique ON public.security_event_embeddings USING btree (tenant_id, source, os_id_ref);


--
-- Name: idx_snapshots_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_snapshots_tenant ON public.training_data_snapshots USING btree (tenant_id, created_at DESC);


--
-- Name: idx_tenant_control_status_control; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_control_status_control ON public.tenant_control_status USING btree (control_id);


--
-- Name: idx_tenant_control_status_evidence; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_control_status_evidence ON public.tenant_control_status USING btree (evidence_collected);


--
-- Name: idx_tenant_control_status_implementation; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_control_status_implementation ON public.tenant_control_status USING btree (implementation_status);


--
-- Name: idx_tenant_control_status_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_control_status_tenant_realm ON public.tenant_control_status USING btree (tenant_id, realm_name);


--
-- Name: idx_tenant_monitors_rule; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_monitors_rule ON public.tenant_detection_monitors USING btree (rule_id);


--
-- Name: idx_tenant_monitors_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_monitors_tenant ON public.tenant_detection_monitors USING btree (tenant_id);


--
-- Name: idx_tenant_provisioning_log_created_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_provisioning_log_created_at ON public.tenant_provisioning_log USING btree (created_at DESC);


--
-- Name: idx_tenant_provisioning_log_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_provisioning_log_customer_id ON public.tenant_provisioning_log USING btree (customer_id);


--
-- Name: idx_tenant_provisioning_log_tenant_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenant_provisioning_log_tenant_id ON public.tenant_provisioning_log USING btree (tenant_id);


--
-- Name: idx_tenants_customer_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenants_customer_id ON public.tenants USING btree (customer_id);


--
-- Name: idx_tenants_organization_id; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenants_organization_id ON public.tenants USING btree (organization_id);


--
-- Name: idx_tenants_realm_name; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenants_realm_name ON public.tenants USING btree (realm_name);


--
-- Name: idx_tenants_region; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tenants_region ON public.tenants USING btree (region);


--
-- Name: idx_tool_registry_category; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tool_registry_category ON public.tool_registry USING btree (category);


--
-- Name: idx_tool_registry_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_tool_registry_status ON public.tool_registry USING btree (status);


--
-- Name: idx_training_created_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_training_created_at ON public.tenant_training_data USING btree (created_at DESC);


--
-- Name: idx_training_jobs_created_at; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_training_jobs_created_at ON public.adapter_training_jobs USING btree (created_at DESC);


--
-- Name: idx_training_jobs_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_training_jobs_status ON public.adapter_training_jobs USING btree (status);


--
-- Name: idx_training_jobs_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_training_jobs_tenant ON public.adapter_training_jobs USING btree (tenant_id, status);


--
-- Name: idx_training_tenant_module; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_training_tenant_module ON public.tenant_training_data USING btree (tenant_id, module);


--
-- Name: idx_training_tenant_type; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_training_tenant_type ON public.tenant_training_data USING btree (tenant_id, data_type);


--
-- Name: idx_user_entitlements_entitlement; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_entitlements_entitlement ON public.user_entitlements USING btree (entitlement_id);


--
-- Name: idx_user_entitlements_expires; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_entitlements_expires ON public.user_entitlements USING btree (expires_at);


--
-- Name: idx_user_entitlements_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_entitlements_status ON public.user_entitlements USING btree (status);


--
-- Name: idx_user_entitlements_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_entitlements_tenant ON public.user_entitlements USING btree (tenant_id);


--
-- Name: idx_user_entitlements_user; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_entitlements_user ON public.user_entitlements USING btree (user_id);


--
-- Name: idx_user_lifecycle_activate; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_lifecycle_activate ON public.user_lifecycle_schedule USING btree (tenant_id, activate_at);


--
-- Name: idx_user_lifecycle_deactivate; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_lifecycle_deactivate ON public.user_lifecycle_schedule USING btree (tenant_id, deactivate_at);


--
-- Name: idx_user_lifecycle_unique; Type: INDEX; Schema: public; Owner: sg
--

CREATE UNIQUE INDEX idx_user_lifecycle_unique ON public.user_lifecycle_schedule USING btree (tenant_id, user_id);


--
-- Name: idx_user_mfa_status_enabled; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_mfa_status_enabled ON public.user_mfa_status USING btree (mfa_enabled);


--
-- Name: idx_user_mfa_status_enforcement; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_mfa_status_enforcement ON public.user_mfa_status USING btree (enforcement_status);


--
-- Name: idx_user_mfa_status_policy; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_mfa_status_policy ON public.user_mfa_status USING btree (applicable_policy_id);


--
-- Name: idx_user_mfa_status_tenant_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_mfa_status_tenant_realm ON public.user_mfa_status USING btree (tenant_id, realm_name);


--
-- Name: idx_user_mfa_status_user; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_mfa_status_user ON public.user_mfa_status USING btree (user_id);


--
-- Name: idx_user_tenants_customer; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_tenants_customer ON public.user_tenants USING btree (customer_id);


--
-- Name: idx_user_tenants_org; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_tenants_org ON public.user_tenants USING btree (organization_id);


--
-- Name: idx_user_tenants_realm; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_tenants_realm ON public.user_tenants USING btree (realm_name);


--
-- Name: idx_user_tenants_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_tenants_tenant ON public.user_tenants USING btree (tenant_id);


--
-- Name: idx_user_tenants_user; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_user_tenants_user ON public.user_tenants USING btree (user_id);


--
-- Name: idx_vault_access_active; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_access_active ON public.vault_access_grants USING btree (user_id, tenant_id) WHERE (revoked_at IS NULL);


--
-- Name: idx_vault_access_level; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_access_level ON public.vault_access_grants USING btree (access_level);


--
-- Name: idx_vault_access_user_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_access_user_tenant ON public.vault_access_grants USING btree (user_id, tenant_id);


--
-- Name: idx_vault_audit_operation; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_audit_operation ON public.vault_audit_log USING btree (operation, created_at DESC);


--
-- Name: idx_vault_audit_scope; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_audit_scope ON public.vault_audit_log USING btree (scope, created_at DESC);


--
-- Name: idx_vault_audit_success; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_audit_success ON public.vault_audit_log USING btree (success, created_at DESC) WHERE (success = false);


--
-- Name: idx_vault_audit_tenant_time; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_audit_tenant_time ON public.vault_audit_log USING btree (tenant_id, created_at DESC);


--
-- Name: idx_vault_customers_entity; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_customers_entity ON public.vault_customers USING btree (vault_entity_id);


--
-- Name: idx_vault_orgs_customer; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_orgs_customer ON public.vault_organizations USING btree (customer_id);


--
-- Name: idx_vault_orgs_entity; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_orgs_entity ON public.vault_organizations USING btree (vault_entity_id);


--
-- Name: idx_vault_tenants_customer; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_tenants_customer ON public.vault_tenants USING btree (customer_id);


--
-- Name: idx_vault_tenants_entity; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_tenants_entity ON public.vault_tenants USING btree (vault_entity_id);


--
-- Name: idx_vault_tenants_org; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_tenants_org ON public.vault_tenants USING btree (organization_id);


--
-- Name: idx_vault_usage_customer; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_usage_customer ON public.vault_usage_history USING btree (customer_id, period_start DESC);


--
-- Name: idx_vault_usage_tenant_time; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vault_usage_tenant_time ON public.vault_usage_history USING btree (tenant_id, period_start DESC);


--
-- Name: idx_version_compatibility_agent; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_version_compatibility_agent ON public.version_compatibility USING btree (agent_version);


--
-- Name: idx_version_compatibility_image; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_version_compatibility_image ON public.version_compatibility USING btree (image_version);


--
-- Name: idx_version_compatibility_status; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_version_compatibility_status ON public.version_compatibility USING btree (compatibility_status);


--
-- Name: idx_version_history_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_version_history_tenant ON public.adapter_version_history USING btree (tenant_id, adapter_version);


--
-- Name: idx_vulnerabilities_cve; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vulnerabilities_cve ON public.vulnerabilities USING btree (cve_id);


--
-- Name: idx_vulnerabilities_exploit; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vulnerabilities_exploit ON public.vulnerabilities USING btree (exploit_available);


--
-- Name: idx_vulnerabilities_severity; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vulnerabilities_severity ON public.vulnerabilities USING btree (cvss_severity);


--
-- Name: idx_vulnerabilities_tenant; Type: INDEX; Schema: public; Owner: sg
--

CREATE INDEX idx_vulnerabilities_tenant ON public.vulnerabilities USING btree (tenant_id);


--
-- Name: idx_generated_reports_generated_at; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_generated_reports_generated_at ON reporting.generated_reports USING btree (generated_at DESC);


--
-- Name: idx_generated_reports_llm; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_generated_reports_llm ON reporting.generated_reports USING btree (llm_ingested);


--
-- Name: idx_generated_reports_status; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_generated_reports_status ON reporting.generated_reports USING btree (status);


--
-- Name: idx_generated_reports_tenant_realm; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_generated_reports_tenant_realm ON reporting.generated_reports USING btree (tenant_id, realm_name);


--
-- Name: idx_generated_reports_type; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_generated_reports_type ON reporting.generated_reports USING btree (report_type);


--
-- Name: idx_llm_docs_report; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_llm_docs_report ON reporting.report_llm_documents USING btree (report_id);


--
-- Name: idx_llm_docs_tenant_realm; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_llm_docs_tenant_realm ON reporting.report_llm_documents USING btree (tenant_id, realm_name);


--
-- Name: idx_report_access_at; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_access_at ON reporting.report_access_log USING btree (accessed_at DESC);


--
-- Name: idx_report_access_report; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_access_report ON reporting.report_access_log USING btree (report_id);


--
-- Name: idx_report_access_tenant_realm; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_access_tenant_realm ON reporting.report_access_log USING btree (tenant_id, realm_name);


--
-- Name: idx_report_access_type; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_access_type ON reporting.report_access_log USING btree (access_type);


--
-- Name: idx_report_access_user; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_access_user ON reporting.report_access_log USING btree (user_id);


--
-- Name: idx_report_schedules_active; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_schedules_active ON reporting.report_schedules USING btree (is_active);


--
-- Name: idx_report_schedules_next_run; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_schedules_next_run ON reporting.report_schedules USING btree (next_run_at);


--
-- Name: idx_report_schedules_tenant_realm; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_schedules_tenant_realm ON reporting.report_schedules USING btree (tenant_id, realm_name);


--
-- Name: idx_report_schedules_type; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_schedules_type ON reporting.report_schedules USING btree (report_type);


--
-- Name: idx_report_shares_report_id; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_shares_report_id ON reporting.report_shares USING btree (report_id);


--
-- Name: idx_report_shares_tenant_id; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_shares_tenant_id ON reporting.report_shares USING btree (tenant_id);


--
-- Name: idx_report_templates_tenant_id; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_report_templates_tenant_id ON reporting.report_templates USING btree (tenant_id);


--
-- Name: idx_reports_created_at; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_reports_created_at ON reporting.reports USING btree (created_at DESC);


--
-- Name: idx_reports_status; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_reports_status ON reporting.reports USING btree (status);


--
-- Name: idx_reports_tenant_id; Type: INDEX; Schema: reporting; Owner: sg
--

CREATE INDEX idx_reports_tenant_id ON reporting.reports USING btree (tenant_id);


--
-- Name: detection_rules_rule_key_builtin_uniq; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE UNIQUE INDEX detection_rules_rule_key_builtin_uniq ON security_ops.detection_rules USING btree (rule_key) WHERE (is_builtin = true);


--
-- Name: idx_actions_incident; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_actions_incident ON security_ops.incident_actions USING btree (incident_id, "timestamp" DESC);


--
-- Name: idx_actions_target; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_actions_target ON security_ops.incident_actions USING btree (target_entity_type, target_entity_id);


--
-- Name: idx_alert_playbook_triggers_alert; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alert_playbook_triggers_alert ON security_ops.alert_playbook_triggers USING btree (alert_id);


--
-- Name: idx_alert_playbook_triggers_execution; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alert_playbook_triggers_execution ON security_ops.alert_playbook_triggers USING btree (playbook_execution_id) WHERE (playbook_execution_id IS NOT NULL);


--
-- Name: idx_alert_playbook_triggers_playbook; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alert_playbook_triggers_playbook ON security_ops.alert_playbook_triggers USING btree (playbook_id);


--
-- Name: idx_alert_playbook_triggers_tenant; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alert_playbook_triggers_tenant ON security_ops.alert_playbook_triggers USING btree (tenant_id);


--
-- Name: idx_alerts_cve_ids; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alerts_cve_ids ON security_ops.alerts USING gin (cve_ids);


--
-- Name: idx_alerts_detection_time; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alerts_detection_time ON security_ops.alerts USING btree (detection_time);


--
-- Name: idx_alerts_mitre_tactics; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alerts_mitre_tactics ON security_ops.alerts USING gin (mitre_tactics);


--
-- Name: idx_alerts_mitre_techniques; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alerts_mitre_techniques ON security_ops.alerts USING gin (mitre_techniques);


--
-- Name: idx_alerts_nist_controls; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alerts_nist_controls ON security_ops.alerts USING gin (nist_controls);


--
-- Name: idx_alerts_status; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alerts_status ON security_ops.alerts USING btree (status);


--
-- Name: idx_alerts_tenant_id; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_alerts_tenant_id ON security_ops.alerts USING btree (tenant_id);


--
-- Name: idx_dedup_active; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_dedup_active ON security_ops.detection_deduplication USING btree (tenant_id, dedup_key, last_seen DESC) WHERE (status = 'active'::text);


--
-- Name: idx_dedup_key; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_dedup_key ON security_ops.detection_deduplication USING btree (tenant_id, rule_id, dedup_key);


--
-- Name: idx_dedup_status; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_dedup_status ON security_ops.detection_deduplication USING btree (tenant_id, status, last_seen DESC);


--
-- Name: idx_detection_bindings_scope; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_detection_bindings_scope ON security_ops.detection_bindings USING btree (scope);


--
-- Name: idx_detection_bindings_tenant; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_detection_bindings_tenant ON security_ops.detection_bindings USING btree (tenant_id);


--
-- Name: idx_enrichments_status; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_enrichments_status ON security_ops.ticket_ai_enrichments USING btree (status);


--
-- Name: idx_enrichments_tenant; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_enrichments_tenant ON security_ops.ticket_ai_enrichments USING btree (tenant_id);


--
-- Name: idx_enrichments_ticket; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_enrichments_ticket ON security_ops.ticket_ai_enrichments USING btree (ticket_id);


--
-- Name: idx_enrichments_type; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_enrichments_type ON security_ops.ticket_ai_enrichments USING btree (enrichment_type);


--
-- Name: idx_evidence_incident; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_evidence_incident ON security_ops.incident_evidence USING btree (incident_id, collected_at DESC);


--
-- Name: idx_incidents_cve_ids; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_incidents_cve_ids ON security_ops.incidents USING gin (cve_ids);


--
-- Name: idx_incidents_mitre_tactics; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_incidents_mitre_tactics ON security_ops.incidents USING gin (mitre_tactics);


--
-- Name: idx_incidents_mitre_techniques; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_incidents_mitre_techniques ON security_ops.incidents USING gin (mitre_techniques);


--
-- Name: idx_incidents_nist_controls; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_incidents_nist_controls ON security_ops.incidents USING gin (nist_controls);


--
-- Name: idx_incidents_status; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_incidents_status ON security_ops.incidents USING btree (status);


--
-- Name: idx_incidents_tenant_id; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_incidents_tenant_id ON security_ops.incidents USING btree (tenant_id);


--
-- Name: idx_lifecycle_incident; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_lifecycle_incident ON security_ops.incident_lifecycle USING btree (incident_id);


--
-- Name: idx_lifecycle_rule; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_lifecycle_rule ON security_ops.incident_lifecycle USING btree (rule_id);


--
-- Name: idx_observables_incident; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_observables_incident ON security_ops.incident_observables USING btree (incident_id);


--
-- Name: idx_observables_value; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_observables_value ON security_ops.incident_observables USING btree (observable_type, observable_value);


--
-- Name: idx_playbook_mappings_alert_type; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_playbook_mappings_alert_type ON security_ops.detection_playbook_mappings USING btree (alert_type);


--
-- Name: idx_playbook_mappings_tenant; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_playbook_mappings_tenant ON security_ops.detection_playbook_mappings USING btree (tenant_id);


--
-- Name: idx_playbooks_soc2_criteria; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_playbooks_soc2_criteria ON security_ops.playbooks USING gin (soc2_criteria);


--
-- Name: idx_rule_executions_rule; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_rule_executions_rule ON security_ops.detection_rule_executions USING btree (rule_id, fired_at DESC);


--
-- Name: idx_rule_executions_tenant; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_rule_executions_tenant ON security_ops.detection_rule_executions USING btree (tenant_id, fired_at DESC);


--
-- Name: idx_suppression_events_dedup; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_suppression_events_dedup ON security_ops.detection_suppression_events USING btree (dedup_id);


--
-- Name: idx_suppression_events_tenant; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_suppression_events_tenant ON security_ops.detection_suppression_events USING btree (tenant_id, suppressed_at DESC);


--
-- Name: idx_suppression_rules_tenant; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_suppression_rules_tenant ON security_ops.detection_suppression_rules USING btree (tenant_id, enabled);


--
-- Name: idx_tickets_cve_ids; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_tickets_cve_ids ON security_ops.tickets USING gin (cve_ids);


--
-- Name: idx_tickets_external_id; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_tickets_external_id ON security_ops.tickets USING btree (external_id);


--
-- Name: idx_tickets_mitre_tactics; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_tickets_mitre_tactics ON security_ops.tickets USING gin (mitre_tactics);


--
-- Name: idx_tickets_mitre_techniques; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_tickets_mitre_techniques ON security_ops.tickets USING gin (mitre_techniques);


--
-- Name: idx_tickets_nist_controls; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_tickets_nist_controls ON security_ops.tickets USING gin (nist_controls);


--
-- Name: idx_tickets_severity; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_tickets_severity ON security_ops.tickets USING btree (severity);


--
-- Name: idx_tickets_status; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_tickets_status ON security_ops.tickets USING btree (status);


--
-- Name: idx_tickets_tenant; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_tickets_tenant ON security_ops.tickets USING btree (tenant_id);


--
-- Name: idx_timeline_actor; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_timeline_actor ON security_ops.incident_timeline USING btree (actor_id, "timestamp" DESC);


--
-- Name: idx_timeline_incident; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_timeline_incident ON security_ops.incident_timeline USING btree (incident_id, "timestamp" DESC);


--
-- Name: idx_timeline_type; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE INDEX idx_timeline_type ON security_ops.incident_timeline USING btree (incident_id, event_type);


--
-- Name: playbooks_tenant_key_uniq; Type: INDEX; Schema: security_ops; Owner: sg
--

CREATE UNIQUE INDEX playbooks_tenant_key_uniq ON security_ops.playbooks USING btree (tenant_id, key);


--
-- Name: tenants trigger_check_realm_capacity; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER trigger_check_realm_capacity BEFORE INSERT ON public.tenants FOR EACH ROW EXECUTE FUNCTION public.check_realm_capacity();


--
-- Name: ai_provider_credentials trigger_update_ai_provider_credentials_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER trigger_update_ai_provider_credentials_updated_at BEFORE UPDATE ON public.ai_provider_credentials FOR EACH ROW EXECUTE FUNCTION public.update_ai_provider_credentials_updated_at();


--
-- Name: tenants trigger_update_customer_counts; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER trigger_update_customer_counts AFTER INSERT OR DELETE ON public.tenants FOR EACH ROW EXECUTE FUNCTION public.update_customer_counts();


--
-- Name: tenants trigger_update_realm_tenant_count; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER trigger_update_realm_tenant_count AFTER INSERT OR DELETE OR UPDATE ON public.tenants FOR EACH ROW EXECUTE FUNCTION public.update_realm_tenant_count();


--
-- Name: vault_audit_log trigger_update_vault_quota; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER trigger_update_vault_quota AFTER INSERT ON public.vault_audit_log FOR EACH ROW EXECUTE FUNCTION public.update_vault_quota_usage();


--
-- Name: endpoint_agent_events update_agent_keepalive_trigger; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_agent_keepalive_trigger AFTER INSERT ON public.endpoint_agent_events FOR EACH ROW EXECUTE FUNCTION public.update_agent_keepalive();


--
-- Name: TRIGGER update_agent_keepalive_trigger ON endpoint_agent_events; Type: COMMENT; Schema: public; Owner: sg
--

COMMENT ON TRIGGER update_agent_keepalive_trigger ON public.endpoint_agent_events IS 'Keeps agent status current based on event activity';


--
-- Name: agent_versions update_agent_versions_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_agent_versions_updated_at BEFORE UPDATE ON public.agent_versions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: customer_cloud_accounts update_customer_cloud_accounts_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_customer_cloud_accounts_updated_at BEFORE UPDATE ON public.customer_cloud_accounts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: customer_endpoint_agents update_customer_endpoint_agents_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_customer_endpoint_agents_updated_at BEFORE UPDATE ON public.customer_endpoint_agents FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: customer_git_providers update_customer_git_providers_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_customer_git_providers_updated_at BEFORE UPDATE ON public.customer_git_providers FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: customer_idp_config update_customer_idp_config_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_customer_idp_config_updated_at BEFORE UPDATE ON public.customer_idp_config FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: git_repositories update_git_repositories_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_git_repositories_updated_at BEFORE UPDATE ON public.git_repositories FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: git_security_findings update_git_security_findings_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_git_security_findings_updated_at BEFORE UPDATE ON public.git_security_findings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: git_security_scans update_git_security_scans_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_git_security_scans_updated_at BEFORE UPDATE ON public.git_security_scans FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: hardened_images update_hardened_images_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_hardened_images_updated_at BEFORE UPDATE ON public.hardened_images FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: onboarding_progress update_onboarding_progress_updated_at; Type: TRIGGER; Schema: public; Owner: sg
--

CREATE TRIGGER update_onboarding_progress_updated_at BEFORE UPDATE ON public.onboarding_progress FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: access_profile_entitlements access_profile_entitlements_access_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_profile_entitlements
    ADD CONSTRAINT access_profile_entitlements_access_profile_id_fkey FOREIGN KEY (access_profile_id) REFERENCES public.access_profiles(id) ON DELETE CASCADE;


--
-- Name: access_profile_entitlements access_profile_entitlements_entitlement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_profile_entitlements
    ADD CONSTRAINT access_profile_entitlements_entitlement_id_fkey FOREIGN KEY (entitlement_id) REFERENCES public.entitlements(id) ON DELETE CASCADE;


--
-- Name: access_requests access_requests_entitlement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_requests
    ADD CONSTRAINT access_requests_entitlement_id_fkey FOREIGN KEY (entitlement_id) REFERENCES public.entitlements(id) ON DELETE CASCADE;


--
-- Name: access_review_decisions access_review_decisions_review_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_decisions
    ADD CONSTRAINT access_review_decisions_review_item_id_fkey FOREIGN KEY (review_item_id) REFERENCES public.access_review_items(id) ON DELETE CASCADE;


--
-- Name: access_review_items access_review_items_app_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_items
    ADD CONSTRAINT access_review_items_app_id_fkey FOREIGN KEY (app_id) REFERENCES public.apps(id);


--
-- Name: access_review_items access_review_items_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_items
    ADD CONSTRAINT access_review_items_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.access_review_campaigns(id) ON DELETE CASCADE;


--
-- Name: access_review_items access_review_items_entitlement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_items
    ADD CONSTRAINT access_review_items_entitlement_id_fkey FOREIGN KEY (entitlement_id) REFERENCES public.entitlements(id);


--
-- Name: access_review_statistics access_review_statistics_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.access_review_statistics
    ADD CONSTRAINT access_review_statistics_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.access_review_campaigns(id) ON DELETE CASCADE;


--
-- Name: adapter_training_jobs adapter_training_jobs_data_snapshot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.adapter_training_jobs
    ADD CONSTRAINT adapter_training_jobs_data_snapshot_id_fkey FOREIGN KEY (data_snapshot_id) REFERENCES public.training_data_snapshots(id) ON DELETE SET NULL;


--
-- Name: ai_events ai_events_ai_app_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ai_events
    ADD CONSTRAINT ai_events_ai_app_id_fkey FOREIGN KEY (ai_app_id) REFERENCES public.ai_apps(id) ON DELETE SET NULL;


--
-- Name: ai_policies ai_policies_ai_app_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.ai_policies
    ADD CONSTRAINT ai_policies_ai_app_id_fkey FOREIGN KEY (ai_app_id) REFERENCES public.ai_apps(id) ON DELETE CASCADE;


--
-- Name: approvals approvals_access_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_access_request_id_fkey FOREIGN KEY (access_request_id) REFERENCES public.access_requests(id) ON DELETE CASCADE;


--
-- Name: certificate_requests certificate_requests_certificate_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.certificate_requests
    ADD CONSTRAINT certificate_requests_certificate_id_fkey FOREIGN KEY (certificate_id) REFERENCES public.certificates(id) ON DELETE SET NULL;


--
-- Name: certificates certificates_ca_authority_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.certificates
    ADD CONSTRAINT certificates_ca_authority_id_fkey FOREIGN KEY (ca_authority_id) REFERENCES public.ca_authorities(id);


--
-- Name: chat_messages chat_messages_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.chat_messages
    ADD CONSTRAINT chat_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.chat_sessions(id) ON DELETE CASCADE;


--
-- Name: compliance_controls compliance_controls_framework_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.compliance_controls
    ADD CONSTRAINT compliance_controls_framework_id_fkey FOREIGN KEY (framework_id) REFERENCES public.compliance_frameworks(id) ON DELETE CASCADE;


--
-- Name: compliance_controls compliance_controls_parent_control_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.compliance_controls
    ADD CONSTRAINT compliance_controls_parent_control_id_fkey FOREIGN KEY (parent_control_id) REFERENCES public.compliance_controls(id);


--
-- Name: connected_apps connected_apps_catalog_app_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.connected_apps
    ADD CONSTRAINT connected_apps_catalog_app_id_fkey FOREIGN KEY (catalog_app_id) REFERENCES public.app_catalog(id);


--
-- Name: control_mappings control_mappings_control_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.control_mappings
    ADD CONSTRAINT control_mappings_control_id_fkey FOREIGN KEY (control_id) REFERENCES public.compliance_controls(id) ON DELETE CASCADE;


--
-- Name: customers customers_realm_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_realm_name_fkey FOREIGN KEY (realm_name) REFERENCES public.realms(realm_name) ON DELETE SET NULL;


--
-- Name: endpoint_agent_events endpoint_agent_events_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.endpoint_agent_events
    ADD CONSTRAINT endpoint_agent_events_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.endpoint_agents(id) ON DELETE CASCADE;


--
-- Name: entitlement_mappings entitlement_mappings_entitlement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.entitlement_mappings
    ADD CONSTRAINT entitlement_mappings_entitlement_id_fkey FOREIGN KEY (entitlement_id) REFERENCES public.entitlements(id) ON DELETE CASCADE;


--
-- Name: entitlements entitlements_app_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.entitlements
    ADD CONSTRAINT entitlements_app_id_fkey FOREIGN KEY (app_id) REFERENCES public.apps(id) ON DELETE CASCADE;


--
-- Name: evidence_collection_tasks evidence_collection_tasks_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.evidence_collection_tasks
    ADD CONSTRAINT evidence_collection_tasks_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.evidence_packages(id) ON DELETE CASCADE;


--
-- Name: evidence_items evidence_items_control_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.evidence_items
    ADD CONSTRAINT evidence_items_control_id_fkey FOREIGN KEY (control_id) REFERENCES public.compliance_controls(id);


--
-- Name: evidence_items evidence_items_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.evidence_items
    ADD CONSTRAINT evidence_items_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.evidence_packages(id) ON DELETE CASCADE;


--
-- Name: evidence_packages evidence_packages_framework_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.evidence_packages
    ADD CONSTRAINT evidence_packages_framework_id_fkey FOREIGN KEY (framework_id) REFERENCES public.compliance_frameworks(id);


--
-- Name: findings findings_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.findings
    ADD CONSTRAINT findings_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE SET NULL;


--
-- Name: fix_group_assets fix_group_assets_fix_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.fix_group_assets
    ADD CONSTRAINT fix_group_assets_fix_group_id_fkey FOREIGN KEY (fix_group_id) REFERENCES public.fix_groups(id) ON DELETE CASCADE;


--
-- Name: fix_group_cves fix_group_cves_fix_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.fix_group_cves
    ADD CONSTRAINT fix_group_cves_fix_group_id_fkey FOREIGN KEY (fix_group_id) REFERENCES public.fix_groups(id) ON DELETE CASCADE;


--
-- Name: fix_groups fix_groups_scan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.fix_groups
    ADD CONSTRAINT fix_groups_scan_id_fkey FOREIGN KEY (scan_id) REFERENCES public.scans(id) ON DELETE CASCADE;


--
-- Name: git_repositories git_repositories_git_provider_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.git_repositories
    ADD CONSTRAINT git_repositories_git_provider_id_fkey FOREIGN KEY (git_provider_id) REFERENCES public.customer_git_providers(id) ON DELETE CASCADE;


--
-- Name: git_security_findings git_security_findings_repo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.git_security_findings
    ADD CONSTRAINT git_security_findings_repo_id_fkey FOREIGN KEY (repo_id) REFERENCES public.git_repositories(id) ON DELETE CASCADE;


--
-- Name: git_security_scans git_security_scans_repo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.git_security_scans
    ADD CONSTRAINT git_security_scans_repo_id_fkey FOREIGN KEY (repo_id) REFERENCES public.git_repositories(id) ON DELETE CASCADE;


--
-- Name: iam_audit_log iam_audit_log_target_access_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.iam_audit_log
    ADD CONSTRAINT iam_audit_log_target_access_request_id_fkey FOREIGN KEY (target_access_request_id) REFERENCES public.access_requests(id) ON DELETE SET NULL;


--
-- Name: iam_audit_log iam_audit_log_target_entitlement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.iam_audit_log
    ADD CONSTRAINT iam_audit_log_target_entitlement_id_fkey FOREIGN KEY (target_entitlement_id) REFERENCES public.entitlements(id) ON DELETE SET NULL;


--
-- Name: image_customer_sharing image_customer_sharing_customer_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.image_customer_sharing
    ADD CONSTRAINT image_customer_sharing_customer_account_id_fkey FOREIGN KEY (customer_account_id) REFERENCES public.customer_cloud_accounts(id) ON DELETE CASCADE;


--
-- Name: image_customer_sharing image_customer_sharing_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.image_customer_sharing
    ADD CONSTRAINT image_customer_sharing_image_id_fkey FOREIGN KEY (image_id) REFERENCES public.hardened_images(id) ON DELETE CASCADE;


--
-- Name: image_version_history image_version_history_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.image_version_history
    ADD CONSTRAINT image_version_history_image_id_fkey FOREIGN KEY (image_id) REFERENCES public.hardened_images(id) ON DELETE CASCADE;


--
-- Name: image_version_history image_version_history_parent_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.image_version_history
    ADD CONSTRAINT image_version_history_parent_image_id_fkey FOREIGN KEY (parent_image_id) REFERENCES public.hardened_images(id) ON DELETE SET NULL;


--
-- Name: jml_workflow_steps jml_workflow_steps_workflow_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.jml_workflow_steps
    ADD CONSTRAINT jml_workflow_steps_workflow_id_fkey FOREIGN KEY (workflow_id) REFERENCES public.jml_workflows(id) ON DELETE CASCADE;


--
-- Name: jml_workflows jml_workflows_target_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.jml_workflows
    ADD CONSTRAINT jml_workflows_target_profile_id_fkey FOREIGN KEY (target_profile_id) REFERENCES public.access_profiles(id);


--
-- Name: mfa_compliance_violations mfa_compliance_violations_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.mfa_compliance_violations
    ADD CONSTRAINT mfa_compliance_violations_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.mfa_enforcement_policies(id);


--
-- Name: organizations organizations_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: organizations organizations_parent_org_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_parent_org_id_fkey FOREIGN KEY (parent_org_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: organizations organizations_realm_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_realm_name_fkey FOREIGN KEY (realm_name) REFERENCES public.realms(realm_name) ON DELETE RESTRICT;


--
-- Name: phishing_observables phishing_observables_phishing_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.phishing_observables
    ADD CONSTRAINT phishing_observables_phishing_report_id_fkey FOREIGN KEY (phishing_report_id) REFERENCES public.phishing_reports(id) ON DELETE CASCADE;


--
-- Name: playbook_analyzers playbook_analyzers_playbook_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_analyzers
    ADD CONSTRAINT playbook_analyzers_playbook_id_fkey FOREIGN KEY (playbook_id) REFERENCES public.playbooks(id) ON DELETE CASCADE;


--
-- Name: playbook_execution_audit playbook_execution_audit_execution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_execution_audit
    ADD CONSTRAINT playbook_execution_audit_execution_id_fkey FOREIGN KEY (execution_id) REFERENCES public.playbook_executions(id) ON DELETE CASCADE;


--
-- Name: playbook_execution_audit playbook_execution_audit_playbook_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_execution_audit
    ADD CONSTRAINT playbook_execution_audit_playbook_id_fkey FOREIGN KEY (playbook_id) REFERENCES public.playbooks(id);


--
-- Name: playbook_executions playbook_executions_playbook_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_executions
    ADD CONSTRAINT playbook_executions_playbook_id_fkey FOREIGN KEY (playbook_id) REFERENCES public.playbooks(id) ON DELETE CASCADE;


--
-- Name: playbook_executions playbook_executions_trigger_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_executions
    ADD CONSTRAINT playbook_executions_trigger_rule_id_fkey FOREIGN KEY (trigger_rule_id) REFERENCES public.playbooks(id);


--
-- Name: playbook_observables playbook_observables_playbook_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.playbook_observables
    ADD CONSTRAINT playbook_observables_playbook_id_fkey FOREIGN KEY (playbook_id) REFERENCES public.playbooks(id) ON DELETE CASCADE;


--
-- Name: policy_conflicts policy_conflicts_policy_id_1_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_conflicts
    ADD CONSTRAINT policy_conflicts_policy_id_1_fkey FOREIGN KEY (policy_id_1) REFERENCES public.policies(id) ON DELETE CASCADE;


--
-- Name: policy_conflicts policy_conflicts_policy_id_2_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_conflicts
    ADD CONSTRAINT policy_conflicts_policy_id_2_fkey FOREIGN KEY (policy_id_2) REFERENCES public.policies(id) ON DELETE CASCADE;


--
-- Name: policy_evaluations policy_evaluations_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_evaluations
    ADD CONSTRAINT policy_evaluations_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policies(id) ON DELETE CASCADE;


--
-- Name: policy_rules policy_rules_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_rules
    ADD CONSTRAINT policy_rules_policy_id_fkey FOREIGN KEY (policy_id) REFERENCES public.policies(id) ON DELETE CASCADE;


--
-- Name: policy_templates policy_templates_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.policy_templates
    ADD CONSTRAINT policy_templates_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: privileged_access_approvals privileged_access_approvals_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.privileged_access_approvals
    ADD CONSTRAINT privileged_access_approvals_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.privileged_access_requests(id) ON DELETE CASCADE;


--
-- Name: realm_capacity_history realm_capacity_history_realm_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.realm_capacity_history
    ADD CONSTRAINT realm_capacity_history_realm_name_fkey FOREIGN KEY (realm_name) REFERENCES public.realms(realm_name) ON DELETE CASCADE;


--
-- Name: remediation_metadata remediation_metadata_playbook_execution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.remediation_metadata
    ADD CONSTRAINT remediation_metadata_playbook_execution_id_fkey FOREIGN KEY (playbook_execution_id) REFERENCES public.playbook_executions(id);


--
-- Name: tenant_control_status tenant_control_status_control_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_control_status
    ADD CONSTRAINT tenant_control_status_control_id_fkey FOREIGN KEY (control_id) REFERENCES public.compliance_controls(id) ON DELETE CASCADE;


--
-- Name: tenant_provisioning_log tenant_provisioning_log_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_provisioning_log
    ADD CONSTRAINT tenant_provisioning_log_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: tenant_provisioning_log tenant_provisioning_log_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenant_provisioning_log
    ADD CONSTRAINT tenant_provisioning_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: tenants tenants_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: tenants tenants_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: tenants tenants_realm_name_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_realm_name_fkey FOREIGN KEY (realm_name) REFERENCES public.realms(realm_name) ON DELETE SET NULL;


--
-- Name: user_entitlements user_entitlements_entitlement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.user_entitlements
    ADD CONSTRAINT user_entitlements_entitlement_id_fkey FOREIGN KEY (entitlement_id) REFERENCES public.entitlements(id) ON DELETE CASCADE;


--
-- Name: user_mfa_status user_mfa_status_applicable_policy_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.user_mfa_status
    ADD CONSTRAINT user_mfa_status_applicable_policy_id_fkey FOREIGN KEY (applicable_policy_id) REFERENCES public.mfa_enforcement_policies(id);


--
-- Name: vault_access_grants vault_access_grants_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_access_grants
    ADD CONSTRAINT vault_access_grants_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: vault_audit_log vault_audit_log_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_audit_log
    ADD CONSTRAINT vault_audit_log_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: vault_audit_log vault_audit_log_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_audit_log
    ADD CONSTRAINT vault_audit_log_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: vault_audit_log vault_audit_log_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_audit_log
    ADD CONSTRAINT vault_audit_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: vault_customers vault_customers_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_customers
    ADD CONSTRAINT vault_customers_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: vault_organizations vault_organizations_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_organizations
    ADD CONSTRAINT vault_organizations_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: vault_organizations vault_organizations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_organizations
    ADD CONSTRAINT vault_organizations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: vault_tenants vault_tenants_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_tenants
    ADD CONSTRAINT vault_tenants_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: vault_tenants vault_tenants_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_tenants
    ADD CONSTRAINT vault_tenants_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: vault_tenants vault_tenants_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_tenants
    ADD CONSTRAINT vault_tenants_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: vault_usage_history vault_usage_history_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_usage_history
    ADD CONSTRAINT vault_usage_history_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: vault_usage_history vault_usage_history_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_usage_history
    ADD CONSTRAINT vault_usage_history_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: vault_usage_history vault_usage_history_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: sg
--

ALTER TABLE ONLY public.vault_usage_history
    ADD CONSTRAINT vault_usage_history_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;


--
-- Name: report_access_log report_access_log_report_id_fkey; Type: FK CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_access_log
    ADD CONSTRAINT report_access_log_report_id_fkey FOREIGN KEY (report_id) REFERENCES reporting.generated_reports(id) ON DELETE CASCADE;


--
-- Name: report_llm_documents report_llm_documents_report_id_fkey; Type: FK CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_llm_documents
    ADD CONSTRAINT report_llm_documents_report_id_fkey FOREIGN KEY (report_id) REFERENCES reporting.generated_reports(id) ON DELETE CASCADE;


--
-- Name: report_schedules report_schedules_last_report_id_fkey; Type: FK CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_schedules
    ADD CONSTRAINT report_schedules_last_report_id_fkey FOREIGN KEY (last_report_id) REFERENCES reporting.generated_reports(id);


--
-- Name: report_shares report_shares_report_id_fkey; Type: FK CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.report_shares
    ADD CONSTRAINT report_shares_report_id_fkey FOREIGN KEY (report_id) REFERENCES reporting.reports(id) ON DELETE CASCADE;


--
-- Name: reports reports_template_id_fkey; Type: FK CONSTRAINT; Schema: reporting; Owner: sg
--

ALTER TABLE ONLY reporting.reports
    ADD CONSTRAINT reports_template_id_fkey FOREIGN KEY (template_id) REFERENCES reporting.report_templates(id);


--
-- Name: alert_ai_analysis alert_ai_analysis_alert_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.alert_ai_analysis
    ADD CONSTRAINT alert_ai_analysis_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES security_ops.alerts(id) ON DELETE CASCADE;


--
-- Name: alert_playbook_triggers alert_playbook_triggers_alert_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.alert_playbook_triggers
    ADD CONSTRAINT alert_playbook_triggers_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES security_ops.alerts(id) ON DELETE CASCADE;


--
-- Name: alert_triage_feedback alert_triage_feedback_ai_analysis_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.alert_triage_feedback
    ADD CONSTRAINT alert_triage_feedback_ai_analysis_id_fkey FOREIGN KEY (ai_analysis_id) REFERENCES security_ops.alert_ai_analysis(id) ON DELETE CASCADE;


--
-- Name: alert_triage_feedback alert_triage_feedback_alert_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.alert_triage_feedback
    ADD CONSTRAINT alert_triage_feedback_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES security_ops.alerts(id) ON DELETE CASCADE;


--
-- Name: detection_bindings detection_bindings_detection_rule_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_bindings
    ADD CONSTRAINT detection_bindings_detection_rule_id_fkey FOREIGN KEY (detection_rule_id) REFERENCES security_ops.detection_rules(id) ON DELETE CASCADE;


--
-- Name: detection_bindings detection_bindings_detection_rule_version_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_bindings
    ADD CONSTRAINT detection_bindings_detection_rule_version_id_fkey FOREIGN KEY (detection_rule_version_id) REFERENCES security_ops.detection_rule_versions(id) ON DELETE SET NULL;


--
-- Name: detection_deduplication detection_deduplication_incident_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_deduplication
    ADD CONSTRAINT detection_deduplication_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES security_ops.incidents(id);


--
-- Name: detection_deduplication detection_deduplication_rule_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_deduplication
    ADD CONSTRAINT detection_deduplication_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES security_ops.detection_rules(id);


--
-- Name: detection_playbook_mappings detection_playbook_mappings_rule_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_playbook_mappings
    ADD CONSTRAINT detection_playbook_mappings_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES security_ops.detection_rules(id) ON DELETE CASCADE;


--
-- Name: detection_rule_executions detection_rule_executions_rule_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_rule_executions
    ADD CONSTRAINT detection_rule_executions_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES security_ops.detection_rules(id);


--
-- Name: detection_rule_versions detection_rule_versions_rule_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_rule_versions
    ADD CONSTRAINT detection_rule_versions_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES security_ops.detection_rules(id) ON DELETE CASCADE;


--
-- Name: detection_suppression_events detection_suppression_events_dedup_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_suppression_events
    ADD CONSTRAINT detection_suppression_events_dedup_id_fkey FOREIGN KEY (dedup_id) REFERENCES security_ops.detection_deduplication(id);


--
-- Name: detection_suppression_events detection_suppression_events_suppression_rule_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_suppression_events
    ADD CONSTRAINT detection_suppression_events_suppression_rule_id_fkey FOREIGN KEY (suppression_rule_id) REFERENCES security_ops.detection_suppression_rules(id);


--
-- Name: detection_suppression_rules detection_suppression_rules_rule_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.detection_suppression_rules
    ADD CONSTRAINT detection_suppression_rules_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES security_ops.detection_rules(id);


--
-- Name: incident_actions incident_actions_incident_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_actions
    ADD CONSTRAINT incident_actions_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES security_ops.incidents(id) ON DELETE CASCADE;


--
-- Name: incident_ai_summaries incident_ai_summaries_incident_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_ai_summaries
    ADD CONSTRAINT incident_ai_summaries_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES security_ops.incidents(id) ON DELETE CASCADE;


--
-- Name: incident_alerts incident_alerts_alert_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_alerts
    ADD CONSTRAINT incident_alerts_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES security_ops.alerts(id) ON DELETE CASCADE;


--
-- Name: incident_alerts incident_alerts_incident_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_alerts
    ADD CONSTRAINT incident_alerts_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES security_ops.incidents(id) ON DELETE CASCADE;


--
-- Name: incident_evidence incident_evidence_incident_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_evidence
    ADD CONSTRAINT incident_evidence_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES security_ops.incidents(id) ON DELETE CASCADE;


--
-- Name: incident_lifecycle incident_lifecycle_incident_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_lifecycle
    ADD CONSTRAINT incident_lifecycle_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES security_ops.incidents(id) ON DELETE CASCADE;


--
-- Name: incident_lifecycle incident_lifecycle_rule_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_lifecycle
    ADD CONSTRAINT incident_lifecycle_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES security_ops.detection_rules(id);


--
-- Name: incident_observables incident_observables_incident_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_observables
    ADD CONSTRAINT incident_observables_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES security_ops.incidents(id) ON DELETE CASCADE;


--
-- Name: incident_timeline incident_timeline_incident_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incident_timeline
    ADD CONSTRAINT incident_timeline_incident_id_fkey FOREIGN KEY (incident_id) REFERENCES security_ops.incidents(id) ON DELETE CASCADE;


--
-- Name: incidents incidents_ticket_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.incidents
    ADD CONSTRAINT incidents_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES security_ops.tickets(id) ON DELETE SET NULL;


--
-- Name: ticket_ai_enrichments ticket_ai_enrichments_ticket_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.ticket_ai_enrichments
    ADD CONSTRAINT ticket_ai_enrichments_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES security_ops.tickets(id) ON DELETE CASCADE;


--
-- Name: ticket_alerts ticket_alerts_alert_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.ticket_alerts
    ADD CONSTRAINT ticket_alerts_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES security_ops.alerts(id) ON DELETE CASCADE;


--
-- Name: ticket_alerts ticket_alerts_ticket_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.ticket_alerts
    ADD CONSTRAINT ticket_alerts_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES security_ops.tickets(id) ON DELETE CASCADE;


--
-- Name: ticket_vulnerabilities ticket_vulnerabilities_ticket_id_fkey; Type: FK CONSTRAINT; Schema: security_ops; Owner: sg
--

ALTER TABLE ONLY security_ops.ticket_vulnerabilities
    ADD CONSTRAINT ticket_vulnerabilities_ticket_id_fkey FOREIGN KEY (ticket_id) REFERENCES security_ops.tickets(id) ON DELETE CASCADE;


--
-- Name: adapter_training_jobs; Type: ROW SECURITY; Schema: public; Owner: sg
--

ALTER TABLE public.adapter_training_jobs ENABLE ROW LEVEL SECURITY;

--
-- Name: adapter_version_history; Type: ROW SECURITY; Schema: public; Owner: sg
--

ALTER TABLE public.adapter_version_history ENABLE ROW LEVEL SECURITY;

--
-- Name: cybersecurity_knowledge_base; Type: ROW SECURITY; Schema: public; Owner: sg
--

ALTER TABLE public.cybersecurity_knowledge_base ENABLE ROW LEVEL SECURITY;

--
-- Name: cybersecurity_knowledge_base knowledge_base_isolation; Type: POLICY; Schema: public; Owner: sg
--

CREATE POLICY knowledge_base_isolation ON public.cybersecurity_knowledge_base USING (((tenant_id IS NULL) OR (tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid)));


--
-- Name: training_data_snapshots snapshots_isolation; Type: POLICY; Schema: public; Owner: sg
--

CREATE POLICY snapshots_isolation ON public.training_data_snapshots USING ((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid));


--
-- Name: tenant_model_adapters tenant_adapters_isolation; Type: POLICY; Schema: public; Owner: sg
--

CREATE POLICY tenant_adapters_isolation ON public.tenant_model_adapters USING ((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid));


--
-- Name: tenant_model_adapters; Type: ROW SECURITY; Schema: public; Owner: sg
--

ALTER TABLE public.tenant_model_adapters ENABLE ROW LEVEL SECURITY;

--
-- Name: tenant_training_data; Type: ROW SECURITY; Schema: public; Owner: sg
--

ALTER TABLE public.tenant_training_data ENABLE ROW LEVEL SECURITY;

--
-- Name: tenant_training_data tenant_training_data_isolation; Type: POLICY; Schema: public; Owner: sg
--

CREATE POLICY tenant_training_data_isolation ON public.tenant_training_data USING ((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid));


--
-- Name: training_data_snapshots; Type: ROW SECURITY; Schema: public; Owner: sg
--

ALTER TABLE public.training_data_snapshots ENABLE ROW LEVEL SECURITY;

--
-- Name: adapter_training_jobs training_jobs_isolation; Type: POLICY; Schema: public; Owner: sg
--

CREATE POLICY training_jobs_isolation ON public.adapter_training_jobs USING ((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid));


--
-- Name: adapter_version_history version_history_isolation; Type: POLICY; Schema: public; Owner: sg
--

CREATE POLICY version_history_isolation ON public.adapter_version_history USING ((tenant_id = (current_setting('app.current_tenant_id'::text, true))::uuid));


--
-- PostgreSQL database dump complete
--

-- stripped \unrestrict marker (psql meta command not needed for Flyway)
