#!/usr/bin/env python3

# This script creates a randomized USD scene with various features.
# It uses the USD Python API to handle the creation and manipulation of USD stages and prims
# This script generates a randomized USD scene with:
# - Randomized cubes (position, size, color)
# - A mesh with a 'materialVariant' variant set
# - An animated camera (pans along X-axis)
# - Unique IDs to avoid duplicate scenes
# - Stage- and prim-level metadata

# Requirements:
# - USD Python bindings installed
# - Python 3.x

# Usage:
# python write_random_scene.py output.usda

#!/usr/bin/env python3

import os
import random
import uuid
import sys

from pxr import Usd, UsdGeom, UsdShade, Gf, Sdf

def write_usd(output_path):
    """
    Creates a USD scene with:
      - Randomized cubes (position, size, color)
      - A mesh with a 'materialVariant' variant set
      - An animated camera (pans along X-axis)
      - Unique IDs to avoid duplicate scenes
      - Stage- and prim-level metadata
    """
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # 1) Create the stage and set metadata
    stage = Usd.Stage.CreateNew(output_path)
    stage.SetStartTimeCode(1)
    stage.SetEndTimeCode(48)
    stage.SetMetadata('metersPerUnit', 0.01)
    root = stage.DefinePrim('/World', 'Xform')
    stage.SetDefaultPrim(root)

    root.SetMetadata(
        'comment',
        'A randomized demo scene with cubes, variants, and animation.'
    )

    # Unique suffix so no two files are identical
    uniq = uuid.uuid4().hex[:6]

    # 2) Random cubes
    for i in range(random.randint(4, 8)):
        name = f'Cube_{uniq}_{i}'
        cube = UsdGeom.Cube.Define(stage, f'/World/{name}')
        # size
        cube.CreateSizeAttr(random.uniform(0.5, 2.0))
        # translation
        t = Gf.Vec3d(
            random.uniform(-5, 5),
            random.uniform(0, 3),
            random.uniform(-5, 5)
        )
        cube.AddTranslateOp().Set(t)
        # color
        col = Gf.Vec3f(random.random(), random.random(), random.random())
        cube.GetDisplayColorAttr().Set([col])

    # 3) Mesh + materialVariant variant set
    mesh_path = f'/World/Mesh_{uniq}'
    mesh = UsdGeom.Mesh.Define(stage, mesh_path)
    mesh.CreatePointsAttr()  # stub geometry

    # CORRECT WAY: get the prim, then its VariantSets
    prim = mesh.GetPrim()
    vsets = prim.GetVariantSets()
    materialVariant = vsets.AddVariantSet('materialVariant')

    variants = ['Metal', 'Plastic', 'Glass']
    color_map = {
        'Metal':   Gf.Vec3f(0.7, 0.7, 0.7),
        'Plastic': Gf.Vec3f(0.1, 0.5, 0.1),
        'Glass':   Gf.Vec3f(0.1, 0.1, 0.5)
    }

    for var in variants:
        materialVariant.AddVariant(var)
        materialVariant.SetVariantSelection(var)

        # open both source and destination edit contexts
        with materialVariant.GetVariantEditContext():
            mat_path = f'/World/Material_{var}_{uniq}'
            material = UsdShade.Material.Define(stage, mat_path)

            shader = UsdShade.Shader.Define(stage, f'{mat_path}/{var}Shader')
            shader.CreateIdAttr('UsdPreviewSurface')
            shader.CreateInput('diffuseColor',
                               Sdf.ValueTypeNames.Color3f).Set(color_map[var])

            material.CreateSurfaceOutput().ConnectToSource(
                shader.ConnectableAPI(),
                'surface')
            # bind to mesh
            UsdShade.MaterialBindingAPI(mesh).Bind(material)

    # Randomly pick one variant to be active
    materialVariant.SetVariantSelection(random.choice(variants))

    # 4) Animated camera
    cam = UsdGeom.Camera.Define(stage, f'/World/Camera_{uniq}')
    cam.CreateFocalLengthAttr(random.uniform(30.0, 70.0))
    xform_op = cam.AddTranslateOp()
    for frame in range(int(stage.GetEndTimeCode()) + 1):
        t = frame / stage.GetEndTimeCode()
        x = Gf.Lerp(-10.0, 10.0, t)
        xform_op.Set(Gf.Vec3d(x, 5.0, 20.0), time=frame)

    # 5) Save
    stage.GetRootLayer().Save()
    print(f'Wrote USD scene to: {output_path}')


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python write_random_scene.py <output.usda>")
        sys.exit(1)
    write_usd(sys.argv[1])
