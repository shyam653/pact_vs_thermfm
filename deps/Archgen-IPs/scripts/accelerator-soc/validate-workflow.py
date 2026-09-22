#!/usr/bin/env python3
"""Lightweight fail-closed checks for generated memory metadata handling."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("prepare", HERE / "synthesis/prepare.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
cell_spec = importlib.util.spec_from_file_location("cell_audit", HERE / "synthesis/cell_audit.py")
cell_audit = importlib.util.module_from_spec(cell_spec)
cell_spec.loader.exec_module(cell_audit)


class MemoryMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.generated = Path(self.temp.name)
        self.rtl = self.generated / "gen-collateral"
        self.rtl.mkdir()
        self.config = self.generated / f"{prepare.PREFIX}.top.mems.conf"
        self.config.write_text("name extra_fft_sram depth 512 width 64 ports rw\n")
        self.hierarchy = self.generated / "top_module_hierarchy.json"
        self.hierarchy.write_text(json.dumps({"module_name": "ChipTop", "instances": [
            {"module_name": "extra_fft_sram", "instances": []},
            {"module_name": "extra_fft_sram", "instances": []}]}))
        shape = prepare.port_shape(512, 64, "rw", 64)
        self.memory_source = self.rtl / f"{prepare.PREFIX}.top.mems.v"
        self.memory_source.write_text("module extra_fft_sram (\n" + ",\n".join(
            f"{direction} " + (f"[{bits-1}:0] " if bits > 1 else "") + name
            for name, (direction, bits) in shape.items()) + "\n);\nendmodule\n")

    def read(self):
        return prepare.memory_inputs(self.generated, self.rtl)

    def test_variable_inventory_and_instances(self):
        inventory, wrappers, golden, _ = self.read()
        self.assertEqual(inventory["physical_macro_instances"], 2)
        self.assertEqual(inventory["logical_bits"], 65536)
        self.assertIn("module extra_fft_sram", wrappers)
        self.assertIn("module gold_extra_fft_sram", golden)
        self.assertIn("gold_extra_fft_sram gold", prepare.render_testbench(inventory))

    def test_reject_independent_read_write_ports(self):
        self.config.write_text("name extra_fft_sram depth 512 width 64 ports read,write\n")
        with self.assertRaisesRegex(ValueError, "Unsupported memory ports"):
            self.read()

    def test_reject_changed_generated_interface(self):
        self.memory_source.write_text(self.memory_source.read_text().replace("[63:0]", "[31:0]"))
        with self.assertRaisesRegex(ValueError, "width/direction changed"):
            self.read()

    def test_reject_missing_hierarchy_instance(self):
        self.hierarchy.write_text('{"module_name":"ChipTop","instances":[]}')
        with self.assertRaisesRegex(ValueError, "missing hierarchy instances"):
            self.read()

    def test_reject_unmasked_port_with_mask_metadata(self):
        self.config.write_text("name extra_fft_sram depth 512 width 64 ports rw mask_gran 8\n")
        with self.assertRaisesRegex(ValueError, "Mask metadata"):
            self.read()


class CellAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.library = Path(self.temp.name) / "test.lib"
        self.library.write_text('library(test) { cell (AND2_X1) {} cell("fakeram45_512x64") {} }')

    def test_mapped_logic_and_explicit_generic_memory(self):
        self.assertEqual(cell_audit.validate_cells({"AND2_X1": 1, "$mem_v2": 1}, [self.library], True)["status"], "PASS")

    def test_reject_unresolved_accelerator_blackbox(self):
        with self.assertRaisesRegex(ValueError, "NV_NVDLA_missing"):
            cell_audit.validate_cells({"AND2_X1": 1, "NV_NVDLA_missing": 1}, [self.library], True)

    def test_reject_unmapped_logic_in_preserve_mode(self):
        with self.assertRaisesRegex(ValueError, "\\$add"):
            cell_audit.validate_cells({"$mem_v2": 1, "$add": 1}, [self.library], True)

    def test_reject_generic_memory_in_fully_mapped_mode(self):
        with self.assertRaisesRegex(ValueError, "\\$mem_v2"):
            cell_audit.validate_cells({"$mem_v2": 1}, [self.library], False)


if __name__ == "__main__":
    unittest.main()
