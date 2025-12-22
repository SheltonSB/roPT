# @Shelton Bumhe
# Assignment 3: Edge-to-Backend Communication
# This file handles all the data objects for our safety system.
# It makes sure the JSON we send back and forth actually makes sense.

class SafetyEventIn:
    def __init__(self, event_type, ts_ms, actor_id, zone_id, payload=None):
        self.event_type = event_type # e.g., "person_entered"
        self.ts_ms = ts_ms           # timestamp in milliseconds
        self.actor_id = actor_id
        self.zone_id = zone_id
        
        if payload is None:
            self.payload = {}
        else:
            self.payload = payload

class SafetyEventOut(SafetyEventIn):
    def __init__(self, event_type, ts_ms, actor_id, zone_id, received_ms, payload=None):
        super().__init__(event_type, ts_ms, actor_id, zone_id, payload)
        self.received_ms = received_ms
class ZoneDef:
    def __init__(self, zone_id, polygon):
        self.zone_id = zone_id
        self.polygon = polygon 

class ZonesPayload:
    def __init__(self, zones_list):
        self.zones = zones_list 

class ActorSnapshot:
    def __init__(self, last_seen_ms, zones_dict):
        self.last_seen_ms = last_seen_ms
        self.zones = zones_dict
class StateSnapshot:
    def __init__(self, ts_ms, actors_dict, recent_events_list):
        self.ts_ms = ts_ms
        self.actors = actors_dict           
        self.recent_events = recent_events_list 

# TODO: Add a method to convert these to dictionaries for JSON export