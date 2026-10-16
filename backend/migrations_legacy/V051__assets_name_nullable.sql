-- Make assets.name nullable (legacy constraint), so inserts can succeed when name is not provided.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'name'
    ) THEN
        BEGIN
            EXECUTE 'ALTER TABLE assets ALTER COLUMN name DROP NOT NULL';
        EXCEPTION WHEN others THEN
            NULL;
        END;
    END IF;
END $$;
