import sys
import os

# Ensure the api directory is in the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "api"))

from check_results import perform_check_and_notify

if __name__ == "__main__":
    result = perform_check_and_notify()
    print("Test Result:")
    print(result)