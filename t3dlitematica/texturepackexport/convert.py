import copy
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Set, List, Optional

from alive_progress import alive_bar


class TextureCacheBuilder:
    """
    Builds a filtered texture cache from resource packs for a specific set of blocks.

    Outputs:
    - <cache_dir>/textures.json: Combined blockstate + model data for needed blocks only
    - <cache_dir>/textures/: PNG texture files maintaining original directory structure

    When multiple resource packs are provided, left-most takes precedence.
    """

    def __init__(
        self,
        block_names: Set[str],
        resource_packs: List[str | Path],
        cache_dir: str | Path,
        show_progress: bool = False,
    ):
        self.block_names = block_names
        self.resource_packs = [Path(p) for p in resource_packs]
        self.cache_dir = Path(cache_dir)
        self.show_progress = show_progress
        self.result: dict = {"models": {}}
        self.copied_textures: Set[str] = set()
        self._extracted_packs: List[tuple[Path, Optional[str]]] = []
        self.build()

    def build(self) -> None:
        """Build the texture cache: extract packs, resolve blocks, write output."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True)
        (self.cache_dir / "textures").mkdir()

        try:
            self._extract_packs()
            self._resolve_blocks()
            with open(self.cache_dir / "textures.json", "w", encoding="utf8") as f:
                json.dump(self.result, f, indent=4, ensure_ascii=False)
        finally:
            self._cleanup()

    def _extract_packs(self) -> None:
        """Extract each resource pack ZIP to a temp directory."""
        for pack_path in self.resource_packs:
            if pack_path.suffix == ".zip":
                tmpdir = tempfile.mkdtemp()
                with zipfile.ZipFile(pack_path, "r") as z:
                    z.extractall(tmpdir)
                mc_path = self._find_minecraft_path(tmpdir)
                self._extracted_packs.append((mc_path, tmpdir))
            else:
                raise ValueError(f"Unsupported resource pack format: {pack_path.suffix}")

    def _find_minecraft_path(self, base: str) -> Path:
        """Navigate to the assets/minecraft directory within an extracted pack."""
        path = Path(base)
        if (path / "assets").exists():
            return path / "assets" / "minecraft"
        # Some zips have a wrapper directory
        for child in path.iterdir():
            if child.is_dir() and (child / "assets").exists():
                return child / "assets" / "minecraft"
        raise FileNotFoundError(f"Cannot find assets/minecraft in {base}")

    def _resolve_blocks(self) -> None:
        """Resolve blockstate + models for each needed block."""
        blocks = sorted(self.block_names)
        if self.show_progress:
            with alive_bar(len(blocks), title="Resolving blocks") as bar:
                for block_name in blocks:
                    self._resolve_block(block_name)
                    bar()
        else:
            for block_name in blocks:
                self._resolve_block(block_name)

    def _resolve_block(self, block_name: str) -> None:
        """Find blockstate for a block from the first available pack (left-to-right priority)."""
        for mc_path, _ in self._extracted_packs:
            blockstate_file = mc_path / "blockstates" / f"{block_name}.json"
            if not blockstate_file.exists():
                continue

            with open(blockstate_file, "r", encoding="utf8") as f:
                blockstate = json.load(f)

            # Resolve all referenced models
            model_refs = self._extract_model_refs(blockstate)
            for model_ref in model_refs:
                self._resolve_model(model_ref)

            # Shorten model paths in blockstate for lookup
            self._shorten_model_refs(blockstate)
            self.result[block_name] = blockstate
            return  # Found in this pack, stop searching

    def _extract_model_refs(self, blockstate: dict) -> Set[str]:
        """Collect all model references from a blockstate definition."""
        refs: Set[str] = set()
        if "variants" in blockstate:
            for variant in blockstate["variants"].values():
                if isinstance(variant, dict):
                    refs.add(variant["model"])
                elif isinstance(variant, list):
                    for v in variant:
                        refs.add(v["model"])
        if "multipart" in blockstate:
            for part in blockstate["multipart"]:
                apply_data = part["apply"]
                if isinstance(apply_data, dict):
                    refs.add(apply_data["model"])
                elif isinstance(apply_data, list):
                    for a in apply_data:
                        refs.add(a["model"])
        return refs

    def _resolve_model(self, model_ref: str) -> None:
        """Resolve a model and its parent chain, copying referenced textures."""
        model_path = model_ref.split(":")[-1]  # Remove "minecraft:" prefix
        short_name = model_path.split("/")[-1]  # Just the filename without path

        if short_name in self.result["models"]:
            return  # Already resolved

        for mc_path, _ in self._extracted_packs:
            model_file = mc_path / "models" / f"{model_path}.json"
            if not model_file.exists():
                continue

            with open(model_file, "r", encoding="utf8") as f:
                raw_data = f.read()
                model_data = json.loads(raw_data)

            # Recursively resolve parent model first
            if "parent" in model_data:
                self._resolve_model(model_data["parent"])

            # Strip "minecraft:" prefixes from all references
            cleaned = json.loads(raw_data.replace("minecraft:", ""))

            # Copy referenced texture PNGs
            if "textures" in cleaned:
                for tex_ref in cleaned["textures"].values():
                    if not tex_ref.startswith("#"):
                        self._copy_texture(tex_ref)

            # Special handling for sculk_sensor UV
            if short_name == "sculk_sensor" and "elements" in cleaned:
                for elem in cleaned["elements"]:
                    for face in ["north", "east", "south", "west"]:
                        if face in elem.get("faces", {}):
                            elem["faces"][face]["uv"] = [0, 0, 16, 8]

            self.result["models"][short_name] = cleaned
            return  # Found in this pack

    def _copy_texture(self, tex_ref: str) -> None:
        """Copy a texture PNG from the first pack that has it, maintaining directory structure."""
        if tex_ref in self.copied_textures:
            return

        for mc_path, _ in self._extracted_packs:
            tex_file = mc_path / "textures" / f"{tex_ref}.png"
            if tex_file.exists():
                dest = self.cache_dir / "textures" / f"{tex_ref}.png"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(tex_file, dest)
                self.copied_textures.add(tex_ref)
                return

    def _shorten_model_refs(self, blockstate: dict) -> None:
        """Replace full model paths with short names in blockstate data."""
        if "variants" in blockstate:
            for key in blockstate["variants"]:
                variant = blockstate["variants"][key]
                if isinstance(variant, dict):
                    variant["model"] = variant["model"].split("/")[-1]
                elif isinstance(variant, list):
                    for v in variant:
                        v["model"] = v["model"].split("/")[-1]
        if "multipart" in blockstate:
            for part in blockstate["multipart"]:
                apply_data = part["apply"]
                if isinstance(apply_data, dict):
                    apply_data["model"] = apply_data["model"].split("/")[-1]
                elif isinstance(apply_data, list):
                    for a in apply_data:
                        a["model"] = a["model"].split("/")[-1]

    def _cleanup(self) -> None:
        """Remove temporary extracted pack directories."""
        for _, tmpdir in self._extracted_packs:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
