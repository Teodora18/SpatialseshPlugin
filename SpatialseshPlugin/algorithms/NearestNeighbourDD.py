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
        feedback = QgsProcessingMultiStepFeedback(9, feedback)
        results: dict[str, Any] = {}
        outputs: dict[str, Any] = {}

        # Join attributes by nearest
        outputs["JoinAttributesByNearest"] = processing.run(
            "native:joinbynearest",
            {
                "DISCARD_NONMATCHING": True,
                "FIELDS_TO_COPY": [""],
                "INPUT": parameters["ecological_merged"],
                "INPUT_2": parameters["red_line_boundary"],
                "MAX_DISTANCE": parameters["maximim_distance_m"],
                "NEIGHBORS": 1,
                "PREFIX": None,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["JoinAttributesByNearest"] is not None

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("Joined attibutes by nearest.")

        # Field calculator - azimuth
        outputs["FieldCalculatorAzimuth"] = processing.run(
            "native:fieldcalculator",
            {
                "FIELD_LENGTH": 0,
                "FIELD_NAME": "Azimuth",
                "FIELD_PRECISION": 0,
                "FIELD_TYPE": 0,  # Decimal (double)
                "FORMULA": 'degrees (azimuth ( make_point( "nearest_x" , "nearest_y" ), make_point( "feature_x" , "feature_y")))',
                "INPUT": outputs["JoinAttributesByNearest"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FieldCalculatorAzimuth"] is not None

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("Azimuth calculated.")

        # Field calculator - bearing
        outputs["FieldCalculatorBearing"] = processing.run(
            "native:fieldcalculator",
            {
                "FIELD_LENGTH": 0,
                "FIELD_NAME": "Bearing",
                "FIELD_PRECISION": 0,
                "FIELD_TYPE": 2,  # Text (string)
                "FORMULA": "case when \"Azimuth\" >337.5 OR \"Azimuth\" <22.5 then 'North' else '' end +\r\ncase when \"Azimuth\" >22.5 AND \"Azimuth\" <67.5 then 'North-East' else '' end +\r\ncase when \"Azimuth\" >67.5 AND \"Azimuth\" <112.5 then 'East' else '' end +\r\ncase when \"Azimuth\" >112.5 AND \"Azimuth\" <157.5 then 'South-East' else '' end +\r\ncase when \"Azimuth\" >157.5 AND \"Azimuth\" <202.5 then 'South' else '' end +\r\ncase when \"Azimuth\" >202.5 AND \"Azimuth\" <247.5 then 'South-West' else '' end +\r\ncase when \"Azimuth\" >247.5 AND \"Azimuth\" <292.5 then 'West' else '' end +\r\ncase when \"Azimuth\" >292.5 AND \"Azimuth\" <337.5 then 'North-West' else '' end",
                "INPUT": outputs["FieldCalculatorAzimuth"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FieldCalculatorBearing"] is not None

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("Bearing calculated.")

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

        # Extract by expression - international
        outputs["ExtractByExpressionInternational"] = processing.run(
            "native:extractbyexpression",
            {
                "EXPRESSION": "DesignationType = 'International'",
                "INPUT": outputs["OrderByExpression"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["ExtractByExpressionInternational"] is not None

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("International sites extracted.")

        # Drop field(s) - international
        outputs["DropFieldsInternational"] = processing.run(
            "native:deletecolumn",
            {
                "COLUMN": QgsExpression("'DesignationType'").evaluate(),
                "INPUT": outputs["ExtractByExpressionInternational"]["OUTPUT"],
                "OUTPUT": parameters["International"],
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["DropFieldsInternational"] is not None
        results["International"] = outputs["DropFieldsInternational"]["OUTPUT"]
        context.layerToLoadOnCompletionDetails(results["International"]).name = (
            "International"
        )

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("Unnecessary fields dropped.")

        # Extract by expression - national
        outputs["ExtractByExpressionNational"] = processing.run(
            "native:extractbyexpression",
            {
                "EXPRESSION": "DesignationType = 'National and Local'",
                "INPUT": outputs["OrderByExpression"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["ExtractByExpressionNational"] is not None

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("National sites extracted.")

        # Drop field(s) - national
        outputs["DropFieldsNational"] = processing.run(
            "native:deletecolumn",
            {
                "COLUMN": QgsExpression("'DesignationType'").evaluate(),
                "INPUT": outputs["ExtractByExpressionNational"]["OUTPUT"],
                "OUTPUT": parameters["NationalAndLocal"],
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["DropFieldsNational"] is not None

        results["NationalAndLocal"] = outputs["DropFieldsNational"]["OUTPUT"]
        context.layerToLoadOnCompletionDetails(results["NationalAndLocal"]).name = (
            "NationalAndLocal"
        )

        feedback.setProgressText("Unnecessary fields dropped.")

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
