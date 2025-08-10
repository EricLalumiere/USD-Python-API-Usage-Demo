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
from pxr import Usd, Sdf


def copy_metadata(src, dst):
    """
    Copy all authored metadata from src-prim to dst-prim.
    """
    dst_keys = dst.GetAllMetadata().keys()
    for key, srcVal in src.GetAllMetadata().items():
        if key == "comment" or key not in dst_keys:
            # Copy metadata if it's not already set on dst or is a comment
            if isinstance(srcVal, Sdf.UnregisteredValue):
                srcVal = srcVal.value
            dst.SetCustomDataByKey(key, srcVal)
        else:
            dst.SetMetadata(key, srcVal)


def copy_relationships(src, dst):
    """
    Copy all relationships (names & targets) from src-prim to dst-prim.
    """
    for rel in src.GetRelationships():
        newRel = dst.CreateRelationship(rel.GetName())
        newRel.SetTargets(rel.GetTargets())


def copy_variant_sets(src, dst):
    """
    Copy all variant sets. For each variant, we select it on both
    src and dst, then recursively copy children authored inside that variant.
    """
    srcVSets = src.GetVariantSets()
    dstVSets = dst.GetVariantSets()

    # Copy variant sets _on this prim_
    for vsetName in srcVSets.GetNames():
        srcVSet = srcVSets.GetVariantSet(vsetName)
        dstVSet = dstVSets.AddVariantSet(vsetName)

        # Ensure all variants exist on dst
        dst_names = dstVSet.GetVariantNames()
        for v in srcVSet.GetVariantNames():
            if v not in dst_names:
                dstVSet.AddVariant(v)

        # Mirror the active selection
        sel = srcVSet.GetVariantSelection()
        if sel:
            srcVSet.SetVariantSelection(sel)
            dstVSet.SetVariantSelection(sel)

        # Enter both edit contexts before recursing
        with srcVSet.GetVariantEditContext(), \
                dstVSet.GetVariantEditContext():
            # Recurse on children _within this variant_
            for child in src.GetChildren():
                _copy_prim(child, dst.GetStage())


def _copy_prim(srcPrim, dstStage):
    """
    Recursively copy a prim (and its subtree) from srcPrim's stage into dstStage
    at the same path, including type, metadata, relationships, variants, and children.
    """
    path = srcPrim.GetPath()
    primType = srcPrim.GetTypeName() or 'Xform'
    dstPrim = dstStage.DefinePrim(path, primType)

    # metadata + relationships
    copy_metadata(srcPrim, dstPrim)
    copy_relationships(srcPrim, dstPrim)

    # variants
    copy_variant_sets(srcPrim, dstPrim)

    # children (outside variant edits)
    for child in srcPrim.GetChildren():
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
    outStage = Usd.Stage.CreateNew(args.output)

    # Helper to open and copy every root-level prim
    def mergeFile(usdaPath):
        stage = Usd.Stage.Open(usdaPath)
        pseudoRoot = stage.GetPseudoRoot()  # top of prim hierarchy
        for prim in pseudoRoot.GetChildren():
            _copy_prim(prim, outStage)

    # Merge both scenes
    mergeFile(args.inputA)
    mergeFile(args.inputB)

    # Save
    outStage.GetRootLayer().Save()
    print(f"Composed {args.inputA} + {args.inputB} → {args.output}")


if __name__ == "__main__":
    main()
