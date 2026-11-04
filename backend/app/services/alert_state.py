from threading import Lock

sms_alerted_zones = set()
sms_lock = Lock()


def claim_sms_alert(zone_id):
    zone_id = str(zone_id)

    with sms_lock:
        if zone_id in sms_alerted_zones:
            return False

        sms_alerted_zones.add(zone_id)
        return True


def release_sms_alert(zone_id):
    with sms_lock:
        sms_alerted_zones.discard(str(zone_id))


def clear_sms_alert(zone_id):
    with sms_lock:
        sms_alerted_zones.discard(str(zone_id))