import unittest
import sys
import os

# Bootstrap project root path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

def run_suite():
    # Make sure we use the current folder for test discovery
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=========================================================")
    print("        HCP ERP QA AUTOMATED TEST SUITE RUNNER")
    print("=========================================================")
    
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=test_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n=========================================================")
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)} | Failures: {len(result.failures)}")
    print("=========================================================")
    
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == '__main__':
    run_suite()
