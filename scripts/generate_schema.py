#!/usr/bin/env python3
"""Generate JSON schema from Pydantic models for YAML preset validation."""

import json
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from pypreset.models import PresetConfig


def main() -> None:
    """Generate and save the JSON schema for PresetConfig."""
    schema = PresetConfig.model_json_schema()
    
    # Add schema metadata
    schema["$schema"] = "http://json-schema.org/draft-07/schema#"
    schema["title"] = "PySetup CLI Preset Configuration"
    schema["description"] = "Schema for pypreset preset YAML files"
    
    output_path = Path(__file__).parent.parent / "schemas" / "preset.schema.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with output_path.open("w") as f:
        json.dump(schema, f, indent=2)
    
    print(f"Schema generated: {output_path}")


if __name__ == "__main__":
    main()
