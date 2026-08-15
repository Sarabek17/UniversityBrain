"""Built-in tools. Importing this package registers all of them.

One file per tool (CLAUDE.md): S11 added `ariza_holati` (`flow_status.py`) the
same way — a file plus a single import line here.
"""

from app.agents.tools import attendance_view  # noqa: F401
from app.agents.tools import document_search  # noqa: F401
from app.agents.tools import document_summary  # noqa: F401
from app.agents.tools import document_translate  # noqa: F401
from app.agents.tools import flow_status  # noqa: F401
from app.agents.tools import payment_status  # noqa: F401
from app.agents.tools import presence_check  # noqa: F401
from app.agents.tools import schedule_view  # noqa: F401
from app.agents.tools import teacher_attendance  # noqa: F401
