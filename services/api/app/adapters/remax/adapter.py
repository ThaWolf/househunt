from app.adapters.common import fetch_with_fixtures
from app.adapters.types import AdapterResult
from app.schemas.common import PortalId
from app.schemas.property import SearchFilters


class RemaxAdapter:
    portal = PortalId.remax
    analysis_status = "needs_probe"

    async def fetch(self, filters: SearchFilters) -> AdapterResult:
        return await fetch_with_fixtures(self.portal, filters, analysis_status=self.analysis_status)
