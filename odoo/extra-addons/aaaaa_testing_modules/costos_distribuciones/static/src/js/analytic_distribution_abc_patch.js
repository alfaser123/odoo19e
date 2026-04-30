/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { roundDecimals } from "@web/core/utils/numbers";
import { AnalyticDistribution } from "@analytic/components/analytic_distribution/analytic_distribution";

const MAP_FIELD = "abc_distribution_account_map";

patch(AnalyticDistribution.prototype, {
    async _abcFetchGlAccounts(ids) {
        if (!ids.length) {
            return {};
        }
        const records = await this.orm.searchRead(
            "account.account",
            [["id", "in", ids]],
            ["id", "display_name"]
        );
        return Object.fromEntries(records.map((r) => [r.id, r]));
    },

	async jsonToData(jsonFieldValue) {
		await super.jsonToData(jsonFieldValue);

		const accountMap = this.props.record.data[MAP_FIELD] || {};
		const glIds = Object.values(accountMap).filter(Boolean);
		const glDict = await this._abcFetchGlAccounts(glIds);

		for (const line of this.state.formattedData) {

			// 🔥 clave EXACTA usada por Odoo
			const key = line.key;

			const glId = accountMap[key];

			line.glAccountId = glId || false;
			line.glAccountDisplayName =
				glId && glDict[glId] ? glDict[glId].display_name : false;
		}
	},

	recordProps(line) {
    const analyticAccountFields = {
        id: { type: "int" },
        display_name: { type: "char" },
        color: { type: "int" },
        plan_id: { type: "many2one" },
        root_plan_id: { type: "many2one" },
    };

    const recordFields = {};
    const values = {};

    // Mapa de cuentas analíticas actuales por plan
    const accountsByPlanId = {};
    for (const account of line.analyticAccounts) {
        accountsByPlanId[account.planId] = account;
    }

    // Crear SIEMPRE una columna por cada plan visible del popup
    for (const plan of this.allPlans) {
		const fieldName = this.planIdToColumn[plan.id] || `x_plan${plan.id}_id`;


        const currentAccount = accountsByPlanId[plan.id];
        const companyId = this.props.record.data.company_id && this.props.record.data.company_id[0];
        const domain = companyId
            ? [
                "&",
                ["root_plan_id", "=", plan.id],
                "|",
                ["company_id", "parent_of", companyId],
                ["company_id", "=", false],
            ]
            : [["root_plan_id", "=", plan.id]];

        recordFields[fieldName] = {
            string: plan.name,
            relation: "account.analytic.account",
            type: "many2one",
            related: {
                fields: analyticAccountFields,
                activeFields: analyticAccountFields,
            },
            domain,
        };

        values[fieldName] = currentAccount?.accountId
            ? [currentAccount.accountId, currentAccount.accountDisplayName]
            : false;
    }

    // Cuenta contable ABC
    recordFields.abc_account_id = {
        string: _t("Cuenta contable"),
        relation: "account.account",
        type: "many2one",
        domain: [["active", "!=", false]],
    };

    values.abc_account_id = line.glAccountId
        ? [line.glAccountId, line.glAccountDisplayName || ""]
        : false;

    // Porcentaje
    recordFields.percentage = {
        string: _t("Percentage"),
        type: "percentage",
        cellClass: "numeric_column_width",
        ...this.decimalPrecision,
    };
    values.percentage = line.percentage;

    // Columna valor, si aplica
    if (this.props.amount_field) {
        const { string, name, type, currency_field } = this.props.record.fields[this.props.amount_field];
        recordFields[name] = {
            string,
            name,
            type,
            currency_field,
            cellClass: "numeric_column_width",
        };
        values[name] = this.props.record.data[name] * values.percentage;

        if (currency_field) {
            const currencyField = this.props.record.fields[currency_field];
            recordFields[currency_field] = {
                name: currencyField.name,
                string: currencyField.string,
                type: currencyField.type,
                relation: currencyField.relation,
                invisible: true,
            };
            values[currency_field] = [this.props.record.data[currency_field].id, ""];
        }
    }

	console.log("ABC allPlans =", this.allPlans);
	console.log("ABC planIdToColumn =", this.planIdToColumn);
	console.log("ABC line.analyticAccounts =", line.analyticAccounts);
	console.log("ABC recordFields =", Object.keys(recordFields));
    return {
        fields: recordFields,
        values: values,
        activeFields: recordFields,
        hooks: {
            onRecordChanged: async (record, changes) => await this.lineChanged(record, changes, line),
        },
    };
},

    async lineChanged(record, changes, line) {
        await super.lineChanged(record, changes, line);

        const glSelected = record.data.abc_account_id || false;
        line.glAccountId = glSelected ? glSelected.id : false;
        line.glAccountDisplayName = glSelected ? glSelected.display_name : false;

        if (changes.percentage !== undefined && changes.percentage !== line.percentage) {
            line.percentage = roundDecimals(record.data.percentage, this.decimalPrecision.digits[1] + 2);
        }
    },



    addLine() {
        super.addLine();
        const line = this.state.formattedData[this.state.formattedData.length - 1];
        if (line) {
            line.glAccountId = false;
            line.glAccountDisplayName = false;
        }
    },



	_abcGetAccountMap() {
		const result = {};

		for (const line of this.state.formattedData) {

			const key = line.key;

			if (key && line.glAccountId) {
				result[key] = line.glAccountId;
			}
		}

		return result;
	},


	
	async save() {
		const distributionData = this.dataToJson();
		const accountMap = this._abcGetAccountMap();

		console.log("ABC SAVE distribution =", distributionData);
		console.log("ABC SAVE accountMap =", accountMap);

		await this.props.record.update({
			[this.props.name]: distributionData,
			[MAP_FIELD]: accountMap,
		});

		if (this.props.multi_edit) {
			await this.jsonToData(this.props.record.data[this.props.name]);
			this.initialFormattedData = this.state.formattedData;
			this.state.formattedData = [];
			this.state.update_plan = {};
		}
	},

    onSaveNew() {
        this.closeAnalyticEditor();
        const { record, product_field, account_field } = this.props;

        this.openTemplate({
            resId: false,
            context: {
                default_analytic_distribution: this.dataToJson(),
                default_abc_distribution_account_map: this._abcGetAccountMap(),
                default_partner_id: record.data.partner_id ? record.data.partner_id.id : undefined,
                default_product_id: product_field ? record.data[product_field]?.id : undefined,
                default_account_prefix: account_field
                    ? record.data[account_field]?.display_name?.substr(0, 3)
                    : undefined,
            },
        });
    },
});