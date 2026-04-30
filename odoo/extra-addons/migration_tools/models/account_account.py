# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)

class AccountAccount(models.Model):
    _inherit = 'account.account'


    historic_id = fields.Integer(
        string="id from OldTable",
        help="preserving ID from old database for migration and validation purposes",
    )
