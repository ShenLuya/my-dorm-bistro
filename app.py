# app.py
import streamlit as st
from recipes_data import RECIPES
from supabase import create_client, Client

# ---------- 数据库连接 ----------
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# ---------- 数据库读写函数 ----------
def load_fridge_from_db():
    try:
        response = supabase.table('fridge').select('items').eq('id', 1).execute()
        if response.data and len(response.data) > 0:
            items = response.data[0].get('items', [])
            return items if items is not None else []
        return []
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        return []

def save_fridge_to_db(items):
    try:
        data = {'id': 1, 'items': items}
        supabase.table('fridge').upsert(data).execute()
    except Exception as e:
        st.error(f"保存数据失败：{e}")

# ---------- 初始化 Session ----------
if "fridge" not in st.session_state:
    st.session_state.fridge = load_fridge_from_db()
    if not st.session_state.fridge:
        save_fridge_to_db([])
        st.session_state.fridge = load_fridge_from_db()

# ---------- 提取所有食材（从菜谱中） ----------
ALL_INGREDIENTS = sorted(set(
    ing for recipe in RECIPES for ing in recipe["ingredients"]
))

# ---------- 推荐逻辑（不变） ----------
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
st.caption("点击食材按钮，一键管理你的冰箱")

# ---------- 区域一：冰箱管理（点击式） ----------
st.subheader("🧊 我的冰箱")

# 显示当前冰箱里的食材（紧凑型）
if st.session_state.fridge:
    st.write("📦 当前存有：", ", ".join(st.session_state.fridge))
else:
    st.info("冰箱是空的，从下面的食材库点击添加吧！")

# 清空按钮（辅助）
if st.button("🗑️ 清空冰箱", use_container_width=False):
    st.session_state.fridge.clear()
    save_fridge_to_db(st.session_state.fridge)
    st.rerun()

st.divider()

# ---------- 食材库（所有可选食材） ----------
st.subheader("📋 食材库（点击切换）")
st.caption("点击未选中的食材 ➕ 添加，点击已选中的食材 ➖ 移除")

# 按行分列显示（每行5个）
cols_per_row = 5
cols = st.columns(cols_per_row)

for idx, ingredient in enumerate(ALL_INGREDIENTS):
    col_idx = idx % cols_per_row
    with cols[col_idx]:
        # 判断是否已在冰箱中
        if ingredient in st.session_state.fridge:
            button_label = f"✅ {ingredient}"
            button_type = "primary"  # 绿色高亮
        else:
            button_label = f"➕ {ingredient}"
            button_type = "secondary"

        # 点击按钮触发切换
        if st.button(button_label, key=f"btn_{ingredient}", use_container_width=True, type=button_type):
            if ingredient in st.session_state.fridge:
                st.session_state.fridge.remove(ingredient)
            else:
                st.session_state.fridge.append(ingredient)
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
    - **点击添加/移除**：所有食材都来自菜谱，点一下即可。
    - **永久记忆**：数据存在 Supabase 云端。
    - **智能推荐**：根据你的冰箱列出能做的菜。
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
