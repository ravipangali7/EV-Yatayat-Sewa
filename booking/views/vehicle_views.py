from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from decimal import Decimal
import json
from ..models import Vehicle, VehicleSeat, VehicleImage, Route
from core.models import User


@api_view(['GET'])
def vehicle_list_get_view(request):
    """List all vehicles"""
    # Get query parameters
    search = request.query_params.get('search', '')
    vehicle_type = request.query_params.get('vehicle_type', None)
    is_active = request.query_params.get('is_active', None)
    driver_id = request.query_params.get('driver', None)
    route_id = request.query_params.get('route', None)
    
    # Build queryset
    queryset = Vehicle.objects.prefetch_related(
        'drivers', 'routes', 'seats', 'images'
    ).all()
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(vehicle_no__icontains=search) |
            Q(imei__icontains=search) |
            Q(description__icontains=search)
        )
    
    if vehicle_type:
        queryset = queryset.filter(vehicle_type=vehicle_type)
    
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() == 'true')
    
    if driver_id:
        queryset = queryset.filter(drivers__id=driver_id)
    
    if route_id:
        queryset = queryset.filter(routes__id=route_id)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    per_page = int(request.query_params.get('per_page', 10))
    start = (page - 1) * per_page
    end = start + per_page
    
    total = queryset.count()
    vehicles = queryset[start:end]
    
    # Return data without serializer
    results = []
    for vehicle in vehicles:
        # Build driver_details
        driver_details = []
        for driver in vehicle.drivers.all():
            driver_details.append({
                'id': str(driver.id),
                'username': driver.username,
                'phone': driver.phone,
                'email': driver.email or '',
                'name': driver.name or '',
                'is_driver': driver.is_driver,
                'is_active': driver.is_active,
            })
        
        # Build route_details
        route_details = []
        for route in vehicle.routes.all():
            route_details.append({
                'id': str(route.id),
                'name': route.name,
                'is_bidirectional': route.is_bidirectional,
                'start_point_details': {
                    'id': str(route.start_point.id),
                    'name': route.start_point.name,
                    'code': route.start_point.code,
                    'latitude': str(route.start_point.latitude),
                    'longitude': str(route.start_point.longitude),
                },
                'end_point_details': {
                    'id': str(route.end_point.id),
                    'name': route.end_point.name,
                    'code': route.end_point.code,
                    'latitude': str(route.end_point.latitude),
                    'longitude': str(route.end_point.longitude),
                },
            })
        
        # Build seats
        seats = []
        for seat in vehicle.seats.all():
            seats.append({
                'id': str(seat.id),
                'vehicle': str(seat.vehicle.id),
                'side': seat.side,
                'number': seat.number,
                'status': seat.status,
                'created_at': seat.created_at.isoformat(),
                'updated_at': seat.updated_at.isoformat(),
            })
        
        # Build images
        images = []
        for img in vehicle.images.all():
            images.append({
                'id': str(img.id),
                'vehicle': str(img.vehicle.id),
                'title': img.title or '',
                'description': img.description or '',
                'image': img.image.url if img.image else None,
                'created_at': img.created_at.isoformat(),
                'updated_at': img.updated_at.isoformat(),
            })
        
        # Build active_driver_details
        active_driver_details = None
        if vehicle.active_driver:
            active_driver_details = {
                'id': str(vehicle.active_driver.id),
                'username': vehicle.active_driver.username,
                'phone': vehicle.active_driver.phone,
                'email': vehicle.active_driver.email or '',
                'name': vehicle.active_driver.name or '',
                'is_driver': vehicle.active_driver.is_driver,
                'is_active': vehicle.active_driver.is_active,
            }
        
        # Build active_route_details
        active_route_details = None
        if vehicle.active_route:
            active_route_details = {
                'id': str(vehicle.active_route.id),
                'name': vehicle.active_route.name,
                'is_bidirectional': vehicle.active_route.is_bidirectional,
                'start_point_details': {
                    'id': str(vehicle.active_route.start_point.id),
                    'name': vehicle.active_route.start_point.name,
                    'code': vehicle.active_route.start_point.code,
                    'latitude': str(vehicle.active_route.start_point.latitude),
                    'longitude': str(vehicle.active_route.start_point.longitude),
                },
                'end_point_details': {
                    'id': str(vehicle.active_route.end_point.id),
                    'name': vehicle.active_route.end_point.name,
                    'code': vehicle.active_route.end_point.code,
                    'latitude': str(vehicle.active_route.end_point.latitude),
                    'longitude': str(vehicle.active_route.end_point.longitude),
                },
            }
        
        results.append({
            'id': str(vehicle.id),
            'imei': vehicle.imei or '',
            'name': vehicle.name,
            'vehicle_no': vehicle.vehicle_no,
            'vehicle_type': vehicle.vehicle_type,
            'odometer': str(vehicle.odometer),
            'overspeed_limit': vehicle.overspeed_limit,
            'description': vehicle.description or '',
            'featured_image': vehicle.featured_image.url if vehicle.featured_image else None,
            'drivers': [str(d.id) for d in vehicle.drivers.all()],
            'driver_details': driver_details,
            'active_driver': str(vehicle.active_driver.id) if vehicle.active_driver else None,
            'active_driver_details': active_driver_details,
            'routes': [str(r.id) for r in vehicle.routes.all()],
            'route_details': route_details,
            'active_route': str(vehicle.active_route.id) if vehicle.active_route else None,
            'active_route_details': active_route_details,
            'is_active': vehicle.is_active,
            'seats': seats,
            'images': images,
            'created_at': vehicle.created_at.isoformat(),
            'updated_at': vehicle.updated_at.isoformat(),
        })
    
    return Response({
        'results': results,
        'count': total,
        'page': page,
        'per_page': per_page
    })


