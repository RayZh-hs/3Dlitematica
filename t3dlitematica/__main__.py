"""
3dLitematica - A tool to transform Litematica to 3D Obj
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .litematicadecoder import Resolve
from .objbuilder import LitimaticaToObj
from .texturepackexport import convert_texturepack


def is_litematic_file(filepath: str) -> bool:
    """Check if the file is a litematic file based on its extension."""
    return filepath.endswith(".litematic") or filepath.endswith(".litematica") or filepath.endswith(".schematic") or filepath.endswith(".schem")


def validate_file_exists(filepath: str, file_type: Optional[str] = None) -> Path:
    """Validate that a file exists."""
    if not os.path.exists(filepath):
        raise argparse.ArgumentTypeError(f"{filepath} does not exist.")

    if file_type == "litematic" and not is_litematic_file(filepath):
        raise argparse.ArgumentTypeError(f"{filepath} is not a litematica file.")
    elif file_type == "json" and not filepath.endswith(".json"):
        raise argparse.ArgumentTypeError(f"{filepath} is not a JSON file.")
    elif file_type == "litematic_or_json":
        if not (is_litematic_file(filepath) or filepath.endswith(".json")):
            raise argparse.ArgumentTypeError(
                f"{filepath} is not a litematica or JSON file."
            )
    elif file_type == "zippack" and not (
        filepath.endswith(".zip") or filepath.endswith(".json")
    ):
        raise argparse.ArgumentTypeError(f"{filepath} is not a zip or JSON file.")

    return Path(filepath).absolute()


def validate_litematic(filepath: str) -> Path:
    """Validate litematic file."""
    return validate_file_exists(filepath, "litematic")


def validate_litematic_or_json(filepath: str) -> Path:
    """Validate litematic or JSON file."""
    return validate_file_exists(filepath, "litematic_or_json")


def validate_zippack_or_json(filepath: str) -> Path:
    """Validate zip or JSON file for texture packs."""
    return validate_file_exists(filepath, "zippack")


def validate_directory(dirpath: str) -> Path:
    """Validate that a directory exists."""
    if not os.path.isdir(dirpath):
        raise argparse.ArgumentTypeError(f"{dirpath} is not a directory or does not exist.")
    return Path(dirpath).absolute()


def cmd_texture(args: argparse.Namespace) -> None:
    """Process texture pack conversion."""
    if not args.input:
        print("Error: At least one input file is required for texture mode.", file=sys.stderr)
        sys.exit(1)

    # Validate input files
    input_files = []
    for input_file in args.input:
        try:
            validated = validate_zippack_or_json(input_file)
            input_files.append(validated)
        except argparse.ArgumentTypeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate output file
    if not args.output.endswith(".json"):
        print("Error: Output file must be a JSON file.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output).absolute()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.verbose:
        print(f"Converting {len(input_files)} texture pack(s) to JSON...")
        for input_file in input_files:
            print(f"  - {input_file}")
        print(f"Output: {output_path}")

    # Process texture packs
    try:
        temp_dir = output_path.parent / "temp_textures"

        def load_texture_data(input_file: Path) -> dict:
            """Load texture data from a .json or .zip file."""
            if input_file.suffix == ".zip":
                convert_texturepack(input_file, temp_dir, show_progress=True)
                with open(temp_dir / "output.json", "r", encoding="utf8") as f:
                    return json.load(f)
            else:
                with open(input_file, "r", encoding="utf8") as f:
                    return json.load(f)

        def merge_texture_data(base: dict, override: dict) -> dict:
            """Deep-merge two texture data dicts. Keys in override take precedence."""
            merged = dict(base)
            for key, value in override.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = {**merged[key], **value}
                else:
                    merged[key] = value
            return merged

        # Load first texture file to start
        combined_data = load_texture_data(input_files[0])

        # Merge additional files: left-most input takes precedence
        for input_file in input_files[1:]:
            additional_data = load_texture_data(input_file)
            # base=additional (lower priority), override=combined (higher priority)
            combined_data = merge_texture_data(additional_data, combined_data)

        # Write output
        with open(output_path, "w", encoding="utf8") as f:
            json.dump(combined_data, f, indent=4)

        if args.verbose:
            print(f"Successfully wrote texture data to {output_path}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_schematic(args: argparse.Namespace) -> None:
    """Process schematic conversion."""
    try:
        input_file = validate_litematic_or_json(args.input)
    except argparse.ArgumentTypeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output).absolute()
    output_ext = output_path.suffix.lower()

    # Validate output format
    if output_ext not in [".json", ".obj"]:
        print("Error: Output file must have .json or .obj extension.", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.verbose:
        print(f"Converting schematic: {input_file}")
        print(f"Output format: {output_ext[1:]}")
        if args.texture:
            print(f"Using texture: {args.texture}")

    try:
        # Load schematic
        if input_file.suffix in (".litematic", ".litematica"):
            schematic_data = Resolve(str(input_file), show_progress=True)
        else:
            with open(input_file, "r", encoding="utf8") as f:
                schematic_data = json.load(f)

        # Convert to output format
        if output_ext == ".json":
            with open(output_path, "w", encoding="utf8") as f:
                json.dump(schematic_data, f, indent=4)
            if args.verbose:
                print(f"Successfully wrote JSON to {output_path}")
        elif output_ext == ".obj":
            if not args.texture:
                print("Error: Texture file required for OBJ output (-t/--texture).", file=sys.stderr)
                sys.exit(1)
            try:
                texture_path = validate_litematic_or_json(args.texture)
            except argparse.ArgumentTypeError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

            # LitimaticaToObj expects a directory for `output`, not a file path.
            # It produces a zip archive containing the .obj, .mtl, and texture files.
            output_dir = str(output_path.parent)
            result = LitimaticaToObj(schematic_data, str(texture_path), output_dir, show_progress=True)
            # Rename the generated zip to match the user's desired output name
            generated_zip = str(result)
            desired_zip = str(output_path.with_suffix(".zip"))
            if os.path.abspath(generated_zip) != os.path.abspath(desired_zip):
                if os.path.exists(desired_zip):
                    os.remove(desired_zip)
                os.rename(generated_zip, desired_zip)
            if args.verbose:
                print(f"Successfully wrote OBJ archive to {desired_zip}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="3dLitematica",
        description="A tool to transform Litematica schematics to 3D OBJ files and process texture packs.",
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

    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    # Texture subcommand
    texture_parser = subparsers.add_parser(
        "texture",
        help="Convert texture packs to JSON format.",
    )
    texture_parser.add_argument(
        "-i",
        "--input",
        nargs="+",
        required=True,
        help="Input texture pack ZIP file(s) or JSON file(s). Left-most file takes precedence.",
    )
    texture_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output JSON file path.",
    )
    texture_parser.set_defaults(func=cmd_texture)

    # Schematic subcommand
    schematic_parser = subparsers.add_parser(
        "schematic",
        help="Convert Litematica schematics to JSON or OBJ format.",
    )
    schematic_parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input schematic file (.litematic, .litematica, or .json).",
    )
    schematic_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output file (.json or .obj).",
    )
    schematic_parser.add_argument(
        "-t",
        "--texture",
        help="Texture JSON file (required for OBJ output).",
    )
    schematic_parser.set_defaults(func=cmd_schematic)

    # Parse arguments
    args = parser.parse_args()

    # Execute the appropriate command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
