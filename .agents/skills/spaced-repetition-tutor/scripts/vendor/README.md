# Vendored code

`fsrs/` is the scheduler of [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) 6.3.2,
MIT licensed (see `fsrs/LICENSE`). It holds the package's modules except `optimizer.py`, which
needs torch.

One change from upstream: in `card.py`, `review_log.py` and `scheduler.py` the import of `Self`
from `typing_extensions` moved under `if TYPE_CHECKING:`, so the package runs with the standard
library only. The modules use `from __future__ import annotations`, so `Self` is needed for type
checking only.
