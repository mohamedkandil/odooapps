{
    "name": "User Access Management",
    "summary": "Manage user interface and model access rules from one screen",
    "version": "17.0.1.0.0",
    "category": "Administration",
    "author": "Mohhamed Kandil",
    "license": "LGPL-3",
    'price': 350.00,
    'currency': 'USD',
    "web_icon": "mk_ccess_manament,static/description/icon.png",
    "images": [
        "static/description/thumbnail.png",
        "static/description/images/main_screenshot.png",
    ],
    "depends": ["base", "web", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/access_management_views.xml",
        "views/menu.xml",
    ],
    "application": True,
    "installable": True,
}
