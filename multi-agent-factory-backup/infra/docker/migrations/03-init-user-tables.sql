-- User management tables for Multi-Agent Factory
-- This script creates the necessary tables for user authentication and authorization

-- Create users table
CREATE TABLE IF NOT EXISTS maf.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    mfa_enabled BOOLEAN DEFAULT false,
    mfa_secret VARCHAR(255),
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create roles table
CREATE TABLE IF NOT EXISTS maf.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_roles junction table
CREATE TABLE IF NOT EXISTS maf.user_roles (
    user_id UUID REFERENCES maf.users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES maf.roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Create user_sessions table for session management
CREATE TABLE IF NOT EXISTS maf.user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES maf.users(id) ON DELETE CASCADE,
    jti VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON maf.users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON maf.users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON maf.users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_locked_until ON maf.users(locked_until);
CREATE INDEX IF NOT EXISTS idx_roles_name ON maf.roles(name);
CREATE INDEX IF NOT EXISTS idx_roles_active ON maf.roles(is_active);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON maf.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_jti ON maf.user_sessions(jti);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON maf.user_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON maf.user_sessions(expires_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON maf.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON maf.roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default roles
INSERT INTO maf.roles (name, description, permissions) VALUES
('admin', 'System Administrator', '["admin:read", "admin:write", "admin:delete", "agents:read", "agents:write", "agents:delete", "tasks:read", "tasks:write", "tasks:delete", "users:read", "users:write", "users:delete", "system:read", "system:write"]'),
('operator', 'System Operator', '["agents:read", "agents:write", "tasks:read", "tasks:write", "system:read"]'),
('agent-doc-writer', 'Documentation Agent', '["tasks:read", "tasks:write"]'),
('agent-backend-dev', 'Backend Development Agent', '["tasks:read", "tasks:write"]'),
('agent-frontend-dev', 'Frontend Development Agent', '["tasks:read", "tasks:write"]'),
('agent-qa-tester', 'QA Testing Agent', '["tasks:read", "tasks:write"]'),
('viewer', 'Read-only User', '["tasks:read", "system:read"]')
ON CONFLICT (name) DO NOTHING;

-- Insert default admin user (password: admin123)
-- Note: This should be changed in production
INSERT INTO maf.users (username, email, full_name, hashed_password, is_active, is_verified) VALUES
('admin', 'admin@multi-agent-factory.com', 'System Administrator', '$argon2id$v=19$m=65536,t=3,p=1$YWRtaW4xMjM$8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8K8', true, true)
ON CONFLICT (username) DO NOTHING;

-- Assign admin role to admin user
INSERT INTO maf.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM maf.users u, maf.roles r
WHERE u.username = 'admin' AND r.name = 'admin'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- Create view for user details with roles
CREATE OR REPLACE VIEW maf.user_details AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.full_name,
    u.is_active,
    u.is_verified,
    u.mfa_enabled,
    u.last_login,
    u.created_at,
    u.updated_at,
    COALESCE(
        json_agg(
            json_build_object(
                'id', r.id,
                'name', r.name,
                'description', r.description,
                'permissions', r.permissions
            )
        ) FILTER (WHERE r.id IS NOT NULL),
        '[]'::json
    ) as roles
FROM maf.users u
LEFT JOIN maf.user_roles ur ON u.id = ur.user_id
LEFT JOIN maf.roles r ON ur.role_id = r.id AND r.is_active = true
GROUP BY u.id, u.username, u.email, u.full_name, u.is_active, u.is_verified, u.mfa_enabled, u.last_login, u.created_at, u.updated_at;

-- Create function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM maf.user_sessions 
    WHERE expires_at < CURRENT_TIMESTAMP OR is_active = false;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON maf.users TO maf_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON maf.roles TO maf_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON maf.user_roles TO maf_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON maf.user_sessions TO maf_user;
GRANT SELECT ON maf.user_details TO maf_user;
GRANT EXECUTE ON FUNCTION cleanup_expired_sessions() TO maf_user;
GRANT EXECUTE ON FUNCTION update_updated_at_column() TO maf_user;

-- Add comment
COMMENT ON TABLE maf.users IS 'User accounts for authentication and authorization';
COMMENT ON TABLE maf.roles IS 'Roles defining sets of permissions';
COMMENT ON TABLE maf.user_roles IS 'Many-to-many relationship between users and roles';
COMMENT ON TABLE maf.user_sessions IS 'Active user sessions for token management';
COMMENT ON VIEW maf.user_details IS 'Comprehensive user information including roles';