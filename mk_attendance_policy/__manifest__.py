{
    'name': 'MK Attendance Policy',
    'version': '17.0.1.0',
    'author': "Mohamed Kandil",
    'website': "mohamed.kandil@myntrocode.com",
    'price': 100,
    'currency': 'USD',
    'summary': 'Attendance policy rules for late deductions, overtime, absence, public holidays, and payroll inputs.',
    'depends': [
        'hr',
        'hr_attendance',
        'hr_contract',
        'hr_payroll_community',
        'account',
        'mail'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/mk_attendance_views.xml',
        'views/hr_employee_views.xml',
        'views/attendance_sheet_line_views.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
