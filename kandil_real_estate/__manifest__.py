{
    'name': 'Kandil Real Estate',
    'version': '1.0.0',
    'summary': 'Manage buildings, units, reservations and contracts',
    'description': 'Real estate management: units, reservations, contracts, installments, payments',
    'author': 'MOHAMED ABDALLAH OMER',
    'website': 'https://kandiltech.com',
    'category': 'Real Estate',
    'depends': ['base', 'mail', 'contacts', 'account'],
'data': [
    # 1. الأمان
    'security/security_groups.xml',
    'security/ir.model.access.csv',
    
    # 2. الأكشنز
    'views/estate_actions.xml',
    
    # 3. المشاهد
    'views/estate_building_views.xml',
    'views/estate_unit_views.xml',
    'views/estate_reservation_views.xml',
    'views/estate_installment_views.xml',
    'views/estate_contract_views.xml',
    
    # 4. القوائم (آخر شيء)
    'views/estate_menus.xml'
],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
