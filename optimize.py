"""Optimize the AgroMap application."""
import os
import sys
import time
import logging
from app import create_app
from app.utils.code_cleaner import CodeCleaner
from app.utils.db_optimizer import DatabaseOptimizer
from app.utils.asset_optimizer import AssetOptimizer
from app.utils.performance import PerformanceOptimizer
from app.utils.api_optimizer import APIOptimizer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/optimization.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def optimize_application():
    """Run all optimization tasks."""
    start_time = time.time()
    app = create_app()
    
    results = {
        'code_cleanup': None,
        'database': None,
        'assets': None,
        'api': None,
        'total_time': 0
    }
    
    try:
        with app.app_context():
            # 1. Code Cleanup
            logger.info("Starting code cleanup...")
            cleaner = CodeCleaner(os.path.join(os.path.dirname(__file__), 'app'))
            results['code_cleanup'] = cleaner.clean_project()
            
            # 2. Database Optimization
            logger.info("Starting database optimization...")
            db_optimizer = DatabaseOptimizer(app.extensions['sqlalchemy'].db.engine)
            results['database'] = db_optimizer.optimize_database()
            
            # 3. Asset Optimization
            logger.info("Starting asset optimization...")
            asset_optimizer = AssetOptimizer()
            results['assets'] = asset_optimizer.optimize_all()
            
            # 4. API Optimization
            logger.info("Starting API optimization...")
            api_optimizer = APIOptimizer(app)
            results['api'] = api_optimizer.get_endpoint_stats()
            
    except Exception as e:
        logger.error(f"Error during optimization: {str(e)}")
        results['error'] = str(e)
    
    results['total_time'] = time.time() - start_time
    
    # Log results
    logger.info("Optimization completed:")
    logger.info(f"Total time: {results['total_time']:.2f} seconds")
    logger.info(f"Files cleaned: {results['code_cleanup']['files_cleaned']}")
    logger.info(f"Database tables optimized: {results['database']['tables_optimized']}")
    logger.info(f"Assets optimized: {len(results['assets'])}")
    logger.info(f"API endpoints analyzed: {len(results['api'])}")
    
    return results

if __name__ == '__main__':
    optimize_application()
