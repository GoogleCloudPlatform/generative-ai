import logging

from backend.app.shared_state import index_manager, prompts
from shared_state import IndexManager, Prompts

logger = logging.getLogger(__name__)


def get_index_manager() -> IndexManager:
    logger.info(index_manager.base_index.docstore)
    logger.info(index_manager.firestore_db_name)
    logger.info(index_manager.firestore_namespace)
    return index_manager


def get_prompts() -> Prompts:
    return prompts
