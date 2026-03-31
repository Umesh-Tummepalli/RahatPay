import datetime

class EligibilityGates:
    
    @staticmethod
    def check_gate1_zone_match(disruption_zone: str, rider_zones: list[str]) -> tuple[bool, str]:
        """
        Gate 1 — Zone match: 
        Does the disruption zone appear in the rider's three registered zones?
        """
        if disruption_zone in rider_zones:
            return True, ""
        return False, f"Disruption in zone {disruption_zone} is not in your registered zones."

    @staticmethod
    def check_gate2_shift_window(event_start_time: datetime.datetime) -> tuple[bool, str]:
        """
        Gate 2 — Shift window overlap: 
        Does the disruption time fall within the rider's working hours?
        Hardcoded typical shift windows: daytime riders work 10 AM to 3 PM and 6 PM to 10 PM.
        """
        hour = event_start_time.hour
        
        # 10 AM (10) to 3 PM (15). 6 PM (18) to 10 PM (22)
        if (10 <= hour < 15) or (18 <= hour < 22):
            return True, ""
            
        time_str = event_start_time.strftime("%I:%M %p")
        return False, f"Disruption at {time_str} is outside your established shift window (10 AM-3 PM, 6 PM-10 PM)."

    @staticmethod
    def check_gate3_platform_inactivity() -> tuple[bool, str]:
        """
        Gate 3 — Platform inactivity: 
        Is the rider confirmed offline (not earning) on their delivery platform?
        Mocked to return True for Phase 2.
        """
        # In production: Check Swiggy/Zomato API for rider earnings/activity within the window.
        return True, ""

    @staticmethod
    def check_gate4_sensor_fusion() -> tuple[bool, str]:
        """
        Gate 4 — Sensor fusion: 
        Does sensor data confirm the rider's location?
        Mocked to return True for Phase 2.
        """
        # In production: Pull GPS × Cell Tower × IMU × Wi-Fi to confirm location inside the disruption boundary.
        return True, ""

    @classmethod
    def run_all_gates(cls, disruption_zone: str, event_time: datetime.datetime, rider_zones: list[str]) -> tuple[bool, dict, str]:
        """
        Runs all gates sequentially. Returns (is_eligible, gate_results_dict, rejection_reason).
        """
        results = {
            "gate1_zone_match": False,
            "gate2_shift_overlap": False,
            "gate3_platform_inactivity": False,
            "gate4_sensor_fusion": False
        }
        
        # Gate 1
        g1_pass, reason = cls.check_gate1_zone_match(disruption_zone, rider_zones)
        results["gate1_zone_match"] = g1_pass
        if not g1_pass:
            return False, results, reason
            
        # Gate 2
        g2_pass, reason = cls.check_gate2_shift_window(event_time)
        results["gate2_shift_overlap"] = g2_pass
        if not g2_pass:
            return False, results, reason
            
        # Gate 3
        g3_pass, reason = cls.check_gate3_platform_inactivity()
        results["gate3_platform_inactivity"] = g3_pass
        if not g3_pass:
            return False, results, reason
            
        # Gate 4
        g4_pass, reason = cls.check_gate4_sensor_fusion()
        results["gate4_sensor_fusion"] = g4_pass
        if not g4_pass:
            return False, results, reason
            
        return True, results, ""
