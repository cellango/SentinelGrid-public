-- Make legacy asset_id optional and defaulted so inserts without it succeed.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'asset_id'
    ) THEN
        BEGIN
            EXECUTE 'ALTER TABLE assets ALTER COLUMN asset_id DROP NOT NULL';
        EXCEPTION WHEN others THEN
            NULL;
        END;
        BEGIN
            EXECUTE 'ALTER TABLE assets ALTER COLUMN asset_id SET DEFAULT uuid_generate_v4()';
        EXCEPTION WHEN others THEN
            NULL;
        END;
    END IF;
END $$;

-- Ensure findings.asset_id is nullable (some findings may hang off tenant only)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'findings' AND column_name = 'asset_id'
    ) THEN
        BEGIN
            EXECUTE 'ALTER TABLE findings ALTER COLUMN asset_id DROP NOT NULL';
        EXCEPTION WHEN others THEN
            NULL;
        END;
    END IF;
END $$;
