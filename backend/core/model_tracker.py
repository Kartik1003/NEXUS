import sqlite3
import logging
import os
from config import DB_PATH, MODEL_COSTS

logger = logging.getLogger(__name__)

class ModelTracker:
    """Tracks model performance (success rate, cost) and applies penalties for failures."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Ensure the model_stats table exists with required metrics."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS model_stats (
                model_id TEXT PRIMARY KEY,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                total_calls INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()

    def update_model(self, model_id: str, success: bool, cost: float):
        """Update stats for a specific model. Automatically penalizes failures."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO model_stats (model_id) VALUES (?)", (model_id,))
        
        if success:
            c.execute("""
                UPDATE model_stats 
                SET success_count = success_count + 1, 
                    total_cost = total_cost + ?,
                    total_calls = total_calls + 1
                WHERE model_id = ?
            """, (cost, model_id))
        else:
            c.execute("""
                UPDATE model_stats 
                SET failure_count = failure_count + 1, 
                    total_cost = total_cost + ?,
                    total_calls = total_calls + 1
                WHERE model_id = ?
            """, (cost, model_id))
            
        conn.commit()
        conn.close()
        logger.info(f"[TRACKER UPDATE] {model_id} success={success} (Cost: {cost:.6f})")

    def get_model_scores(self, models: list[str]) -> dict[str, float]:
        """Calculate scores. If model has failed, apply a significant penalty (score * 0.3)."""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        placeholder = ', '.join(['?'] * len(models))
        c.execute(f"SELECT model_id, success_count, failure_count, total_calls, total_cost FROM model_stats WHERE model_id IN ({placeholder})", models)
        rows = c.fetchall()
        conn.close()

        stats = {r[0]: {"success": r[1], "failures": r[2], "calls": r[3], "cost": r[4]} for r in rows}
        scores = {}
        epsilon = 0.00001
        
        for m in models:
            m_stats = stats.get(m, {"success": 0, "failures": 0, "calls": 0, "cost": 0.0})
            
            if m_stats["calls"] == 0:
                # Default for new models
                success_rate = 0.5
                avg_cost = (MODEL_COSTS.get(m, {"input": 1.0, "output": 2.0})["input"] / 1_000_000) * 500 
                score = success_rate / (avg_cost + epsilon)
            else:
                success_rate = m_stats["success"] / m_stats["calls"]
                avg_cost = m_stats["cost"] / m_stats["calls"]
                score = success_rate / (avg_cost + epsilon)
                
                # --- APPLY FAILURE PENALTY ---
                if m_stats["failures"] > 0:
                    # Penalize based on failure ratio/counts as requested
                    score = score * (0.3 ** m_stats["failures"])

            scores[m] = score
            
        return scores

    def rank_models(self, models: list[str]) -> list[str]:
        """Return models sorted by their performance score (descending)."""
        scores = self.get_model_scores(models)
        ranked = sorted(models, key=lambda m: scores[m], reverse=True)
        
        logger.info("[TRACKER] Current Rankings:")
        for i, m in enumerate(ranked):
            logger.info(f"  {i+1}. {m} (Score: {scores[m]:.4f})")
            
        return ranked

model_tracker = ModelTracker()
