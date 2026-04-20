from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from emulator.cpu import VirtualCPU

# @api-design-principles: Clean, self-documenting REST API setup
app = FastAPI(
    title="AsmBox",
    description="Stateless 8086 Assembly Emulation API",
    version="1.0.0",
    docs_url=None
)

class EmulationRequest(BaseModel):
    instructions: List[str] = Field(
        ..., 
        example=["MOV AX, 0005", "PUSH AX", "MOV BX, 000A", "ADD AX, BX", "POP CX"],
        description="Array of valid TASM/8086 instructions."
    )

class EmulationResponse(BaseModel):
    registers: Dict[str, str]
    cpu_flags: Dict[str, bool]
    stack_snapshot: List[str]
    output: List[str]
    flags: Dict[str, Any]

@app.get("/docs", include_in_schema=False)
async def scalar_html():
    html_content = """
    <!doctype html>
    <html>
      <head>
        <title>AsmBox API Reference</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <script id="api-reference" data-url="/openapi.json"></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
      </body>
    </html>
    """
    return HTMLResponse(html_content)

@app.post("/api/v1/emulate/8086", response_model=EmulationResponse)
async def emulate_8086(payload: EmulationRequest):
    """
    Executes a sequence of 8086 assembly instructions statelessly.
    """
    # Instantiate an isolated, sandboxed CPU per request
    cpu = VirtualCPU()
    
    try:
        # Pre-validate and load instructions (@lint-and-validate)
        cpu.load(payload.instructions)
        
        # Execute the loaded instructions
        cpu.run()
        
        # Extract telemetry
        telemetry = cpu.get_telemetry()
        return EmulationResponse(**telemetry)
        
    except Exception as e:
        # @debugging-strategies: Return explicit error details
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
