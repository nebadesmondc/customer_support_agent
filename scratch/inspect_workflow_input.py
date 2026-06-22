import inspect
from google.adk.workflow import Workflow, node
from google.adk.agents.context import Context

# Print the init signature of Workflow and node
print("Workflow __init__ signature:", inspect.signature(Workflow.__init__))
print("node signature:", inspect.signature(node))

# Let's inspect google.adk.workflow._workflow.Workflow's implementation file or search for how node inputs are resolved.
import google.adk.workflow._workflow as wf
with open(wf.__file__, "r", encoding="utf-8") as f:
    wf_code = f.read()

# Print lines where "run_async" or "edges" or "next" or similar are defined/used.
for i, line in enumerate(wf_code.splitlines()):
    if "async def run" in line or "def run_async" in line or "route" in line or "node_input" in line:
        print(f"Workflow:{i+1}: {line}")
