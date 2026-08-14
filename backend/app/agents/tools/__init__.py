"""Built-in tools. Importing this package registers all of them.

One file per tool (CLAUDE.md): later sessions add `tolov_holati` (S8),
`mavjudlik_tekshir` / `davomat_kor` (S9), `oqituvchi_davomat` (S10),
`ariza_holati` (S11), `tarjima_qil` (S7) the same way.
"""

from app.agents.tools import document_search  # noqa: F401
from app.agents.tools import document_summary  # noqa: F401
from app.agents.tools import schedule_view  # noqa: F401
