import streamlit as st
import requests
import base64
import pandas as pd

# 🌍 核心配置：后端 API 地址
STUDENT_API_URL = "http://127.0.0.1:8000/api/v1/students"
TEACHER_API_URL = "http://127.0.0.1:8000/api/v1/teachers"

# 暂且模拟当前登录学号
CURRENT_STUDENT_ID = "2024001" 

st.set_page_config(page_title="经院科研加分系统", page_icon="🎓", layout="wide")

# ==========================================
# 🔐 侧边栏：角色权限控制中心
# ==========================================
with st.sidebar:
    st.title("⚙️ 系统控制台")
    st.caption("SaaS 微服务架构展示")
    st.divider()
    
    # 核心：身份切换器
    role = st.radio(
        "请选择您的系统角色：",
        ["👨‍🎓 学生端 (申请与查询)", "👩‍🏫 教师端 (审批工作台)"],
        index=0
    )
    
    st.divider()
    st.info("💡 提示：在真实环境中，这里将通过教务处统一身份认证 (SSO) 自动分配权限，无需手动切换。")


# ==========================================
# 🧑‍🎓 视界 A：学生端界面 (保持你最爱的原汁原味排版)
# ==========================================
if role == "👨‍🎓 学生端 (申请与查询)":
    st.title("👨‍🎓 学生个人学术中心")
    st.success(f"👋 欢迎回来，张三 同学 (学号: {CURRENT_STUDENT_ID})！")

    tab1, tab2 = st.tabs(["📤 提交新申请", "📊 我的加分档案"])

    # --- 标签页 1：提交申请 ---
    with tab1:
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                contest_name = st.text_input("竞赛名称", placeholder="例如：全国大学生数学建模竞赛")
            with col2:
                award_level = st.selectbox("获奖等级", ["国家级一等奖", "国家级二等奖", "省级一等奖", "C类参与奖"])

            user_rank = st.number_input("自填位次", min_value=1, max_value=10, value=1)
            uploaded_file = st.file_uploader("上传证书图片", type=['png', 'jpg', 'jpeg'])

        if st.button("✨ 提交至后端数据工厂", type="primary", use_container_width=True):
            if not contest_name or not uploaded_file:
                st.warning("请完整填写并上传图片！")
            else:
                with st.status("🚀 正在呼叫后端 API...", expanded=True) as status:
                    img_bytes = uploaded_file.getvalue()
                    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                    
                    payload = {
                        "contest_name": contest_name,
                        "award_level": award_level,
                        "user_rank": user_rank,
                        "image_base64": img_base64[:50] + "..."
                    }
                    try:
                        response = requests.post(f"{STUDENT_API_URL}/apply", json=payload)
                        if response.status_code == 200:
                            status.update(label="✅ 处理成功！", state="complete")
                            st.success(f"🎉 提交成功！AI核定加分：{response.json()['ai_score']} 分。请等待教师复核。")
                        else:
                            st.error(f"❌ 提交失败: {response.text}")
                    except Exception as e:
                        st.error("无法连接后端服务器！")

    # --- 标签页 2：历史档案查询 ---
    with tab2:
        st.subheader("🗂️ 个人科研档案库")
        if st.button("🔄 刷新我的数据"):
            with st.spinner("正在向后端请求数据..."):
                try:
                    res = requests.get(f"{STUDENT_API_URL}/{CURRENT_STUDENT_ID}/records")
                    if res.status_code == 200:
                        records_data = res.json()
                        if len(records_data) > 0:
                            df = pd.DataFrame(records_data)
                            display_df = df[['id', 'contest_name', 'award_level', 'ai_score', 'status', 'comment', 'created_at']]
                            display_df.columns = ['流水号', '竞赛名称', '获奖等级', '加分', '当前状态', '系统评语', '提交时间']
                            
                            st.metric("💰 累计获取综测加分", f"{df[df['status'] == '已通过']['ai_score'].sum()} 分", help="仅计算已通过的申请")
                            st.dataframe(display_df, use_container_width=True, hide_index=True)
                        else:
                            st.info("您还没有提交过任何加分申请哦！")
                except Exception as e:
                    st.error("无法连接后端服务器！")


