import codecs

def main():
    try:
        content = open("log.txt", "rb").read()
        try:
            text = content.decode("utf-16")
        except:
            text = content.decode("mbcs", errors="ignore")

        lines = text.splitlines()
        found = False
        with open("error.txt", "w") as f:
            for line in lines:
                if "error" in line.lower() or "fatal" in line.lower() or "unresolved" in line.lower():
                    f.write(line + "\n")
                    found = True
                    # Let's write up to 5 lines of context
                    continue
                if found:
                     f.write(line + "\n")
                     # Limit to a few lines
                     # But actually, let's just dump all errors.
            
            if not found:
                f.write("No error found in log.txt")

    except Exception as e:
        with open("error.txt", "w") as f:
            f.write(str(e))

if __name__ == "__main__":
    main()
