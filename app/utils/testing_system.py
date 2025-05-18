"""Testing and QA utilities for AgroMap."""
import os
import re
import json
import time
import logging
import requests
import subprocess
from typing import Dict, List, Optional, Any
from flask import Flask, current_app

# Set up logger
logger = logging.getLogger('testing')
handler = logging.FileHandler('logs/testing.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class TestingSystem:
    """Testing and QA system for AgroMap."""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        self.reports_dir = 'data/testing/reports'
        self.screenshots_dir = 'data/testing/screenshots'
        self.test_users = {
            'admin': {
                'username': os.environ.get('TEST_ADMIN_USERNAME', 'admin'),
                'password': os.environ.get('TEST_ADMIN_PASSWORD', 'password')
            },
            'user': {
                'username': os.environ.get('TEST_USER_USERNAME', 'user'),
                'password': os.environ.get('TEST_USER_PASSWORD', 'password')
            }
        }
        
        # Create directories if they don't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize with Flask app."""
        self.app = app
        
        # Register commands
        @app.cli.command("run-security-tests")
        def run_security_tests_command():
            """Run security tests."""
            results = self.run_security_tests()
            print(f"Security tests completed. Passed: {results['passed']}, Failed: {results['failed']}")
            if results['failed_tests']:
                print("Failed tests:")
                for test in results['failed_tests']:
                    print(f"- {test['name']}: {test['message']}")
        
        @app.cli.command("run-load-tests")
        def run_load_tests_command():
            """Run load tests."""
            results = self.run_load_tests()
            print(f"Load tests completed. Average response time: {results['avg_response_time']}ms")
            print(f"Requests per second: {results['requests_per_second']}")
        
        @app.cli.command("run-feature-tests")
        def run_feature_tests_command():
            """Run feature tests."""
            results = self.run_feature_tests()
            print(f"Feature tests completed. Passed: {results['passed']}, Failed: {results['failed']}")
            if results['failed_tests']:
                print("Failed tests:")
                for test in results['failed_tests']:
                    print(f"- {test['name']}: {test['message']}")
        
        @app.cli.command("test-mobile-support")
        def test_mobile_support_command():
            """Test mobile support."""
            results = self.test_mobile_support()
            print(f"Mobile support tests completed. Passed: {results['passed']}, Failed: {results['failed']}")
            if results['failed_tests']:
                print("Failed tests:")
                for test in results['failed_tests']:
                    print(f"- {test['name']}: {test['message']}")
        
        @app.cli.command("validate-forms")
        def validate_forms_command():
            """Validate forms."""
            results = self.validate_forms()
            print(f"Form validation tests completed. Passed: {results['passed']}, Failed: {results['failed']}")
            if results['failed_tests']:
                print("Failed tests:")
                for test in results['failed_tests']:
                    print(f"- {test['name']}: {test['message']}")
        
        @app.cli.command("test-offline-mode")
        def test_offline_mode_command():
            """Test offline mode."""
            results = self.test_offline_mode()
            print(f"Offline mode tests completed. Passed: {results['passed']}, Failed: {results['failed']}")
            if results['failed_tests']:
                print("Failed tests:")
                for test in results['failed_tests']:
                    print(f"- {test['name']}: {test['message']}")
        
        @app.cli.command("verify-translations")
        def verify_translations_command():
            """Verify translations."""
            results = self.verify_translations()
            print(f"Translation verification completed. Passed: {results['passed']}, Failed: {results['failed']}")
            if results['failed_tests']:
                print("Failed tests:")
                for test in results['failed_tests']:
                    print(f"- {test['name']}: {test['message']}")
    
    def run_security_tests(self) -> Dict:
        """Run security tests."""
        logger.info("Running security tests")
        
        results = {
            'passed': 0,
            'failed': 0,
            'failed_tests': []
        }
        
        # List of security tests to run
        tests = [
            self._test_csrf_protection,
            self._test_xss_protection,
            self._test_sql_injection,
            self._test_authentication,
            self._test_authorization
        ]
        
        # Run each test
        for test in tests:
            try:
                test_result = test()
                if test_result['passed']:
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                    results['failed_tests'].append({
                        'name': test.__name__,
                        'message': test_result['message']
                    })
            except Exception as e:
                results['failed'] += 1
                results['failed_tests'].append({
                    'name': test.__name__,
                    'message': str(e)
                })
                logger.error(f"Error in {test.__name__}: {str(e)}")
        
        # Save results to file
        self._save_test_results('security_tests', results)
        
        return results
    
    def _test_csrf_protection(self) -> Dict:
        """Test CSRF protection."""
        try:
            # Try to submit a form without CSRF token
            response = requests.post(
                f"{self.base_url}/login",
                data={
                    'username': 'test',
                    'password': 'test'
                }
            )
            
            # Check if request was rejected
            if response.status_code == 400 or 'csrf' in response.text.lower():
                return {
                    'passed': True,
                    'message': 'CSRF protection is working'
                }
            else:
                return {
                    'passed': False,
                    'message': f"CSRF protection failed: {response.status_code}"
                }
        except Exception as e:
            return {
                'passed': False,
                'message': f"Error testing CSRF protection: {str(e)}"
            }
    
    def _test_xss_protection(self) -> Dict:
        """Test XSS protection."""
        try:
            # Try to inject a script
            xss_payload = '<script>alert("XSS")</script>'
            response = requests.get(
                f"{self.base_url}/search",
                params={'q': xss_payload}
            )
            
            # Check if script was escaped
            if xss_payload in response.text:
                return {
                    'passed': False,
                    'message': 'XSS payload was not escaped'
                }
            else:
                return {
                    'passed': True,
                    'message': 'XSS protection is working'
                }
        except Exception as e:
            return {
                'passed': False,
                'message': f"Error testing XSS protection: {str(e)}"
            }
    
    def _test_sql_injection(self) -> Dict:
        """Test SQL injection protection."""
        try:
            # Try a simple SQL injection
            sql_payload = "' OR '1'='1"
            response = requests.post(
                f"{self.base_url}/login",
                data={
                    'username': sql_payload,
                    'password': sql_payload
                }
            )
            
            # Check if login was successful (it shouldn't be)
            if 'welcome' in response.text.lower() or 'dashboard' in response.text.lower():
                return {
                    'passed': False,
                    'message': 'SQL injection may have succeeded'
                }
            else:
                return {
                    'passed': True,
                    'message': 'SQL injection protection is working'
                }
        except Exception as e:
            return {
                'passed': False,
                'message': f"Error testing SQL injection protection: {str(e)}"
            }
    
    def _test_authentication(self) -> Dict:
        """Test authentication system."""
        try:
            # Try to access a protected page without authentication
            response = requests.get(f"{self.base_url}/dashboard")
            
            # Check if redirected to login
            if response.url.endswith('/login') or 'login' in response.text.lower():
                return {
                    'passed': True,
                    'message': 'Authentication is working'
                }
            else:
                return {
                    'passed': False,
                    'message': 'Authentication bypass may be possible'
                }
        except Exception as e:
            return {
                'passed': False,
                'message': f"Error testing authentication: {str(e)}"
            }
    
    def _test_authorization(self) -> Dict:
        """Test authorization system."""
        try:
            # Login as regular user
            session = requests.Session()
            login_response = session.post(
                f"{self.base_url}/login",
                data={
                    'username': self.test_users['user']['username'],
                    'password': self.test_users['user']['password']
                }
            )
            
            # Try to access admin page
            response = session.get(f"{self.base_url}/admin")
            
            # Check if access was denied
            if response.status_code == 403 or 'forbidden' in response.text.lower():
                return {
                    'passed': True,
                    'message': 'Authorization is working'
                }
            else:
                return {
                    'passed': False,
                    'message': 'Authorization bypass may be possible'
                }
        except Exception as e:
            return {
                'passed': False,
                'message': f"Error testing authorization: {str(e)}"
            }
    
    def run_load_tests(self, num_requests: int = 100, concurrency: int = 10) -> Dict:
        """Run load tests."""
        logger.info(f"Running load tests with {num_requests} requests and {concurrency} concurrent users")
        
        results = {
            'num_requests': num_requests,
            'concurrency': concurrency,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'requests_per_second': 0
        }
        
        # Use Apache Bench if available
        try:
            output = subprocess.check_output([
                'ab',
                '-n', str(num_requests),
                '-c', str(concurrency),
                self.base_url + '/'
            ], stderr=subprocess.STDOUT, text=True)
            
            # Parse results
            rps_match = re.search(r'Requests per second:\s+(\d+\.\d+)', output)
            if rps_match:
                results['requests_per_second'] = float(rps_match.group(1))
            
            time_match = re.search(r'Time per request:\s+(\d+\.\d+)', output)
            if time_match:
                results['avg_response_time'] = float(time_match.group(1))
            
            success_match = re.search(r'Complete requests:\s+(\d+)', output)
            if success_match:
                results['successful_requests'] = int(success_match.group(1))
            
            failed_match = re.search(r'Failed requests:\s+(\d+)', output)
            if failed_match:
                results['failed_requests'] = int(failed_match.group(1))
            
            logger.info(f"Load test completed: {results['requests_per_second']} req/s, {results['avg_response_time']}ms avg")
        
        # Fallback to manual testing if Apache Bench is not available
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.warning("Apache Bench not available, using simple load test")
            
            start_time = time.time()
            
            # Make requests sequentially for simplicity
            for _ in range(num_requests):
                try:
                    response = requests.get(self.base_url)
                    if response.status_code == 200:
                        results['successful_requests'] += 1
                    else:
                        results['failed_requests'] += 1
                except Exception:
                    results['failed_requests'] += 1
            
            # Calculate results
            total_time = time.time() - start_time
            if total_time > 0:
                results['requests_per_second'] = num_requests / total_time
                results['avg_response_time'] = (total_time * 1000) / num_requests  # Convert to ms
            
            logger.info(f"Simple load test completed: {results['requests_per_second']:.2f} req/s, {results['avg_response_time']:.2f}ms avg")
        
        # Save results to file
        self._save_test_results('load_tests', results)
        
        return results
    
    def run_feature_tests(self) -> Dict:
        """Run feature tests."""
        logger.info("Running feature tests")
        
        results = {
            'passed': 0,
            'failed': 0,
            'failed_tests': []
        }
        
        # List of features to test
        features = [
            {'name': 'Home Page', 'url': '/'},
            {'name': 'Login Page', 'url': '/login'},
            {'name': 'Registration Page', 'url': '/register'},
            {'name': 'Dashboard', 'url': '/dashboard'},
            {'name': 'Map', 'url': '/map'},
            {'name': 'Profile', 'url': '/profile'}
        ]
        
        # Test each feature
        for feature in features:
            try:
                response = requests.get(f"{self.base_url}{feature['url']}")
                
                # Check if page loaded successfully
                if response.status_code == 200 or (response.status_code == 302 and '/login' in response.url):
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                    results['failed_tests'].append({
                        'name': feature['name'],
                        'message': f"Failed with status code {response.status_code}"
                    })
            except Exception as e:
                results['failed'] += 1
                results['failed_tests'].append({
                    'name': feature['name'],
                    'message': str(e)
                })
                logger.error(f"Error testing {feature['name']}: {str(e)}")
        
        # Save results to file
        self._save_test_results('feature_tests', results)
        
        return results
    
    def test_mobile_support(self) -> Dict:
        """Test mobile support."""
        logger.info("Testing mobile support")
        
        results = {
            'passed': 0,
            'failed': 0,
            'failed_tests': []
        }
        
        # List of mobile user agents to test
        mobile_agents = [
            {'name': 'iPhone', 'agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'},
            {'name': 'Android', 'agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Mobile Safari/537.36'}
        ]
        
        # Pages to test
        pages = [
            {'name': 'Home Page', 'url': '/'},
            {'name': 'Login Page', 'url': '/login'},
            {'name': 'Map Page', 'url': '/map'}
        ]
        
        # Test each page with each mobile agent
        for agent in mobile_agents:
            for page in pages:
                try:
                    headers = {'User-Agent': agent['agent']}
                    response = requests.get(f"{self.base_url}{page['url']}", headers=headers)
                    
                    # Check if page loaded successfully
                    if response.status_code == 200:
                        results['passed'] += 1
                    else:
                        results['failed'] += 1
                        results['failed_tests'].append({
                            'name': f"{page['name']} on {agent['name']}",
                            'message': f"Failed with status code {response.status_code}"
                        })
                except Exception as e:
                    results['failed'] += 1
                    results['failed_tests'].append({
                        'name': f"{page['name']} on {agent['name']}",
                        'message': str(e)
                    })
                    logger.error(f"Error testing {page['name']} on {agent['name']}: {str(e)}")
        
        # Save results to file
        self._save_test_results('mobile_tests', results)
        
        return results
    
    def validate_forms(self) -> Dict:
        """Validate forms."""
        logger.info("Validating forms")
        
        results = {
            'passed': 0,
            'failed': 0,
            'failed_tests': []
        }
        
        # List of forms to test
        forms = [
            {
                'name': 'Login Form',
                'url': '/login',
                'data': {'username': '', 'password': ''},
                'expected_error': True
            },
            {
                'name': 'Registration Form',
                'url': '/register',
                'data': {'username': 'test', 'email': 'invalid-email', 'password': 'short'},
                'expected_error': True
            }
        ]
        
        # Test each form
        for form in forms:
            try:
                response = requests.post(f"{self.base_url}{form['url']}", data=form['data'])
                
                # Check if validation worked as expected
                if (form['expected_error'] and response.status_code != 200) or \
                   (form['expected_error'] and 'error' in response.text.lower()) or \
                   (not form['expected_error'] and response.status_code == 200):
                    results['passed'] += 1
                else:
                    results['failed'] += 1
                    results['failed_tests'].append({
                        'name': form['name'],
                        'message': "Form validation did not work as expected"
                    })
            except Exception as e:
                results['failed'] += 1
                results['failed_tests'].append({
                    'name': form['name'],
                    'message': str(e)
                })
                logger.error(f"Error testing {form['name']}: {str(e)}")
        
        # Save results to file
        self._save_test_results('form_validation', results)
        
        return results
    
    def test_offline_mode(self) -> Dict:
        """Test offline mode."""
        logger.info("Testing offline mode")
        
        # This is a simplified test since we can't easily test offline functionality
        # without a browser automation tool like Selenium
        
        results = {
            'passed': 0,
            'failed': 0,
            'failed_tests': []
        }
        
        # Check if service worker is registered
        try:
            response = requests.get(f"{self.base_url}/static/sw.js")
            if response.status_code == 200:
                results['passed'] += 1
            else:
                results['failed'] += 1
                results['failed_tests'].append({
                    'name': 'Service Worker',
                    'message': f"Service worker file not found: {response.status_code}"
                })
        except Exception as e:
            results['failed'] += 1
            results['failed_tests'].append({
                'name': 'Service Worker',
                'message': str(e)
            })
            logger.error(f"Error testing service worker: {str(e)}")
        
        # Check if manifest exists
        try:
            response = requests.get(f"{self.base_url}/static/manifest.json")
            if response.status_code == 200:
                results['passed'] += 1
            else:
                results['failed'] += 1
                results['failed_tests'].append({
                    'name': 'Manifest',
                    'message': f"Manifest file not found: {response.status_code}"
                })
        except Exception as e:
            results['failed'] += 1
            results['failed_tests'].append({
                'name': 'Manifest',
                'message': str(e)
            })
            logger.error(f"Error testing manifest: {str(e)}")
        
        # Save results to file
        self._save_test_results('offline_mode', results)
        
        return results
    
    def verify_translations(self) -> Dict:
        """Verify translations."""
        logger.info("Verifying translations")
        
        results = {
            'passed': 0,
            'failed': 0,
            'failed_tests': []
        }
        
        # List of languages to test
        languages = ['en', 'ru', 'uz']
        
        # Pages to test
        pages = [
            {'name': 'Home Page', 'url': '/'}
        ]
        
        # Test each page with each language
        for lang in languages:
            for page in pages:
                try:
                    headers = {'Accept-Language': lang}
                    response = requests.get(f"{self.base_url}{page['url']}", headers=headers)
                    
                    # Check if page loaded successfully
                    if response.status_code == 200:
                        results['passed'] += 1
                    else:
                        results['failed'] += 1
                        results['failed_tests'].append({
                            'name': f"{page['name']} in {lang}",
                            'message': f"Failed with status code {response.status_code}"
                        })
                except Exception as e:
                    results['failed'] += 1
                    results['failed_tests'].append({
                        'name': f"{page['name']} in {lang}",
                        'message': str(e)
                    })
                    logger.error(f"Error testing {page['name']} in {lang}: {str(e)}")
        
        # Save results to file
        self._save_test_results('translations', results)
        
        return results
    
    def _save_test_results(self, test_type: str, results: Dict) -> None:
        """Save test results to file."""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(self.reports_dir, f"{test_type}_{timestamp}.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': timestamp,
                'test_type': test_type,
                'results': results
            }, f, indent=2)
        
        logger.info(f"Saved {test_type} results to {filename}")

# Initialize testing system
def init_testing_system(app: Optional[Flask] = None) -> TestingSystem:
    """Initialize testing system."""
    testing = TestingSystem(app)
    logger.info("Testing system initialized")
    return testing