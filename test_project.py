# test_project.py

import pytest
from unittest.mock import MagicMock, patch
import json
import sqlite3
import os
import requests
from recipe_helper import DataStore, GroceryList, RecipeFinder


# 1. Test DataStore (ใช้ฐานข้อมูลชั่วคราว)
@pytest.fixture
def temp_datastore():
    """Fixture สำหรับ DataStore ที่ใช้ฐานข้อมูลชั่วคราวใน memory"""
    ds = DataStore(db_name=":memory:")
    yield ds
    ds.close()


def test_datastore_save_and_get_favorite(temp_datastore):
    """ทดสอบการบันทึกและดึงข้อมูลสูตรโปรด"""
    recipe_id = 12345
    title = "Test Cake"
    ingredients = ["flour", "sugar"]

    assert temp_datastore.save_favorite(recipe_id, title, ingredients) is True

    favorites = temp_datastore.get_favorites()
    assert len(favorites) == 1

    r_id, r_title, r_json = favorites[0]
    assert r_id == recipe_id
    assert r_title == title
    assert json.loads(r_json) == ingredients


# 2. Test GroceryList (ตรรกะการรวมวัตถุดิบ)
@pytest.fixture
def mock_datastore_for_grocery():
    """Fixture สำหรับจำลอง DataStore เพื่อทดสอบ GroceryList"""
    mock_ds = MagicMock(spec=DataStore)
    # สูตร 1: มี Garlic
    # สูตร 2: มี Garlic และ 1 cup of Milk (เพื่อทดสอบ normalization)
    mock_ds.get_favorites.return_value = [
        (100, "Spaghetti", json.dumps(["pasta", "tomato sauce", "garlic"])),
        (101, "Soup", json.dumps(["1 cup of milk", "garlic", "salt"]))
    ]
    return mock_ds


def test_build_list_combines_and_normalizes(mock_datastore_for_grocery):
    """ทดสอบว่า GroceryList รวมวัตถุดิบและล้างหน่วย/ตัวเลขออกอย่างถูกต้อง"""
    grocery = GroceryList(mock_datastore_for_grocery)
    shopping_list = grocery.build_list()

    # วัตถุดิบควรถูก Normalize และแสดงเพียงครั้งเดียว
    # 'garlic' ควรมี key เดียว แม้มาจาก 2 สูตร
    assert 'garlic' in shopping_list
    assert 'pasta' in shopping_list
    assert 'tomato sauce' in shopping_list
    assert 'milk' in shopping_list  # ตรวจสอบว่า "1 cup of milk" เหลือ "milk"
    assert 'salt' in shopping_list

    # ตรวจสอบจำนวนรายการที่ไม่ซ้ำกัน
    assert len(shopping_list) == 5


# 3. Test RecipeFinder (การจัดการ API Error)
@patch('recipe_helper.requests.get')
def test_finder_handles_http_error(mock_get):
    """ทดสอบการจัดการข้อผิดพลาด HTTP 404"""

    # กำหนดให้ requests.get() ส่ง HTTPError 404 กลับมา
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
    mock_get.return_value = mock_response

    finder = RecipeFinder("dummy_key")
    results = finder.search_by_ingredient("onion")

    # ผลลัพธ์ควรเป็น Dict/List ว่างเมื่อเกิดข้อผิดพลาด
    assert results == []
