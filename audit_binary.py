import os
import re

catalog_dir = r"custom_components/electrolux"
files = [
    f for f in os.listdir(catalog_dir) if f.startswith("catalog_") and f.endswith(".py")
]

for fname in sorted(files):
    src = open(os.path.join(catalog_dir, fname), encoding="utf-8").read()
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if "BinarySensorDeviceClass" in line and "device_class=" in line:
            block_start = i
            for j in range(i, max(i - 60, 0), -1):
                if "ElectroluxDevice(" in lines[j]:
                    block_start = j
                    break
            block = "\n".join(lines[block_start : i + 1])
            vals = re.findall(r'"([A-Z_]+)": \{\}', block)
            if len(vals) > 2:
                key = "?"
                for j in range(block_start, max(block_start - 5, 0), -1):
                    m = re.search(r'"([^"]+)": ElectroluxDevice\(', lines[j])
                    if m:
                        key = m.group(1)
                        break
                print(f"{fname}: {key!r} -> {vals}")
