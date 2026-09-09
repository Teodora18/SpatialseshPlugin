from collections.abc import Callable
from typing import Any, cast
import uuid
import json
from qgis.core import QgsNetworkAccessManager, QgsSettings
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply

API_SLUG = "spatialseshplugin"
API_KEY = "pk_live_34avXrXppqjRoygHHZUFcRqecaj9c1zew"


def noop(*args, **kwargs):
    pass


def get_fingerprint() -> str:
    return QgsSettings().value("maplango/deviceId", "")


if not get_fingerprint():
    fingerprint = str(uuid.uuid4())
    QgsSettings().setValue("maplango/deviceId", fingerprint)


# parent = QLabel()


class LicenseSeatApi:
    def __init__(self, api_slug: str, api_key: str) -> None:
        self._nam: QgsNetworkAccessManager = cast(
            QgsNetworkAccessManager, QgsNetworkAccessManager.instance()
        )
        self.api_slug = api_slug
        self.api_key = api_key

    def _get_qt_request(
        self, url: str, headers: dict[str | QNetworkRequest.KnownHeaders, str]
    ) -> QNetworkRequest:
        qt_request = QNetworkRequest(QUrl(url))

        for header, value in headers.items():
            if isinstance(header, QNetworkRequest.KnownHeaders):
                qt_request.setHeader(header, value)
            elif isinstance(header, str):
                qt_request.setRawHeader(header.encode("utf8"), value.encode("utf8"))
            else:
                raise NotImplementedError(
                    f"Unexpected header type={type(header)} for {header}={value}"
                )

        return qt_request

    def get_url(self, uri: str) -> str:
        return f"https://licenseseat.com/api/v1/products/{self.api_slug}/{uri}"

    def post(
        self,
        uri: str,
        payload: dict[str, Any],
        on_finished: Callable[[QNetworkReply], None] | None = None,
        on_error_occured: Callable[[QNetworkReply], None] | None = None,
    ) -> QNetworkReply:
        request = self._get_qt_request(
            self.get_url(uri),
            {
                QNetworkRequest.KnownHeaders.ContentTypeHeader: "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        payload_bytes = json.dumps(payload).encode("utf-8")
        reply = self._nam.post(request, payload_bytes)

        assert reply is not None

        if on_finished:
            reply.finished.connect(lambda: on_finished(reply))

        if on_error_occured:
            reply.errorOccurred.connect(lambda: on_error_occured(reply))

        return reply

    def activate_licence(
        self,
        license_key: str,
        on_success: Callable[[dict[str, Any]], None] = noop,
        on_error: Callable[[str], None] = noop,
    ) -> QNetworkReply:
        def _on_reply_finished(reply: QNetworkReply) -> None:
            # `replyAll()` returns `ByteArray`, which is not automatically converted to `bytes`, so we do the conversion manually
            raw_content = bytes(reply.readAll())

            try:
                json_content = json.loads(raw_content)
            except Exception as err:
                if reply.error() in (
                    QNetworkReply.NetworkError.HostNotFoundError,
                    QNetworkReply.NetworkError.NetworkSessionFailedError,
                    QNetworkReply.NetworkError.TimeoutError,
                ):
                    on_error(
                        "Could not connect to the license validation platform. "
                        "Please check your internet connection and try again."
                    )
                elif reply.error() != QNetworkReply.NetworkError.NoError:
                    on_error(
                        f"Failed to connect to license validation platform, reason: {reply.errorString()}"
                    )
                else:
                    on_error(
                        f"Failed to parse license validation platform response with `{err}` for supposed-to-be-JSON: {raw_content}"
                    )
                return

            if (
                reply.error() != QNetworkReply.NetworkError.NoError
                or "error" in json_content
            ):
                error_code = json_content.get("error", {}).get("code")
                print(json_content)
            else:
                on_success(json_content)
                return

            if error_code is None:
                on_error("Unknown error from the licence validation platform!")

            elif error_code == "license_not_found":
                on_error("Invalid license. Please check for typos!")

            elif error_code == "expired":
                on_error("This license has expired. Please renew your license!")
            elif error_code == "revoked":
                on_error(
                    "This license has been revoked. Please contact support at matt@maplango.com!"
                )
            elif error_code == "seat_limit_exceeded":
                on_error(
                    "This license has reached its maximum number of activated devices!"
                )
            else:
                error_message = json_content.get("error", {}).get("message")

                on_error(
                    f"Unknown license error from the licence validation platform: `{error_code}`"
                    + (f" with error message: {error_message}" if error_message else "")
                )

            return

        reply = self.post(
            "licenses/activate",
            {
                "license_key": license_key,
                "fingerprint": get_fingerprint(),
            },
            on_finished=_on_reply_finished,
        )

        return reply


# reply.finished.connect(_on_reply_finished)


# licenseseat_api = LicenseSeatApi(API_SLUG, API_KEY)

# def on_success(payload: dict[str, Any]) -> None:
#     # QSettings.setValue("maplango/licenseLastCheckedAt", now())
#     print(f"Success!")
#     # QLabel(f"Success with: {payload}", parent).show()


# def on_error(error: str) -> None:
#     print(f"Error! {error}")
#     # QLabel("Opa, ne stana!", parent).show()


# # на LoadPlugin и в properties на QGIS
# licenseseat_api.activate_licence(license_key, on_success, on_error)
