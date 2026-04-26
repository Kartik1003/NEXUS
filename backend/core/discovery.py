import httpx
import logging
from config import (
    OPENROUTER_MODELS_URL, 
    TIER_THRESHOLD_CHEAP, 
    TIER_THRESHOLD_MID, 
    SAFE_MODELS
)

logger = logging.getLogger(__name__)

class ModelDiscovery:
    """Dynamically fetches and classifies OpenRouter models into tiers."""

    def __init__(self):
        self.raw_models = []
        self.pools = {"cheap": [], "mid": [], "expensive": []}
        self.costs = {}

    async def fetch_and_build(self):
        """Main entry: Fetch from API and build pools."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(OPENROUTER_MODELS_URL)
                if resp.status_code == 200:
                    self.raw_models = resp.json().get("data", [])
                    logger.info(f"[MODEL FETCH] {len(self.raw_models)} models retrieved from OpenRouter.")
                    self._classify_models()
                else:
                    logger.error(f"Failed to fetch models: {resp.status_code}")
                    self._load_fallbacks()
        except Exception as e:
            logger.error(f"Error during model discovery: {e}")
            self._load_fallbacks()
        
        return self.pools, self.costs

    def _classify_models(self):
        """Categorize models based on pricing."""
        for m in self.raw_models:
            m_id = m.get("id")
            pricing = m.get("pricing", {})
            prompt_cost = float(pricing.get("prompt", 0)) * 1000000 # Convert to $ per 1M
            completion_cost = float(pricing.get("completion", 0)) * 1000000
            
            # Simple avg cost metric
            avg_cost = (prompt_cost + completion_cost) / 2
            
            # Filter: only active and not deprecated
            if m.get("description") and "deprecated" in m.get("description", "").lower():
                continue
                
            self.costs[m_id] = {"input": prompt_cost, "output": completion_cost}

            if avg_cost < TIER_THRESHOLD_CHEAP:
                self.pools["cheap"].append(m_id)
            elif avg_cost < TIER_THRESHOLD_MID:
                self.pools["mid"].append(m_id)
            else:
                self.pools["expensive"].append(m_id)

        # Ensure pools are not empty
        for tier, models in self.pools.items():
            if not models:
                self.pools[tier] = [SAFE_MODELS[tier]]
            logger.info(f"[MODEL POOLS] {tier}: {len(models)} models classified.")

    def _load_fallbacks(self):
        """Use hardcoded safe models if API fails."""
        logger.warning("[MODEL FETCH] Using fallback models due to discovery failure.")
        self.pools = {k: [v] for k, v in SAFE_MODELS.items()}
        self.costs = {v: {"input": 0.5, "output": 1.5} for v in SAFE_MODELS.values()}

model_discovery = ModelDiscovery()
