"""
3dLitematica - A tool to transform Litematica to 3D Obj
"""

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .litematicadecoder import Resolve
from .objbuilder import LitimaticaToObj
from .texturepackexport import TextureCacheBuilder

SCHEMATIC_EXTENSIONS = {".litematic", ".litematica", ".schematic", ".schem"}


def is_schematic_file(filepath: str) -> bool:
    """Check if the file is a schematic file based on its extension."""
    return Path(filepath).suffix.lower() in SCHEMATIC_EXTENSIONS


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="3dLitematica",
        description="A tool to transform Litematica schematics to 3D OBJ files.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output.",
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input schematic file (.litematic, .litematica, .schematic, .schem).",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output file (.json for decoded schematic, .obj for 3D model).",
    )

    parser.add_argument(
        "-t",
        "--texture",
        nargs="+",
        help="Resource pack ZIP file(s). Required for OBJ output. Left-most takes precedence.",
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input).absolute()
    if not input_path.exists():
        print(f"Error: {args.input} does not exist.", file=sys.stderr)
        sys.exit(1)
    if not is_schematic_file(str(input_path)):
        print(
            f"Error: {args.input} is not a supported schematic file.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Validate output format
    output_path = Path(args.output).absolute()
    output_ext = output_path.suffix.lower()
    if output_ext not in (".json", ".obj"):
        print("Error: Output file must have .json or .obj extension.", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Parse schematic
        if args.verbose:
            print(f"Parsing schematic: {input_path}")
        schematic_data = Resolve(str(input_path), show_progress=args.verbose)

        if output_ext == ".json":
            # Output decoded schematic as JSON (no textures needed)
            with open(output_path, "w", encoding="utf8") as f:
                json.dump(schematic_data, f, indent=4)
            if args.verbose:
                print(f"Successfully wrote JSON to {output_path}")

        elif output_ext == ".obj":
            if not args.texture:
                print(
                    "Error: Resource pack(s) required for OBJ output (-t).",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Validate texture packs
            texture_packs = []
            for tp in args.texture:
                tp_path = Path(tp).absolute()
                if not tp_path.exists():
                    print(f"Error: {tp} does not exist.", file=sys.stderr)
                    sys.exit(1)
                if tp_path.suffix.lower() != ".zip":
                    print(f"Error: {tp} is not a ZIP file.", file=sys.stderr)
                    sys.exit(1)
                texture_packs.append(tp_path)

            # Collect unique block names from schematic
            block_names: set[str] = set()
            for region in schematic_data["Regions"].values():
                for block in region["decode_BlockStates"]:
                    name = block["Name"].replace("minecraft:", "")
                    if name != "air":
                        block_names.add(name)

            if args.verbose:
                print(f"Found {len(block_names)} unique block types")

            # Step 2: Build texture cache (only needed blocks + their PNGs)
            cache_dir = Path("temp") / ".cache"
            if args.verbose:
                print(
                    f"Building texture cache from {len(texture_packs)} resource pack(s)..."
                )

            TextureCacheBuilder(
                block_names, texture_packs, cache_dir, show_progress=args.verbose
            )

            # Step 3: Build 3D model
            if args.verbose:
                print("Building 3D model...")

            output_dir = str(output_path.parent)
            result = LitimaticaToObj(
                schematic_data, str(cache_dir), output_dir, show_progress=args.verbose
            )

            # Rename generated zip to match user's desired output name
            generated_zip = str(result)
            desired_zip = str(output_path.with_suffix(".zip"))
            if os.path.abspath(generated_zip) != os.path.abspath(desired_zip):
                if os.path.exists(desired_zip):
                    os.remove(desired_zip)
                os.rename(generated_zip, desired_zip)

            if args.verbose:
                print(f"Successfully wrote OBJ archive to {desired_zip}")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
