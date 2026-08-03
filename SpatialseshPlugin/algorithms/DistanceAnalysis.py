from typing import Any, Optional

from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import Qgis
from qgis import processing

from ..utils.calculate_direction import calculate_distance_and_direction


class DistanceAnalysisAlgorithm(QgsProcessingAlgorithm):
    def initAlgorithm(self, configuration: Optional[dict[str, Any]] = None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "input_layer",
                "Input layer",
                types=[Qgis.ProcessingSourceType.VectorPolygon],
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "red_line_boundary",
                "Red line Boundary",
                types=[
                    Qgis.ProcessingSourceType.VectorLine,
                    Qgis.ProcessingSourceType.VectorPolygon,
                ],
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "maximim_distance_m",
                "Maximim distance (m)",
                type=Qgis.ProcessingNumberParameterType.Double,
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "Result",
                "result",
                type=Qgis.ProcessingSourceType.VectorPolygon,
                createByDefault=True,
                defaultValue=None,
            )
        )

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:
        feedback = QgsProcessingMultiStepFeedback(4, feedback)
        results: dict[str, Any] = {}
        outputs: dict[str, Any] = {}

        direction_outputs = calculate_distance_and_direction(
            parameters["input_layer"],
            parameters["red_line_boundary"],
            parameters["maximim_distance_m"],
            context,
            feedback,
        )

        if direction_outputs is not None:
            outputs.update(direction_outputs)

        # Order by expression
        outputs["OrderByExpression"] = processing.run(
            "native:orderbyexpression",
            {
                "ASCENDING": True,
                "EXPRESSION": "distance",
                "INPUT": outputs["FieldCalculatorBearing"]["OUTPUT"],
                "NULLS_FIRST": False,
                "OUTPUT": parameters["Result"],
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["OrderByExpression"] is not None

        feedback.setProgressText("Features ordered by distance.")

        results["Result"] = outputs["OrderByExpression"]["OUTPUT"]
        return results

    def name(self) -> str:
        return "DistanceAnalysis"

    def displayName(self) -> str:
        return "DistanceAnalysis"

    def group(self) -> str:
        return ""

    def groupId(self) -> str:
        return ""

    def createInstance(self):
        return self.__class__()
