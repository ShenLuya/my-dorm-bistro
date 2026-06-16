# app.py
import streamlit as st
import json
import os
from recipes_data import RECIPES

# ---------- 数据持久化 ----------
FRIDGE_FILE = "fridge.json"


# app.py 修改部分

# 在文件最开头，导入部分之后，添加下面这行
if "fridge" not in st.session_state:
    st.session_state.fridge = []

# 然后删掉原来的 load_fridge 和 save_fridge 函数
# 用下面这两个新函数替换：

def load_fridge():
    """从内存（session_state）加载冰箱数据"""
    return st.session_state.fridge

def save_fridge(items):
    """保存冰箱数据到内存（session_state）"""
    st.session_state.fridge = items


# ---------- 推荐逻辑（模糊匹配 + 部分匹配） ----------
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


# ---------- 初始化 Session 状态 ----------
if "fridge" not in st.session_state:
    st.session_state.fridge = load_fridge()

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
                save_fridge(st.session_state.fridge)
                st.success(f"✅ 已添加 {item}")
                st.rerun()
            else:
                st.warning(f"⚠️ {item} 已经在冰箱里了")
        else:
            st.error("请输入食材名称")

# 显示当前冰箱列表（每个食材带删除按钮，独立显示，不用逗号）
if st.session_state.fridge:
    st.write("📦 当前存有：")
    # 用网格显示，每行4个
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.fridge):
        col_idx = idx % 4
        with cols[col_idx]:
            if st.button(f"❌ {item}", key=f"del_{item}"):
                st.session_state.fridge.remove(item)
                save_fridge(st.session_state.fridge)
                st.rerun()
else:
    st.info("冰箱是空的，快去添加食材吧！")

# 清空按钮
if st.button("🗑️ 清空冰箱"):
    st.session_state.fridge.clear()
    save_fridge(st.session_state.fridge)
    st.rerun()

st.divider()

# ---------- 区域二：推荐菜谱 ----------
st.subheader("🔍 今日推荐")

if st.button("✨ 根据冰箱推荐菜谱", use_container_width=True):
    if not st.session_state.fridge:
        st.warning("冰箱是空的，先添加食材吧！")
    else:
        full, partial = recommend_recipes(st.session_state.fridge)

        # 显示完全匹配
        if full:
            st.success(f"✅ 完全可以做（{len(full)}道）")
            for r in full:
                with st.expander(f"{r['id']} {r['name']}（{r['time_level']}，{r['equipment'][0]}）"):
                    # 用 • 逐行显示食材，不用逗号
                    st.write("📦 需要食材：")
                    for ing in r["ingredients"]:
                        st.write(f"  • {ing}")
                    st.caption(f"类型：{r['type']} | 用时：{r['time_level']}")
        else:
            st.info("😅 没有能完全匹配的菜，看看下面还缺什么吧")

        # 显示部分匹配
        if partial:
            st.warning(f"🔍 差一点点就能做（{len(partial)}道），按缺少数量从少到多排列：")
            for r, missing in partial[:15]:
                with st.expander(f"{r['id']} {r['name']}（缺少 {len(missing)} 样）"):
                    st.write("📦 需要食材：")
                    for ing in r["ingredients"]:
                        # 如果这个食材在缺失列表里，用红色标记
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

# ---------- 侧边栏辅助信息 ----------
with st.sidebar:
    st.header("📋 小贴士")
    st.markdown("""
    - **模糊匹配**：输入“牛肉片”能匹配到需要“牛肉”的菜。
    - **部分推荐**：即使缺食材也会列出，告诉你缺什么。
    - **数据持久化**：关闭页面再打开，冰箱内容还在。
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
    st.caption("数据保存在同目录的 fridge.json")