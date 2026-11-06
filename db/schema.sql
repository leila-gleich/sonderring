-- ====================================================================
-- SONDERRING MASTER RELATIONAL SCHEMA (PostgreSQL 18)
-- Modernized Architecture: Stays, Moves, Tastes, Plays, Attachments,
-- Security Audit Logs, and Unified Itinerary View
-- ====================================================================

-- 1. USERS & AUTHENTICATION
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    handle VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    password VARCHAR(128) DEFAULT '', -- Hashed password (standard Django PBKDF2/Argon2)
    phone_number VARCHAR(255),        -- AES-256-GCM encrypted
    profile_image_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1b. DECOUPLED OAUTH / SOCIAL IDENTITIES
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
    start_month INT,
    end_month INT,
    status VARCHAR(20) NOT NULL DEFAULT 'UPCOMING' CHECK (status IN ('UPCOMING', 'CURRENT', 'PAST')),
    rec_token VARCHAR(64) UNIQUE,
    created_by_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_trip_time_granularity CHECK (
        (time_granularity = 'SEASON_YEAR' AND season IS NOT NULL) OR
        (time_granularity = 'EXACT_RANGE' AND start_date IS NOT NULL AND end_date IS NOT NULL AND start_date <= end_date) OR
        (time_granularity = 'MONTH' AND start_month IS NOT NULL AND (end_month IS NULL OR start_month <= end_month)) OR
        (time_granularity = 'YEAR')
    ),
    CONSTRAINT chk_trip_start_month CHECK (start_month IS NULL OR (start_month >= 1 AND start_month <= 12)),
    CONSTRAINT chk_trip_end_month CHECK (end_month IS NULL OR (end_month >= 1 AND end_month <= 12))
);

CREATE INDEX idx_trips_created_by ON trips(created_by_id);
CREATE INDEX idx_trips_created_by_year ON trips(created_by_id, year);
CREATE INDEX idx_trips_status ON trips(status);
CREATE INDEX idx_trips_rec_token ON trips(rec_token);

-- 3. TRIP MEMBERS (ACCESS CONTROL / COLLABORATORS)
CREATE TABLE trip_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'EDITOR' CHECK (role IN ('OWNER', 'EDITOR', 'VIEWER')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trip_id, user_id)
);

CREATE INDEX idx_trip_members_trip_id ON trip_members(trip_id);
CREATE INDEX idx_trip_members_user_id ON trip_members(user_id);
CREATE INDEX idx_trip_members_user_role ON trip_members(user_id, role);

-- 4. STAYS (ACCOMMODATIONS)
CREATE TABLE stays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'IDEA' CHECK (status IN ('IDEA', 'CONFIRMED', 'COMPLETE')),
    place_type VARCHAR(50) DEFAULT 'Hotel',
    stay_length INT,
    stay_length_unit VARCHAR(20) DEFAULT 'Days',
    num_beds INT,
    num_rooms INT,
    num_guests INT,
    description TEXT,
    address TEXT,
    check_in TIMESTAMP WITH TIME ZONE,
    check_out TIMESTAMP WITH TIME ZONE,
    has_check_in_time BOOLEAN DEFAULT FALSE,
    has_check_out_time BOOLEAN DEFAULT FALSE,
    total_price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    booking_link TEXT,
    encrypted_confirmation_code TEXT, -- Encrypted via AES-256-GCM
    notes TEXT,                       -- Encrypted via AES-256-GCM
    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_stay_dates CHECK (check_out IS NULL OR check_in IS NULL OR check_out >= check_in),
    CONSTRAINT chk_stay_price CHECK (total_price IS NULL OR total_price >= 0)
);

CREATE INDEX idx_stays_trip_id ON stays(trip_id);
CREATE INDEX idx_stays_trip_status_checkin ON stays(trip_id, status, check_in);

