-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- AlloyDB for PostgreSQL Fail-Closed Row-Level Security & RBAC Schema (Blog Section 4)
-- Non-superuser, non-bypass-RLS application role (`cymbal_mcp_app`) enforces
-- transaction-scoped `app.current_tenant_id`, `app.current_user_role`, and
-- `app.current_agent_id` claims, returning 0 rows whenever any claim is missing.

CREATE TABLE IF NOT EXISTS tenant_incidents (
    incident_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    service_name TEXT NOT NULL,
    severity TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cymbal_mcp_app') THEN
        CREATE ROLE cymbal_mcp_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION;
    END IF;
END
$$;

REVOKE ALL ON TABLE tenant_incidents FROM PUBLIC;
GRANT SELECT (incident_id, tenant_id, service_name, severity, summary, created_at)
    ON TABLE tenant_incidents TO cymbal_mcp_app;
GRANT UPDATE (severity, summary)
    ON TABLE tenant_incidents TO cymbal_mcp_app;

ALTER TABLE tenant_incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_incidents FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_incidents_rls_policy ON tenant_incidents;
CREATE POLICY tenant_incidents_rls_policy ON tenant_incidents
    USING (
        NULLIF(current_setting('app.current_tenant_id', true), '') IS NOT NULL
        AND tenant_id = current_setting('app.current_tenant_id', true)
        AND NULLIF(current_setting('app.current_user_role', true), '') IS NOT NULL
        AND current_setting('app.current_user_role', true) IN (
            'sre_admin',
            'compliance_officer',
            'read_only_analyst'
        )
        AND NULLIF(current_setting('app.current_agent_id', true), '') IS NOT NULL
        AND current_setting('app.current_agent_id', true) IN (
            'cymbal_shared_diagnostic_agent',
            'finvault_regulatory_escalation_agent'
        )
    );

DROP POLICY IF EXISTS tenant_incidents_write_rbac_policy ON tenant_incidents;
CREATE POLICY tenant_incidents_write_rbac_policy ON tenant_incidents
    AS RESTRICTIVE
    FOR UPDATE
    USING (
        NULLIF(current_setting('app.current_tenant_id', true), '') IS NOT NULL
        AND tenant_id = current_setting('app.current_tenant_id', true)
        AND current_setting('app.current_user_role', true) = 'sre_admin'
        AND current_setting('app.current_agent_id', true) = 'cymbal_shared_diagnostic_agent'
    )
    WITH CHECK (
        NULLIF(current_setting('app.current_tenant_id', true), '') IS NOT NULL
        AND tenant_id = current_setting('app.current_tenant_id', true)
        AND current_setting('app.current_user_role', true) = 'sre_admin'
        AND current_setting('app.current_agent_id', true) = 'cymbal_shared_diagnostic_agent'
    );
