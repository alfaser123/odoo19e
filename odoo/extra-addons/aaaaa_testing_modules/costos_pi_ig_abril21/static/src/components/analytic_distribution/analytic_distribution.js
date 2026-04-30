/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AnalyticDistribution } from "@analytic/components/analytic_distribution/analytic_distribution";

patch(AnalyticDistribution.prototype, {
    
    async jsonToData(jsonFieldValue) {
        // En Odoo estándar, jsonFieldValue es solo un diccionario de floats { account_ids: percentage }
        await super.jsonToData(jsonFieldValue);
        
        // Leemos nuestro campo paralelo desde el registro
        let ourAccounts = {};
        if (this.props.record && this.props.record.data.analytic_distribution_accounts) {
            ourAccounts = this.props.record.data.analytic_distribution_accounts || {};
            if (typeof ourAccounts === "string") {
                try {
                    ourAccounts = JSON.parse(ourAccounts);
                } catch(e) {
                    ourAccounts = {};
                }
            }
        }
        
        for (const line of this.state.formattedData) {
            const key = line.analyticAccounts.reduce((p, n) => p.concat(n.accountId ? n.accountId : []), []).join(",");
            let acctRecord = false;
            
            if (ourAccounts[key]) {
                let rawId = ourAccounts[key];
                let cleanId = Array.isArray(rawId) ? rawId[0] : (typeof rawId === "object" && rawId !== null ? rawId.id : rawId);
                cleanId = parseInt(cleanId, 10);
                
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
            }
            line.account_account_id = acctRecord || false;
        }
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
            line.account_account_id = record.data.account_account_id;
            
            // Actualizamos en vivo el campo paralelo del registro
            if (this.props.record && "analytic_distribution_accounts" in this.props.record.data) {
                const accountsMapping = this.calculateAccountsMapping();
                await this.props.record.update({ analytic_distribution_accounts: accountsMapping });
            }
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
        // Lee `state.formattedData` y actualiza el campo paralelo
        const mapping = {};
        for (const line of this.state.formattedData) {
            const key = line.analyticAccounts.reduce((p, n) => p.concat(n.accountId ? n.accountId : []), []).join(",");
            if (key) {
                let acctId = false;
                if (line.account_account_id) {
                    acctId = Array.isArray(line.account_account_id) ? line.account_account_id[0] : line.account_account_id;
                }
                if (acctId) {
                    mapping[key] = acctId;
                }
            }
        }
        return mapping;
    },

    addLine() {
        super.addLine();
        const line = this.state.formattedData[this.state.formattedData.length - 1];
        if (line) {
            line.account_account_id = false;
        }
    },

    // Sobreescribimos save si hace falta forzar update del modelo
    async save() {
        if (this.props.record && "analytic_distribution_accounts" in this.props.record.data) {
            const accountsMapping = this.calculateAccountsMapping();
            await this.props.record.update({ analytic_distribution_accounts: accountsMapping });
        }
        return super.save();
    }
});
