# TODO potentially make the Delete holes and Field calculator algs as a function in utils as well.
from typing import Any, Optional
import os

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
from qgis.core import Qgis
from qgis import processing

from qgis.PyQt.QtGui import QIcon

from ..utils.fix_layer import (
    fix_validate_reproject_layer,
    fix_layer_main_pipeline,
    process_gaps,
)
from ..utils.license_manager import MaplangoLicensedAlgorithm


class Fix_layer_general(MaplangoLicensedAlgorithm):
    def __init__(self):
        super().__init__()

    def initAlgorithm(self, configuration: Optional[dict[str, Any]] = None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                "polygon_layer_to_fix",
                "Polygon layer to fix",
                types=[Qgis.ProcessingSourceType.VectorPolygon],
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "minimum_mappable_unit_m2",
                "Minimum Mappable Unit (m2)",
                type=Qgis.ProcessingNumberParameterType.Double,
                defaultValue=10,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "snapping_tolerance_m",
                "Snapping tolerance (m)",
                type=Qgis.ProcessingNumberParameterType.Double,
                defaultValue=0.3,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                "output_crs", "Output CRS", defaultValue="EPSG:27700"
            )
        )

        interim_results_parameter = QgsProcessingParameterFile(
            "set_file_path_for_interim_results",
            "Set file path for interim results",
            behavior=Qgis.ProcessingFileParameterBehavior.File,
            fileFilter="All files (*.*)",
            defaultValue=os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "interim_results.gpkg",
                )
            ),
        )
        interim_results_parameter.setFlags(
            interim_results_parameter.flags() | Qgis.ProcessingParameterFlag.Advanced
        )
        self.addParameter(interim_results_parameter)

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "fixed_output",
                "Fixed output",
                type=Qgis.ProcessingSourceType.VectorPolygon,
                createByDefault=True,
                supportsAppend=True,
                defaultValue=None,
            )
        )

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, str]:
        feedback = QgsProcessingMultiStepFeedback(28, feedback)
        results: dict[str, str] = {}
        outputs: dict[str, Any] = {}

        # Fix layer with the three utils algorithms: fix_validate_reproject_layer, fix_layer_main_pipeline, and process_gaps
        initial_fixed_layer = fix_validate_reproject_layer(
            parameters["polygon_layer_to_fix"],
            parameters["output_crs"],
            context,
            feedback,
            starting_step=1,
        )

        if initial_fixed_layer is None:
            return {}
        fix_layer_main_pipeline_outputs = fix_layer_main_pipeline(
            initial_fixed_layer,
            parameters["minimum_mappable_unit_m2"],
            parameters["snapping_tolerance_m"],
            parameters["set_file_path_for_interim_results"],
            context,
            feedback,
            starting_step=4,
        )
        if fix_layer_main_pipeline_outputs is not None:
            outputs.update(fix_layer_main_pipeline_outputs)

        if feedback.isCanceled():
            return {}

        outputs["Dissolve"] = processing.run(
            "native:dissolve",
            {
                "FIELD": [""],
                # outputs["FixGeometriesSnap"]["OUTPUT"] comes from the fix_layer_main_pipeline_outputs
                "INPUT": outputs["FixGeometriesSnap"]["OUTPUT"],
                "SEPARATE_DISJOINT": False,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["Dissolve"] is not None

        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}

        # Delete holes - dissolve
        outputs["DeleteHolesDissolve"] = processing.run(
            "native:deleteholes",
            {
                "INPUT": outputs["Dissolve"]["OUTPUT"],
                "MIN_AREA": 50,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["DeleteHolesDissolve"] is not None

        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}

        process_gaps_outputs = process_gaps(
            # outputs["FixGeometriesSnap"]["OUTPUT"] comes from the fix_layer_main_pipeline_outputs
            outputs["FixGeometriesSnap"]["OUTPUT"],
            outputs["DeleteHolesDissolve"]["OUTPUT"],
            context,
            feedback,
            starting_step=20,
        )

        if process_gaps_outputs is not None:
            outputs.update(process_gaps_outputs)

        if feedback.isCanceled():
            return {}

        # Drop field - fid
        outputs["DropFieldFid"] = processing.run(
            "native:deletecolumn",
            {
                "COLUMN": QgsExpression("'fid;cat;gap;path'").evaluate(),
                "INPUT": outputs["EliminateSelectedPolygonsGaps"][
                    "OUTPUT"
                ],  # comes from the process_gaps_outputs
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["DropFieldFid"] is not None

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}

        # Delete holes
        outputs["DeleteHoles"] = processing.run(
            "native:deleteholes",
            {
                "INPUT": outputs["DropFieldFid"]["OUTPUT"],
                "MIN_AREA": 0.1,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["DeleteHoles"] is not None

        feedback.setCurrentStep(27)
        if feedback.isCanceled():
            return {}

        # Field calculator - area
        outputs["FieldCalculatorArea"] = processing.run(
            "native:fieldcalculator",
            {
                "FIELD_LENGTH": 0,
                "FIELD_NAME": "Area",
                "FIELD_PRECISION": 0,
                "FIELD_TYPE": 1,  # Integer (32 bit)
                "FORMULA": "area($geometry)",
                "INPUT": outputs["DeleteHoles"]["OUTPUT"],
                "OUTPUT": parameters["fixed_output"],
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FieldCalculatorArea"] is not None

        results["fixed_output"] = outputs["FieldCalculatorArea"]["OUTPUT"]
        context.layerToLoadOnCompletionDetails(
            results["fixed_output"]
        ).name = "fixed_output"
        return results

    def icon(self) -> QIcon:
        return QIcon(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "icons",
                "Fix_layer_general.svg",
            )
        )

    def shortHelpString(self) -> str:
        text = """<b>General:</b><br>\
This algorithm cleans and repairs a polygon layer by fixing invalid geometries, removing duplicate and small polygons, snapping nearby geometries, eliminating gaps and duplicate geometires, and applying additional geometry corrections.<br><br>\
 <b>Parameters:</b><br>\
 The following parameters must be defined to execute the algorithm:
<ul> <li>Polygon layer to fix</li> <li> Minimum Mappable Unit (m2)</li> <li>Snapping tolerance (m)</li> <li>Output CRS</li> <li> Set file path for interim results - <b>Advanced parameter with a default value</b></li> </ul><br>\
<b>Output:</b><br>\
 The algorithm produces a fixed polygon layer with repaired geometries, removed small polygons, slivers and gaps, and an additional <i>Area</i> field containing the area of each resulting feature.<br>\
"""

        return text

    def name(self) -> str:
        return "FixLayer_general"

    def displayName(self) -> str:
        return "Fix Layer General"

    def group(self) -> str:
        return ""

    def groupId(self) -> str:
        return ""

    def createInstance(self):
        return self.__class__()
