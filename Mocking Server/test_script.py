#!/usr/bin/env python3
"""
Setup and test script for the Infoblox Mock Server.
This script checks dependencies, starts the server, and runs basic tests.
"""

import os
import sys
import subprocess
import time
import argparse
import requests
import json
import signal
import platform

# Default values
DEFAULT_PORT = 8080
DEFAULT_HOST = "localhost"
SERVER_SCRIPT = "infoblox_mock_server.py"
TEST_SCRIPT = "test_infoblox_client.py"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(message, color):
    """Print colored text if supported"""
    if sys.stdout.isatty():
        print(f"{color}{message}{Colors.ENDC}")
    else:
        print(message)

def print_header(message):
    """Print a header"""
    print("\n" + "=" * 60)
    print_colored(f"  {message}", Colors.CYAN + Colors.BOLD)
    print("=" * 60)

def check_dependencies():
    """Check if required dependencies are installed"""
    print_header("Checking Dependencies")
    
    required_packages = ["flask", "requests"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print_colored(f"✗ {package} is not installed", Colors.RED)
    
    if missing_packages:
        print_colored(f"\nMissing packages: {', '.join(missing_packages)}", Colors.YELLOW)
        install = input("Do you want to install missing packages? (y/n): ")
        if install.lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print_colored("Packages installed successfully", Colors.GREEN)
        else:
            print_colored("Warning: Missing packages may cause the server to fail", Colors.YELLOW)
    else:
        print_colored("\nAll dependencies are installed", Colors.GREEN)

def wait_for_server(url, max_attempts=30, delay=1):
    """Wait for the server to become responsive"""
    print("Waiting for server to start", end="", flush=True)
    
    for i in range(max_attempts):
        try:
            # Try a simple unauthenticated request to check if server is up
            response = requests.get(f"{url}/grid", timeout=1)
            # We expect a 401 response since we're not authenticated
            if response.status_code == 401:
                print("\nServer is up and running!")
                return True
        except requests.RequestException:
            pass
        
        print(".", end="", flush=True)
        time.sleep(delay)
    
    print("\nServer failed to start in the expected time")
    return False

def start_server(host, port, delay=False, failures=False, persistence=False):
    """Start the Infoblox mock server"""
    print_header(f"Starting Infoblox Mock Server on {host}:{port}")
    
    if not os.path.exists(SERVER_SCRIPT):
        print_colored(f"Error: Server script {SERVER_SCRIPT} not found", Colors.RED)
        sys.exit(1)
    
    # Build command line arguments
    cmd = [sys.executable, SERVER_SCRIPT, "--host", host, "--port", str(port)]
    
    if delay:
        cmd.append("--delay")
    if failures:
        cmd.append("--failures")
    if persistence:
        cmd.append("--persistence")
    
    # Start the server
    if platform.system() == "Windows":
        # On Windows, we use a new console window
        from subprocess import CREATE_NEW_CONSOLE
        server_process = subprocess.Popen(cmd, creationflags=CREATE_NEW_CONSOLE)
    else:
        # On Unix-like systems, we use a background process
        server_process = subprocess.Popen(cmd, 
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         preexec_fn=os.setsid)
    
    # Wait for the server to be ready
    server_url = f"http://{host}:{port}/wapi/v2.11"
    if not wait_for_server(server_url):
        print_colored("Error: Server failed to start properly", Colors.RED)
        try:
            if platform.system() != "Windows":
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
            else:
                server_process.terminate()
        except:
            pass
        sys.exit(1)
    
    return server_process, server_url

def run_basic_tests(server_url):
    """Run basic tests against the server"""
    print_header("Running Basic Tests")
    
    # Define tests
    tests = [
        {
            "name": "Authentication",
            "method": "POST",
            "endpoint": "/grid/session",
            "auth": ("admin", "infoblox"),
            "expected_status": 200
        },
        {
            "name": "Get Grid Info",
            "method": "GET",
            "endpoint": "/grid",
            "auth": ("admin", "infoblox"),
            "expected_status": 200
        },
        {
            "name": "Get Networks",
            "method": "GET",
            "endpoint": "/network",
            "auth": ("admin", "infoblox"),
            "expected_status": 200
        },
        {
            "name": "Create Network",
            "method": "POST",
            "endpoint": "/network",
            "auth": ("admin", "infoblox"),
            "json": {"network": "192.168.100.0/24", "comment": "Test network"},
            "expected_status": 200
        },
        {
            "name": "Next Available IP",
            "method": "POST",
            "endpoint": "/network/192.168.100.0%2F24/next_available_ip",
            "auth": ("admin", "infoblox"),
            "expected_status": 200
        },
        {
            "name": "Search IP",
            "method": "GET",
            "endpoint": "/ipv4address?ip_address=192.168.100.10",
            "auth": ("admin", "infoblox"),
            "expected_status": 200
        },
        {
            "name": "Unauthorized Access",
            "method": "GET",
            "endpoint": "/network",
            "auth": None,
            "expected_status": 401
        }
    ]
    
    # Run tests
    success_count = 0
    for test in tests:
        print(f"Running test: {test['name']}...", end=" ")
        
        # Prepare request
        method = test["method"]
        url = f"{server_url}{test['endpoint']}"
        kwargs = {
            "timeout": 5
        }
        
        if test.get("auth"):
            kwargs["auth"] = test["auth"]
        
        if test.get("json"):
            kwargs["json"] = test["json"]
        
        # Send request
        try:
            response = requests.request(method, url, **kwargs)
            
            # Check status code
            if response.status_code == test["expected_status"]:
                print_colored("PASSED", Colors.GREEN)
                success_count += 1
            else:
                print_colored(f"FAILED - Expected {test['expected_status']}, got {response.status_code}", Colors.RED)
                print(f"Response: {response.text}")
        except Exception as e:
            print_colored(f"ERROR - {str(e)}", Colors.RED)
    
    # Show summary
    print(f"\nTest summary: {success_count} of {len(tests)} tests passed")
    if success_count == len(tests):
        print_colored("All tests passed successfully!", Colors.GREEN)
    else:
        print_colored(f"Some tests failed ({len(tests) - success_count} failures)", Colors.YELLOW)

def run_comprehensive_tests(server_url):
    """Run more comprehensive tests using the client example"""
    print_header("Running Comprehensive Tests")
    
    if not os.path.exists(TEST_SCRIPT):
        print(f"Test script {TEST_SCRIPT} not found. Creating it...")
        
        # Create a copy of the client example to use as test script
        from shutil import copyfile
        if os.path.exists("test_infoblox_client.py"):
            # Rename existing file if it exists
            os.rename("test_infoblox_client.py", "test_infoblox_client.py.bak")
        
        # Copy
        copyfile("example_infoblox_client.py", TEST_SCRIPT)
        print_colored(f"Created {TEST_SCRIPT} from example client", Colors.GREEN)
    
    # Run the test script
    print(f"Running {TEST_SCRIPT}...")
    try:
        result = subprocess.run([sys.executable, TEST_SCRIPT, server_url], 
                               capture_output=True, text=True, timeout=60)
        
        # Check output
        if result.returncode == 0:
            print_colored("Comprehensive tests completed successfully", Colors.GREEN)
            # Print some of the output
            lines = result.stdout.split('\n')
            if len(lines) > 20:
                print("First 10 lines of output:")
                for line in lines[:10]:
                    print(f"  {line}")
                print("...")
                print("Last 10 lines of output:")
                for line in lines[-10:]:
                    print(f"  {line}")
            else:
                print("Output:")
                print(result.stdout)
        else:
            print_colored("Comprehensive tests failed", Colors.RED)
            print("Error output:")
            print(result.stderr)
    except subprocess.TimeoutExpired:
        print_colored("Comprehensive tests timed out", Colors.YELLOW)
    except Exception as e:
        print_colored(f"Error running comprehensive tests: {str(e)}", Colors.RED)

def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Setup and test the Infoblox Mock Server')
    parser.add_argument('--host', default=DEFAULT_HOST, help='Host to bind the server to')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Port to run the server on')
    parser.add_argument('--skip-deps', action='store_true', help='Skip dependency check')
    parser.add_argument('--delay', action='store_true', help='Enable simulated delay')
    parser.add_argument('--failures', action='store_true', help='Enable simulated failures')
    parser.add_argument('--persistence', action='store_true', help='Enable database persistence')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running tests')
    
    args = parser.parse_args()
    
    # Print banner
    print_colored("\n  Infoblox Mock Server - Setup and Test Script  ", Colors.CYAN + Colors.BOLD)
    print_colored("  ========================================  \n", Colors.CYAN)
    
    # Check dependencies
    if not args.skip_deps:
        check_dependencies()
    
    # Start the server
    server_process, server_url = start_server(
        args.host, args.port, 
        delay=args.delay, 
        failures=args.failures,
        persistence=args.persistence
    )
    
    # Run tests if not skipped
    if not args.skip_tests:
        run_basic_tests(server_url)
        
        run_comprehensive = input("\nDo you want to run comprehensive tests? (y/n): ")
        if run_comprehensive.lower() == 'y':
            run_comprehensive_tests(server_url)
    
    # Keep server running?
    keep_running = input("\nDo you want to keep the server running? (y/n): ")
    if keep_running.lower() == 'y':
        print_colored(f"\nServer is running on {args.host}:{args.port}", Colors.GREEN)
        print("Press Ctrl+C to stop...")
        try:
            # Keep script running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping server...")
    
    # Clean up
    try:
        if platform.system() != "Windows":
            os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
        else:
            server_process.terminate()
        print("Server stopped")
    except:
        print("Server process may still be running")

if __name__ == "__main__":
    main()