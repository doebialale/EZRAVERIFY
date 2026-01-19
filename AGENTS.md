# AGENTS Guidelines for EzraVerify

## Project Overview

EzraVerify is a product authenticity verification system that generates unique QR codes linked to UUIDs. Users scan QR codes to verify product authenticity via a web server.

### Architecture

```
EzraVerify/
├── code_generator.py   # Generates UUIDs, QR codes, and stores records
├── verifier.py         # HTTP server for QR code verification lookups
├── QR_codes/
│   ├── code.csv        # Database of all generated UUIDs and metadata
│   └── *.png           # Generated QR code images
└── pyproject.toml      # Project dependencies (managed by uv)
```

### Data Flow

1. `code_generator.py` creates a unique 24-character alphanumeric UUID
2. UUID + metadata (manufacturing date, expiration date, info) saved to `QR_codes/code.csv`
3. QR code image generated pointing to `{BASE_URL}/{UUID}` and saved as PNG
4. `verifier.py` serves HTTP requests and looks up UUIDs in the CSV to return VERIFIED/UNVERIFIED status

---

## Code Style & Conventions

### Naming Conventions

| Element   | Convention    | Example                          |
| --------- | ------------- | -------------------------------- |
| Functions | **camelCase** | `generateCode`, `loadRecords`    |
| Variables | snake_case    | `manufacturing_date`, `base_url` |
| Constants | UPPER_SNAKE   | `CODE_LENGTH`, `DB_PATH`         |
| Classes   | PascalCase    | `RequestHandler`                 |

### Type Hints

- All functions must include type hints for parameters and return types
- Use `dict[str, str]` style (Python 3.9+), not `Dict[str, str]`

```python
def loadExistingCodes(path: str) -> set[str]:
    ...
```

---

## Development Setup

### Package Manager

This project uses **uv** for dependency management. Do not use pip directly.

```bash
# Install dependencies
uv sync

# Add a new package
uv add <package>

# Remove a package
uv remove <package>
```

### Running the Application

```bash
# Generate a new QR code
uv run python code_generator.py

# Start the verification server (default: http://0.0.0.0:8000)
uv run python verifier.py
```

### Environment Variables

| Variable   | Description                  | Default                          |
| ---------- | ---------------------------- | -------------------------------- |
| `BASE_URL` | Base URL encoded in QR codes | `http://rhc6549.glddns.com:8000` |

---

## Key Implementation Details

### UUID Generation

- Length: 24 characters
- Character set: Uppercase letters (A-Z) + digits (0-9)
- Generated using `secrets` module for cryptographic randomness
- Uniqueness enforced by checking against existing codes in CSV

### CSV Schema (`QR_codes/code.csv`)

| Column              | Description                       |
| ------------------- | --------------------------------- |
| `UUID`              | Unique 24-char alphanumeric code  |
| `ManufacturingDate` | ISO format date (YYYY-MM-DD)      |
| `ExpirationDate`    | Manufacturing date + 3 years      |
| `Info`              | Random identifier (WORD-WORD-###) |

### Verification Server

- Runs on `0.0.0.0:8000` by default
- Endpoints:
  - `GET /` - Landing page
  - `GET /{UUID}` - Lookup and display verification status

---

## File Modification Guidelines

### When modifying `code_generator.py`:

- Ensure new UUIDs remain unique (check against existing codes)
- Maintain CSV header consistency with `verifier.py` expectations
- QR codes must point to valid verification URLs

### When modifying `verifier.py`:

- Handle missing/malformed CSV fields gracefully (use coalesce patterns)
- Keep HTML responses self-contained (inline CSS)
- Support legacy field names for backward compatibility

---

## Dependencies

Defined in `pyproject.toml`:

- `qrcode` - QR code generation
- `pyOpenSSL` - SSL/cryptographic operations

Standard library modules used:

- `secrets` - Cryptographic random generation
- `datetime` - Date handling
- `csv` - Database operations
- `http.server` - Web server

---

## Notes for AI Agents

- Always use `uv` commands for package management, never `pip`
- The `secrets` and `datetime` modules are part of Python's standard library—do not add them to dependencies
- Function names must use **camelCase** (e.g., `generateCode`, not `generate_code`)
- Preserve backward compatibility with existing CSV records when modifying schemas
