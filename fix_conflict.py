
import sys

def fix_conflict(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    with open(file_path, 'w') as f:
        in_conflict = False
        for line in lines:
            if line.startswith('<<<<<<<'):
                in_conflict = True
                continue
            elif line.startswith('======='):
                in_conflict = False
                continue
            elif line.startswith('>>>>>>>'):
                in_conflict = False
                continue

            if not in_conflict:
                f.write(line)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python fix_conflict.py <file_path>")
        sys.exit(1)

    fix_conflict(sys.argv[1])
