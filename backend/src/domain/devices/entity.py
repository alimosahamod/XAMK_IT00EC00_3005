from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class Device:
    
    #Fachliches Device-Objekt, das in der Domain verwendet wird

    id: UUID | None
    device_type: str
    role: str
    device_family: str
    display_name: str 
    default_config: dict
    # Phase 8: gespeicherter Zustand aus actuator_states, bei Sensoren None.
    state: str | None = None
    # None = nicht zugewiesen; dann bleiben die ids auch im Event None.
    location_id: UUID | None = None
    zone_id: UUID | None = None
    tracking_enabled: bool = True
    #created_at: str  #Zeitstempel