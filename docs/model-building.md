# Model Building

When 3dLitematica is used to convert a schematic to an obj file, it will follow these passes:

1. **Schematic Parsing**: The schematic file is read and parsed to extract block information.
2. **Texture Lookup**: Obtain a list of blocks the litematic requires. For each, search sequentially through the provided resource packs to find the json files that define the block's model and texture. The relevant json files are concentrated into `/temp/.cache/textures.json` and the texture files copied to `/temp/.cache/textures/`, maintaining the original directory structure to facilitate easy lookup.
3. **Model Building**: Using the block information and the json files, build a 3D model using the implemented algorithm. The model is exported as a zip containing the obj file and the textures, with the name specified by the user.
