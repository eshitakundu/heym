"""Unit tests for pythonExec node executor logic."""

import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("ENCRYPTION_KEY", "0" * 64)

from app.services.workflow_executor import WorkflowExecutor


def _make_executor(node_data: dict):
    """Build a minimal WorkflowExecutor with a single pythonExec node."""

    node_id = "node_py1"
    nodes = [{"id": node_id, "type": "pythonExec", "data": node_data}]
    return WorkflowExecutor(nodes=nodes, edges=[])


_MOCK_RESULT = MagicMock()
_MOCK_RESULT.generated_files = []
_MOCK_RESULT.hitl_request = None


class PythonExecNodeTests(unittest.TestCase):
    @patch("app.services.skill_python_executor.execute_skill_python")
    def test_basic_exec_returns_dict_output(self, mock_exec: MagicMock) -> None:
        """When script returns a dict, it becomes the node output directly."""
        _MOCK_RESULT.output = {"result": 42}
        mock_exec.return_value = _MOCK_RESULT

        executor = _make_executor(
            {
                "label": "pythonExec",
                "code": "import json, sys\ndata = json.load(sys.stdin)\nprint(json.dumps({'result': 42}))",
                "inputExpression": "$input",
                "timeoutSeconds": 30,
            }
        )
        result = executor.execute_node("node_py1", {"start": {"text": "hello"}})
        self.assertEqual(result.output["result"], 42)

    @patch("app.services.skill_python_executor.execute_skill_python")
    def test_non_dict_output_wrapped_in_result_key(self, mock_exec: MagicMock) -> None:
        """When script returns a non-dict (e.g. plain string), it is wrapped as {'result': ...}."""
        _MOCK_RESULT.output = "plain string"
        mock_exec.return_value = _MOCK_RESULT

        executor = _make_executor(
            {
                "label": "pythonExec",
                "code": "print('plain string')",
                "inputExpression": "$input",
                "timeoutSeconds": 30,
            }
        )
        result = executor.execute_node("node_py1", {"start": {"text": "hello"}})
        self.assertEqual(result.output["result"], "plain string")

    def test_empty_code_raises(self) -> None:
        """Empty or whitespace-only code raises ValueError before execution."""
        executor = _make_executor(
            {
                "label": "pythonExec",
                "code": "   ",
                "inputExpression": "$input",
                "timeoutSeconds": 30,
            }
        )
        result = executor.execute_node("node_py1", {"start": {"text": "hello"}})
        self.assertEqual(result.status, "error")

    @patch("app.services.skill_python_executor.execute_skill_python")
    def test_timeout_surfaces_as_node_error(self, mock_exec: MagicMock) -> None:
        """TimeoutError from executor becomes a node-level error, not an uncaught exception."""
        mock_exec.side_effect = TimeoutError("timed out")

        executor = _make_executor(
            {
                "label": "pythonExec",
                "code": "import time\ntime.sleep(999)",
                "inputExpression": "$input",
                "timeoutSeconds": 2,
            }
        )
        result = executor.execute_node("node_py1", {"start": {"text": "hello"}})
        self.assertEqual(result.status, "error")
        self.assertIn("timed out", result.error or "")

    @patch("app.services.skill_python_executor.execute_skill_python")
    def test_runtime_exception_surfaces_as_node_error(self, mock_exec: MagicMock) -> None:
        """Any exception from execute_skill_python becomes a node-level error."""
        mock_exec.side_effect = RuntimeError("syntax error")

        executor = _make_executor(
            {
                "label": "pythonExec",
                "code": "this is not python",
                "inputExpression": "$input",
                "timeoutSeconds": 30,
            }
        )
        result = executor.execute_node("node_py1", {"start": {"text": "hello"}})
        self.assertEqual(result.status, "error")

    @patch("app.services.skill_python_executor.execute_skill_python")
    def test_custom_timeout_passed_through(self, mock_exec: MagicMock) -> None:
        """timeoutSeconds from node_data is passed to execute_skill_python."""
        _MOCK_RESULT.output = {"ok": True}
        mock_exec.return_value = _MOCK_RESULT

        executor = _make_executor(
            {
                "label": "pythonExec",
                "code": "print('{\"ok\": true}')",
                "inputExpression": "$input",
                "timeoutSeconds": 10,
            }
        )
        executor.execute_node("node_py1", {"start": {"text": "hello"}})
        _, kwargs = mock_exec.call_args
        self.assertEqual(kwargs.get("timeout_seconds") or mock_exec.call_args[0][2], 10.0)

    @patch("app.services.skill_python_executor.execute_skill_python")
    def test_input_expression_resolved_and_sent(self, mock_exec: MagicMock) -> None:
        """inputExpression is resolved and serialized as the 'input' argument to the script."""
        _MOCK_RESULT.output = {"echoed": "hello"}
        mock_exec.return_value = _MOCK_RESULT

        executor = _make_executor(
            {
                "label": "pythonExec",
                "code": "import json,sys; d=json.load(sys.stdin); print(json.dumps({'echoed': d}))",
                "inputExpression": "$start.text",
                "timeoutSeconds": 30,
            }
        )
        executor.execute_node("node_py1", {"start": {"text": "hello"}})
        _, kwargs = mock_exec.call_args
        arguments = kwargs.get("arguments", {})
        self.assertTrue(mock_exec.called)
        self.assertIn("input", arguments)
        self.assertIn("hello", arguments["input"])
