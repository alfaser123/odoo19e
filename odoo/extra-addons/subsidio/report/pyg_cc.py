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


class account_financial_reports_accounting_pyg_cc(models.Model):
    _name = "fpa.pyg.cc"

    date = fields.Datetime(string="Fecha")
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Año fiscal',index=True)
    period_id = fields.Many2one('account.period', string='Periodo',index=True)
    date_from = fields.Date(string="Fecha Inicial")
    date_to = fields.Date(string="Fecha Final")
    estado = fields.Selection(
        [('borrador', 'Borrador'), ('validados', 'Validados'), ('todos', 'Todos')], default='todos', string='Estados')
    company_id = fields.Many2one('res.company', string='Compañia')
    user_id = fields.Many2one('res.users', string='Usuario')
    financial_id = fields.Many2one('fpa.financial.reports', string='Reporte')
    chart_account_id = fields.Many2one('account.account', string='Plan Contable',
                                       help='Select Charts of Accounts', required=True, domain=[('parent_id', '=', False)])


class account_financial_reports_accounting_pyg_cc_line(models.Model):
    _name = "fpa.pyg.cc.line"

    account_id = fields.Many2one(
        'account.account', string='Cuenta', ondelete='cascade')
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Cuenta analitica', ondelete='cascade')
    amount_ejecutado = fields.Float(string='Ejecutado', digits=dp.get_precision('Account'))
    amount_presupuestado = fields.Float(string='Presupuestado', digits=dp.get_precision('Account'))
    amount_ejecutado_ant = fields.Float(string='Ejecutado Periodo Ant.', digits=dp.get_precision('Account'))
    nivel = fields.Integer(string='Nivel')
    cuenta = fields.Char(string='Cuenta')
    company_id = fields.Many2one('res.company', string='Compañia')
    user_id = fields.Many2one('res.users', string='Usuario')
    description = fields.Text(string="Descripción")
    resume = fields.Boolean(string="Resumen")
    concepto = fields.Integer(string="Concepto")
    encabezado_id = fields.Many2one('fpa.pyg.cc', string='Encabezado', ondelete='cascade')

