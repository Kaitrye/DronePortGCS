"""
StateStore — абстракция над Redis для хранения состояния дронопорта.
"""
import redis
import datetime
from typing import Dict, Any, Optional, List

class StateStore:
    def __init__(self, redis_host: str = "redis", redis_port: int = 6379):
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2
        )
    
    # === Drone operations ===
    def save_drone(self, drone_id: str, data: Dict[str, Any]) -> bool:
        key = f"drone:{drone_id}"
        return self.redis.hset(key, mapping=data) > 0
    
    def get_drone(self, drone_id: str) -> Optional[Dict[str, Any]]:
        key = f"drone:{drone_id}"
        data = self.redis.hgetall(key)
        return data if data else None
    
    def delete_drone(self, drone_id: str) -> bool:
        key = f"drone:{drone_id}"
        return self.redis.delete(key) > 0
    
    def list_drones(self) -> List[Dict[str, Any]]:
        keys = self.redis.keys("drone:*")
        return [self.redis.hgetall(k) for k in keys if self.redis.hgetall(k)]
    
    # === Port operations ===
    def save_port(self, port_id: str, data: Dict[str, Any]) -> bool:
        key = f"port:{port_id}"
        return self.redis.hset(key, mapping=data) > 0
    
    def get_port(self, port_id: str) -> Optional[Dict[str, Any]]:
        key = f"port:{port_id}"
        return self.redis.hgetall(key)
    
    def is_port_occupied(self, port_id: str) -> bool:
        port = self.get_port(port_id)
        return bool(port and port.get("drone_id"))
    
    def get_all_ports_status(self) -> List[Dict[str, Any]]:
        keys = self.redis.keys("port:*")
        ports = []
        for k in keys:
            port_id = k.split(":")[1]
            data = self.redis.hgetall(k)
            data["port_id"] = port_id
            ports.append(data)
        return ports
    
    # === Meta operations ===
    def register_drone_meta(self, drone_id: str, specs: Dict[str, Any]) -> bool:
        key = f"drone_meta:{drone_id}"
        return self.redis.hset(key, mapping=specs) > 0
    
    def get_drone_meta(self, drone_id: str) -> Optional[Dict[str, Any]]:
        key = f"drone_meta:{drone_id}"
        data = self.redis.hgetall(key)
        return data if data else None
    
    def get_aggregated_fleet_status(self) -> Dict[str, Any]:
        """Агрегирует данные по всем дронам для отправки эксплуатанту."""
        drones = self.list_drones()
        ports = self.get_all_ports_status()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "fleet": {
                "total": len(drones),
                "charging": sum(1 for d in drones if d.get("status") == "charging"),
                "ready": sum(1 for d in drones if d.get("status") == "landed"),
                "issues": sum(1 for d in drones if d.get("issues"))
            },
            "ports": {
                "total": len(ports),
                "occupied": sum(1 for p in ports if p.get("drone_id")),
                "maintenance": sum(1 for p in ports if p.get("status") == "maintenance")
            },
            "alerts": [
                {"drone_id": d["drone_id"], "issue": d["issues"]} 
                for d in drones if d.get("issues")
            ]
        }