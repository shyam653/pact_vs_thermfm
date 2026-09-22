#!/usr/bin/env python3
"""Validate this exact DualRocketConfig and generate isolated synthesis inputs."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
PREFIX = "chipyard.harness.TestHarness.DualRocketConfig"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def git_head(path):
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def port_shape(depth, width, ports, granularity):
    shape = {
        "RW0_addr": ("input", depth.bit_length() - 1),
        "RW0_clk": ("input", 1), "RW0_wdata": ("input", width),
        "RW0_rdata": ("output", width), "RW0_en": ("input", 1),
        "RW0_wmode": ("input", 1),
    }
    if ports == "mrw":
        shape["RW0_wmask"] = ("input", width // granularity)
    return shape


def validate_interface(source, name, expected):
    # Deliberately accept only the generated ANSI literal-width port grammar.
    # A changed generator syntax fails closed instead of guessing its meaning.
    matches = re.findall(r"^module\s+" + re.escape(name) + r"\s*\((.*?)\);",
                         source, re.MULTILINE | re.DOTALL)
    require(len(matches) == 1, f"Expected exactly one generated interface: {name}")
    actual = {}
    for declaration in matches[0].split(","):
        match = re.fullmatch(r"\s*(input|output)\s+(?:\[(\d+):0\]\s+)?(\w+)\s*",
                             declaration)
        require(match is not None, f"Unrecognized generated port in {name}: {declaration}")
        direction, msb, port = match.groups()
        require(port not in actual, f"Duplicate port in {name}: {port}")
        actual[port] = (direction, int(msb) + 1 if msb is not None else 1)
    require(actual == expected, f"Generated interface width/direction changed: {name}")


def memory_inputs(generated, rtl):
    spec = json.loads((HERE / "macro-map/inventory-spec.json").read_text())
    conf_path = generated / f"{PREFIX}.top.mems.conf"
    hierarchy_path = generated / "top_module_hierarchy.json"
    original_path = rtl / f"{PREFIX}.top.mems.v"
    original = original_path.read_text()
    hierarchy = json.loads(hierarchy_path.read_text())
    require(hierarchy["module_name"] == "ChipTop", "Hierarchy must describe full ChipTop")
    counts = Counter()

    def walk(node):
        counts[node["module_name"]] += 1
        for child in node["instances"]:
            walk(child)

    walk(hierarchy)
    records = {}
    for line in conf_path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        require(len(fields) % 2 == 0, "Malformed top.mems.conf record")
        record = dict(zip(fields[::2], fields[1::2]))
        require(len(record) * 2 == len(fields), "Duplicate top.mems.conf keys")
        name = record["name"]
        require(name not in records, f"Duplicate memory metadata: {name}")
        records[name] = record
    require(set(records) == set(spec), "Memory metadata module inventory changed")
    memories, wrappers = [], [(HERE / "macro-map/chipyard_sram_1rw.v").read_text()]
    gold = original
    for name, (depth, width, ports, granularity, instances) in spec.items():
        record = records[name]
        require((int(record["depth"]), int(record["width"]), record["ports"],
                 int(record.get("mask_gran", width))) == (depth, width, ports, granularity),
                f"Memory geometry changed: {name}")
        require(counts[name] == instances, f"Memory hierarchy instance count changed: {name}")
        require(depth > 0 and depth & (depth - 1) == 0 and width % granularity == 0,
                f"Unsupported geometry: {name}")
        shape = port_shape(depth, width, ports, granularity)
        validate_interface(original, name, shape)
        declarations = [f"    {direction} " + (f"[{bits-1}:0] " if bits > 1 else "") + port
                        for port, (direction, bits) in shape.items()]
        wrapper = f"module {name} (\n" + ",\n".join(declarations) + "\n);\n"
        if ports == "rw":
            wrapper += "    wire RW0_wmask = 1'b1;\n"
        wrapper += (f"    chipyard_sram_1rw #(.ABITS({depth.bit_length()-1}), "
                    f".WIDTH({width}), .MASK_BITS({width//granularity})) ram (.*);\nendmodule\n")
        wrappers.append(wrapper)
        gold, replaced = re.subn(r"^module\s+" + re.escape(name) + r"(?=\s*\()",
                                 f"module gold_{name}", gold, flags=re.MULTILINE)
        require(replaced == 1, f"Cannot prepare original golden model: {name}")
        macros_each = ((depth + 511) // 512) * ((width + 63) // 64)
        memories.append({"module": name, "depth": depth, "width": width, "ports": ports,
                         "mask_granularity": granularity, "mask_bits": width // granularity,
                         "instances": instances, "macros_per_instance": macros_each,
                         "total_macros": macros_each * instances,
                         "logical_bits": depth * width * instances})
    restored = gold
    for name in spec:
        restored = restored.replace(f"module gold_{name}", f"module {name}")
    require(restored == original, "Golden model differs beyond module renaming")
    inventory = {"configuration": "DualRocketConfig", "top": "ChipTop",
                 "macro": "fakeram45_512x64", "memories": memories,
                 "memory_instances": sum(m["instances"] for m in memories),
                 "logical_bits": sum(m["logical_bits"] for m in memories),
                 "physical_macro_instances": sum(m["total_macros"] for m in memories)}
    inventory["physical_capacity_bits"] = inventory["physical_macro_instances"] * 512 * 64
    require((inventory["memory_instances"], inventory["logical_bits"],
             inventory["physical_macro_instances"]) == (16, 5958656, 194),
            "Unexpected aggregate SRAM inventory")
    return inventory, "\n".join(wrappers), gold, [conf_path, hierarchy_path, original_path]


def render(template, values):
    # read_slang retains literal quotes in .ys filenames. Use controlled relative
    # aliases; filesystem symlinks carry real input paths, including whitespace.
    def replace(match):
        value = str(values[match[1]]) + (match[2] or "")
        require(re.fullmatch(r"[A-Za-z0-9_./+-]+", value), "Unsafe Yosys alias or plugin name")
        return value
    result = re.sub(r"@([A-Z_]+)@(/[^\s]+)?", replace, template)
    require(re.search(r"@[A-Z_]+@", result) is None, "Unexpanded Yosys template")
    return result


def main():
    chipyard = Path(os.environ["CHIPYARD_ROOT"]).resolve(strict=True)
    generated = Path(os.environ["GENERATED_DIR"]).resolve(strict=True)
    rtl = Path(os.environ["RTL_DIR"]).resolve(strict=True)
    platform = Path(os.environ["PLATFORM_ROOT"]).resolve(strict=True)
    output = Path(os.environ["OUTPUT_ROOT"]).resolve()
    require(not output.exists(), f"Refusing to overwrite existing output directory: {output}")
    platform_files = [platform / relative for relative in (
        "lib/NangateOpenCellLibrary_typical.lib", "lib/fakeram45_512x64.lib",
        "lef/NangateOpenCellLibrary.tech.lef", "lef/NangateOpenCellLibrary.macro.lef",
        "lef/fakeram45_512x64.lef")]
    for path in platform_files + [rtl / "ChipTop.sv"]:
        require(path.is_file(), f"Missing required input: {path}")
    inventory, wrappers, gold, metadata = memory_inputs(generated, rtl)
    plugin = Path(os.environ["SLANG_PLUGIN"])
    aliases = {"rtl": rtl, "cell.lib": platform_files[0], "sram.lib": platform_files[1],
               "enabled-output-map.v": HERE / "enabled-output-map.v"}
    if plugin.is_file():
        aliases["slang.so"] = plugin.resolve(strict=True)
    values = {"SLANG_PLUGIN": "inputs/slang.so" if plugin.is_file() else os.environ["SLANG_PLUGIN"],
              "RTL_DIR": "inputs/rtl", "CHIP_TOP": "inputs/rtl/ChipTop.sv",
              "ORIGINAL_MEMORIES": f"inputs/rtl/{PREFIX}.top.mems.v",
              "OUT": ".", "SRAM_LIB": "inputs/sram.lib", "CELL_LIB": "inputs/cell.lib",
              "WRAPPERS": "macro-map/chipyard_sram_macros.v",
              "OUTPUT_MAP": "inputs/enabled-output-map.v"}
    stages = {name: render((HERE / f"{name}.ys.in").read_text(), values)
              for name in ("preflight", "elaborate", "prepare", "map", "finalize")}
    sources = sorted(set(rtl.glob("*.sv")) | set(rtl.glob("*.v")) |
                     set(rtl.glob("*.vh")) | set(rtl.glob("*.svh")))
    require(sources, "No generated RTL source files")
    scripts = sorted(path for path in HERE.rglob("*") if path.is_file()
                     and "__pycache__" not in path.parts)
    if plugin.is_file():
        scripts.append(plugin.resolve(strict=True))
    tools = {}
    for key in ("YOSYS", "OPENROAD", "IVERILOG", "VVP", "PYTHON"):
        path = Path(shutil.which(os.environ[key])).resolve(strict=True)
        tools[key] = {"path": str(path), "sha256": digest(path)}
    provenance = {"started_utc": datetime.now(timezone.utc).isoformat(),
                  "configuration": "DualRocketConfig", "top": "ChipTop",
                  "chipyard_commit": git_head(chipyard), "platform_commit": git_head(platform),
                  "tools": tools, "slang_plugin": os.environ["SLANG_PLUGIN"],
                  "inputs": [{"path": str(path), "sha256": digest(path)}
                             for path in sorted(set(sources + metadata + platform_files + scripts))]}
    output.mkdir(parents=True, exist_ok=False)
    (output / "macro-map").mkdir()
    (output / "inputs").mkdir()
    for name, target in aliases.items():
        (output / "inputs" / name).symlink_to(target, target_is_directory=target.is_dir())
    (output / "macro-map/inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    (output / "macro-map/chipyard_sram_macros.v").write_text(wrappers)
    (output / "macro-map/gold_mems.v").write_text(gold)
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    for name, contents in stages.items():
        (output / f"{name}.ys").write_text(contents)
    print("Prepared full ChipTop: seven SRAM interfaces, 16 instances, 194 physical macros")


if __name__ == "__main__":
    main()
