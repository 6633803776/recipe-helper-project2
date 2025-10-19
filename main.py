# main.py

from recipe_helper import DataStore, RecipeFinder, GroceryList
import sys

# **********************************************
# 🚨 สำคัญ: ต้องใส่ API Key ของคุณที่นี่
API_KEY = "3d590967e60048a6887dfd1866830566"
# **********************************************


def display_menu():
    """แสดงเมนูหลัก"""
    print("\n=================================")
    print("🍳 Recipe Recommender & Helper")
    print("1. ค้นหาสูตรจากวัตถุดิบ")
    print("2. ดูสูตรโปรดและสร้างรายการซื้อของ")
    print("3. ออกจากโปรแกรม")
    print("=================================")


def run_recipe_search(finder: RecipeFinder, ds: DataStore):
    """จัดการตรรกะการค้นหาสูตรและบันทึกโปรด"""
    ingredient = input("ป้อนวัตถุดิบที่คุณมี: ")
    if not ingredient:
        print("❌ กรุณาป้อนวัตถุดิบ")
        return

    results = finder.search_by_ingredient(ingredient)

    if results:
        print("\n=== ผลการค้นหา 🔎 ===")
        # แสดงผลการค้นหา
        for i, r in enumerate(results):
            print(f"{i + 1}. {r.get('title')} (ID: {r.get('id')})")
        print("========================")

        # แก้ E226 และ W293
        save_choice = input(
            "ต้องการบันทึกสูตรใดเป็นสูตรโปรดหรือไม่? (ป้อนหมายเลข, 'n' เพื่อข้าม): "
        )

        if save_choice.isdigit():
            idx = int(save_choice) - 1
            if 0 <= idx < len(results):
                recipe_id = results[idx]['id']

                # ดึงรายละเอียดวัตถุดิบก่อนบันทึก (ต้องเรียก API อีกครั้ง)
                recipe_info = finder.get_recipe_details(recipe_id)

                if recipe_info and recipe_info.get('title'):
                    ds.save_favorite(
                        recipe_id,
                        recipe_info['title'],
                        recipe_info['ingredients']
                    )
                else:
                    print("❌ ไม่สามารถดึงข้อมูลรายละเอียดสูตรอาหารได้")
            else:
                print("❌ หมายเลขไม่ถูกต้อง")
    else:
        print("💡 ไม่พบสูตรอาหารสำหรับวัตถุดิบที่ป้อน")


def main():
    if API_KEY == "YOUR_SPOONACULAR_API_KEY_HERE":
        print("🚨 กรุณาแก้ไข API_KEY ในไฟล์ main.py ก่อนเริ่มต้น")
        sys.exit(1)

    # สร้าง Instance ของคลาสต่างๆ
    ds = DataStore()
    finder = RecipeFinder(API_KEY)
    grocery = GroceryList(ds)

    try:
        while True:
            display_menu()
            choice = input("เลือกเมนู (1-3): ")

            if choice == '1':
                run_recipe_search(finder, ds)
            elif choice == '2':
                shopping_list = grocery.build_list()
                grocery.display_list(shopping_list)
            elif choice == '3':
                print("👋 ลาก่อน ขอบคุณที่ใช้บริการครับ")
                break
            else:
                print("กรุณาเลือกเมนู 1, 2, หรือ 3")
    finally:
        # ปิดการเชื่อมต่อฐานข้อมูลเมื่อโปรแกรมจบ
        ds.close()


if __name__ == "__main__":
    main()
