# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'


    historic_id = fields.Integer(
        string="id from OldTable",
        help="preserving ID from old database for migration and validation purposes",
    )

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    historic_id = fields.Integer(
        string="id from OldTable",
        help="preserving ID from old database for migration and validation purposes",
    )
    

class AccountJournal(models.Model):
    _inherit = 'account.journal'


    historic_id = fields.Integer(
        string="id from OldTable",
        help="preserving ID from old database for migration and validation purposes",
    )