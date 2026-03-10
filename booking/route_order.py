"""
Shared helpers for route place order (forward or reverse).
Used by trip, vehicle schedule, and ticket booking logic.
"""


def get_route_place_order(route, reverse=False):
    """
    Return dict place_id -> order_index for traversal order.
    0 = first place (start or end when reversed), 1..n = stops, n+1 = last.
    Forward: start_point -> stop_points by order -> end_point.
    Reverse: end_point -> stop_points in reverse order -> start_point.
    """
    if not route:
        return {}
    order_map = {}
    stops = list(route.stop_points.all().order_by('order'))
    if reverse:
        order_map[route.end_point_id] = 0
        for i, sp in enumerate(reversed(stops)):
            order_map[sp.place_id] = i + 1
        order_map[route.start_point_id] = len(stops) + 1
    else:
        order_map[route.start_point_id] = 0
        for i, sp in enumerate(stops):
            order_map[sp.place_id] = i + 1
        order_map[route.end_point_id] = len(stops) + 1
    return order_map


def get_route_ordered_points(route, reverse=False):
    """
    Return list of (kind, place, route_stop_point_or_None) in traversal order.
    kind is 'start', 'stop', or 'end'. route_stop_point is None for start/end.
    """
    if not route:
        return []
    points = []
    stops = list(route.stop_points.all().select_related('place').order_by('order'))
    if reverse:
        points.append(('start', route.end_point, None))
        for rsp in reversed(stops):
            points.append(('stop', rsp.place, rsp))
        points.append(('end', route.start_point, None))
    else:
        points.append(('start', route.start_point, None))
        for rsp in stops:
            points.append(('stop', rsp.place, rsp))
        points.append(('end', route.end_point, None))
    return points
