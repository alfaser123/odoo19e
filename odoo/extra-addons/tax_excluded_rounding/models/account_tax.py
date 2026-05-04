from odoo import fields, models
from odoo.tools.float_utils import float_is_zero, float_round


class AccountTax(models.Model):
    _inherit = "account.tax"

    excluded_rounding_method = fields.Selection(
        selection=[
            ("none", "Sin redondeo"),
            ("unit_total", "Redondear sin decimales: precio unitario + incl imp"),
            ("line_total", "Redondear sin decimales: cant x precio unit + incl imp"),
        ],
        string="Metodo redondeo",
        default="none",
        tracking=True,
        help="Disponible cuando el impuesto fuerza precio sin impuesto. Ajusta el impuesto, no la base.",
    )

    def _round_base_lines_tax_details(self, base_lines, company, tax_lines=None):
        res = super()._round_base_lines_tax_details(base_lines, company, tax_lines=tax_lines)
        self._apply_excluded_total_rounding(base_lines, company)
        return res

    def _apply_excluded_total_rounding(self, base_lines, company):
        for base_line in base_lines:
            if base_line.get("special_type"):
                continue
            tax_details = base_line.get("tax_details") or {}
            taxes_data = tax_details.get("taxes_data") or []
            eligible_taxes_data = [
                tax_data
                for tax_data in taxes_data
                if tax_data["tax"].price_include_override == "tax_excluded"
                and tax_data["tax"].excluded_rounding_method in ("unit_total", "line_total")
                and not tax_data.get("is_reverse_charge")
            ]
            if not eligible_taxes_data:
                continue

            self._sync_excluded_rounding_total_included(base_line, company)

            method = eligible_taxes_data[0]["tax"].excluded_rounding_method
            if any(tax_data["tax"].excluded_rounding_method != method for tax_data in eligible_taxes_data):
                continue

            quantity = abs(base_line.get("quantity") or 1.0) or 1.0
            if method == "unit_total":
                target_total_currency = float_round(
                    tax_details["total_included_currency"] / quantity,
                    precision_digits=0,
                ) * quantity
            else:
                target_total_currency = float_round(
                    tax_details["total_included_currency"],
                    precision_digits=0,
                )

            currency = base_line["currency_id"]
            delta_currency = currency.round(target_total_currency - tax_details["total_included_currency"])
            if currency.is_zero(delta_currency):
                continue

            self._distribute_excluded_rounding_delta(
                eligible_taxes_data,
                delta_currency,
                "_currency",
                currency,
            )
            tax_details["total_included_currency"] = currency.round(tax_details["total_included_currency"] + delta_currency)

            rate = base_line.get("rate") or 0.0
            if rate:
                delta_company = company.currency_id.round(delta_currency / rate)
                self._distribute_excluded_rounding_delta(
                    eligible_taxes_data,
                    delta_company,
                    "",
                    company.currency_id,
                )
                tax_details["total_included"] = company.currency_id.round(tax_details["total_included"] + delta_company)

    def _sync_excluded_rounding_total_included(self, base_line, company):
        tax_details = base_line["tax_details"]
        for suffix, currency in (("_currency", base_line["currency_id"]), ("", company.currency_id)):
            tax_details[f"total_included{suffix}"] = currency.round(
                tax_details[f"total_excluded{suffix}"]
                + sum(tax_data[f"tax_amount{suffix}"] for tax_data in tax_details["taxes_data"])
            )

    def _distribute_excluded_rounding_delta(self, taxes_data, delta_amount, suffix, currency):
        if float_is_zero(delta_amount, precision_digits=currency.decimal_places):
            return

        target_factors = [
            {
                "factor": abs(tax_data[f"tax_amount{suffix}"]) or 1.0,
                "tax_data": tax_data,
            }
            for tax_data in taxes_data
        ]
        amounts_to_distribute = self._distribute_delta_amount_smoothly(
            precision_digits=currency.decimal_places,
            delta_amount=delta_amount,
            target_factors=target_factors,
        )
        for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
            tax_data = target_factor["tax_data"]
            tax_data[f"tax_amount{suffix}"] = currency.round(tax_data[f"tax_amount{suffix}"] + amount_to_distribute)
            for tax_rep_data in tax_data.get("tax_reps_data", []):
                factor = tax_rep_data["tax_rep"].factor
                tax_rep_data[f"tax_amount{suffix}"] = currency.round(
                    tax_rep_data[f"tax_amount{suffix}"] + (amount_to_distribute * factor)
                )