@api_view(['POST'])
def vehicle_list_post_view(request):
    """Create a new vehicle"""
    # Extract data from request.POST or request.data
    imei = request.POST.get('imei') or request.data.get('imei') or None
    name = request.POST.get('name') or request.data.get('name')
    vehicle_no = request.POST.get('vehicle_no') or request.data.get('vehicle_no')
    vehicle_type = request.POST.get('vehicle_type') or request.data.get('vehicle_type')
    odometer = request.POST.get('odometer') or request.data.get('odometer', '0')
    overspeed_limit = request.POST.get('overspeed_limit') or request.data.get('overspeed_limit', '80')
    description = request.POST.get('description') or request.data.get('description') or None
    active_driver_id = request.POST.get('active_driver') or request.data.get('active_driver') or None
    active_route_id = request.POST.get('active_route') or request.data.get('active_route') or None
    is_active = request.POST.get('is_active') or request.data.get('is_active', 'true')
    
    # Handle nested data
    seats_data = request.POST.get('seats') or request.data.get('seats', [])
    images_data = request.POST.get('images') or request.data.get('images', [])
    drivers_data = request.POST.get('drivers') or request.data.get('drivers', [])
    routes_data = request.POST.get('routes') or request.data.get('routes', [])
    
    # Parse JSON strings if they come from FormData
    if isinstance(seats_data, str):
        try:
            seats_data = json.loads(seats_data)
        except:
            seats_data = []
    if isinstance(images_data, str):
        try:
            images_data = json.loads(images_data)
        except:
            images_data = []
    if isinstance(drivers_data, str):
        try:
            drivers_data = json.loads(drivers_data) if drivers_data.startswith('[') else [drivers_data]
        except:
            drivers_data = []
    if isinstance(routes_data, str):
        try:
            routes_data = json.loads(routes_data) if routes_data.startswith('[') else [routes_data]
        except:
            routes_data = []
    
    # Validate required fields
    if not name:
        return Response({'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not vehicle_no:
        return Response({'error': 'Vehicle number is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not vehicle_type:
        return Response({'error': 'Vehicle type is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if vehicle_no already exists
    if Vehicle.objects.filter(vehicle_no=vehicle_no).exists():
        return Response({'error': 'Vehicle with this number already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Convert values
    try:
        odometer = Decimal(str(odometer))
        overspeed_limit = int(overspeed_limit)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid odometer or overspeed_limit values'}, status=status.HTTP_400_BAD_REQUEST)
    
    is_active = is_active.lower() == 'true' if isinstance(is_active, str) else bool(is_active)
    
    # Handle file uploads
    featured_image = request.FILES.get('featured_image')
    
    # Create vehicle directly without serializer
    vehicle = Vehicle.objects.create(
        imei=imei,
        name=name,
        vehicle_no=vehicle_no,
        vehicle_type=vehicle_type,
        odometer=odometer,
        overspeed_limit=overspeed_limit,
        description=description,
        featured_image=featured_image,
        active_driver_id=active_driver_id if active_driver_id else None,
        active_route_id=active_route_id if active_route_id else None,
        is_active=is_active,
    )
    
    # Handle many-to-many relationships
    if drivers_data:
        vehicle.drivers.set(drivers_data)
    if routes_data:
        vehicle.routes.set(routes_data)
    
    # Create seats
    if seats_data:
        for seat_data in seats_data:
            VehicleSeat.objects.create(
                vehicle=vehicle,
                side=seat_data.get('side'),
                number=seat_data.get('number'),
                status=seat_data.get('status', 'available')
            )
    
    # Create images - handle file uploads
    if images_data:
        # Ensure images_data is a list
        if not isinstance(images_data, list):
            images_data = [images_data] if images_data else []
        
        for idx, image_data in enumerate(images_data):
            # Ensure image_data is a dict
            if not isinstance(image_data, dict):
                continue  # Skip invalid entries
            
            # Check if image is in request.FILES (for new uploads)
            image_file = None
            # Check if image is in request.FILES (for new uploads)
            image_file = None
            if f'images[{idx}].image' in request.FILES:
                image_file = request.FILES[f'images[{idx}].image']
            elif hasattr(request, '_request') and f'images[{idx}].image' in request._request.FILES:
                image_file = request._request.FILES[f'images[{idx}].image']
            elif 'image' in image_data and hasattr(image_data['image'], 'read'):
                image_file = image_data['image']
            
            VehicleImage.objects.create(
                vehicle=vehicle,
                title=image_data.get('title', ''),
                description=image_data.get('description', ''),
                image=image_file if image_file else None
            )
    
    # Reload vehicle with all relationships
    vehicle.refresh_from_db()
    vehicle = Vehicle.objects.prefetch_related('drivers', 'routes', 'seats', 'images').select_related('active_driver', 'active_route').get(pk=vehicle.id)
    
    # Build response data (similar to GET)
    driver_details = []
    for driver in vehicle.drivers.all():
        driver_details.append({
            'id': str(driver.id),
            'username': driver.username,
            'phone': driver.phone,
            'email': driver.email or '',
            'name': driver.name or '',
            'is_driver': driver.is_driver,
            'is_active': driver.is_active,
        })
    
    route_details = []
    for route in vehicle.routes.all():
        route_details.append({
            'id': str(route.id),
            'name': route.name,
            'is_bidirectional': route.is_bidirectional,
            'start_point_details': {
                'id': str(route.start_point.id),
                'name': route.start_point.name,
                'code': route.start_point.code,
                'latitude': str(route.start_point.latitude),
                'longitude': str(route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(route.end_point.id),
                'name': route.end_point.name,
                'code': route.end_point.code,
                'latitude': str(route.end_point.latitude),
                'longitude': str(route.end_point.longitude),
            },
        })
    
    seats = []
    for seat in vehicle.seats.all():
        seats.append({
            'id': str(seat.id),
            'vehicle': str(seat.vehicle.id),
            'side': seat.side,
            'number': seat.number,
            'status': seat.status,
            'created_at': seat.created_at.isoformat(),
            'updated_at': seat.updated_at.isoformat(),
        })
    
    images = []
    for img in vehicle.images.all():
        images.append({
            'id': str(img.id),
            'vehicle': str(img.vehicle.id),
            'title': img.title or '',
            'description': img.description or '',
            'image': img.image.url if img.image else None,
            'created_at': img.created_at.isoformat(),
            'updated_at': img.updated_at.isoformat(),
        })
    
    active_driver_details = None
    if vehicle.active_driver:
        active_driver_details = {
            'id': str(vehicle.active_driver.id),
            'username': vehicle.active_driver.username,
            'phone': vehicle.active_driver.phone,
            'email': vehicle.active_driver.email or '',
            'name': vehicle.active_driver.name or '',
            'is_driver': vehicle.active_driver.is_driver,
            'is_active': vehicle.active_driver.is_active,
        }
    
    active_route_details = None
    if vehicle.active_route:
        active_route_details = {
            'id': str(vehicle.active_route.id),
            'name': vehicle.active_route.name,
            'is_bidirectional': vehicle.active_route.is_bidirectional,
            'start_point_details': {
                'id': str(vehicle.active_route.start_point.id),
                'name': vehicle.active_route.start_point.name,
                'code': vehicle.active_route.start_point.code,
                'latitude': str(vehicle.active_route.start_point.latitude),
                'longitude': str(vehicle.active_route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(vehicle.active_route.end_point.id),
                'name': vehicle.active_route.end_point.name,
                'code': vehicle.active_route.end_point.code,
                'latitude': str(vehicle.active_route.end_point.latitude),
                'longitude': str(vehicle.active_route.end_point.longitude),
            },
        }
    
    return Response({
        'id': str(vehicle.id),
        'imei': vehicle.imei or '',
        'name': vehicle.name,
        'vehicle_no': vehicle.vehicle_no,
        'vehicle_type': vehicle.vehicle_type,
        'odometer': str(vehicle.odometer),
        'overspeed_limit': vehicle.overspeed_limit,
        'description': vehicle.description or '',
        'featured_image': vehicle.featured_image.url if vehicle.featured_image else None,
        'drivers': [str(d.id) for d in vehicle.drivers.all()],
        'driver_details': driver_details,
        'active_driver': str(vehicle.active_driver.id) if vehicle.active_driver else None,
        'active_driver_details': active_driver_details,
        'routes': [str(r.id) for r in vehicle.routes.all()],
        'route_details': route_details,
        'active_route': str(vehicle.active_route.id) if vehicle.active_route else None,
        'active_route_details': active_route_details,
        'is_active': vehicle.is_active,
        'seats': seats,
        'images': images,
        'created_at': vehicle.created_at.isoformat(),
        'updated_at': vehicle.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def vehicle_detail_get_view(request, pk):
    """Retrieve a single vehicle"""
    try:
        vehicle = Vehicle.objects.prefetch_related(
            'drivers', 'routes', 'seats', 'images'
        ).select_related('active_driver', 'active_route').get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Build response data (same as list view)
    driver_details = []
    for driver in vehicle.drivers.all():
        driver_details.append({
            'id': str(driver.id),
            'username': driver.username,
            'phone': driver.phone,
            'email': driver.email or '',
            'name': driver.name or '',
            'is_driver': driver.is_driver,
            'is_active': driver.is_active,
        })
    
    route_details = []
    for route in vehicle.routes.all():
        route_details.append({
            'id': str(route.id),
            'name': route.name,
            'is_bidirectional': route.is_bidirectional,
            'start_point_details': {
                'id': str(route.start_point.id),
                'name': route.start_point.name,
                'code': route.start_point.code,
                'latitude': str(route.start_point.latitude),
                'longitude': str(route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(route.end_point.id),
                'name': route.end_point.name,
                'code': route.end_point.code,
                'latitude': str(route.end_point.latitude),
                'longitude': str(route.end_point.longitude),
            },
        })
    
    seats = []
    for seat in vehicle.seats.all():
        seats.append({
            'id': str(seat.id),
            'vehicle': str(seat.vehicle.id),
            'side': seat.side,
            'number': seat.number,
            'status': seat.status,
            'created_at': seat.created_at.isoformat(),
            'updated_at': seat.updated_at.isoformat(),
        })
    
    images = []
    for img in vehicle.images.all():
        images.append({
            'id': str(img.id),
            'vehicle': str(img.vehicle.id),
            'title': img.title or '',
            'description': img.description or '',
            'image': img.image.url if img.image else None,
            'created_at': img.created_at.isoformat(),
            'updated_at': img.updated_at.isoformat(),
        })
    
    active_driver_details = None
    if vehicle.active_driver:
        active_driver_details = {
            'id': str(vehicle.active_driver.id),
            'username': vehicle.active_driver.username,
            'phone': vehicle.active_driver.phone,
            'email': vehicle.active_driver.email or '',
            'name': vehicle.active_driver.name or '',
            'is_driver': vehicle.active_driver.is_driver,
            'is_active': vehicle.active_driver.is_active,
        }
    
    active_route_details = None
    if vehicle.active_route:
        active_route_details = {
            'id': str(vehicle.active_route.id),
            'name': vehicle.active_route.name,
            'is_bidirectional': vehicle.active_route.is_bidirectional,
            'start_point_details': {
                'id': str(vehicle.active_route.start_point.id),
                'name': vehicle.active_route.start_point.name,
                'code': vehicle.active_route.start_point.code,
                'latitude': str(vehicle.active_route.start_point.latitude),
                'longitude': str(vehicle.active_route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(vehicle.active_route.end_point.id),
                'name': vehicle.active_route.end_point.name,
                'code': vehicle.active_route.end_point.code,
                'latitude': str(vehicle.active_route.end_point.latitude),
                'longitude': str(vehicle.active_route.end_point.longitude),
            },
        }
    
    return Response({
        'id': str(vehicle.id),
        'imei': vehicle.imei or '',
        'name': vehicle.name,
        'vehicle_no': vehicle.vehicle_no,
        'vehicle_type': vehicle.vehicle_type,
        'odometer': str(vehicle.odometer),
        'overspeed_limit': vehicle.overspeed_limit,
        'description': vehicle.description or '',
        'featured_image': vehicle.featured_image.url if vehicle.featured_image else None,
        'drivers': [str(d.id) for d in vehicle.drivers.all()],
        'driver_details': driver_details,
        'active_driver': str(vehicle.active_driver.id) if vehicle.active_driver else None,
        'active_driver_details': active_driver_details,
        'routes': [str(r.id) for r in vehicle.routes.all()],
        'route_details': route_details,
        'active_route': str(vehicle.active_route.id) if vehicle.active_route else None,
        'active_route_details': active_route_details,
        'is_active': vehicle.is_active,
        'seats': seats,
        'images': images,
        'created_at': vehicle.created_at.isoformat(),
        'updated_at': vehicle.updated_at.isoformat(),
    })


@api_view(['POST'])
def vehicle_detail_post_view(request, pk):
    """Update/edit a vehicle"""
    try:
        vehicle = Vehicle.objects.prefetch_related('drivers', 'routes', 'seats', 'images').get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data from request.POST or request.data
    if 'name' in request.POST or 'name' in request.data:
        name = request.POST.get('name') or request.data.get('name')
        if name:
            vehicle.name = name
    
    if 'imei' in request.POST or 'imei' in request.data:
        imei = request.POST.get('imei') or request.data.get('imei')
        vehicle.imei = imei if imei else None
    
    if 'vehicle_no' in request.POST or 'vehicle_no' in request.data:
        vehicle_no = request.POST.get('vehicle_no') or request.data.get('vehicle_no')
        if vehicle_no and vehicle_no != vehicle.vehicle_no:
            # Check if new vehicle_no already exists
            if Vehicle.objects.filter(vehicle_no=vehicle_no).exclude(pk=pk).exists():
                return Response({'error': 'Vehicle with this number already exists'}, status=status.HTTP_400_BAD_REQUEST)
            vehicle.vehicle_no = vehicle_no
    
    if 'vehicle_type' in request.POST or 'vehicle_type' in request.data:
        vehicle_type = request.POST.get('vehicle_type') or request.data.get('vehicle_type')
        if vehicle_type:
            vehicle.vehicle_type = vehicle_type
    
    if 'odometer' in request.POST or 'odometer' in request.data:
        odometer = request.POST.get('odometer') or request.data.get('odometer')
        try:
            vehicle.odometer = Decimal(str(odometer))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid odometer value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'overspeed_limit' in request.POST or 'overspeed_limit' in request.data:
        overspeed_limit = request.POST.get('overspeed_limit') or request.data.get('overspeed_limit')
        try:
            vehicle.overspeed_limit = int(overspeed_limit)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid overspeed_limit value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'description' in request.POST or 'description' in request.data:
        description = request.POST.get('description') or request.data.get('description')
        vehicle.description = description if description else None
    
    if 'is_active' in request.POST or 'is_active' in request.data:
        is_active = request.POST.get('is_active') or request.data.get('is_active')
        vehicle.is_active = is_active.lower() == 'true' if isinstance(is_active, str) else bool(is_active)
    
    if 'active_driver' in request.POST or 'active_driver' in request.data:
        active_driver_id = request.POST.get('active_driver') or request.data.get('active_driver')
        if active_driver_id:
            try:
                vehicle.active_driver = User.objects.get(pk=active_driver_id)
            except User.DoesNotExist:
                return Response({'error': 'Active driver not found'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            vehicle.active_driver = None
    
    if 'active_route' in request.POST or 'active_route' in request.data:
        active_route_id = request.POST.get('active_route') or request.data.get('active_route')
        if active_route_id:
            try:
                vehicle.active_route = Route.objects.get(pk=active_route_id)
            except Route.DoesNotExist:
                return Response({'error': 'Active route not found'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            vehicle.active_route = None
    
    # Handle file uploads - save immediately to ensure database field is updated
    if 'featured_image' in request.FILES:
        vehicle.featured_image = request.FILES['featured_image']
        vehicle.save(update_fields=['featured_image'])  # Save immediately to database
    
    # Handle nested data
    seats_data = request.POST.get('seats') or request.data.get('seats', None)
    images_data = request.POST.get('images') or request.data.get('images', None)
    drivers_data = request.POST.get('drivers') or request.data.get('drivers', None)
    routes_data = request.POST.get('routes') or request.data.get('routes', None)
    
    # Parse JSON strings if they come from FormData
    if seats_data is not None:
        if isinstance(seats_data, str):
            try:
                seats_data = json.loads(seats_data)
            except:
                seats_data = None
        if seats_data is not None:
            # Delete existing seats
            VehicleSeat.objects.filter(vehicle=vehicle).delete()
            # Create new seats
            for seat_data in seats_data:
                VehicleSeat.objects.create(
                    vehicle=vehicle,
                    side=seat_data.get('side'),
                    number=seat_data.get('number'),
                    status=seat_data.get('status', 'available')
                )
    
    if images_data is not None:
        if isinstance(images_data, str):
            try:
                images_data = json.loads(images_data)
            except:
                images_data = None
        if images_data is not None:
            # Ensure images_data is a list
            if not isinstance(images_data, list):
                images_data = [images_data] if images_data else []
            
            # Delete existing images
            VehicleImage.objects.filter(vehicle=vehicle).delete()
            # Create new images - handle file uploads
            for idx, image_data in enumerate(images_data):
                # Ensure image_data is a dict
                if not isinstance(image_data, dict):
                    continue  # Skip invalid entries
                
                # Check if image is in request.FILES (for new uploads)
                image_file = None
                if f'images[{idx}].image' in request.FILES:
                    image_file = request.FILES[f'images[{idx}].image']
                elif hasattr(request, '_request') and f'images[{idx}].image' in request._request.FILES:
                    image_file = request._request.FILES[f'images[{idx}].image']
                elif 'image' in image_data and hasattr(image_data['image'], 'read'):
                    image_file = image_data['image']
                
                VehicleImage.objects.create(
                    vehicle=vehicle,
                    title=image_data.get('title', ''),
                    description=image_data.get('description', ''),
                    image=image_file if image_file else None
                )
    
    if drivers_data is not None:
        if isinstance(drivers_data, str):
            try:
                drivers_data = json.loads(drivers_data) if drivers_data.startswith('[') else [drivers_data]
            except:
                drivers_data = []
        vehicle.drivers.set(drivers_data)
    
    if routes_data is not None:
        if isinstance(routes_data, str):
            try:
                routes_data = json.loads(routes_data) if routes_data.startswith('[') else [routes_data]
            except:
                routes_data = []
        vehicle.routes.set(routes_data)
    
    vehicle.save()
    
    # Reload vehicle with all relationships
    vehicle.refresh_from_db()
    vehicle = Vehicle.objects.prefetch_related('drivers', 'routes', 'seats', 'images').select_related('active_driver', 'active_route').get(pk=vehicle.id)
    
    # Build response data (same as GET)
    driver_details = []
    for driver in vehicle.drivers.all():
        driver_details.append({
            'id': str(driver.id),
            'username': driver.username,
            'phone': driver.phone,
            'email': driver.email or '',
            'name': driver.name or '',
            'is_driver': driver.is_driver,
            'is_active': driver.is_active,
        })
    
    route_details = []
    for route in vehicle.routes.all():
        route_details.append({
            'id': str(route.id),
            'name': route.name,
            'is_bidirectional': route.is_bidirectional,
            'start_point_details': {
                'id': str(route.start_point.id),
                'name': route.start_point.name,
                'code': route.start_point.code,
                'latitude': str(route.start_point.latitude),
                'longitude': str(route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(route.end_point.id),
                'name': route.end_point.name,
                'code': route.end_point.code,
                'latitude': str(route.end_point.latitude),
                'longitude': str(route.end_point.longitude),
            },
        })
    
    seats = []
    for seat in vehicle.seats.all():
        seats.append({
            'id': str(seat.id),
            'vehicle': str(seat.vehicle.id),
            'side': seat.side,
            'number': seat.number,
            'status': seat.status,
            'created_at': seat.created_at.isoformat(),
            'updated_at': seat.updated_at.isoformat(),
        })
    
    images = []
    for img in vehicle.images.all():
        images.append({
            'id': str(img.id),
            'vehicle': str(img.vehicle.id),
            'title': img.title or '',
            'description': img.description or '',
            'image': img.image.url if img.image else None,
            'created_at': img.created_at.isoformat(),
            'updated_at': img.updated_at.isoformat(),
        })
    
    active_driver_details = None
    if vehicle.active_driver:
        active_driver_details = {
            'id': str(vehicle.active_driver.id),
            'username': vehicle.active_driver.username,
            'phone': vehicle.active_driver.phone,
            'email': vehicle.active_driver.email or '',
            'name': vehicle.active_driver.name or '',
            'is_driver': vehicle.active_driver.is_driver,
            'is_active': vehicle.active_driver.is_active,
        }
    
    active_route_details = None
    if vehicle.active_route:
        active_route_details = {
            'id': str(vehicle.active_route.id),
            'name': vehicle.active_route.name,
            'is_bidirectional': vehicle.active_route.is_bidirectional,
            'start_point_details': {
                'id': str(vehicle.active_route.start_point.id),
                'name': vehicle.active_route.start_point.name,
                'code': vehicle.active_route.start_point.code,
                'latitude': str(vehicle.active_route.start_point.latitude),
                'longitude': str(vehicle.active_route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(vehicle.active_route.end_point.id),
                'name': vehicle.active_route.end_point.name,
                'code': vehicle.active_route.end_point.code,
                'latitude': str(vehicle.active_route.end_point.latitude),
                'longitude': str(vehicle.active_route.end_point.longitude),
            },
        }
    
    return Response({
        'id': str(vehicle.id),
        'imei': vehicle.imei or '',
        'name': vehicle.name,
        'vehicle_no': vehicle.vehicle_no,
        'vehicle_type': vehicle.vehicle_type,
        'odometer': str(vehicle.odometer),
        'overspeed_limit': vehicle.overspeed_limit,
        'description': vehicle.description or '',
        'featured_image': vehicle.featured_image.url if vehicle.featured_image else None,
        'drivers': [str(d.id) for d in vehicle.drivers.all()],
        'driver_details': driver_details,
        'active_driver': str(vehicle.active_driver.id) if vehicle.active_driver else None,
        'active_driver_details': active_driver_details,
        'routes': [str(r.id) for r in vehicle.routes.all()],
        'route_details': route_details,
        'active_route': str(vehicle.active_route.id) if vehicle.active_route else None,
        'active_route_details': active_route_details,
        'is_active': vehicle.is_active,
        'seats': seats,
        'images': images,
        'created_at': vehicle.created_at.isoformat(),
        'updated_at': vehicle.updated_at.isoformat(),
    })


@api_view(['GET'])
def vehicle_delete_get_view(request, pk):
    """Delete a vehicle"""
    try:
        vehicle = Vehicle.objects.get(pk=pk)
        vehicle.delete()
        return Response({'message': 'Vehicle deleted successfully'})
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)


# Vehicle Seat Views
@api_view(['GET'])
def vehicle_seat_list_get_view(request, vehicle_id):
    """List all seats for a vehicle"""
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
    
    seats = VehicleSeat.objects.filter(vehicle=vehicle).order_by('side', 'number')
    
    # Return data without serializer
    results = []
    for seat in seats:
        results.append({
            'id': str(seat.id),
            'vehicle': str(seat.vehicle.id),
            'side': seat.side,
            'number': seat.number,
            'status': seat.status,
            'created_at': seat.created_at.isoformat(),
            'updated_at': seat.updated_at.isoformat(),
        })
    
    return Response(results)


@api_view(['POST'])
def vehicle_seat_list_post_view(request, vehicle_id):
    """Create a new seat for a vehicle"""
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data
    side = request.POST.get('side') or request.data.get('side')
    number = request.POST.get('number') or request.data.get('number')
    status_val = request.POST.get('status') or request.data.get('status', 'available')
    
    if not side:
        return Response({'error': 'Side is required'}, status=status.HTTP_400_BAD_REQUEST)
    if not number:
        return Response({'error': 'Number is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate side and status
    valid_sides = ['A', 'B', 'C']
    valid_statuses = ['available', 'booked']
    if side not in valid_sides:
        return Response({'error': f'Invalid side. Must be one of: {", ".join(valid_sides)}'}, status=status.HTTP_400_BAD_REQUEST)
    if status_val not in valid_statuses:
        return Response({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        number = int(number)
    except (ValueError, TypeError):
        return Response({'error': 'Invalid number value'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if seat already exists
    if VehicleSeat.objects.filter(vehicle=vehicle, side=side, number=number).exists():
        return Response({'error': 'Seat with this side and number already exists'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create seat directly without serializer
    seat = VehicleSeat.objects.create(
        vehicle=vehicle,
        side=side,
        number=number,
        status=status_val
    )
    
    return Response({
        'id': str(seat.id),
        'vehicle': str(seat.vehicle.id),
        'side': seat.side,
        'number': seat.number,
        'status': seat.status,
        'created_at': seat.created_at.isoformat(),
        'updated_at': seat.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def vehicle_seat_detail_get_view(request, vehicle_id, pk):
    """Retrieve a single seat"""
    try:
        seat = VehicleSeat.objects.get(pk=pk, vehicle_id=vehicle_id)
    except VehicleSeat.DoesNotExist:
        return Response({'error': 'Seat not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'id': str(seat.id),
        'vehicle': str(seat.vehicle.id),
        'side': seat.side,
        'number': seat.number,
        'status': seat.status,
        'created_at': seat.created_at.isoformat(),
        'updated_at': seat.updated_at.isoformat(),
    })


@api_view(['POST'])
def vehicle_seat_detail_post_view(request, vehicle_id, pk):
    """Update/edit a seat"""
    try:
        seat = VehicleSeat.objects.get(pk=pk, vehicle_id=vehicle_id)
    except VehicleSeat.DoesNotExist:
        return Response({'error': 'Seat not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data
    if 'side' in request.POST or 'side' in request.data:
        side = request.POST.get('side') or request.data.get('side')
        valid_sides = ['A', 'B', 'C']
        if side not in valid_sides:
            return Response({'error': f'Invalid side. Must be one of: {", ".join(valid_sides)}'}, status=status.HTTP_400_BAD_REQUEST)
        seat.side = side
    
    if 'number' in request.POST or 'number' in request.data:
        number = request.POST.get('number') or request.data.get('number')
        try:
            seat.number = int(number)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid number value'}, status=status.HTTP_400_BAD_REQUEST)
    
    if 'status' in request.POST or 'status' in request.data:
        status_val = request.POST.get('status') or request.data.get('status')
        valid_statuses = ['available', 'booked']
        if status_val not in valid_statuses:
            return Response({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)
        seat.status = status_val
    
    seat.save()
    
    return Response({
        'id': str(seat.id),
        'vehicle': str(seat.vehicle.id),
        'side': seat.side,
        'number': seat.number,
        'status': seat.status,
        'created_at': seat.created_at.isoformat(),
        'updated_at': seat.updated_at.isoformat(),
    })


@api_view(['GET'])
def vehicle_seat_delete_get_view(request, vehicle_id, pk):
    """Delete a seat"""
    try:
        seat = VehicleSeat.objects.get(pk=pk, vehicle_id=vehicle_id)
        seat.delete()
        return Response({'message': 'Seat deleted successfully'})
    except VehicleSeat.DoesNotExist:
        return Response({'error': 'Seat not found'}, status=status.HTTP_404_NOT_FOUND)


# Vehicle Image Views
@api_view(['GET'])
def vehicle_image_list_get_view(request, vehicle_id):
    """List all images for a vehicle"""
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
    
    images = VehicleImage.objects.filter(vehicle=vehicle)
    
    # Return data without serializer
    results = []
    for img in images:
        results.append({
            'id': str(img.id),
            'vehicle': str(img.vehicle.id),
            'title': img.title or '',
            'description': img.description or '',
            'image': img.image.url if img.image else None,
            'created_at': img.created_at.isoformat(),
            'updated_at': img.updated_at.isoformat(),
        })
    
    return Response(results)


@api_view(['POST'])
def vehicle_image_list_post_view(request, vehicle_id):
    """Create a new image for a vehicle"""
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data
    title = request.POST.get('title') or request.data.get('title') or ''
    description = request.POST.get('description') or request.data.get('description') or ''
    
    # Handle file uploads
    image_file = request.FILES.get('image')
    
    if not image_file:
        return Response({'error': 'Image file is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create image directly without serializer
    vehicle_image = VehicleImage.objects.create(
        vehicle=vehicle,
        title=title,
        description=description,
        image=image_file
    )
    
    return Response({
        'id': str(vehicle_image.id),
        'vehicle': str(vehicle_image.vehicle.id),
        'title': vehicle_image.title or '',
        'description': vehicle_image.description or '',
        'image': vehicle_image.image.url if vehicle_image.image else None,
        'created_at': vehicle_image.created_at.isoformat(),
        'updated_at': vehicle_image.updated_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def vehicle_image_detail_get_view(request, vehicle_id, pk):
    """Retrieve a single image"""
    try:
        image = VehicleImage.objects.get(pk=pk, vehicle_id=vehicle_id)
    except VehicleImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'id': str(image.id),
        'vehicle': str(image.vehicle.id),
        'title': image.title or '',
        'description': image.description or '',
        'image': image.image.url if image.image else None,
        'created_at': image.created_at.isoformat(),
        'updated_at': image.updated_at.isoformat(),
    })


@api_view(['POST'])
def vehicle_image_detail_post_view(request, vehicle_id, pk):
    """Update/edit an image"""
    try:
        image = VehicleImage.objects.get(pk=pk, vehicle_id=vehicle_id)
    except VehicleImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract data
    if 'title' in request.POST or 'title' in request.data:
        title = request.POST.get('title') or request.data.get('title')
        image.title = title if title else ''
    
    if 'description' in request.POST or 'description' in request.data:
        description = request.POST.get('description') or request.data.get('description')
        image.description = description if description else ''
    
    # Handle file uploads
    if 'image' in request.FILES:
        image.image = request.FILES['image']
    
    image.save()
    
    return Response({
        'id': str(image.id),
        'vehicle': str(image.vehicle.id),
        'title': image.title or '',
        'description': image.description or '',
        'image': image.image.url if image.image else None,
        'created_at': image.created_at.isoformat(),
        'updated_at': image.updated_at.isoformat(),
    })


@api_view(['GET'])
def vehicle_image_delete_get_view(request, vehicle_id, pk):
    """Delete an image"""
    try:
        image = VehicleImage.objects.get(pk=pk, vehicle_id=vehicle_id)
        image.delete()
        return Response({'message': 'Image deleted successfully'})
    except VehicleImage.DoesNotExist:
        return Response({'error': 'Image not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vehicle_connect_view(request):
    """Connect to a vehicle by setting the authenticated user as active_driver"""
    vehicle_id = request.POST.get('vehicle_id') or request.data.get('vehicle_id')
    
    if not vehicle_id:
        return Response({'error': 'vehicle_id is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        vehicle = Vehicle.objects.prefetch_related(
            'drivers', 'routes', 'seats', 'images'
        ).select_related('active_driver', 'active_route').get(pk=vehicle_id)
    except Vehicle.DoesNotExist:
        return Response({'error': 'Vehicle not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user is in vehicle.drivers
    user = request.user
    if not vehicle.drivers.filter(id=user.id).exists():
        return Response(
            {'error': 'User is not a driver of this vehicle'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Set user as active_driver
    vehicle.active_driver = user
    vehicle.save()
    
    # Refresh vehicle to get updated data
    vehicle = Vehicle.objects.prefetch_related(
        'drivers', 'routes', 'seats', 'images'
    ).select_related('active_driver', 'active_route').get(pk=vehicle_id)
    
    # Build response data (same format as vehicle_detail_get_view)
    driver_details = []
    for driver in vehicle.drivers.all():
        driver_details.append({
            'id': str(driver.id),
            'username': driver.username,
            'phone': driver.phone,
            'email': driver.email or '',
            'name': driver.name or '',
            'is_driver': driver.is_driver,
            'is_active': driver.is_active,
        })
    
    route_details = []
    for route in vehicle.routes.all():
        route_details.append({
            'id': str(route.id),
            'name': route.name,
            'is_bidirectional': route.is_bidirectional,
            'start_point_details': {
                'id': str(route.start_point.id),
                'name': route.start_point.name,
                'code': route.start_point.code,
                'latitude': str(route.start_point.latitude),
                'longitude': str(route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(route.end_point.id),
                'name': route.end_point.name,
                'code': route.end_point.code,
                'latitude': str(route.end_point.latitude),
                'longitude': str(route.end_point.longitude),
            },
        })
    
    seats = []
    for seat in vehicle.seats.all():
        seats.append({
            'id': str(seat.id),
            'vehicle': str(seat.vehicle.id),
            'side': seat.side,
            'number': seat.number,
            'status': seat.status,
            'created_at': seat.created_at.isoformat(),
            'updated_at': seat.updated_at.isoformat(),
        })
    
    images = []
    for img in vehicle.images.all():
        images.append({
            'id': str(img.id),
            'vehicle': str(img.vehicle.id),
            'title': img.title or '',
            'description': img.description or '',
            'image': img.image.url if img.image else None,
            'created_at': img.created_at.isoformat(),
            'updated_at': img.updated_at.isoformat(),
        })
    
    active_driver_details = None
    if vehicle.active_driver:
        active_driver_details = {
            'id': str(vehicle.active_driver.id),
            'username': vehicle.active_driver.username,
            'phone': vehicle.active_driver.phone,
            'email': vehicle.active_driver.email or '',
            'name': vehicle.active_driver.name or '',
            'is_driver': vehicle.active_driver.is_driver,
            'is_active': vehicle.active_driver.is_active,
        }
    
    active_route_details = None
    if vehicle.active_route:
        active_route_details = {
            'id': str(vehicle.active_route.id),
            'name': vehicle.active_route.name,
            'is_bidirectional': vehicle.active_route.is_bidirectional,
            'start_point_details': {
                'id': str(vehicle.active_route.start_point.id),
                'name': vehicle.active_route.start_point.name,
                'code': vehicle.active_route.start_point.code,
                'latitude': str(vehicle.active_route.start_point.latitude),
                'longitude': str(vehicle.active_route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(vehicle.active_route.end_point.id),
                'name': vehicle.active_route.end_point.name,
                'code': vehicle.active_route.end_point.code,
                'latitude': str(vehicle.active_route.end_point.latitude),
                'longitude': str(vehicle.active_route.end_point.longitude),
            },
        }
    
    return Response({
        'id': str(vehicle.id),
        'imei': vehicle.imei or '',
        'name': vehicle.name,
        'vehicle_no': vehicle.vehicle_no,
        'vehicle_type': vehicle.vehicle_type,
        'odometer': str(vehicle.odometer),
        'overspeed_limit': vehicle.overspeed_limit,
        'description': vehicle.description or '',
        'featured_image': vehicle.featured_image.url if vehicle.featured_image else None,
        'drivers': [str(d.id) for d in vehicle.drivers.all()],
        'driver_details': driver_details,
        'active_driver': str(vehicle.active_driver.id) if vehicle.active_driver else None,
        'active_driver_details': active_driver_details,
        'routes': [str(r.id) for r in vehicle.routes.all()],
        'route_details': route_details,
        'active_route': str(vehicle.active_route.id) if vehicle.active_route else None,
        'active_route_details': active_route_details,
        'is_active': vehicle.is_active,
        'seats': seats,
        'images': images,
        'created_at': vehicle.created_at.isoformat(),
        'updated_at': vehicle.updated_at.isoformat(),
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vehicle_my_active_get_view(request):
    """Get the vehicle where the authenticated user is the active_driver.
    If the user is active on multiple vehicles, returns the most recently updated one.
    """
    user = request.user

    vehicle = (
        Vehicle.objects.prefetch_related(
            'drivers', 'routes', 'seats', 'images'
        )
        .select_related('active_driver', 'active_route')
        .filter(active_driver=user)
        .order_by('-updated_at')
        .first()
    )
    if not vehicle:
        return Response({'vehicle': None}, status=status.HTTP_200_OK)
    
    # Build response data (same format as vehicle_detail_get_view)
    driver_details = []
    for driver in vehicle.drivers.all():
        driver_details.append({
            'id': str(driver.id),
            'username': driver.username,
            'phone': driver.phone,
            'email': driver.email or '',
            'name': driver.name or '',
            'is_driver': driver.is_driver,
            'is_active': driver.is_active,
        })
    
    route_details = []
    for route in vehicle.routes.all():
        route_details.append({
            'id': str(route.id),
            'name': route.name,
            'is_bidirectional': route.is_bidirectional,
            'start_point_details': {
                'id': str(route.start_point.id),
                'name': route.start_point.name,
                'code': route.start_point.code,
                'latitude': str(route.start_point.latitude),
                'longitude': str(route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(route.end_point.id),
                'name': route.end_point.name,
                'code': route.end_point.code,
                'latitude': str(route.end_point.latitude),
                'longitude': str(route.end_point.longitude),
            },
        })
    
    seats = []
    for seat in vehicle.seats.all():
        seats.append({
            'id': str(seat.id),
            'vehicle': str(seat.vehicle.id),
            'side': seat.side,
            'number': seat.number,
            'status': seat.status,
            'created_at': seat.created_at.isoformat(),
            'updated_at': seat.updated_at.isoformat(),
        })
    
    images = []
    for img in vehicle.images.all():
        images.append({
            'id': str(img.id),
            'vehicle': str(img.vehicle.id),
            'title': img.title or '',
            'description': img.description or '',
            'image': img.image.url if img.image else None,
            'created_at': img.created_at.isoformat(),
            'updated_at': img.updated_at.isoformat(),
        })
    
    active_driver_details = None
    if vehicle.active_driver:
        active_driver_details = {
            'id': str(vehicle.active_driver.id),
            'username': vehicle.active_driver.username,
            'phone': vehicle.active_driver.phone,
            'email': vehicle.active_driver.email or '',
            'name': vehicle.active_driver.name or '',
            'is_driver': vehicle.active_driver.is_driver,
            'is_active': vehicle.active_driver.is_active,
        }
    
    active_route_details = None
    if vehicle.active_route:
        active_route_details = {
            'id': str(vehicle.active_route.id),
            'name': vehicle.active_route.name,
            'is_bidirectional': vehicle.active_route.is_bidirectional,
            'start_point_details': {
                'id': str(vehicle.active_route.start_point.id),
                'name': vehicle.active_route.start_point.name,
                'code': vehicle.active_route.start_point.code,
                'latitude': str(vehicle.active_route.start_point.latitude),
                'longitude': str(vehicle.active_route.start_point.longitude),
            },
            'end_point_details': {
                'id': str(vehicle.active_route.end_point.id),
                'name': vehicle.active_route.end_point.name,
                'code': vehicle.active_route.end_point.code,
                'latitude': str(vehicle.active_route.end_point.latitude),
                'longitude': str(vehicle.active_route.end_point.longitude),
            },
        }
    
    return Response({
        'vehicle': {
            'id': str(vehicle.id),
            'imei': vehicle.imei or '',
            'name': vehicle.name,
            'vehicle_no': vehicle.vehicle_no,
            'vehicle_type': vehicle.vehicle_type,
            'odometer': str(vehicle.odometer),
            'overspeed_limit': vehicle.overspeed_limit,
            'description': vehicle.description or '',
            'featured_image': vehicle.featured_image.url if vehicle.featured_image else None,
            'drivers': [str(d.id) for d in vehicle.drivers.all()],
            'driver_details': driver_details,
            'active_driver': str(vehicle.active_driver.id) if vehicle.active_driver else None,
            'active_driver_details': active_driver_details,
            'routes': [str(r.id) for r in vehicle.routes.all()],
            'route_details': route_details,
            'active_route': str(vehicle.active_route.id) if vehicle.active_route else None,
            'active_route_details': active_route_details,
            'is_active': vehicle.is_active,
            'seats': seats,
            'images': images,
            'created_at': vehicle.created_at.isoformat(),
            'updated_at': vehicle.updated_at.isoformat(),
        }
    }, status=status.HTTP_200_OK)
