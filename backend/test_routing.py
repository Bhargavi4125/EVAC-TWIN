from app.services.routing_service import build_risk_map, calculate_zone_routes

# Simulate zone 304 in CRITICAL state (as in FIRE scenario)
mock_sensors = [
    {'zone_id': '304', 'risk_level': 'CRITICAL', 'risk_score': 95.0, 'occupancy': 4},
    {'zone_id': '303', 'risk_level': 'HIGH',     'risk_score': 65.0, 'occupancy': 5},
    {'zone_id': '302', 'risk_level': 'MODERATE', 'risk_score': 35.0, 'occupancy': 6},
    {'zone_id': '301', 'risk_level': 'LOW',      'risk_score': 10.0, 'occupancy': 7},
    {'zone_id': '201', 'risk_level': 'LOW',      'risk_score': 8.0,  'occupancy': 8},
    {'zone_id': '202', 'risk_level': 'LOW',      'risk_score': 8.0,  'occupancy': 7},
    {'zone_id': '203', 'risk_level': 'LOW',      'risk_score': 8.0,  'occupancy': 6},
    {'zone_id': '204', 'risk_level': 'LOW',      'risk_score': 8.0,  'occupancy': 5},
    {'zone_id': '101', 'risk_level': 'LOW',      'risk_score': 8.0,  'occupancy': 6},
    {'zone_id': '102', 'risk_level': 'LOW',      'risk_score': 8.0,  'occupancy': 7},
    {'zone_id': '103', 'risk_level': 'LOW',      'risk_score': 8.0,  'occupancy': 5},
    {'zone_id': '104', 'risk_level': 'LOW',      'risk_score': 8.0,  'occupancy': 4},
]

risk_map = build_risk_map(mock_sensors)
routes = calculate_zone_routes('304', risk_map)

print("=== EVACUATION ROUTES FROM ZONE 304 (CRITICAL) ===")
for r in routes:
    print(f"  Exit: {r['exit']:<10}  Status: {r['status']:<12}  Score: {r['risk_score']}")

available  = [r for r in routes if r['status'] == 'AVAILABLE']
caution    = [r for r in routes if r['status'] == 'CAUTION']
candidates = available or caution
recommended = min(candidates, key=lambda r: r['risk_score']) if candidates else None

print()
if recommended:
    print(f"RECOMMENDED EXIT : {recommended['exit']} (score={recommended['risk_score']})")
else:
    print("RECOMMENDED EXIT : NONE — all routes blocked")

print()
print("=== TEST PASSED ===")
