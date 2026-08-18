from pathlib import Path

import pandas as pd

from queo_data_platform.contracts.tracker import (
    RAW_TRACKER_REQUIRED_COLUMNS,
)


def build_tracker_row(
    *,
    event_date: str,
    event_time: str,
    message_type: str,
    serial_count: int,
) -> dict[str, object]:
    row: dict[str, object] = {
        column: "value"
        for column in RAW_TRACKER_REQUIRED_COLUMNS
    }

    row.update(
        {
            "DATA_SERVIDOR": f"{event_date} {event_time}",
            "TM_STAMP": f"{event_date} {event_time}",
            "TIPO_LOG": "tracker",
            "MESS_TYPE": message_type,
            "REPT_TYPE": "1",
            "PRT_VER": "1",
            "S/N ou IMEI": "M123456789",
            "TERM_STATUS": "OK",
            "BAT_VOLT": "12.5",
            "LOC_STATUS": "A",
            "LAT": "-3.7319",
            "LONT": "-38.5267",
            "SPEED": "45.5",
            "DIR": "180",
            "INT_BATT": "4.1",
            "ODO_TRIP": "100",
            "ODO_TOTAL": "20000",
            "HORIMETER": "1500",
            "HDOP": "1.2",
            "MCC": "724",
            "MNC": "05",
            "LAC": "100",
            "CELL_ID": "200",
            "RX_LEVEL": "-70",
            "SER_COUNT": str(serial_count),
            "TX_TECH": "GPRS",
            "GRP_MSG": "G1",
            "IO_STATUS": "0",
            "DRIVER_ID": "",
            "PASS_ID": "",
            "RPM": "2500",
            "TACHO_SPD": "45",
            "TACHO_ODO": "20000",
            "TEMP_1": "25",
            "TEMP_2": "26",
            "TEMP_3": "27",
            "TEMP_4": "28",
        }
    )

    return row


def build_identity_row(
    *,
    event_date: str,
    serial_count: int,
) -> dict[str, object]:
    row = build_tracker_row(
        event_date=event_date,
        event_time="09:00:00",
        message_type="T1",
        serial_count=serial_count,
    )

    row["BAT_VOLT"] = "8955000000000000001"
    row["LOC_STATUS"] = "aux"
    row["LAT"] = "724000000000001"
    row["LONT"] = "359000000000001"

    return row


def main() -> None:
    inbox = Path("data/raw/inbox")

    inbox.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = pd.DataFrame(
        [
            build_tracker_row(
                event_date="2026-08-18",
                event_time="10:00:00",
                message_type="T2",
                serial_count=1,
            ),
            build_identity_row(
                event_date="2026-08-18",
                serial_count=2,
            ),
            build_tracker_row(
                event_date="2026-08-18",
                event_time="11:00:00",
                message_type="INVALID",
                serial_count=3,
            ),
        ]
    )

    output = inbox / "tracker-validation-2026-08-18.csv"

    dataframe.to_csv(
        output,
        index=False,
    )

    print(f"Created: {output}")


if __name__ == "__main__":
    main()