class wizard_account_financial_reports_accounting_pyg_cc(models.TransientModel):
    _name = "fpa.pyg.cc.wizard"

    account_filter = fields.Boolean(string="Filtro adicional de cuentas")
    analytic_filter = fields.Boolean(string="Filtro adicional de cuenta analitica")
    chart_account_id = fields.Many2one('account.account', string='Plan Contable',
                                       help='Select Charts of Accounts', required=True, domain=[('parent_id', '=', False)])
    company_id = fields.Many2one(
        'res.company', related='chart_account_id.company_id', string='Company', readonly=True)
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Año fiscal',index=True)
    period_id = fields.Many2one('account.period', string='Periodo',index=True)
    account_ids = fields.Many2many(
        'account.account', string='Cuentas', domain=[('type', '!=', 'view')])
    analytic_ids = fields.Many2many(
        'account.analytic.account', string='Cuentas analiticas', domain=[('type', '!=', 'view')])

    estado = fields.Selection([('borrador', 'Borrador'), ('validados', 'Validados'), (
        'todos', 'Todos')], default='todos', string='Estados', required=True)

    @api.one
    @api.onchange('chart_account_id')
    def get_filter(self):
        id = self.env.context.get('active_ids',False)
        financial_reports = self.env['fpa.financial.reports'].browse(id)
        self.account_filter = financial_reports.account_filter
        self.partner_filter = financial_reports.partner_filter
        self.journal_filter = financial_reports.journal_filter
        self.analytic_filter = financial_reports.analytic_filter

    @api.one
    @api.constrains('date_from', 'date_to')
    def _validar_fechas(self):
        if self.date_from > self.date_to:
            raise Warning(_('Error en las fechas!'), _(
                "Las fechas planificadas estan mal configuradas"))

    @api.multi
    def generar(self):
        conf = self.env['account.budget.config'].search([])
        self.env.cr.execute(''' DELETE FROM fpa_pyg_cc_line WHERE company_id = %s and user_id = %s''' % (
            self.company_id.id, self.env.user.id))
        self.env.cr.execute(''' DELETE FROM fpa_pyg_cc WHERE company_id = %s and user_id = %s''' % (
            self.company_id.id, self.env.user.id))
        where = ' 1=1 '
        financial_reports = self.env['fpa.financial.reports'].browse(self.env.context['active_id'])
        if financial_reports:
            if financial_reports.concepts_ids:
                where = '  ( '
                for conceptos in financial_reports.concepts_ids:
                    if conceptos.account_ids and not conceptos.resume:
                        for cuentas in conceptos.account_ids:
                            where += " aa.code like '%s%s' OR" % (cuentas.code,'%')
                where = where[:len(where)-2]
                where += ' ) '
        # Agrega encabezado con parametros indicados por el usuario
        if conf.mensual:
            if not self.period_id:
                raise Warning(_('Error de usuario'), _("Debe indicar un periodo"))
            #buscar periodo anterior
            periodo_anterior = self.period_id.id -1
            anterior = self.env['account.period'].browse(periodo_anterior)
            if anterior.special:
                periodo_anterior = anterior.id -1
                anterior = self.env['account.period'].browse(periodo_anterior)
            sql = " INSERT INTO fpa_pyg_cc(date, period_id, date_from, date_to, estado, company_id, user_id,chart_account_id,financial_id) VALUES ('%s',%s,'%s','%s', '%s',%s,%s,%s,%s) RETURNING ID " % (datetime.now(), self.period_id.id, self.period_id.date_start, self.period_id.date_stop, self.estado, self.company_id.id, self.env.user.id, self.chart_account_id.id, financial_reports.id)
        else:
            if not self.fiscalyear_id:
                raise Warning(_('Error de usuario'), _("Debe indicar un periodo"))
            #buscar periodo anterior
            anio_anterior = self.fiscalyear_id.id -1
            anterior = self.env['account.fiscalyear'].browse(anio_anterior)
            sql = " INSERT INTO fpa_pyg_cc(date, fiscalyear_id, date_from, date_to, estado, company_id, user_id,chart_account_id,financial_id) VALUES ('%s',%s,'%s','%s', '%s',%s,%s,%s,%s) RETURNING ID " % (datetime.now(), self.fiscalyear_id.id,self.fiscalyear_id.date_start, self.fiscalyear_id.date_stop,                                                                                                                                                                      self.estado, self.company_id.id, self.env.user.id, self.chart_account_id.id, financial_reports.id)

        self.env.cr.execute(sql)
        encabezado_id = False
        try:
            encabezado_id = self.env.cr.fetchone()[0]
        except ValueError:
            encabezado_id = False

        if self.analytic_ids:
            where += ''' AND gbeb.account_id in (%s) ''' % (','.join(str(x.id) for x in self.analytic_ids))

        conf = self.env['account.budget.config'].search([])
        if conf.mensual:
            where += ''' AND gbeb.period_id = %s'''%self.period_id.id
        else:
            where += ''' AND gbeb.fiscalyear_id = %s '''%self.fiscalyear_id.id

        movimientos = " INSERT INTO fpa_pyg_cc_line (user_id, company_id, account_id, cuenta, analytic_account_id, amount_ejecutado, "\
                " amount_presupuestado, amount_ejecutado_ant, encabezado_id, nivel, resume) select %s, %s, abp.account_id, "\
                " abp.code, gbeb.account_id as analytic_account_id, (gbeb.compromiso + gbeb.causado) as ejecutado, gbeb.aprobado, "\
                " gbeba.aprobado, %s, %s, %s from goverment_budget_execution_budget gbeb inner join account_budget_post abp on abp.id = gbeb.general_budget_id "\
                " inner join account_account aa on aa.id = abp.account_id "\
                " left join goverment_budget_execution_budget gbeba "\
				" on gbeba.general_budget_id = gbeb.general_budget_id and gbeba.account_id = gbeb.account_id and gbeba.period_id = %s "\
                " WHERE %s " % (self.env.user.id, self.env.user.company_id.id, encabezado_id, '98', False, anterior.id, where)
        self.env.cr.execute(movimientos)

        if financial_reports:
            amount_ejecutado,amount_presupuestado,amount_ejecutado_ant  = 0.0,0.0,0.0
            if self.analytic_ids:
                for analytic_line in self.analytic_ids:
                    amount_ejecutado,amount_presupuestado,amount_ejecutado_ant  = 0.0,0.0,0.0
                    for conceptos in financial_reports.concepts_ids:
                        if conceptos.account_ids:
                            for cuentas in conceptos.account_ids:
                                sql = " SELECT amount_ejecutado, amount_presupuestado, amount_ejecutado_ant FROM fpa_pyg_cc_line WHERE analytic_account_id = %s and account_id = %s AND user_id = %s AND company_id = %s "%(analytic_line.id,cuentas.id, self.env.user.id, self.company_id.id)
                                self.env.cr.execute(sql)
                                line = self.env.cr.fetchone()
                                if line:
                                    amount_ejecutado += line[0]
                                    amount_presupuestado += line[1]
                                    amount_ejecutado_ant += line[2]
                                #Hacer resumen cuentas tipo resumen para que no se muestre en la vista
                                #self.env.cr.execute(" UPDATE fpa_pyg_cc_line SET resume = True WHERE user_id = %s AND company_id =%s AND account_id = %s "%(self.env.user.id, self.env.user.company_id.id,cuentas.id))
                                #actualizr conceptos en movimientos
                                self.env.cr.execute(" UPDATE fpa_pyg_cc_line SET concepto = %s WHERE user_id = %s AND company_id =%s AND account_id = %s "%(conceptos.id,self.env.user.id, self.env.user.company_id.id,cuentas.id))
                        #Resumen por concepto
                        resumen = " INSERT INTO fpa_pyg_cc_line (user_id, company_id, description, analytic_account_id, amount_ejecutado, "\
                                " amount_presupuestado, amount_ejecutado_ant, encabezado_id, nivel, resume, concepto) " \
                                " VALUES (%s, %s, '%s', %s, %s, %s, %s, %s, 100,%s,%s) " % (self.env.user.id, self.company_id.id,
                                    conceptos.name, analytic_line.id, amount_ejecutado, amount_presupuestado, amount_ejecutado_ant, encabezado_id, False, conceptos.id)
                        self.env.cr.execute(resumen)
                    #Resumen por cuenta analitica
                    resumen_cc = " INSERT INTO fpa_pyg_cc_line (user_id, company_id, analytic_account_id, amount_ejecutado, "\
                                " amount_presupuestado, amount_ejecutado_ant, encabezado_id, nivel, resume) " \
                                " VALUES (%s, %s, %s, %s, %s, %s, %s, 100,%s) " % (self.env.user.id, self.company_id.id,
                                    analytic_line.id, amount_ejecutado, amount_presupuestado, amount_ejecutado_ant, encabezado_id, False)
                    self.env.cr.execute(resumen_cc)
                totales = " INSERT INTO fpa_pyg_cc_line (user_id,company_id,description,amount_ejecutado, amount_presupuestado,amount_ejecutado_ant, "\
                            " encabezado_id,nivel,resume) VALUES (%s, %s, '%s', %s, %s, %s,%s, 100,True) " % (self.env.user.id, self.company_id.id, 'TOTAL: ',
                            amount_ejecutado, amount_presupuestado, amount_ejecutado_ant , encabezado_id)
                self.env.cr.execute(totales)
        self.env.cr.execute(" DELETE FROM fpa_pyg_cc_line WHERE amount_ejecutado=0 AND amount_presupuestado=0 AND amount_ejecutado_ant=0 AND user_id = %s and company_id = %s "%(self.env.user.id, self.env.user.company_id.id))
        #Actualizar
        return financial_reports.view()
