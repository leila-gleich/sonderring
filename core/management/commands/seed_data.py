import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import UserProfile, Trip, TripMember, Stay, Nav, Do, Rec, Attachment

class Command(BaseCommand):
    help = 'Seeds canonical Sonderring trips and demo data based on real-world trip archives'

    def handle(self, *args, **options):
        self.stdout.write("Seeding Sonderring database with canonical trips and users...")

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
            description='Flagship Mediterranean journey exploring the ancient forts of Valletta, coastal swimming at Gozo Blue Lagoon, and Sicilian wine & dining in Taormina and Syracuse.',
            location='Malta, Sicily (Taormina, Syracuse), Gozo',
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
            notes='Proposed lodging for our 3-night Gozo extension.',
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
            origin_address='Los Angeles International Airport (LAX)',
            destination_address='Malta International Airport (MLA)',
            price=1280.00,
            currency='USD',
            date_confidence='CONFIRMED',
            time_confidence='CONFIRMED',
            flexibility_notes='Layover of 2h 45m at JFK Terminal 4.',
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
            destination_address='Mgarr Harbour, Gozo',
            price=45.00,
            currency='USD',
            flexibility_notes='Ferries run every 45 minutes; tickets bought at the pier.',
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

        # Dos
        Do.objects.create(
            trip=trip_malticilia,
            title='Valletta Waterfront & Upper Barrakka Gardens',
            activity_type='Sightseeing',
            status='CONFIRMED',
            address='Upper Barrakka Gardens, Battery St, Valletta, Malta',
            price=0.00,
            description='Historic midday cannon salute and panoramic views over the three cities.',
            created_by=leila
        )

        Do.objects.create(
            trip=trip_malticilia,
            title='Comino & Blue Lagoon Private Boat Charter',
            activity_type='Activity',
            status='IDEA',
            address='Blue Lagoon, Comino Island, Malta',
            price=65.00,
            description='Full-day swimming, snorkeling, and cave exploration.',
            created_by=alex
        )

        Do.objects.create(
            trip=trip_malticilia,
            title='Taormina Wine Bar Tastings & Cliffside Dinner',
            activity_type='Dining',
            status='CONFIRMED',
            address='Piazza IX Aprile, Taormina, Italy',
            price=120.00,
            description='Etna Rosso wine tasting paired with fresh Sicilian seafood.',
            created_by=sam
        )

        # Recs
        Rec.objects.create(
            trip=trip_malticilia,
            title='Trattoria da Nino for fresh swordfish pasta',
            category='Food',
            address='Via Pirandello 37, Taormina, Italy',
            description='Best artisanal pasta in town, highly recommended by locals. Book 3 days early.',
            recommended_by=sam
        )
        Rec.objects.create(
            trip=trip_malticilia,
            title='Isola Bella pebble beach and nature reserve swim',
            category='Spot',
            address='Isola Bella, Taormina, Sicily',
            description='Bring water shoes for the rocky beach; cable car goes straight down from town.',
            recommended_by=alex
        )
        Rec.objects.create(
            trip=trip_malticilia,
            title='Visit Blue Grotto before noon for calm waters',
            category='Tip',
            description='The light hits the caverns best between 10 AM and 11:30 AM before afternoon winds pick up.',
            recommended_by=leila
        )

        # Vault attachment
        Attachment.objects.create(
            trip=trip_malticilia,
            stay=stay_scl,
            file_name='Villa_Bellini_Taormina_Receipt.pdf',
            file_type='application/pdf',
            storage_path='vault/demo/villa_bellini.pdf',
            uploaded_by=sam
        )

        # ==========================================
        # TRIP 2: Iceland (Ring Road & South Coast)
        # ==========================================
        trip_iceland = Trip.objects.create(
            title='Iceland Ring Road Expedition',
            description='8-day road trip across the Golden Circle, South Coast waterfalls, and geothermal hot springs in a 4x4 campervan.',
            location='Ring Road, Reykjavik, South Coast, Iceland',
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
            notes='Geothermal hot tub included outside the cabin. Ideal base for Golden Circle.',
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
            notes='Central location near University of Iceland and downtown.',
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
            notes='Backup lodging choice right on main shopping street.',
            created_by=leila
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
            destination_address='Keflavík International Airport (KEF)',
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
            origin_address='Keflavík Airport Car Rental Desk',
            destination_address='Ring Road & Selfoss Basecamp',
            departure_time=timezone.make_aware(datetime.datetime(2026, 10, 14, 21, 30)),
            arrival_time=timezone.make_aware(datetime.datetime(2026, 10, 22, 9, 0)),
            price=640.00,
            currency='USD',
            flexibility_notes='Studded tires and gravel insurance included for F-roads.',
            created_by=jordan
        )
        nav_suv.confirmation_code = 'CAMP-99120-IS'
        nav_suv.save()

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
            description='Walk through the Almannagjá rift valley between the North American and Eurasian tectonic plates.',
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
            description='Freshly baked bread and endless tomato soup inside a geothermal greenhouse.',
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
            description='Oldest natural hot spring swimming pool in Iceland.',
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
            description='Scenic river path hike leading to intense azure-blue falls.',
            created_by=sam
        )

        Do.objects.create(
            trip=trip_iceland,
            title='Northern Lights Super Jeep Tour with Hot Chocolate',
            activity_type='Tour',
            status='IDEA',
            address='Reykjavik Hotel Pickups',
            price=260.00,
            description='Chase auroras away from city light pollution with professional photographer.',
            created_by=jordan
        )

        # Recs
        Rec.objects.create(
            trip=trip_iceland,
            title='Bæjarins Beztu Pylsur famous hot dog stand',
            category='Food',
            address='Tryggvagata 1, 101 Reykjavik, Iceland',
            description='Order "eina með öllu" (one with everything including crispy fried onions and remoulade).',
            recommended_by=jordan
        )
        Rec.objects.create(
            trip=trip_iceland,
            title='Reynisfjara sneaker waves caution',
            category='Tip',
            description='Never turn your back to the ocean on the black sand beach. Sneaker waves pull people in unexpectedly.',
            recommended_by=leila
        )
        Rec.objects.create(
            trip=trip_iceland,
            title='Walk behind Seljalandsfoss waterfall at golden hour',
            category='Spot',
            address='Seljalandsfoss, Route 1, Iceland',
            description='Bring waterproof pants and jacket; the mist covers you completely.',
            recommended_by=sam
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
        # TRIP 3: Norway Fjords & Hurtigruten Cruise
        # ==========================================
        trip_norway = Trip.objects.create(
            title='Norway Fjords Coastal Voyage',
            description='Coastal expedition from Kirkenes to Bergen aboard Hurtigruten, stopping at Tromsø, Sommarøy, Trondheim, and Ålesund.',
            location='Kirkenes, Trondheim, Ålesund, Bergen, Norway',
            time_granularity='MONTH',
            start_month=9,
            end_month=10,
            year=2026,
            created_by=leila
        )
        TripMember.objects.create(trip=trip_norway, user=leila, role='OWNER')
        TripMember.objects.create(trip=trip_norway, user=alex, role='EDITOR')

        # Navs
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
            flexibility_notes='Stops in Trondheim, Ålesund, Brønnøysund, and Geiranger.',
            created_by=leila
        )
        nav_cruise.confirmation_code = 'HRTG-88192-NO'
        nav_cruise.save()

        # Dos
        Do.objects.create(
            trip=trip_norway,
            title='Nidaros Cathedral Historic Tour in Trondheim',
            activity_type='Sightseeing',
            status='CONFIRMED',
            address='Kongsgårdsgata 2, 7013 Trondheim, Norway',
            price=18.00,
            description='Gothic cathedral dating back to 1070 AD.',
            created_by=alex
        )

        Do.objects.create(
            trip=trip_norway,
            title='Aksla Viewpoint 418 Steps Climb in Ålesund',
            activity_type='Outdoor',
            status='CONFIRMED',
            address='Fjellstua, Aksla, 6003 Ålesund, Norway',
            price=0.00,
            description='Panoramic viewpoint over the Art Nouveau archipelago.',
            created_by=leila
        )

        # ==========================================
        # PAST TRIPS (From Sonderring.com Prototype)
        # ==========================================
        # 4. Joshua Tree Jan '22
        trip_jt22 = Trip.objects.create(
            title="Joshua Tree Jan '22",
            description='High desert cabin retreat with stargazing, campfire cooking, and bouldering at Jumbo Rocks.',
            location='Joshua Tree National Park, California',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2022, 1, 14),
            end_date=datetime.date(2022, 1, 17),
            year=2022,
            created_by=leila
        )
        TripMember.objects.create(trip=trip_jt22, user=leila, role='OWNER')
        TripMember.objects.create(trip=trip_jt22, user=sam, role='EDITOR')

        # 5. NYE 21-22
        trip_nye = Trip.objects.create(
            title="NYE 21-22",
            description='New York City New Years celebration, Central Park winter strolls, and holiday dining.',
            location='New York City, New York',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2021, 12, 30),
            end_date=datetime.date(2022, 1, 3),
            year=2021,
            created_by=leila
        )
        TripMember.objects.create(trip=trip_nye, user=leila, role='OWNER')

        # 6. California Sept. '21
        trip_cal = Trip.objects.create(
            title="California Sept. '21",
            description='Pacific Coast Highway road trip from San Francisco down through Big Sur and Napa Valley wine country.',
            location='Big Sur, San Francisco, Napa Valley, California',
            time_granularity='MONTH',
            start_month=9,
            year=2021,
            created_by=leila
        )
        TripMember.objects.create(trip=trip_cal, user=leila, role='OWNER')

        # 7. Utah/Vegas '21
        trip_utah = Trip.objects.create(
            title="Utah/Vegas '21",
            description='Fly-drive national park loop through Zion Narrows, Angels Landing, and Bryce Canyon.',
            location='Las Vegas, Zion National Park, Bryce Canyon',
            time_granularity='YEAR',
            year=2021,
            created_by=leila
        )
        TripMember.objects.create(trip=trip_utah, user=leila, role='OWNER')

        # 8. Colorado '21
        trip_co = Trip.objects.create(
            title="Colorado '21",
            description='Alpine hiking in Rocky Mountain National Park and craft brewery tours in Denver and Boulder.',
            location='Denver, Boulder, Rocky Mountain National Park, Colorado',
            time_granularity='YEAR',
            year=2021,
            created_by=leila
        )
        TripMember.objects.create(trip=trip_co, user=leila, role='OWNER')

        # 9. Asheville Dec '21
        trip_ash = Trip.objects.create(
            title="Asheville Dec '21",
            description='Biltmore Estate holiday candlelight tour and Blue Ridge Mountain winter exploration.',
            location='Asheville, Blue Ridge Mountains, North Carolina',
            time_granularity='EXACT_RANGE',
            start_date=datetime.date(2021, 12, 10),
            end_date=datetime.date(2021, 12, 13),
            year=2021,
            created_by=leila
        )
        TripMember.objects.create(trip=trip_ash, user=leila, role='OWNER')

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded database with {Trip.objects.count()} trips and {UserProfile.objects.count()} users!"))
