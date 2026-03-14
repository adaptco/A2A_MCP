import pytest
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    ret = pytest.main(["tests/test_mlops_ticker.py", "-v"])
    sys.exit(ret)