-- 5. MOVES (TRANSPORTATION & LOGISTICS)
CREATE TABLE moves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    mode VARCHAR(50) DEFAULT 'Planes',
    company VARCHAR(150),
    trip_stage VARCHAR(20) DEFAULT 'START_END' CHECK (trip_stage IN ('START_END', 'MID_TRIP')),
    direction VARCHAR(20) DEFAULT 'ARRIVING' CHECK (direction IN ('ARRIVING', 'LEAVING')),
    status VARCHAR(20) NOT NULL DEFAULT 'IDEA' CHECK (status IN ('IDEA', 'CONFIRMED', 'COMPLETE')),
    passenger_name TEXT,              -- Encrypted via AES-256-GCM
    description TEXT,
    origin_address TEXT,
    destination_address TEXT,
    departure_time TIMESTAMP WITH TIME ZONE,
    arrival_time TIMESTAMP WITH TIME ZONE,
    has_departure_time BOOLEAN DEFAULT FALSE,
    has_arrival_time BOOLEAN DEFAULT FALSE,
    date_confidence VARCHAR(20) DEFAULT 'CONFIRMED',
    time_confidence VARCHAR(20) DEFAULT 'CONFIRMED',
    flexibility_notes TEXT,           -- Encrypted via AES-256-GCM
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    booking_link TEXT,
    encrypted_confirmation_code TEXT, -- Encrypted via AES-256-GCM
    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_move_times CHECK (arrival_time IS NULL OR departure_time IS NULL OR arrival_time >= departure_time),
    CONSTRAINT chk_move_price CHECK (price IS NULL OR price >= 0)
);

CREATE INDEX idx_moves_trip_id ON moves(trip_id);
CREATE INDEX idx_moves_trip_status_dept ON moves(trip_id, status, departure_time);

-- 6. TASTES (FOOD & DRINKS / RESTAURANTS & BARS)
CREATE TABLE tastes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    taste_type VARCHAR(50) DEFAULT 'Food',
    cuisine VARCHAR(50),
    drink_category VARCHAR(50),
    status VARCHAR(20) NOT NULL DEFAULT 'IDEA' CHECK (status IN ('IDEA', 'CONFIRMED', 'COMPLETE')),
    description TEXT,
    address TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    has_start_time BOOLEAN DEFAULT FALSE,
    has_end_time BOOLEAN DEFAULT FALSE,
    price NUMERIC(10, 2),
    price_range VARCHAR(10),
    currency VARCHAR(3) DEFAULT 'USD',
    link TEXT,
    menu_link TEXT,
    general_link TEXT,
    encrypted_confirmation_code TEXT, -- Encrypted via AES-256-GCM
    notes TEXT,                       -- Encrypted via AES-256-GCM
    guest_name VARCHAR(100),
    recommended_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_taste_times CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time),
    CONSTRAINT chk_taste_price CHECK (price IS NULL OR price >= 0)
);

CREATE INDEX idx_tastes_trip_id ON tastes(trip_id);
CREATE INDEX idx_tastes_trip_status_start ON tastes(trip_id, status, start_time);

-- 7. PLAYS (ACTIVITIES, SIGHTS & EXPERIENCES)
CREATE TABLE plays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    play_type VARCHAR(50) DEFAULT 'Sightseeing',
    price_tier VARCHAR(10),
    status VARCHAR(20) NOT NULL DEFAULT 'IDEA' CHECK (status IN ('IDEA', 'CONFIRMED', 'COMPLETE')),
    description TEXT,
    address TEXT,
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    has_start_time BOOLEAN DEFAULT FALSE,
    has_end_time BOOLEAN DEFAULT FALSE,
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    link TEXT,
    encrypted_confirmation_code TEXT, -- Encrypted via AES-256-GCM
    notes TEXT,                       -- Encrypted via AES-256-GCM
    guest_name VARCHAR(100),
    recommended_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_play_times CHECK (end_time IS NULL OR start_time IS NULL OR end_time >= start_time),
    CONSTRAINT chk_play_price CHECK (price IS NULL OR price >= 0)
);

CREATE INDEX idx_plays_trip_id ON plays(trip_id);
CREATE INDEX idx_plays_trip_status_start ON plays(trip_id, status, start_time);

