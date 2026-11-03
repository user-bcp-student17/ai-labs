import sqlite3

from app.schemas import TaskCreate, TaskResponse

TASK_COLUMNS = "id,title,description,status,owner,priority,created_at"
CREATE_TASKS_TABLE = (
    "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, "
    "description TEXT NOT NULL, status TEXT NOT NULL, owner TEXT NOT NULL, priority TEXT NOT NULL, created_at TEXT NOT NULL)"
)
SELECT_BY_OWNER = "SELECT " + TASK_COLUMNS + " FROM tasks WHERE owner = ? ORDER BY id"
SELECT_BY_ID = "SELECT " + TASK_COLUMNS + " FROM tasks WHERE id = ?"
SELECT_STATUS_PRIORITY_BY_OWNER = "SELECT status,priority FROM tasks WHERE owner = ?"
INSERT_TASK = "INSERT INTO tasks(title,description,status,owner,priority,created_at) VALUES (?,?,?,?,?,datetime('now'))"
SEED_TASKS = (
    ("Refactor login", "Separar responsabilidades en frontend", "TODO", "student", "HIGH"),
    ("Review API", "Revisar seguridad de endpoints", "IN_PROGRESS", "student", "MEDIUM"),
    ("Trainer notes", "Preparar retrospectiva", "TODO", "trainer", "LOW"),
)


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @classmethod
    def open(cls, db_path: str) -> "TaskRepository":
        connection = sqlite3.connect(db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return cls(connection)

    def close(self) -> None:
        self._connection.close()

    def initialize(self) -> None:
        self._connection.execute(CREATE_TASKS_TABLE)
        total = self._connection.execute("SELECT COUNT(*) AS total FROM tasks").fetchone()["total"]
        if total == 0:
            self._seed()
        self._connection.commit()

    def _seed(self) -> None:
        for title, description, status, owner, priority in SEED_TASKS:
            self._insert(title, description, status, owner, priority)

    def list_by_owner(self, owner: str) -> list[TaskResponse]:
        rows = self._connection.execute(SELECT_BY_OWNER, (owner,)).fetchall()
        return [_to_task(row) for row in rows]

    def add(self, owner: str, payload: TaskCreate) -> TaskResponse:
        task_id = self._insert(payload.title, payload.description, payload.status, owner, payload.priority)
        self._connection.commit()
        row = self._connection.execute(SELECT_BY_ID, (task_id,)).fetchone()
        return _to_task(row)

    def status_and_priority_by_owner(self, owner: str) -> list[tuple[str, str]]:
        rows = self._connection.execute(SELECT_STATUS_PRIORITY_BY_OWNER, (owner,)).fetchall()
        return [(row["status"], row["priority"]) for row in rows]

    def _insert(self, title: str, description: str, status: str, owner: str, priority: str) -> int:
        return self._connection.execute(INSERT_TASK, (title, description, status, owner, priority)).lastrowid


def _to_task(row: sqlite3.Row) -> TaskResponse:
    return TaskResponse(**{key: row[key] for key in row.keys()})
