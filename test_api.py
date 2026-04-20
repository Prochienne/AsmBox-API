import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_test(name, payload, expected_status=200, check_fn=None):
    print(f"--- Running Test: {name} ---")
    response = client.post("/api/v1/emulate/8086", json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code != expected_status:
        print(f"FAILED! Expected {expected_status}, got {response.status_code}")
        print(response.json())
        assert False
    
    if expected_status == 200 and check_fn:
        check_fn(response.json())
    elif expected_status != 200:
        print("Error Payload:", response.json())
    print("PASSED.\n")

def test_bitwise_operations():
    def check(data):
        assert data["registers"]["AX"] == "0005" # AND 000F, 0005
        assert data["registers"]["BX"] == "000F" # OR 000A, 0005
        assert data["registers"]["CX"] == "0000" # XOR 00FF, 00FF
    
    payload = {
        "instructions": [
            "MOV AX, 000F",
            "AND AX, 0005",
            "MOV BX, 000A",
            "OR BX, 0005",
            "MOV CX, 00FF",
            "XOR CX, 00FF"
        ]
    }
    run_test("Bitwise Operations", payload, 200, check)

def test_register_truncation():
    # Adding two large numbers should truncate to 16-bit and set CF
    def check(data):
        assert data["registers"]["AX"] == "0000" # FFFF + 1 = 10000 -> 0000
        assert data["cpu_flags"]["CF"] == True
        assert data["cpu_flags"]["ZF"] == True

    payload = {
        "instructions": [
            "MOV AX, FFFF",
            "ADD AX, 0001"
        ]
    }
    run_test("16-bit Truncation & Carry Flag", payload, 200, check)

def test_invalid_opcode():
    payload = {
        "instructions": [
            "MOV AX, 0001",
            "FAKE_OPCODE AX, BX"
        ]
    }
    # It logs as a runtime error inside the flags, status is still 200 because the payload was valid
    # Wait, our cpu.py raises ValueError for unsupported instructions. Let's see how it behaves.
    def check(data):
        errors = data["flags"]["errors"]
        assert len(errors) > 0
        assert "Unsupported instruction: FAKE_OPCODE" in errors[0]

    run_test("Invalid Opcode", payload, 200, check)

def test_jump_to_missing_label():
    payload = {
        "instructions": [
            "MOV AX, 0001",
            "JMP NONEXISTENT"
        ]
    }
    def check(data):
        errors = data["flags"]["errors"]
        assert len(errors) > 0
        assert "Unknown label: NONEXISTENT" in errors[0]

    run_test("Missing Label Jump", payload, 200, check)

def test_empty_instructions():
    payload = {
        "instructions": []
    }
    # FastAPI might reject this if we use constraints, or VirtualCPU load() raises ValueError
    # VirtualCPU.load raises ValueError("No instructions provided.") which main.py catches and returns 400
    run_test("Empty Instructions", payload, 400)

if __name__ == "__main__":
    test_bitwise_operations()
    test_register_truncation()
    test_invalid_opcode()
    test_jump_to_missing_label()
    test_empty_instructions()
    print("ALL TESTS PASSED!")
