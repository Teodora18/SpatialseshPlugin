import datetime
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsSettings


def is_maplango_license_active():
    checked_at = QgsSettings().value("maplango/licenseLastCheckedAt", None)

    try:
        checked_at = datetime.datetime.fromisoformat(checked_at)
    except (ValueError, TypeError):
        checked_at = None

    if (
        checked_at is None
        or (datetime.datetime.now(datetime.timezone.utc) - checked_at).days > 7
    ):
        return False
    else:
        return True


class MaplangoLicensedAlgorithm(QgsProcessingAlgorithm):
    def prepareAlgorithm(self, parameters, context, feedback):
        if not is_maplango_license_active():
            feedback.reportError(
                "Maplango license is not active. Please activate your license to use this algorithm."
            )

            return False

        return super().prepareAlgorithm(parameters, context, feedback)
