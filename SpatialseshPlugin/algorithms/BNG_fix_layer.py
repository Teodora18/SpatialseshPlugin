from typing import Any, Optional

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import Qgis
from qgis import processing

from ..utils.fix_layer import fix_layer_main_pipeline


class BNG_FixLayerAlgorithm(QgsProcessingAlgorithm):
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
                "final_cleaned_output",
                type=Qgis.ProcessingSourceType.VectorPolygon,
                createByDefault=True,
                supportsAppend=True,
                defaultValue="TEMPORARY_OUTPUT",
            )
        )

    def create_text_field(self, expression, name, length=0) -> dict[str, Any]:
        return {
            "alias": None,
            "comment": None,
            "expression": expression,
            "length": length,
            "name": name,
            "precision": 0,
            "sub_type": 0,
            "type": 10,
            "type_name": "text",
        }

    def create_int_field(self, expression, name, length=0) -> dict[str, Any]:
        return {
            "alias": None,
            "comment": None,
            "expression": expression,
            "length": length,
            "name": name,
            "precision": 0,
            "sub_type": 0,
            "type": 4,
            "type_name": "int8",
        }

    def create_date_field(self, expression, name, length=0) -> dict[str, Any]:
        return {
            "alias": None,
            "comment": None,
            "expression": expression,
            "length": length,
            "name": name,
            "precision": 0,
            "sub_type": 0,
            "type": 14,
            "type_name": "date",
        }

    def get_field_mapping(self, bng_type) -> list[dict[str, Any]]:
        create_fields = {
            "PARCEL_REF": lambda: self.create_text_field(
                "Parcel_Ref", "Parcel Ref", 99
            ),
            "BASELINE_BROAD_HABITAT_TYPE": lambda: self.create_text_field(
                "Baseline_Broad_Habitat_Type", "Baseline Broad Habitat Type", 99
            ),
            "BASELINE_HABITAT_TYPE": lambda: self.create_text_field(
                "Baseline_Habitat_Type",
                "Baseline Habitat Type",
                99,
            ),
            "AREA": lambda: self.create_int_field("Area", "Area"),
            "BASELINE_CONDITION": lambda: self.create_text_field(
                "Baseline_Condition",
                "Baseline Condition",
                99,
            ),
            "BASELINE_STRATEGIC_SIGNIFICANCE": lambda: self.create_text_field(
                "Baseline_Strategic_Significance",
                "Baseline Strategic Significance",
                99,
            ),
            "RETENTION_CATEGORY": lambda: self.create_text_field(
                "Retention_Category",
                "Retention Category",
                99,
            ),
            "LOCATION": lambda: self.create_text_field("Location", "Location", 99),
            "PROPOSED_BROAD_HABITAT_TYPE": lambda: self.create_text_field(
                "Proposed_Broad_Habitat_Type",
                "Proposed Broad Habitat Type",
                99,
            ),
            "PROPOSED_HABITAT_TYPE": lambda: self.create_text_field(
                "Proposed_Habitat_Type",
                "Proposed Habitat Type",
                99,
            ),
            "PROPOSED_CONDITION": lambda: self.create_text_field(
                "Proposed_Condition",
                "Proposed Condition",
                99,
            ),
            "PROPOSED_STRATEGIC_SIGNIFICANCE": lambda: self.create_text_field(
                "Proposed_Strategic_Significance",
                "Proposed Strategic Significance",
                99,
            ),
            "HABITAT_CREATED_IN_ADVANCE_YEARS": lambda: self.create_text_field(
                "Habitat_created_in_advance_years",
                "Habitat created in advance/years",
                99,
            ),
            "DELAY_IN_STARTING_HABITAT_CREATION_YEARS": lambda: self.create_text_field(
                "Delay_in_starting_habitat_creation_years",
                "Delay in starting habitat creation/years",
                99,
            ),
            "SPATIAL_RISK_CATEGORY": lambda: self.create_text_field(
                "Spatial_risk_category",
                "Spatial risk category",
                99,
            ),
            "SITE_NAME": lambda: self.create_text_field("Site_Name", "Site Name"),
            "SURVEY_DATE": lambda: self.create_date_field("Survey_Date", "Survey Date"),
            "SURVEY_DETAILS": lambda: self.create_text_field(
                "Survey_Details", "Survey Details"
            ),
            "COMMENT": lambda: self.create_text_field("Comment", "Comment"),
            "MAPPED_BY": lambda: self.create_text_field("Mapped_by", "Mapped by"),
            "COMPANY": lambda: self.create_text_field("Company", "Company"),
            "BASE_MAP": lambda: self.create_text_field("Base_Map", "Base Map"),
            "BASELINE_DISTINCTIVENESS": lambda: self.create_text_field(
                "Baseline_Distinctiveness",
                "Baseline Distinctiveness",
                999,
            ),
            "PROPOSED_DISTINCTIVENESS": lambda: self.create_text_field(
                "Proposed_Distinctiveness",
                "Proposed Distinctiveness",
                999,
            ),
            "PHOTO": lambda: self.create_text_field("Photo", "Photo"),
            "UKHAB_LV1": lambda: self.create_text_field("UKhabLv1", "UKhabLv1"),
            "UKHAB_LV1_CODE": lambda: self.create_text_field(
                "UKhabLv1_Code", "UKhabLv1_Code"
            ),
            "UKHAB_LV2": lambda: self.create_text_field("UKHabLv2", "UKhabLv2"),
            "UKHAB_LV2_CODE": lambda: self.create_text_field(
                "UKhabLv2_Code", "UKhabLv2_Code"
            ),
            "UKHAB_LV3": lambda: self.create_text_field("UKhabLv3", "UKhabLv3"),
            "UKHAB_LV3_CODE": lambda: self.create_text_field(
                "UKhabLv3_Code", "UKhabLv3_Code"
            ),
            "UKHAB_LV4": lambda: self.create_text_field("UKhabLv4", "UKhabLv4"),
            "UKHAB_LV4_CODE": lambda: self.create_text_field(
                "UKhabLv4_Code", "UKhabLv4_Code"
            ),
            "UKHAB_LV5": lambda: self.create_text_field("UKhabLv5", "UKhabLv5"),
            "UKHAB_LV5_CODE": lambda: self.create_text_field(
                "UKhabLv5_Code", "UKhabLv5_Code"
            ),
            "ESSENTIAL_SECONDARY_CODE": lambda: self.create_text_field(
                "EssentialSecondaryCode",
                "EssentialSecondaryCode",
            ),
            "ESSENTIAL_CODE_LABEL": lambda: self.create_text_field(
                "EssentialCodeLabel",
                "EssentialCodeLabel",
            ),
            "ADDITIONAL_SECONDARY_CODE": lambda: self.create_text_field(
                "AdditionalSecondaryCode",
                "AdditionalSecondaryCode",
            ),
            "ASSOCIATED_CODE_LABEL": lambda: self.create_text_field(
                "AssociatedCodeLabel",
                "AssociatedCodeLabel",
            ),
            "UKHABITAT": lambda: self.create_text_field("UKhabitat", "UKhabitat"),
            "UKHAB_CODE": lambda: self.create_text_field("UKhabCode", "UKhabCode"),
            "PREVIOUS_SURVEY": lambda: self.create_text_field(
                "PreviousSurvey",
                "PreviousSurvey",
            ),
            "SITE": lambda: self.create_text_field(
                "Site",
                "Site",
            ),
            "HABITAT_MANAGEMENT": lambda: self.create_text_field(
                "HabitatManagement",
                "HabitatManagement",
            ),
            "GUIDANCE": lambda: self.create_text_field(
                "Guidance",
                "Guidance",
            ),
            "GUIDANCE_Q": lambda: self.create_text_field(
                "Guidance_Q",
                "Guidance_Q",
            ),
        }

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
                    "BASELINE_BROAD_HABITAT_TYPE",
                    "BASELINE_HABITAT_TYPE",
                    "AREA",
                    "BASELINE_CONDITION",
                    "BASELINE_STRATEGIC_SIGNIFICANCE",
                    "RETENTION_CATEGORY",
                    "LOCATION",
                    "PROPOSED_BROAD_HABITAT_TYPE",
                    "PROPOSED_HABITAT_TYPE",
                    "PROPOSED_CONDITION",
                    "PROPOSED_STRATEGIC_SIGNIFICANCE",
                    "HABITAT_CREATED_IN_ADVANCE_YEARS",
                    "DELAY_IN_STARTING_HABITAT_CREATION_YEARS",
                    "SPATIAL_RISK_CATEGORY",
                ]
                + COMMON_ADDITIONAL_FIELDS
                + ["BASELINE_DISTINCTIVENESS", "PROPOSED_DISTINCTIVENESS", "PHOTO"]
            ),
            1: (  # BASELINE
                [
                    "PARCEL_REF",
                    "UKHAB_LV1",
                    "UKHAB_LV1_CODE",
                    "UKHAB_LV2",
                    "UKHAB_LV2_CODE",
                    "UKHAB_LV3",
                    "UKHAB_LV3_CODE",
                    "UKHAB_LV4",
                    "UKHAB_LV4_CODE",
                    "UKHAB_LV5",
                    "UKHAB_LV5_CODE",
                    "ESSENTIAL_SECONDARY_CODE",
                    "ESSENTIAL_CODE_LABEL",
                    "ADDITIONAL_SECONDARY_CODE",
                    "ASSOCIATED_CODE_LABEL",
                    "BASELINE_BROAD_HABITAT_TYPE",
                    "BASELINE_HABITAT_TYPE",
                    "BASELINE_CONDITION",
                    "BASELINE_STRATEGIC_SIGNIFICANCE",
                    "RETENTION_CATEGORY",
                    "LOCATION",
                    "BASELINE_DISTINCTIVENESS",
                    "AREA",
                    "UKHABITAT",
                    "UKHAB_CODE",
                ]
                + COMMON_ADDITIONAL_FIELDS
                + [
                    "PHOTO",
                    "PREVIOUS_SURVEY",
                    "SITE",
                    "HABITAT_MANAGEMENT",
                    "GUIDANCE",
                    "GUIDANCE_Q",
                ]
            ),
            2: (  # PROPOSED
                [
                    "PROPOSED_BROAD_HABITAT_TYPE",
                    "PROPOSED_HABITAT_TYPE",
                    "PROPOSED_CONDITION",
                    "PROPOSED_STRATEGIC_SIGNIFICANCE",
                    "HABITAT_CREATED_IN_ADVANCE_YEARS",
                    "DELAY_IN_STARTING_HABITAT_CREATION_YEARS",
                    "SPATIAL_RISK_CATEGORY",
                    "LOCATION",
                ]
                + COMMON_ADDITIONAL_FIELDS
                + [
                    "PROPOSED_DISTINCTIVENESS",
                    "PHOTO",
                    "AREA",
                ]
            ),
        }
        if bng_type not in field_mapping_by_bng_type.keys():
            raise NotImplementedError(
                "Unexpected BNG layer type. Layer type must be 'Master', 'Baseline' or 'Proposed'"
            )
        return [create_fields[key]() for key in field_mapping_by_bng_type[bng_type]]

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, str]:
        feedback = QgsProcessingMultiStepFeedback(27, feedback)
        results: dict[str, str] = {}
        outputs: dict[str, Any] = {}

        # Fix layer with the main pipeline of algorithms

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

        # QgsProject.instance().addMapLayer(outputs["EliminateSelectedPolygonsGaps"]['OUTPUT'])

        # Refactor fields - names
        refactor_fields_params: list[dict[str, Any]] = self.get_field_mapping(
            parameters["Layer_type"]
        )

        outputs[f"RefactorFieldsNames_bng{parameters['Layer_type']}"] = processing.run(
            "native:refactorfields",
            {
                "FIELDS_MAPPING": refactor_fields_params,
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
        return "BNG_FixLayer"

    def displayName(self) -> str:
        return "BNG_FixLayer"

    def group(self) -> str:
        return ""

    def groupId(self) -> str:
        return ""

    def createInstance(self):
        return self.__class__()