# ==========================================
# 👩‍🏫 视界 B：教师端界面 (极简卡片流审批)
# ==========================================
elif role == "👩‍🏫 教师端 (审批工作台)":
    st.title("👩‍🏫 教务审批工作台")
    st.caption("🚀 正在监听全院学生的加分申请...")
    
    # 自动获取待办数据
    try:
        res = requests.get(f"{TEACHER_API_URL}/pending")
        if res.status_code == 200:
            pending_records = res.json()
            
            if len(pending_records) == 0:
                st.success("🎉 太棒了！当前没有任何待审批的申请。您可以喝杯咖啡休息一下！☕")
            else:
                st.warning(f"🔔 您有 {len(pending_records)} 条待审批记录，请及时处理。")
                
                # 使用你最爱的 container 画出优雅的审批卡片流
                for record in pending_records:
                    with st.container(border=True):
                        # 卡片头部信息
                        cols = st.columns([3, 1, 1, 1])
                        cols[0].subheader(f"📄 {record['contest_name']}")
                        cols[1].metric("学生学号", record['student_id'])
                        cols[2].metric("申报排位", f"第 {record['user_rank']} 名")
                        cols[3].metric("AI 建议加分", f"{record['ai_score']} 分")
                        
                        st.markdown(f"**🏅 奖项级别：** `{record['award_level']}`")
                        st.info(f"**🤖 AI 审查意见：** {record['comment']}")
                        
                        st.divider()
                        
                        # 教师操作区
                        feedback = st.text_input("📝 教师补充意见 (选填)", key=f"fb_{record['id']}", placeholder="如果有驳回理由，请在此填写...")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("✅ 批准该申请 (Approve)", key=f"btn_approve_{record['id']}", use_container_width=True, type="primary"):
                                payload = {"action": "approve", "feedback": feedback}
                                # 呼叫后端审批接口
                                requests.post(f"{TEACHER_API_URL}/{record['id']}/review", json=payload)
                                st.rerun() # 神奇的魔法：处理完立刻刷新网页，卡片瞬间消失！
                                
                        with col_btn2:
                            if st.button("❌ 驳回该申请 (Reject)", key=f"btn_reject_{record['id']}", use_container_width=True):
                                payload = {"action": "reject", "feedback": feedback}
                                requests.post(f"{TEACHER_API_URL}/{record['id']}/review", json=payload)
                                st.rerun() # 刷新网页

    except Exception as e:
         st.error("无法连接后端服务器！请确保 backend_main.py (8000端口) 正在运行。")
# ==========================================
    # 🌟 新增：教务数据管理中心
    # ==========================================
    st.divider()
    st.subheader("🛠️ 教务数据管理中心")
    
    col_import, col_export = st.columns(2)
    
    # 模块 1：一键导入学生
    with col_import:
        with st.expander("📥 一键导入学生名单 (Excel)", expanded=True):
            st.info("💡 请确保表头包含：**学号、姓名、专业、邮箱**")
            uploaded_student_file = st.file_uploader("拖拽或点击上传 Excel 文件", type=['xlsx', 'xls'])
            
            if st.button("🚀 开始批量导入", use_container_width=True, type="primary"):
                if uploaded_student_file:
                    with st.spinner("系统正在高速解析并写入数据库..."):
                        try:
                            # 极其关键：用 requests 上传文件的标准姿势
                            files = {"file": (uploaded_student_file.name, uploaded_student_file.getvalue())}
                            res = requests.post(f"{TEACHER_API_URL}/import/students", files=files)
                            
                            if res.status_code == 200:
                                data = res.json()
                                st.success(f"🎉 导入大成功！新增 `{data['success_count']}` 名学生，跳过已存在 `{data['skip_count']}` 名。")
                            else:
                                st.error(f"❌ 导入失败: {res.json().get('detail')}")
                        except Exception as e:
                            st.error("无法连接后端服务器！")
                else:
                    st.warning("⚠️ 老师，您还没上传文件呢！")

    # 模块 2：一键导出申请档案
    with col_export:
        with st.expander("📤 一键导出加分档案 (Excel)", expanded=True):
            st.success("💡 导出全院所有学生的加分申请记录，用于期末归档。")
            # 这是一个极其巧妙的写法：Streamlit 允许我们直接放一个超链接按钮去访问 GET 接口下载文件
            st.link_button("📊 点击下载《全院加分统计表.xlsx》", f"{TEACHER_API_URL}/export/excel", use_container_width=True)