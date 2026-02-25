"""
3dLitematica - A tool to transform Litematica schematics to 3D OBJ files.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("3dLitematica")
except PackageNotFoundError:
    __version__ = "unknown"

from t3dlitematica.litematicadecoder import Resolve
from t3dlitematica.objbuilder import LitimaticaToObj
from t3dlitematica.texturepackexport import TextureCacheBuilder

__all__ = ["Resolve", "LitimaticaToObj", "TextureCacheBuilder"]