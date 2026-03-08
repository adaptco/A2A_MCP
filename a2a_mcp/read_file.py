
import sys

def read_file(file_path):
    with open(file_path, 'r') as f:
        print(f.read())

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python read_file.py <file_path>")
        sys.exit(1)

    read_file(sys.argv[1])
