from typing import Any
from qgis.core import (
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingMultiStepFeedback,
)
import processing


def calculate_distance_and_direction(
    input_layer: str,
    boundary_layer: str,
    max_distance: float,
    context: QgsProcessingContext,
    feedback: QgsProcessingMultiStepFeedback,
    starting_step: int = 1,
) -> dict[str, Any] | None:
    outputs: dict[str, Any] = {}

    # Join attributes by nearest
    outputs["JoinAttributesByNearest"] = processing.run(
        "native:joinbynearest",
        {
            "DISCARD_NONMATCHING": True,
            "FIELDS_TO_COPY": [""],
            "INPUT": input_layer,
            "INPUT_2": boundary_layer,
            "MAX_DISTANCE": max_distance,
            "NEIGHBORS": 1,
            "PREFIX": None,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["JoinAttributesByNearest"] is not None

    feedback.setCurrentStep(starting_step)
    if feedback.isCanceled():
        return None

    feedback.setProgressText("Joined attributes by nearest.")

    # Calculate azimuth
    outputs["FieldCalculatorAzimuth"] = processing.run(
        "native:fieldcalculator",
        {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Azimuth",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 0,
            "FORMULA": 'degrees(azimuth(make_point("nearest_x", "nearest_y"), make_point("feature_x", "feature_y")))',
            "INPUT": outputs["JoinAttributesByNearest"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["FieldCalculatorAzimuth"] is not None

    feedback.setCurrentStep(starting_step + 1)
    if feedback.isCanceled():
        return None

    feedback.setProgressText("Azimuth calculated.")

    # Calculate bearing
    outputs["FieldCalculatorBearing"] = processing.run(
        "native:fieldcalculator",
        {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Bearing",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 2,
            "FORMULA": "case when \"Azimuth\" >337.5 OR \"Azimuth\" <22.5 then 'North' else '' end +\r\ncase when \"Azimuth\" >22.5 AND \"Azimuth\" <67.5 then 'North-East' else '' end +\r\ncase when \"Azimuth\" >67.5 AND \"Azimuth\" <112.5 then 'East' else '' end +\r\ncase when \"Azimuth\" >112.5 AND \"Azimuth\" <157.5 then 'South-East' else '' end +\r\ncase when \"Azimuth\" >157.5 AND \"Azimuth\" <202.5 then 'South' else '' end +\r\ncase when \"Azimuth\" >202.5 AND \"Azimuth\" <247.5 then 'South-West' else '' end +\r\ncase when \"Azimuth\" >247.5 AND \"Azimuth\" <292.5 then 'West' else '' end +\r\ncase when \"Azimuth\" >292.5 AND \"Azimuth\" <337.5 then 'North-West' else '' end",
            "INPUT": outputs["FieldCalculatorAzimuth"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
        context=context,
        feedback=feedback,
        is_child_algorithm=True,
    )

    assert outputs["FieldCalculatorBearing"] is not None

    feedback.setCurrentStep(starting_step + 2)
    if feedback.isCanceled():
        return None

    feedback.setProgressText("Bearing calculated.")

    return outputs
