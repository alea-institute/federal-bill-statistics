# imports
import gzip
import json
from pathlib import Path


if __name__ == "__main__":
    # Get all JSON and gzipped JSON files
    bills_path = Path.home() / ".cache" / "fbs" / "bills"
    json_files = list(bills_path.rglob("*"))

    for json_file in json_files:
        data = {}
        with gzip.open(json_file, "rt") as input_file:
            data.update(json.load(input_file))
            if "num_characters" not in data:
                data["num_characters"] = len(data["text"])

            for section_data in data["sections"]:
                if "num_characters" not in section_data:
                    section_data["num_characters"] = len(section_data["text"])

        with gzip.open(json_file, "wt") as output_file:
            json.dump(data, output_file)
