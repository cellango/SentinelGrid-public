-- Drop legacy playbooks with empty playbook_key
DELETE FROM playbooks WHERE COALESCE(playbook_key, '') = '';
