import csv
import os
import secrets
import string

# The `import qrcode` statement is importing a Python library named `qrcode`. This library allows you
# to generate QR codes programmatically. In the code snippet provided, the `qrcode` library is used to
# create a QR code image for a specific URL that is generated based on a base URL and a unique code.
# The generated QR code is then saved as a PNG image file.
from datetime import date, datetime, timezone

import qrcode


CODE_LENGTH = 24
DB_PATH = "QR_codes/code.csv"
ALPHANUM = string.ascii_uppercase + string.digits
BASE_URL = os.environ.get("BASE_URL", "http://rhc6549.glddns.com:8000")
INFO_WORDS = [
    "ALPHA",
    "BRAVO",
    "CHARLIE",
    "DELTA",
    "ECHO",
    "FOXTROT",
    "GOLF",
    "HOTEL",
    "JULIET",
    "KILO",
    "LIMA",
    "MIKE",
    "NOVEMBER",
    "OSCAR",
    "PAPA",
    "QUEBEC",
    "ROMEO",
    "SIERRA",
    "TANGO",
    "UNIFORM",
    "VICTOR",
    "WHISKEY",
    "XRAY",
    "YANKEE",
    "ZULU",
]


def loadExistingCodes(path: str) -> set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="ascii", newline="") as f:
        reader = csv.DictReader(f)
        return {
            row.get("UUID", "").strip() for row in reader if row.get("UUID", "").strip()
        }


FIELDNAMES = [
    "UUID",
    "ManufacturingDate",
    "ExpirationDate",
    "Info",
    "SoldDate",
    "ScanCount",
]


def ensureHeader(path: str) -> None:
    if os.path.exists(path):
        return
    with open(path, "w", encoding="ascii", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()


def generateCode() -> str:
    return "".join(secrets.choice(ALPHANUM) for _ in range(CODE_LENGTH))


def generateInfo() -> str:
    word1 = secrets.choice(INFO_WORDS)
    word2 = secrets.choice(INFO_WORDS)
    number = secrets.randbelow(1000)
    return f"{word1}-{word2}-{number:03d}"


def saveBarcode(code: str) -> None:
    url = f"{BASE_URL}/{code}"
    img = qrcode.make(url)
    img.save(f"QR_codes/{code}.png")


def addYears(base_date: date, years: int) -> date:
    try:
        return base_date.replace(year=base_date.year + years)
    except ValueError:
        # Handle Feb 29 -> Feb 28 in non-leap years.
        return base_date.replace(month=2, day=28, year=base_date.year + years)


def main() -> None:
    ensureHeader(DB_PATH)
    codes = loadExistingCodes(DB_PATH)
    code = generateCode()
    while code in codes:
        code = generateCode()

    manufacturing_date = datetime.now(timezone.utc).date()
    expiration_date = addYears(manufacturing_date, 3)
    info = generateInfo()
    with open(DB_PATH, "a", encoding="ascii", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(
            {
                "UUID": code,
                "ManufacturingDate": manufacturing_date.isoformat(),
                "ExpirationDate": expiration_date.isoformat(),
                "Info": info,
                "SoldDate": "",
                "ScanCount": "0",
            }
        )

    saveBarcode(code)
    print(code)


if __name__ == "__main__":
    main()
