# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    John W. Viloria Amaris <john.viloria.amaris@gmail.com>
#    Christian Camilo Camargo <ccamargov20@gmail.com﻿>
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

{
    'name':'unlock expiration date 19e',
    'version': '19.0.1.1.0',
    'category': 'Accounting',
    'sequence': 14,
    'summary': '',
    "author":"others",
    'website': 'www.others.com',
    'license': 'AGPL-3',
    'description':"""\
This module intercept the updating params for expiration date on 19e """,
    "depends":['base','mail'],
    "author":"others",
    "data":[
        # 'views/res_currency_view.xml',
        # 'views/cop_trm_cron_data.xml',
    ],
    "installable":True
 }
