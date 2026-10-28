"""SAP access over RFC for releases without ADT (NetWeaver 7.31 and older, R/3).

Needs the SAP NW RFC SDK and the `pyrfc` package. Without them every call explains what is missing.
"""

from .. import vault


class RfcUnavailable(Exception):
    pass


class RfcConnector:
    def __init__(self, base_url: str, auth: str, username: str, secret_ref: str, options: dict):
        try:
            from pyrfc import Connection  # type: ignore
        except ImportError as exc:
            raise RfcUnavailable("RFC needs the SAP NW RFC SDK and the pyrfc package on the server") from exc
        self._conn = Connection(
            ashost=options.get("ashost") or base_url,
            sysnr=options.get("sysnr", "00"),
            client=options.get("client", "100"),
            user=username,
            passwd=vault.resolve(secret_ref),
        )

    def system_info(self) -> dict:
        info = self._conn.call("RFC_SYSTEM_INFO")["RFCSI_EXPORT"]
        release = info.get("RFCSAPRL", "").strip()
        return {"basis_release": int(release) if release.isdigit() else None, "cloud": False,
                "components": {"SAP_BASIS": release}}

    def read_source(self, name: str) -> str | None:
        try:
            result = self._conn.call("RPY_PROGRAM_READ", PROGRAM_NAME=name.upper(), WITH_LOWERCASE="X")
        except Exception:
            return None
        lines = result.get("SOURCE_EXTENDED") or result.get("SOURCE") or []
        return "\n".join(line.get("LINE", "") for line in lines) or None

    def where_used(self, name: str) -> list[dict]:
        return []  # Phase 2: cross-reference tables (WBCROSSGT, CROSS)

    def open_transports(self, name: str) -> list[dict]:
        return []  # Phase 2: E070 / E071

    def unit_tests(self, name: str) -> list[str]:
        return []

    def test(self) -> str:
        info = self.system_info()
        return f"Connected over RFC, SAP_BASIS {info['basis_release'] or 'unknown'}"
