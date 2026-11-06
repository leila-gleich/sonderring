from django.db import migrations

CASCADE_SQL = """
-- 1. Cascade on Trip deletion
ALTER TABLE stays DROP CONSTRAINT IF EXISTS stays_trip_id_2ff61a43_fk_trips_id;
ALTER TABLE stays DROP CONSTRAINT IF EXISTS stays_trip_id_fk_trips_id;
ALTER TABLE stays ADD CONSTRAINT stays_trip_id_fk_trips_id FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE moves DROP CONSTRAINT IF EXISTS moves_trip_id_20cedd40_fk_trips_id;
ALTER TABLE moves DROP CONSTRAINT IF EXISTS moves_trip_id_fk_trips_id;
ALTER TABLE moves ADD CONSTRAINT moves_trip_id_fk_trips_id FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_trip_id_333ab9d3_fk_trips_id;
ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_trip_id_fk_trips_id;
ALTER TABLE plays ADD CONSTRAINT plays_trip_id_fk_trips_id FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE tastes DROP CONSTRAINT IF EXISTS tastes_trip_id_f04b7079_fk_trips_id;
ALTER TABLE tastes DROP CONSTRAINT IF EXISTS tastes_trip_id_fk_trips_id;
ALTER TABLE tastes ADD CONSTRAINT tastes_trip_id_fk_trips_id FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE trip_members DROP CONSTRAINT IF EXISTS trip_members_trip_id_3adc75ea_fk_trips_id;
ALTER TABLE trip_members DROP CONSTRAINT IF EXISTS trip_members_trip_id_fk_trips_id;
ALTER TABLE trip_members ADD CONSTRAINT trip_members_trip_id_fk_trips_id FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_trip_id_fa17c8f2_fk_trips_id;
ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_trip_id_fk_trips_id;
ALTER TABLE attachments ADD CONSTRAINT attachments_trip_id_fk_trips_id FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

ALTER TABLE security_audit_logs DROP CONSTRAINT IF EXISTS security_audit_logs_trip_id_ea347bde_fk_trips_id;
ALTER TABLE security_audit_logs DROP CONSTRAINT IF EXISTS security_audit_logs_trip_id_fk_trips_id;
ALTER TABLE security_audit_logs ADD CONSTRAINT security_audit_logs_trip_id_fk_trips_id FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE;

-- 2. Cascade on module item deletion for Attachments
ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_stay_id_4c6dfea1_fk_stays_id;
ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_stay_id_fk_stays_id;
ALTER TABLE attachments ADD CONSTRAINT attachments_stay_id_fk_stays_id FOREIGN KEY (stay_id) REFERENCES stays(id) ON DELETE CASCADE;

ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_move_id_daed1f35_fk_moves_id;
ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_move_id_fk_moves_id;
ALTER TABLE attachments ADD CONSTRAINT attachments_move_id_fk_moves_id FOREIGN KEY (move_id) REFERENCES moves(id) ON DELETE CASCADE;

ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_taste_id_a75c5e85_fk_tastes_id;
ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_taste_id_fk_tastes_id;
ALTER TABLE attachments ADD CONSTRAINT attachments_taste_id_fk_tastes_id FOREIGN KEY (taste_id) REFERENCES tastes(id) ON DELETE CASCADE;

ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_play_id_734dba07_fk_plays_id;
ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_play_id_fk_plays_id;
ALTER TABLE attachments ADD CONSTRAINT attachments_play_id_fk_plays_id FOREIGN KEY (play_id) REFERENCES plays(id) ON DELETE CASCADE;

-- 3. Cascade on User deletion for Ownership / Membership / Identity
ALTER TABLE trips DROP CONSTRAINT IF EXISTS trips_created_by_id_b828d324_fk_users_id;
ALTER TABLE trips DROP CONSTRAINT IF EXISTS trips_created_by_id_fk_users_id;
ALTER TABLE trips ADD CONSTRAINT trips_created_by_id_fk_users_id FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE trip_members DROP CONSTRAINT IF EXISTS trip_members_user_id_66f2d0f7_fk_users_id;
ALTER TABLE trip_members DROP CONSTRAINT IF EXISTS trip_members_user_id_fk_users_id;
ALTER TABLE trip_members ADD CONSTRAINT trip_members_user_id_fk_users_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE oauth_identities DROP CONSTRAINT IF EXISTS oauth_identities_user_id_f1cade30_fk_users_id;
ALTER TABLE oauth_identities DROP CONSTRAINT IF EXISTS oauth_identities_user_id_fk_users_id;
ALTER TABLE oauth_identities ADD CONSTRAINT oauth_identities_user_id_fk_users_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 4. Set Null on User deletion for audit and modification links
ALTER TABLE trips DROP CONSTRAINT IF EXISTS trips_updated_by_id_10b24808_fk_users_id;
ALTER TABLE trips DROP CONSTRAINT IF EXISTS trips_updated_by_id_fk_users_id;
ALTER TABLE trips ADD CONSTRAINT trips_updated_by_id_fk_users_id FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE stays DROP CONSTRAINT IF EXISTS stays_created_by_id_4988d47a_fk_users_id;
ALTER TABLE stays DROP CONSTRAINT IF EXISTS stays_created_by_id_fk_users_id;
ALTER TABLE stays ADD CONSTRAINT stays_created_by_id_fk_users_id FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE stays DROP CONSTRAINT IF EXISTS stays_updated_by_id_182dd7a0_fk_users_id;
ALTER TABLE stays DROP CONSTRAINT IF EXISTS stays_updated_by_id_fk_users_id;
ALTER TABLE stays ADD CONSTRAINT stays_updated_by_id_fk_users_id FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE moves DROP CONSTRAINT IF EXISTS moves_created_by_id_82159ca0_fk_users_id;
ALTER TABLE moves DROP CONSTRAINT IF EXISTS moves_created_by_id_fk_users_id;
ALTER TABLE moves ADD CONSTRAINT moves_created_by_id_fk_users_id FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE moves DROP CONSTRAINT IF EXISTS moves_updated_by_id_d13c7ff3_fk_users_id;
ALTER TABLE moves DROP CONSTRAINT IF EXISTS moves_updated_by_id_fk_users_id;
ALTER TABLE moves ADD CONSTRAINT moves_updated_by_id_fk_users_id FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_created_by_id_5b8a43b8_fk_users_id;
ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_created_by_id_fk_users_id;
ALTER TABLE plays ADD CONSTRAINT plays_created_by_id_fk_users_id FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_recommended_by_id_b0c23acb_fk_users_id;
ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_recommended_by_id_fk_users_id;
ALTER TABLE plays ADD CONSTRAINT plays_recommended_by_id_fk_users_id FOREIGN KEY (recommended_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_updated_by_id_cd277b73_fk_users_id;
ALTER TABLE plays DROP CONSTRAINT IF EXISTS plays_updated_by_id_fk_users_id;
ALTER TABLE plays ADD CONSTRAINT plays_updated_by_id_fk_users_id FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE tastes DROP CONSTRAINT IF EXISTS tastes_created_by_id_058ef225_fk_users_id;
ALTER TABLE tastes DROP CONSTRAINT IF EXISTS tastes_created_by_id_fk_users_id;
ALTER TABLE tastes ADD CONSTRAINT tastes_created_by_id_fk_users_id FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE tastes DROP CONSTRAINT IF EXISTS tastes_recommended_by_id_c81082a5_fk_users_id;
ALTER TABLE tastes DROP CONSTRAINT IF EXISTS tastes_recommended_by_id_fk_users_id;
ALTER TABLE tastes ADD CONSTRAINT tastes_recommended_by_id_fk_users_id FOREIGN KEY (recommended_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE tastes DROP CONSTRAINT IF EXISTS tastes_updated_by_id_47b44bda_fk_users_id;
ALTER TABLE tastes DROP CONSTRAINT IF EXISTS tastes_updated_by_id_fk_users_id;
ALTER TABLE tastes ADD CONSTRAINT tastes_updated_by_id_fk_users_id FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_uploaded_by_id_ffd2878c_fk_users_id;
ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_uploaded_by_id_fk_users_id;
ALTER TABLE attachments ADD CONSTRAINT attachments_uploaded_by_id_fk_users_id FOREIGN KEY (uploaded_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_updated_by_id_45c66f7b_fk_users_id;
ALTER TABLE attachments DROP CONSTRAINT IF EXISTS attachments_updated_by_id_fk_users_id;
ALTER TABLE attachments ADD CONSTRAINT attachments_updated_by_id_fk_users_id FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE security_audit_logs DROP CONSTRAINT IF EXISTS security_audit_logs_user_id_4e796a42_fk_users_id;
ALTER TABLE security_audit_logs DROP CONSTRAINT IF EXISTS security_audit_logs_user_id_fk_users_id;
ALTER TABLE security_audit_logs ADD CONSTRAINT security_audit_logs_user_id_fk_users_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_create_itinerary_items_view'),
    ]

    operations = [
        migrations.RunSQL(
            sql=CASCADE_SQL,
            reverse_sql=migrations.RunSQL.noop
        ),
    ]
