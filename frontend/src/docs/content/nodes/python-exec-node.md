# Python Exec

The **Python Exec** node runs inline Python code as part of a workflow. Use it to transform data, run calculations, or perform any logic that's easier to express in code than with other nodes.

## Overview

| Property | Value |
|----------|-------|
| Inputs | 1 |
| Outputs | 1 |
| Output | Result of the Python script |

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `label` | string | Node identifier (camelCase) |
| `inputExpression` | expression | Value passed to the script via stdin. Supports [expressions](../reference/expression-dsl.md). Defaults to `$input`. |
| `code` | string | Python code to execute. Read input from `sys.stdin`, write output to `stdout`. |
| `timeoutSeconds` | number | Maximum execution time in seconds. Defaults to `30`. |

## How it works

The resolved `inputExpression` is JSON-serialized and piped to the script's **stdin**. Your script reads it with `json.load(sys.stdin)` and writes its result to **stdout** as JSON.

```python
import json
import sys

data = json.load(sys.stdin)
# data is whatever inputExpression resolved to

result = data["value"] * 2
print(json.dumps({"result": result}))
```

The printed JSON becomes the node's output, accessible downstream as `$label.result` (or any key you print).

If the script prints a plain string instead of JSON, the output is wrapped as `{"result": "your string"}`.

## Example

Double a number passed from a previous node:

```json
{
  "type": "pythonExec",
  "data": {
    "label": "doubler",
    "inputExpression": "$start.number",
    "code": "import json, sys\nn = json.load(sys.stdin)\nprint(json.dumps({'value': n * 2}))",
    "timeoutSeconds": 30
  }
}
```

Downstream nodes reference the output as `$doubler.value`.

## Notes

- The script runs in an isolated subprocess; backend secrets are stripped from its environment.
- Standard library is available. Third-party packages are **not** pre-installed; use the [AI Agent](./agent-node.md) node with a Python tool if you need `pip` dependencies.
- Memory is capped at 512 MB.
- Use `print(..., file=sys.stderr)` for debug logging; stderr appears in the backend logs but does not affect the output.

## Related

- [Node Types](../reference/node-types.md) – Overview of all node types
- [Expression DSL](../reference/expression-dsl.md) – How to reference upstream node data
- [AI Agent](./agent-node.md) – For Python tools with pip dependencies
