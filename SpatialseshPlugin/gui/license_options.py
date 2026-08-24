import os
from typing import Any

from datetime import datetime, timedelta, timezone
from qgis.gui import QgsOptionsPageWidget
from qgis.PyQt.uic import loadUiType
from qgis.core import QgsSettings

from ..licenseseat_api import API_KEY, API_SLUG, LicenseSeatApi

WidgetUi, _ = loadUiType(
    os.path.join(
        os.path.dirname(__file__),
        "../ui/dialog.ui",
    )
)


class LicenseOptionsWidget(WidgetUi, QgsOptionsPageWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)

        self.settings = QgsSettings()

        self.license_api = LicenseSeatApi(
            API_SLUG,
            API_KEY,
        )

        self.load_settings()

        self.validateButton.clicked.connect(self.validate_license)
        self.statusIconLabel.setVisible(False)
        self.validUntilValueLabel.setVisible(False)

    def load_settings(self):
        self.licenseKeyEdit.setText(
            self.settings.value(
                "maplango/license_key",
                "",
                type=str,
            )
        )

    def apply(self):
        if self.settings.value("maplango/license_valid") is True:
            self.settings.setValue(
                "maplango/license_key",
                self.licenseKeyEdit.text().strip(),
            )

    def validate_license(self):
        license_key = self.licenseKeyEdit.text().strip()

        if not license_key:
            self.statusValueLabel.setText("Please enter a license key.")
            return

        self.statusValueLabel.setText("Validating...")

        self.validateButton.setEnabled(False)

        self.license_api.activate_licence(
            license_key,
            self.on_license_success,
            self.on_license_error,
        )

    def on_license_success(self, payload: dict[str, Any]) -> None:
        self.validateButton.setEnabled(True)
        self.statusIconLabel.setVisible(True)

        self.statusValueLabel.setText("License key validated.")

        self.settings.setValue(
            "maplango/license_valid",
            True,
        )
        checked_at = datetime.now(timezone.utc)
        valid_until = checked_at + timedelta(days=7)

        self.settings.setValue(
            "maplango/licenseLastCheckedAt",
            checked_at.isoformat(),
        )

        self.statusIconLabel.setVisible(True)

        self.statusValueLabel.setText("License key validated.")

        self.validUntilValueLabel.setText(
            f"Valid until: {valid_until.strftime('%d %B %Y')}"
        )

        self.validUntilValueLabel.setVisible(True)

    def on_license_error(self, error: str) -> None:
        self.validateButton.setEnabled(True)
        self.statusIconLabel.setVisible(False)
        self.validUntilValueLabel.setVisible(False)

        self.statusValueLabel.setText(error)

        self.settings.setValue(
            "maplango/license_key",
            "",
        )

        self.settings.setValue(
            "maplango/licenseLastCheckedAt",
            "",
        )

        self.settings.setValue(
            "maplango/license_valid",
            False,
        )

        print(f"Error! {error}")
