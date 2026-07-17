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
from qgis.core import QgsExpression
from qgis.core import Qgis
from qgis.core import QgsProject
from qgis import processing


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
                type=QgsProcessingParameterNumber.Double,  # type: ignore
                defaultValue=10,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                "snapping_tolerance_m",
                "Snapping tolerance (m)",
                type=QgsProcessingParameterNumber.Double,  # type: ignore
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
                behavior=QgsProcessingParameterFile.File,  # type: ignore
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
        "PARCEL_REF": lambda: self.create_text_field("Parcel_Ref", "Parcel Ref", 99),
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
        "SURVEY_DETAILS": lambda: self.create_text_field("Survey_Details", "Survey Details"),
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
        "UKHAB_LV1_CODE": lambda: self.create_text_field("UKhabLv1_Code", "UKhabLv1_Code"),
        "UKHAB_LV2": lambda: self.create_text_field("UKHabLv2", "UKhabLv2"),
        "UKHAB_LV2_CODE": lambda: self.create_text_field("UKhabLv2_Code", "UKhabLv2_Code"),
        "UKHAB_LV3": lambda: self.create_text_field("UKhabLv3", "UKhabLv3"),
        "UKHAB_LV3_CODE": lambda: self.create_text_field("UKhabLv3_Code", "UKhabLv3_Code"),
        "UKHAB_LV4": lambda: self.create_text_field("UKhabLv4", "UKhabLv4"),
        "UKHAB_LV4_CODE": lambda: self.create_text_field("UKhabLv4_Code", "UKhabLv4_Code"),
        "UKHAB_LV5": lambda: self.create_text_field("UKhabLv5", "UKhabLv5"),
        "UKHAB_LV5_CODE": lambda: self.create_text_field("UKhabLv5_Code", "UKhabLv5_Code"),
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
        )
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
            0 : ( # MASTER
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
            1 : ( # BASELINE
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
            2 : ( # PROPOSED
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
                + ["PROPOSED_DISTINCTIVENESS", "PHOTO", "AREA",]
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

        feedback = QgsProcessingMultiStepFeedback(28, feedback)
        results: dict[str, str] = {}
        outputs: dict[str, Any] = {}

        # Fix geometries

        outputs["FixGeometries"] = processing.run(
            "native:fixgeometries",
            {
                "INPUT": parameters["polygon_layer_to_clean"],
                "METHOD": 0,  # Linework
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FixGeometries"] is not None

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Check validity
        outputs["CheckValidity"] = processing.run(
            "qgis:checkvalidity",
            {
                "IGNORE_RING_SELF_INTERSECTION": False,
                "INPUT_LAYER": outputs["FixGeometries"]["OUTPUT"],
                "METHOD": 2,  # GEOS
                "VALID_OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["CheckValidity"] is not None

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Reproject layer
        outputs["ReprojectLayer"] = processing.run(
            "native:reprojectlayer",
            {
                "CONVERT_CURVED_GEOMETRIES": False,
                "INPUT": outputs["CheckValidity"]["VALID_OUTPUT"],
                "OPERATION": None,
                "TARGET_CRS": parameters["crs_to_reproject"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["ReprojectLayer"] is not None

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Rename field
        outputs["RenameField"] = processing.run(
            "native:renametablefield",
            {
                "FIELD": "fid",
                "INPUT": outputs["ReprojectLayer"]["OUTPUT"],
                "NEW_NAME": "id",
                "OUTPUT": f"{parameters['temporary_file_path_before_cleaning']}",
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["RenameField"] is not None

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # v.clean
        outputs["Vclean"] = processing.run(
            "grass:v.clean",
            {
                "-b": False,
                "-c": False,
                "GRASS_MIN_AREA_PARAMETER": 0.0001,
                "GRASS_OUTPUT_TYPE_PARAMETER": 0,  # auto
                "GRASS_REGION_PARAMETER": None,
                "GRASS_SNAP_TOLERANCE_PARAMETER": -1,
                "GRASS_VECTOR_DSCO": None,
                "GRASS_VECTOR_EXPORT_NOCAT": False,
                "GRASS_VECTOR_LCO": None,
                "input": outputs["RenameField"]["OUTPUT"],
                "threshold": None,
                "tool": [0],  # break
                "type": [4],  # area
                "error": QgsProcessing.TEMPORARY_OUTPUT,
                "output": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["Vclean"] is not None

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Fix geometries - v.clean
        outputs["FixGeometriesVclean"] = processing.run(
            "native:fixgeometries",
            {
                "INPUT": outputs["Vclean"]["output"],
                "METHOD": 0,  # Linework
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FixGeometriesVclean"] is not None

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Union
        outputs["Union"] = processing.run(
            "native:union",
            {
                "GRID_SIZE": None,
                "INPUT": outputs["FixGeometriesVclean"]["OUTPUT"],
                "OVERLAY": None,
                "OVERLAY_FIELDS_PREFIX": None,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["Union"] is not None

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Delete duplicate geometries
        outputs["DeleteDuplicateGeometries"] = processing.run(
            "native:deleteduplicategeometries",
            {
                "INPUT": outputs["Union"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["DeleteDuplicateGeometries"] is not None

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Remove null geometries
        outputs["RemoveNullGeometries"] = processing.run(
            "native:removenullgeometries",
            {
                "INPUT": outputs["DeleteDuplicateGeometries"]["OUTPUT"],
                "REMOVE_EMPTY": True,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["RemoveNullGeometries"] is not None

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Select by expression
        outputs["SelectByExpression"] = processing.run(
            "qgis:selectbyexpression",
            {
                "EXPRESSION": f"area($geometry) < {parameters['filter_small_polygons_size_m2']}",
                "INPUT": outputs["RemoveNullGeometries"]["OUTPUT"],
                "METHOD": 0,  # creating new selection
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["SelectByExpression"] is not None

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Eliminate selected polygons
        outputs["EliminateSelectedPolygons"] = processing.run(
            "qgis:eliminateselectedpolygons",
            {
                "INPUT": outputs["SelectByExpression"]["OUTPUT"],
                "MODE": 2,  # Largest Common Boundary
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["EliminateSelectedPolygons"] is not None

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Multipart to singleparts
        outputs["MultipartToSingleparts"] = processing.run(
            "native:multiparttosingleparts",
            {
                "INPUT": outputs["EliminateSelectedPolygons"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["MultipartToSingleparts"] is not None

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Convert geometry type
        outputs["ConvertGeometryType"] = processing.run(
            "qgis:convertgeometrytype",
            {
                "INPUT": outputs["MultipartToSingleparts"]["OUTPUT"],
                "TYPE": 4,  # Polygons
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["ConvertGeometryType"] is not None

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # Remove duplicate vertices
        outputs["RemoveDuplicateVertices"] = processing.run(
            "native:removeduplicatevertices",
            {
                "INPUT": outputs["ConvertGeometryType"]["OUTPUT"],
                "TOLERANCE": 0.01,
                "USE_Z_VALUE": False,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["RemoveDuplicateVertices"] is not None

        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}

        # Extract by expression
        # for small polygons with no neighbous
        outputs["ExtractByExpression"] = processing.run(
            "native:extractbyexpression",
            {
                "EXPRESSION": "area($geometry) > 0.50",
                "INPUT": outputs["RemoveDuplicateVertices"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["ExtractByExpression"] is not None

        feedback.setCurrentStep(15)
        if feedback.isCanceled():
            return {}

        # Snap geometries to layer
        outputs["SnapGeometriesToLayer"] = processing.run(
            "native:snapgeometries",
            {
                "BEHAVIOR": 0,  # Prefer aligning nodes, insert extra vertices where required
                "INPUT": outputs["ExtractByExpression"]["OUTPUT"],
                "REFERENCE_LAYER": outputs["ExtractByExpression"]["OUTPUT"],
                "TOLERANCE": parameters["snapping_tolerance_m"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["SnapGeometriesToLayer"] is not None

        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}

        # Fix geometries - snap
        outputs["FixGeometriesSnap"] = processing.run(
            "native:fixgeometries",
            {
                "INPUT": outputs["SnapGeometriesToLayer"]["OUTPUT"],
                "METHOD": 0,  # Linework
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FixGeometriesSnap"] is not None

        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}

        # Dissolve
        outputs["Dissolve"] = processing.run(
            "native:dissolve",
            {
                "FIELD": [""],
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

        # Symmetrical difference
        outputs["SymmetricalDifference"] = processing.run(
            "native:symmetricaldifference",
            {
                "GRID_SIZE": None,
                "INPUT": outputs["FixGeometriesSnap"]["OUTPUT"],
                "OVERLAY": outputs["DeleteHolesDissolve"]["OUTPUT"],
                "OVERLAY_FIELDS_PREFIX": None,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["SymmetricalDifference"] is not None

        feedback.setCurrentStep(20)
        if feedback.isCanceled():
            return {}

        # Multipart to singleparts - symmetrical difference
        outputs["MultipartToSinglepartsSymmetricalDifference"] = processing.run(
            "native:multiparttosingleparts",
            {
                "INPUT": outputs["SymmetricalDifference"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["MultipartToSinglepartsSymmetricalDifference"] is not None

        feedback.setCurrentStep(21)
        if feedback.isCanceled():
            return {}

        # Field calculator - gaps
        outputs["FieldCalculatorGaps"] = processing.run(
            "native:fieldcalculator",
            {
                "FIELD_LENGTH": 0,
                "FIELD_NAME": "gap",
                "FIELD_PRECISION": 0,
                "FIELD_TYPE": 2,  # Text (string)
                "FORMULA": "'yes'",
                "INPUT": outputs["MultipartToSinglepartsSymmetricalDifference"][
                    "OUTPUT"
                ],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FieldCalculatorGaps"] is not None

        feedback.setCurrentStep(22)
        if feedback.isCanceled():
            return {}

        # Merge vector layers
        outputs["MergeVectorLayers"] = processing.run(
            "native:mergevectorlayers",
            {
                "CRS": None,
                "LAYERS": [
                    outputs["FieldCalculatorGaps"]["OUTPUT"],
                    outputs["FixGeometriesSnap"]["OUTPUT"],
                ],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["MergeVectorLayers"] is not None

        feedback.setCurrentStep(23)
        if feedback.isCanceled():
            return {}

        # Select by expression - gaps
        outputs["SelectByExpressionGaps"] = processing.run(
            "qgis:selectbyexpression",
            {
                "EXPRESSION": "gap = 'yes'",
                "INPUT": outputs["MergeVectorLayers"]["OUTPUT"],
                "METHOD": 0,  # creating new selection
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["SelectByExpressionGaps"] is not None

        feedback.setCurrentStep(24)
        if feedback.isCanceled():
            return {}

        # Eliminate selected polygons - gaps
        outputs["EliminateSelectedPolygonsGaps"] = processing.run(
            "qgis:eliminateselectedpolygons",
            {
                "INPUT": outputs["SelectByExpressionGaps"]["OUTPUT"],
                "MODE": 0,  # Largest Area
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["EliminateSelectedPolygonsGaps"] is not None

        # QgsProject.instance().addMapLayer(outputs["EliminateSelectedPolygonsGaps"]['OUTPUT'])

        feedback.setCurrentStep(25)
        if feedback.isCanceled():
            return {}

        # Refactor fields - names
        refactor_fields_params: list[dict[str, Any]] = self.get_field_mapping(parameters['Layer_type'])

        outputs[f"RefactorFieldsNames_bng{parameters['Layer_type']}"] = processing.run(
            "native:refactorfields",
            {
                "FIELDS_MAPPING": refactor_fields_params,
                "INPUT": outputs["EliminateSelectedPolygonsGaps"]['OUTPUT'],
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

        # Drop field - fid, cat, gap, path
        outputs["DropFields"] = processing.run(
            "native:deletecolumn",
            {
            "COLUMN": QgsExpression("'fid;cat;gap;path'").evaluate(),
            "INPUT": outputs[f"RefactorFieldsNames_bng{parameters['Layer_type']}"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["DropFields"] is not None

        feedback.setCurrentStep(27)
        if feedback.isCanceled():
            return {}

        # Delete holes
        outputs["DeleteHoles"] = processing.run(
            "native:deleteholes",
            {
            "INPUT": outputs["DropFields"]["OUTPUT"],
            "MIN_AREA": 0.1,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["DeleteHoles"] is not None

        feedback.setCurrentStep(28)
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
            "OUTPUT": parameters['Final_cleaned_output'],
        },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FieldCalculatorArea"] is not None

        results["Final_cleaned_output"] = outputs["FieldCalculatorArea"]['OUTPUT']
        context.layerToLoadOnCompletionDetails(results["Final_cleaned_output"]).name = (
            "Final_cleaned_output"
        )
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
