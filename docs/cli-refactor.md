# Refactored CLI

The new commandline interface infers what to do based on the extension name of the file(s) provided.

For simplicity, we remove the `texture` system and rely on lookup 

```
3dLitematica -i <input.schematic> -o <output.json>
3dLitematica -i <input.schematic> -o <output.obj> -t [input.zip ...]
```

- If the output file is a json, the schematic will be converted to a decoded json file. The `-t` flag is not needed.
- If the output file is an obj, the schematic will be converted to an obj file. The `-t` flag is required.

Other file formats will be rejected.

When multiple resource packs are provided, they are treated as a resource stack like in minecraft: The search order for each texture is from left to right, meaning that if a texture is defined in multiple input files, the one on the left will be used.

## Misc

Use the `--help` flag to get more information about the commands and their options.

```
3dLitematica --help
```

Use the `--version` flag to get the version of the CLI.

```
3dLitematica --version
```

Use the `--verbose` flag to get more detailed output.

```
3dLitematica --verbose -i <input.schematic> -o <output.obj> -t [input.zip ...]
```
