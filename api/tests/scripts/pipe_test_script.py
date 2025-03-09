#!/usr/bin/env python3
"""
Test script for the PIPE Queue Service.
This script tests all functionality and cleans up after itself.
No traces are left in the database after completion.
"""

import requests
import json
import time
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Test the PIPE Queue Service')
parser.add_argument('--base-url', default='https://api.photonranch.org/dev',
                    help='Base URL for the API (default: https://api.photonranch.org/api)')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Enable verbose output')

args = parser.parse_args()

BASE_URL = args.base_url
VERBOSE = args.verbose

# Create unique test identifiers
TEST_ID = int(time.time())
TEST_QUEUE = f"test-queue-{TEST_ID}"
TEST_PIPE = f"test-pipe-{TEST_ID}"

# Test results tracking
tests_run = 0
tests_passed = 0
tests_failed = 0

def log(message, is_error=False):
    """Print a message if verbose mode is enabled or it's an error."""
    if VERBOSE or is_error:
        print(message)

def run_test(name, func, *args, **kwargs):
    """Run a test function and track results."""
    global tests_run, tests_passed, tests_failed

    tests_run += 1

    print(f"Running test: {name}...", end=" ")
    sys.stdout.flush()

    try:
        result = func(*args, **kwargs)
        if result:
            print("✅ PASSED")
            tests_passed += 1
            return True
        else:
            print("❌ FAILED")
            tests_failed += 1
            return False
    except Exception as e:
        print(f"❌ FAILED (Exception: {e})")
        tests_failed += 1
        return False

def api_request(method, endpoint, data=None, params=None, expected_status=200):
    """Make an API request and handle response."""
    url = f"{BASE_URL}/pipe/{endpoint}"

    try:
        if method.lower() == 'get':
            response = requests.get(url, params=params)
        elif method.lower() == 'post':
            response = requests.post(url, json=data)
        elif method.lower() == 'delete':
            response = requests.delete(url)
        else:
            log(f"Unsupported method: {method}", True)
            return None

        if response.status_code != expected_status:
            log(f"API Error: {response.status_code} - {response.text}", True)
            return None

        try:
            return response.json()
        except:
            return response.text
    except Exception as e:
        log(f"Request failed: {e}", True)
        return None

# Test functions
def test_create_queue():
    """Test creating a queue."""
    response = api_request('post', 'queue', {"queue_name": TEST_QUEUE})
    if not response:
        return False

    log(f"Created queue: {TEST_QUEUE}")
    return True

def test_list_queues():
    """Test listing all queues."""
    response = api_request('get', 'queues')
    if not response or TEST_QUEUE not in response:
        return False

    log(f"Listed queues: {response}")
    return True

def test_enqueue_item():
    """Test adding an item to a queue."""
    payload = {
        "image_path": f"s3://bucket/test-image-{TEST_ID}.fits",
        "process_type": "test"
    }

    response = api_request('post', 'enqueue', {
        "queue_name": TEST_QUEUE,
        "payload": payload,
        "sender": "test-script"
    })

    if not response:
        return False

    log(f"Enqueued item: {response}")
    return True

def test_peek_queue():
    """Test peeking at queue items."""
    response = api_request('get', f'queue/{TEST_QUEUE}', params={"limit": 5})

    if not response or len(response) == 0:
        return False

    log(f"Peeked at queue: {response}")
    return True

def test_dequeue_item():
    """Test removing an item from a queue."""
    response = api_request('post', f'queue/{TEST_QUEUE}/dequeue')

    if not response:
        return False

    log(f"Dequeued item: {response}")
    return True

def test_queue_is_empty():
    """Test that the queue is empty after dequeuing."""
    url = f"{BASE_URL}/pipe/queue/{TEST_QUEUE}/dequeue"

    response = requests.post(url)
    log(f"Queue empty test got status code: {response.status_code}")

    # We expect a 404 status code
    return response.status_code == 404

def test_set_pipe_status():
    """Test setting the status of a PIPE machine."""
    details = {
        "cpu_usage": "25%",
        "memory_usage": "1.2GB",
        "test_id": TEST_ID
    }

    response = api_request('post', 'status', {
        "pipe_id": TEST_PIPE,
        "status": "online",
        "details": details
    })

    if not response:
        return False

    log(f"Set pipe status: {response}")
    return True

def test_get_pipe_status():
    """Test getting the status of a PIPE machine."""
    response = api_request('get', f'status/{TEST_PIPE}')

    if not response or response.get('status') != 'online':
        return False

    log(f"Got pipe status: {response}")
    return True

def test_get_all_pipe_statuses():
    """Test getting the status of all PIPE machines."""
    response = api_request('get', 'statuses')

    if not response:
        return False

    found = False
    for status in response:
        if status.get('pipe_id') == TEST_PIPE:
            found = True
            break

    if not found:
        log(f"Test pipe not found in statuses", True)
        return False

    log(f"Got all pipe statuses")
    return True

def test_delete_pipe_status():
    """Test deleting the status of a PIPE machine."""
    response = api_request('delete', f'status/{TEST_PIPE}')

    if not response:
        return False

    log(f"Deleted pipe status: {TEST_PIPE}")
    return True

def test_delete_queue():
    """Test deleting a queue."""
    response = api_request('delete', f'queue/{TEST_QUEUE}')

    if not response:
        return False

    log(f"Deleted queue: {TEST_QUEUE}")
    return True

def cleanup():
    """Clean up any remaining test resources."""
    # Delete the test queue if it exists
    api_request('delete', f'queue/{TEST_QUEUE}', expected_status=None)

    # Delete the pipe status
    api_request('delete', f'status/{TEST_PIPE}', expected_status=None)

    log("Cleanup completed")

# Run the tests
print(f"\n📋 PIPE Queue Service Test - {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🔗 API URL: {BASE_URL}")
print(f"🏷️  Test ID: {TEST_ID}")
print("=" * 60)

try:
    run_test("Create Queue", test_create_queue)
    run_test("List Queues", test_list_queues)
    run_test("Enqueue Item", test_enqueue_item)
    run_test("Peek Queue", test_peek_queue)
    run_test("Dequeue Item", test_dequeue_item)
    run_test("Queue is Empty", test_queue_is_empty)
    run_test("Set PIPE Status", test_set_pipe_status)
    run_test("Get PIPE Status", test_get_pipe_status)
    run_test("Get All PIPE Statuses", test_get_all_pipe_statuses)
    run_test("Delete PIPE Status", test_delete_pipe_status)
    run_test("Delete Queue", test_delete_queue)

    # Run final cleanup
    cleanup()

    # Print summary
    print("=" * 60)
    print(f"Total tests: {tests_run}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")

    if tests_failed == 0:
        print("\n✨ All tests passed! ✨")
        sys.exit(0)
    else:
        print(f"\n❌ {tests_failed} test(s) failed")
        sys.exit(1)

except KeyboardInterrupt:
    print("\n\nTest interrupted. Running cleanup...")
    cleanup()
    sys.exit(2)
except Exception as e:
    print(f"\n\nUnexpected error: {e}")
    print("Running cleanup...")
    cleanup()
    sys.exit(3)