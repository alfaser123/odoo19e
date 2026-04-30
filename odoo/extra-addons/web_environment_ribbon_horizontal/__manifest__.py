# Copyright 2022-2025 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

{
    "name": "Web Environment Ribbon Horizontal",
    "summary": """Mark a Test Environment with a red ribbon on the top in every page
        """,
    "version": "19.0.1.0.0",
    "category": "web",
    "website": "https://sodexis.com/",
    "author": "Sodexis",
    "license": "OPL-1",
    "installable": True,
    "application": False,
    "depends": ["web"],
    "data": [
        "data/ribbon_data.xml",
    ],
    "images": ["images/main_screenshot.jpg"],
    "live_test_url": "https://sodexis.com/odoo-apps-store-demo",
    "assets": {
        "web.assets_backend": [
            "web_environment_ribbon_horizontal/static/src/components/*",
        ],
    },
}
