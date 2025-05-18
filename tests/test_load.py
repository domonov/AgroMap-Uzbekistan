"""Load testing module for AgroMap."""
import pytest
import multiprocessing
import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

def make_request(url: str, method: str = 'GET', data: Dict = None) -> Tuple[float, int]:
    """Make a request and return response time and status code."""
    start_time = time.time()
    try:
        if method == 'GET':
            response = requests.get(url)
        else:
            response = requests.post(url, json=data)
        response_time = time.time() - start_time
        return response_time, response.status_code
    except:
        return time.time() - start_time, 500

def load_test_endpoint(url: str, num_requests: int = 100, 
                      concurrent_users: int = 10) -> Dict[str, Any]:
    """Run a load test on a specific endpoint."""
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [
            executor.submit(make_request, url)
            for _ in range(num_requests)
        ]
        
        response_times = []
        status_codes = []
        
        for future in as_completed(futures):
            response_time, status_code = future.result()
            response_times.append(response_time)
            status_codes.append(status_code)
    
    successful_requests = sum(1 for code in status_codes if 200 <= code < 300)
    failed_requests = len(status_codes) - successful_requests
    
    return {
        'total_requests': num_requests,
        'successful_requests': successful_requests,
        'failed_requests': failed_requests,
        'avg_response_time': statistics.mean(response_times),
        'median_response_time': statistics.median(response_times),
        'min_response_time': min(response_times),
        'max_response_time': max(response_times),
        'percentile_95': statistics.quantiles(response_times, n=20)[18],
        'requests_per_second': num_requests / sum(response_times)
    }

def test_homepage_load(live_server):
    """Test homepage under load."""
    results = load_test_endpoint(
        f"{live_server.url()}/",
        num_requests=100,
        concurrent_users=10
    )
    
    # Assert performance requirements
    assert results['avg_response_time'] < 1.0  # Average response time under 1 second
    assert results['percentile_95'] < 2.0  # 95th percentile under 2 seconds
    assert results['failed_requests'] == 0  # No failed requests
    assert results['requests_per_second'] > 10  # At least 10 RPS

def test_api_endpoints_load(live_server):
    """Test API endpoints under load."""
    api_endpoints = [
        '/api/weather',
        '/api/crops',
        '/api/predictions',
        '/api/analytics'
    ]
    
    for endpoint in api_endpoints:
        results = load_test_endpoint(
            f"{live_server.url()}{endpoint}",
            num_requests=50,
            concurrent_users=5
        )
        
        # Assert API performance requirements
        assert results['avg_response_time'] < 0.5  # Average response under 500ms
        assert results['percentile_95'] < 1.0  # 95th percentile under 1 second
        assert results['failed_requests'] == 0  # No failed requests
        assert results['requests_per_second'] > 20  # At least 20 RPS

def test_map_load(live_server):
    """Test map functionality under load."""
    results = load_test_endpoint(
        f"{live_server.url()}/map",
        num_requests=30,
        concurrent_users=3
    )
    
    # Assert map performance requirements
    assert results['avg_response_time'] < 2.0  # Average response under 2 seconds
    assert results['percentile_95'] < 4.0  # 95th percentile under 4 seconds
    assert results['failed_requests'] == 0  # No failed requests

def test_database_load():
    """Test database performance under load."""
    from app import db
    from app.models import Crop, Weather, Prediction
    import random
    
    # Test batch inserts
    start_time = time.time()
    crops = []
    for _ in range(1000):
        crop = Crop(
            name=f"Test Crop {random.randint(1, 1000)}",
            type="Test",
            planted_date=time.strftime('%Y-%m-%d')
        )
        crops.append(crop)
    
    db.session.bulk_save_objects(crops)
    db.session.commit()
    
    insert_time = time.time() - start_time
    assert insert_time < 5.0  # Batch insert should take less than 5 seconds
    
    # Test batch queries
    start_time = time.time()
    results = db.session.query(Crop).limit(1000).all()
    query_time = time.time() - start_time
    assert query_time < 1.0  # Batch query should take less than 1 second
