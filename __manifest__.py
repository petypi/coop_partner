{
    "name": "Copia Partner",
    "version": "1.0",
    "category": "Sale",
    "sequence": 80,
    "author": "Muratha & Musa",
    "summary": "Partner customizations for Copia",
    "description": """
Customizations to Partner(base)
    * Added __agent.type__ e.g *Field*, *TBCs* etc
    * Locations
    * Territories
    * Geo-location and Directions
    * Kiswahili translations e.g for SMSs
""",
    "website": "https://www.copiaglobal.com",
    "depends": [
        "base",
        "sale_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/copia_partner_security.xml",
        "views/res_partner_view.xml",
        "views/res_partner_territory_view.xml",
        "views/res_partner_location_view.xml",
        "views/res_partner_location_type_view.xml",
        "data/res_partner_data.xml"
    ],
    "installable": True,
    "auto_install": False
}
