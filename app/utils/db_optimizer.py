"""Database optimization utilities."""
import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import Table

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.inspector = inspect(engine)
    
    def analyze_table_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics for a table."""
        with Session(self.engine) as session:
            result = session.execute(text(f"""
                SELECT
                    relname as table,
                    n_live_tup as row_count,
                    n_dead_tup as dead_tuples,
                    round(100 * n_dead_tup / (n_live_tup + n_dead_tup + 1))::integer as dead_tuple_pct,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                WHERE relname = :table_name
            """), {'table_name': table_name})
            return dict(result.fetchone() or {})

    def get_slow_queries(self, min_time: float = 1.0) -> List[Dict[str, Any]]:
        """Get list of slow queries."""
        with Session(self.engine) as session:
            result = session.execute(text("""
                SELECT
                    query,
                    calls,
                    total_time / calls as avg_time,
                    rows / calls as avg_rows
                FROM pg_stat_statements
                WHERE total_time / calls > :min_time
                ORDER BY avg_time DESC
                LIMIT 10
            """), {'min_time': min_time})
            return [dict(row) for row in result]

    def suggest_indexes(self, table_name: str) -> List[str]:
        """Suggest indexes based on query patterns."""
        with Session(self.engine) as session:
            # Check existing indexes
            existing_indexes = {
                idx['name']: idx['column_names'] 
                for idx in self.inspector.get_indexes(table_name)
            }
            
            # Analyze query patterns
            result = session.execute(text("""
                SELECT
                    schemaname,
                    relname,
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    idx_tup_fetch
                FROM pg_stat_user_tables
                WHERE relname = :table_name
            """), {'table_name': table_name})
            
            stats = dict(result.fetchone() or {})
            suggestions = []
            
            # If many sequential scans but few index scans
            if stats.get('seq_scan', 0) > stats.get('idx_scan', 0) * 10:
                # Get commonly queried columns
                result = session.execute(text("""
                    SELECT
                        attname,
                        n_distinct,
                        correlation
                    FROM pg_stats
                    WHERE tablename = :table_name
                    AND n_distinct > -0.5  -- Not unique
                    AND correlation < 0.9   -- Not highly correlated
                """), {'table_name': table_name})
                
                for row in result:
                    col_name = row['attname']
                    # Suggest index if not already exists
                    if not any(col_name in idx_cols for idx_cols in existing_indexes.values()):
                        suggestions.append(f"CREATE INDEX idx_{table_name}_{col_name} ON {table_name} ({col_name});")
            
            return suggestions

    def optimize_table(self, table_name: str):
        """Optimize a specific table."""
        with Session(self.engine) as session:
            # Analyze table
            session.execute(text(f"ANALYZE {table_name};"))
            
            # Vacuum table
            session.execute(text(f"VACUUM ANALYZE {table_name};"))
            
            # Reindex if needed
            session.execute(text(f"REINDEX TABLE {table_name};"))

    def optimize_queries(self, table_name: str) -> List[Dict[str, Any]]:
        """Get query optimization suggestions."""
        suggestions = []
        
        with Session(self.engine) as session:
            # Check for queries not using indexes
            result = session.execute(text("""
                SELECT
                    query,
                    calls,
                    total_time / calls as avg_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements
                WHERE query ilike :table_pattern
                AND not query ilike '%EXPLAIN%'
                ORDER BY total_time DESC
                LIMIT 5
            """), {'table_pattern': f'%{table_name}%'})