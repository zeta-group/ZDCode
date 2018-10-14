import traceback
import sys
import general

if __name__ == "__main__":
    try:
        dec = general.ZDCode.parse(open(sys.argv[1]).read()).decorate()
        open(sys.argv[2], "w").write(dec)
        print("Wrote to file successfully.")

    except (IndexError, IOError):
        print("Format: zdcode [<input file> <output file>]")
        print("Caught following error:")
        traceback.print_exc()
        print("Using stdin -> parse -> stdout instead.")

        data = []

        for line in iter(sys.stdin.readline, ""):
            data.append(line.decode("utf-8"))

        if not data:
            print("No data to use! Provide as stdin or as arguments.")
            sys.exit(1)

        open(sys.argv[2]).write(general.ZDCode.parse("".join(data)).decorate())
