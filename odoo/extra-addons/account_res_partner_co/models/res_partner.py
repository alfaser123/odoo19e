# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree
from odoo.addons.l10n_co_dian import xml_utils
import re
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

class ResPartnerExtended(models.Model):
    _inherit = 'res.partner'

   
    # num_id = fields.Char(string='Numero ID')
    firstname = fields.Char(string='Primer nombre')
    middlename = fields.Char(string='Segundo nombre')
    lastname = fields.Char(string='Primer apellido')
    othername = fields.Char(string='Segundo apellido')
    nit = fields.Char(string='NIT')
    dv = fields.Char(string='DV')
    
    name_dian = fields.Char(string='Nombre en DIAN',  help="nombre reportado por DIAN , la consulta debe ser consecuente con el numero y tipo de Documento")
    email_dian = fields.Char(string='Email en DIAN' , help="nombre reportado por DIAN , la consulta debe ser consecuente con el numero y tipo de Documento")
    
    
    """datos de consulta individual en aportes"""
    apor_num_afil_ppal =  fields.Char(string='ID Afiliado',  help="Numero ID del afiliado principal")
    apor_categorias_id =  fields.Char(string='Categoria Subsidio',  help="Categoria Subsidio desde la ultima consulta")
    apor_is_benefic = fields.Boolean(string='Es beneficiario')
    apor_relation_withafil =  fields.Char(string='Parentesco con Afiliado',  help="Parentesco con Afiliado")   
    apor_firstname_aportes = fields.Char(string='Primer Nombre',  help=" Primer nombre registrado en aportes")
    apor_middlename = fields.Char(string='Segundo nombre',  help=" Segundo nombre registrado en aportes")
    apor_lastname = fields.Char(string='Primer apellido',  help=" Primer apellido registrado en aportes")
    apor_othername = fields.Char(string='Segundo apellido',  help=" Segundo apellido registrado en aportes ")
    # apor_type_doc =  fields.Char(string='Tipo Documento')
    apor_type_doc =  fields.Many2one('l10n_latam.identification.type' , string='Tipo Documento')
    apor_email = fields.Char(string='Email'  , help="nombre reportado por DIAN , la consulta debe ser consecuente con el nu'mero y tipo de Documento")
    apor_address =  fields.Char(string='Direccion')
    apor_phone =   fields.Char(string='Telefono')
    last_date_report = fields.Datetime(string='Ultima actualizacion en Odoo',  help=" Fecha de la u'ltima descarga de datos que se realiz'o para odoo")
    


    @api.constrains('ref')  # o 'num_id' según tu campo
    def _check_num_id_only_numbers(self):
        for record in self:
            if record.ref and not re.match(r'^\d+$', record.ref):
                raise ValidationError("El campo Num_id solo acepta números. No se permiten símbolos ni letras, coloque el Número de ID sin dígito de verificación")    
    
 
    # type_ref = fields.Many2one('res.reference.type', string='Tipo de referencia', required=True)
    #city = fields.Many2one('res.city', string='Ciudad', required=True, oldname='city')
    # city_id = fields.Many2one('res.city', string='Ciudad', required=False)
 

    """reemplazamos origen /usr/lib/python3/dist-packages/odoo/addons/l10n_co_dian"""
    @api.model
    def _l10n_co_dian_call_get_acquirer(self, data: dict):
        if not self.env.ref('l10n_co_dian.get_acquirer', raise_if_not_found=False):
            # Could happen when the user did not update their db
            return dict()

        response = xml_utils._build_and_send_request(
            self,
            payload={
                'identification_type': data['identification_type'],
                'identification_number': data['identification_number'],
                'soap_body_template': "l10n_co_dian.get_acquirer",
            },
            service='GetAcquirer',
            company=data['company'],
        )
        # _logger.info("_l10n_co_dian_call_get_acquirer  %s", response)
        if response['status_code'] != 200:
            return dict()

        root = etree.fromstring(response['response'])
        # return {
            # 'email': root.findtext('.//{*}ReceiverEmail'),
            # 'name': root.findtext('.//{*}ReceiverName'),
        # }
        return {
            'email_dian': root.findtext('.//{*}ReceiverEmail'),
            'name_dian': root.findtext('.//{*}ReceiverName'),
        }


    def button_insert_from_aportes_data(self):
        self._aportes_insert_data(self.env.company)





    def button_aportes_refresh_data(self):
        # self.apor_firstname_aportes =  None
        self._aportes_update_data(self.env.company)



    def insert_def (self):
        
        insrt =''' insert into res_partner
                    (
                    Name,
                    Active,
                    Street ,
                    Supplier,
                    display_Name ,
                    country_id,
                    parent_id,
                    employee,
                    ref,
                    Email,
                    is_company,
                    lang,
                    phone,
                    write_date,
                    tz,
                    write_uid,
                    customer,
                    create_uid,
                    Mobile,
                    type,
                    partner_share,
                    state_id,
                    notify_email,
                    opt_out,
                    message_bounce,
                    invoice_warn,
                    sale_warn,
                    dv,
                    othername,
                    middlename,
                    type_ref,
                    city_id,
                    firstname,
                    lastname,
                    nit,
                    categorias_id,
                    company_id,
                    color,
                    Title,
                    credit_limit,
                    date,
                    user_id,
                    picking_warn,
                    num_id,
                    fe_fiscal_regimen,
                    fe_fiscal_resp,
                    fe_organization_type,
                    purchase_warn,
                    comment
                    )
                            '''
        return insrt


    def _aportes_update_data(self, company):
        
        
        
        # ***************************************
        # ***************************************
        # ***************************************
        # extrae informacion del principal   
        # ***************************************
        # ***************************************
        # ***************************************        
                
        
        
        if self.ref:
            sql = """
                SELECT
                    '[' || a.cedtra || '] ' ||
                    COALESCE(a.prinom, '') || ' ' ||
                    COALESCE(a.segnom, '') || ' ' ||
                    COALESCE(a.priape, '') || ' ' ||
                    COALESCE(a.segape, '') AS afiliado_name,

                    true AS active,
                    COALESCE(a.direccion, '') AS street,
                    false AS supplier,

                    '[' || a.cedtra || '] ' ||
                    COALESCE(a.prinom, '') || ' ' ||
                    COALESCE(a.segnom, '') || ' ' ||
                    COALESCE(a.priape, '') || ' ' ||
                    COALESCE(a.segape, '') AS display_name,

                    50 AS country_id,
                    0 AS parent_id,
                    false AS employee,
                    a.cedtra AS ref,
                    COALESCE(a.email, 'a@a') AS email,
                    false AS is_company,
                    'es_CO' AS lang,

                    CASE
                        WHEN length(a.telefono) = 10 THEN '0'
                        WHEN a.telefono IS NULL THEN '0'
                        ELSE a.telefono
                    END AS phone,

                    current_date AS write_date,
                    'America/Bogota' AS tz,
                    5 AS write_uid,
                    true AS customer,
                    5 AS create_uid,

                    CASE
                        WHEN length(a.telefono) = 10 THEN a.telefono
                        ELSE '0'
                    END AS mobile,

                    'contact' AS type,
                    false AS partner_share,
                    substr(b.id_dpto, 30, 100) AS state_id,
                    'always' AS notify_email,
                    false AS opt_out,
                    0 AS message_bounce,
                    'no-message' AS invoice_warn,
                    'no-message' AS sale_warn,
                    NULL AS dv,

                    COALESCE(a.segape, '') AS othername,
                    COALESCE(a.segnom, '') AS middlename,

                    CASE a.coddoc
                        WHEN '1' THEN '2'
                        WHEN '2' THEN '4'
                        WHEN '3' THEN '1'
                        WHEN '4' THEN '3'
                        WHEN '5' THEN '5'
                        WHEN '6' THEN '7'
                        WHEN '7' THEN '8'
                        WHEN '8' THEN '8'
                        WHEN '9' THEN '6'
                    END AS type_ref,

                    substr(b.id_ciudad, 21, 100) AS city_id,
                    COALESCE(a.prinom, '') AS firstname,
                    COALESCE(a.priape, '') AS lastname,
                    COALESCE(a.cedtra, '0') AS nit,
                    c.id AS categorias_id,
                    1 AS company_id,
                    0 AS color,
                    3 AS title,
                    1000000 AS credit_limit,
                    current_date AS date,
                    1 AS user_id,
                    'no-message' AS picking_warn,
                    '' AS comment,
                    'Afiliado' AS relationship,
                    0 AS is_benefic

                FROM mysql_aportes.subsi15 a
                JOIN mysql_aportes.odoo_ciudades b
                    ON b.cd_ciudad = substring(a.codzon from length(a.codzon) - 2 for 3)
                   AND b.cd_dpto   = substring(a.codzon from 1 for 2)
                JOIN mysql_aportes.odoo_subsidio_categorias c
                    ON c.name = a.codcat
                WHERE (a.estado <> 'M' OR a.estado = 'A')
                  AND a.cedtra = %s::text
            """
            self.env.cr.execute(sql, (self.ref,))

            res_mysql =  self.env.cr.dictfetchall()

            _logger.info("principal  %s  %s", res_mysql, len(res_mysql))        



        
        # ***************************************
        # ***************************************
        # ***************************************
        # extrae informacion de LA EMPRESA
        # ***************************************
        # ***************************************
        # ***************************************        
        
        
        if self.ref:
            sql = """                
                     
                  SELECT
                    '[' || a.nit || '] ' || a.razsoc AS name,
                    CASE WHEN a.estado = 'A' THEN true ELSE true END AS active,
                    COALESCE(a.direccion, '') AS street,
                    false AS supplier,
                    '[' || a.nit || '] ' || a.razsoc AS display_name,
                    50 AS country_id,
                    0 AS parent_id,
                    false AS employee,
                    a.nit AS ref,
                    COALESCE(a.email, 'a@a') AS email,
                    true AS is_company,
                    'es_CO' AS lang,
                    CASE
                        WHEN length(a.telefono) = 10 THEN '0'
                        WHEN a.telefono IS NULL THEN '0'
                        ELSE a.telefono
                    END AS phone,
                    current_date AS write_date,
                    'America/Bogota' AS tz,
                    5 AS write_uid,
                    true AS customer,
                    5 AS create_uid,
                    CASE
                        WHEN length(a.telefono) = 10 THEN a.telefono
                        ELSE '0'
                    END AS mobile,
                    'contact' AS type,
                    false AS partner_share,
                    substring(b.id_dpto from 30 for 100) AS state_id,
                    'always' AS notify_email,
                    false AS opt_out,
                    0 AS message_bounce,
                    'no-message' AS invoice_warn,
                    'no-message' AS sale_warn,
                    NULL AS dv,
                    '' AS othername,
                    '' AS middlename,
               /*     
                    CASE a.coddoc
                        WHEN '1' THEN '2'
                        WHEN '2' THEN '4'
                        WHEN '3' THEN '1'
                        WHEN '4' THEN '3'
                        WHEN '5' THEN '5'
                        WHEN '6' THEN '7'
                        WHEN '7' THEN '8'
                        WHEN '8' THEN '8'
                        WHEN '9' THEN '6'
                    END AS type_ref,
                 */  
                    latam.id  as type_ref,
                    
                    substring(b.id_ciudad from 21 for 100) AS city,
                    a.razsoc AS firstname,
                    '' AS lastname,
                    COALESCE(a.nit, '0') AS nit,
                    4 AS categorias_id,
                    1 AS company_id,
                    0 AS color,
                    3 AS title,
                    1000000 AS credit_limit,
                    current_date AS date,
                    1 AS user_id,
                    'no-message' AS picking_warn,
                    'Empresa Aportante' AS relationship,
                    0 AS is_benefic,
                    NULL AS afiliado_name
                FROM view_subsi02 a
                JOIN mysql_aportes.odoo_ciudades b
                    ON b.cd_ciudad = right(a.codzon, 3)
                   AND b.cd_dpto = left(a.codzon, 2)
                JOIN view_subsi54 c
                    ON a.tipsoc = c.tipsoc
                    
                left join l10n_latam_identification_type latam on latam.mysql_data_id= a.coddoc::integer 
                    
                WHERE a.nit NOT IN (
                    SELECT cedtra
                    FROM view_subsi15
                )
                AND a.nit = %s::text
            """
            self.env.cr.execute(sql, (self.ref,))

            res_mysql =  self.env.cr.dictfetchall()

            _logger.info("empressa  %s  %s", res_mysql, len(res_mysql))        

 
        # ***************************************
        # ***************************************
        # ***************************************
        # extrae informacion de conyugue   subsi15 tiene la relacion codtra, codcon por cada mes y subsi09 la info de la codcon
        # ***************************************
        # ***************************************
        # ***************************************        
                
        
        # self.ensure_one()
        if self.ref and len(res_mysql) == 0 :
            _logger.info("entra a select  conyugue  %s %s  %s", self.ref,  res_mysql, len(res_mysql))        
            sql = '''   SELECT
                            concat(
                                '[',
                                a.cedcon,
                                '] ',
                                coalesce(a.prinom,''),
                                ' ',
                                coalesce(a.segnom,''),
                                ' ',
                                coalesce(a.priape,''),
                                ' ',
                                coalesce(a.segape,'')
                            ) AS name,

                            true  AS active,
                            coalesce(a.direccion,'') AS street,
                            false AS supplier,

                            concat(
                                '[',
                                a.cedcon,
                                '] ',
                                coalesce(a.prinom,''),
                                ' ',
                                coalesce(a.segnom,''),
                                ' ',
                                coalesce(a.priape,''),
                                ' ',
                                coalesce(a.segape,'')
                            ) AS display_name,

                            50  AS country_id,
                            null   AS parent_id,
                            false AS employee,
                            a.cedcon AS ref,
                            coalesce(a.email,'') AS email,
                            false AS is_company,
                            'es_CO' AS lang,

                            CASE
                                WHEN length(a.telefono) = 10 THEN '0'
                                WHEN a.telefono IS NULL THEN '0'
                                ELSE a.telefono
                            END AS phone,

                            now() AS write_date,
                            'America/Bogota' AS tz,
                            1 AS write_uid,
                            true AS customer,
                            1 AS create_uid,

                            CASE
                                WHEN length(a.telefono) = 10 THEN a.telefono
                                ELSE '0'
                            END AS mobile,

                            'contact' AS type,
                            false AS partner_share,
                            
                            CASE WHEN length(b.id_dpto)>1
                                then substring(b.id_dpto,30,10)::int  
                                else 85
                            END AS state_id,
                            'always'    AS notify_email,
                            false       AS opt_out,
                            0           AS message_bounce,
                            'no-message' AS invoice_warn,
                            'no-message' AS sale_warn,
                            null AS dv,

                            coalesce(a.segape,'') AS othername,
                            coalesce(a.segnom,'') AS middlename,
                        /*
                            CASE a.coddoc
                                WHEN '1' THEN '2'
                                WHEN '2' THEN '4'
                                WHEN '3' THEN '5'
                                WHEN '4' THEN '3'
                                WHEN '5' THEN '8'
                                WHEN '6' THEN '6'
                                WHEN '7' THEN '1'
                                WHEN '8' THEN '7'
                                WHEN '9' THEN '10'
                            END::INTEGER  AS type_ref,   
                        */                       
                        latam.id  as type_ref,
                    
                             
                             
                             
                            CASE WHEN length(b.id_ciudad)>1
                                then  substring(b.id_ciudad,21,10)::int  
                                else 2174
                            END AS  city_id,	 
                             
                            coalesce(a.prinom,'') AS firstname,
                            coalesce(a.priape,'') AS lastname,
                            coalesce(a.cedcon,'0') AS nit,

                            c.id AS categorias_id,
                            1 AS company_id,
                            0 AS color,
                            3 AS title,
                            1000000 AS credit_limit,
                            current_date AS date,
                            1 AS user_id,
                            'no-message' AS picking_warn,
                        a.cedcon,
                        '49' as fe_fiscal_regimen,
                        5 as fe_fiscal_resp,
                        2  as fe_organization_type,
                        '\no-message\' as purchase_warn,
                       -- s9.cedtra,
                        concat(
                                '[',
                                s15.cedtra,
                                '] ',
                                coalesce(s15.prinom,''),
                                ' ',
                                coalesce(s15.segnom,''),
                                ' ',
                                coalesce(s15.priape,''),
                                ' ',
                                coalesce(s15.segape,'')
                            ) AS afiliado_name,
                        'Conyugue' as relationship,
                        '1' as is_benefic


                        FROM ( SELECT msqs.*
                           FROM 
                            view_subsi20 msqs 
                            WHERE msqs.cedcon IS NOT NULL
                            and msqs.cedcon = %s::text 
                        ) a

                        JOIN mysql_aportes.odoo_ciudades b
                          ON b.cd_ciudad = right(a.codzon, 3)
                         AND b.cd_dpto   = substring(a.codzon from 1 for 2)
                        JOIN mysql_aportes.odoo_subsidio_categorias c
                          ON c.name = a.codcat
                        JOIN mysql_aportes.subsi09 s9 on s9.cedcon = a.cedcon
                        
                        JOIN mysql_aportes.subsi15 s15 ON s15.cedtra=s9.cedtra
                        
                        left join l10n_latam_identification_type latam on latam.mysql_data_id= a.coddoc::integer 
                        
                        order by s9.periodo desc limit 1
                          '''%(self.ref)

            self.env.cr.execute(sql)
            res_mysql =  self.env.cr.dictfetchall()


 # [{'name': '[1000768359] SANDRA MILENA ALZATE ZABALA', 'active': True, 'street': 'CR  6  8B  46 VILLA ESTER', 'supplier': False, 'display_name': '[1000768359] SANDRA MILENA ALZATE ZABALA', 'country_id': 50, 'parent_id': None, 'employee': False, 'ref': '1000768359', 'email': '', 'is_company': False, 'lang': 'es_CO', 'phone': '0', 'write_date': datetime.datetime(2026, 4, 16, 0, 40, 12, 944229, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=68400))), 'tz': 'America/Bogota', 'write_uid': 1, 'customer': True, 'create_uid': 1, 'mobile': '0', 'type': 'contact', 'partner_share': False, 'state_id': 110, 'notify_email': 'always', 'opt_out': False, 'message_bounce': 0, 'invoice_warn': 'no-message', 'sale_warn': 'no-message', 'dv': 6, 'othername': 'ZABALA', 'middlename': 'MILENA', 'type_ref': 2, 'city_id': 2190, 'firstname': 'SANDRA', 'lastname': 'ALZATE', 'nit': '1000768359', 'categorias_id': 3, 'company_id': 1, 'color': 0, 'title': 3, 'credit_limit': 1000000, 'date': datetime.date(2026, 4, 16), 'user_id': 1, 'picking_warn': 'no-message', 'cedcon': '1000768359', 'fe_fiscal_regimen': '49', 'fe_fiscal_resp': 5, 'fe_organization_type': 2, 'purchase_warn': '\no-message'}]
             
            _logger.info("conyugue  %s  %s", res_mysql, len(res_mysql))

 
     
 
 
 
        # ***************************************
        # ***************************************
        # ***************************************
        # extrae informacion de hijos detectados
        # ***************************************
        # ***************************************
        # ***************************************

        

        if self.ref and len(res_mysql) == 0 :
            
 
            sql = ''' 
                    SELECT
                        concat(
                            '[',
                            a.cedtra,
                            '] ',
                            coalesce(a.prinom,''),
                            ' ',
                            coalesce(a.segnom,''),
                            ' ',
                            coalesce(a.priape,''),
                            ' ',
                            coalesce(a.segape,'')
                        ) AS name,

                        true  AS active,
                        coalesce(a.direccion,'') AS street,
                        false AS supplier,

                        concat(
                            '[',
                            a.cedtra,
                            '] ',
                            coalesce(a.prinom,''),
                            ' ',
                            coalesce(a.segnom,''),
                            ' ',
                            coalesce(a.priape,''),
                            ' ',
                            coalesce(a.segape,'')
                        ) AS display_name,

                        50  AS country_id,
                        null   AS parent_id,
                        false AS employee,
                        a.cedtra AS ref,
                        coalesce(a.email,'') AS email,
                        false AS is_company,
                        'es_CO' AS lang,

                        CASE
                            WHEN length(a.telefono) = 10 THEN '0'
                            WHEN a.telefono IS NULL THEN '0'
                            ELSE a.telefono
                        END AS phone,

                        now() AS write_date,
                        'America/Bogota' AS tz,
                        1 AS write_uid,
                        true AS customer,
                        1 AS create_uid,

                        CASE
                            WHEN length(a.telefono) = 10 THEN a.telefono
                            ELSE '0'
                        END AS mobile,

                        'contact' AS type,
                        false AS partner_share,
                        
                        CASE WHEN length(b.id_dpto)>1
                            then substring(b.id_dpto,30,10)::int  
                            else 85
                        END AS state_id,
                        'always'    AS notify_email,
                        false       AS opt_out,
                        0           AS message_bounce,
                        'no-message' AS invoice_warn,
                        'no-message' AS sale_warn,
                            null  AS dv,

                        coalesce(a.segape,'') AS othername,
                        coalesce(a.segnom,'') AS middlename,
/*
                        CASE a.coddoc
                       ---tabla  gener18 de mysql
                            
                            WHEN '1'
                                    THEN '2'
                            WHEN '2'
                                    THEN '4'
                            WHEN '3'
                                    THEN '1'
                            WHEN '4'
                                    THEN '3'
                        WHEN '5'
                                    THEN '5'
                            WHEN '6'
                                    THEN '7'
                            WHEN '7'
                                    THEN '8'
                            when '8'
                                    THEN '8'
                        when '9'
                                    THEN '6'		
                        END::INTEGER  AS   type_ref,
 */                       
                        latam.id  as type_ref,

                         
                        CASE WHEN length(b.id_ciudad)>1
                            then  substring(b.id_ciudad,21,10)::int  
                            else 2174
                        END AS  city_id,	 
                         
                        coalesce(a.prinom,'') AS firstname,
                        coalesce(a.priape,'') AS lastname,
                        coalesce(a.cedtra,'0') AS nit,

                        c.id AS categorias_id,
                        1 AS company_id,
                        0 AS color,
                        3 AS title,
                        1000000 AS credit_limit,
                        current_date AS date,
                        1 AS user_id,
                        'no-message' AS picking_warn,
                    a.cedtra as num_id,
                    '49' as fe_fiscal_regimen,
                    5 as fe_fiscal_resp,
                    2  as fe_organization_type,
                    '\no-message\' as purchase_warn,
                    'Beneficiario / Cuota Monetaria' as comment,
                    concat(
                                '[',
                                vs15.cedtra,
                                '] ',
                                coalesce(vs15.prinom,''),
                                ' ',
                                coalesce(vs15.segnom,''),
                                ' ',
                                coalesce(vs15.priape,''),
                                ' ',
                                coalesce(vs15.segape,'')
                            ) AS afiliado_name,
                'Conyugue' as relationship,
                '1' as is_benefic


                    FROM (select 
                                s15.nit, s15.codsuc, s15.codlis,z.codben,s15.fecexp,z.coddoc, z.priape,z.segape,z.prinom,z.segnom, s15.direccion,
                                s15.codciu,s15.codpai, s15.celular,s15.telefono,s15.email,s15.codzon,s15.agro,s15.captra,s15.tipdis,s15.horas,s15.salario,s15.codpro,
                                s15.fecadd,s15.fecmod,  s15.codcat, s15.cedtra
   
                            from  	
                            (
                                 select * from 
                                (select *, ROW_NUMBER() OVER (PARTITION BY codben,  codafil  ORDER BY codben,  codafil) AS contador  from view_subsi90 ) x  where contador=1
                                    and codben = %s::text  
                            ) z
                            
                            inner join  view_subsi15   s15
                            on s15.cedtra =  z.codafil 
                            and s15.nit is not null 		
                        ) a
                    JOIN mysql_aportes.odoo_ciudades b
                      ON b.cd_ciudad = right(a.codzon, 3)
                     AND b.cd_dpto   = substring(a.codzon from 1 for 2)
                    JOIN mysql_aportes.odoo_subsidio_categorias c
                      ON c.name = a.codcat
                     
                    JOIN view_subsi15 vs15 ON vs15.cedtra = a.cedtra
                    left join l10n_latam_identification_type latam on latam.mysql_data_id= a.coddoc::integer


                     
                          '''%(self.ref)

            self.env.cr.execute(sql)
            res_mysql =  self.env.cr.dictfetchall()

            _logger.info("hijos  %s  %s", res_mysql, len(res_mysql))
            

            
            # if len(res_mysql): 
                # _logger.info("  hijo conyugue name   %s", res_mysql[0]['name'])
                # self.apor_num_afil_ppal = res_mysql[0]['afiliado_name']
                # self.apor_categorias_id = res_mysql[0]['categorias_id']
                # self.apor_is_benefic = '1'
                # self.apor_relation_withafil = 'Hijos'
                # self.apor_firstname_aportes = res_mysql[0]['firstname']
                # self.apor_middlename = res_mysql[0]['middlename']
                # self.apor_lastname = res_mysql[0]['lastname']
                # self.apor_othername = res_mysql[0]['othername']
                # self.apor_type_doc = res_mysql[0]['type_ref']
                # self.apor_email = res_mysql[0]['email']
                # self.apor_address = res_mysql[0]['street']
                # self.apor_phone = res_mysql[0]['mobile']
                # self.last_date_report = datetime.now()



        # ***************************************
        # ***************************************
        # ***************************************
        # extrae informacion de otro responsable de subsidio  no hijos no conyugue
        # ***************************************
        # ***************************************
        # ***************************************

        if self.ref and len(res_mysql) == 0 :
            sql = '''
                            
                            

                SELECT
                    concat(
                        '[',
                        a.cedtra,
                        '] ',
                        coalesce(a.prinom,''),
                        ' ',
                        coalesce(a.segnom,''),
                        ' ',
                        coalesce(a.priape,''),
                        ' ',
                        coalesce(a.segape,'')
                    ) AS name,

                    true  AS active,
                    coalesce(a.direccion,'') AS street,
                    false AS supplier,

                    concat(
                        '[',
                        a.cedtra,
                        '] ',
                        coalesce(a.prinom,''),
                        ' ',
                        coalesce(a.segnom,''),
                        ' ',
                        coalesce(a.priape,''),
                        ' ',
                        coalesce(a.segape,'')
                    ) AS display_name,

                    50  AS country_id,
                    null   AS parent_id,
                    false AS employee,
                    a.cedtra AS ref,
                    coalesce(a.email,'') AS email,
                    false AS is_company,
                    'es_CO' AS lang,

                    CASE
                        WHEN length(a.telefono) = 10 THEN '0'
                        WHEN a.telefono IS NULL THEN '0'
                        ELSE a.telefono
                    END AS phone,

                    now() AS write_date,
                    'America/Bogota' AS tz,
                    1 AS write_uid,
                    true AS customer,
                    1 AS create_uid,

                    CASE
                        WHEN length(a.telefono) = 10 THEN a.telefono
                        ELSE '0'
                    END AS mobile,

                    'contact' AS type,
                    false AS partner_share,
                    
                    CASE WHEN length(b.id_dpto)>1
                        then substring(b.id_dpto,30,10)::int  
                        else 85
                    END AS state_id,
                    'always'    AS notify_email,
                    false       AS opt_out,
                    0           AS message_bounce,
                    'no-message' AS invoice_warn,
                    'no-message' AS sale_warn,
                    null AS dv,

                    coalesce(a.segape,'') AS othername,
                    coalesce(a.segnom,'') AS middlename,

                    CASE a.coddoc
                   ---tabla  gener18 de mysql
                        
                        WHEN '1'
                                THEN '2'
                        WHEN '2'
                                THEN '4'
                        WHEN '3'
                                THEN '1'
                        WHEN '4'
                                THEN '3'
                    WHEN '5'
                                THEN '5'
                        WHEN '6'
                                THEN '7'
                        WHEN '7'
                                THEN '8'
                        when '8'
                                THEN '8'
                    when '9'
                                THEN '6'		
                    END::INTEGER  AS type_ref,

                     
                    CASE WHEN length(b.id_ciudad)>1
                        then  substring(b.id_ciudad,21,10)::int  
                        else 2174
                    END AS  city_id,	 
                     
                    coalesce(a.prinom,'') AS firstname,
                    coalesce(a.priape,'') AS lastname,
                    coalesce(a.cedtra,'0') AS nit,

                    c.id AS categorias_id,
                    1 AS company_id,
                    0 AS color,
                    3 AS title,
                    1000000 AS credit_limit,
                    current_date AS date,
                    1 AS user_id,
                    'no-message' AS picking_warn,
                a.cedtra as num_id,
                '49' as fe_fiscal_regimen,
                5 as fe_fiscal_resp,
                2  as fe_organization_type,
                '\no-message\' as purchase_warn,
                'Beneficiario / Cuota Monetaria' AS comment,
                 concat(
                                '[',
                                vs15.cedtra,
                                '] ',
                                coalesce(vs15.prinom,''),
                                ' ',
                                coalesce(vs15.segnom,''),
                                ' ',
                                coalesce(vs15.priape,''),
                                ' ',
                                coalesce(vs15.segape,'')
                ) AS afiliado_name,
                'Responsable , No es Conyugue/No es hijo' as relationship,
                '1' as is_benefic
                


                FROM (
                        select 
                            s15.nit, s15.codsuc, s15.codlis, 
                            z.cedres,
                            s15.fecexp,
                            s15.coddoc,
                            z.priape,z.segape,z.prinom,z.segnom, z.cedtra,
                    
                            s15.direccion,
                            s15.codciu,s15.codpai, s15.celular,s15.telefono,s15.email,s15.codzon,s15.agro,s15.captra,s15.tipdis,s15.horas,s15.salario,s15.codpro,
                            s15.fecadd,s15.fecmod,s15.codcat

                            from  (	select distinct v.cedres,v.cedtra,v.priape,v.segape,v.prinom,v.segnom from 

                                    (select * from 
                                    (select *, ROW_NUMBER() OVER (PARTITION BY cedres  ORDER BY  cedtra,cedres   desc ) AS contador  from mysql_aportes.subsi18  ) x  where contador=1
                                     and cedres = %s::text  
                                    ) as v 

                            ) z  
                            left join view_subsi15 s15
                            on s15.cedtra =  z.cedtra
                            and s15.nit is not null 
                            where z.cedres is not null

                ) a
                JOIN mysql_aportes.odoo_ciudades b
                  ON b.cd_ciudad = right(a.codzon, 3)
                 AND b.cd_dpto   = substring(a.codzon from 1 for 2)
                JOIN mysql_aportes.odoo_subsidio_categorias c
                  ON c.name = a.codcat
       
                JOIN view_subsi15 vs15 ON vs15.cedtra = a.cedtra
                '''%(self.ref)

            self.env.cr.execute(sql)
            res_mysql =  self.env.cr.dictfetchall()

            _logger.info("  responsable   %s  %s", res_mysql, len(res_mysql))
            

       

            
        if len(res_mysql)>0: 
            
            _logger.info("partner name   %s", res_mysql[0]['afiliado_name'])
            # self.apor_num_afil_ppal = res_mysql[0]['afiliado_name']
            # self.apor_categorias_id = res_mysql[0]['categorias_id']
            # self.apor_is_benefic = res_mysql[0]['is_benefic']
            # self.apor_relation_withafil = res_mysql[0]['relationship']
            # self.apor_firstname_aportes = res_mysql[0]['firstname']
            # self.apor_middlename = res_mysql[0]['middlename']
            # self.apor_lastname = res_mysql[0]['lastname']
            # self.apor_othername = res_mysql[0]['othername']
            # self.apor_type_doc = res_mysql[0]['type_ref']
            # self.apor_email = res_mysql[0]['email']
            # self.apor_address = res_mysql[0]['street']
            # self.apor_phone = res_mysql[0]['mobile']
            # self.last_date_report = datetime.now()
 
            vals = {
                'apor_num_afil_ppal': res_mysql[0]['afiliado_name'],
                'apor_categorias_id': res_mysql[0]['categorias_id'],
                'apor_is_benefic': res_mysql[0]['is_benefic'],
                'apor_relation_withafil': res_mysql[0]['relationship'],
                'apor_firstname_aportes': res_mysql[0]['firstname'],
                'apor_middlename': res_mysql[0]['middlename'],
                'apor_lastname': res_mysql[0]['lastname'],
                'apor_othername': res_mysql[0]['othername'],
                'apor_type_doc': res_mysql[0]['type_ref'],
                'apor_email': res_mysql[0]['email'],
                'apor_address': res_mysql[0]['street'],
                'apor_phone': res_mysql[0]['mobile'],
                'last_date_report': fields.Datetime.now(),
            }
            self.with_context(skip_validation=True).write(vals) 
            
            # self.with_context(skip_write_validation=True).write({
                # 'apor_num_afil_ppal ': res_mysql[0]['afiliado_name'],
                # 'apor_categorias_id ': res_mysql[0]['categorias_id'],
                # 'apor_is_benefic ': res_mysql[0]['is_benefic'],
                # 'apor_relation_withafil ': res_mysql[0]['relationship'],
                # 'apor_firstname_aportes ': res_mysql[0]['firstname'],
                # 'apor_middlename ': res_mysql[0]['middlename'],
                # 'apor_lastname ': res_mysql[0]['lastname'],
                # 'apor_othername ': res_mysql[0]['othername'],
                # 'apor_type_doc ': res_mysql[0]['type_ref'],
                # 'apor_email ': res_mysql[0]['email'],
                # 'apor_address ': res_mysql[0]['street'],
                # 'apor_phone ': res_mysql[0]['mobile'],
                # 'last_date_report ': datetime.now()
            # })
                    

        else:
                        

            vals = {
                    'apor_num_afil_ppal': '',
                    'apor_categorias_id': '',
                    'apor_is_benefic': '',
                    'apor_relation_withafil': '',
                    'apor_firstname_aportes': 'Sin datos en la busqueda',
                    'apor_middlename': '',
                    'apor_lastname': '',
                    'apor_othername': '',
                    'apor_type_doc': '',
                    'apor_email': '',
                    'apor_address': '',
                    'apor_phone': '',
                    'last_date_report': fields.Datetime.now(),
            }
            self.with_context(skip_validation=True).write(vals) 



 
    # @api.multi
    # @api.onchange('nit','num_id','firstname','middlename','lastname','othername')
    @api.onchange('ref','firstname','middlename','lastname','othername')
    def onchange_name(self):
        _logger.info("onchange_name  %s", self.firstname)
        # val={}

        # raise UserError(_(self.num_id))
        # for r in self:
                # newval = r
                # raise UserError(_(newval))
        # val['ref']= self.val()
        # newval = record[ref]
        # raise UserError(_(val['ref']))
        
        # self.ref = self.num_id
        # ref = self.ref or ''
        # nit = self.nit or ''
        name1 = self.firstname or ''
        name2 = self.middlename or ''
        name3 = self.lastname or ''
        name4 = self.othername or ''
        # self.name = '['+ nit + ref +'] ' + name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
        # self.commercial_company_name = '['+ nit + ref +'] ' + name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
        
        self.name =  name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
        self.complete_name =  name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
        _logger.info("complete_name  %s", self.complete_name)
        self.commercial_company_name =  name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
        _logger.info("commercial_company_name  %s",self.commercial_company_name)


    def procesar_nit(self, valor):
        limpio = re.sub(r'[^0-9-]', '', valor or '')
        
        if '-' in limpio:
            numero, dv = limpio.split('-', 1)
        else:
            numero = limpio
            dv = None
        
        return numero, dv


    def calcular_dv(self, nit):
        nit = str(nit)
        
        if not nit.isdigit():
            return False

        pesos = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        
        # Invertir el NIT para aplicar pesos desde la derecha
        nit_invertido = nit[::-1]

        total = 0
        for i in range(len(nit_invertido)):
            total += int(nit_invertido[i]) * pesos[i]

        residuo = total % 11
        dv = 11 - residuo

        if dv == 11:
            return 0
        elif dv == 10:
            return 1
        else:
            return dv


 
    @api.onchange('ref')
    def onchange_nit(self):
        
        # ref = self.num_id or ''
        
        # nit = self.nit or ''
        name1 = self.firstname or ''
        name2 = self.middlename or ''
        name3 = self.lastname or ''
        name4 = self.othername or ''
        # self.ref = self.num_id 
        # if self.ref:
        if self.ref  and self.ref.isdigit() :
            
            
            print ('self vat')
            numero, dv = self.procesar_nit(self.ref)
            print(numero, dv)        # self.ref = self.num_id

            self.dv = self.calcular_dv(self.ref)
 
            # self.name = '['+ nit + ref +'] ' + name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
            # self.commercial_company_name = '['+ nit + ref +'] ' + name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
            self.complete_name =  name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
            self.commercial_company_name =  name1 + ' ' + name2 + ' ' + name3 + ' ' + name4
            self.vat = numero+'-'+self.dv 
 

    def write(self, vals):
            _logger.info("write vals  %s",vals)
            for rec in self:
                # a = vals.get('is_company')
                # raise UserError( _("Valores recibidos: %s | is_company: %s   | Es compañía: %s   | Ref: %s  | ctxt:  %s" ) % (vals, a, self.is_company,  self.ref,  self.env.context))
              
                if 'ref'  and  (vals.get('is_company'))== True  and not  self.env.context.get('skip_validation'):  

                    required_fields = ['firstname']
                    
                    missing_fields = []

                    for field in required_fields:
                        value = vals.get(field, rec[field])
                        if not value:
                            missing_fields.append(rec._fields[field].string)

                    if missing_fields:
                        raise UserError(
                            _("Debe diligenciar los campos: %s") % ", ".join(missing_fields)
                        )

                
                elif 'ref'  and  (vals.get('is_company')) == False  and not self.env.context.get('skip_validation'):
                    required_fields = ['firstname', 'middlename', 'lastname']
                    
                    missing_fields = []

                    for field in required_fields:
                        value = vals.get(field, rec[field])
                        if not value:
                            missing_fields.append(rec._fields[field].string)

                    if missing_fields:
                        raise UserError(
                            _("Debe diligenciar los campos: %s") % ", ".join(missing_fields)
                        )

            # raise UserError( _("ctl"))
            res = super().write(vals) 
        
    # @api.multi
    # def onchange_city(self, city_id):
    
        # # parent_city_id = ''
        # if self.parent_id:
            # print('######################################################_logger.info city_id ')
            # if not city_id:
                    # city_id = self.parent_id.city_id 
            
        # if city_id:
            # _logger.info('city_id')
            # print('*************************************************************************************_logger.info city_id ')
            # _logger.info(city_id)
            # city = self.env['res.city'].browse(city_id)
            

            # return {'value': {'state_id': city.state_id.id,
                              # 'city': city.name,
                              # 'city_id': city_id
                              # }}
        # return {'value': {}}



# # #ver10comm
# # # class Bank(models.Model):
    # # # _inherit = 'res.bank'

    # # # city_id = fields.Many2one('res.city', string = 'City', ondelete='restrict')

    # # # @api.multi
    # # # def onchange_city(self, city_id):
        # # # if city_id:
            # # # city = self.env['res.city'].browse(city_id)
            # # # return {'value': {'state': city.state_id.id,
                              # # # 'city': city.name}}
        # # # return {'value': {}}

# # # class Company(models.Model):
    # # # _inherit = 'res.company'

    # # # city_id = fields.Many2one('res.city', string = 'City', ondelete='restrict')

    # # # @api.multi
    # # # def onchange_city(self, city_id):
        # # # if city_id:
            # # # city = self.env['res.city'].browse(city_id)
            # # # return {'value': {'state_id': city.state_id.id,
                              # # # 'city': city.name}}
        # # # return {'value': {}}

# # # class ResDocumentType(models.Model):
    # # # _name = 'res.reference.type'

    # # # code = fields.Char(string='Código letras')
    # # # codigo_DIAN = fields.Char(string='Código DIAN')
    # # # name = fields.Char(string='Nombre')
