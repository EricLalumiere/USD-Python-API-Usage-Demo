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

def validate_metadata(src_prim, dst_prim, errors):
    """
    Compare all authored metadata on srcPrim vs dstPrim.
    """
    for key, src_val in src_prim.GetAllMetadata().items():
        dst_val = dst_prim.GetMetadata(key)
        if src_val != dst_val:
            errors.append(f"Metadata mismatch at {src_prim.GetPath()}: "
                          f"'{key}' src={src_val} vs dst={dst_val}")


def validate_relationships(src_prim, dst_prim, errors):
    """
    Compare relationship names and target lists.
    """
    src_rels = {r.GetName(): set(r.GetTargets())
               for r in src_prim.GetRelationships()}
    dst_rels = {r.GetName(): set(r.GetTargets())
               for r in dst_prim.GetRelationships()}

    # missing or mismatched
    for name, targets in src_rels.items():
        if name not in dst_rels:
            errors.append(f"Missing relationship '{name}' at {src_prim.GetPath()}")
        elif dst_rels[name] != targets:
            errors.append(f"Relationship targets differ at {src_prim.GetPath()}: "
                          f"{name} src={targets} vs dst={dst_rels[name]}")

    # any extra in dst?
    for name in dst_rels.keys() - src_rels.keys():
        errors.append(f"Extra relationship '{name}' at {src_prim.GetPath()} in composed")


def validate_variant_sets(src_prim, dst_prim, errors):
    """
    Compare variant-set names, variant names, selections, and
    recursively validate contents for each variant.
    """
    src_var_sets = src_prim.GetVariantSets()
    dst_var_sets = dst_prim.GetVariantSets()

    src_names = set(src_var_sets.GetNames())
    dst_names = set(dst_var_sets.GetNames())

    for name in src_names - dst_names:
        errors.append(f"Missing variant set '{name}' at {src_prim.GetPath()}")
    for name in dst_names - src_names:
        errors.append(f"Extra variant set '{name}' at {src_prim.GetPath()}")

    for name in src_names & dst_names:
        src_var = src_var_sets.GetVariantSet(name)
        dst_var = dst_var_sets.GetVariantSet(name)

        # variant name comparison
        src_vars = set(src_var.GetVariantNames())
        dst_vars = set(dst_var.GetVariantNames())
        for v in src_vars - dst_vars:
            errors.append(f"Missing variant '{v}' in set '{name}' at {src_prim.GetPath()}")
        for v in dst_vars - src_vars:
            errors.append(f"Extra variant '{v}' in set '{name}' at {src_prim.GetPath()}")

        # selection comparison
        sel_src = src_var.GetVariantSelection()
        sel_dst = dst_var.GetVariantSelection()
        if sel_src != sel_dst:
            errors.append(f"Variant selection mismatch in '{name}' at {src_prim.GetPath()}: "
                          f"src='{sel_src}' vs dst='{sel_dst}'")

        # dive into each variant for recursive validation
        for variant in src_vars & dst_vars:
            src_var.SetVariantSelection(variant)
            dst_var.SetVariantSelection(variant)
            for child in src_prim.GetChildren():
                dst_child = dst_prim.GetChild(child.GetName())
                if not dst_child:
                    errors.append(f"Missing child '{child.GetName()}' under variant "
                                  f"'{variant}' at {src_prim.GetPath()}")
                else:
                    validate_prim(child, dst_child, errors)


def validate_prim(src_prim, dst_prim, errors):
    """
    Recursively validate a prim and its subtree for type, metadata,
    relationships, variants, and children.
    """
    if not dst_prim or not dst_prim.IsValid():
        errors.append(f"Missing prim: {src_prim.GetPath()}")
        return

    # type name
    t1 = src_prim.GetTypeName()
    t2 = dst_prim.GetTypeName()
    if t1 != t2:
        errors.append(f"Type mismatch at {src_prim.GetPath()}: src={t1} vs dst={t2}")

    validate_metadata(src_prim, dst_prim, errors)
    validate_relationships(src_prim, dst_prim, errors)
    validate_variant_sets(src_prim, dst_prim, errors)

    # default children
    for child in src_prim.GetChildren():
        validate_prim(child, dst_prim.GetChild(child.GetName()), errors)


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
        stage_a = Usd.Stage.Open(args.inputA)
        stage_b = Usd.Stage.Open(args.inputB)
        stage_c = Usd.Stage.Open(args.composed)
    except Exception as e:
        print("Failed to open USD stages:", e, file=sys.stderr)
        sys.exit(2)

    errors = []

    for _, stage in (("A", stage_a), ("B", stage_b)):
        pseudo = stage.GetPseudoRoot()
        for prim in pseudo.GetChildren():
            dst_prim = stage_c.GetPrimAtPath(prim.GetPath())
            validate_prim(prim, dst_prim, errors)

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
