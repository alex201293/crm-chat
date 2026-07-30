-- =============================================================================
-- Database Initialization Script
-- Runs on first container startup only
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";        -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- Trigram for fuzzy search

-- Create test database for integration tests
CREATE DATABASE crm_chat_test;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE crm_chat TO postgres;
GRANT ALL PRIVILEGES ON DATABASE crm_chat_test TO postgres;
