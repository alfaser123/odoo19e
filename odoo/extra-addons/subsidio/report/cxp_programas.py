# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp import addons
from openerp import SUPERUSER_ID
import itertools
from dateutil.relativedelta import relativedelta
from lxml import etree
from openerp import models, fields, api, _
from openerp.osv import osv, fields as fields2
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp.addons.decimal_precision as dp
import math


class account_financial_reports_accounting_cxp_programas(models.Model):
    _name = "fpa.cxp.programas"

    date = fields.Datetime(string="Fecha")
    date_from = fields.Date(string="Fecha Inicial")
    date_to = fields.Date(string="Fecha Final")
    estado = fields.Selection(
        [('borrador', 'Borrador'), ('validados', 'Validados'), ('todos', 'Todos')], default='todos', string='Estados')
    company_id = fields.Many2one('res.company', string='Compañia')
    user_id = fields.Many2one('res.users', string='Usuario')
    financial_id = fields.Many2one('fpa.financial.reports', string='Reporte')
    chart_account_id = fields.Many2one('account.account', string='Plan Contable',
                                       help='Select Charts of Accounts', required=True, domain=[('parent_id', '=', False)])


class account_financial_reports_accounting_cxp_programas_line(models.Model):
    _name = "fpa.cxp.programas.line"

    account_id = fields.Many2one(
        'account.account', string='Cuenta', ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner', string='Tercero', ondelete='cascade')
    tipo_partner = fields.Char(string='Tipo de deudor')
    rango = fields.Char(string='Rango')
    valor = fields.Float(string='Valor', digits=dp.get_precision('Account'))
    provision = fields.Float(string='Provisión', digits=dp.get_precision('Account'))
    nivel = fields.Integer(string='Nivel')
    cuenta = fields.Char(string='Cuenta')
    company_id = fields.Many2one('res.company', string='Compañia')
    user_id = fields.Many2one('res.users', string='Usuario')
    encabezado_id = fields.Many2one(
        'fpa.cxp.programas', string='Encabezado', ondelete='cascade')


class wizard_account_financial_reports_accounting_cxp_programas(models.TransientModel):
    _name = "fpa.cxp.programas.wizard"


    account_filter = fields.Boolean(string="Filtro adicional de cuentas")
    partner_filter = fields.Boolean(string="Filtro adicional de terceros")
    journal_filter = fields.Boolean(string="Filtro adicional de diarios")
    chart_account_id = fields.Many2one('account.account', string='Plan Contable',
                                       help='Select Charts of Accounts', required=True, domain=[('parent_id', '=', False)])
    company_id = fields.Many2one(
        'res.company', related='chart_account_id.company_id', string='Company', readonly=True)
    journal_ids = fields.Many2many('account.journal', string='Diarios')
    account_ids = fields.Many2many(
        'account.account', string='Cuentas', domain=[('type', '!=', 'view')])
    partner_ids = fields.Many2many('res.partner', string='Terceros')
    date_to = fields.Date(string="Fecha Final", required=True)

    @api.one
    @api.onchange('chart_account_id')
    def get_filter(self):
        print 'contexto'
        id = self.env.context.get('active_ids',False)
        financial_reports = self.env['fpa.financial.reports'].browse(id)
        self.account_filter = financial_reports.account_filter
        self.partner_filter = financial_reports.partner_filter
        self.journal_filter = financial_reports.journal_filter

    @api.multi
    def generar(self):
        print 'GENERAR'
        self.env.cr.execute(''' DELETE FROM fpa_cxp_programas_line WHERE company_id = %s and user_id = %s''' % (
            self.company_id.id, self.env.user.id))
        print '0'
        self.env.cr.execute(''' DELETE FROM fpa_cxp_programas WHERE company_id = %s and user_id = %s''' % (
            self.company_id.id, self.env.user.id))
        print '1'
        where = ''
        financial_reports = self.env['fpa.financial.reports'].browse(self.env.context['active_id'])
        if financial_reports:
            if financial_reports.concepts_ids:
                where += ' AND ( '
                for conceptos in financial_reports.concepts_ids:
                    if conceptos.account_ids:
                        for cuentas in conceptos.account_ids:
                            where += " aa.code like '%s%s' OR" % (cuentas.code,'%')
                where = where[:len(where)-2]
                where += ' ) '
        # Agrega encabezado con parametros indicados por el usuario
        self.env.cr.execute(''' INSERT INTO fpa_cxp_programas(date, date_to, company_id, user_id,chart_account_id,financial_id) VALUES ('%s','%s',%s,%s,%s,%s) RETURNING ID ''' % (
            datetime.now(), self.date_to, self.company_id.id, self.env.user.id, self.chart_account_id.id,financial_reports.id))
        try:
            encabezado_id = self._cr.fetchone()[0]
        except ValueError:
            encabezado_id = False
        if self.journal_ids:
            where += ''' AND aml.journal_id in (%s) ''' % (
                ','.join(str(x.id) for x in self.journal_ids))
        if self.account_ids:
            where += ''' AND aml.account_id in (%s) ''' % (
                ','.join(str(x.id) for x in self.account_ids))
        if self.partner_ids:
            where += ''' AND aml.partner_id in (%s) ''' % (
                ','.join(str(x.id) for x in self.partner_ids))

        print '2'
        # Verificar si tiene el modulo de niif_account instalado
        module = self.env['ir.module.module'].search([('name','=','niif_account'),('state','=','installed')])
        if not module:
            condition = 'aa.id = aml.account_id'
        else:
            condition = '((aa.id = aml.account_id AND aa.niif is false)or((aa.id = aml.account_niif_id AND aa.niif is true)))'
        #Movimientos
        movimientos = '''INSERT INTO fpa_cxp_programas_line (user_id,company_id,account_id, cuenta, valor, encabezado_id,nivel, tipo_partner,rango)
                            SELECT %s,%s,aa.id, aa.code, sum(aml.debit - aml.credit) as valor, %s::integer as encabezado_id, 100::integer nivel, td.name as tipo_partner,FV.name as rango
                                FROM account_move_line aml
                                    INNER JOIN account_move am ON am.id = aml.move_id
                                    INNER JOIN account_journal aj ON aj.id = am.journal_id AND aj.provision = False
                                    INNER JOIN account_account aa ON %s AND aa.type = 'payable'
                                    INNER JOIN res_partner rp ON rp.id = aml.partner_id
                                    LEFT JOIN tipo_da td ON td.id = rp.tipo_da_id
                                    LEFT JOIN (select facturas_vencidas.partner_id, ec.name, facturas_vencidas.edad from (
                                        select ai.partner_id, max(extract(days from now()-ai.date_due)) as edad
                                        from account_invoice ai
                                        group by ai.partner_id
                                        ) as facturas_vencidas
                                        INNER JOIN edad_cartera ec on (ec.desde > facturas_vencidas.edad and ec.hasta < facturas_vencidas.edad)
                                    ) as FV ON FV.partner_id = aml.partner_id
                                        AND aml.company_id = aa.company_id
                                        WHERE  aml.company_id = %s AND aa.parent_zero = %s
                                        AND aml.date <= '%s'
                                        AND am.state = 'posted'
                                        %s
                                        GROUP BY aa.id, aa.code, td.name, FV.name ''' % (self.env.user.id, self.company_id.id, encabezado_id,condition, self.env.user.company_id.id, self.chart_account_id.id,self.date_to, where)
        print movimientos
        self._cr.execute(movimientos)
        for structure in self.chart_account_id.structure_id.sorted(key=lambda r: r.sequence, reverse=True):
            # nivel
            nivel = '''INSERT INTO fpa_cxp_programas_line (user_id, company_id, account_id, cuenta, partner_id,
                        valor ,encabezado_id,nivel)
                          select %s,%s,aar.id, aar.code, null, sum(valor),
                          %s, %s
                             from
                                 fpa_cxp_programas_line fbpl
                                inner join account_account aar on aar.code = substring(fbpl.cuenta from 1 for %s) and aar.type ='view' and length(fbpl.cuenta) > %s and length(aar.code) = %s and aar.company_id = fbpl.company_id
                                 where fbpl.nivel=100 and fbpl.user_id = %s and fbpl.company_id = %s
                                 group by aar.id, aar.code ''' % (self.env.user.id, self.company_id.id, encabezado_id,
                                                                  structure.sequence, structure.digits, structure.digits, structure.digits, self.env.user.id, self.company_id.id)
            self._cr.execute(nivel)
        #print '4'
        # Inserta movimiento resumen por cuenta regular
        #resumen_account = '''INSERT INTO fpa_cxp_programas_line (user_id, company_id,account_id, partner_id, valor, provision, encabezado_id, nivel)
        #                     select %s,%s, account_id, null, sum(fbpl.valor),  sum(fbpl.provision) as provision, %s, 99
        #                         from fpa_cxp_programas_line fbpl
        #                             where fbpl.user_id = %s and fbpl.nivel=100 and fbpl.company_id = %s
        #                             GROUP BY account_id''' % (self.env.user.id, self.company_id.id, encabezado_id, self.env.user.id, self.company_id.id)
        #self._cr.execute(resumen_account)
        print '5'
        # Inserta PUC como resumen de todos los movimiento
        chart_account = '''INSERT INTO fpa_cxp_programas_line (user_id,company_id,account_id, cuenta, partner_id, valor ,encabezado_id,nivel)
                            select %s,%s,%s, '%s', null, sum(fbpl.valor) as valor, %s, 98
                                from fpa_cxp_programas_line fbpl
                                    where fbpl.user_id = %s and fbpl.nivel=100 and fbpl.company_id = %s''' % (self.env.user.id, self.company_id.id, self.chart_account_id.id, self.chart_account_id.code, encabezado_id, self.env.user.id, self.company_id.id)
        self._cr.execute(chart_account)

        print '6'
        self._cr.execute(" DELETE FROM fpa_cxp_programas_line WHERE valor=0 ")
        return financial_reports.view()
