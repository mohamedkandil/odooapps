# fix_all_xml.py - ضعه في مجلد الموديل
import os
import glob

def fix_all_xml_files():
    # ابحث عن جميع ملفات XML
    xml_files = glob.glob('**/*.xml', recursive=True)
    
    for xml_file in xml_files:
        print(f"🔧 إصلاح: {xml_file}")
        
        with open(xml_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()
        
        # تحقق إذا كان الملف يبدأ بـ <?xml
        if not content.startswith('<?xml'):
            print(f"  ❌ مفقود <?xml ... إضافة...")
            
            # أضف <?xml إذا كان مفقوداً
            new_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + content
            
            # تأكد أن الملف ينتهي بـ </odoo>
            if not new_content.strip().endswith('</odoo>'):
                print(f"  ⚠️ قد يكون مفقود </odoo>")
            
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"  ✅ تم الإصلاح")
        else:
            print(f"  ✅ جيد")
        
        print()

if __name__ == "__main__":
    print("فحص وإصلاح جميع ملفات XML...")
    fix_all_xml_files()
    print("✅ تم الانتهاء!")