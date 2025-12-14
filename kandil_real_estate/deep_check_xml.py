import os
import glob

def deep_check_xml():
    xml_files = glob.glob('**/*.xml', recursive=True)
    
    for xml_file in xml_files:
        print(f"\n🔍 فحص: {xml_file}")
        
        try:
            with open(xml_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # تحقق من السطر الأول
            if len(lines) > 0:
                first_line = lines[0].strip()
                if not first_line.startswith('<?xml'):
                    print(f"  ❌ الخطأ: لا يبدأ بـ <?xml")
                    print(f"     السطر الأول: '{first_line}'")
                    
                    # أضف <?xml إذا كان مفقوداً
                    lines.insert(0, '<?xml version="1.0" encoding="UTF-8"?>\n')
                    with open(xml_file, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    print(f"  ✅ تم إصلاح الملف")
                
                # تحقق من السطر الثاني
                if len(lines) > 1:
                    second_line = lines[1].strip()
                    if not second_line.startswith('<odoo>'):
                        print(f"  ⚠️  تحذير: السطر الثاني ليس <odoo>")
                        print(f"     السطر الثاني: '{second_line}'")
            
            # عد الأسطر
            print(f"  عدد الأسطر: {len(lines)}")
            
        except Exception as e:
            print(f"  ❌ خطأ في قراءة الملف: {e}")

if __name__ == "__main__":
    print("فحص شامل لجميع ملفات XML...")
    deep_check_xml()
    print("\n✅ تم الانتهاء من الفحص!")