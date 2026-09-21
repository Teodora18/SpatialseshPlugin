"""
Model exported as python.
Name : fix_bng_union_baseline_proposed
Group :
With QGIS : 34408
"""

import os
from typing import Any, Optional

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterCrs
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import Qgis
from qgis import processing

from qgis.PyQt.QtGui import QIcon

from ..utils.fix_layer import fix_layer_basic, fix_layer_main_pipeline2, process_gaps
from ..utils.license_manager import MaplangoLicensedAlgorithm


class Union_BNGAlgorithm(MaplangoLicensedAlgorithm):
    def __init__(self):
        super().__init__()

    def initAlgorithm(self, configuration: Optional[dict[str, Any]] = None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "baseline_layer",
                "Baseline layer",
                types=[Qgis.ProcessingSourceType.VectorPolygon],
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "proposed_layer",
                "Proposed layer",
                types=[Qgis.ProcessingSourceType.VectorPolygon],
                defaultValue=None,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "redline_boundary",
                "Red Line Boundary",
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
                "union_BNG_output",
                "Union BNG output",
                type=Qgis.ProcessingSourceType.VectorPolygon,
                createByDefault=True,
                supportsAppend=True,
                defaultValue=None,
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

    def get_field_mapping(self) -> list[dict[str, Any]]:
        create_fields = {
            "PARCEL_REF": self.create_text_field("Parcel_Ref", "Parcel Ref", 99),
            "BASELINE_BROAD_HABITAT_TYPE": self.create_text_field(
                "Baseline_Broad_Habitat_Type", "Baseline Broad Habitat Type", 99
            ),
            "BASELINE_HABITAT_TYPE": self.create_text_field(
                "Baseline_Habitat_Type",
                "Baseline Habitat Type",
                99,
            ),
            "BASELINE_CONDITION": self.create_text_field(
                "Baseline_Condition",
                "Baseline Condition",
                99,
            ),
            "BASELINE_STRATEGIC_SIGNIFICANCE": self.create_text_field(
                "Baseline_Strategic_Significance",
                "Baseline Strategic Significance",
                99,
            ),
            "RETENTION_CATEGORY": self.create_text_field(
                "Retention_Category",
                "Retention Category",
                99,
            ),
            "LOCATION": self.create_text_field("Location", "Location", 99),
            "BASELINE_DISTINCTIVENESS": self.create_text_field(
                "Baseline_Distinctiveness",
                "Baseline Distinctiveness",
                999,
            ),
            "PROPOSED_BROAD_HABITAT_TYPE": self.create_text_field(
                "Proposed_Broad_Habitat_Type",
                "Proposed Broad Habitat Type",
                99,
            ),
            "PROPOSED_HABITAT_TYPE": self.create_text_field(
                "Proposed_Habitat_Type",
                "Proposed Habitat Type",
                99,
            ),
            "PROPOSED_CONDITION": self.create_text_field(
                "Proposed_Condition",
                "Proposed Condition",
                99,
            ),
            "PROPOSED_STRATEGIC_SIGNIFICANCE": self.create_text_field(
                "Proposed_Strategic_Significance",
                "Proposed Strategic Significance",
                99,
            ),
            "HABITAT_CREATED_IN_ADVANCE_YEARS": self.create_text_field(
                "Habitat_created_in_advance_years",
                "Habitat created in advance/years",
                99,
            ),
            "DELAY_IN_STARTING_HABITAT_CREATION_YEARS": self.create_text_field(
                "Delay_in_starting_habitat_creation_years",
                "Delay in starting habitat creation/years",
                99,
            ),
            "SPATIAL_RISK_CATEGORY": self.create_text_field(
                "Spatial_risk_category",
                "Spatial risk category",
                99,
            ),
            "PROPOSED_DISTINCTIVENESS": self.create_text_field(
                "Proposed_Distinctiveness",
                "Proposed Distinctiveness",
                999,
            ),
            "AREA": self.create_int_field("Area", "Area"),
        }
        return list(create_fields.values())

    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict[str, str]:
        feedback = QgsProcessingMultiStepFeedback(27, feedback)
        results: dict[str, str] = {}
        outputs: dict[str, Any] = {}

        baseline_layer = fix_layer_basic(
            parameters["baseline_layer"],
            parameters["output_crs"],
            context,
            feedback,
        )

        proposed_layer = fix_layer_basic(
            parameters["proposed_layer"],
            parameters["output_crs"],
            context,
            feedback,
        )

        # Fix geometries - redline
        alg_params = {
            "INPUT": parameters["redline_boundary"],
            "METHOD": 0,  # Linework
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
        outputs["FixGeometriesRedline"] = processing.run(
            "native:fixgeometries",
            alg_params,
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FixGeometriesRedline"] is not None

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Union - baseline and proposed
        outputs["UnionBaselineAndProposed"] = processing.run(
            "native:union",
            {
                "GRID_SIZE": None,
                "INPUT": baseline_layer,
                "OVERLAY": proposed_layer,
                "OVERLAY_FIELDS_PREFIX": None,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            # is_child_algorithm=True,
        )

        assert outputs["UnionBaselineAndProposed"] is not None

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        fix_union_layer_main_pipeline_outputs = fix_layer_main_pipeline2(
            outputs["UnionBaselineAndProposed"]["OUTPUT"],
            parameters["minimum_mappable_unit_m2"],
            parameters["snapping_tolerance_m"],
            parameters["set_file_path_for_interim_results"],
            context,
            feedback,
            starting_step=1,
        )

        if fix_union_layer_main_pipeline_outputs is not None:
            outputs.update(fix_union_layer_main_pipeline_outputs)

        # Clip - layer to redline
        outputs["ClipLayer"] = processing.run(
            "native:clip",
            {
                "INPUT": outputs["FixGeometriesSnap"]["OUTPUT"],
                "OVERLAY": outputs["FixGeometriesRedline"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        feedback.setCurrentStep(24)
        if feedback.isCanceled():
            return {}

        assert outputs["ClipLayer"] is not None

        process_gaps_outputs = process_gaps(
            outputs["ClipLayer"]["OUTPUT"],
            outputs["FixGeometriesRedline"]["OUTPUT"],
            context,
            feedback,
            starting_step=25,
        )

        if process_gaps_outputs is not None:
            outputs.update(process_gaps_outputs)

        # Refactor fields - names
        refactor_fields_mapping: list[dict[str, Any]] = self.get_field_mapping()

        outputs["RefactorFieldsNames"] = processing.run(
            "native:refactorfields",
            {
                "FIELDS_MAPPING": refactor_fields_mapping,
                "INPUT": outputs["EliminateSelectedPolygonsGaps"]["OUTPUT"],
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["RefactorFieldsNames"] is not None

        feedback.setCurrentStep(26)
        if feedback.isCanceled():
            return {}

        # Delete holes
        outputs["DeleteHoles"] = processing.run(
            "native:deleteholes",
            {
                "INPUT": outputs["RefactorFieldsNames"]["OUTPUT"],
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
                "OUTPUT": parameters["union_BNG_output"],
            },
            context=context,
            feedback=feedback,
            is_child_algorithm=True,
        )

        assert outputs["FieldCalculatorArea"] is not None

        results["union_BNG_output"] = outputs["FieldCalculatorArea"]["OUTPUT"]
        context.layerToLoadOnCompletionDetails(
            results["union_BNG_output"]
        ).name = "union_BNG_output"
        return results

    def icon(self) -> QIcon:
        return QIcon(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "icons",
                "Union_BNG.png",
            )
        )

    def shortHelpString(self) -> str:
        text = """<b>General:</b><br>\
Combines the Baseline and Proposed Spatialsesh BNG polygon layers into a single layer, preserving and combining their relevant attribute fields, and then cleans and repairs the resulting layer. The cleaning process includes fixing invalid geometries, removing duplicate and small polygons, snapping geometries, and eliminating gaps.<br>\
<br> <b>Parameters:</b><br>\
<ul> <li>Baseline layer</li><li>Proposed layer</li> <li><b>Minimum Mappable Unit (m2)</li> <li><b>Snapping tolerance (m)</li> <li><b>Output CRS</li><li> Set file path for interim results - <b>Advanced parameter with a default value</b></li> </ul><br>\
<b>Output:</b><br>\
Produces a single fixed polygon layer Master BNG layer, which can be exported to the NE metric. Baseline and Proposed features are combined, with their relevant attributes preserved and standardised. Invalid geometries, small polygons and slivers, duplicate geometries, and gaps are addressed during the cleaning process."""

        return text

    def name(self) -> str:
        return "Union_BNG"

    def displayName(self) -> str:
        return "Union BNG"

    def group(self) -> str:
        return ""

    def groupId(self) -> str:
        return ""

    def createInstance(self):
        return self.__class__()
