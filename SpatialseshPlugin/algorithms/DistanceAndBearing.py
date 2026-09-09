from typing import Any, Optional
import os

from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import Qgis
from qgis import processing
from qgis.PyQt.QtGui import QIcon

from ..utils.calculate_direction import calculate_distance_and_direction


class DistanceAndBearingAlgorithm(QgsProcessingAlgorithm):
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
                "site_boundary",
                "Site boundary",
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
                "result",
                "Result",
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
            parameters["site_boundary"],
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
                "OUTPUT": parameters["result"],
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["OrderByExpression"] is not None

        feedback.setProgressText("Features ordered by distance.")

        results["result"] = outputs["OrderByExpression"]["OUTPUT"]
        context.layerToLoadOnCompletionDetails(results["result"]).name = "Result"
        return results

    def icon(self) -> QIcon:
        return QIcon(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "icons",
                "icon.png",
            )
        )

    def shortHelpString(self) -> str:
        text = """ <b>General:</b><br>\
        This algorithm calculates the distance and direction from input features to their nearest Red Line Boundary, assigns a compass bearing, and orders the results by distance.<br><br>\
        <b>Parameters:</b><br>\
       The following parameters must be defined to execute the algorithm:
        <ul><li>Input layer</li><li>Site boundary </li><li>Maximum distance (m)</li></ul><br>\
        <b>Output:</b><br>\
        The output of the algorithm is a polygon layer with the features from the input layer that meet the condition of the maximum distance constraint with additional fields in the attribute table for distance, azimuth and bearing.
<br>\
        """
        return text

    def name(self) -> str:
        return "DistanceAndBearing"

    def displayName(self) -> str:
        return "Distance and bearing"

    def group(self) -> str:
        return ""

    def groupId(self) -> str:
        return ""

    def createInstance(self):
        return self.__class__()
