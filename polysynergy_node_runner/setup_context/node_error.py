import traceback
import logging

logger = logging.getLogger(__name__)

class NodeError:
    @staticmethod
    def format(error: Exception, include_traceback: bool = False) -> dict:
        error_dict = { "error": str(error) }

        if include_traceback:
            error_dict["details"] = traceback.format_exc()
            logger.error("Exception occurred", exc_info=True)
        else:
            logger.error(str(error))

        return error_dict