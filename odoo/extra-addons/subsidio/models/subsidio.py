
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#     Copyright (C) 2012 Cubic ERP - Teradata SAC (<http://cubicerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api,_
from odoo.exceptions import ValidationError,Warning,UserError
from datetime import datetime
from odoo.tools import float_compare
import logging

_logger = logging.getLogger('SUBSIDIO 2')



class res_partner_category_subsidio(models.Model):
    _inherit = 'res.partner'

    historico_ids = fields.One2many('subsidio.categorias.historico', 'partner_id', string='Referencias', readonly=True)
    categorias_id = fields.Many2one('subsidio.categorias', string='Categoria Subs')

    @api.model
    def create(self, vals):
        print('/opt/extra-addons/subsidio/models/    subsidio.py    create')
        return super(res_partner_category_subsidio, self).create(vals)

    @api.multi
    def write(self, vals):
        print('subsidio write')
        if vals.get('categorias_id',False):
            vals['historico_ids'] = [(0,0,{'fecha':fields.Datetime.now(),
                'user_id':self.env.user.id,'partner_id':self.id,
                'categorias_id':vals.get('categorias_id',False)})]
        return super(res_partner_category_subsidio, self).write(vals);

class res_partner_categorias_subsidio(models.Model):
    _name = 'subsidio.categorias.historico'

    partner_id = fields.Many2one('res.partner', string='Afiliados', help="Afiliados",readonly=True)
    fecha = fields.Datetime('Fecha',readonly=True)
    user_id = fields.Many2one('res.users',string='Responsable',readonly=True)
    categorias_id = fields.Many2one('subsidio.categorias', string='Categoria', required=True)

class res_partner_categorias_subsidio(models.Model):
    _name = 'subsidio.categorias'

    name = fields.Char(string='Nombre de la categoria', help="Nombre de la Categoria")

# class product_pricelist_version_extended(models.Model):
    # _inherit = 'product.pricelist.item'

    # categorias_id = fields.Many2one('subsidio.categorias', string='Categoria', required=True)




