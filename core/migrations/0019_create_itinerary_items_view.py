from django.db import migrations

CREATE_VIEW_SQL = """
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
"""

DROP_VIEW_SQL = "DROP VIEW IF EXISTS v_itinerary_items;"


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_add_data_integrity_check_constraints'),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_VIEW_SQL,
            reverse_sql=DROP_VIEW_SQL
        ),
    ]
