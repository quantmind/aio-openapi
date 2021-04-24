import os

import dotenv

dotenv.load_dotenv()
dotenv.load_dotenv("tests/test.env")

if not os.environ.get("PYTHON_ENV"):
    os.environ["PYTHON_ENV"] = "test"
