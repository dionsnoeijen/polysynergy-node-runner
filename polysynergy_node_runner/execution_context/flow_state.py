from enum import Enum

class FlowState(Enum):
    ENABLED = "enabled"
    FLOW_IN = "flowIn"
    FLOW_STOP = "flowStop"
    PENDING = "pending"
