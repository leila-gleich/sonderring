-- ====================================================================
-- SONDERRING MASTER RELATIONAL SCHEMA (PostgreSQL)
-- Includes Hybrid Time Model, AES-256-GCM Field-Level Encryption,
-- Strict Integrity Constraints, and Performance Indexes
-- ====================================================================

-- 1. USERS & AUTHENTICATION
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    handle VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    password VARCHAR(128) DEFAULT '', -- Hashed password (standard Django PBKDF2/Argon2)
    phone_number VARCHAR(30),
    profile_image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1b. DECOUPLED OAUTH / SOCIAL IDENTITIES
-- Maps external providers (Google, Apple, etc.) to internal user accounts.
-- If OAuth is disabled or uninstalled, user accounts and trip data remain 100% intact.
CREATE TABLE oauth_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(30) NOT NULL DEFAULT 'google',
    uid VARCHAR(255) NOT NULL,     -- Provider user ID (e.g. Google sub)
    email VARCHAR(255),            -- Verified email from provider
    extra_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_oauth_provider_uid UNIQUE (provider, uid),
    CONSTRAINT uq_oauth_user_provider UNIQUE (user_id, provider)
);

CREATE INDEX idx_oauth_provider_uid ON oauth_identities(provider, uid);
CREATE INDEX idx_oauth_user_provider ON oauth_identities(user_id, provider);

-- 2. TRIPS (With Hybrid Time Model & Conditional Integrity Constraints)
CREATE TABLE trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(150) NOT NULL,
    description TEXT,
    location VARCHAR(255) NOT NULL,
    time_granularity VARCHAR(20) NOT NULL CHECK (time_granularity IN ('SEASON_YEAR', 'EXACT_RANGE', 'MONTH', 'YEAR')),
    season VARCHAR(10) CHECK (season IN ('SPRING', 'SUMMER', 'FALL', 'WINTER')),
    year INT NOT NULL,
    start_date DATE,
    end_date DATE,
    start_month INT CHECK (start_month BETWEEN 1 AND 12),
    end_month INT CHECK (end_month BETWEEN 1 AND 12),
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- High-Priority Constraint: Enforce structured time rules per granularity
    CONSTRAINT chk_trip_time_granularity CHECK (
        (time_granularity = 'SEASON_YEAR' AND season IS NOT NULL) OR
        (time_granularity = 'EXACT_RANGE' AND start_date IS NOT NULL AND end_date IS NOT NULL AND start_date <= end_date) OR
        (time_granularity = 'MONTH' AND start_month IS NOT NULL AND (end_month IS NULL OR start_month <= end_month)) OR
        (time_granularity = 'YEAR')
    )
);

-- 3. TRIP MEMBERS (ACCESS CONTROL)
CREATE TABLE trip_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'EDITOR' CHECK (role IN ('OWNER', 'EDITOR', 'VIEWER')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trip_id, user_id)
);

-- 4. STAYS (ACCOMMODATIONS)
CREATE TABLE stays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'IDEA' CHECK (status IN ('IDEA', 'CONFIRMED')),
    description TEXT,
    address TEXT,
    check_in TIMESTAMP WITH TIME ZONE,
    check_out TIMESTAMP WITH TIME ZONE,
    total_price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    booking_link TEXT,
    encrypted_confirmation_code TEXT, -- Encrypted via AES-256-GCM
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- High-Priority Constraint: Chronological date boundary check
    CONSTRAINT chk_stay_dates CHECK (
        check_out IS NULL OR check_in IS NULL OR check_out >= check_in
    )
);

-- 5. NAVS (TRANSPORTATION)
CREATE TABLE navs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    mode VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'IDEA' CHECK (status IN ('IDEA', 'CONFIRMED')),
    description TEXT,
    origin_address TEXT,
    destination_address TEXT,
    departure_time TIMESTAMP WITH TIME ZONE,
    arrival_time TIMESTAMP WITH TIME ZONE,
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    booking_link TEXT,
    encrypted_confirmation_code TEXT, -- Encrypted via AES-256-GCM
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- High-Priority Constraint: Chronological timestamp boundary check
    CONSTRAINT chk_nav_times CHECK (
        arrival_time IS NULL OR departure_time IS NULL OR arrival_time >= departure_time
    )
);

-- 6. DOS (ACTIVITIES)
CREATE TABLE dos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    activity_type VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'IDEA' CHECK (status IN ('IDEA', 'CONFIRMED')),
    description TEXT,
    address TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    link TEXT,
    encrypted_confirmation_code TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- High-Priority Constraint: Chronological timestamp boundary check
    CONSTRAINT chk_do_times CHECK (
        end_time IS NULL OR start_time IS NULL OR end_time >= start_time
    )
);

-- 7. ATTACHMENTS (SECURE VAULT)
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    stay_id UUID REFERENCES stays(id) ON DELETE CASCADE,
    nav_id UUID REFERENCES navs(id) ON DELETE CASCADE,
    do_id UUID REFERENCES dos(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- High-Priority Constraint: Exclusive arc (attachment links to at most one module)
    CONSTRAINT chk_attachment_target CHECK (
        ((stay_id IS NOT NULL)::int + (nav_id IS NOT NULL)::int + (do_id IS NOT NULL)::int) <= 1
    )
);

-- ====================================================================
-- 8. INDEXES (HIGH-PRIORITY QUERY OPTIMIZATION)
-- ====================================================================

-- Foreign Key Indexes (Eliminate full table sequential scans on JOINs / CASCADE deletes)
CREATE INDEX idx_trips_created_by ON trips(created_by);
CREATE INDEX idx_trip_members_user_id ON trip_members(user_id);
CREATE INDEX idx_trip_members_trip_id ON trip_members(trip_id);

CREATE INDEX idx_stays_trip_id ON stays(trip_id);
CREATE INDEX idx_stays_created_by ON stays(created_by);

CREATE INDEX idx_navs_trip_id ON navs(trip_id);
CREATE INDEX idx_navs_created_by ON navs(created_by);

CREATE INDEX idx_dos_trip_id ON dos(trip_id);
CREATE INDEX idx_dos_created_by ON dos(created_by);

CREATE INDEX idx_attachments_trip_id ON attachments(trip_id);
CREATE INDEX idx_attachments_stay_id ON attachments(stay_id);
CREATE INDEX idx_attachments_nav_id ON attachments(nav_id);
CREATE INDEX idx_attachments_do_id ON attachments(do_id);
CREATE INDEX idx_attachments_uploaded_by ON attachments(uploaded_by);

-- Compound Indexes (Optimized for Itinerary Timeline, Status Filtering & Dashboard)
CREATE INDEX idx_stays_trip_status_checkin ON stays(trip_id, status, check_in);
CREATE INDEX idx_navs_trip_status_dept ON navs(trip_id, status, departure_time);
CREATE INDEX idx_dos_trip_status_start ON dos(trip_id, status, start_time);
CREATE INDEX idx_trip_members_user_role ON trip_members(user_id, role);
CREATE INDEX idx_trips_created_by_year ON trips(created_by, year);
