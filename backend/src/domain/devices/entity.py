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
    #created_at: str  #Zeitstempel