from typing import Any
from qgis.core import (
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingMultiStepFeedback,
    QgsVectorLayer,
)
import processing


def fix_validate_reproject_layer(
    input_layer: str,
    output_crs: str,
    context: QgsProcessingContext,
    feedback: QgsProcessingMultiStepFeedback,
    starting_step: int = 1,
) -> QgsVectorLayer | None:
    outputs: dict[str, Any] = {}

    # Fix geometries

    outputs["FixGeometries"] = processing.run(
        "native:fixgeometries",
        {
            "INPUT": input_layer,
            "METHOD": 0,  # Linework
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["FixGeometries"] is not None

    feedback.setCurrentStep(starting_step)
    if feedback.isCanceled():
        return None

    # Check validity
    outputs["CheckValidity"] = processing.run(
        "qgis:checkvalidity",
        {
            "IGNORE_RING_SELF_INTERSECTION": False,
            "INPUT_LAYER": outputs["FixGeometries"]["OUTPUT"],
            "METHOD": 2,  # GEOS
            "VALID_OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["CheckValidity"] is not None

    feedback.setCurrentStep(starting_step + 1)
    if feedback.isCanceled():
        return None

    # Reproject layer
    outputs["ReprojectLayer"] = processing.run(
        "native:reprojectlayer",
        {
            "CONVERT_CURVED_GEOMETRIES": False,
            "INPUT": outputs["CheckValidity"]["VALID_OUTPUT"],
            "OPERATION": None,
            "TARGET_CRS": output_crs,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        # is_child_algorithm=True,
    )

    assert outputs["ReprojectLayer"] is not None

    feedback.setCurrentStep(starting_step + 2)
    if feedback.isCanceled():
        return None

    return outputs["ReprojectLayer"]["OUTPUT"]


def fix_layer_main_pipeline(
    input_layer: QgsVectorLayer,
    minimum_mappable_unit_m2: float,
    snapping_tolerance_m: float,
    set_file_path_for_interim_results: str,
    context: QgsProcessingContext,
    feedback: QgsProcessingMultiStepFeedback,
    starting_step=1,
) -> dict[str, Any] | None:
    outputs: dict[str, Any] = {}

    if input_layer.fields().indexOf("fid") != -1:
        outputs["PrepareInterimLayer"] = processing.run(
            "native:renametablefield",
            {
                "FIELD": "fid",
                "INPUT": input_layer,
                "NEW_NAME": "old_fid",
                "OUTPUT": f"{set_file_path_for_interim_results}",
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
    else:
        outputs["PrepareInterimLayer"] = processing.run(
            "native:savefeatures",
            {
                "INPUT": input_layer,
                "OUTPUT": set_file_path_for_interim_results,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

    assert outputs["PrepareInterimLayer"] is not None

    feedback.setCurrentStep(starting_step)
    if feedback.isCanceled():
        return {}

    # v.clean
    outputs["Vclean"] = processing.run(
        "grass:v.clean",
        {
            "-b": False,
            "-c": False,
            "GRASS_MIN_AREA_PARAMETER": 0.0001,
            "GRASS_OUTPUT_TYPE_PARAMETER": 0,  # auto
            "GRASS_REGION_PARAMETER": None,
            "GRASS_SNAP_TOLERANCE_PARAMETER": -1,
            "GRASS_VECTOR_DSCO": None,
            "GRASS_VECTOR_EXPORT_NOCAT": False,
            "GRASS_VECTOR_LCO": None,
            "input": outputs["PrepareInterimLayer"]["OUTPUT"],
            "threshold": None,
            "tool": [0, 6, 11, 12],  # break,rmdupl,rmline,rmsa
            "type": [4],  # area
            "error": QgsProcessing.TEMPORARY_OUTPUT,
            "output": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["Vclean"] is not None

    feedback.setCurrentStep(starting_step + 1)
    if feedback.isCanceled():
        return {}

    # Fix geometries - v.clean
    outputs["FixGeometriesVclean"] = processing.run(
        "native:fixgeometries",
        {
            "INPUT": outputs["Vclean"]["output"],
            "METHOD": 0,  # Linework
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["FixGeometriesVclean"] is not None

    feedback.setCurrentStep(starting_step + 2)
    if feedback.isCanceled():
        return {}

    # Union
    outputs["Union"] = processing.run(
        "native:union",
        {
            "GRID_SIZE": None,
            "INPUT": outputs["FixGeometriesVclean"]["OUTPUT"],
            "OVERLAY": None,
            "OVERLAY_FIELDS_PREFIX": None,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["Union"] is not None

    feedback.setCurrentStep(starting_step + 3)
    if feedback.isCanceled():
        return {}

    # Delete duplicate geometries
    outputs["DeleteDuplicateGeometries"] = processing.run(
        "native:deleteduplicategeometries",
        {
            "INPUT": outputs["Union"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["DeleteDuplicateGeometries"] is not None

    feedback.setCurrentStep(starting_step + 4)
    if feedback.isCanceled():
        return {}

    # Remove null geometries
    outputs["RemoveNullGeometries"] = processing.run(
        "native:removenullgeometries",
        {
            "INPUT": outputs["DeleteDuplicateGeometries"]["OUTPUT"],
            "REMOVE_EMPTY": True,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["RemoveNullGeometries"] is not None

    feedback.setCurrentStep(starting_step + 5)
    if feedback.isCanceled():
        return {}

    # Select by expression
    outputs["SelectByExpression"] = processing.run(
        "qgis:selectbyexpression",
        {
            "EXPRESSION": f"area($geometry) < {minimum_mappable_unit_m2}",
            "INPUT": outputs["RemoveNullGeometries"]["OUTPUT"],
            "METHOD": 0,  # creating new selection
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["SelectByExpression"] is not None

    feedback.setCurrentStep(starting_step + 6)
    if feedback.isCanceled():
        return {}

    # Eliminate selected polygons
    outputs["EliminateSelectedPolygons"] = processing.run(
        "qgis:eliminateselectedpolygons",
        {
            "INPUT": outputs["SelectByExpression"]["OUTPUT"],
            "MODE": 2,  # Largest Common Boundary
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["EliminateSelectedPolygons"] is not None

    feedback.setCurrentStep(starting_step + 7)
    if feedback.isCanceled():
        return {}

    # Multipart to singleparts
    outputs["MultipartToSingleparts"] = processing.run(
        "native:multiparttosingleparts",
        {
            "INPUT": outputs["EliminateSelectedPolygons"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["MultipartToSingleparts"] is not None

    feedback.setCurrentStep(starting_step + 8)
    if feedback.isCanceled():
        return {}

    # Convert geometry type
    outputs["ConvertGeometryType"] = processing.run(
        "qgis:convertgeometrytype",
        {
            "INPUT": outputs["MultipartToSingleparts"]["OUTPUT"],
            "TYPE": 4,  # Polygons
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["ConvertGeometryType"] is not None

    feedback.setCurrentStep(starting_step + 9)
    if feedback.isCanceled():
        return {}

    # Remove duplicate vertices
    outputs["RemoveDuplicateVertices"] = processing.run(
        "native:removeduplicatevertices",
        {
            "INPUT": outputs["ConvertGeometryType"]["OUTPUT"],
            "TOLERANCE": 0.01,
            "USE_Z_VALUE": False,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["RemoveDuplicateVertices"] is not None

    feedback.setCurrentStep(starting_step + 10)
    if feedback.isCanceled():
        return {}

    # Extract by expression
    # for small polygons with no neighbous
    outputs["ExtractByExpression"] = processing.run(
        "native:extractbyexpression",
        {
            "EXPRESSION": "area($geometry) > 0.50",
            "INPUT": outputs["RemoveDuplicateVertices"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["ExtractByExpression"] is not None

    feedback.setCurrentStep(starting_step + 11)
    if feedback.isCanceled():
        return {}

    # Snap geometries to layer
    outputs["SnapGeometriesToLayer"] = processing.run(
        "native:snapgeometries",
        {
            "BEHAVIOR": 0,  # Prefer aligning nodes, insert extra vertices where required
            "INPUT": outputs["ExtractByExpression"]["OUTPUT"],
            "REFERENCE_LAYER": outputs["ExtractByExpression"]["OUTPUT"],
            "TOLERANCE": snapping_tolerance_m,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["SnapGeometriesToLayer"] is not None

    feedback.setCurrentStep(starting_step + 12)
    if feedback.isCanceled():
        return {}

    # Fix geometries - snap
    outputs["FixGeometriesSnap"] = processing.run(
        "native:fixgeometries",
        {
            "INPUT": outputs["SnapGeometriesToLayer"]["OUTPUT"],
            "METHOD": 0,  # Linework
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["FixGeometriesSnap"] is not None

    feedback.setCurrentStep(starting_step + 13)
    if feedback.isCanceled():
        return {}

    return outputs


def process_gaps(
    input_layer: str,
    overlay_layer: str,
    context: QgsProcessingContext,
    feedback: QgsProcessingMultiStepFeedback,
    starting_step=1,
) -> dict[str, Any] | None:
    outputs: dict[str, Any] = {}

    # Symmetrical difference
    outputs["SymmetricalDifference"] = processing.run(
        "native:symmetricaldifference",
        {
            "GRID_SIZE": None,
            "INPUT": input_layer,
            "OVERLAY": overlay_layer,
            "OVERLAY_FIELDS_PREFIX": None,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["SymmetricalDifference"] is not None

    feedback.setCurrentStep(starting_step)
    if feedback.isCanceled():
        return {}

    # Multipart to singleparts - symmetrical difference
    outputs["MultipartToSinglepartsSymmetricalDifference"] = processing.run(
        "native:multiparttosingleparts",
        {
            "INPUT": outputs["SymmetricalDifference"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["MultipartToSinglepartsSymmetricalDifference"] is not None

    feedback.setCurrentStep(starting_step + 1)
    if feedback.isCanceled():
        return {}

    # Field calculator - gaps
    outputs["FieldCalculatorGaps"] = processing.run(
        "native:fieldcalculator",
        {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "gap",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 2,  # Text (string)
            "FORMULA": "'yes'",
            "INPUT": outputs["MultipartToSinglepartsSymmetricalDifference"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["FieldCalculatorGaps"] is not None

    feedback.setCurrentStep(starting_step + 2)
    if feedback.isCanceled():
        return {}

    # Merge vector layers
    outputs["MergeVectorLayers"] = processing.run(
        "native:mergevectorlayers",
        {
            "CRS": None,
            "LAYERS": [
                outputs["FieldCalculatorGaps"]["OUTPUT"],
                input_layer,  # the so-far-cleaned layer
            ],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["MergeVectorLayers"] is not None

    feedback.setCurrentStep(starting_step + 3)
    if feedback.isCanceled():
        return {}

    # Select by expression - gaps
    outputs["SelectByExpressionGaps"] = processing.run(
        "qgis:selectbyexpression",
        {
            "EXPRESSION": "gap = 'yes'",
            "INPUT": outputs["MergeVectorLayers"]["OUTPUT"],
            "METHOD": 0,  # creating new selection
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["SelectByExpressionGaps"] is not None

    feedback.setCurrentStep(starting_step + 4)
    if feedback.isCanceled():
        return {}

    # Eliminate selected polygons - gaps
    outputs["EliminateSelectedPolygonsGaps"] = processing.run(
        "qgis:eliminateselectedpolygons",
        {
            "INPUT": outputs["SelectByExpressionGaps"]["OUTPUT"],
            "MODE": 0,  # Largest Area
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["EliminateSelectedPolygonsGaps"] is not None

    feedback.setCurrentStep(starting_step + 5)
    if feedback.isCanceled():
        return {}

    return outputs
