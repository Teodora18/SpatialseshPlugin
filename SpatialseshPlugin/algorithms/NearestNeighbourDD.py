from typing import Any, Optional

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsExpression
from qgis import processing


class NearestNeighbourDDAlgorithm(QgsProcessingAlgorithm):

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        self.addParameter(QgsProcessingParameterVectorLayer('ecological_merged', 'Ecological merged', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('red_line_boundary', 'Red line Boundary', types=[QgsProcessing.TypeVectorLine,QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('maximim_distance_m', 'Maximim distance (m)', type=QgsProcessingParameterNumber.Double, defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('NationalAndLocal', 'National and local', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue='TEMPORARY_OUTPUT'))
        self.addParameter(QgsProcessingParameterFeatureSink('International', 'International', type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, supportsAppend=True, defaultValue=None))

    def processAlgorithm(self, parameters: dict[str, Any], context: QgsProcessingContext, model_feedback: QgsProcessingFeedback) -> dict[str, Any]:
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(9, model_feedback)
        results = {}
        outputs = {}

        # Join attributes by nearest
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'FIELDS_TO_COPY': [''],
            'INPUT': parameters['ecological_merged'],
            'INPUT_2': parameters['red_line_boundary'],
            'MAX_DISTANCE': parameters['maximim_distance_m'],
            'NEIGHBORS': 1,
            'PREFIX': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinAttributesByNearest'] = processing.run('native:joinbynearest', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Field calculator - azimuth
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'Azimuth',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': 'degrees (azimuth ( make_point( "nearest_x" , "nearest_y" ), make_point( "feature_x" , "feature_y")))',
            'INPUT': outputs['JoinAttributesByNearest']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FieldCalculatorAzimuth'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Field calculator - bearing
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'Bearing',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 2,  # Text (string)
            'FORMULA': 'case when "Azimuth" >337.5 OR "Azimuth" <22.5 then \'North\' else \'\' end +\r\ncase when "Azimuth" >22.5 AND "Azimuth" <67.5 then \'North-East\' else \'\' end +\r\ncase when "Azimuth" >67.5 AND "Azimuth" <112.5 then \'East\' else \'\' end +\r\ncase when "Azimuth" >112.5 AND "Azimuth" <157.5 then \'South-East\' else \'\' end +\r\ncase when "Azimuth" >157.5 AND "Azimuth" <202.5 then \'South\' else \'\' end +\r\ncase when "Azimuth" >202.5 AND "Azimuth" <247.5 then \'South-West\' else \'\' end +\r\ncase when "Azimuth" >247.5 AND "Azimuth" <292.5 then \'West\' else \'\' end +\r\ncase when "Azimuth" >292.5 AND "Azimuth" <337.5 then \'North-West\' else \'\' end',
            'INPUT': outputs['FieldCalculatorAzimuth']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FieldCalculatorBearing'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Retain fields
        alg_params = {
            'FIELDS': QgsExpression("'DesignationType;Designation;SiteName;distance;Bearing;Azimuth'").evaluate(),
            'INPUT': outputs['FieldCalculatorBearing']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RetainFields'] = processing.run('native:retainfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Order by expression
        alg_params = {
            'ASCENDING': True,
            'EXPRESSION': 'distance',
            'INPUT': outputs['RetainFields']['OUTPUT'],
            'NULLS_FIRST': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['OrderByExpression'] = processing.run('native:orderbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Extract by expression - international
        alg_params = {
            'EXPRESSION': "DesignationType = 'International'",
            'INPUT': outputs['OrderByExpression']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByExpressionInternational'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Drop field(s) - international
        alg_params = {
            'COLUMN': QgsExpression("'DesignationType'").evaluate(),
            'INPUT': outputs['ExtractByExpressionInternational']['OUTPUT'],
            'OUTPUT': parameters['International']
        }
        outputs['DropFieldsInternational'] = processing.run('native:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['International'] = outputs['DropFieldsInternational']['OUTPUT']

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Extract by expression - national
        alg_params = {
            'EXPRESSION': "DesignationType = 'National and Local'",
            'INPUT': outputs['OrderByExpression']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByExpressionNational'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Drop field(s) - national
        alg_params = {
            'COLUMN': QgsExpression("'DesignationType'").evaluate(),
            'INPUT': outputs['ExtractByExpressionNational']['OUTPUT'],
            'OUTPUT': parameters['NationalAndLocal']
        }
        outputs['DropFieldsNational'] = processing.run('native:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['NationalAndLocal'] = outputs['DropFieldsNational']['OUTPUT']
        return results

    def name(self) -> str:
        return 'DesignationsDatabase'

    def displayName(self) -> str:
        return 'DesignationsDatabase'

    def group(self) -> str:
        return ''

    def groupId(self) -> str:
        return ''

    def createInstance(self):
        return self.__class__()
