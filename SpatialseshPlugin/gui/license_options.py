import os

from qgis.gui import QgsOptionsPageWidget
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.uic import loadUiType

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

        self.settings = QSettings()

        self.load_settings()

        self.validateButton.clicked.connect(self.validate_license)

    def load_settings(self):
        self.licenseKeyEdit.setText(
            self.settings.value(
                "maplango/license_key",
                "",
                type=str,
            )
        )

    def apply(self):
        license_key = self.licenseKeyEdit.text().strip()

        self.settings.setValue(
            "maplango/license_key",
            license_key,
        )

    def validate_license(self):
        license_key = self.licenseKeyEdit.text().strip()

        if not license_key:
            self.statusValueLabel.setText("Please enter a license key.")
            return

        # Call your LicenseSeat API here
        #
        # result = ...
        #
        # if successful:
        #     self.statusLabel.setText("License activated.")
        # else:
        #     self.statusLabel.setText("Invalid license.")

        self.statusValueLabel.setText("Validating...")