# # class account_invoice_extended(models.Model):
# # class account_invoice(models.Model):
# class AccountInvoice(models.Model):
    # _inherit = 'account.invoice'

    # categoria_id = fields.Many2one('subsidio.categorias', string='Categoria Manual',)


    # @api.multi
    # def action_move_create(self):
        # print('action_move_create - subsidio')
        # # res = super(account_invoice_extended, self).action_move_create()
        # res = super(AccountInvoice, self).action_move_create()
        # # print('account_id_subsidio', self.account_id.code)
        # # raise UserError('--------------------------entra4'+str(self.type ))
        # if self.type in ('out_invoice', 'out_refund'):
            # date_maturity = datetime.now()
            # for line in self.move_id.line_ids:
                # if line.date_maturity:
                    # date_maturity = line.date_maturity
                    # break
            # diff = 0.0
            # if not self.journal_id.account_deb_subdem or not self.journal_id.account_cre_subdem:
                # raise Warning("Se debe configurar las cuentas de subsidio a la demanda en el diario.")
            
            # active_model = self._context.get('active_model')   
            
            
            
            # if not self.partner_id.parent_id:
                # p = self.partner_id
            # else:
                # p = self.partner_id.parent_id
            
            # # raise UserError('--------------------------entra4'+str( p )+str('   ' ) + str(self.type)+str('   ' ) + str(active_model))
            
            # if self.type in ('out_invoice', 'out_refund') and active_model != 'account.invoice.debitnote' :
            
                    # # raise UserError('--------------------------entra4'+str( p )+str('   ' ) + str(self.type)+str('   ' ) + str(active_model))
                    # for line in self.invoice_line_ids:

                        # # print('--------------------------entra2')
                        # if line.analytics_id.state == 'valid':
                            # # print('--------------------------entra3')
                            # # raise UserError('-------------state == valid-------------'+str( p )+str('   ' ) + str(self.type)+str('   ' ) + str(active_model))
                            # for dist in line.analytics_id.account_ids:
                                # # raise UserError('--------------------------entra4'+str(line))
                                # # raise UserError('--------------------------entra4'+str(line.product_id))
                                # diff = (line.diferencia_subsidio * line.quantity) * dist.rate
                                # if diff > 0:
                                    # if not p.categorias_id.id:
                                        # raise UserError ('No existe categoria de subsidio para el Asociado: '+str(p.name)) 
                                    # else:
                                        # # _logger.info('diff')
                                        # # _logger.info(diff)
                                    
                                        # if self.categoria_id:  #si es categoria manual
                                            # categoria_subs = self.categoria_id.id
                                        # else: 
                                            # self.categoria_id =  p.categorias_id
                                            # categoria_subs = p.categorias_id.id
                                        # #DEBITO SUBSIDIO DEMANDA
                                        # self.env.cr.execute(" INSERT INTO account_move_line (create_date, company_id, date_maturity, partner_id, blocked, "
                                            # " create_uid, credit, journal_id, debit, ref, account_id, write_date, "
                                            # " date, write_uid, move_id, name, analytic_account_id,categ_id,company_currency_id,balance,product_id) "
                                            # " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING ID ",(datetime.now(), self.env.user.company_id.id, date_maturity, p.id, 
                                            # False,self.env.user.id, 0.0, self.journal_id.id,diff, self.number, self.journal_id.account_deb_subdem.id,datetime.now(),self.date_invoice, self.env.user.id,
                                            # self.move_id.id,'SD'+' REF: '+dist.ref,line.account_analytic_id.id,categoria_subs,self.env.user.company_id.currency_id.id,diff,line.product_id.id))
                                        # #DEBITO SUBSIDIO DEMANDA
                                        # self.env.cr.execute(" INSERT INTO account_move_line (create_date, company_id, date_maturity, partner_id, blocked, "
                                            # " create_uid, credit, journal_id, debit, ref, account_id, write_date, "
                                            # " date, write_uid, move_id, name, analytic_account_id,categ_id,company_currency_id,balance,product_id) "
                                            # " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING ID ",(datetime.now(), self.env.user.company_id.id, date_maturity, p.id, 
                                            # False,self.env.user.id, diff, self.journal_id.id, 0.0, self.number, self.journal_id.account_cre_subdem.id,datetime.now(),self.date_invoice, self.env.user.id,
                                            # self.move_id.id,'SD'+' REF: '+dist.ref,line.account_analytic_id.id,categoria_subs,self.env.user.company_id.currency_id.id,-diff,line.product_id.id))
                                        # _logger.info('/////////////////////////')
 
            # if active_model == 'account.invoice.debitnote' :
                    # for line in self.invoice_line_ids:

                        # print('--------------------------entra2')
                        # if line.analytics_id.state == 'valid':
                            # print('--------------------------entra3')
                            # for dist in line.analytics_id.account_ids:
                                # # raise UserError('--------------------------entra4'+str(line))
                                # diff = (line.diferencia_subsidio * line.quantity) * dist.rate
                                # if diff > 0:
                                    # if not p.categorias_id.id:
                                        # raise UserError ('No existe categoria de subsidio para el Asociado: '+str(p.name)) 
                                    # else:
                                        # if self.categoria_id:
                                            # categoria_subs = self.categoria_id.id
                                        # else: 
                                            # categoria_subs = p.categorias_id.id
                                        # #DEBITO SUBSIDIO DEMANDA
                                        # self.env.cr.execute(" INSERT INTO account_move_line (create_date, company_id, date_maturity, partner_id, blocked, "
                                            # " create_uid, debit, journal_id, credit, ref, account_id, write_date, "
                                            # " date, write_uid, move_id, name, analytic_account_id,categ_id,company_currency_id,balance) "
                                            # " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING ID ",(datetime.now(), self.env.user.company_id.id, date_maturity,
                                            # p.id, False,self.env.user.id, 0.0, self.journal_id.id,diff, self.number, self.journal_id.account_deb_subdem.id,datetime.now(),
                                            # self.date_invoice, self.env.user.id,self.move_id.id,'SD'+' REF: '+dist.ref,line.account_analytic_id.id,categoria_subs,
                                            # self.env.user.company_id.currency_id.id,diff,line.product_id.id))
                                        # #DEBITO SUBSIDIO DEMANDA
                                        # self.env.cr.execute(" INSERT INTO account_move_line (create_date, company_id, date_maturity, partner_id, blocked, "
                                            # " create_uid, debit, journal_id, credit, ref, account_id, write_date, "
                                            # " date, write_uid, move_id, name, analytic_account_id,categ_id,company_currency_id,balance) "
                                            # " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING ID ",(datetime.now(), self.env.user.company_id.id, date_maturity, 
                                            # p.id, False,self.env.user.id, diff, self.journal_id.id, 0.0, self.number, self.journal_id.account_cre_subdem.id,datetime.now(),
                                            # self.date_invoice, self.env.user.id,self.move_id.id,'SD'+' REF: '+dist.ref,line.account_analytic_id.id,categoria_subs,
                                            # self.env.user.company_id.currency_id.id,-diff,line.product_id.id))
                               
                                
        # return res
        
        
        
        
        
