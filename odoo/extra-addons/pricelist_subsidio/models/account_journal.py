from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    account_db_subs = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta DB Subsidio",
        check_company=True,
        domain="[('company_ids', 'in', company_id)]",
    )
    account_cr_subs = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta CR subsidio",
        check_company=True,
        domain="[('company_ids', 'in', company_id)]",
    )
