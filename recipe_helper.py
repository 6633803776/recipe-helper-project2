from typing import List, Tuple, Dict, Any
import sqlite3
import json
import requests
from collections import defaultdict
import re


class DataStore:
    """จัดการการเชื่อมต่อและการจัดการข้อมูลกับฐานข้อมูล SQLite"""

    def __init__(self, db_name="recipes.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        """สร้างตาราง favorites หากยังไม่มี"""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY,
                title TEXT,
                ingredients_json TEXT
            )
            """
        )
        self.conn.commit()

    def save_favorite(
        self,
        recipe_id: int,
        title: str,
        ingredients: List[str]
    ) -> bool:
        """บันทึกสูตรอาหารที่ชอบ
        (ใช้ INSERT OR REPLACE เพื่ออัปเดตหาก ID ซ้ำ)"""

        ingredients_str = json.dumps(ingredients)
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO favorites "
                "(id, title, ingredients_json) VALUES (?, ?, ?)",
                (recipe_id, title, ingredients_str)
            )
            self.conn.commit()
            return True
        except Exception as e:
            # แก้ไข Docstring สั้นๆ เพื่อให้บรรทัดไม่ยาวเกิน 79 ตัวอักษร
            print(f"Database Save Error: {e}")
            return False

    def get_favorites(self) -> List[Tuple[int, str, str]]:
        """ดึงสูตรอาหารที่ชอบทั้งหมด (คืนค่าเป็น List ของ Tuple)"""
        self.cursor.execute(
            "SELECT id, title, ingredients_json FROM favorites"
        )
        return self.cursor.fetchall()

    def close(self):
        """ปิดการเชื่อมต่อฐานข้อมูล"""
        self.conn.close()

    # 🚨 แก้ไข: ฟังก์ชัน delete_favorite ถูกย้ายออกมาจาก close() แล้ว
    def delete_favorite(self, recipe_id: int) -> bool:
        """ลบสูตรอาหารโปรดออกจากฐานข้อมูล"""
        try:
            self.cursor.execute(
                "DELETE FROM favorites WHERE id = ?",
                (recipe_id,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Database Delete Error: {e}")
            return False


class RecipeFinder:
    """จัดการการสื่อสารกับ Spoonacular API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.spoonacular.com/recipes/"

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ฟังก์ชันช่วยเหลือสำหรับการเรียก API และจัดการข้อผิดพลาด"""

        params['apiKey'] = self.api_key
        try:
            # ทำ GET request
            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params
            )

            # ตรวจสอบ HTTP status code (เช่น 404, 500)
            response.raise_for_status()

            return response.json()
        except requests.exceptions.HTTPError as e:
            # การแก้ไขสำคัญ: ตรวจสอบ response และใช้ f-string สั้นๆ
            status = e.response.status_code if e.response is not None \
                else 'Unknown'
            print(f"❌ HTTP Error: {status} - API Key หรือ Limit มีปัญหา")
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection Error: ไม่สามารถเชื่อมต่อกับ API ได้: {e}")
        return {}

    def search_by_ingredient(
        self,
        ingredient: str
    ) -> List[Dict[str, Any]]:
        """ค้นหาสูตรอาหารจากวัตถุดิบที่กำหนด"""
        params = {
            "ingredients": ingredient,
            "number": 5  # จำกัดผลลัพธ์แค่ 5 รายการ
        }
        results = self._make_request("findByIngredients", params)
        # API นี้อาจคืนค่าเป็น List หรือ Dict (ในกรณี error)
        return results if isinstance(results, list) else []

    def get_recipe_details(self, recipe_id: int) -> Dict[str, Any]:
        """ดึงรายละเอียดวัตถุดิบทั้งหมดสำหรับสูตรอาหาร"""
        endpoint = f"{recipe_id}/information"
        params = {"includeNutrition": "false"}
        data = self._make_request(endpoint, params)

        if data:
            # ดึงเฉพาะชื่อวัตถุดิบเดิม (original) ที่ใช้ในสูตร
            ingredients = [
                item['original']
                for item in data.get('extendedIngredients', [])
            ]
            return {
                "title": data.get("title"),
                "ingredients": ingredients
            }
        return {}


class GroceryList:
    """จัดการตรรกะในการสร้างรายการซื้อของ"""

    def __init__(self, datastore: DataStore):
        self.datastore = datastore

    def build_list(self) -> Dict[str, int]:
        """สร้างรายการซื้อของที่รวมวัตถุดิบทั้งหมดจากสูตรโปรด"""
        favorites = self.datastore.get_favorites()
        shopping_list: Dict[str, int] = defaultdict(int)

        if not favorites:
            # คืนค่า Dict ว่างเปล่าถ้าไม่มีสูตรโปรด
            return {}

        for _, _, ingredients_json in favorites:
            ingredients = json.loads(ingredients_json)

            for item_full in ingredients:
                # 1. ลบตัวเลข, เศษส่วน, และหน่วยวัดทั่วไป
                item_normalized = re.sub(
                    r'(\d+\s*[\/|\.]*\d*|\d)', '', item_full, 1
                ).strip()
                item_normalized = re.sub(
                    r'(cup|teaspoon|tablespoon|tsp|tbsp|oz|g|kg|ml|l|pound|lb)'
                    r's?\b',
                    '',
                    item_normalized,
                    flags=re.IGNORECASE
                ).strip()

                # 2. ลบคำเชื่อมที่ไม่จำเป็น
                final_item = (
                    item_normalized.lower()
                    .replace('of', '').replace('and', '')
                    .replace(',', '').strip()
                )

                # 3. นับรวมรายการ
                if final_item:
                    shopping_list[final_item] += 1

        return shopping_list

    def display_list(self, shopping_list: Dict[str, int]):
        """แสดงรายการซื้อของ"""
        if not shopping_list:
            print(
                "💡 ยังไม่มีสูตรอาหารโปรดในรายการ / "
                "รายการซื้อของว่างเปล่า"
            )
            return

        print("\n=== รายการซื้อของที่จำเป็น 🛒 ===")
        # แสดงรายการที่รวมแล้ว โดยเรียงตามตัวอักษร
        for item, count in sorted(shopping_list.items()):
            # ใช้ .title() เพื่อให้ตัวอักษรแรกเป็นตัวพิมพ์ใหญ่
            print(f"• {item.title()}")
        print("================================")
