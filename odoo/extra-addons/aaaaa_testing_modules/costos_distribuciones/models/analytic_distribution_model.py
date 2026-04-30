from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    abc_distribution_account_map = fields.Json(
        string='Mapa cuentas contables ABC',
        copy=True,
    )

    @api.constrains('analytic_distribution', 'abc_distribution_account_map')
    def _check_abc_distribution_account_map(self):
        for rec in self:
            analytic_distribution = rec.analytic_distribution or {}
            account_map = rec.abc_distribution_account_map or {}

            invalid_keys = set(account_map.keys()) - set(analytic_distribution.keys())
            if invalid_keys:
                raise ValidationError(_(
                    "El mapa contable ABC contiene combinaciones analíticas que no existen en la distribución analítica."
                ))

            account_ids = [acc_id for acc_id in account_map.values() if acc_id]
            existing = set(self.env['account.account'].browse(account_ids).exists().ids)
            missing = set(account_ids) - existing
            if missing:
                raise ValidationError(_(
                    "Hay cuentas contables ABC que no existen o fueron eliminadas."
                ))

    @api.model
    def _abc_get_distribution_with_accounts(self, vals):
        """
        Devuelve:
        {
            'distribution': {...},
            'account_map': {...}
        }
        usando los mismos modelos aplicables que usa analytic_distribution.
        """
        applicable_models = self._get_applicable_models({
            k: v for k, v in vals.items() if k != 'related_root_plan_ids'
        })

        distribution = {}
        account_map = {}
        applied_plans = vals.get('related_root_plan_ids', self.env['account.analytic.plan'])

        for model in applicable_models:
            if not applied_plans & model.distribution_analytic_account_ids.root_plan_id:
                model_distribution = model.analytic_distribution or {}
                distribution |= model_distribution

                model_account_map = model.abc_distribution_account_map or {}
                for key in model_distribution.keys():
                    if model_account_map.get(key):
                        account_map[key] = model_account_map[key]

                applied_plans += model.distribution_analytic_account_ids.root_plan_id

        return {
            'distribution': distribution,
            'account_map': account_map,
        }