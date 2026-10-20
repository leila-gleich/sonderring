-- ====================================================================
-- MIGRATION 001: High-Priority Integrity Constraints and Indexes
-- Target Database: PostgreSQL
-- ====================================================================

-- 1. CONDITIONAL INTEGRITY CONSTRAINTS
ALTER TABLE trips ADD CONSTRAINT chk_trip_time_granularity CHECK (
    (time_granularity = 'SEASON_YEAR' AND season IS NOT NULL) OR
    (time_granularity = 'EXACT_RANGE' AND start_date IS NOT NULL AND end_date IS NOT NULL AND start_date <= end_date) OR
    (time_granularity = 'MONTH' AND start_month IS NOT NULL AND (end_month IS NULL OR start_month <= end_month)) OR
    (time_granularity = 'YEAR')
);

ALTER TABLE stays ADD CONSTRAINT chk_stay_dates CHECK (
    check_out IS NULL OR check_in IS NULL OR check_out >= check_in
);

ALTER TABLE navs ADD CONSTRAINT chk_nav_times CHECK (
    arrival_time IS NULL OR departure_time IS NULL OR arrival_time >= departure_time
);

ALTER TABLE dos ADD CONSTRAINT chk_do_times CHECK (
    end_time IS NULL OR start_time IS NULL OR end_time >= start_time
);

ALTER TABLE attachments ADD CONSTRAINT chk_attachment_target CHECK (
    ((stay_id IS NOT NULL)::int + (nav_id IS NOT NULL)::int + (do_id IS NOT NULL)::int) <= 1
);

-- 2. FOREIGN KEY INDEXES
CREATE INDEX IF NOT EXISTS idx_trips_created_by ON trips(created_by);
CREATE INDEX IF NOT EXISTS idx_trip_members_user_id ON trip_members(user_id);
CREATE INDEX IF NOT EXISTS idx_trip_members_trip_id ON trip_members(trip_id);

CREATE INDEX IF NOT EXISTS idx_stays_trip_id ON stays(trip_id);
CREATE INDEX IF NOT EXISTS idx_stays_created_by ON stays(created_by);

CREATE INDEX IF NOT EXISTS idx_navs_trip_id ON navs(trip_id);
CREATE INDEX IF NOT EXISTS idx_navs_created_by ON navs(created_by);

CREATE INDEX IF NOT EXISTS idx_dos_trip_id ON dos(trip_id);
CREATE INDEX IF NOT EXISTS idx_dos_created_by ON dos(created_by);

CREATE INDEX IF NOT EXISTS idx_attachments_trip_id ON attachments(trip_id);
CREATE INDEX IF NOT EXISTS idx_attachments_stay_id ON attachments(stay_id);
CREATE INDEX IF NOT EXISTS idx_attachments_nav_id ON attachments(nav_id);
CREATE INDEX IF NOT EXISTS idx_attachments_do_id ON attachments(do_id);
CREATE INDEX IF NOT EXISTS idx_attachments_uploaded_by ON attachments(uploaded_by);

-- 3. COMPOUND ITINERARY & ACCESS INDEXES
CREATE INDEX IF NOT EXISTS idx_stays_trip_status_checkin ON stays(trip_id, status, check_in);
CREATE INDEX IF NOT EXISTS idx_navs_trip_status_dept ON navs(trip_id, status, departure_time);
CREATE INDEX IF NOT EXISTS idx_dos_trip_status_start ON dos(trip_id, status, start_time);
CREATE INDEX IF NOT EXISTS idx_trip_members_user_role ON trip_members(user_id, role);
CREATE INDEX IF NOT EXISTS idx_trips_created_by_year ON trips(created_by, year);
