# SPDX-License-Identifier: Apache-2.0
"""Evidence-validator fault controls, independent of native runtime qualification."""

import json
from pathlib import Path
import tempfile
import unittest

from observer import analyze


class EvidenceControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sg-attempt-evidence-test-")
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        (self.out / "attempt-events").mkdir()
        (self.out / "attempt-calibration.private.json").write_text(
            json.dumps({"expected_abrupt_database_pid": 99,
                        "expected_logger_fault_pid": 98}))
        self.rows = {}

    def event(self, pid, event, *, origin="LAB", request=0, hook="recorder", verb="NONE",
              connection="-", rpc=0, result="OK", span=0, session="-", transaction="NONE"):
        rows = self.rows.setdefault(pid, [])
        row = [pid, len(rows) + 1, 1, event, span, 0, origin, request, hook, verb,
               connection, rpc, "-", result, session, transaction]
        rows.append(row)

    def result(self):
        for pid, rows in self.rows.items():
            (self.out / "attempt-events" / f"{pid}.tsv").write_text(
                "".join("\t".join(map(str, row)) + "\n" for row in rows))
        return analyze(self.out)

    def pair(self, *, client_opcode="OP_3", server_opcode="OP_3"):
        self.event(7, "CLIENT_RPC", origin="ADMIN", request=101,
                   connection="100:200", rpc=1, result=client_opcode)
        self.event(8, "SERVER_RPC", origin="SERVER", connection="100:200", rpc=1,
                   result=server_opcode)

    def test_exact_protocol_pair_and_route_survive_connection_reuse(self):
        self.pair()
        self.event(7, "CLIENT_RPC", origin="OBSERVER", request=102,
                   connection="100:200", rpc=2, result="OP_2")
        self.event(8, "SERVER_RPC", origin="SERVER", connection="100:200", rpc=2,
                   result="OP_2")
        value = self.result()
        self.assertEqual(value["matched_frame_origins"], {"ADMIN": 1, "OBSERVER": 1})
        self.assertEqual(value["protocol_opcode_mismatches"], [])

    def test_opcode_mismatch_cannot_attribute_an_Admin_write_to_observer(self):
        self.pair(client_opcode="OP_2", server_opcode="OP_3")
        self.event(8, "ROW", origin="SERVER", hook="CLIENT", verb="UPDATE",
                   connection="100:200", rpc=1, session="3", transaction="1:10")
        value = self.result()
        self.assertEqual(len(value["protocol_opcode_mismatches"]), 1)
        self.assertEqual(value["scoped_row_attempts"].get("ADMIN", {}), {})
        self.assertEqual(value["scoped_row_attempts"]["SERVER"], {"CLIENT": 1})
        self.assertFalse(value["bounded_calibration_gate_passed"])

    def test_server_parse_attempt_without_client_frame_remains_unattributed(self):
        self.event(8, "SERVER_RPC", origin="SERVER", connection="100:200", rpc=1,
                   result="OP_18")
        value = self.result()
        self.assertEqual(len(value["unmatched_server_frames"]), 1)
        self.assertFalse(value["bounded_calibration_gate_passed"])

    def test_duplicate_connection_ordinal_is_rejected(self):
        self.pair()
        self.event(7, "CLIENT_RPC", origin="OBSERVER", request=102,
                   connection="100:200", rpc=1, result="OP_2")
        value = self.result()
        self.assertTrue(value["duplicate_protocol_keys"])
        self.assertFalse(value["bounded_calibration_gate_passed"])

    def test_missing_entry_is_not_treated_as_successful_exit(self):
        self.event(7, "EXIT", span=9)
        self.assertEqual(self.result()["orphan_exits"], 1)

    def test_sequence_loss_and_incomplete_span_are_visible(self):
        self.event(7, "BOOT")
        self.event(7, "ENTER", span=10)
        self.rows[7][1][1] = 3
        value = self.result()
        self.assertEqual(len(value["per_process_event_sequence_gaps"]), 1)
        self.assertEqual(value["incomplete_spans"], 1)

    def test_request_must_remain_owned_through_close(self):
        self.event(7, "HTTP_ROUTE", origin="OBSERVER", request=101)
        self.assertFalse(self.result()["native_route_contexts_all_closed"])
        self.event(7, "HTTP_END", origin="OBSERVER", request=101)
        self.assertTrue(self.result()["native_route_contexts_all_closed"])

    def test_unknown_statement_cannot_be_cleared_by_zero_row_events(self):
        self.event(7, "CLIENT_RPC", origin="OBSERVER", request=101,
                   connection="100:200", rpc=1, result="OP_18")
        self.event(8, "SERVER_RPC", origin="SERVER", connection="100:200", rpc=1,
                   result="OP_18")
        self.event(8, "ENTER", origin="UNKNOWN", span=1, hook="org.h2.command.Parser.prepare",
                   verb="UNKNOWN", connection="100:200", rpc=1, session="3")
        value = self.result()
        self.assertEqual(value["scoped_server_entries"]["OBSERVER"]["mutating_or_unknown_entries"], 1)
        self.assertEqual(value["scoped_row_attempts"].get("OBSERVER", {}), {})
        self.assertFalse(value["bounded_calibration_gate_passed"])

    def test_client_attempt_without_server_receipt_is_retained(self):
        self.event(7, "CLIENT_RPC", origin="OBSERVER", request=101,
                   connection="100:200", rpc=1, result="OP_18")
        value = self.result()
        self.assertEqual(len(value["client_attempt_frames_without_server_receipt"]), 1)
        self.assertEqual(len(value["claimed_native_route_frames_without_server_receipt"]), 1)

    def test_conflicting_request_route_is_not_a_trusted_join(self):
        self.event(7, "HTTP_ROUTE", origin="OBSERVER", request=101)
        self.event(7, "HTTP_ROUTE", origin="ADMIN", request=101)
        self.assertTrue(self.result()["duplicate_protocol_keys"])

    def test_redaction_control_rejects_a_known_canary(self):
        self.event(7, "BOOT", hook="fixture_canary_value")
        self.result()
        value = analyze(self.out, protected_values=("fixture_canary_value",))
        self.assertTrue(value["redaction_probe_applied"])
        self.assertEqual(value["redaction_failure_records"], 1)
        self.assertFalse(value["bounded_calibration_gate_passed"])


if __name__ == "__main__":
    unittest.main()
