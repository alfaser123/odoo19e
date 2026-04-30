# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class NiifAccountConsolidate(models.Model):
    _inherit = 'account.account'

    @api.one
    @api.depends('code','parent_id')
    def _get_puc(self):
        if self.code:
            if self.parent_id or len(self.code)>1:
                if self.code:
                    chart_account = self.env['account.account'].search([['code', '=', self.code[:1]]])
                    if chart_account:
                        self.chart_account = chart_account.id
                    elif not chart_account:
                        self.chart_account = self.env['account.account'].search([['code', '=', '0']])
                    elif not self.chart_account:
                        chart_account = self.env['account.account'].search([['code', '=', '0']])
                        raise UserError(_("You must define a Chart of Accounts"))

    child_consol_ids = fields.Many2many('account.account', 'account_account_consol_rel', 'child_id', 'parent_id', 'Consolidated Children',invisible=True)
    chart_account = fields.Many2one('account.account',string='Chart of Accounts', compute='_get_puc', store=True)
    #chart_account = fields.Many2one('account.account',string='Chart of Accounts', compute='_get_puc', store=True)
    parent_id = fields.Many2one('account.account',string='Parent',domain='[("user_type_id","=",18)]')

class AccountAccountTypeExtended(models.Model):
    _inherit = "account.account.type"

    type = fields.Selection([
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity', 'Liquidity'),
        ('view', _('View')),
        ('consolidation', _('Consolidation'))
    ], required=True, default='other',
        help="The 'Internal Type' is used for features available on "\
        "different types of accounts: liquidity type is for cash or bank accounts"\
        ", payable/receivable is for vendor/customer accounts.",oldname="type")
        

        
        
    # @api.onchange('internal_type')
    # def onchange_internal_type(self):
        # print('entraaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        # if self.internal_type in ('receivable', 'payable'):
            # self.reconcile = True

        
        # if self.internal_type == 'view':
            # account_moves = '''SELECT distinct %s as account_id
                                    # FROM account_move_line aml
                                # where company_id = %s  ''' % (self.account_id, self.env.user.company_id.id)
	    # _logger.info(account_moves)
        
        # ids = self.env.cr.execute(account_moves)
        # if ids :
                 # raise UserError(_('You cannot do that on an account that contains journal items.'))


class AccountAccount_ctrlview(models.Model):
    _inherit = "account.account"

    @api.multi
    def write(self, vals):
        # Dont allow changing the company_id when account_move_line already exist
        if vals.get('company_id', False):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            for account in self:
                if (account.company_id.id <> vals['company_id']) and move_lines:
                    raise UserError(_('You cannot change the owner company of an account that already contains journal items.'))
        # If user change the reconcile flag, all aml should be recomputed for that account and this is very costly.
        # So to prevent some bugs we add a constraint saying that you cannot change the reconcile field if there is any aml existing
        # for that account.
        if vals.get('reconcile'):
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            if len(move_lines):
                raise UserError(_('You cannot change the value of the reconciliation on this account as it already has some moves'))
                
        if vals.get('internal_type')=='view':
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            if len(move_lines):
                raise UserError(_('No puede cambiar a tipo "Vista" debido a que ya tiene movimientos contables, You cannot change the value of  "view" this account as it already has some moves '))
                
        if vals.get('user_type_id')=='view':
            move_lines = self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1)
            if len(move_lines):
                raise UserError(_(', No puede cambiar a tipo "Vista" debido a que ya tiene movimientos contables, You cannot change the value of  "view" this account as it already has some moves '))
                 
                 
        return super(AccountAccount_ctrlview, self).write(vals)                 


        
        
        
        
        
        
        