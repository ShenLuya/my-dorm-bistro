# app.py
import streamlit as st
import json
import os
from recipes_data import RECIPES
from supabase import create_client, Client

# ---------- 数据持久化 ----------
FRIDGE_FILE = "fridge.json"

# ---------- 数据库连接 ----------
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# ---------- 数据库读写函数 ----------
def load_fridge_from_db():
    """从 Supabase 加载冰箱数据（只取 id=1 的行）"""
    try:
        # 明确查询 id=1 的行，只取 items 字段
        response = supabase.table('fridge').select('items').eq('id', 1).execute()
        
        # ---------- 调试信息（部署后可查看） ----------
        st.write("### 🐞 调试：load_fridge_from_db 执行结果")
        st.write("完整 response 对象：", response)
        st.write("response.data：", response.data)
        # --------------------------------------------

        if response.data and len(response.data) > 0:
            row = response.data[0]
            items = row.get('items', [])
            st.write("提取的 items：", items)   # 调试
            if items is None:
                return []
            return items
        else:
            st.warning("⚠️ 数据库中没有 id=1 的记录，将返回空列表")
            return []
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        st.write(f"错误详情：{e}")   # 调试
        return []

def save_fridge_to_db(items):
    """使用 upsert 保存（存在则更新，不存在则插入）"""
    try:
        data = {'id': 1, 'items': items}
        supabase.table('fridge').upsert(data).execute()
        st.success(f"✅ 数据已保存到数据库：{items}")
    except Exception as e:
        st.error(f"❌ 保存失败：{e}")
        st.write(f"错误详情：{e}")

# ---------- 初始化 Session ----------
if "fridge" not in st.session_state:
    st.session_state.fridge = load_fridge_from_db()
    # 如果加载后仍为空，可主动创建一行（可选）
    if not st.session_state.fridge:
        # 尝试写入一个空列表，确保行存在
        save_fridge_to_db([])
        # 重新加载一次
        st.session_state.fridge = load_fridge_from_db()

# ---------- 推荐逻辑 ----------
def is_ingredient_available(recipe_ing, user_ings):
    for user_ing in user_ings:
        if recipe_ing in user_ing or user_ing in recipe_ing:
            return True
    return False

def recommend_recipes(user_items):
    full_matches = []
    partial_matches = []

    for recipe in RECIPES:
        needed = recipe["ingredients"]
        missing = []
        for ing in needed:
            if not is_ingredient_available(ing, user_items):
                missing.append(ing)

        if not missing:
            full_matches.append(recipe)
        else:
            partial_matches.append((recipe, missing))

    partial_matches.sort(key=lambda x: len(x[1]))
    return full_matches, partial_matches

# ============================================
# 页面布局
# ============================================
st.set_page_config(page_title="宿舍小厨房", page_icon="🍳", layout="centered")

st.title("🍳 宿舍小厨房")
st.caption("记住你的冰箱，推荐能做的菜")

# ---------- 区域一：冰箱管理 ----------
st.subheader("🧊 我的冰箱")

col1, col2 = st.columns([3, 1])
with col1:
    new_item = st.text_input("输入食材名称（如：牛肉片）", key="input_item", placeholder="例如：鸡蛋")
with col2:
    if st.button("➕ 添加"):
        if new_item and new_item.strip():
            item = new_item.strip()
            if item not in st.session_state.fridge:
                st.session_state.fridge.append(item)
                save_fridge_to_db(st.session_state.fridge)
                st.success(f"✅ 已添加 {item}")
                st.rerun()
            else:
                st.warning(f"⚠️ {item} 已经在冰箱里了")
        else:
            st.error("请输入食材名称")

# 显示当前冰箱列表
if st.session_state.fridge:
    st.write("📦 当前存有：")
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.fridge):
        col_idx = idx % 4
        with cols[col_idx]:
            if st.button(f"❌ {item}", key=f"del_{item}"):
                st.session_state.fridge.remove(item)
                save_fridge_to_db(st.session_state.fridge)
                st.rerun()
else:
    st.info("冰箱是空的，快去添加食材吧！")

# 清空按钮
if st.button("🗑️ 清空冰箱"):
    st.session_state.fridge.clear()
    save_fridge_to_db(st.session_state.fridge)
    st.rerun()

st.divider()

# ---------- 区域二：推荐菜谱 ----------
st.subheader("🔍 今日推荐")

if st.button("✨ 根据冰箱推荐菜谱", use_container_width=True):
    if not st.session_state.fridge:
        st.warning("冰箱是空的，先添加食材吧！")
    else:
        full, partial = recommend_recipes(st.session_state.fridge)

        if full:
            st.success(f"✅ 完全可以做（{len(full)}道）")
            for r in full:
                with st.expander(f"{r['id']} {r['name']}（{r['time_level']}，{r['equipment'][0]}）"):
                    st.write("📦 需要食材：")
                    for ing in r["ingredients"]:
                        st.write(f"  • {ing}")
                    st.caption(f"类型：{r['type']} | 用时：{r['time_level']}")
        else:
            st.info("😅 没有能完全匹配的菜，看看下面还缺什么吧")

        if partial:
            st.warning(f"🔍 差一点点就能做（{len(partial)}道），按缺少数量从少到多排列：")
            for r, missing in partial[:15]:
                with st.expander(f"{r['id']} {r['name']}（缺少 {len(missing)} 样）"):
                    st.write("📦 需要食材：")
                    for ing in r["ingredients"]:
                        if ing in missing:
                            st.write(f"  • ❌ {ing}（缺少）")
                        else:
                            st.write(f"  • ✅ {ing}")
                    st.caption(f"类型：{r['type']} | 用时：{r['time_level']} | 厨具：{', '.join(r['equipment'])}")
            if len(partial) > 15:
                st.text(f"... 还有 {len(partial) - 15} 道未显示")
        else:
            st.balloons()
            st.success("🎉 你冰箱里的东西太全了！所有菜都能做！")

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("📋 小贴士")
    st.markdown("""
    - **永久记忆**：数据存在 Supabase 云端数据库。
    - **模糊匹配**：输入“牛肉片”能匹配到需要“牛肉”的菜。
    - **部分推荐**：即使缺食材也会列出，告诉你缺什么。
    """)

    if st.button("📊 查看统计"):
        total = len(RECIPES)
        types = {}
        for r in RECIPES:
            types[r["type"]] = types.get(r["type"], 0) + 1
        st.write(f"总菜谱：{total} 道")
        st.write("分类统计：")
        for t, count in types.items():
            st.write(f"  - {t}：{count} 道")

    st.divider()
    st.caption("数据保存在 Supabase 云端数据库")
