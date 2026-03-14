import sys
def test_path():
    with open('pytest_sys_path.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sys.path))
