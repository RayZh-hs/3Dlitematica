# Refactored CLI

The new commandline interface infers what to do based on the extension name of the file(s) provided.

## Texture Mode

```
3dLitematica texture -i [input.zip|json ...] -o <output.json>
```

Each input file is either a zip (minecraft resource pack) or a json file (texture json). The output file is a concentrated texture json file. The search order of the input files is from left to right, meaning that if a texture is defined in multiple input files, the one on the left will be used.

## Schematics Mode

```
3dLitematica schematic -i <input.schematic> -o <output.json>
3dLitematica schematic -i <input.schematic> -o <output.obj> -t <texture.json>
```

- If the output file is a json, the schematic will be converted to a decoded json file.
- If the output file is an obj, the schematic will be converted to an obj file.

Other file formats will be rejected.

## Misc

Use the `--help` flag to get more information about the commands and their options.

```
3dLitematica --help
3dLitematica texture --help
3dLitematica schematic --help
```

Use the `--version` flag to get the version of the CLI.

```
3dLitematica --version
```

Use the `--verbose` flag to get more detailed output.

```
3dLitematica --verbose texture -i [input.zip|json ...] -o <output.json>
```

The flag can be placed after `3dLitematica` or anywhere after the action keyword.