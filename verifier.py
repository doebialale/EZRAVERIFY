import csv
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


DB_PATH = "QR_codes/code.csv"
HOST = "0.0.0.0"
PORT = 8000
MAX_SCANS = 5
FIELDNAMES = ["UUID", "ManufacturingDate", "ExpirationDate", "Info", "SoldDate", "ScanCount"]


def loadRecords(path: str) -> dict[str, dict[str, str]]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="ascii", newline="") as f:
        reader = csv.DictReader(f)
        records: dict[str, dict[str, str]] = {}
        for row in reader:
            uuid = (row.get("UUID") or "").strip()
            if not uuid:
                continue
            records[uuid] = {
                "UUID": uuid,
                "ManufacturingDate": (row.get("ManufacturingDate") or "").strip(),
                "ExpirationDate": (row.get("ExpirationDate") or "").strip(),
                "Timestamp": (row.get("Timestamp") or "").strip(),
                "CreatedDate": (row.get("CreatedDate") or "").strip(),
                "ExpiryDate": (row.get("ExpiryDate") or "").strip(),
                "Info": (row.get("Info") or "").strip(),
                "SoldDate": (row.get("SoldDate") or "").strip(),
                "ScanCount": (row.get("ScanCount") or "0").strip(),
            }
        return records


def saveRecords(path: str, records: dict[str, dict[str, str]]) -> None:
    with open(path, "w", encoding="ascii", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for record in records.values():
            writer.writerow({
                "UUID": record.get("UUID", ""),
                "ManufacturingDate": record.get("ManufacturingDate") or record.get("CreatedDate") or record.get("Timestamp") or "",
                "ExpirationDate": record.get("ExpirationDate") or record.get("ExpiryDate") or "",
                "Info": record.get("Info", ""),
                "SoldDate": record.get("SoldDate", ""),
                "ScanCount": record.get("ScanCount", "0"),
            })


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/" or path == "":
            self._sendHtml(
                200,
                "<h1>Code Lookup</h1><p>Scan a QR code or visit /&lt;UUID&gt;.</p>",
            )
            return

        uuid = path.lstrip("/")
        records = loadRecords(DB_PATH)
        record = records.get(uuid)
        if not record:
            body = (
                "<div class='unverified'>"
                "<span class='unverified-text'>UNVERIFIED</span>"
                "<span class='unverified-icon'>"
                "<svg viewBox='0 0 24 24' aria-hidden='true' focusable='false'>"
                "<circle cx='12' cy='12' r='11'></circle>"
                "<path d='M8 8l8 8M16 8l-8 8'></path>"
                "</svg>"
                "</span>"
                "</div>"
            )
            self._sendHtml(200, body)
            return

        # Check scan count
        scan_count = int(record.get("ScanCount", "0") or "0")

        if scan_count >= MAX_SCANS:
            body = (
                "<div class='expired'>"
                "<span class='expired-text'>SCAN LIMIT REACHED</span>"
                "<span class='expired-icon'>"
                "<svg viewBox='0 0 24 24' aria-hidden='true' focusable='false'>"
                "<circle cx='12' cy='12' r='11'></circle>"
                "<path d='M12 7v6M12 16v1'></path>"
                "</svg>"
                "</span>"
                "</div>"
                "<h1>Item Details</h1>"
                f"<p><strong>UUID:</strong> {record['UUID']}</p>"
                f"<p><strong>Scans:</strong> {scan_count}/{MAX_SCANS} (Maximum reached)</p>"
                "<p class='warning'>This QR code has reached its maximum scan limit.</p>"
            )
            self._sendHtml(200, body)
            return

        # Increment scan count and save
        scan_count += 1
        record["ScanCount"] = str(scan_count)
        saveRecords(DB_PATH, records)

        sold_date = record.get("SoldDate", "")
        sold_info = (
            f"<p><strong>Sold Date:</strong> {sold_date}</p>"
            if sold_date
            else "<p><strong>Sold Date:</strong> Not yet sold</p>"
        )

        body = (
            "<div class='verified'>"
            "<span class='verified-text'>VERIFIED</span>"
            "<span class='verified-icon'>"
            "<svg viewBox='0 0 24 24' aria-hidden='true' focusable='false'>"
            "<circle cx='12' cy='12' r='11'></circle>"
            "<path d='M7 12.5l3 3 7-7'></path>"
            "</svg>"
            "</span>"
            "</div>"
            "<h1>Item Details</h1>"
            f"<p><strong>UUID:</strong> {record['UUID']}</p>"
            f"<p><strong>Manufacturing Date:</strong> {self._coalesceDate(record)}</p>"
            f"<p><strong>Expiration Date:</strong> {self._coalesceExpiration(record)}</p>"
            f"{sold_info}"
            f"<p><strong>Info:</strong> {record['Info']}</p>"
            f"<p><strong>Scans:</strong> {scan_count}/{MAX_SCANS}</p>"
        )
        self._sendHtml(200, body)

    def _coalesceDate(self, record: dict[str, str]) -> str:
        return (
            record.get("ManufacturingDate")
            or record.get("CreatedDate")
            or record.get("Timestamp")
            or ""
        )

    def _coalesceExpiration(self, record: dict[str, str]) -> str:
        return record.get("ExpirationDate") or record.get("ExpiryDate") or ""

    def _sendHtml(self, status: int, body: str) -> None:
        html = (
            "<!doctype html>"
            "<html><head><meta charset='utf-8'>"
            "<title>Code Lookup</title>"
            "<style>"
            "body{font-family:Arial, sans-serif; margin:40px;}"
            "h1{margin-bottom:16px;}"
            "p{margin:8px 0;}"
            ".verified{display:flex; align-items:center; gap:10px; margin:0 0 18px 0;}"
            ".verified-text{background:#1f7a1f; color:#fff; padding:6px 10px; "
            "font-weight:700; letter-spacing:0.5px; border-radius:6px;}"
            ".verified-icon svg{width:28px; height:28px;}"
            ".verified-icon circle{fill:#e6f1ff; stroke:#1f5fa8; stroke-width:2;}"
            ".verified-icon path{fill:none; stroke:#1f5fa8; stroke-width:3; "
            "stroke-linecap:round; stroke-linejoin:round;}"
            ".unverified{display:flex; align-items:center; gap:10px; margin:0 0 18px 0;}"
            ".unverified-text{background:#a81f1f; color:#fff; padding:6px 10px; "
            "font-weight:700; letter-spacing:0.5px; border-radius:6px;}"
            ".unverified-icon svg{width:28px; height:28px;}"
            ".unverified-icon circle{fill:#ffecec; stroke:#a81f1f; stroke-width:2;}"
            ".unverified-icon path{fill:none; stroke:#a81f1f; stroke-width:3; "
            "stroke-linecap:round;}"
            ".expired{display:flex; align-items:center; gap:10px; margin:0 0 18px 0;}"
            ".expired-text{background:#b86800; color:#fff; padding:6px 10px; "
            "font-weight:700; letter-spacing:0.5px; border-radius:6px;}"
            ".expired-icon svg{width:28px; height:28px;}"
            ".expired-icon circle{fill:#fff4e6; stroke:#b86800; stroke-width:2;}"
            ".expired-icon path{fill:none; stroke:#b86800; stroke-width:3; "
            "stroke-linecap:round;}"
            ".warning{color:#b86800; font-style:italic;}"
            "</style></head><body>"
            f"{body}"
            "</body></html>"
        )
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    server = HTTPServer((HOST, PORT), RequestHandler)
    print(f"Serving on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
