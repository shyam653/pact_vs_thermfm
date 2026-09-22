#!/usr/bin/env python3
"""Validate generated memory metadata and create isolated full-SoC synthesis inputs."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from source_plan import describe
CONFIG = os.environ.get("CONFIG", "")
PREFIX = f"chipyard.harness.TestHarness.{CONFIG}"


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
    require(records, "No generated SRAM metadata")
    spec = {}
    for name, record in records.items():
        require(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name), f"Unsafe memory module name: {name}")
        require(set(record) <= {"name", "depth", "width", "ports", "mask_gran"},
                f"Unsupported memory metadata keys: {name}")
        depth, width = int(record["depth"]), int(record["width"])
        ports, granularity = record["ports"], int(record.get("mask_gran", width))
        require(ports in {"rw", "mrw"}, f"Unsupported memory ports {ports}: {name}")
        require((ports == "mrw") == ("mask_gran" in record),
                f"Mask metadata does not match port kind: {name}")
        require(2 <= depth <= 2**31 and width > 0 and granularity > 0 and counts[name] > 0,
                f"Invalid geometry or missing hierarchy instances: {name}")
        spec[name] = (depth, width, ports, granularity, counts[name])
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
    inventory = {"configuration": CONFIG, "top": "ChipTop",
                 "macro": "fakeram45_512x64", "memories": memories,
                 "memory_instances": sum(m["instances"] for m in memories),
                 "logical_bits": sum(m["logical_bits"] for m in memories),
                 "physical_macro_instances": sum(m["total_macros"] for m in memories)}
    inventory["physical_capacity_bits"] = inventory["physical_macro_instances"] * 512 * 64
    return inventory, "\n".join(wrappers), gold, [conf_path, hierarchy_path, original_path]


def render(template, values):
    # read_slang retains literal quotes in .ys filenames. Use controlled relative
    # aliases; filesystem symlinks carry real input paths, including whitespace.
    def replace(match):
        if match[1] == "ABC_OPTIONS":
            value = values[match[1]]
            require(not match[2] and value in {"", " -script inputs/direct.abc"},
                    "Unsupported explicit ABC options")
            return value
        if match[1] == "EXTRA_SOURCES":
            value = values[match[1]]
            require(not match[2] and all(re.fullmatch(r"inputs/extra-\d+\.v", p) for p in value.split()),
                    "Unsafe bundled source alias")
            return value
        value = str(values[match[1]]) + (match[2] or "")
        require(re.fullmatch(r"[A-Za-z0-9_./+-]+", value), "Unsafe Yosys alias or plugin name")
        return value
    result = re.sub(r"@([A-Z_]+)@(/[^\s]+)?", replace, template)
    require(re.search(r"@[A-Z_]+@", result) is None, "Unexpanded Yosys template")
    return result


def render_testbench(inventory):
    """Instantiate and exercise every actual generated SRAM public interface."""
    branches, instances = [], []
    for kind, memory in enumerate(inventory["memories"]):
        name = memory["module"]
        shape = port_shape(memory["depth"], memory["width"], memory["ports"],
                           memory["mask_granularity"])
        connections = ", ".join(f".{port}({port})" for port in shape)
        golden = ", ".join(f".{port}({'expected' if port == 'RW0_rdata' else port})"
                           for port in shape)
        branches.append(f"        if (KIND == {kind}) begin\n"
                        f"            {name} dut ({connections});\n"
                        f"            gold_{name} gold ({golden});\n"
                        "        end")
        instances.append(f"    test_memory #({kind}, {memory['depth'].bit_length()-1}, "
                         f"{memory['width']}, {memory['mask_bits']}) m{kind} (done[{kind}]);")
    template = (HERE / "macro-map/test_sram.sv.in").read_text()
    return template.replace("    // @MEMORY_INSTANCES@", "    generate\n" +
                            "\n".join(branches) + "\n    endgenerate").replace(
        "    // @TEST_INSTANCES@", f"    wire [{len(instances)-1}:0] done;\n" + "\n".join(instances))


def main():
    mode = os.environ.get("SYNTHESIS_MODE", "mapped")
    require(mode in {"mapped", "preserve-memories"}, f"Unknown synthesis mode: {mode}")
    abc_mode = os.environ.get("ABC_MODE", "default")
    require(abc_mode in {"default", "direct"}, f"Unknown ABC mode: {abc_mode}")
    chipyard = Path(os.environ["CHIPYARD_ROOT"]).resolve(strict=True)
    generated = Path(os.environ["GENERATED_DIR"]).resolve(strict=True)
    rtl = generated / "gen-collateral"
    source_plan = describe(generated, CONFIG)
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
    if abc_mode == "direct":
        aliases["direct.abc"] = HERE / "direct.abc"
    if plugin.is_file():
        aliases["slang.so"] = plugin.resolve(strict=True)
    for index, path in enumerate(source_plan["extra_sources"]):
        aliases[f"extra-{index}.v"] = Path(path)
    values = {"MACRO_COUNT": inventory["physical_macro_instances"],
              "ABC_OPTIONS": " -script inputs/direct.abc" if abc_mode == "direct" else "",
              "PREFLIGHT_TOP": inventory["memories"][0]["module"],
              "EXTRA_SOURCES": " ".join(f"inputs/extra-{index}.v" for index in range(len(source_plan["extra_sources"]))),
              "SLANG_PLUGIN": "inputs/slang.so" if plugin.is_file() else os.environ["SLANG_PLUGIN"],
              "RTL_DIR": "inputs/rtl", "CHIP_TOP": "inputs/rtl/ChipTop.sv",
              "ORIGINAL_MEMORIES": f"inputs/rtl/{PREFIX}.top.mems.v",
              "OUT": ".", "SRAM_LIB": "inputs/sram.lib", "CELL_LIB": "inputs/cell.lib",
              "WRAPPERS": "macro-map/chipyard_sram_macros.v",
              "OUTPUT_MAP": "inputs/enabled-output-map.v"}
    stages = {name: render((HERE / (f"{name}-preserve.ys.in"
                                   if mode == "preserve-memories" and name in {"map", "finalize"}
                                   else f"{name}.ys.in")).read_text(), values)
              for name in ("preflight", "elaborate", "prepare", "map", "finalize")}
    sources = sorted(set(rtl.glob("*.sv")) | set(rtl.glob("*.v")) |
                     set(rtl.glob("*.vh")) | set(rtl.glob("*.svh")))
    require(sources, "No generated RTL source files")
    scripts = sorted(path for path in HERE.parent.rglob("*") if path.is_file()
                     and "__pycache__" not in path.parts)
    if plugin.is_file():
        scripts.append(plugin.resolve(strict=True))
    tools = {}
    for key in ("YOSYS", "OPENROAD", "IVERILOG", "VVP", "PYTHON"):
        path = Path(shutil.which(os.environ[key])).resolve(strict=True)
        tools[key] = {"path": str(path), "sha256": digest(path)}
    provenance = {"started_utc": datetime.now(timezone.utc).isoformat(),
                  "configuration": CONFIG, "top": "ChipTop",
                  "synthesis_mode": mode,
                  "frontend_cleanup": "opt_clean -purge before check -assert",
                  "stage_order": ["preflight", "prepare", "elaborate", "sram-simulation",
                                  "memory-audit", "map", "finalize", "physical-link-if-mapped", "summary"],
                  "abc_mode": abc_mode,
                  "abc_commands": ["strash", "&get -n", "&nf", "&put"] if abc_mode == "direct" else None,
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
    (output / "macro-map/test_sram.sv").write_text(render_testbench(inventory))
    (output / "source-plan.json").write_text(json.dumps(source_plan, indent=2) + "\n")
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    for name, contents in stages.items():
        (output / f"{name}.ys").write_text(contents)
    print(f"Prepared {CONFIG} ChipTop: {len(inventory['memories'])} SRAM interfaces, "
          f"{inventory['memory_instances']} instances, {inventory['physical_macro_instances']} physical macros")


if __name__ == "__main__":
    main()
