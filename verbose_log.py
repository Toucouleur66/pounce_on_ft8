from logger import get_logger

log = get_logger(__name__)

log.debug(f"""After Check Wkb4 and Marathon:\n
    Callsign: {callsign}
    Callsign Info: {callsign_info}
    Directed: {directed}
    Wanted: {wanted}
    Excluded: {excluded}
    Monitored: {monitored}
    Monitored CQ Zone: {monitored_cq_zone}
    Worked B4: {worked_b4}  
    Marathon: {marathon}
    Entity Code: {entity_code}              
    self.mycall: {self.my_call}
    self.targeted_call: {self.targeted_call}
    self.worked_callsigns: {self.worked_callsigns}
    self.wanted_callsigns_per_entity: {self.wanted_callsigns_per_entity}
    self.adif_data: {self.adif_data}
    self.marathon_preference: {self.marathon_preference}
    self.enable_marathon: {self.enable_marathon}
""")