# class account_invoice_line_extended(models.Model):
    # _inherit = 'account.invoice.line'

    # diferencia_subsidio = fields.Float(string="Diferencia",default=0)

    # def _set_taxes(self):
        # print('subsidio _set_taxes')
        # """ Used in on_change to set taxes and price."""
        # if self.invoice_id.type in ('out_invoice', 'out_refund'):
            # taxes = self.product_id.taxes_id or self.account_id.tax_ids
        # else:
            # taxes = self.product_id.supplier_taxes_id or self.account_id.tax_ids
        
        # # Keep only taxes of the company
        # company_id = self.company_id or self.env.user.company_id
        # taxes = taxes.filtered(lambda r: r.company_id == company_id)

        # self.invoice_line_tax_ids = fp_taxes = self.invoice_id.fiscal_position_id.map_tax(taxes, self.product_id, self.invoice_id.partner_id)

        # fix_price = self.env['account.tax']._fix_tax_included_price
        
        # if self.invoice_id.type in ('in_invoice', 'in_refund'):

            # prec = self.env['decimal.precision'].precision_get('Product Price')
            # if not self.price_unit or float_compare(self.price_unit, self.product_id.standard_price, precision_digits=prec) == 0:
                # self.price_unit = fix_price(self.product_id.standard_price, taxes, fp_taxes)
        # else:
            # res = self._get_diff(self.product_id,self.invoice_id.partner_id)
            # _logger.info('ventas')
            # _logger.info(res)
            # self.price_unit = res.get('price_unit',self.product_id.standard_price)
            # self.diferencia_subsidio = res.get('diferencia_subsidio',0)
            # _logger.info(self.price_unit)
            # _logger.info(self.diferencia_subsidio)
            # self.price_unit = fix_price(self.price_unit, taxes, fp_taxes)


        
    # def _get_diff(self, product_id, partner_id):
        # print('subsidio _get_diff')
        # res,diff,price = {},0.0,0.0
        # for items in partner_id.property_product_pricelist.item_ids:
            # if items.categoria_id.id == partner_id.categorias_id.id and (items.product_id.id == product_id.id or items.categ_id.id == product_id.categ_id.id or items.product_tmpl_id.id == product_id.product_tmpl_id.id):
                # if price != 0:
                    # break

                # if  items.price_taxed_subsidiado and  items.tax_id.price_subsi_include:
                
                    # price = items.price_taxed_subsidiado
                # else:
                    # price = product_id.lst_price+items.price_surcharge
                # if items.price_surcharge < 0:
                    # res['diferencia_subsidio'] = abs(items.price_surcharge)
            # if price >0:
                # res['price_unit'] = price
            # else:
                # res['price_unit'] = float(product_id.lst_price)
        # return res

