import json
import sys


def read_ndjson(lines):
    for line in lines:
        if line.strip():
            yield json.loads(line)


def summarize(readings):
    count = total_watts = 0
    for reading in readings:
        count += 1
        total_watts += reading["watts"]
    return {"count": count, "total_watts": total_watts}


def main(path):
    with open(path, encoding="utf-8") as source:
        print(json.dumps(summarize(read_ndjson(source))))


if __name__ == "__main__":
    main(sys.argv[1])
