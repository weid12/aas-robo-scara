import sqlite3
import json
from pathlib import Path


def main(root: Path) -> None:
    db_path = root / "data/aas_history.sqlite3"
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    before = cur.execute(
        "SELECT COUNT(1) FROM submodel_snapshots WHERE submodel_name='OperationalData' AND idshort LIKE 'OperationalData.JointPosition%'"
    ).fetchone()[0]
    print("Before normalized OperationalData.JointPosition* rows:", before)

    # Remove all JointPosition rows (both enumerated and base), we will rebuild
    cur.execute(
        "DELETE FROM submodel_snapshots WHERE submodel_name='OperationalData' AND idshort LIKE 'OperationalData.JointPosition%'"
    )
    con.commit()

    rows = []
    BATCH = 4000
    inserted = 0
    rows_src = cur.execute(
        "SELECT data, created_at FROM submodel_snapshots_json WHERE submodel_name='OperationalData'"
    ).fetchall()
    for data_json, created_at in rows_src:
        try:
            d = json.loads(data_json)
        except Exception:
            continue
        for name, idx in (
            ("JointPosition1", 0),
            ("JointPosition2", 1),
            ("JointPosition3", 2),
            ("JointPosition4", 3),
        ):
            v = None
            try:
                arr = d.get(name)
                if isinstance(arr, list) and len(arr) > idx:
                    v = float(arr[idx])
            except Exception:
                v = None
            rows.append((
                "OperationalData",
                f"OperationalData.{name}",
                None,
                v,
                None,
                created_at,
            ))
        if len(rows) >= BATCH:
            cur.executemany(
                "INSERT INTO submodel_snapshots(submodel_name,idshort,value_text,value_num,value_bool,created_at) VALUES (?,?,?,?,?,?)",
                rows,
            )
            con.commit()
            inserted += len(rows)
            rows.clear()
    if rows:
        cur.executemany(
            "INSERT INTO submodel_snapshots(submodel_name,idshort,value_text,value_num,value_bool,created_at) VALUES (?,?,?,?,?,?)",
            rows,
        )
        con.commit()
        inserted += len(rows)
        rows.clear()

    after = cur.execute(
        "SELECT COUNT(1) FROM submodel_snapshots WHERE submodel_name='OperationalData' AND idshort LIKE 'OperationalData.JointPosition%'"
    ).fetchone()[0]
    print("Inserted:", inserted, "After rows:", after)
    con.close()


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    main(root)
