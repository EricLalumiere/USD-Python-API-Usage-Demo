#!/usr/bin/env python

# Simple USD Composer
# This script combines two USD scenes into one, preserving metadata,
# relationships, and variant sets. It reads two input .usda files,
# merges their contents, and writes the result to a new .usda file.
# It is intended to be run from the command line with three arguments:
# 1. The first source USD file (inputA)
# 2. The second source USD file (inputB)
# 3. The composed USD file to write out (output)
# It uses the USD Python API to handle the reading, writing, and
# manipulation of USD stages and prims.

# Requirements:
# - USD Python bindings installed
# - Python 3.x

# # Usage:
# python simple_composer.py inputA.usda inputB.usda output.usda



import argparse
from sitecustomize import new_prefix

from pxr import Usd, Sdf


def copy_metadata(src, dst):
    """
    Copy all authored metadata from src-prim to dst-prim.
    """
    custom_data_keys = ["comment", "documentation"]
    dst_keys = dst.GetAllMetadata().keys()
    for key, src_val in src.GetAllMetadata().items():
        if isinstance(src_val, Sdf.UnregisteredValue):
            src_val = src_val.value
        if key in custom_data_keys or key not in dst_keys:
            # Copy metadata if it's not already set on dst or is a comment
            dst.SetCustomDataByKey(key, src_val)
        else:
            dst.SetMetadata(key, src_val)


def copy_relationships(src, dst):
    """
    Copy all relationships (names & targets) from src-prim to dst-prim.
    """
    for rel in src.GetRelationships():
        new_rel = dst.CreateRelationship(rel.GetName())
        new_rel.SetTargets(rel.GetTargets())


def copy_variant_sets(src, dst):
    """
    Copy all variant sets. For each variant, we select it on both
    src and dst, then recursively copy children authored inside that variant.
    """
    src_var_sets = src.GetVariantSets()
    dstVSets = dst.GetVariantSets()

    # Copy variant sets _on this prim_
    for var_set_name in src_var_sets.GetNames():
        src_var_set = src_var_sets.GetVariantSet(var_set_name)
        dst_var_set = dstVSets.AddVariantSet(var_set_name)

        # Ensure all variants exist on dst
        dst_names = dst_var_set.GetVariantNames()
        for v in src_var_set.GetVariantNames():
            if v not in dst_names:
                dst_var_set.AddVariant(v)

        # Mirror the active selection
        sel = src_var_set.GetVariantSelection()
        if sel:
            src_var_set.SetVariantSelection(sel)
            dst_var_set.SetVariantSelection(sel)

        # Enter both edit contexts before recursing
        with src_var_set.GetVariantEditContext(), \
                dst_var_set.GetVariantEditContext():
            # Recurse on children _within this variant_
            for child in src.GetChildren():
                _copy_prim(child, dst.GetStage())


def _copy_prim(src_prim, dstStage):
    """
    Recursively copy a prim (and its subtree) from srcPrim's stage into dstStage
    at the same path, including type, metadata, relationships, variants, and children.
    """
    path = src_prim.GetPath()
    prim_type = src_prim.GetTypeName() or 'Xform'
    dst_prim = dstStage.DefinePrim(path, prim_type)

    # metadata + relationships
    copy_metadata(src_prim, dst_prim)
    copy_relationships(src_prim, dst_prim)

    # variants
    copy_variant_sets(src_prim, dst_prim)

    # children (outside variant edits)
    for child in src_prim.GetChildren():
        _copy_prim(child, dstStage)


def main():
    parser = argparse.ArgumentParser(
        description="Compose two USDA scenes into one, preserving metadata, relationships, and variants."
    )
    parser.add_argument("inputA",  help="first .usda scene")
    parser.add_argument("inputB",  help="second .usda scene")
    parser.add_argument("output", help="composed .usda to write out")
    args = parser.parse_args()

    # Create the output stage (overwrites if exists)
    out_stage = Usd.Stage.CreateNew(args.output)

    # Helper to open and copy every root-level prim
    def mergeFile(usda_path):
        stage = Usd.Stage.Open(usda_path)
        pseudo_root = stage.GetPseudoRoot()  # top of prim hierarchy
        for prim in pseudo_root.GetChildren():
            _copy_prim(prim, out_stage)

    # Merge both scenes
    mergeFile(args.inputA)
    mergeFile(args.inputB)

    # Save
    out_stage.GetRootLayer().Save()
    print(f"Composed {args.inputA} + {args.inputB} → {args.output}")


if __name__ == "__main__":
    main()
