import datetime
from django.utils import timezone
from core.models import UserProfile, Trip, TripMember, Stay, Nav, Do, Rec, Attachment
from core.md_sync import sync_trip_to_markdown

def bootstrap_canonical_trips(stdout=None):
    def log(msg):
        if stdout and hasattr(stdout, "write"):
            stdout.write(str(msg) + "\n")
        else:
            print(msg)

    log("Seeding Sonderring database with all 11 canonical trips, elements, and users...")

    # 1. Users
    leila, _ = UserProfile.objects.get_or_create(
        email='leila@sonderring.com',
        defaults={
            'handle': 'leila',
            'full_name': 'Leila Gleich',
            'phone_number': '+1-310-555-0192',
            'profile_image_url': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=200&q=80'
        }
    )
    leila.set_password('Sonderring2026!')
    leila.save()

    sam, _ = UserProfile.objects.get_or_create(
        email='sam@sonderring.com',
        defaults={
            'handle': 'samt',
            'full_name': 'Sam Taylor',
            'phone_number': '+1-415-555-0144',
            'profile_image_url': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=200&q=80'
        }
    )
    sam.set_password('Sonderring2026!')
    sam.save()

    alex, _ = UserProfile.objects.get_or_create(
        email='alex@sonderring.com',
        defaults={
            'handle': 'alexm',
            'full_name': 'Alex Morgan',
            'phone_number': '+1-212-555-0188',
            'profile_image_url': 'https://images.unsplash.com/photo-1517841905240-472988babdf9?auto=format&fit=crop&w=200&q=80'
        }
    )
    alex.set_password('Sonderring2026!')
    alex.save()

    jordan, _ = UserProfile.objects.get_or_create(
        email='jordan@sonderring.com',
        defaults={
            'handle': 'jordanl',
            'full_name': 'Jordan Lee',
            'phone_number': '+1-646-555-0163',
            'profile_image_url': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=200&q=80'
        }
    )
    jordan.set_password('Sonderring2026!')
    jordan.save()

    # Clear existing trips to allow clean idempotent re-seeding
    Trip.objects.all().delete()

    # ==========================================
    # TRIP 1: Malticilia 26
    # ==========================================
    trip_malticilia = Trip.objects.create(
        title='Malticilia 26',
        description='Flagship Mediterranean journey exploring the ancient forts of Valletta, coastal swimming at Gozo Blue Lagoon, and Sicilian wine & dining in Taormina and Syracuse. Features complex multi-country logistics with flights, inter-island ferries, and coastal rail.',
        location='Malta, Sicily (Taormina, Syracuse), Gozo',
        status='UPCOMING',
        time_granularity='SEASON_YEAR',
        season='SUMMER',
        year=2026,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_malticilia, user=leila, role='OWNER')
    TripMember.objects.create(trip=trip_malticilia, user=sam, role='EDITOR')
    TripMember.objects.create(trip=trip_malticilia, user=alex, role='EDITOR')

    # Stays
    stay_vlt = Stay(
        trip=trip_malticilia,
        title='Valletta Grand Harbour Suites',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='14 St. Barbara Bastion, Valletta VLT 1961, Malta',
        total_price=890.00,
        currency='USD',
        booking_link='https://example.com/valletta-suites',
        notes='Rooftop view of the Grand Harbour. Luggage drop-off available at 11 AM.',
        created_by=leila
    )
    stay_vlt.confirmation_code = 'VLT-5512-MT'
    stay_vlt.save()

    stay_scl = Stay(
        trip=trip_malticilia,
        title='Villa Bellini Taormina',
        status='CONFIRMED',
        place_type='Entire Place',
        num_beds=4,
        num_rooms=3,
        num_guests=6,
        address='Via Teatro Greco 12, 98039 Taormina ME, Sicily, Italy',
        total_price=1420.00,
        currency='USD',
        booking_link='https://example.com/villa-bellini',
        notes='Lockbox code: 4421. Private terrace overlooking Mount Etna.',
        created_by=sam
    )
    stay_scl.confirmation_code = 'BEL-98214-IT'
    stay_scl.save()

    Stay.objects.create(
        trip=trip_malticilia,
        title='Gozo Farmhouse with Pool',
        status='IDEA',
        place_type='Shared Room/Guest House',
        num_beds=5,
        num_rooms=4,
        num_guests=8,
        address='Triq tal-Qasam, Gharb, Gozo, Malta',
        total_price=1100.00,
        currency='USD',
        booking_link='https://example.com/gozo-farmhouse',
        notes='Proposed lodging for our 3-night Gozo extension; walking distance to Gharb village square.',
        created_by=alex
    )

    # Navs
    nav_lax_mla = Nav(
        trip=trip_malticilia,
        title='Multi-hop Flights LAX > JFK > MLA',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila, @sam, @alex',
        origin_address='Los Angeles International Airport (LAX), Terminal 2',
        destination_address='Malta International Airport (MLA), Luqa, Malta',
        price=1280.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='CONFIRMED',
        flexibility_notes='Layover of 2h 45m at JFK Terminal 4. Baggage checked through to MLA.',
        created_by=leila
    )
    nav_lax_mla.confirmation_code = 'DL-67291-MLA'
    nav_lax_mla.save()

    Nav.objects.create(
        trip=trip_malticilia,
        title='Cirkewwa to Mgarr Passenger & Vehicle Ferry',
        mode='Ferry',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        origin_address='Cirkewwa Ferry Terminal, Mellieha, Malta',
        destination_address='Mgarr Harbour, Gozo, Malta',
        price=45.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='TENTATIVE',
        flexibility_notes='Standard Gozo Channel line; tickets bought at the pier upon arrival.',
        created_by=alex
    )

    nav_train = Nav(
        trip=trip_malticilia,
        title='Trenitalia Coastal Rail Syracuse to Taormina',
        mode='Train',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila, @sam, @alex',
        origin_address='Stazione di Siracusa, Piazza della Stazione 1, Syracuse, Italy',
        destination_address='Stazione di Taormina-Giardini, Taormina, Italy',
        price=32.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='CONFIRMED',
        created_by=sam
    )
    nav_train.confirmation_code = 'TRN-817203'
    nav_train.save()

    Nav.objects.create(
        trip=trip_malticilia,
        title='Sicily Regional Car Rental (Catania Airport / Taormina)',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        origin_address='Catania Fontanarossa Airport (CTA)',
        destination_address='Syracuse & Taormina region',
        price=350.00,
        currency='USD',
        date_confidence='TENTATIVE',
        time_confidence='TENTATIVE',
        flexibility_notes='Backup option if group decides against rail; requires automatic transmission booking.',
        created_by=sam
    )

    # Dos
    Do.objects.create(
        trip=trip_malticilia,
        title='Valletta Waterfront & Upper Barrakka Gardens',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Upper Barrakka Gardens, Battery St, Valletta, Malta',
        price=0.00,
        description='Historic midday cannon salute and panoramic views over the Grand Harbour and the Three Cities.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_malticilia,
        title='Taormina Wine Bar Tastings & Cliffside Dinner',
        activity_type='Dining',
        status='CONFIRMED',
        address='Piazza IX Aprile, Taormina, Italy',
        price=120.00,
        description='Etna Rosso DOC wine tasting paired with local Sicilian seafood overlooking the Ionian Sea.',
        created_by=sam
    )

    Do.objects.create(
        trip=trip_malticilia,
        title='Ancient Greek Theater of Taormina Tour',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Via del Teatro Greco 1, 98039 Taormina ME, Italy',
        price=14.00,
        description='Explore the 3rd-century BC Greco-Roman amphitheater with panoramic vistas framing Mount Etna.',
        created_by=sam
    )

    Do.objects.create(
        trip=trip_malticilia,
        title='Comino & Blue Lagoon Private Boat Charter',
        activity_type='Activity',
        status='IDEA',
        address='Blue Lagoon, Comino Island, Malta',
        price=65.00,
        description='Full-day swimming, snorkeling, and sea cave exploration around Comino Island.',
        created_by=alex
    )

    Do.objects.create(
        trip=trip_malticilia,
        title='Ortigia Walking & Historic Market Food Tour',
        activity_type='Dining',
        status='IDEA',
        address='Mercato di Ortigia, Via De Benedictis, Syracuse, Sicily',
        price=40.00,
        description='Sample fresh oysters, Sicilian cannoli, and local cheeses in Syracuse historic island center.',
        created_by=sam
    )

    # Recs
    Rec.objects.create(
        trip=trip_malticilia,
        title='Trattoria da Nino for fresh swordfish pasta',
        category='Food',
        status='CONFIRMED',
        address='Via Pirandello 37, Taormina, Italy',
        link='https://example.com/trattoria-da-nino',
        description='Best artisanal busiate pasta with swordfish and eggplant in town, highly recommended by locals. Book reservation 3 days early.',
        recommended_by=sam
    )
    Rec.objects.create(
        trip=trip_malticilia,
        title='Visit Blue Grotto before noon for calm waters',
        category='Tip',
        status='CONFIRMED',
        address='Blue Grotto, Qrendi, Malta',
        description='The sunlight illuminates the sea caverns best between 10:00 AM and 11:30 AM before afternoon trade winds create choppy water.',
        recommended_by=leila
    )
    Rec.objects.create(
        trip=trip_malticilia,
        title='Isola Bella pebble beach and nature reserve swim',
        category='Spot',
        status='IDEA',
        address='Isola Bella, Taormina, Sicily',
        description='Bring sturdy water shoes for the rocky beach; cable car goes straight down from town center.',
        recommended_by=alex
    )
    Rec.objects.create(
        trip=trip_malticilia,
        title='Ggantija Megalithic Temples Tour',
        category='Spot',
        status='IDEA',
        address='Triq John Otto Bayer, Xaghra, Gozo, Malta',
        description='UNESCO World Heritage prehistoric temple complex older than Stonehenge and the Egyptian pyramids.',
        recommended_by=alex
    )

    # Attachment
    Attachment.objects.create(
        trip=trip_malticilia,
        stay=stay_scl,
        file_name='Villa_Bellini_Taormina_Receipt.pdf',
        file_type='application/pdf',
        storage_path='vault/demo/villa_bellini.pdf',
        uploaded_by=sam
    )

    # ==========================================
    # TRIP 2: Iceland (Ring Road Expedition)
    # ==========================================
    trip_iceland = Trip.objects.create(
        title='Iceland Ring Road Expedition',
        description='8-day road trip across the Golden Circle, South Coast waterfalls, and geothermal hot springs in a 4x4 campervan. Highlights include tectonic rift hiking, glacier viewing, and chasing the Aurora Borealis.',
        location='Ring Road, Reykjavik, South Coast, Selfoss, Iceland',
        status='UPCOMING',
        time_granularity='EXACT_RANGE',
        start_date=datetime.date(2026, 10, 14),
        end_date=datetime.date(2026, 10, 22),
        year=2026,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_iceland, user=leila, role='OWNER')
    TripMember.objects.create(trip=trip_iceland, user=jordan, role='EDITOR')
    TripMember.objects.create(trip=trip_iceland, user=sam, role='VIEWER')

    # Stays
    stay_grims = Stay(
        trip=trip_iceland,
        title='Hotel Grimsborgir Luxury Rooms',
        status='CONFIRMED',
        place_type='Entire Place',
        num_beds=3,
        num_rooms=2,
        num_guests=4,
        address='Asborgir 30, 801 Selfoss, Golden Circle, Iceland',
        check_in=timezone.make_aware(datetime.datetime(2026, 10, 14, 15, 0)),
        check_out=timezone.make_aware(datetime.datetime(2026, 10, 18, 11, 0)),
        total_price=1023.00,
        currency='USD',
        booking_link='https://example.com/grimsborgir',
        notes='Geothermal hot tub included on private cabin terrace. Ideal central staging base for Golden Circle routes.',
        created_by=leila
    )
    stay_grims.confirmation_code = 'GRIM-77319-IS'
    stay_grims.save()

    stay_saga = Stay(
        trip=trip_iceland,
        title='Saga Hotel Reykjavik',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='Hagatorg, 107 Reykjavik, Iceland',
        check_in=timezone.make_aware(datetime.datetime(2026, 10, 18, 15, 0)),
        check_out=timezone.make_aware(datetime.datetime(2026, 10, 22, 11, 0)),
        total_price=1591.00,
        currency='USD',
        booking_link='https://example.com/saga-hotel',
        notes='Central location near University of Iceland and downtown Laugavegur shopping area.',
        created_by=jordan
    )
    stay_saga.confirmation_code = 'SAGA-44012-IS'
    stay_saga.save()

    Stay.objects.create(
        trip=trip_iceland,
        title='Alda Hotel Laugavegur',
        status='IDEA',
        place_type='Hotel Room',
        num_beds=1,
        num_rooms=1,
        num_guests=2,
        address='Laugavegur 89-91, 101 Reykjavik, Iceland',
        total_price=878.00,
        currency='USD',
        notes='Backup downtown lodging option right on the main shopping boulevard with an outdoor courtyard sauna.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_iceland,
        title='Reykjavik Konsulat Hotel (Curio Collection)',
        status='IDEA',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='Hafnarstræti 17-19, 101 Reykjavik, Iceland',
        total_price=1187.00,
        currency='USD',
        notes='Evaluated via Amex Fine Hotels + Resorts ($100 experience credit + breakfast included).',
        created_by=jordan
    )

    # Navs
    nav_ice_flight = Nav(
        trip=trip_iceland,
        title='Delta Flights LAX > KEF Non-stop',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila, @jordan, @sam',
        origin_address='Los Angeles International Airport (LAX)',
        destination_address='Keflavík International Airport (KEF), Iceland',
        departure_time=timezone.make_aware(datetime.datetime(2026, 10, 14, 6, 0)),
        arrival_time=timezone.make_aware(datetime.datetime(2026, 10, 14, 20, 30)),
        price=780.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='CONFIRMED',
        created_by=leila
    )
    nav_ice_flight.confirmation_code = 'DL-KEF-4820'
    nav_ice_flight.save()

    nav_suv = Nav(
        trip=trip_iceland,
        title='4x4 SUV / Campervan Rental',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        origin_address='Keflavík Airport Car Rental Desk, 235 Keflavík, Iceland',
        destination_address='Ring Road & Selfoss Basecamp',
        departure_time=timezone.make_aware(datetime.datetime(2026, 10, 14, 21, 30)),
        arrival_time=timezone.make_aware(datetime.datetime(2026, 10, 22, 9, 0)),
        price=640.00,
        currency='USD',
        flexibility_notes='Studded winter tires and full gravel insurance included for F-roads.',
        created_by=jordan
    )
    nav_suv.confirmation_code = 'CAMP-99120-IS'
    nav_suv.save()

    Nav.objects.create(
        trip=trip_iceland,
        title='Outbound Return Flight KEF > JFK > LAX',
        mode='Flight',
        trip_stage='START_END',
        direction='LEAVING',
        status='CONFIRMED',
        passenger_name='@leila, @jordan, @sam',
        origin_address='Keflavík International Airport (KEF)',
        destination_address='Los Angeles International Airport (LAX)',
        departure_time=timezone.make_aware(datetime.datetime(2026, 10, 22, 11, 30)),
        arrival_time=timezone.make_aware(datetime.datetime(2026, 10, 22, 18, 45)),
        price=820.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_iceland,
        title='Contingency Storm Transit & Highland Route Bypass',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        flexibility_notes='Backup southern highway routing in case of high-wind closures on Route 1 near Vík.',
        price=0.00,
        currency='USD',
        created_by=leila
    )

    # Dos
    Do.objects.create(
        trip=trip_iceland,
        title='Thingvellir National Park Walking Tour',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Thingvellir, 801 Selfoss, Iceland',
        start_time=timezone.make_aware(datetime.datetime(2026, 10, 15, 9, 30)),
        end_time=timezone.make_aware(datetime.datetime(2026, 10, 15, 13, 0)),
        price=0.00,
        description='Walk through the Almannagjá rift valley between the North American and Eurasian continental tectonic plates.',
        created_by=leila
    )

    do_frid = Do(
        trip=trip_iceland,
        title='Friðheimar Greenhouse Tomato Soup & Horse Farm',
        activity_type='Dining',
        status='CONFIRMED',
        address='Friðheimar, 801 Reykholt, Iceland',
        start_time=timezone.make_aware(datetime.datetime(2026, 10, 16, 12, 30)),
        end_time=timezone.make_aware(datetime.datetime(2026, 10, 16, 14, 0)),
        price=45.00,
        description='Freshly baked bread buffet and unlimited tomato soup served directly inside a geothermal greenhouse.',
        created_by=jordan
    )
    do_frid.confirmation_code = 'FRID-8821'
    do_frid.save()

    Do.objects.create(
        trip=trip_iceland,
        title='Secret Lagoon Geothermal Pool Soak',
        activity_type='Activity',
        status='CONFIRMED',
        address='Hvammsvegur, 845 Flúðir, Iceland',
        start_time=timezone.make_aware(datetime.datetime(2026, 10, 16, 15, 30)),
        price=35.00,
        description='Relax in the oldest natural hot spring swimming pool in Iceland, surrounded by mini-geysers.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_iceland,
        title='Brúarfoss Blue Waterfall Hike',
        activity_type='Outdoor',
        status='CONFIRMED',
        address='Brúarvegur, 801 Laugarvatn, Iceland',
        start_time=timezone.make_aware(datetime.datetime(2026, 10, 17, 10, 30)),
        price=0.00,
        description='7 km roundtrip river path hike leading to intense icy-azure cascading glacial falls.',
        created_by=jordan
    )

    Do.objects.create(
        trip=trip_iceland,
        title='Hella Coastal Town & Waterfall Exploration',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Route 1 South Coast, Hella, Iceland',
        start_time=timezone.make_aware(datetime.datetime(2026, 10, 18, 11, 0)),
        end_time=timezone.make_aware(datetime.datetime(2026, 10, 18, 15, 30)),
        price=0.00,
        description='Southern waterfall stops including Seljalandsfoss and Skógafoss with staircase climb to upper cataract.',
        created_by=jordan
    )

    Do.objects.create(
        trip=trip_iceland,
        title='Northern Lights Super Jeep Tour with Hot Chocolate',
        activity_type='Tour',
        status='IDEA',
        address='Reykjavik Hotel Pickups, Reykjavik, Iceland',
        price=260.00,
        description='Chase auroras away from city light pollution with professional astro-photographer guide.',
        created_by=jordan
    )

    Do.objects.create(
        trip=trip_iceland,
        title='Glacier Hiking & Blue Lagoon Geothermal Spa',
        activity_type='Activity',
        status='IDEA',
        address='Sólheimajökull Glacier & Grindavík, Iceland',
        price=145.00,
        description='Guided crampon glacier walk on black volcanic ash ice sheet, followed by post-hike spa soak.',
        created_by=leila
    )

    # Recs
    Rec.objects.create(
        trip=trip_iceland,
        title='Bæjarins Beztu Pylsur famous hot dog stand',
        category='Food',
        status='CONFIRMED',
        address='Tryggvagata 1, 101 Reykjavik, Iceland',
        link='https://bbp.is',
        description='Order "eina með öllu" (one with everything: ketchup, sweet mustard, fried onions, raw onions, remoulade).',
        recommended_by=jordan
    )
    Rec.objects.create(
        trip=trip_iceland,
        title='Reynisfjara sneaker waves safety warning',
        category='Tip',
        status='CONFIRMED',
        address='Reynisfjara Black Sand Beach, Vík, Iceland',
        description='Never turn your back to the ocean on the black sand beach. Sneaker waves pull tourists into freezing rip currents with zero warning.',
        recommended_by=leila
    )
    Rec.objects.create(
        trip=trip_iceland,
        title='Walk behind Seljalandsfoss waterfall at golden hour',
        category='Spot',
        status='IDEA',
        address='Seljalandsfoss, Route 1, Iceland',
        description='Bring waterproof pants and jacket; the wind gusts cover you in glacial spray behind the cavern wall.',
        recommended_by=jordan
    )
    Rec.objects.create(
        trip=trip_iceland,
        title='Lava Tunnel Raufarhólshellir Exploration',
        category='Activity',
        status='IDEA',
        address='Leitahraun, Route 39, Iceland',
        description='Massive subterranean volcanic lava tube cave with illuminated boardwalk paths.',
        recommended_by=jordan
    )

    # Attachment
    Attachment.objects.create(
        trip=trip_iceland,
        nav=nav_ice_flight,
        file_name='Delta_KEF_Flight_BoardingPass.pdf',
        file_type='application/pdf',
        storage_path='vault/demo/delta_kef.pdf',
        uploaded_by=leila
    )

    # ==========================================
    # TRIP 3: Norway Fjords Coastal Voyage
    # ==========================================
    trip_norway = Trip.objects.create(
        title='Norway Fjords Coastal Voyage',
        description='Arctic coastal voyage and fjord navigation from Kirkenes (near the Russian border) south to Bergen aboard the historic Hurtigruten Coastal Express. Features scenic fjord excursions, coastal bus transfers, and historical maritime explorations.',
        location='Kirkenes, Tromsø, Sommarøy, Trondheim, Ålesund, Geiranger, Bergen, Norway',
        status='UPCOMING',
        time_granularity='MONTH',
        start_month=9,
        end_month=10,
        year=2026,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_norway, user=leila, role='OWNER')
    TripMember.objects.create(trip=trip_norway, user=alex, role='EDITOR')

    # Stays
    stay_cruise = Stay(
        trip=trip_norway,
        title='Hurtigruten Coastal Cruise Stateroom (MS Polarlys / Nordlys)',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='Port of Kirkenes to Port of Bergen, Norway',
        total_price=2450.00,
        currency='USD',
        notes='Arctic outside cabin with unobstructed sea view. Full board dining included in voyage package.',
        created_by=leila
    )
    stay_cruise.confirmation_code = 'HRTG-88192-NO'
    stay_cruise.save()

    Stay.objects.create(
        trip=trip_norway,
        title='Bergen Børs Hotel',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=1,
        num_rooms=1,
        num_guests=2,
        address='Vågsallmenningen 1, 5014 Bergen, Norway',
        total_price=540.00,
        currency='USD',
        booking_link='https://example.com/bergen-bors',
        notes='Historic converted stock exchange hotel overlooking the Vågen harbor.',
        created_by=alex
    )

    Stay.objects.create(
        trip=trip_norway,
        title='Kirkenes Snowhotel 365',
        status='IDEA',
        place_type='Shared Room/Guest House',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='Sandnesdalen 14, 9910 Bjørnevatn, Kirkenes, Norway',
        total_price=420.00,
        currency='USD',
        notes='Thermal sleeping bags provided inside ice sculptures; includes husky kennel visit.',
        created_by=alex
    )

    Stay.objects.create(
        trip=trip_norway,
        title='Sommarøy Arctic Hotel',
        status='IDEA',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='Skipsholmen, 9110 Sommarøy, Norway',
        total_price=280.00,
        currency='USD',
        created_by=leila
    )

    # Navs
    Nav.objects.create(
        trip=trip_norway,
        title='Inbound Flight into Kirkenes Airport (KKN)',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila, @alex',
        origin_address='Oslo Gardermoen (OSL)',
        destination_address='Kirkenes Airport Høybuktmoen (KKN), Norway',
        price=220.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='CONFIRMED',
        created_by=alex
    )

    Nav.objects.create(
        trip=trip_norway,
        title='Barents Airport Shuttle to Hurtigruten Port',
        mode='Bus',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila, @alex',
        origin_address='Kirkenes Airport (KKN)',
        destination_address='Hurtigruten Cruise Terminal, Kirkenes Port',
        price=30.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='CONFIRMED',
        created_by=leila
    )

    nav_cruise = Nav(
        trip=trip_norway,
        title='Hurtigruten Coastal Cruise (Kirkenes > Bergen)',
        mode='Ferry',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila, @alex',
        origin_address='Kirkenes Hurtigruten Port, Norway',
        destination_address='Bergen Hurtigruten Terminal, Norway',
        price=2450.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='CONFIRMED',
        flexibility_notes='Multi-port coastal liner stopping in Tromsø, Trondheim, Ålesund, and Geirangerfjord.',
        created_by=leila
    )
    nav_cruise.confirmation_code = 'HRTG-88192-NO'
    nav_cruise.save()

    Nav.objects.create(
        trip=trip_norway,
        title='Outbound Flight from Bergen (BGO)',
        mode='Flight',
        trip_stage='START_END',
        direction='LEAVING',
        status='CONFIRMED',
        passenger_name='@leila, @alex',
        origin_address='Bergen Airport Flesland (BGO), Norway',
        destination_address='Los Angeles International (LAX)',
        price=680.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='CONFIRMED',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_norway,
        title='Sommarøy Fjord Speedboat / RIB Express Transfer',
        mode='Ferry',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        price=95.00,
        currency='USD',
        date_confidence='TENTATIVE',
        time_confidence='TENTATIVE',
        flexibility_notes='Weather-dependent coastal transit between Tromsø and Sommarøy fishing archipelago.',
        created_by=alex
    )

    # Dos
    Do.objects.create(
        trip=trip_norway,
        title='Nidaros Cathedral Historic Tour in Trondheim',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Kongsgårdsgata 2, 7013 Trondheim, Norway',
        price=18.00,
        description='World northernmost medieval cathedral, built over the burial site of King Olav II dating back to 1070 AD.',
        created_by=alex
    )

    Do.objects.create(
        trip=trip_norway,
        title='Aksla Viewpoint 418 Steps Climb in Ålesund',
        activity_type='Outdoor',
        status='CONFIRMED',
        address='Fjellstua, Aksla, 6003 Ålesund, Norway',
        price=0.00,
        description='Climb 418 stone steps from the town park to panoramic viewpoint over Ålesund Art Nouveau peninsula and surrounding fjords.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_norway,
        title='Geirangerfjord UNESCO Waterfall Cruise Excursion',
        activity_type='Tour',
        status='CONFIRMED',
        address='Geirangerfjord, Møre og Romsdal, Norway',
        price=115.00,
        description='Spectacular tender excursion sailing right beneath the Seven Sisters and Suitor cascading waterfalls.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_norway,
        title='Sommarøy Arctic White Sand Beach Walk',
        activity_type='Sightseeing',
        status='IDEA',
        address='Sommarøy, 9110 Troms, Norway',
        price=0.00,
        description='Walk across Caribbean-like turquoise waters and Arctic shell sand beaches in the far north.',
        created_by=alex
    )

    Do.objects.create(
        trip=trip_norway,
        title='Tromsø Fjellheisen Cable Car & Midnight Aurora Watch',
        activity_type='Activity',
        status='IDEA',
        address='Sollivegen 12, 9020 Tromsdalen, Norway',
        price=38.00,
        description='Aerial tramway up Mount Storsteinen (421 meters) for nighttime views over Tromsø island.',
        created_by=alex
    )

    # Recs
    Rec.objects.create(
        trip=trip_norway,
        title='Bryggen historic Hanseatic wooden wharf stroll',
        category='Spot',
        status='CONFIRMED',
        address='Bryggen, 5003 Bergen, Norway',
        description='UNESCO World Heritage site consisting of preserved timber trading quarters along the Vågen harbor.',
        recommended_by=leila
    )
    Rec.objects.create(
        trip=trip_norway,
        title='Hurtigruten exterior deck wind gear preparation',
        category='Tip',
        status='CONFIRMED',
        description='Bring windproof Gore-Tex outer shell, thermal base layers, and fleece balaclava for observation decks when crossing the Arctic Circle.',
        recommended_by=alex
    )
    Rec.objects.create(
        trip=trip_norway,
        title='Fisketorget Bergen Fish Market seafood chowder',
        category='Food',
        status='IDEA',
        address='Strandkaien 3, 5012 Bergen, Norway',
        description='Historic open-air harbor fish market serving traditional creamy Bergen fish soup with fresh cod and shrimp.',
        recommended_by=leila
    )
    Rec.objects.create(
        trip=trip_norway,
        title='Tromsø Arctic Cathedral midnight organ concert',
        category='Activity',
        status='IDEA',
        address='Hans Nilsens veg 41, 9020 Tromsdalen, Norway',
        description='Special candlelit acoustics concert inside the striking triangular stained-glass modernist church.',
        recommended_by=alex
    )

    # ==========================================
    # TRIP 4: Joshua Tree Jan '22
    # ==========================================
    trip_jt22 = Trip.objects.create(
        title="Joshua Tree Jan '22",
        status='PAST',
        description='High-desert off-grid cabin retreat featuring nighttime astrophotography, campfire cooking, and boulder scrambling through Joshua Tree iconic rock labyrinths.',
        location='Joshua Tree National Park & Twentynine Palms, California',
        time_granularity='EXACT_RANGE',
        start_date=datetime.date(2022, 1, 14),
        end_date=datetime.date(2022, 1, 17),
        year=2022,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_jt22, user=leila, role='OWNER')
    TripMember.objects.create(trip=trip_jt22, user=sam, role='EDITOR')

    stay_jt = Stay(
        trip=trip_jt22,
        title='High-Desert Off-Grid Airbnb Cabin Retreat',
        status='CONFIRMED',
        place_type='Entire Place',
        num_beds=3,
        num_rooms=2,
        num_guests=5,
        address='Amboy Road & Valley View, Twentynine Palms, CA 92277',
        total_price=750.00,
        currency='USD',
        booking_link='https://airbnb.com/rooms/joshua-tree-cabin',
        notes='Keyless keypad entry. Outdoor hot tub, propane fire table, and 360-degree dark-sky mountain horizon.',
        created_by=leila
    )
    stay_jt.confirmation_code = 'HMAB-2022-JT'
    stay_jt.save()

    Stay.objects.create(
        trip=trip_jt22,
        title='Pioneertown Motel',
        status='IDEA',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='5240 Curtis Paths, Pioneertown, CA 92268',
        total_price=580.00,
        currency='USD',
        notes='Rustic western movie-set motel next door to Pappy & Harriet.',
        created_by=sam
    )

    Nav.objects.create(
        trip=trip_jt22,
        title='Shared SUV Carpool Convoy from Los Angeles / LAX',
        mode='Car',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila, @sam',
        origin_address='Los Angeles, CA (LAX pickup)',
        destination_address='Twentynine Palms Cabin, CA',
        price=85.00,
        currency='USD',
        flexibility_notes='I-10 East through Banning Pass with grocery stop in Yucca Valley.',
        created_by=sam
    )

    Nav.objects.create(
        trip=trip_jt22,
        title='Local Park Trailhead Driving & Navigation',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila, @sam',
        origin_address='North Entrance (Twentynine Palms)',
        destination_address='Park Boulevard, Hidden Valley & Jumbo Rocks',
        price=30.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_jt22,
        title='Cabazon Outlets & Palm Springs EV Supercharging Stop',
        mode='Car',
        trip_stage='START_END',
        direction='ARRIVING',
        status='IDEA',
        price=25.00,
        currency='USD',
        created_by=sam
    )

    Do.objects.create(
        trip=trip_jt22,
        title='Barker Dam & Hidden Valley Nature Loop Hikes',
        activity_type='Outdoor',
        status='CONFIRMED',
        address='Barker Dam Trailhead, Park Blvd, Joshua Tree National Park',
        price=0.00,
        description='2.5-mile combination trail viewing historic water reservoir, Native American petroglyphs, and iconic Monzogranite rock formations.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_jt22,
        title='Desert Sunset Viewing at Keys View',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Keys View Rd, Joshua Tree National Park',
        price=0.00,
        description='Panoramic crest overlooking the Coachella Valley, Salton Sea, and the San Andreas Fault at twilight.',
        created_by=sam
    )

    Do.objects.create(
        trip=trip_jt22,
        title='Nighttime Desert Stargazing & Astrophotography Session',
        activity_type='Activity',
        status='CONFIRMED',
        address='Cabin Open Desert Deck, Twentynine Palms, CA',
        price=0.00,
        description='Dark sky observation session tracking the Milky Way, constellations, and long-exposure tripod photography.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_jt22,
        title='Rock Scrambling & Bouldering at Jumbo Rocks',
        activity_type='Outdoor',
        status='CONFIRMED',
        address='Jumbo Rocks Campground & Amphitheater, Joshua Tree',
        price=0.00,
        description='Technical rock scrambling across giant granite bulbous formations and labyrinth crevices.',
        created_by=sam
    )

    Do.objects.create(
        trip=trip_jt22,
        title='Integratron Sound Bath Acoustic Meditation',
        activity_type='Activity',
        status='IDEA',
        address='2477 Belfield Blvd, Landers, CA 92285',
        price=50.00,
        description='60-minute sonic healing session inside a wood acoustic dome built on a geomagnetic anomaly.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_jt22,
        title='Cholla Cactus Garden Sunrise Photography',
        activity_type='Sightseeing',
        status='IDEA',
        address='Pinto Basin Rd, Joshua Tree National Park',
        price=0.00,
        description='Golden morning light illuminating thousands of densely packed cholla cactus needles.',
        created_by=sam
    )

    Rec.objects.create(
        trip=trip_jt22,
        title='Bring gallon water jugs and download offline Google/AllTrails maps',
        category='Tip',
        status='CONFIRMED',
        address='Joshua Tree National Park',
        description='Zero cellular signal inside the park boundaries; hydration is critical in the dry high-desert winter air.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_jt22,
        title='Joshua Tree Saloon for live music and post-hike burgers',
        category='Food',
        status='IDEA',
        address='61835 29 Palms Hwy, Joshua Tree, CA 92252',
        description='Lively Old West style watering hole with patio grill and local craft beers.',
        recommended_by=sam
    )

    Rec.objects.create(
        trip=trip_jt22,
        title='Pappy & Harriet Pioneertown Palace',
        category='Food',
        status='IDEA',
        address='53688 Pioneertown Rd, Pioneertown, CA 92268',
        description='Famous mesquite barbecue roadhouse and legendary indie live music venue.',
        recommended_by=leila
    )

    # ==========================================
    # TRIP 5: Joshua Tree Oct '21
    # ==========================================
    trip_jt21 = Trip.objects.create(
        title="Joshua Tree Oct '21",
        status='PAST',
        description='Autumn desert weekend getaway focused on mild daytime bouldering temperatures, sunset viewing, campfire cooking, and gear testing.',
        location='Joshua Tree National Park, California',
        time_granularity='MONTH',
        start_month=10,
        year=2021,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_jt21, user=leila, role='OWNER')

    Stay.objects.create(
        trip=trip_jt21,
        title='Desert Stargazer Homestead Cabin',
        status='CONFIRMED',
        place_type='Entire Place',
        num_beds=2,
        num_rooms=1,
        num_guests=3,
        address='7200 Desert Queen Ave, Twentynine Palms, CA 92277',
        total_price=620.00,
        currency='USD',
        booking_link='https://example.com/desert-stargazer',
        notes='Off-grid solar cabin with outdoor shower and cast-iron woodstove.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_jt21,
        title='Hidden Valley Campground (First-Come, First-Served)',
        status='IDEA',
        place_type='Shared Room/Guest House',
        num_guests=6,
        address='Park Blvd, Joshua Tree National Park',
        total_price=15.00,
        currency='USD',
        notes='Requires arriving before 8:00 AM on Friday to secure an open site.',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_jt21,
        title='Regional Road Trip Transport from Southern California',
        mode='Car',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Los Angeles Basin (I-10 East)',
        destination_address='Joshua Tree West Entrance, CA',
        price=70.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_jt21,
        title='Park Trailhead Route & Scenic Drive',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        origin_address='Park Entrance',
        destination_address='Jumbo Rocks, Hall of Horrors, Ryan Mountain',
        price=0.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_jt21,
        title='Palm Springs Scenic Highway 111 Detour',
        mode='Car',
        trip_stage='START_END',
        direction='ARRIVING',
        status='IDEA',
        price=15.00,
        currency='USD',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_jt21,
        title='Rock Scrambling at Jumbo Rocks',
        activity_type='Outdoor',
        status='CONFIRMED',
        address='Jumbo Rocks, Joshua Tree National Park',
        price=0.00,
        description='Boulder scrambling across granite corridors and natural arches in moderate autumn weather.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_jt21,
        title='Desert Sunset Viewing at Keys View',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Keys View Rd, Joshua Tree National Park',
        price=0.00,
        description='Sunset watch over the Coachella Valley and San Jacinto peaks with evening desert colors.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_jt21,
        title='Campfire Bonding & Outdoor Dutch-Oven Cooking',
        activity_type='Dining',
        status='CONFIRMED',
        address='Cabin Fire Pit, Twentynine Palms, CA',
        price=45.00,
        description='Campfire chili and dutch-oven cornbread cooked over mesquite coals.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_jt21,
        title='Skull Rock Nature Trail Loop Walk',
        activity_type='Sightseeing',
        status='IDEA',
        address='Park Blvd near Jumbo Rocks',
        price=0.00,
        description='Short 1.7-mile self-guided nature trail featuring wind-eroded skull hollows.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_jt21,
        title='Ryan Mountain Summit Hike',
        activity_type='Outdoor',
        status='IDEA',
        address='Ryan Mountain Trailhead, Joshua Tree',
        price=0.00,
        description='Strenuous 1,000-foot vertical elevation climb to the center peak of the national park.',
        created_by=leila
    )

    Rec.objects.create(
        trip=trip_jt21,
        title='Layer clothing for drastic 35-degree temperature drops at dusk',
        category='Tip',
        status='CONFIRMED',
        description='Clear desert skies mean radiant heat vanishes immediately once the sun drops behind the mountains; pack insulated down jackets even on 80°F days.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_jt21,
        title='Natural Sisters Cafe for organic breakfast burritos',
        category='Food',
        status='IDEA',
        address='61760 29 Palms Hwy, Joshua Tree, CA 92252',
        description='Popular cafe serving homemade vegetarian wraps, vegan baked goods, and iced smoothies.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_jt21,
        title='Coyote Corner for local desert gifts & trail maps',
        category='Spot',
        status='IDEA',
        address='6535 Park Blvd, Joshua Tree, CA 92252',
        description='Authentic local outfitter store selling field guides, minerals, and desert survival gear.',
        recommended_by=leila
    )

    # ==========================================
    # TRIP 6: New York City (NYE 21-22)
    # ==========================================
    trip_nye = Trip.objects.create(
        title="NYE 21-22",
        status='PAST',
        description='New York City holiday winter celebration featuring the Times Square New Year Eve countdown, ice skating at Central Park, boutique Soho dining, and comprehensive subway transit.',
        location='Manhattan & Brooklyn, New York City, New York',
        time_granularity='EXACT_RANGE',
        start_date=datetime.date(2021, 12, 30),
        end_date=datetime.date(2022, 1, 3),
        year=2021,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_nye, user=leila, role='OWNER')

    stay_archer = Stay(
        trip=trip_nye,
        title='Archer Hotel New York (Midtown Manhattan)',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=1,
        num_rooms=1,
        num_guests=2,
        address='45 W 38th St, New York, NY 10018',
        total_price=1450.00,
        currency='USD',
        booking_link='https://example.com/archer-nyc',
        notes='Midtown boutique hotel within walking distance of Bryant Park and Herald Square subway hubs; rooftop view of the Empire State Building.',
        created_by=leila
    )
    stay_archer.confirmation_code = 'ARCH-NYC-2112'
    stay_archer.save()

    Stay.objects.create(
        trip=trip_nye,
        title='The Hoxton, Williamsburg',
        status='IDEA',
        place_type='Hotel Room',
        num_beds=1,
        num_rooms=1,
        num_guests=2,
        address='97 Wythe Ave, Brooklyn, NY 11249',
        total_price=1280.00,
        currency='USD',
        notes='Trendy waterfront hotel with rooftop skyline views of Lower Manhattan across the East River.',
        created_by=leila
    )

    nav_nyc = Nav(
        trip=trip_nye,
        title='Inbound Flight into New York (LAX > JFK)',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Los Angeles International Airport (LAX)',
        destination_address='John F. Kennedy International Airport (JFK), Terminal 4',
        price=420.00,
        currency='USD',
        date_confidence='CONFIRMED',
        time_confidence='CONFIRMED',
        created_by=leila
    )
    nav_nyc.confirmation_code = 'B6-JFK-9102'
    nav_nyc.save()

    Nav.objects.create(
        trip=trip_nye,
        title='MTA Subway Unlimited Pass & JFK AirTrain',
        mode='Train',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Jamaica Station / Howard Beach',
        destination_address='Midtown Manhattan (34th St / Herald Sq)',
        price=41.25,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_nye,
        title='Outbound Return Flight (LGA > LAX)',
        mode='Flight',
        trip_stage='START_END',
        direction='LEAVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='LaGuardia Airport (LGA), Terminal B',
        destination_address='Los Angeles International Airport (LAX)',
        price=440.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_nye,
        title='Yellow Taxi / Uber Airport Transfer (JFK > Midtown)',
        mode='Rideshare',
        trip_stage='START_END',
        direction='ARRIVING',
        status='IDEA',
        price=85.00,
        currency='USD',
        flexibility_notes='Flat rate cab option if snow delays subways.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_nye,
        title='Times Square New Year Eve Countdown',
        activity_type='Event',
        status='CONFIRMED',
        address='Times Square / Broadway & 42nd St, New York, NY',
        price=0.00,
        description='Ringing in 2022 amidst the annual Waterford Crystal ball drop and confetti shower in central Manhattan.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_nye,
        title='Central Park Winter Walk & Wollman Rink Ice Skating',
        activity_type='Activity',
        status='CONFIRMED',
        address='Wollman Rink, 830 5th Ave, New York, NY 10065',
        price=35.00,
        description='Outdoor ice skating surrounded by Central Park winter trees and the South Central Park skyline.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_nye,
        title='Group Holiday Dining in Soho / West Village',
        activity_type='Dining',
        status='CONFIRMED',
        address='Balthazar, 80 Spring St, New York, NY 10012',
        price=140.00,
        description='French brasserie New Year holiday dinner featuring oysters, duck confit, and festive champagne.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_nye,
        title='Broadway Matinee Show Reservation',
        activity_type='Tour',
        status='IDEA',
        address='Minskoff Theatre, 200 W 45th St, New York, NY',
        price=160.00,
        description='Broadway theater matinee performance in the heart of the theater district.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_nye,
        title='Brooklyn Bridge Pedestrian Sunset Walk',
        activity_type='Sightseeing',
        status='IDEA',
        address='Brooklyn Bridge Promenade, New York, NY',
        price=0.00,
        description='Golden hour walk from DUMBO across the historic suspension bridge into Lower Manhattan.',
        created_by=leila
    )

    Rec.objects.create(
        trip=trip_nye,
        title='Joe Pizza on Carmine Street for authentic NYC slice',
        category='Food',
        status='CONFIRMED',
        address='7 Carmine St, New York, NY 10014',
        description='Quintessential New York cheese slice; quick standing room only with crispy, foldable thin crust.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_nye,
        title='Download offline MTA Subway map before entering stations',
        category='Tip',
        status='CONFIRMED',
        description='Deep underground stations and cross-river tunnel segments frequently lack cellular connectivity; having the offline PDF or app map saved prevents navigation confusion.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_nye,
        title='The High Line elevated linear park stroll',
        category='Spot',
        status='IDEA',
        address='High Line (Gansevoort St to 34th St), New York, NY',
        description='Former elevated freight rail line transformed into a landscaped public park overlooking Hudson Yards and Chelsea.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_nye,
        title='Levain Bakery warm chocolate chip walnut cookies',
        category='Food',
        status='IDEA',
        address='167 W 74th St, New York, NY 10023',
        description='Massive, gooey, warm 6-ounce cookies fresh from the oven on the Upper West Side.',
        recommended_by=leila
    )

    # ==========================================
    # TRIP 7: California Sept. '21
    # ==========================================
    trip_cal = Trip.objects.create(
        title="California Sept. '21",
        status='PAST',
        description='Pacific Coast Highway road trip connecting San Francisco coastal headlands, cliffside Big Sur ocean overlooks, and estate winery tastings across Napa and Sonoma valleys.',
        location='Big Sur, San Francisco, Napa Valley, California',
        time_granularity='MONTH',
        start_month=9,
        year=2021,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_cal, user=leila, role='OWNER')

    Stay.objects.create(
        trip=trip_cal,
        title='Big Sur River Inn & Lodge',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='46800 CA-1, Big Sur, CA 93920',
        total_price=680.00,
        currency='USD',
        booking_link='https://example.com/big-sur-river-inn',
        notes='Adirondack chairs set directly in the Big Sur River; redwood forest setting.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_cal,
        title='St. Helena Vineyard Guest Cottage',
        status='CONFIRMED',
        place_type='Entire Place',
        num_beds=2,
        num_rooms=2,
        num_guests=4,
        address='Main St & Sulphur Springs Ave, St. Helena, Napa Valley, CA 94574',
        total_price=920.00,
        currency='USD',
        booking_link='https://example.com/st-helena-cottage',
        notes='Private cottage located directly on an organic Cabernet Sauvignon vineyard; private patio and barbecue grill.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_cal,
        title='Post Ranch Inn (Cliff House)',
        status='IDEA',
        place_type='Entire Place',
        num_beds=1,
        num_rooms=1,
        num_guests=2,
        address='47900 CA-1, Big Sur, CA 93920',
        total_price=1450.00,
        currency='USD',
        notes='Overhang cliff architecture 1,200 feet above the Pacific Ocean with infinity hot tubs.',
        created_by=leila
    )

    nav_sfo = Nav(
        trip=trip_cal,
        title='Inbound Flights into San Francisco (LAX > SFO)',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Los Angeles International Airport (LAX)',
        destination_address='San Francisco International Airport (SFO)',
        price=210.00,
        currency='USD',
        created_by=leila
    )
    nav_sfo.confirmation_code = 'UA-SFO-8190'
    nav_sfo.save()

    Nav.objects.create(
        trip=trip_cal,
        title='Pacific Coast Highway (PCH) Rental SUV',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='SFO Rental Car Center',
        destination_address='Highway 1 / Big Sur / Napa Valley Circuit',
        price=380.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_cal,
        title='Outbound Return Flight (SFO > LAX)',
        mode='Flight',
        trip_stage='START_END',
        direction='LEAVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='San Francisco International Airport (SFO)',
        destination_address='Los Angeles International Airport (LAX)',
        price=220.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_cal,
        title='Napa Valley Wine Train or Group Chauffeur Service',
        mode='Train',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        price=180.00,
        currency='USD',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_cal,
        title='McWay Falls & Pfeiffer Beach Purple Sand Exploration',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Julia Pfeiffer Burns State Park & Sycamore Canyon Rd, Big Sur, CA',
        price=10.00,
        description='View the 80-foot waterfall dropping straight into an emerald ocean cove, followed by purple garnet mineral sand dunes at Keyhole Rock.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_cal,
        title='Bixby Creek Bridge Photography Stop',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='CA-1, Monterey County, CA 93940',
        price=0.00,
        description='Iconic concrete single-span open-spandrel arch bridge spanning the canyon overlook.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_cal,
        title='Napa Valley Estate Winery Tastings & Cellar Tour',
        activity_type='Dining',
        status='CONFIRMED',
        address='Rutherford & Stag Leap District, Napa Valley, CA',
        price=160.00,
        description='Reserved tastings at historic stone cellar wineries featuring Bordeaux blends and estate olive oils.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_cal,
        title='Hot Air Balloon Flight over Napa Valley',
        activity_type='Activity',
        status='IDEA',
        address='6525 Washington St, Yountville, CA 94599',
        price=290.00,
        description='Sunrise balloon ascension over morning fog rolls and endless vineyard rows.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_cal,
        title='Muir Woods National Monument Redwood Canopy Walk',
        activity_type='Outdoor',
        status='IDEA',
        address='1 Muir Woods Rd, Mill Valley, CA 94941',
        price=15.00,
        description='Stroll beneath old-growth coastal redwoods over 1,000 years old.',
        created_by=leila
    )

    Rec.objects.create(
        trip=trip_cal,
        title='Nepenthe cliffside restaurant for Ambrosia burgers',
        category='Food',
        status='CONFIRMED',
        address='48510 CA-1, Big Sur, CA 93920',
        description='Famous redwood outdoor terrace situated 800 feet above the Pacific; extraordinary ocean views with no reservations needed for the terrace bar.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_cal,
        title='Check Caltrans QuickMap for Highway 1 landslide closures',
        category='Tip',
        status='CONFIRMED',
        description='Pacific Coast Highway between Ragged Point and Big Sur experiences seasonal mudslides; always confirm road passability before departure.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_cal,
        title='Oxbow Public Market in Napa for artisanal picnic provisions',
        category='Food',
        status='IDEA',
        address='610 1st St, Napa, CA 94559',
        description='Gourmet indoor market hall with wood-fired pizza, local cheeses, charcuterie, and artisanal chocolates.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_cal,
        title='Point Lobos State Natural Reserve coastal tide pools',
        category='Spot',
        status='IDEA',
        address='62 CA-1, Carmel-By-The-Sea, CA 93923',
        description='Known as the crown jewel of California State Parks, featuring sea otters, harbor seals, and Monterey cypress groves.',
        recommended_by=leila
    )

    # ==========================================
    # TRIP 8: Utah/Vegas '21
    # ==========================================
    trip_utah = Trip.objects.create(
        title="Utah/Vegas '21",
        status='PAST',
        description='Fly-drive national park loop through southwestern red rock country, featuring the towering canyon walls of Zion, the hoodoo natural amphitheaters of Bryce Canyon, and neon nightlife on the Las Vegas Strip.',
        location='Las Vegas, Zion National Park, Bryce Canyon, Nevada / Utah',
        time_granularity='YEAR',
        year=2021,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_utah, user=leila, role='OWNER')

    Stay.objects.create(
        trip=trip_utah,
        title='Desert Pearl Inn (Springdale / Zion Entrance)',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=3,
        address='705 Zion Park Blvd, Springdale, UT 84767',
        total_price=780.00,
        currency='USD',
        booking_link='https://example.com/desert-pearl',
        notes='Located directly on the Virgin River; 3-minute ride on the free town shuttle to the Zion National Park South Entrance footbridge.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_utah,
        title='Bellagio Resort & Casino (Las Vegas Strip)',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='3600 S Las Vegas Blvd, Las Vegas, NV 89109',
        total_price=640.00,
        currency='USD',
        notes='Strip-view fountain room booked via Amex FHR.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_utah,
        title='Under Canvas Zion Glamping',
        status='IDEA',
        place_type='Entire Place',
        num_beds=2,
        num_rooms=1,
        num_guests=4,
        address='3955 Kolob Terrace Rd, Virgin, UT 84779',
        total_price=850.00,
        currency='USD',
        notes='Upscale canvas tent with ensuite bathroom, wood-burning stove, and private patio on 196 secluded desert acres.',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_utah,
        title='Flights into Las Vegas McCarran (LAX > LAS)',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Los Angeles International Airport (LAX)',
        destination_address='Harry Reid / McCarran International Airport (LAS), Las Vegas, NV',
        price=230.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_utah,
        title='4x4 National Park Road Trip SUV Rental',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='LAS Airport Car Rental Center',
        destination_address='Las Vegas > St. George > Springdale > Bryce Canyon Circuit',
        price=410.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_utah,
        title='Zion Canyon Scenic Boulevard Shuttle',
        mode='Bus',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        price=0.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_utah,
        title='Outbound Return Flight (LAS > LAX)',
        mode='Flight',
        trip_stage='START_END',
        direction='LEAVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Harry Reid International Airport (LAS)',
        destination_address='Los Angeles International Airport (LAX)',
        price=240.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_utah,
        title='Bryce Canyon National Park Guided Tour Shuttle',
        mode='Bus',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        price=60.00,
        currency='USD',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_utah,
        title='Zion Narrows Wading Hike & Angel Landing Chain Section',
        activity_type='Outdoor',
        status='CONFIRMED',
        address='Temple of Sinawava & The Grotto, Zion National Park',
        price=0.00,
        description='Hike the narrow 1,500-foot sandstone gorge of the Virgin River wading knee-deep in current, followed by the exhilarating chain-assisted ridge ascent to Angel Landing overlook.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_utah,
        title='Bryce Canyon Natural Amphitheater Sunrise Viewing',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Sunrise Point, Bryce Canyon National Park',
        price=0.00,
        description='Watch dawn golden sunlight break across thousands of red, orange, and white limestone hoodoo spires.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_utah,
        title='Las Vegas Strip Group Dining & Fountain Gala',
        activity_type='Dining',
        status='CONFIRMED',
        address='Spago / Lago by Julian Serrano, Bellagio, Las Vegas, NV',
        price=125.00,
        description='Fountain-side Italian lakeside dining with choreographed musical fountain water shows.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_utah,
        title='Guided Canyoneering & Slot Canyon Rappelling in Orderville Canyon',
        activity_type='Activity',
        status='IDEA',
        address='Orderville Canyon, East Zion, UT',
        price=175.00,
        description='Professional guide service navigating technical sandstone rappels and desert slot waterfalls.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_utah,
        title='Bryce Canyon Dark Sky Astronomy Telescope Session',
        activity_type='Outdoor',
        status='IDEA',
        address='Bryce Canyon Visitor Center Telescope Field',
        price=0.00,
        description='Ranger-led telescope session under one of the darkest certified night skies in North America.',
        created_by=leila
    )

    Rec.objects.create(
        trip=trip_utah,
        title='Rent dry bibs, neoprene booties, and wooden sticks in Springdale',
        category='Tip',
        status='CONFIRMED',
        address='Zion Outfitters, 95 Zion Park Blvd, Springdale, UT',
        description='Essential gear for the Narrows; river boulders are covered in slick moss and water temperatures remain cold year-round.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_utah,
        title='Bit & Spur Restaurant & Saloon for Southwestern dinner',
        category='Food',
        status='CONFIRMED',
        address='1212 Zion Park Blvd, Springdale, UT 84767',
        description='Incredible smoked pork chile verde, sweet potato tamales, and prickly pear margaritas on a garden patio.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_utah,
        title='Queen Garden & Navajo Loop combination trail in Bryce',
        category='Spot',
        status='IDEA',
        address='Sunset Point to Sunrise Point, Bryce Canyon',
        description='Walk down through Wall Street—a narrow, sheer slot canyon between towering limestone switchbacks and 400-year-old Douglas firs.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_utah,
        title='Oscar Cafe in Springdale for massive post-hike breakfasts',
        category='Food',
        status='IDEA',
        address='948 Zion Park Blvd, Springdale, UT 84767',
        description='Legendary gigantic ribeye steak and eggs, chile verde omelets, and fresh salsa.',
        recommended_by=leila
    )

    # ==========================================
    # TRIP 9: Colorado '21
    # ==========================================
    trip_co = Trip.objects.create(
        title="Colorado '21",
        status='PAST',
        description='Alpine mountain road trip across the Front Range and Continental Divide, featuring gold aspen leaf-peeping, high-altitude hiking along Trail Ridge Road, and craft brewery hopping in Denver and Boulder.',
        location='Denver, Boulder, Rocky Mountain National Park, Colorado',
        time_granularity='YEAR',
        year=2021,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_co, user=leila, role='OWNER')

    Stay.objects.create(
        trip=trip_co,
        title='Estes Park Mountain Timber Cabin',
        status='CONFIRMED',
        place_type='Entire Place',
        num_beds=3,
        num_rooms=2,
        num_guests=4,
        address='Fish Creek Rd, Estes Park, CO 80517',
        total_price=720.00,
        currency='USD',
        booking_link='https://example.com/estes-cabin',
        notes='Wood-burning stone fireplace, outdoor hot tub, and frequent elk wandering through the meadow.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_co,
        title='The Maven Hotel at Dairy Block (Denver LoDo)',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=1,
        num_rooms=1,
        num_guests=2,
        address='1850 Wazee St, Denver, CO 80202',
        total_price=540.00,
        currency='USD',
        notes='Modern boutique hotel in Denver pedestrian Dairy Block micro-district; walkable to Union Station.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_co,
        title='St Julien Hotel & Spa (Boulder)',
        status='IDEA',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='900 Walnut St, Boulder, CO 80302',
        total_price=650.00,
        currency='USD',
        notes='Unobstructed view of the Boulder Flatirons from the terrace.',
        created_by=leila
    )

    nav_den = Nav(
        trip=trip_co,
        title='Inbound Flights into Denver International Airport (DEN)',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Los Angeles International Airport (LAX)',
        destination_address='Denver International Airport (DEN), Terminal West',
        price=195.00,
        currency='USD',
        created_by=leila
    )
    nav_den.confirmation_code = 'WN-DEN-4421'
    nav_den.save()

    Nav.objects.create(
        trip=trip_co,
        title='Mountain AWD SUV Rental with Roof Rack',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='DEN Airport Car Rental Center',
        destination_address='Denver > Boulder > Estes Park > Trail Ridge Road Circuit',
        price=360.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_co,
        title='Outbound Return Flight from Denver (DEN > LAX)',
        mode='Flight',
        trip_stage='START_END',
        direction='LEAVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Denver International Airport (DEN)',
        destination_address='Los Angeles International Airport (LAX)',
        price=210.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_co,
        title='Rocky Mountain National Park Hiker Shuttle',
        mode='Bus',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        price=2.00,
        currency='USD',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_co,
        title='Rocky Mountain Alpine Hiking along Trail Ridge Road',
        activity_type='Outdoor',
        status='CONFIRMED',
        address='Trail Ridge Road & Alpine Visitor Center (Elevation 11,796 ft), RMNP',
        price=0.00,
        description='Drive the highest continuous paved highway in North America through windswept alpine tundra with panoramic Continental Divide vistas.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_co,
        title='Scenic Leaf-Peeping Drives for Fall Aspen Foliage',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Peak to Peak Scenic Byway (CO-7 / CO-72), Nederland to Estes Park',
        price=0.00,
        description='Golden aspen groves glowing against jagged snowcapped granite peaks.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_co,
        title='Craft Brewery Tours in Denver & Boulder',
        activity_type='Dining',
        status='CONFIRMED',
        address='RiNo Art District (Denver) & Pearl Street (Boulder)',
        price=75.00,
        description='Microbrewery crawls tasting hazy IPAs, wild fermented sours, and crisp pilsners at pioneering Front Range taprooms.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_co,
        title='Red Rocks Amphitheatre Morning Stair Climb & Visitor Center',
        activity_type='Activity',
        status='IDEA',
        address='18300 W Alameda Pkwy, Morrison, CO 80465',
        price=0.00,
        description='Run the historic sandstone amphitheater stairs and visit the Colorado Music Hall of Fame.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_co,
        title='Bear Lake to Emerald Lake Alpine Lakes Hike',
        activity_type='Sightseeing',
        status='IDEA',
        address='Bear Lake Trailhead, Rocky Mountain National Park',
        price=0.00,
        description='3.6-mile trail passing Nymph Lake, Dream Lake, and beneath the dramatic vertical face of Hallett Peak.',
        created_by=leila
    )

    Rec.objects.create(
        trip=trip_co,
        title='Hydrate aggressively and acclimatize for 24 hours to prevent altitude sickness',
        category='Tip',
        status='CONFIRMED',
        description='Trail Ridge Road exceeds 12,000 feet elevation where oxygen levels are ~33% lower than sea level. Drink at least 3 liters of water daily, avoid heavy alcohol on night one, and carry electrolyte tablets.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_co,
        title='Great Divide Brewing Company in Denver for Yeti Imperial Stout',
        category='Food',
        status='CONFIRMED',
        address='2201 Arapahoe St, Denver, CO 80205',
        description='Classic Denver downtown brewery taproom with legendary roasted malt stouts and rotating experimental taps.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_co,
        title='The Stanley Hotel historic ghost & architecture tour in Estes Park',
        category='Spot',
        status='IDEA',
        address='333 E Wonderview Ave, Estes Park, CO 80517',
        description='Historic 1909 Georgian colonial revival resort that inspired Stephen King The Shining.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_co,
        title='Avery Brewing Company in Boulder for barrel-aged ales',
        category='Food',
        status='IDEA',
        address='4910 Nautilus Ct N, Boulder, CO 80301',
        description='Massive open-air beer hall in Gunbarrel with world-class bourbon barrel-aged specialty beers and barbecue.',
        recommended_by=leila
    )

    # ==========================================
    # TRIP 10: Asheville Dec '21
    # ==========================================
    trip_ash = Trip.objects.create(
        title="Asheville Dec '21",
        status='PAST',
        description='Winter holiday weekend getaway nestled in the Blue Ridge Mountains, centered around the Biltmore Estate Christmas candlelight tour, craft dining in downtown Asheville, and crisp mountain lookout drives.',
        location='Asheville, Blue Ridge Mountains, North Carolina',
        time_granularity='EXACT_RANGE',
        start_date=datetime.date(2021, 12, 10),
        end_date=datetime.date(2021, 12, 13),
        year=2021,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_ash, user=leila, role='OWNER')

    stay_alb = Stay(
        trip=trip_ash,
        title='Albemarle Inn Historic Bed & Breakfast',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=1,
        num_rooms=1,
        num_guests=2,
        address='86 Edgemont Rd, Asheville, NC 28804',
        total_price=580.00,
        currency='USD',
        booking_link='https://example.com/albemarle-inn',
        notes='1909 Greek Revival mansion in the Grove Park residential historic district; gourmet two-course cooked breakfast included daily.',
        created_by=leila
    )
    stay_alb.confirmation_code = 'ALB-2112-NC'
    stay_alb.save()

    Stay.objects.create(
        trip=trip_ash,
        title='The Omni Grove Park Inn',
        status='IDEA',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='290 Macon Ave, Asheville, NC 28804',
        total_price=890.00,
        currency='USD',
        notes='Famous subterranean subterranean rock spa and annual National Gingerbread House Competition display.',
        created_by=leila
    )

    nav_avl = Nav(
        trip=trip_ash,
        title='Regional Flights into Asheville (LAX > CLT > AVL)',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Los Angeles International Airport (LAX)',
        destination_address='Asheville Regional Airport (AVL), Fletcher, NC',
        price=310.00,
        currency='USD',
        created_by=leila
    )
    nav_avl.confirmation_code = 'AA-AVL-7832'
    nav_avl.save()

    Nav.objects.create(
        trip=trip_ash,
        title='Blue Ridge Mountain Rental AWD Car',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='AVL Airport Terminal Desk',
        destination_address='Asheville & Blue Ridge Parkway Overlooks',
        price=220.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_ash,
        title='Outbound Return Flight (AVL > CLT > LAX)',
        mode='Flight',
        trip_stage='START_END',
        direction='LEAVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Asheville Regional Airport (AVL)',
        destination_address='Los Angeles International Airport (LAX)',
        price=325.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_ash,
        title='Historic Asheville Gray Line Trolley Tour',
        mode='Bus',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        price=35.00,
        currency='USD',
        created_by=leila
    )

    do_bilt = Do(
        trip=trip_ash,
        title='Biltmore Estate Holiday Evening Candlelight Tour',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='1 Lodge St, Asheville, NC 28803',
        price=110.00,
        description='George Vanderbilt 250-room French Renaissance chateau decorated with dozens of Christmas trees, thousands of ornaments, roaring fireplaces, and live choir performances.',
        created_by=leila
    )
    do_bilt.confirmation_code = 'BIL-DEC-2104'
    do_bilt.save()

    Do.objects.create(
        trip=trip_ash,
        title='Blue Ridge Parkway Scenic Lookouts & Craggy Gardens',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Blue Ridge Parkway MP 364.1 to MP 382, NC',
        price=0.00,
        description='High-elevation mountain parkway drive through rock tunnels with frosty winter vistas over the French Broad River valley.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_ash,
        title='Downtown Arts District Culinary & Gallery Walk',
        activity_type='Dining',
        status='CONFIRMED',
        address='Biltmore Ave & Broadway St, Asheville, NC',
        price=65.00,
        description='Stroll independent bookstore passages, contemporary pottery studios, and sample local artisanal cider.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_ash,
        title='French Broad Chocolate Lounge Dessert Tasting',
        activity_type='Dining',
        status='IDEA',
        address='10 S Pack Square, Asheville, NC 28801',
        price=25.00,
        description='Artisan bean-to-bar hot chocolate, liquid truffles, and lavender honey mousse cakes.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_ash,
        title='DuPont State Forest Triple Falls Winter Walk',
        activity_type='Outdoor',
        status='IDEA',
        address='Staton Rd, Cedar Mountain, NC 28718',
        price=0.00,
        description='2.2-mile scenic trail viewing High Falls, Triple Falls, and Hooker Falls cascading over frozen granite riverbed drops.',
        created_by=leila
    )

    Rec.objects.create(
        trip=trip_ash,
        title='Cúrate Bar de Tapas for world-class Spanish tapas',
        category='Food',
        status='CONFIRMED',
        address='13 Biltmore Ave, Asheville, NC 28801',
        description='James Beard award-winning Spanish tapas restaurant by Chef Katie Button. Must order the jamón ibérico de bellota, grilled octopus, and crispy patatas bravas. Reservations mandatory weeks in advance.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_ash,
        title='Check Blue Ridge Parkway gate alerts for winter closures',
        category='Tip',
        status='CONFIRMED',
        description='The National Park Service frequently locks access gates between Milepost 355 and 380 after light snow or freezing temperatures due to shaded road icing.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_ash,
        title='River Arts District working artist warehouse studios',
        category='Spot',
        status='IDEA',
        address='Roberts St & Depot St along the French Broad River',
        description='23 historic industrial buildings converted into open studios for 300+ local ceramicists, glassblowers, and painters.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_ash,
        title='Burial Beer Co. South Slope taproom & forestry camp',
        category='Food',
        status='IDEA',
        address='40 Collier Ave, Asheville, NC 28801',
        description='Cult favorite taproom serving complex hazy IPAs, saisons, and pastry stouts with a rustic outdoor patio.',
        recommended_by=leila
    )

    # ==========================================
    # TRIP 11: Hawaii Multi-Island Exploration
    # ==========================================
    trip_hawaii = Trip.objects.create(
        title='Hawaii',
        status='UPCOMING',
        description='Multi-island tropical journey exploring volcanic lava fields, marine life sanctuaries, rainforest lodges, and coastal road trips across the Big Island and Maui.',
        location='Kona (Big Island), Volcano Village, Maui, Hawaii',
        time_granularity='MONTH',
        start_month=5,
        end_month=6,
        year=2026,
        created_by=leila
    )
    TripMember.objects.create(trip=trip_hawaii, user=leila, role='OWNER')

    Stay.objects.create(
        trip=trip_hawaii,
        title='Volcano Village Rainforest Treehouse Cottage',
        status='CONFIRMED',
        place_type='Entire Place',
        num_beds=2,
        num_rooms=1,
        num_guests=3,
        address='Wright Rd & Kilauea Rd, Volcano Village, Big Island, HI 96785',
        total_price=950.00,
        currency='USD',
        booking_link='https://example.com/volcano-treehouse',
        notes='Secluded cedar treehouse enveloped by giant native hapu tree ferns, 5 minutes from the national park entrance; indoor fireplace and outdoor cedar hot tub.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_hawaii,
        title='Outrigger Kona Resort & Spa (Keauhou Bay)',
        status='CONFIRMED',
        place_type='Hotel Room',
        num_beds=2,
        num_rooms=1,
        num_guests=2,
        address='78-128 Ehukai St, Kailua-Kona, HI 96740',
        total_price=1420.00,
        currency='USD',
        booking_link='https://example.com/outrigger-kona',
        notes='Oceanfront cliffs overlooking manta ray feeding grounds; private balcony and saltwater lagoon pool.',
        created_by=leila
    )

    Stay.objects.create(
        trip=trip_hawaii,
        title='Hana-Maui Resort (Hyatt Destination)',
        status='IDEA',
        place_type='Entire Place',
        num_beds=1,
        num_rooms=1,
        num_guests=2,
        address='5031 Hana Hwy, Hana, Maui, HI 96713',
        total_price=1250.00,
        currency='USD',
        notes='Ocean view plantation bungalow with private lanai; ideal base to avoid driving the Hana Highway round-trip in one day.',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_hawaii,
        title='Inbound Transpacific Flight (LAX > KOA)',
        mode='Flight',
        trip_stage='START_END',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Los Angeles International Airport (LAX)',
        destination_address='Ellison Onizuka Kona International Airport (KOA), Kailua-Kona, HI',
        price=520.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_hawaii,
        title='Inter-Island Hop Flight (KOA > OGG)',
        mode='Flight',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Kona International Airport (KOA)',
        destination_address='Kahului Airport (OGG), Maui, HI',
        price=190.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_hawaii,
        title='Island 4x4 Jeep Wrangler Rentals',
        mode='Car',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='KOA Airport & OGG Airport',
        destination_address='Saddle Road, South Point, and Hana Highway routes',
        price=580.00,
        currency='USD',
        flexibility_notes='4-wheel drive required for Mauna Kea access road past the visitor center.',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_hawaii,
        title='Outbound Return Flight (OGG > LAX)',
        mode='Flight',
        trip_stage='START_END',
        direction='LEAVING',
        status='CONFIRMED',
        passenger_name='@leila',
        origin_address='Kahului Airport (OGG), Maui, HI',
        destination_address='Los Angeles International Airport (LAX)',
        price=490.00,
        currency='USD',
        created_by=leila
    )

    Nav.objects.create(
        trip=trip_hawaii,
        title='Expeditions Maui-to-Lanai Passenger Ferry',
        mode='Ferry',
        trip_stage='MID_TRIP',
        direction='ARRIVING',
        status='IDEA',
        price=60.00,
        currency='USD',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_hawaii,
        title='Snorkeling at Kealakekua Bay Marine Sanctuary',
        activity_type='Activity',
        status='CONFIRMED',
        address='Kealakekua Bay / Captain Cook Monument, Kona, HI',
        price=85.00,
        description='Snorkel in crystal-clear protected coral reef waters with pods of Hawaiian spinner dolphins, green sea turtles, and vibrant parrotfish.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_hawaii,
        title='Hawaii Volcanoes National Park Crater Rim Exploration',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Crater Rim Drive & Chain of Craters Rd, Volcano, HI 96718',
        price=30.00,
        description='Walk through Thurston Lava Tube (Nahuku), witness steaming sulfur vents, and view active Halemaumau summit crater glow at dusk.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_hawaii,
        title='Sunset Beach Sessions & Local Farmers Market Visits',
        activity_type='Sightseeing',
        status='CONFIRMED',
        address='Hapuna Beach State Recreation Area & Waimea Town Market',
        price=10.00,
        description='White-sand swimming on the Kohala Coast followed by fresh tropical fruit and local macadamia nut treats.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_hawaii,
        title='Manta Ray Night Snorkel Tour in Keauhou Bay',
        activity_type='Activity',
        status='IDEA',
        address='Keauhou Bay Boat Ramp, Kailua-Kona, HI',
        price=135.00,
        description='Float over an illuminated neon light board while giant 12-foot manta rays somersault inches below feeding on plankton.',
        created_by=leila
    )

    Do.objects.create(
        trip=trip_hawaii,
        title='Haleakala National Park Sunrise Crater Summit',
        activity_type='Outdoor',
        status='IDEA',
        address='Haleakala Highway, Kula, Maui, HI 96790',
        price=1.50,
        description='Watch the sun rise above a blanket of clouds from the 10,023-foot summit of Maui dormant shield volcano.',
        created_by=leila
    )

    Rec.objects.create(
        trip=trip_hawaii,
        title='Strict reef-safe mineral sunscreen requirement across all islands',
        category='Tip',
        status='CONFIRMED',
        description='Hawaii state law bans sunscreens containing oxybenzone and octinoxate to protect coral reefs. Use only non-nano zinc oxide or titanium dioxide mineral formulas.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_hawaii,
        title='Da Poke Shack in Kailua-Kona for ultra-fresh ahi poke',
        category='Food',
        status='CONFIRMED',
        address='76-6246 Ali‘i Dr, Kailua-Kona, HI 96740',
        description='Legendary roadside counter serving freshly caught yellowfin ahi poke with Wet Shack sesame oil, spicy garlic, and seaweed salad.',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_hawaii,
        title='Punaluu Black Sand Beach to view resting honu (green sea turtles)',
        category='Spot',
        status='IDEA',
        address='Ninole Loop Rd, Pahala, HI 96777',
        description='Jet-black basalt volcanic sand beach lined with coconut palms where large green sea turtles frequently bask on the warm sand (maintain legal 10-foot distance).',
        recommended_by=leila
    )

    Rec.objects.create(
        trip=trip_hawaii,
        title='Merriman Waimea for farm-to-table Hawaiian regional cuisine',
        category='Food',
        status='IDEA',
        address='65-1227 Opelo Rd, Kamuela, HI 96743',
        description='Pioneering restaurant by Chef Peter Merriman featuring local grass-fed Big Island beef, macadamia nut crusted mahi-mahi, and organic Upcountry produce.',
        recommended_by=leila
    )

    # Mark confirmed elements on historical past trips as COMPLETE
    from core.md_sync import sync_trip_to_markdown
    for past_trip in Trip.objects.filter(status='PAST'):
        past_trip.stays.filter(status='CONFIRMED').update(status='COMPLETE')
        past_trip.navs.filter(status='CONFIRMED').update(status='COMPLETE')
        past_trip.dos.filter(status='CONFIRMED').update(status='COMPLETE')
        past_trip.recs.filter(status='CONFIRMED').update(status='COMPLETE')
        sync_trip_to_markdown(past_trip)

    log(f"Successfully seeded database with all {Trip.objects.count()} trips and {UserProfile.objects.count()} users!")

