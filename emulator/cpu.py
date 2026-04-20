import re
from typing import List, Dict, Any

class VirtualCPU:
    def __init__(self):
        # 16-bit General Purpose, Index, and Pointer Registers
        self.registers = {
            "AX": 0, "BX": 0, "CX": 0, "DX": 0,
            "SI": 0, "DI": 0, "BP": 0, "SP": 0xFFFE,
            "IP": 0
        }
        # 16-bit Segment Registers
        self.segments = {
            "CS": 0x1000, "DS": 0x2000, "SS": 0x3000, "ES": 0x4000
        }
        
        # Hardware Flags
        self.cpu_flags = {
            "ZF": False, "SF": False, "CF": False, "OF": False
        }
        
        # 64KB Sandboxed Memory Buffer
        self.memory = bytearray(0x10000)
        
        self.instructions = []
        self.labels = {}
        self.output_hex = []
        self.flags = {
            "warnings": [],
            "errors": [],
            "corruption_detected": False
        }
        
        # Snapshot for Corruption Tracking
        self._initial_registers = {}

    def load(self, instructions: List[str]):
        """Lint and load instructions, resolving labels for jumps."""
        self.instructions = []
        self.labels = {}
        idx = 0
        
        for instr in instructions:
            instr = instr.strip().upper()
            if not instr:
                continue
            
            # Check for label
            if ":" in instr:
                parts = instr.split(":", 1)
                label = parts[0].strip()
                self.labels[label] = idx
                instr_part = parts[1].strip()
                if instr_part:
                    self.instructions.append(instr_part)
                    idx += 1
            else:
                self.instructions.append(instr)
                idx += 1
                
        if not self.instructions and not self.labels:
            raise ValueError("No instructions provided.")

    def run(self):
        """Main execution loop with sandboxing constraints."""
        self._initial_registers = self.registers.copy()
        instruction_count = 0
        MAX_INSTRUCTIONS = 10000 # @security-auditor: Prevent infinite loops
        
        self.registers["IP"] = 0
        
        while self.registers["IP"] < len(self.instructions):
            if instruction_count >= MAX_INSTRUCTIONS:
                self.flags["errors"].append("Execution aborted: Instruction limit reached (infinite loop protection).")
                break
            
            instr = self.instructions[self.registers["IP"]]
            self.registers["IP"] += 1
            
            try:
                self._execute_single(instr)
            except Exception as e:
                self.flags["errors"].append(f"Runtime error at '{instr}': {str(e)}")
                break
                
            instruction_count += 1

        self._check_register_corruption()

    def _execute_single(self, instr: str):
        """Minimal Opcode Parser for MVP subset."""
        tokens = re.split(r'[\s,]+', instr)
        op = tokens[0]
        
        if op == "MOV":
            dest, src = tokens[1], tokens[2]
            val = self._get_value(src)
            self._set_register(dest, val)
        elif op == "ADD":
            dest, src = tokens[1], tokens[2]
            val1 = self._get_value(dest)
            val2 = self._get_value(src)
            res = val1 + val2
            self._set_register(dest, res & 0xFFFF)
            self._update_flags_add(val1, val2, res)
        elif op == "SUB":
            dest, src = tokens[1], tokens[2]
            val1 = self._get_value(dest)
            val2 = self._get_value(src)
            res = val1 - val2
            self._set_register(dest, res & 0xFFFF)
            self._update_flags_sub(val1, val2, res)
        elif op == "CMP":
            dest, src = tokens[1], tokens[2]
            val1 = self._get_value(dest)
            val2 = self._get_value(src)
            res = val1 - val2
            self._update_flags_sub(val1, val2, res)
        elif op == "AND":
            dest, src = tokens[1], tokens[2]
            res = self._get_value(dest) & self._get_value(src)
            self._set_register(dest, res & 0xFFFF)
            self._update_flags_logic(res)
        elif op == "OR":
            dest, src = tokens[1], tokens[2]
            res = self._get_value(dest) | self._get_value(src)
            self._set_register(dest, res & 0xFFFF)
            self._update_flags_logic(res)
        elif op == "XOR":
            dest, src = tokens[1], tokens[2]
            res = self._get_value(dest) ^ self._get_value(src)
            self._set_register(dest, res & 0xFFFF)
            self._update_flags_logic(res)
        elif op == "PUSH":
            val = self._get_value(tokens[1])
            self._push(val)
        elif op == "POP":
            val = self._pop()
            self._set_register(tokens[1], val)
        elif op == "CALL":
            label = tokens[1]
            if label not in self.labels:
                raise ValueError(f"Unknown label: {label}")
            self._push(self.registers["IP"])
            self.registers["IP"] = self.labels[label]
        elif op == "RET":
            self.registers["IP"] = self._pop()
        elif op == "JMP":
            self._jump(tokens[1])
        elif op in ("JE", "JZ"):
            if self.cpu_flags["ZF"]:
                self._jump(tokens[1])
        elif op in ("JNE", "JNZ"):
            if not self.cpu_flags["ZF"]:
                self._jump(tokens[1])
        elif op == "JB": # Jump if below (unsigned less than) -> CF=1
            if self.cpu_flags["CF"]:
                self._jump(tokens[1])
        elif op == "JL": # Jump if less (signed) -> SF != OF
            if self.cpu_flags["SF"] != self.cpu_flags["OF"]:
                self._jump(tokens[1])
        elif op == "INT":
            self.flags["warnings"].append(f"Interrupts ({tokens[1]}) are stubbed out and ignored.")
        else:
            raise ValueError(f"Unsupported instruction: {op}")

    def _jump(self, label: str):
        if label in self.labels:
            self.registers["IP"] = self.labels[label]
        else:
            raise ValueError(f"Unknown label: {label}")

    def _update_flags_add(self, v1: int, v2: int, res: int):
        self.cpu_flags["ZF"] = (res & 0xFFFF) == 0
        self.cpu_flags["SF"] = (res & 0x8000) != 0
        self.cpu_flags["CF"] = res > 0xFFFF
        # OF is set if two numbers of same sign yield result of opposite sign
        v1_sign = (v1 & 0x8000) != 0
        v2_sign = (v2 & 0x8000) != 0
        res_sign = (res & 0x8000) != 0
        self.cpu_flags["OF"] = (v1_sign == v2_sign) and (v1_sign != res_sign)

    def _update_flags_sub(self, v1: int, v2: int, res: int):
        self.cpu_flags["ZF"] = (res & 0xFFFF) == 0
        self.cpu_flags["SF"] = (res & 0x8000) != 0
        self.cpu_flags["CF"] = v1 < v2  # borrow
        v1_sign = (v1 & 0x8000) != 0
        v2_sign = (v2 & 0x8000) != 0
        res_sign = (res & 0x8000) != 0
        # OF is set if signs of operands differ and sign of result matches subtrahend
        self.cpu_flags["OF"] = (v1_sign != v2_sign) and (v1_sign != res_sign)
        
    def _update_flags_logic(self, res: int):
        self.cpu_flags["ZF"] = (res & 0xFFFF) == 0
        self.cpu_flags["SF"] = (res & 0x8000) != 0
        self.cpu_flags["CF"] = False
        self.cpu_flags["OF"] = False

    def _get_value(self, operand: str) -> int:
        """Resolve an operand to its 16-bit integer value."""
        if operand in self.registers:
            return self.registers[operand]
        try:
            return int(operand, 16)
        except ValueError:
            raise ValueError(f"Invalid operand: {operand}")

    def _set_register(self, reg: str, value: int):
        """Safely set a register with 16-bit truncation."""
        if reg in self.registers:
            self.registers[reg] = value & 0xFFFF
        else:
            raise ValueError(f"Invalid destination register: {reg}")

    def _physical_address(self, segment: int, offset: int) -> int:
        return ((segment << 4) + offset) & 0xFFFF

    def _push(self, value: int):
        self.registers["SP"] = (self.registers["SP"] - 2) & 0xFFFF
        addr = self._physical_address(self.segments["SS"], self.registers["SP"])
        self.memory[addr] = value & 0xFF
        self.memory[addr + 1] = (value >> 8) & 0xFF
        self.output_hex.append(f"{value & 0xFF:02X}")
        self.output_hex.append(f"{(value >> 8) & 0xFF:02X}")

    def _pop(self) -> int:
        addr = self._physical_address(self.segments["SS"], self.registers["SP"])
        low_byte = self.memory[addr]
        high_byte = self.memory[addr + 1]
        value = (high_byte << 8) | low_byte
        self.registers["SP"] = (self.registers["SP"] + 2) & 0xFFFF
        return value

    def _check_register_corruption(self):
        for reg in ["BX", "CX", "DX", "SI", "DI", "BP"]:
            if self.registers[reg] != self._initial_registers[reg]:
                self.flags["corruption_detected"] = True
                self.flags["warnings"].append(f"Register {reg} was clobbered (mutated but not restored).")

    def get_telemetry(self) -> Dict[str, Any]:
        reg_hex = {k: f"{v:04X}" for k, v in self.registers.items()}
        sp = self.registers["SP"]
        stack_snapshot = []
        for i in range(sp, min(sp + 8, 0xFFFF), 2):
            addr = self._physical_address(self.segments["SS"], i)
            val = (self.memory[addr + 1] << 8) | self.memory[addr]
            stack_snapshot.append(f"{val:04X}")

        # Add IP and cpu_flags to the telemetry
        return {
            "registers": reg_hex,
            "cpu_flags": self.cpu_flags,
            "stack_snapshot": stack_snapshot,
            "output": self.output_hex,
            "flags": self.flags
        }
