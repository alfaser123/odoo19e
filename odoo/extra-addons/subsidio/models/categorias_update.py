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

from odoo import models, fields, api
from ftplib import FTP, error_perm
import csv
from odoo.exceptions import ValidationError
from datetime import datetime

class categorias_ftp_datos(models.Model):
    _name='categorias.ftp.datos'

    url = fields.Char(string='URL',required=True)
    port = fields.Char(string='Puerto',required=True,)
    user = fields.Char(string='Usuario',required=True)
    password = fields.Char(string='Clave',required=True)
    file = fields.Char(string='Archivo',required=True)
    timeout = fields.Char(string='Tiempo de espera',required=True)


class categorias_update(models.TransientModel):
    _name = "categorias.update"

    @api.multi
    def generar(self):
        try:
            datos = self.env['categorias.ftp.datos'].search([],limit=1)
            ftp = FTP()
            ftp.connect(datos.url,int(datos.port),int(datos.timeout))
            ftp.login(datos.user,datos.password)
            ftp.retrbinary('RETR '+datos.file,open('/tmp/'+datos.file,'wb').write)
            with open('/tmp/'+datos.file, 'rb') as f:
                reader = csv.reader(f)
                c = True
                for row in reader:
                    if c:
                        c=False
                        continue
                    line = list(row[0].split(';'))
                    ref =  line[8].replace('"','')
                    active=True
                    if line[0] != "1":
                        active =  False
                    categoria =line[len(line)-1].replace('"','')
                    if categoria != "":
                        self.env.cr.execute(" SELECT id FROM subsidio_categorias WHERE name = '%s' LIMIT 1"%str(categoria.replace('"','')))
                        id = self.env.cr.fetchone()
                        if id:
                            id = id[0]
			    print '---'
			    print id
			    print line[8].replace('"','')
                            self.env.cr.execute(" UPDATE res_partner set active = %s, categorias_id = %s where ref = '%s' "%(active,id,str(line[8].replace('"',''))))
            ftp.rename(datos.file, datos.file+str(datetime.now()))
            ftp.close()
        except error_perm, msg:
            raise ValidationError(msg)
        return True
