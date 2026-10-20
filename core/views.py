from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Trip, Stay, Nav, Do, UserProfile, TripMember, Attachment

# ==========================================
# Server-Rendered Desktop Request Handlers
# ==========================================

def dashboard_view(request):
    """
    Renders the main TripSpace dashboard view displaying user trips.
    """
    trips = Trip.objects.all().order_by('-created_at')
    context = {
        'trips': trips,
        'past_trips': [
            "Joshua Tree Jan '22",
            "NYE 21-22",
            "California Sept. '21",
            "Utah/Vegas '21",
            "Joshua Tree Oct '21",
            "Colorado '21",
            "Asheville Dec '21",
        ]
    }
    return render(request, 'dashboard.html', context)


def profile_view(request):
    """
    Renders the user profile page.
    """
    user_profile = UserProfile.objects.first()
    context = {'user_profile': user_profile}
    return render(request, 'dashboard.html', context)


def trip_workspace_view(request, trip_id):
    """
    Renders the detailed Trip Workspace view with Timeline, Stays, Navs, Dos, and Vault.
    """
    trip = get_object_or_404(Trip, id=trip_id)
    stays = trip.stays.all()
    navs = trip.navs.all()
    dos = trip.dos.all()
    attachments = trip.attachments.all()
    members = trip.members.select_related('user').all()

    context = {
        'trip': trip,
        'stays': stays,
        'navs': navs,
        'dos': dos,
        'attachments': attachments,
        'members': members,
    }
    return render(request, 'dashboard.html', context)


# ==========================================
# REST API Endpoints (Mobile / Client Sync)
# ==========================================

class TripListCreateAPIView(APIView):
    """
    API endpoint to list and create Trip records.
    """
    def get(self, request):
        trips = Trip.objects.all().values(
            'id', 'title', 'description', 'location',
            'time_granularity', 'season', 'year',
            'start_date', 'end_date', 'created_at'
        )
        return Response(list(trips), status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data
        user_id = data.get('created_by')
        user = UserProfile.objects.filter(id=user_id).first() if user_id else UserProfile.objects.first()

        if not user:
            return Response(
                {"error": "UserProfile required to create a trip."},
                status=status.HTTP_400_BAD_REQUEST
            )

        trip = Trip.objects.create(
            title=data.get('title', 'Untitled Trip'),
            description=data.get('description', ''),
            location=data.get('location', 'TBD'),
            time_granularity=data.get('time_granularity', 'YEAR'),
            season=data.get('season'),
            year=data.get('year', 2024),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            created_by=user
        )
        TripMember.objects.create(trip=trip, user=user, role='OWNER')
        return Response({"id": str(trip.id), "title": trip.title}, status=status.HTTP_201_CREATED)


class StayListCreateAPIView(APIView):
    """
    API endpoint for accommodations (Stays), supporting confirmation code encryption.
    """
    def get(self, request, trip_id):
        stays = Stay.objects.filter(trip_id=trip_id)
        results = []
        for s in stays:
            results.append({
                'id': str(s.id),
                'title': s.title,
                'status': s.status,
                'address': s.address,
                'check_in': s.check_in,
                'check_out': s.check_out,
                'total_price': str(s.total_price) if s.total_price else None,
                'booking_link': s.booking_link,
                'has_confirmation_code': bool(s._encrypted_confirmation_code),
            })
        return Response(results, status=status.HTTP_200_OK)

    def post(self, request, trip_id):
        trip = get_object_or_404(Trip, id=trip_id)
        data = request.data
        stay = Stay(
            trip=trip,
            title=data.get('title'),
            status=data.get('status', 'IDEA'),
            description=data.get('description'),
            address=data.get('address'),
            check_in=data.get('check_in'),
            check_out=data.get('check_out'),
            total_price=data.get('total_price'),
            booking_link=data.get('booking_link'),
        )
        if 'confirmation_code' in data:
            stay.confirmation_code = data['confirmation_code']
        stay.save()
        return Response({"id": str(stay.id), "title": stay.title}, status=status.HTTP_201_CREATED)
