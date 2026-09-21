"""Route implementation aggregator for CV text endpoints."""

from .routes_common import router
from .budget import get_llm_runtime_state

# Import endpoints for router registration.
from . import routes_async as _routes_async  # noqa: F401
from . import routes_runtime as _routes_runtime  # noqa: F401
from . import routes_sync as _routes_sync  # noqa: F401
from . import routes_recommend as _routes_recommend  # noqa: F401
from . import routes_improve as _routes_improve  # noqa: F401
from . import routes_document as _routes_document  # noqa: F401

__all__ = ["router", "get_llm_runtime_state"]
