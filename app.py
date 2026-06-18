# app.py
import streamlit as st
from recipes_data import RECIPES
from supabase import create_client, Client
from collections import defaultdict

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

if "mode" not in st.session_state:
    st.session_state.mode = None          # None=首页, "cook"=做菜, "shop"=买菜
if "selected_recipes" not in st.session_state:
    st.session_state.selected_recipes = []  # 存放选中的菜谱 id

# ---------- 提取所有食材（用于做菜模式的食材库） ----------
ALL_INGREDIENTS = sorted(set(
    ing for recipe in RECIPES for ing in recipe["ingredients"]
))

# ---------- 推荐逻辑（做菜模式） ----------
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
# 页面 - 首页
# ============================================
def show_home():
    st.set_page_config(page_title="宿舍小厨房", page_icon="🍳", layout="centered")
    st.title("🍳 宿舍小厨房")
    st.subheader("今天你想做什么？")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🍳 今天做菜", use_container_width=True, type="primary"):
            st.session_state.mode = "cook"
            st.rerun()
    with col2:
        if st.button("🛒 今天买菜", use_container_width=True, type="secondary"):
            st.session_state.mode = "shop"
            st.rerun()

    with st.sidebar:
        st.header("📋 小贴士")
        st.markdown("""
        - **做菜**：管理冰箱，推荐能做的菜。
        - **买菜**：挑选想吃的菜，生成购物清单。
        - 数据永久保存在云端。
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

# ============================================
# 页面 - 做菜模式（原完整功能）
# ============================================
def show_cook_mode():
    st.set_page_config(page_title="做菜 - 宿舍小厨房", page_icon="🍳", layout="centered")

    # 侧边栏返回按钮
    with st.sidebar:
        if st.button("🏠 返回首页"):
            st.session_state.mode = None
            st.session_state.selected_recipes = []  # 清空选菜记录（若有）
            st.rerun()
        st.divider()
        st.header("📋 小贴士")
        st.markdown("""
        - **点击食材**：添加/移除冰箱。
        - **推荐菜谱**：根据冰箱食材智能推荐。
        - 数据永久保存。
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

    st.title("🍳 做菜模式")
    st.caption("管理冰箱，推荐能做的菜")

    # ---------- 冰箱管理 ----------
    st.subheader("🧊 我的冰箱")
    if st.session_state.fridge:
        st.write("📦 当前存有：", ", ".join(st.session_state.fridge))
    else:
        st.info("冰箱是空的，从下面的食材库点击添加吧！")

    if st.button("🗑️ 清空冰箱", use_container_width=False):
        st.session_state.fridge.clear()
        save_fridge_to_db(st.session_state.fridge)
        st.rerun()

    st.divider()

    # ---------- 食材库 ----------
    st.subheader("📋 食材库（点击切换）")
    st.caption("点击未选中的食材 ➕ 添加，点击已选中的食材 ➖ 移除")

    cols_per_row = 5
    cols = st.columns(cols_per_row)
    for idx, ingredient in enumerate(ALL_INGREDIENTS):
        col_idx = idx % cols_per_row
        with cols[col_idx]:
            if ingredient in st.session_state.fridge:
                button_label = f"✅ {ingredient}"
                button_type = "primary"
            else:
                button_label = f"➕ {ingredient}"
                button_type = "secondary"
            if st.button(button_label, key=f"btn_{ingredient}", use_container_width=True, type=button_type):
                if ingredient in st.session_state.fridge:
                    st.session_state.fridge.remove(ingredient)
                else:
                    st.session_state.fridge.append(ingredient)
                save_fridge_to_db(st.session_state.fridge)
                st.rerun()

    st.divider()

    # ---------- 推荐菜谱 ----------
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

# ============================================
# 页面 - 买菜模式（选菜→生成购物清单）
# ============================================
def show_shop_mode():
    st.set_page_config(page_title="买菜 - 宿舍小厨房", page_icon="🛒", layout="centered")

    # 侧边栏返回按钮
    with st.sidebar:
        if st.button("🏠 返回首页"):
            st.session_state.mode = None
            st.session_state.selected_recipes = []  # 清空选择
            st.rerun()
        st.divider()
        st.header("📋 小贴士")
        st.markdown("""
        - **勾选菜谱**：选择今天想吃的菜。
        - **生成清单**：系统自动汇总所需食材。
        - 可以多选，清单会去重合并。
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

    st.title("🛒 买菜模式")
    st.caption("勾选你想吃的菜，一键生成购物清单")

    # 显示所有菜谱，按分组折叠
    # 先按 type 分组
    groups = defaultdict(list)
    for r in RECIPES:
        groups[r["type"]].append(r)

    # 清空所有选择的按钮
    col_clear, col_count = st.columns([1, 3])
    with col_clear:
        if st.button("🗑️ 清空所有选择"):
            st.session_state.selected_recipes = []
            st.rerun()
    with col_count:
        st.write(f"已选 {len(st.session_state.selected_recipes)} 道菜")

    st.divider()

    # 遍历每个分组，显示折叠面板
    for group_name, recipes in groups.items():
        with st.expander(f"📂 {group_name}（{len(recipes)}道）", expanded=True):
            # 每行显示3个菜谱（带复选框）
            for i in range(0, len(recipes), 3):
                cols = st.columns(3)
                for j in range(3):
                    idx = i + j
                    if idx < len(recipes):
                        recipe = recipes[idx]
                        with cols[j]:
                            # 判断是否被选中
                            is_checked = recipe["id"] in st.session_state.selected_recipes
                            if st.checkbox(
                                f"{recipe['name']}",
                                value=is_checked,
                                key=f"shop_{recipe['id']}",
                            ):
                                if recipe["id"] not in st.session_state.selected_recipes:
                                    st.session_state.selected_recipes.append(recipe["id"])
                            else:
                                if recipe["id"] in st.session_state.selected_recipes:
                                    st.session_state.selected_recipes.remove(recipe["id"])
                            # 显示用时和厨具小标签
                            st.caption(f"⏱ {recipe['time_level']} | {recipe['equipment'][0]}")

    st.divider()

    # 生成购物清单按钮
    if st.button("🛒 选好了，生成购物清单", use_container_width=True, type="primary"):
        if not st.session_state.selected_recipes:
            st.warning("请至少选择一道菜！")
        else:
            # 汇总食材
            ingredients_set = set()
            for recipe_id in st.session_state.selected_recipes:
                recipe = next(r for r in RECIPES if r["id"] == recipe_id)
                for ing in recipe["ingredients"]:
                    ingredients_set.add(ing)
            shopping_list = sorted(ingredients_set)

            # 显示购物清单
            st.subheader("📋 你的购物清单")
            st.success(f"共需要 {len(shopping_list)} 种食材")
            # 以网格显示
            cols = st.columns(4)
            for idx, item in enumerate(shopping_list):
                with cols[idx % 4]:
                    st.write(f"• {item}")

            # 额外显示选中菜谱名称（参考）
            with st.expander("📖 查看选中的菜谱"):
                for recipe_id in st.session_state.selected_recipes:
                    recipe = next(r for r in RECIPES if r["id"] == recipe_id)
                    st.write(f"- {recipe['name']}（{recipe['type']}）")

            # 可选：复制按钮（仅文本）
            st.code(", ".join(shopping_list), language="text")

            st.balloons()

# ============================================
# 主路由
# ============================================
def main():
    if st.session_state.mode is None:
        show_home()
    elif st.session_state.mode == "cook":
        show_cook_mode()
    elif st.session_state.mode == "shop":
        show_shop_mode()

if __name__ == "__main__":
    main()
