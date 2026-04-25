import csv
import os


class InputProcessor:
    def download_input_file(self):
        local_file_path = os.path.join(
            os.path.dirname(__file__),
            "instagram_inputs.csv"
        )

        return local_file_path

    def get_csv_input_generator(self, input_file):
        with open(input_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                accounts = row.get("accounts")

                input_meta = {
                    "accounts": accounts,
                }

                yield input_meta
