
import logging
from .file_system_cache import FileSystemCache

logger = logging.getLogger(__name__)  # Same name as calling module
logger.addHandler(logging.NullHandler())  # No output unless configured by calling program


def paginated_iterator(knex, initial_url, error_handler=None):
    cache = FileSystemCache()
    result = cache.get_cached_blob(initial_url)
    if not result:
        try:
            result = knex.get(initial_url)
        except Exception as e:
            logger.debug(f'Error fetching blob:\n\t{initial_url}\n\t{e}')
            if error_handler:
                error_handler(e)
            else:
                raise
        cache.cache_blob(initial_url, result)
    for blob in result['results']:
        yield blob
    next_page = result.get('next', None)
    if next_page:
        for blob in paginated_iterator(knex, next_page):
            yield blob
