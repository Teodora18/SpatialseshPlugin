from typing import Any, Optional

import os

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import Qgis
from qgis import processing

from qgis.PyQt.QtGui import QIcon

from ..utils.fix_layer import (
    fix_validate_reproject_layer,
    fix_layer_main_pipeline,
    process_gaps,
)
from ..utils.bng_field_mapping import get_fields
from ..utils.license_manager import MaplangoLicensedAlgorithm


class BNG_FixLayerAlgorithm(MaplangoLicensedAlgorithm):
    def __init__(self):
        super().__init__()

    def initAlgorithm(self, configuration: Optional[dict[str, Any]] = None):
        self.addParameter(
            QgsProcessingParameterEnum(
                "Layer_type",
                "Select a layer type to fix",
                options=[
                    "Master",
                    "Baseline",
                    "Proposed",
                ],
                allowMultiple=False,
                defaultValue=None,
            )
        )
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
                "fixed_BNG_output",
                "Fixed BNG output",
                type=Qgis.ProcessingSourceType.VectorPolygon,
                createByDefault=True,
                supportsAppend=True,
                defaultValue="TEMPORARY_OUTPUT",
            )
        )

    def get_field_mapping(self, bng_type: int) -> list[dict[str, Any]]:
        COMMON_ADDITIONAL_FIELDS = [
            "SITE_NAME",
            "SURVEY_DATE",
            "SURVEY_DETAILS",
            "COMMENT",
            "MAPPED_BY",
            "COMPANY",
            "BASE_MAP",
        ]

        field_mapping_by_bng_type = {
            0: (  # MASTER
                [
                    "PARCEL_REF",
                    "AREA",
                    "BASELINE_BROAD_HABITAT_TYPE",
                    "BASELINE_HABITAT_TYPE",
                    "BASELINE_DISTINCTIVENESS",
                    "BASELINE_CONDITION",
                    "BASELINE_STRATEGIC_SIGNIFICANCE",
                    "RETENTION_CATEGORY",
                    "PROPOSED_BROAD_HABITAT_TYPE",
                    "PROPOSED_HABITAT_TYPE",
                    "PROPOSED_DISTINCTIVENESS",
                    "PROPOSED_CONDITION",
                    "PROPOSED_STRATEGIC_SIGNIFICANCE",
                    "DELAY_IN_STARTING_HABITAT_CREATION_YEARS",
                    "HABITAT_CREATED_IN_ADVANCE_YEARS",
                    "LOCATION",
                    "SPATIAL_RISK_CATEGORY",
                ]
                + COMMON_ADDITIONAL_FIELDS
                + ["PHOTO"]
            ),
            1: (  # BASELINE
                [
                    "PARCEL_REF",
                    "UKHAB_LV1_CODE",
                    "UKHAB_LV2_CODE",
                    "UKHAB_LV3_CODE",
                    "UKHAB_LV4_CODE",
                    "UKHAB_LV5_CODE",
                    "ESSENTIAL_SECONDARY_CODE",
                    "ADDITIONAL_SECONDARY_CODE",
                    "BASELINE_BROAD_HABITAT_TYPE",
                    "BASELINE_HABITAT_TYPE",
                    "BASELINE_DISTINCTIVENESS",
                    "BASELINE_CONDITION",
                    "BASELINE_STRATEGIC_SIGNIFICANCE",
                    "RETENTION_CATEGORY",
                    "LOCATION",
                    "AREA",
                    "UKHABITAT",
                    "UKHAB_CODE",
                ]
                + COMMON_ADDITIONAL_FIELDS
                + [
                    "PHOTO",
                    "PREVIOUS_SURVEY",
                    "PREVIOUS_COMMENT",
                    "HABITAT_MANAGEMENT",
                    "GUIDANCE",
                    "GUIDANCE_Q",
                ]
            ),
            2: (  # PROPOSED
                [
                    "PARCEL_REF",
                    "RETENTION_CATEGORY",
                    "PROPOSED_BROAD_HABITAT_TYPE",
                    "PROPOSED_HABITAT_TYPE",
                    "PROPOSED_DISTINCTIVENESS",
                    "PROPOSED_CONDITION",
                    "PROPOSED_STRATEGIC_SIGNIFICANCE",
                    "DELAY_IN_STARTING_HABITAT_CREATION_YEARS",
                    "HABITAT_CREATED_IN_ADVANCE_YEARS",
                    "LOCATION",
                    "SPATIAL_RISK_CATEGORY",
                ]
                + COMMON_ADDITIONAL_FIELDS
                + [
                    "PREVIOUS_SURVEY",
                    "PREVIOUS_COMMENT",
                    "AREA",
                ]
            ),
        }
        if bng_type not in field_mapping_by_bng_type.keys():
            raise NotImplementedError(
                "Unexpected BNG layer type. Layer type must be 'Master', 'Baseline' or 'Proposed'"
            )
        return get_fields(field_mapping_by_bng_type[bng_type])

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
        assert initial_fixed_layer is not None
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
                # outputs["FixGeometriesSnap"]["OUTPUT"]comes from the fix_layer_main_pipeline_outputs dict
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
            # outputs["FixGeometriesSnap"]["OUTPUT"] comes from the fix_layer_main_pipeline_outputs dict
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

        # Refactor fields - names
        refactor_fields_params: list[dict[str, Any]] = self.get_field_mapping(
            parameters["Layer_type"]
        )

        outputs[f"RefactorFieldsNames_bng{parameters['Layer_type']}"] = processing.run(
            "native:refactorfields",
            {
                "FIELDS_MAPPING": refactor_fields_params,
                # outputs["EliminateSelectedPolygonsGaps"]["OUTPUT"] comes from the process_gaps_outputs dict
                "INPUT": outputs["EliminateSelectedPolygonsGaps"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs[f"RefactorFieldsNames_bng{parameters['Layer_type']}"] is not None

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}

        # Delete holes
        outputs["DeleteHoles"] = processing.run(
            "native:deleteholes",
            {
                "INPUT": outputs[f"RefactorFieldsNames_bng{parameters['Layer_type']}"][
                    "OUTPUT"
                ],
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
                "OUTPUT": parameters["fixed_BNG_output"],
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FieldCalculatorArea"] is not None

        results["fixed_BNG_output"] = outputs["FieldCalculatorArea"]["OUTPUT"]
        context.layerToLoadOnCompletionDetails(
            results["fixed_BNG_output"]
        ).name = "fixed_BNG_output"
        return results

    def icon(self) -> QIcon:
        return QIcon(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "icons",
                "Fix_layer_BNG.svg",
            )
        )

    def shortHelpString(self) -> str:
        text = """<b>General:</b><br>\
    Cleans and fixes a Spatialsesh BNG polygon layer by repairing invalid geometries, removing duplicate and small polygons, snapping geometries, and eliminating gaps. The output fields are configured according to the selected BNG layer type selected (Master, Baseline, or Proposed) so that the output can be exported to the NE metric.<br><br>\
    <b>Parameters:</b><br>\
    The following parameters must be defined to execute the algorithm:
    <ul><li>Layer type: Select whether the input layer is a Master, Baseline, or Proposed BNG layer.</li><li>Polygon layer to fix</li><li>Minimum Mappable Unit (m2)</li><li>Snapping tolerance (m)</li><li>Output CRS</li><li> Set file path for interim results - <b>Advanced parameter with a default value</b></li> </ul><br>\
    <b>Output:</b><br>\
    Produces a fixed polygon layer with repaired geometries, small polygons, slivers and gaps and duplicate features removed, and fields standardized according to the selected BNG layer type.<br>\
    """

        return text

    def name(self) -> str:
        return "FixLayer_BNG"

    def displayName(self) -> str:
        return "Fix layer BNG"

    def group(self) -> str:
        return ""

    def groupId(self) -> str:
        return ""

    def createInstance(self):
        return self.__class__()
