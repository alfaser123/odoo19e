/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AnalyticDistribution } from "@analytic/components/analytic_distribution/analytic_distribution";

patch(AnalyticDistribution.prototype, {

    async jsonToData(jsonFieldValue) {
        // En Odoo estándar
        await super.jsonToData(jsonFieldValue);

        // Leemos nuestro campo paralelo desde el registro
        let detailedData = [];
        if (this.props.record && this.props.record.data.analytic_distribution_accounts) {
            let rawData = this.props.record.data.analytic_distribution_accounts;
            if (typeof rawData === "string") {
                try {
                    detailedData = JSON.parse(rawData);
                } catch(e) {
                    detailedData = [];
                }
            } else if (Array.isArray(rawData)) { // por si acaso
                detailedData = rawData;
            }
        }

        // Si no hay detalle guardado, dejamos lo estándar
        if (!Array.isArray(detailedData) || detailedData.length === 0) {
            for (const line of this.state.formattedData) {
                line.account_account_id = false;
            }
            return;
        }

        // Si tenemos detalle, reconstruimos state.formattedData basado en nuestra matriz
        let newFormattedData = [];
        for (const detail of detailedData) {
            // Buscamos una línea estándar que contenga esta cuenta, para heredar los nombres de etiquetas / colores ya consultadas.
            const modelLine = this.state.formattedData.find(ld => {
                const k = ld.analyticAccounts.reduce((p, n) => p.concat(n.accountId ? n.accountId : []), []).join(",");
                return k === detail.analytic_account_ids;
            });

            let analyticAccountsParams = modelLine ? JSON.parse(JSON.stringify(modelLine.analyticAccounts)) : [];

            let acctRecord = false;
            let cleanId = parseInt(detail.account_id, 10);
            if (cleanId) {
                try {
                    const records = await this.orm.searchRead(
                        "account.account",
                        [["id", "=", cleanId]],
                        ["id", "display_name"]
                    );
                    if (records && records.length) {
                        acctRecord = [records[0].id, records[0].display_name];
                    }
                } catch (e) {
                    console.error("Error buscando cuenta:", e);
                }
            }

            newFormattedData.push({
                ...modelLine,
                id: this.nextId++,
                analyticAccounts: analyticAccountsParams,
                percentage: detail.percentage / 100.0,
                account_account_id: acctRecord || false
            });
        }

        this.state.formattedData = newFormattedData;
    },

    recordProps(line) {
        const parentProps = super.recordProps(line);

        parentProps.fields["account_account_id"] = {
            string: _t("Account"),
            type: "many2one",
            relation: "account.account",
            domain: [["active", "!=", false]],
        };

        parentProps.values["account_account_id"] = line.account_account_id || false;
        return parentProps;
    },

    async lineChanged(record, changes, line) {
        await super.lineChanged(record, changes, line);

        if ("account_account_id" in changes) {
            line.account_account_id = changes.account_account_id;
        }
    },

    dataToJson() {
        // Devolvemos el diccionario ESTANDAR a Odoo (flotantes puros)
        const result = super.dataToJson();

        // Antes de que esto se envíe al backend, nos aseguramos que save() o onChange
        // también guarde el campo accounts, pero aqui solo retornamos lo estándar para analytic_distribution
        return result;
    },

    calculateAccountsMapping() {
        // Ahora guardaremos un array de objetos con los detalles de cada línea (incluidos los repetidos)
        const detailedDistribution = [];
        for (const line of this.state.formattedData) {
            const key = line.analyticAccounts.reduce((p, n) => p.concat(n.accountId ? n.accountId : []), []).join(",");
            if (key) {
                let acctId = false;
                if (line.account_account_id) {
                    acctId = Array.isArray(line.account_account_id) ? line.account_account_id[0] : line.account_account_id;
                }

                // Podemos guardar más campos (ej. categoria_id) aquí
                detailedDistribution.push({
                    analytic_account_ids: key,
                    percentage: line.percentage * 100,
                    account_id: acctId || false
                });
            }
        }
        return JSON.stringify(detailedDistribution);
    },

    addLine() {
        super.addLine();
        const line = this.state.formattedData[this.state.formattedData.length - 1];
        if (line) {
            line.account_account_id = false;
        }
    },

    // Sobreescribimos save para hacer la actualizacion de forma unificada sin onchanges dobles
    async save() {
        const updates = { [this.props.name]: this.dataToJson() };
        if (this.props.record && "analytic_distribution_accounts" in this.props.record.data) {
            updates.analytic_distribution_accounts = this.calculateAccountsMapping();
        }
        await this.props.record.update(updates);

        if (this.props.multi_edit) {
            await this.jsonToData(this.props.record.data[this.props.name]);
            this.initialFormattedData = this.state.formattedData;
            this.state.formattedData = [];
            this.state.update_plan = {};
        }
    }
});
