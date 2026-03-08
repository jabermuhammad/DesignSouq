from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine


def ensure_admin_tables() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS admin_designer_bans (
                    designer_id INTEGER PRIMARY KEY,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    reason TEXT NOT NULL DEFAULT '',
                    banned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS admin_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_type TEXT NOT NULL,
                    target_id INTEGER NOT NULL,
                    reporter_name TEXT NOT NULL DEFAULT '',
                    reporter_email TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    action_note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS admin_featured_projects (
                    project_id INTEGER PRIMARY KEY,
                    featured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )


def get_ban_map(db: Session) -> dict[int, dict]:
    rows = db.execute(
        text(
            """
            SELECT designer_id, is_active, reason, banned_at, updated_at
            FROM admin_designer_bans
            """
        )
    ).mappings()
    return {int(row["designer_id"]): dict(row) for row in rows}


def set_designer_ban(db: Session, designer_id: int, reason: str, active: bool) -> None:
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    existing = db.execute(
        text("SELECT designer_id FROM admin_designer_bans WHERE designer_id = :designer_id"),
        {"designer_id": designer_id},
    ).first()
    if existing:
        db.execute(
            text(
                """
                UPDATE admin_designer_bans
                SET is_active = :is_active, reason = :reason, updated_at = :updated_at
                WHERE designer_id = :designer_id
                """
            ),
            {
                "designer_id": designer_id,
                "is_active": 1 if active else 0,
                "reason": reason.strip(),
                "updated_at": now,
            },
        )
    else:
        db.execute(
            text(
                """
                INSERT INTO admin_designer_bans (designer_id, is_active, reason, banned_at, updated_at)
                VALUES (:designer_id, :is_active, :reason, :banned_at, :updated_at)
                """
            ),
            {
                "designer_id": designer_id,
                "is_active": 1 if active else 0,
                "reason": reason.strip(),
                "banned_at": now,
                "updated_at": now,
            },
        )
    db.commit()


def list_reports(
    db: Session,
    status: str = "",
    target_type: str = "",
) -> list[dict]:
    sql = """
        SELECT id, target_type, target_id, reporter_name, reporter_email, reason, status, action_note, created_at, reviewed_at
        FROM admin_reports
        WHERE 1=1
    """
    params: dict[str, str] = {}
    if status:
        sql += " AND status = :status"
        params["status"] = status
    if target_type:
        sql += " AND target_type = :target_type"
        params["target_type"] = target_type
    sql += " ORDER BY created_at DESC, id DESC"
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]


def create_report(
    db: Session,
    target_type: str,
    target_id: int,
    reason: str,
    reporter_name: str = "",
    reporter_email: str = "",
) -> None:
    db.execute(
        text(
            """
            INSERT INTO admin_reports (target_type, target_id, reporter_name, reporter_email, reason, status)
            VALUES (:target_type, :target_id, :reporter_name, :reporter_email, :reason, 'open')
            """
        ),
        {
            "target_type": target_type,
            "target_id": target_id,
            "reporter_name": reporter_name.strip(),
            "reporter_email": reporter_email.strip(),
            "reason": reason.strip(),
        },
    )
    db.commit()


def update_report_status(db: Session, report_id: int, status: str, action_note: str = "") -> None:
    now = datetime.utcnow().isoformat(sep=" ", timespec="seconds")
    db.execute(
        text(
            """
            UPDATE admin_reports
            SET status = :status, action_note = :action_note, reviewed_at = :reviewed_at
            WHERE id = :report_id
            """
        ),
        {
            "status": status,
            "action_note": action_note.strip(),
            "reviewed_at": now,
            "report_id": report_id,
        },
    )
    db.commit()


def get_report(db: Session, report_id: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT id, target_type, target_id, reporter_name, reporter_email, reason, status, action_note, created_at, reviewed_at
            FROM admin_reports
            WHERE id = :report_id
            """
        ),
        {"report_id": report_id},
    ).mappings().first()
    return dict(row) if row else None


def get_featured_project_ids(db: Session) -> set[int]:
    rows = db.execute(text("SELECT project_id FROM admin_featured_projects")).all()
    return {int(row[0]) for row in rows}


def set_project_featured(db: Session, project_id: int, featured: bool) -> None:
    if featured:
        db.execute(
            text(
                """
                INSERT OR REPLACE INTO admin_featured_projects (project_id, featured_at)
                VALUES (:project_id, :featured_at)
                """
            ),
            {
                "project_id": project_id,
                "featured_at": datetime.utcnow().isoformat(sep=" ", timespec="seconds"),
            },
        )
    else:
        db.execute(
            text("DELETE FROM admin_featured_projects WHERE project_id = :project_id"),
            {"project_id": project_id},
        )
    db.commit()


def build_daily_series(db: Session, days: int = 14) -> dict[str, list[int] | list[str]]:
    start = datetime.utcnow().date() - timedelta(days=days - 1)
    labels = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    index = {label: idx for idx, label in enumerate(labels)}

    new_designers = [0] * days
    new_viewers = [0] * days
    new_projects = [0] * days
    reports = [0] * days
    visitors = [0] * days

    designer_rows = db.execute(
        text(
            """
            SELECT date(created_at) AS d, COUNT(*) AS c
            FROM designers
            WHERE date(created_at) >= :start_date
            GROUP BY date(created_at)
            """
        ),
        {"start_date": start.isoformat()},
    ).all()
    for d, c in designer_rows:
        if d in index:
            new_designers[index[d]] = int(c)

    viewer_rows = db.execute(
        text(
            """
            SELECT date(created_at) AS d, COUNT(*) AS c
            FROM viewers
            WHERE date(created_at) >= :start_date
            GROUP BY date(created_at)
            """
        ),
        {"start_date": start.isoformat()},
    ).all()
    for d, c in viewer_rows:
        if d in index:
            new_viewers[index[d]] = int(c)

    project_rows = db.execute(
        text(
            """
            SELECT date(created_at) AS d, COUNT(*) AS c
            FROM projects
            WHERE date(created_at) >= :start_date
            GROUP BY date(created_at)
            """
        ),
        {"start_date": start.isoformat()},
    ).all()
    for d, c in project_rows:
        if d in index:
            new_projects[index[d]] = int(c)

    report_rows = db.execute(
        text(
            """
            SELECT date(created_at) AS d, COUNT(*) AS c
            FROM admin_reports
            WHERE date(created_at) >= :start_date
            GROUP BY date(created_at)
            """
        ),
        {"start_date": start.isoformat()},
    ).all()
    for d, c in report_rows:
        if d in index:
            reports[index[d]] = int(c)

    for i in range(days):
        users_growth = new_designers[i] + new_viewers[i]
        visitors[i] = max(5, users_growth * 4 + new_projects[i] * 3 + reports[i] * 2)

    return {
        "labels": labels,
        "visitors": visitors,
        "new_users": [new_designers[i] + new_viewers[i] for i in range(days)],
        "new_projects": new_projects,
        "reports": reports,
    }
