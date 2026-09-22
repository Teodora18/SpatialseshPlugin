from typing import Any


def create_text_field(expression, name, length=0) -> dict[str, Any]:
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


def create_int_field(expression, name, length=0) -> dict[str, Any]:
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


def create_date_field(expression, name, length=0) -> dict[str, Any]:
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


def get_fields(
    field_names: list[str],
) -> list[dict[str, Any]]:
    create_fields = {
        "PARCEL_REF": lambda: create_text_field("Parcel_Ref", "Parcel Ref", 99),
        "BASELINE_BROAD_HABITAT_TYPE": lambda: create_text_field(
            "Baseline_Broad_Habitat_Type", "Baseline Broad Habitat Type", 99
        ),
        "BASELINE_HABITAT_TYPE": lambda: create_text_field(
            "Baseline_Habitat_Type",
            "Baseline Habitat Type",
            99,
        ),
        "AREA": lambda: create_int_field("Area", "Area"),
        "BASELINE_CONDITION": lambda: create_text_field(
            "Baseline_Condition",
            "Baseline Condition",
            99,
        ),
        "BASELINE_STRATEGIC_SIGNIFICANCE": lambda: create_text_field(
            "Baseline_Strategic_Significance",
            "Baseline Strategic Significance",
            99,
        ),
        "RETENTION_CATEGORY": lambda: create_text_field(
            "Retention_Category",
            "Retention Category",
            99,
        ),
        "LOCATION": lambda: create_text_field("Location", "Location", 99),
        "PROPOSED_BROAD_HABITAT_TYPE": lambda: create_text_field(
            "Proposed_Broad_Habitat_Type",
            "Proposed Broad Habitat Type",
            99,
        ),
        "PROPOSED_HABITAT_TYPE": lambda: create_text_field(
            "Proposed_Habitat_Type",
            "Proposed Habitat Type",
            99,
        ),
        "PROPOSED_CONDITION": lambda: create_text_field(
            "Proposed_Condition",
            "Proposed Condition",
            99,
        ),
        "PROPOSED_STRATEGIC_SIGNIFICANCE": lambda: create_text_field(
            "Proposed_Strategic_Significance",
            "Proposed Strategic Significance",
            99,
        ),
        "HABITAT_CREATED_IN_ADVANCE_YEARS": lambda: create_text_field(
            "Habitat_created_in_advance_years",
            "Habitat created in advance/years",
            99,
        ),
        "DELAY_IN_STARTING_HABITAT_CREATION_YEARS": lambda: create_text_field(
            "Delay_in_starting_habitat_creation_years",
            "Delay in starting habitat creation/years",
            99,
        ),
        "SPATIAL_RISK_CATEGORY": lambda: create_text_field(
            "Spatial_risk_category",
            "Spatial risk category",
            99,
        ),
        "SITE_NAME": lambda: create_text_field("Site_Name", "Site Name"),
        "SURVEY_DATE": lambda: create_date_field("Survey_Date", "Survey Date"),
        "SURVEY_DETAILS": lambda: create_text_field("Survey_Details", "Survey Details"),
        "COMMENT": lambda: create_text_field("Comment", "Comment"),
        "MAPPED_BY": lambda: create_text_field("Mapped_by", "Mapped by"),
        "COMPANY": lambda: create_text_field("Company", "Company"),
        "BASE_MAP": lambda: create_text_field("Base_Map", "Base Map"),
        "BASELINE_DISTINCTIVENESS": lambda: create_text_field(
            "Baseline_Distinctiveness",
            "Baseline Distinctiveness",
            999,
        ),
        "PROPOSED_DISTINCTIVENESS": lambda: create_text_field(
            "Proposed_Distinctiveness",
            "Proposed Distinctiveness",
            999,
        ),
        "PHOTO": lambda: create_text_field("Photo", "Photo"),
        "UKHAB_LV1_CODE": lambda: create_text_field("UKhabLv1_Code", "UKhabLv1_Code"),
        "UKHAB_LV2_CODE": lambda: create_text_field("UKhabLv2_Code", "UKhabLv2_Code"),
        "UKHAB_LV3_CODE": lambda: create_text_field("UKhabLv3_Code", "UKhabLv3_Code"),
        "UKHAB_LV4_CODE": lambda: create_text_field("UKhabLv4_Code", "UKhabLv4_Code"),
        "UKHAB_LV5_CODE": lambda: create_text_field("UKhabLv5_Code", "UKhabLv5_Code"),
        "ESSENTIAL_SECONDARY_CODE": lambda: create_text_field(
            "EssentialSecondaryCode",
            "EssentialSecondaryCode",
        ),
        "ADDITIONAL_SECONDARY_CODE": lambda: create_text_field(
            "AdditionalSecondaryCode",
            "AdditionalSecondaryCode",
        ),
        "UKHABITAT": lambda: create_text_field("UKhabitat", "UKhabitat"),
        "UKHAB_CODE": lambda: create_text_field("UKhabCode", "UKhabCode"),
        "PREVIOUS_SURVEY": lambda: create_text_field(
            "PreviousSurvey",
            "PreviousSurvey",
        ),
        "PREVIOUS_COMMENT": lambda: create_text_field(
            "PreviousComment",
            "PreviousComment",
        ),
        "HABITAT_MANAGEMENT": lambda: create_text_field(
            "HabitatManagement",
            "HabitatManagement",
        ),
        "GUIDANCE": lambda: create_text_field(
            "Guidance",
            "Guidance",
        ),
        "GUIDANCE_Q": lambda: create_text_field(
            "Guidance_Q",
            "Guidance_Q",
        ),
    }
    return [create_fields[field_name]() for field_name in field_names]
