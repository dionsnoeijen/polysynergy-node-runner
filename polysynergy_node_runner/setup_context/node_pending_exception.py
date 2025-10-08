"""
Exception for nodes that need to pause execution and wait for external input.

This exception is used when a node cannot proceed without user interaction
or external events (e.g., OAuth authorization, manual approval, etc.).
"""


class NodePendingException(Exception):
    """
    Raised when a node needs to pause execution and wait for external input.

    This is not an error - it's a signal to the flow engine that the node
    is waiting for something (user interaction, webhook, etc.) and the flow
    should pause until the external input is received.
    """

    def __init__(self, message: str, interaction_type: str = None, data: dict = None):
        """
        Initialize NodePendingException.

        Args:
            message: Human-readable description of what the node is waiting for
            interaction_type: Type of interaction being waited for (e.g. 'oauth_authorization')
            data: Additional data about the pending state
        """
        super().__init__(message)
        self.interaction_type = interaction_type
        self.data = data or {}

    def __str__(self):
        return f"Node pending: {super().__str__()}"