from flask import Flask, render_template, request, redirect, url_for, g
from recipe_helper import DataStore, RecipeFinder, GroceryList
from typing import Dict, Any

# 🚨 กำหนดค่า API KEY
API_KEY = "3d590967e60048a6887dfd1866830566"

# สร้าง Flask App
app = Flask(__name__)

# สร้าง Instance ที่เป็น Global (Finder ไม่ยุ่งกับ DB จึงไม่มีปัญหา Threading)
finder = RecipeFinder(API_KEY)


# -------------------------------------------------------------
# 1. การจัดการฐานข้อมูลใน Application Context (แก้ไขปัญหา Threading)
# -------------------------------------------------------------
def get_db():
    if 'db' not in g:
        # สร้าง DataStore Instance และเก็บไว้ใน g
        g.db = DataStore("recipes.db")
    return g.db

def get_grocery_helper(ds):
    # สร้าง GroceryList Instance โดยใช้ DataStore ที่ถูกต้อง
    if 'grocery_helper' not in g:
        g.grocery_helper = GroceryList(ds)
    return g.grocery_helper

@app.teardown_appcontext
def close_connection(exception):
    # ปิดการเชื่อมต่อ DB และลบ Instance ของ GroceryList เมื่อ Request สิ้นสุดลง
    db = g.pop('db', None)
    g.pop('grocery_helper', None)
    if db is not None:
        db.close()


# -------------------------------------------------------------
# 2. ฟังก์ชันหลัก: หน้าค้นหา (Homepage)
# -------------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    recipes = []
    query = ""

    if request.method == 'POST':
        query = request.form.get('ingredient')
        if query:
            # เรียกใช้ Logic ที่คุณเขียนไว้ใน RecipeFinder
            results_from_api = finder.search_by_ingredient(query)

            # แปลงผลลัพธ์ให้อยู่ในรูปแบบที่ Template เข้าใจง่าย
            recipes = [
                {'id': r['id'], 'title': r['title']}
                for r in results_from_api
            ]

    # แสดงผลลัพธ์ในไฟล์ HTML 'index.html'
    return render_template('index.html', recipes=recipes, query=query)


# -------------------------------------------------------------
# 3. ฟังก์ชัน: บันทึกสูตรโปรด
# -------------------------------------------------------------
@app.route('/favorite/<int:recipe_id>')
def favorite(recipe_id):
    ds = get_db() # 🚨 ใช้ get_db() เพื่อเข้าถึง DB
    
    # ดึงรายละเอียดวัตถุดิบทั้งหมดจาก API
    recipe_info: Dict[str, Any] = finder.get_recipe_details(recipe_id)

    if recipe_info and recipe_info.get('title'):
        # เรียกใช้ Logic บันทึกสูตรใน DataStore
        ds.save_favorite(recipe_id,
                         recipe_info['title'],
                         recipe_info['ingredients'])

    # Redirect กลับไปหน้าหลัก
    return redirect(url_for('index'))


# -------------------------------------------------------------
# 4. ฟังก์ชัน: ดูรายการซื้อของ
# -------------------------------------------------------------
@app.route('/grocery')
def show_grocery_list():
    ds = get_db() # 🚨 ใช้ get_db() เพื่อเข้าถึง DB
    
    # ใช้ DataStore ใน Context เพื่อสร้าง GroceryList
    grocery_helper = get_grocery_helper(ds)
    
    # ดึงสูตรโปรดทั้งหมด (จาก Logic ใน DataStore)
    favorites = ds.get_favorites()

    # สร้างรายการซื้อของ (จาก Logic ใน GroceryList)
    shopping_list_dict = grocery_helper.build_list()

    # แปลง Dictionary เป็น List ของชื่อวัตถุดิบสำหรับแสดงผลใน HTML
    shopping_list = sorted(list(shopping_list_dict.keys()))

    return render_template(
        'favorites.html',
        favorites=favorites,
        shopping_list=shopping_list
    )


# -------------------------------------------------------------
# 5. ฟังก์ชัน: ดูรายละเอียดสูตรอาหาร
# -------------------------------------------------------------
@app.route('/recipe/<int:recipe_id>')
def view_recipe(recipe_id):
    recipe_info = finder.get_recipe_details(recipe_id)
    
    # 🚨 สำคัญ: ต้องส่ง ID ไปด้วยเพื่อให้ปุ่ม Favorite ทำงานในหน้านี้
    if recipe_info:
        recipe_info['id'] = recipe_id
        # ส่งข้อมูลไปแสดงผลใน template ใหม่
        return render_template('recipe_detail.html', info=recipe_info)

    return "ไม่พบข้อมูลสูตรอาหาร", 404




# -------------------------------------------------------------
# 6. ฟังก์ชัน: ลบสูตรโปรด
# -------------------------------------------------------------
@app.route('/delete/<int:recipe_id>', methods=['POST']) 
def delete_favorite_route(recipe_id):
    ds = get_db()
    # 🚨 เมื่อคุณแก้ไข delete_favorite ใน recipe_helper.py แล้ว
    ds.delete_favorite(recipe_id) 
    # Redirect กลับไปหน้า Grocery List
    return redirect(url_for('show_grocery_list')) 
# ...


# -------------------------------------------------------------
# 7. รัน Web Server
# -------------------------------------------------------------
if __name__ == '__main__':
    # รันด้วย threaded=False เพื่อแก้ปัญหา SQLite Threading
    app.run(debug=True, threaded=False)
