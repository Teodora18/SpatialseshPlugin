# TODOs:
# - fix the feedback numbering
# - create a function for the processing of the three separated layers
# - fix the conditions on which each layer's fields are refactored


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
from qgis import processing


class BNG_FixLayerAlgorithm(QgsProcessingAlgorithm):

    def initAlgorithm(self, configuration: Optional[dict[str, Any]] = None):
        self.addParameter(
            QgsProcessingParameterEnum(
                "Layer_type",
                "Select a layer type to fix",
                options=[
                    "Baseline",
                    "Proposed",
                    "Master",
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

    def create_text_field(self, expression, name, length=0):
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
    
    def create_int_field(self, expression, name, length=0):
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
    
    def create_date_field(self, expression, name, length=0):
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

    def get_field_mapping(self):
        PARCEL_REF = self.create_text_field("Parcel_Ref", "Parcel Ref", 99)



        pass

    def processBNGlayer(
        self,
        bng_type,
        input_layer,
        refactor_fields_params: list[dict[str, Any]],
        outputs_bng: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ):

        feedback = QgsProcessingMultiStepFeedback(4, feedback)

        # Refactor fields - names
        outputs_bng[f"RefactorFieldsNames{bng_type}"] = processing.run(
            "native:refactorfields",
            {
                "FIELDS_MAPPING": refactor_fields_params,
                "INPUT": input_layer,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Drop field - fid
        alg_params = {
            "COLUMN": QgsExpression("'fid;cat;gap;path'").evaluate(),
            "INPUT": outputs_bng[f"RefactorFieldsNames{bng_type}"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs_bng[f"DropFieldFid{bng_type}"] = processing.run(
            "native:deletecolumn",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Delete holes
        alg_params = {
            "INPUT": outputs_bng[f"DropFieldFid{bng_type}"]["OUTPUT"],
            "MIN_AREA": 0.1,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs_bng[f"DeleteHoles{bng_type}"] = processing.run(
            "native:deleteholes",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Field calculator - area
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Area",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 1,  # Integer (32 bit)
            "FORMULA": "area($geometry)",
            "INPUT": outputs_bng[f"DeleteHoles{bng_type}"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs_bng[f"FieldCalculatorArea{bng_type}"] = processing.run(
            "native:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}
        pass

        return outputs_bng[f"FieldCalculatorArea{bng_type}"]["OUTPUT"]

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, Any]:

        feedback = QgsProcessingMultiStepFeedback(41, feedback)
        results: dict[str, Any] = {}
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

        # Conditional branch
        outputs["ConditionalBranch"] = processing.run(
            "native:condition",
            {},
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(3)
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

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Rename field
        outputs["RenameField"] = processing.run(
            "native:renametablefield",
            {
                "FIELD": "fid",
                "INPUT": outputs["ReprojectLayer"]["OUTPUT"],
                "NEW_NAME": "id",
                "OUTPUT": QgsExpression(
                    " @temporary_file_path_before_cleaning"
                ).evaluate(),
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["RenameField"] is not None

        feedback.setCurrentStep(5)
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

        feedback.setCurrentStep(6)
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

        feedback.setCurrentStep(7)
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

        feedback.setCurrentStep(8)
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

        feedback.setCurrentStep(9)
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

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Select by expression
        outputs["SelectByExpression"] = processing.run(
            "qgis:selectbyexpression",
            {
                "EXPRESSION": "area($geometry) < @filter_small_polygons_size_m2  ",
                "INPUT": outputs["RemoveNullGeometries"]["OUTPUT"],
                "METHOD": 0,  # creating new selection
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["SelectByExpression"] is not None

        feedback.setCurrentStep(11)
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

        feedback.setCurrentStep(12)
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

        feedback.setCurrentStep(13)
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

        feedback.setCurrentStep(14)
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

        feedback.setCurrentStep(15)
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

        feedback.setCurrentStep(16)
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

        feedback.setCurrentStep(17)
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

        feedback.setCurrentStep(18)
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

        feedback.setCurrentStep(19)
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

        feedback.setCurrentStep(20)
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

        feedback.setCurrentStep(21)
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

        feedback.setCurrentStep(22)
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

        feedback.setCurrentStep(23)
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

        feedback.setCurrentStep(24)
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

        feedback.setCurrentStep(25)
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

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}

        # Refactor fields - names
        alg_params = {
            "FIELDS_MAPPING": [
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Parcel_Ref",
                    "length": 99,
                    "name": "Parcel Ref",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Broad_Habitat_Type",
                    "length": 99,
                    "name": "Baseline Broad Habitat Type",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Habitat_Type",
                    "length": 99,
                    "name": "Baseline Habitat Type",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Area",
                    "length": 0,
                    "name": "Area",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 2,
                    "type_name": "integer",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Condition",
                    "length": 99,
                    "name": "Baseline Condition",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Strategic_Significance",
                    "length": 99,
                    "name": "Baseline Strategic Significance",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Retention_Category",
                    "length": 99,
                    "name": "Retention Category",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Location",
                    "length": 99,
                    "name": "Location",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Broad_Habitat_Type",
                    "length": 99,
                    "name": "Proposed Broad Habitat Type",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Habitat_Type",
                    "length": 99,
                    "name": "Proposed Habitat Type",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Condition",
                    "length": 99,
                    "name": "Proposed Condition",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Strategic_Significance",
                    "length": 99,
                    "name": "Proposed Strategic Significance",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Habitat_created_in_advance_years",
                    "length": 99,
                    "name": "Habitat created in advance/years",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Delay_in_starting_habitat_creation_years",
                    "length": 99,
                    "name": "Delay in starting habitat creation/years",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Spatial_risk_category",
                    "length": 99,
                    "name": "Spatial risk category",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Site_Name",
                    "length": 0,
                    "name": "Site Name",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Survey_Date",
                    "length": 0,
                    "name": "Survey Date",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 14,
                    "type_name": "date",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Survey_Details",
                    "length": 0,
                    "name": "Survey Details",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Comment",
                    "length": 0,
                    "name": "Comment",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Mapped_by",
                    "length": 0,
                    "name": "Mapped by",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Company",
                    "length": 0,
                    "name": "Company",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Base_Map",
                    "length": 0,
                    "name": "Base Map",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Distinctiveness",
                    "length": 999,
                    "name": "Baseline Distinctiveness",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Distinctiveness",
                    "length": 999,
                    "name": "Proposed Distinctiveness",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Photo",
                    "length": 0,
                    "name": "Photo",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
            ],
            "INPUT": outputs["EliminateSelectedPolygonsGaps"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["RefactorFieldsNames"] = processing.run(
            "native:refactorfields",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(27)
        if feedback.isCanceled():
            return {}

        # Drop field - fid
        alg_params = {
            "COLUMN": QgsExpression("'fid;cat;gap;path'").evaluate(),
            "INPUT": outputs["RefactorFieldsNames"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["DropFieldFid"] = processing.run(
            "native:deletecolumn",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(36)
        if feedback.isCanceled():
            return {}

        # Delete holes
        alg_params = {
            "INPUT": outputs["DropFieldFid"]["OUTPUT"],
            "MIN_AREA": 0.1,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["DeleteHoles"] = processing.run(
            "native:deleteholes",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(38)
        if feedback.isCanceled():
            return {}

        # Field calculator - area
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Area",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 1,  # Integer (32 bit)
            "FORMULA": "area($geometry)",
            "INPUT": outputs["DeleteHoles"]["OUTPUT"],
            "OUTPUT": parameters["Final_cleaned_output"],
        }
        outputs["FieldCalculatorArea"] = processing.run(
            "native:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        results["Final_cleaned_output"] = outputs["FieldCalculatorArea"]["OUTPUT"]

        feedback.setCurrentStep(40)
        if feedback.isCanceled():
            return {}

        # Refactor fields - names baseline
        alg_params = {
            "FIELDS_MAPPING": [
                {
                    "alias": None,
                    "comment": None,
                    "expression": "fid",
                    "length": 0,
                    "name": "fid",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 4,
                    "type_name": "int8",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Parcel_Ref",
                    "length": 99,
                    "name": "Parcel Ref",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv1",
                    "length": 0,
                    "name": "UKhabLv1",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv1_Code",
                    "length": 0,
                    "name": "UKhabLv1_Code",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKHabLv2",
                    "length": 0,
                    "name": "UKhabLv2",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv2_Code",
                    "length": 0,
                    "name": "UKhabLv2_Code",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv3",
                    "length": 0,
                    "name": "UKhabLv3",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv3_Code",
                    "length": 0,
                    "name": "UKhabLv3_Code",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv4",
                    "length": 0,
                    "name": "UKhabLv4",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv4_Code",
                    "length": 0,
                    "name": "UKhabLv4_Code",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv5",
                    "length": 0,
                    "name": "UKhabLv5",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabLv5_Code",
                    "length": 0,
                    "name": "UKhabLv5_Code",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "EssentialSecondaryCode",
                    "length": 0,
                    "name": "EssentialSecondaryCode",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "EssentialCodeLabel",
                    "length": 0,
                    "name": "EssentialCodeLabel",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "AdditionalSecondaryCode",
                    "length": 0,
                    "name": "AdditionalSecondaryCode",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "AssociatedCodeLabel",
                    "length": 0,
                    "name": "AssociatedCodeLabel",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Broad_Habitat_Type",
                    "length": 99,
                    "name": "Baseline Broad Habitat Type",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Habitat_Type",
                    "length": 99,
                    "name": "Baseline Habitat Type",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Condition",
                    "length": 99,
                    "name": "Baseline Condition",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Strategic_Significance",
                    "length": 99,
                    "name": "Baseline Strategic Significance",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Retention_Category",
                    "length": 99,
                    "name": "Retention Category",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Location",
                    "length": 99,
                    "name": "Location",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Baseline_Distinctiveness",
                    "length": 999,
                    "name": "Baseline Distinctiveness",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Area",
                    "length": 0,
                    "name": "Area",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 2,
                    "type_name": "integer",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabitat",
                    "length": 0,
                    "name": "UKhabitat",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "UKhabCode",
                    "length": 0,
                    "name": "UKhabCode",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Site_Name",
                    "length": 0,
                    "name": "Site Name",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Survey_Date",
                    "length": 0,
                    "name": "Survey Date",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 14,
                    "type_name": "date",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Survey_Details",
                    "length": 0,
                    "name": "Survey Details",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Comment",
                    "length": 0,
                    "name": "Comment",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Mapped_by",
                    "length": 0,
                    "name": "Mapped by",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Company",
                    "length": 0,
                    "name": "Company",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Base_Map",
                    "length": 0,
                    "name": "Base Map",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Photo",
                    "length": 0,
                    "name": "Photo",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "PreviousSurvey",
                    "length": 0,
                    "name": "PreviousSurvey",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Site",
                    "length": 0,
                    "name": "Site",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "HabitatManagement",
                    "length": 0,
                    "name": "HabitatManagement",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Guidance",
                    "length": 0,
                    "name": "Guidance",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Guidance_Q",
                    "length": 0,
                    "name": "Guidance_Q",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
            ],
            "INPUT": outputs["EliminateSelectedPolygonsGaps"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["RefactorFieldsNamesBaseline"] = processing.run(
            "native:refactorfields",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(31)
        if feedback.isCanceled():
            return {}

        # Drop field - fid baseline
        alg_params = {
            "COLUMN": QgsExpression("'fid;cat;gap;path'").evaluate(),
            "INPUT": outputs["RefactorFieldsNamesBaseline"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["DropFieldFidBaseline"] = processing.run(
            "native:deletecolumn",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(33)
        if feedback.isCanceled():
            return {}

        # Delete holes baseline
        alg_params = {
            "INPUT": outputs["DropFieldFidBaseline"]["OUTPUT"],
            "MIN_AREA": 0.1,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["DeleteHolesBaseline"] = processing.run(
            "native:deleteholes",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(34)
        if feedback.isCanceled():
            return {}

        # Field calculator - area baseline
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Area",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 1,  # Integer (32 bit)
            "FORMULA": "area($geometry)",
            "INPUT": outputs["DeleteHolesBaseline"]["OUTPUT"],
            "OUTPUT": parameters["Final_cleaned_output"],
        }
        outputs["FieldCalculatorAreaBaseline"] = processing.run(
            "native:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        results["Final_cleaned_output"] = outputs["FieldCalculatorAreaBaseline"][
            "OUTPUT"
        ]

        feedback.setCurrentStep(37)
        if feedback.isCanceled():
            return {}

        # Refactor fields - names proposed
        alg_params = {
            "FIELDS_MAPPING": [
                {
                    "alias": None,
                    "comment": None,
                    "expression": "fid",
                    "length": 0,
                    "name": "fid",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 4,
                    "type_name": "int8",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Area",
                    "length": 0,
                    "name": "Area",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 2,
                    "type_name": "integer",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Broad_Habitat_Type",
                    "length": 99,
                    "name": "Proposed Broad Habitat Type",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Habitat_Type",
                    "length": 99,
                    "name": "Proposed Habitat Type",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Condition",
                    "length": 99,
                    "name": "Proposed Condition",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Strategic_Significance",
                    "length": 99,
                    "name": "Proposed Strategic Significance",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Habitat_created_in_advance_years",
                    "length": 99,
                    "name": "Habitat created in advance/years",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Delay_in_starting_habitat_creation_years",
                    "length": 99,
                    "name": "Delay in starting habitat creation/years",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Spatial_risk_category",
                    "length": 99,
                    "name": "Spatial risk category",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Location",
                    "length": 99,
                    "name": "Location",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Site_Name",
                    "length": 0,
                    "name": "Site Name",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Survey_Date",
                    "length": 0,
                    "name": "Survey Date",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 14,
                    "type_name": "date",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Survey_Details",
                    "length": 0,
                    "name": "Survey Details",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Comment",
                    "length": 0,
                    "name": "Comment",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Mapped_by",
                    "length": 0,
                    "name": "Mapped by",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Company",
                    "length": 0,
                    "name": "Company",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Base_Map",
                    "length": 0,
                    "name": "Base Map",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Proposed_Distinctiveness",
                    "length": 999,
                    "name": "Proposed Distinctiveness",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
                {
                    "alias": None,
                    "comment": None,
                    "expression": "Photo",
                    "length": 0,
                    "name": "Photo",
                    "precision": 0,
                    "sub_type": 0,
                    "type": 10,
                    "type_name": "text",
                },
            ],
            "INPUT": outputs["EliminateSelectedPolygonsGaps"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["RefactorFieldsNamesProposed"] = processing.run(
            "native:refactorfields",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(32)
        if feedback.isCanceled():
            return {}

        # Drop field - fid proposed
        alg_params = {
            "COLUMN": QgsExpression("'fid;cat;gap;path'").evaluate(),
            "INPUT": outputs["RefactorFieldsNamesProposed"]["OUTPUT"],
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["DropFieldFidProposed"] = processing.run(
            "native:deletecolumn",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(35)
        if feedback.isCanceled():
            return {}

        # Delete holes proposed
        alg_params = {
            "INPUT": outputs["DropFieldFidProposed"]["OUTPUT"],
            "MIN_AREA": 0.1,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["DeleteHolesProposed"] = processing.run(
            "native:deleteholes",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(39)
        if feedback.isCanceled():
            return {}

        # Field calculator - area proposed
        alg_params = {
            "FIELD_LENGTH": 0,
            "FIELD_NAME": "Area",
            "FIELD_PRECISION": 0,
            "FIELD_TYPE": 1,  # Integer (32 bit)
            "FORMULA": "area($geometry)",
            "INPUT": outputs["DeleteHolesProposed"]["OUTPUT"],
            "OUTPUT": parameters["Final_cleaned_output"],
        }
        outputs["FieldCalculatorAreaProposed"] = processing.run(
            "native:fieldcalculator",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )
        results["Final_cleaned_output"] = outputs["FieldCalculatorAreaProposed"][
            "OUTPUT"
        ]
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
