import logging

from odoo.exceptions import UserError

from . import models
from . import controllers
from . import wizard

_logger = logging.getLogger(__name__)


def _post_init_hook(env):
    try:
        env["portal.order"]._get_global_purchase_tax()
    except UserError as e:
        # no company country yet: the tax is created on first use instead
        _logger.warning("%s", e)