-- 8. ATTACHMENTS (SECURE VAULT)
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    stay_id UUID REFERENCES stays(id) ON DELETE CASCADE,
    move_id UUID REFERENCES moves(id) ON DELETE CASCADE,
    taste_id UUID REFERENCES tastes(id) ON DELETE CASCADE,
    play_id UUID REFERENCES plays(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL DEFAULT 'application/pdf',
    storage_path TEXT NOT NULL DEFAULT '',
    file VARCHAR(100),
    uploaded_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_attachment_single_target CHECK (
        ((stay_id IS NOT NULL) AND (move_id IS NULL) AND (taste_id IS NULL) AND (play_id IS NULL)) OR
        ((move_id IS NOT NULL) AND (stay_id IS NULL) AND (taste_id IS NULL) AND (play_id IS NULL)) OR
        ((taste_id IS NOT NULL) AND (stay_id IS NULL) AND (move_id IS NULL) AND (play_id IS NULL)) OR
        ((play_id IS NOT NULL) AND (stay_id IS NULL) AND (move_id IS NULL) AND (taste_id IS NULL)) OR
        ((stay_id IS NULL) AND (move_id IS NULL) AND (taste_id IS NULL) AND (play_id IS NULL))
    )
);

CREATE INDEX idx_attachments_trip_id ON attachments(trip_id);
CREATE INDEX idx_attachments_stay_id ON attachments(stay_id);
CREATE INDEX idx_attachments_move_id ON attachments(move_id);
CREATE INDEX idx_attachments_taste_id ON attachments(taste_id);
CREATE INDEX idx_attachments_play_id ON attachments(play_id);
CREATE INDEX idx_att_trip_created ON attachments(trip_id, created_at);

-- 9. SECURITY AUDIT LOGS (TAMPER-EVIDENT SHA-256 HASH CHAIN)
CREATE TABLE security_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID REFERENCES trips(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    ip_address INET,
    user_agent TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}'::jsonb,
    previous_hash VARCHAR(64) NOT NULL DEFAULT repeat('0', 64),
    record_hash VARCHAR(64) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_security_audit_record_hash UNIQUE (record_hash)
);

CREATE INDEX idx_audit_trip_ts ON security_audit_logs(trip_id, timestamp);
CREATE INDEX idx_audit_user_ts ON security_audit_logs(user_id, timestamp);
CREATE INDEX idx_audit_action_ts ON security_audit_logs(action, timestamp);

-- ====================================================================
-- 10. UNIFIED ITINERARY VIEW (For Desktop Database Apps & Reporting)
-- ====================================================================
CREATE OR REPLACE VIEW v_itinerary_items AS
SELECT
    id,
    trip_id,
    'STAY'::varchar(10) AS item_type,
    title,
    status,
    check_in AS start_time,
    check_out AS end_time,
    total_price AS price,
    currency,
    address,
    NULL::text AS secondary_address,
    place_type::varchar(50) AS subtype,
    booking_link,
    created_by_id,
    updated_by_id,
    created_at,
    updated_at
FROM stays
UNION ALL
SELECT
    id,
    trip_id,
    'MOVE'::varchar(10) AS item_type,
    title,
    status,
    departure_time AS start_time,
    arrival_time AS end_time,
    price,
    currency,
    origin_address AS address,
    destination_address AS secondary_address,
    mode::varchar(50) AS subtype,
    booking_link,
    created_by_id,
    updated_by_id,
    created_at,
    updated_at
FROM moves
UNION ALL
SELECT
    id,
    trip_id,
    'TASTE'::varchar(10) AS item_type,
    title,
    status,
    start_time,
    end_time,
    price,
    currency,
    address,
    NULL::text AS secondary_address,
    taste_type::varchar(50) AS subtype,
    link AS booking_link,
    created_by_id,
    updated_by_id,
    created_at,
    updated_at
FROM tastes
UNION ALL
SELECT
    id,
    trip_id,
    'PLAY'::varchar(10) AS item_type,
    title,
    status,
    start_time,
    end_time,
    price,
    currency,
    address,
    NULL::text AS secondary_address,
    play_type::varchar(50) AS subtype,
    link AS booking_link,
    created_by_id,
    updated_by_id,
    created_at,
    updated_at
FROM plays;
