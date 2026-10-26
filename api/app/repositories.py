import sqlite3


TASK_COLUMNS = "id,title,description,status,owner,priority,created_at"


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_by_owner(self, owner: str) -> list[sqlite3.Row]:
        rows = self.connection.execute(
            f"SELECT {TASK_COLUMNS} FROM tasks WHERE owner=? ORDER BY id",
            (owner,),
        )
        return rows.fetchall()

    def create(
        self,
        title: str,
        description: str,
        status: str,
        owner: str,
        priority: str,
    ) -> sqlite3.Row:
        cursor = self.connection.execute(
            "INSERT INTO tasks(title,description,status,owner,priority,created_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (title, description, status, owner, priority),
        )
        self.connection.commit()
        row = self.connection.execute(
            f"SELECT {TASK_COLUMNS} FROM tasks WHERE id=?",
            (cursor.lastrowid,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Created task could not be loaded")
        return row

    def summary_by_owner(self, owner: str) -> list[sqlite3.Row]:
        rows = self.connection.execute(
            "SELECT status,priority FROM tasks WHERE owner=?",
            (owner,),
        )
        return rows.fetchall()