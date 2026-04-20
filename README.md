# AsmBox API 🚀

**AsmBox API** is a high-performance "Emulation-as-a-Service" engine built with FastAPI. It provides a stateless, sandboxed virtual CPU that executes 16-bit 8086 assembly instructions over HTTP. 

Designed for EdTech platforms, coding challenges, and legacy system testing, AsmBox not only executes control flow, math, and bitwise logic, but returns deep telemetry—including a complete snapshot of hardware registers, stack memory, and CPU flags—while employing strict safeguards against infinite loops and register corruption.

## Features
- **Stateless Emulation:** Spins up a pristine, 64KB sandboxed Virtual CPU for every single request.
- **Deep Telemetry:** Returns the exact hexadecimal state of all 16-bit registers (AX, BX, CX, DX, SI, DI, BP, SP, IP), Hardware Flags (ZF, SF, CF, OF), and the Stack memory upon execution completion.
- **Control Flow & Subroutines:** Supports Labels, Conditional Jumps (`JE`, `JNE`, `JB`, `JL`), and Stack Subroutines (`CALL`, `RET`).
- **Infinite Loop Sandbox:** Automatically detects and safely aborts execution if an instruction limit is exceeded (e.g., from an accidental `JMP` infinite loop), ensuring server stability.
- **Register Corruption Detection:** Flags poorly written subroutines that clobber registers (mutate without restoring).
- **Stripe-like Interactive Documentation:** Powered by Scalar to provide a beautiful, dual-pane API reference out of the box.

## Installation

Ensure you have Python 3.9+ installed.

1. Clone the repository:
   ```bash
   git clone https://github.com/Prochienne/AsmBox-API.git
   cd AsmBox-API
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the API Locally

Start the uvicorn server:
```bash
uvicorn main:app --reload
```

Open your browser and navigate to **[http://localhost:8000/docs](http://localhost:8000/docs)** to view the interactive API reference and test the endpoints directly!

## Example Usage

**Endpoint:** `POST /api/v1/emulate/8086`

**Request Payload:**
```json
{
  "instructions": [
    "MOV AX, 0005",
    "PUSH AX",
    "MOV BX, 000A",
    "ADD AX, BX",
    "POP CX"
  ]
}
```

**Response:**
```json
{
  "registers": {
    "AX": "000F",
    "BX": "000A",
    "CX": "0005",
    "DX": "0000",
    "SI": "0000",
    "DI": "0000",
    "BP": "0000",
    "SP": "FFFE",
    "IP": "0005"
  },
  "cpu_flags": {
    "ZF": false,
    "SF": false,
    "CF": false,
    "OF": false
  },
  "stack_snapshot": [
    "0000"
  ],
  "output": [
    "05",
    "00"
  ],
  "flags": {
    "warnings": [
      "Register BX was clobbered (mutated but not restored).",
      "Register CX was clobbered (mutated but not restored)."
    ],
    "errors": [],
    "corruption_detected": true
  }
}
```

## Running Tests
To run the automated edge-case test suite:
```bash
python test_api.py
```
