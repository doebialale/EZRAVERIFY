# EzraVerify

A product authenticity verification system that generates unique QR codes linked to UUIDs. Users scan QR codes to verify product authenticity via a web server.

## Features

- **Unique QR Code Generation**: Creates cryptographically secure 24-character alphanumeric UUIDs
- **Product Verification**: Web server for real-time product authenticity checks
- **Scan Limiting**: Prevents abuse by limiting scans per QR code (default: 5 scans)
- **Product Metadata**: Tracks manufacturing date, expiration date, and custom info

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Clone the repository
git clone https://github.com/doebialale/EZRAVERIFY.git
cd EzraVerify

# Install dependencies
uv sync
```

## Usage

### Generate a QR Code

```bash
uv run python code_generator.py
```

This will:
1. Generate a unique 24-character UUID
2. Create a QR code image in `QR_codes/`
3. Add a record to `QR_codes/code.csv`

### Start the Verification Server

```bash
uv run python verifier.py
```

The server runs on `http://0.0.0.0:8000` by default.

### Verify a Product

- **Web**: Visit `http://localhost:8000/{UUID}`
- **QR Scan**: Scan the generated QR code with any QR reader

## Configuration

### Environment Variables

| Variable   | Description                  | Default                          |
| ---------- | ---------------------------- | -------------------------------- |
| `BASE_URL` | Base URL encoded in QR codes | `http://rhc6549.glddns.com:8000` |

### Constants

- `CODE_LENGTH`: UUID length (24 characters)
- `MAX_SCANS`: Maximum scans per QR code (5)
- `PORT`: Server port (8000)

## Project Structure

```
EzraVerify/
├── code_generator.py   # Generates UUIDs, QR codes, and stores records
├── verifier.py         # HTTP server for QR code verification lookups
├── QR_codes/
│   ├── code.csv        # Database of all generated UUIDs and metadata
│   └── *.png           # Generated QR code images
├── pyproject.toml      # Project dependencies
├── AGENTS.md           # AI agent development guidelines
└── README.md           # This file
```

## Data Schema

The `QR_codes/code.csv` file contains:

| Column              | Description                       |
| ------------------- | --------------------------------- |
| `UUID`              | Unique 24-char alphanumeric code  |
| `ManufacturingDate` | ISO format date (YYYY-MM-DD)      |
| `ExpirationDate`    | Manufacturing date + 3 years      |
| `Info`              | Random identifier (WORD-WORD-###) |
| `SoldDate`          | Date when product was sold        |
| `ScanCount`         | Number of times QR was scanned    |

## Dependencies

- `qrcode` - QR code generation
- `pillow` - Image processing
- `pyOpenSSL` - SSL/cryptographic operations

## Requirements

- Python 3.11+
- uv package manager

## License

MIT
