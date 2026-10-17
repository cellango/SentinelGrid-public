SET search_path = public, pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $registry$
BEGIN
    -- The shared app-catalog lineage has no IAM role/grant domain.
    IF to_regclass('public.role_entitlement_patterns') IS NULL THEN RETURN; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='public.entitlements'::regclass
                   AND attname='granted_to_id' AND atttypid='uuid'::regtype AND NOT attisdropped) THEN
        RAISE EXCEPTION 'Unreviewed grant store; reconcile history before migration';
    END IF;
    -- A new name deliberately avoids adopting the private runtime-created table.
    -- Existing nhi_service_accounts and shared api_keys are never read or changed.
    CREATE TABLE public.iam_service_accounts (
        id uuid PRIMARY KEY,
        tenant_id uuid NOT NULL,
        name varchar(255) NOT NULL,
        description text,
        client_id varchar(40) NOT NULL,
        owner_user_id uuid NOT NULL,
        created_by uuid NOT NULL,
        status varchar(20) NOT NULL DEFAULT 'active',
        rotation_days integer NOT NULL DEFAULT 90,
        credential_version integer NOT NULL DEFAULT 1,
        secret_hash varchar(64),
        credential_expires_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT iam_service_account_name UNIQUE (tenant_id,name),
        CONSTRAINT iam_service_account_client UNIQUE (client_id),
        CONSTRAINT iam_service_account_status CHECK (status IN ('active','inactive','deleted')),
        CONSTRAINT iam_service_account_rotation CHECK (rotation_days BETWEEN 1 AND 365),
        CONSTRAINT iam_service_account_version CHECK (credential_version >= 1),
        CONSTRAINT iam_service_account_credential CHECK (
            (status='active' AND secret_hash IS NOT NULL AND secret_hash ~ '^[0-9a-f]{64}$' AND credential_expires_at IS NOT NULL)
            OR (status IN ('inactive','deleted') AND secret_hash IS NULL AND credential_expires_at IS NULL))
    );
    CREATE INDEX ix_iam_service_account_expiry ON public.iam_service_accounts(tenant_id,status,credential_expires_at);
    CREATE TRIGGER update_iam_service_accounts_updated_at BEFORE UPDATE ON public.iam_service_accounts
        FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
    ALTER TABLE public.iam_service_accounts ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.iam_service_accounts FORCE ROW LEVEL SECURITY;
    CREATE POLICY iam_service_account_access ON public.iam_service_accounts
        USING (tenant_id=public.iam_current_tenant_id()) WITH CHECK (tenant_id=public.iam_current_tenant_id());
    CREATE POLICY iam_service_account_guard ON public.iam_service_accounts AS RESTRICTIVE
        USING (tenant_id=public.iam_current_tenant_id()) WITH CHECK (tenant_id=public.iam_current_tenant_id());
    CREATE POLICY iam_service_account_no_delete ON public.iam_service_accounts AS RESTRICTIVE FOR DELETE USING (false);
    REVOKE ALL ON public.iam_service_accounts FROM PUBLIC;

    CREATE FUNCTION public.iam_guard_service_account_lifecycle() RETURNS trigger
    LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $lifecycle$
    BEGIN
        IF ROW(OLD.id,OLD.tenant_id,OLD.name,OLD.description,OLD.client_id,OLD.owner_user_id,OLD.created_by,OLD.rotation_days,OLD.created_at)
           IS DISTINCT FROM ROW(NEW.id,NEW.tenant_id,NEW.name,NEW.description,NEW.client_id,NEW.owner_user_id,NEW.created_by,NEW.rotation_days,NEW.created_at) THEN
            RAISE EXCEPTION 'Service account ownership and definition are immutable' USING ERRCODE='23514';
        END IF;
        IF OLD.status='deleted' THEN
            RAISE EXCEPTION 'Deleted service accounts are terminal' USING ERRCODE='23514';
        END IF;
        IF ROW(OLD.status,OLD.secret_hash,OLD.credential_expires_at) IS DISTINCT FROM ROW(NEW.status,NEW.secret_hash,NEW.credential_expires_at) THEN
            IF NEW.credential_version <> OLD.credential_version+1 THEN
                RAISE EXCEPTION 'Credential transitions require the next version' USING ERRCODE='23514';
            END IF;
            IF NEW.status='active' AND NEW.secret_hash IS NOT DISTINCT FROM OLD.secret_hash THEN
                RAISE EXCEPTION 'Activation and rotation require a fresh credential' USING ERRCODE='23514';
            END IF;
        ELSIF NEW.credential_version <> OLD.credential_version THEN
            RAISE EXCEPTION 'Version change requires a lifecycle transition' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END
    $lifecycle$;
    CREATE TRIGGER guard_iam_service_account_lifecycle BEFORE UPDATE ON public.iam_service_accounts
        FOR EACH ROW EXECUTE FUNCTION public.iam_guard_service_account_lifecycle();
END
$registry$;
