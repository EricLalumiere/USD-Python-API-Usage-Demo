#!/usr/bin/env python
import logging

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
from multiprocessing.util import LOGGER_NAME

from pxr import Usd, Sdf


LOGGER = logging.getLogger(LOGGER_NAME)
DEBUG = True  # Set to True to enable debug output
# Enable debug logging if needed
if DEBUG:
    logging.basicConfig(level=logging.DEBUG)


def copy_metadata(src_prim, dst_prim):
    """
    Copy all authored metadata from src-prim to dst-prim.
    """
    custom_data_keys = ["comment", "documentation", "focalLength"]
    dst_keys = dst_prim.GetAllMetadata().keys()
    src_attr_names = src_prim.GetAttributes()
    for key, src_val in src_prim.GetAllMetadata().items():
        if key in src_attr_names or key in custom_data_keys:
            # Will use copy_attributes instead of copy_metadata
            continue

        LOGGER.debug("[M][%s] → [%s] metadata '%s' with value %s [%s]" % (
            src_prim.GetPath(), dst_prim.GetPath(), key, src_val, type(src_val)))
        # If src_val is an unregistered value, use its actual value
        # This is common for custom data that may not be registered in the schema
        # e.g. Sdf.UnregisteredValue("comment", "This is a comment")
        # or Sdf.UnregisteredValue("documentation", "This is documentation")
        if isinstance(src_val, Sdf.UnregisteredValue):
            LOGGER.debug("Unregistered value for key '%s': %s", key, src_val)
            src_val = src_val.value
        if key == "customData":
            LOGGER.debug("Copying customData from a dictionary")
            for k, v in src_val.items():
                if isinstance(v, Sdf.UnregisteredValue):
                    LOGGER.debug("Unregistered value for key '%s': %s", k, v)
                    v = v.value
                if k not in dst_keys:
                    LOGGER.debug("Copying custom data key '%s' with value %s [%s]",
                                 k, v, type(v))
                    # Copy custom data if it's not already set on dst or is a comment
                    dst_prim.SetCustomDataByKey(k, v)
        elif key not in dst_keys:
            LOGGER.debug("Copying custom metadata key '%s' with value %s [%s]",
                         key, src_val, type(src_val))
            # Copy metadata if it's not already set on dst or is a comment
            dst_prim.SetCustomDataByKey(key, src_val)
        else:
            LOGGER.debug("Assign metadata directly on key '%s' as it "
                         "already exists on dst", key)
            # Set the metadata on the destination prim
            dst_prim.SetMetadata(key, src_val)

        LOGGER.debug("Resulting value: %s [%s]\n" % (
            dst_prim.GetMetadata(key), type(dst_prim.GetMetadata(key))))


def copy_attributes(src_prim, dst_prim):
    # Copy attributes (e.g. focalLength on Camera)

    for src_attr in src_prim.GetAttributes():
        name = src_attr.GetName()
        type_name = src_attr.GetTypeName()
        value = src_attr.Get()
        variability = src_attr.GetVariability()
        is_custom = src_attr.IsCustom()
        if not value:
            LOGGER.debug("[A][%s]->[%s] Skipping empty attribute '%s' [%s]" % (
                src_prim.GetPath(),
                dst_prim.GetPath(),
                name,
                type_name))
            continue

        LOGGER.debug("[A][%s]->[%s] Copying attribute '%s' with value %s [%s]" % (
            src_prim.GetPath(),
            dst_prim.GetPath(),
            src_attr.GetName(),
            value,
            src_attr.GetTypeName()))

        # Create or get matching attr on dst
        dst_attr = dst_prim.CreateAttribute(name,
                                            type_name,
                                            variability=variability,
                                            custom=is_custom)
        dst_attr.Set(value)

        LOGGER.debug("Resulting value: %s [%s]\n" % (dst_attr.Get(),
                                                     dst_attr.GetTypeName()))


def copy_relationships(src_prim, dst_prim):
    """
    Copy all relationships (names & targets) from src-prim to dst-prim.
    """
    for rel in src_prim.GetRelationships():
        new_rel = dst_prim.CreateRelationship(rel.GetName())
        new_rel.SetTargets(rel.GetTargets())


def copy_variant_sets(src, dst):
    """
    Copy all variant sets. For each variant, we select it on both
    src and dst, then recursively copy children authored inside that variant.
    """
    src_var_sets = src.GetVariantSets()
    dst_var_sets = dst.GetVariantSets()

    # Copy variant sets _on this prim_
    for var_set_name in src_var_sets.GetNames():
        src_var_set = src_var_sets.GetVariantSet(var_set_name)
        dst_var_set = dst_var_sets.AddVariantSet(var_set_name)

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


def _copy_prim(src_prim, dst_stage):
    """
    Recursively copy a prim (and its subtree) from srcPrim's stage into dstStage
    at the same path, including type, metadata, relationships, variants, and children.
    """
    path = src_prim.GetPath()
    prim_type = src_prim.GetTypeName() or 'Xform'
    dst_prim = dst_stage.DefinePrim(path, prim_type)

    # metadata + attributes + relationships
    copy_metadata(src_prim, dst_prim)
    copy_attributes(src_prim, dst_prim)
    copy_relationships(src_prim, dst_prim)

    # variants
    copy_variant_sets(src_prim, dst_prim)

    # children (outside variant edits)
    for child in src_prim.GetChildren():
        _copy_prim(child, dst_stage)


def main():
    """
    Main function to parse command line arguments and compose two USD scenes.
    :return:  None
    """
    parser = argparse.ArgumentParser(
        description="Compose two USDA scenes into one, preserving metadata, "
                    "relationships, and variants."
    )
    parser.add_argument("inputA",  help="first .usda scene")
    parser.add_argument("inputB",  help="second .usda scene")
    parser.add_argument("output", help="composed .usda to write out")
    args = parser.parse_args()

    # Create the output stage (overwrites if exists)
    out_stage = Usd.Stage.CreateNew(args.output)

    # Helper to open and copy every root-level prim
    def merge_file(usda_path):
        stage = Usd.Stage.Open(usda_path)
        pseudo_root = stage.GetPseudoRoot()  # top of prim hierarchy
        for prim in pseudo_root.GetChildren():
            _copy_prim(prim, out_stage)

    # Merge both scenes
    merge_file(args.inputA)
    merge_file(args.inputB)

    # Save
    out_stage.GetRootLayer().Save()
    print(f"Composed {args.inputA} + {args.inputB} → {args.output}")


if __name__ == "__main__":
    main()