# class account_journal_extended(models.Model):
    # _inherit = 'account.journal'

    # acc_db_subdem = fields.Many2one('account.account', string='Débito Subsidio Demanda')
    # acc_cr_subdem = fields.Many2one('account.account', string='Crédito Subsidio Demanda')




# class AccountMoveLineCategorias(models.Model):
    # _inherit = 'account.move.line'

    # categorias_id = fields.Many2one('subsidio.categorias', string='Categ Subs')
    
    
    

# class WithholdingTaxLine(models.Model):
    # _inherit = 'withholding.tax.line'

    # #### agregamos categ_id en el  done_taxes = {  para el impuesto

    # @api.model
    # def withholding_tax_line_move_line_get(self):
        # print('subsidio withholding_tax_line_move_line_get')
        # done_taxes = {}
        # account_move = self.env['account.move']


        # part = self.tax_id.withholding_partner_id
        # line = [(0, 0, part.id)]
# )
        # withholding_line = self.env['withholding.tax.line'].search([('id','=', self.id)])

        # self.withholding_ref =self.env['account.invoice'].search([('number','=', self.invoice_id.number)])
        # self.date_invoice = self.env['account.invoice'].search([('id','=', self.invoice_id.id)]).date_invoice

        # for tax_line in withholding_line:

            # journal = self.tax_id.withholding_journal_id

            # move_vals = {

                # 'journal_id': journal.id,
                # 'date': self.date_invoice,
                # 'narration': 'Retenciones',
            # }

            # self.tax_move_id = account_move.create(move_vals)
            

            # tax_line.move_id= self.tax_move_id

            # if tax_line.amount:
                # tax = tax_line.tax_id
                # acc_id_db = tax_line.account_id_db.id
                # acc_id_cr = tax_line.account_id_cr.id
                # if not acc_id_db:
                     # raise UserError('Por favor debe indicar la cuenta débito para retenciones en el impuesto .')
                # if not acc_id_cr:
                     # raise UserError('Por favor debe indicar la cuenta crédito para retenciones en el impuesto.')
                     
                # print('tax',tax)
                # print('journal_id',tax_line.tax_id.withholding_journal_id.id)
                

                # done_taxes_db = {'account_id':tax_line.account_id_db.id,
                        # 'partner_id':tax_line.tax_id.withholding_partner_id.id,
                        # 'journal_id':tax_line.tax_id.withholding_journal_id.id,
                        # 'product_id':'',
                        # 'debit': tax_line.amount,
                        # 'credit': 0,
                        # 'date_maturity':self.date_invoice,
                        # 'categ_id':tax_line.tax_id.withholding_partner_id.categorias_id.id,
                        # 'analytics_id':'',
                        # 'analytic_account_id':'',
                        # 'name':self.invoice_id.number,
                        # 'move_id':self.tax_move_id.id,
                        # 'ref':self.withholding_ref.number,
                        # 'date': self.date_invoice}
                        

                # done_taxes_cr = {'account_id':tax_line.account_id_cr.id,
                        # 'partner_id':tax_line.tax_id.withholding_partner_id.id,
                        # 'journal_id':tax_line.tax_id.withholding_journal_id.id,
                        # 'product_id':'',
                        # 'debit': 0,
                        # 'credit': tax_line.amount,
                        # 'date_maturity':self.date_invoice,
                        # 'categ_id':tax_line.tax_id.withholding_partner_id.categorias_id.id,
                        # 'analytics_id':'',
                        # 'analytic_account_id':'',
                        # 'name':self.invoice_id.number,
                        # 'move_id':self.tax_move_id.id,
                        # 'ref':self.withholding_ref.number,
                        # 'date': self.date_invoice,}
                        

                # self.tax_move_id.write({'line_ids':[(0, 0, done_taxes_db),(0, 0, done_taxes_cr)]})              

            # self.tax_move_id.post()    

        # print ('done_taxes', done_taxes)
        # return (done_taxes)

