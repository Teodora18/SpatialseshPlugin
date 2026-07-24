from typing import Any, Optional

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
from qgis.core import Qgis
from qgis import processing

from ..utils.calculate_direction import calculate_distance_and_direction


class NearestNeighbourDDAlgorithm(QgsProcessingAlgorithm):

    def initAlgorithm(self, configuration: Optional[dict[str, Any]] = None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "ecological_merged",
                "Ecological merged",
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
                type=QgsProcessingParameterNumber.Double,  # type: ignore
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "NationalAndLocal",
                "National and local",
                type=Qgis.ProcessingSourceType.VectorPolygon,
                createByDefault=True,
                supportsAppend=True,
                defaultValue="TEMPORARY_OUTPUT",
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                "International",
                "International",
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
    ) -> dict[str, Any]:
        feedback = QgsProcessingMultiStepFeedback(7, feedback)
        results: dict[str, Any] = {}
        outputs: dict[str, Any] = {}

        # Calculate join attributes by nearest, azimuth and bearing
        direction_outputs = calculate_distance_and_direction(
            parameters["ecological_merged"],
            parameters["red_line_boundary"],
            parameters["maximim_distance_m"],
            context,
            feedback,
        )

        if direction_outputs is not None:
            outputs.update(direction_outputs)

        # Retain fields
        outputs["RetainFields"] = processing.run(
            "native:retainfields",
            {
                "FIELDS": QgsExpression(
                    "'DesignationType;Designation;SiteName;distance;Bearing;Azimuth'"
                ).evaluate(),
                "INPUT": outputs["FieldCalculatorBearing"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["RetainFields"] is not None

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("Retained only required fields.")

        # Order by expression
        outputs["OrderByExpression"] = processing.run(
            "native:orderbyexpression",
            {
                "ASCENDING": True,
                "EXPRESSION": "distance",
                "INPUT": outputs["RetainFields"]["OUTPUT"],
                "NULLS_FIRST": False,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["OrderByExpression"] is not None

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("Features ordered by distance.")

        cases = [
            ("International", "International"),
            ("National and Local", "NationalAndLocal"),
        ]

        for step, (designation, output_name) in enumerate(cases, start=6):

            feedback.setCurrentStep(step)

            if feedback.isCanceled():
                return {}

            # Extract by expression
            outputs[f"ExtractByExpression{output_name}"] = processing.run(
                "native:extractbyexpression",
                {
                    "EXPRESSION": f"DesignationType = '{designation}'",
                    "INPUT": outputs["OrderByExpression"]["OUTPUT"],
                    "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
                },
                context=context,
                feedback=feedback,
                is_child_algorithm=True,
            )

            assert outputs[f"ExtractByExpression{output_name}"] is not None

            if feedback.isCanceled():
                return {}

            feedback.setProgressText(f"{designation} sites extracted.")

            # Drop field(s)
            outputs[f"DropFields{output_name}"] = processing.run(
                "native:deletecolumn",
                {
                    "COLUMN": ["DesignationType"],
                    "INPUT": outputs[f"ExtractByExpression{output_name}"]["OUTPUT"],
                    "OUTPUT": parameters[output_name],
                },
                context=context,
                feedback=feedback,
                is_child_algorithm=True,
            )

            assert outputs[f"DropFields{output_name}"] is not None

            results[output_name] = outputs[f"DropFields{output_name}"]["OUTPUT"]

            context.layerToLoadOnCompletionDetails(results[output_name]).name = (
                output_name
            )

            feedback.setProgressText(f"{designation} unnecessary fields dropped.")
        return results

    def name(self) -> str:
        return "NearestNeighbourDD"

    def displayName(self) -> str:
        return "NearestNeighbourDD"

    def group(self) -> str:
        return ""

    def groupId(self) -> str:
        return ""

    def createInstance(self):
        return self.__class__()
