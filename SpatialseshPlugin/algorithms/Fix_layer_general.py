# TODO potentially make the Delete holes and Field calculator algs as a function in utils as well.
from typing import Any, Optional

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
from qgis.core import Qgis
from qgis import processing

from ..utils.fix_layer import fix_layer_main_pipeline


class Fix_layer_general(QgsProcessingAlgorithm):
    def initAlgorithm(self, configuration: Optional[dict[str, Any]] = None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "polygon_layer_to_clean",
                "Polygon layer to clean",
                types=[Qgis.ProcessingSourceType.VectorPolygon],
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "filter_small_polygons_size_m2",
                "Filter small polygons size (m2)",
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
                "crs_to_reproject", "CRS to reproject", defaultValue="EPSG:27700"
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "temporary_file_path_before_cleaning",
                "File path for interim results",
                behavior=Qgis.ProcessingFileParameterBehavior.File,
                fileFilter="All files (*.*)",
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "Final_cleaned_output",
                "Final cleaned output",
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
        feedback = QgsProcessingMultiStepFeedback(27, feedback)
        results: dict[str, str] = {}
        outputs: dict[str, Any] = {}

        fix_layer_main_pipeline_outputs = fix_layer_main_pipeline(
            parameters["polygon_layer_to_clean"],
            parameters["filter_small_polygons_size_m2"],
            parameters["snapping_tolerance_m"],
            parameters["crs_to_reproject"],
            parameters["temporary_file_path_before_cleaning"],
            context,
            feedback,
            starting_step=1,
        )

        if fix_layer_main_pipeline_outputs is not None:
            outputs.update(fix_layer_main_pipeline_outputs)

        # Drop field - fid
        outputs["DropFieldFid"] = processing.run(
            "native:deletecolumn",
            {
                "COLUMN": QgsExpression("'fid;cat;gap;path'").evaluate(),
                "INPUT": outputs["EliminateSelectedPolygonsGaps"]["OUTPUT"],
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
                "OUTPUT": parameters["Final_cleaned_output"],
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FieldCalculatorArea"] is not None

        results["Final_cleaned_output"] = outputs["FieldCalculatorArea"]["OUTPUT"]
        context.layerToLoadOnCompletionDetails(
            results["Final_cleaned_output"]
        ).name = "Final_cleaned_output"
        return results

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
