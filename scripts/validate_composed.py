#!/usr/bin/env python

# Validate Composed USD Stage
# This script validates that a composed USD stage contains all prims, metadata,
# relationships, and variant sets from two source scenes.
# This script compares the prims in the composed stage against
# the prims in two source stages, ensuring that all expected data
# is present and correctly authored.

# This script is intended to be run from the command line with three arguments:
# 1. The first source USD file (inputA)
# 2. The second source USD file (inputB)
# 3. The composed USD file to validate (composed)

# It uses the USD Python API to handle the reading, writing, and
# manipulation of USD stages and prims.

# Requirements:
# - USD Python bindings installed
# - Python 3.x

# Usage:
# python validate_composed.py inputA.usda inputB.usda composed.usda


import sys
import argparse
from pxr import Usd

def validate_metadata(srcPrim, dstPrim, errors):
    """
    Compare all authored metadata on srcPrim vs dstPrim.
    """
    for key, srcVal in srcPrim.GetAllMetadata().items():
        dstVal = dstPrim.GetMetadata(key)
        if srcVal != dstVal:
            errors.append(f"Metadata mismatch at {srcPrim.GetPath()}: "
                          f"'{key}' src={srcVal} vs dst={dstVal}")

def validate_relationships(srcPrim, dstPrim, errors):
    """
    Compare relationship names and target lists.
    """
    srcRels = {r.GetName(): set(r.GetTargets())
               for r in srcPrim.GetRelationships()}
    dstRels = {r.GetName(): set(r.GetTargets())
               for r in dstPrim.GetRelationships()}

    # missing or mismatched
    for name, targets in srcRels.items():
        if name not in dstRels:
            errors.append(f"Missing relationship '{name}' at {srcPrim.GetPath()}")
        elif dstRels[name] != targets:
            errors.append(f"Relationship targets differ at {srcPrim.GetPath()}: "
                          f"{name} src={targets} vs dst={dstRels[name]}")

    # any extra in dst?
    for name in dstRels.keys() - srcRels.keys():
        errors.append(f"Extra relationship '{name}' at {srcPrim.GetPath()} in composed")

def validate_variant_sets(srcPrim, dstPrim, errors):
    """
    Compare variant-set names, variant names, selections, and
    recursively validate contents for each variant.
    """
    srcVS = srcPrim.GetVariantSets()
    dstVS = dstPrim.GetVariantSets()

    srcNames = set(srcVS.GetNames())
    dstNames = set(dstVS.GetNames())

    for name in srcNames - dstNames:
        errors.append(f"Missing variant set '{name}' at {srcPrim.GetPath()}")
    for name in dstNames - srcNames:
        errors.append(f"Extra variant set '{name}' at {srcPrim.GetPath()}")

    for name in srcNames & dstNames:
        sV = srcVS.GetVariantSet(name)
        dV = dstVS.GetVariantSet(name)

        # variant name comparison
        sVars = set(sV.GetVariantNames())
        dVars = set(dV.GetVariantNames())
        for v in sVars - dVars:
            errors.append(f"Missing variant '{v}' in set '{name}' at {srcPrim.GetPath()}")
        for v in dVars - sVars:
            errors.append(f"Extra variant '{v}' in set '{name}' at {srcPrim.GetPath()}")

        # selection comparison
        selSrc = sV.GetVariantSelection()
        selDst = dV.GetVariantSelection()
        if selSrc != selDst:
            errors.append(f"Variant selection mismatch in '{name}' at {srcPrim.GetPath()}: "
                          f"src='{selSrc}' vs dst='{selDst}'")

        # dive into each variant for recursive validation
        for variant in sVars & dVars:
            sV.SetVariantSelection(variant)
            dV.SetVariantSelection(variant)
            for child in srcPrim.GetChildren():
                dstChild = dstPrim.GetChild(child.GetName())
                if not dstChild:
                    errors.append(f"Missing child '{child.GetName()}' under variant "
                                  f"'{variant}' at {srcPrim.GetPath()}")
                else:
                    validate_prim(child, dstChild, errors)

def validate_prim(srcPrim, dstPrim, errors):
    """
    Recursively validate a prim and its subtree for type, metadata,
    relationships, variants, and children.
    """
    if not dstPrim or not dstPrim.IsValid():
        errors.append(f"Missing prim: {srcPrim.GetPath()}")
        return

    # type name
    t1 = srcPrim.GetTypeName()
    t2 = dstPrim.GetTypeName()
    if t1 != t2:
        errors.append(f"Type mismatch at {srcPrim.GetPath()}: src={t1} vs dst={t2}")

    validate_metadata(srcPrim, dstPrim, errors)
    validate_relationships(srcPrim, dstPrim, errors)
    validate_variant_sets(srcPrim, dstPrim, errors)

    # default children
    for child in srcPrim.GetChildren():
        validate_prim(child, dstPrim.GetChild(child.GetName()), errors)

def main():
    parser = argparse.ArgumentParser(
        description="Validate that composed.usda contains all prims, metadata, "
                    "relationships, and variant sets from two source scenes."
    )
    parser.add_argument("inputA", help="first source .usda")
    parser.add_argument("inputB", help="second source .usda")
    parser.add_argument("composed", help="composed .usda to validate")
    args = parser.parse_args()

    # open stages
    try:
        stageA = Usd.Stage.Open(args.inputA)
        stageB = Usd.Stage.Open(args.inputB)
        stageC = Usd.Stage.Open(args.composed)
    except Exception as e:
        print("Failed to open USD stages:", e, file=sys.stderr)
        sys.exit(2)

    errors = []

    for label, stage in (("A", stageA), ("B", stageB)):
        pseudo = stage.GetPseudoRoot()
        for prim in pseudo.GetChildren():
            dstPrim = stageC.GetPrimAtPath(prim.GetPath())
            validate_prim(prim, dstPrim, errors)

    if errors:
        print("\nValidation FAILED with the following errors:\n")
        for err in errors:
            print(" -", err)
        sys.exit(1)
    else:
        print("\nValidation PASSED: composed USD contains all expected data.\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
