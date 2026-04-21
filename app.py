import streamlit as st
import time
import requests
from streamlit_lottie import st_lottie
import os
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import random

# ==========================================
# 🔐 邮件验证码安全模块
# ==========================================
# ⚠️ 注意：这里要换成你自己的 QQ 邮箱和获取到的 16 位授权码！
SYSTEM_EMAIL = "1762079094@qq.com"  
EMAIL_AUTH_CODE = "rwdmelbxiftcfchh"  

def send_verification_email(target_email, code):
    """调用 QQ 邮箱免费发送验证码"""
    try:
        msg = MIMEText(f"【武汉理工大学经济学院】\n\n亲爱的同学，你好：\n\n您的科研能力分析系统登录验证码为：{code}。\n该验证码在 5 分钟内有效，请勿泄露给他人。\n\n如非本人操作，请忽略此邮件。", 'plain', 'utf-8')
        msg['Subject'] = "经院科研系统 - 登录验证码"
        msg['From'] = SYSTEM_EMAIL
        msg['To'] = target_email

        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(SYSTEM_EMAIL, EMAIL_AUTH_CODE)
        server.sendmail(SYSTEM_EMAIL, [target_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False

def generate_code():
    """生成 6 位随机数字验证码"""
    return str(random.randint(100000, 999999))

# 导入你辛辛苦苦写好的后端引擎！
from engine import get_ocr_text, ai_verify_workflow, calculate_score

# ==========================================
# 1. 页面基本设置与 CSS 动画
# ==========================================
st.set_page_config(page_title="经院科研分析系统", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stDeployButton {display:none;}
    [data-testid="stHeader"] {background-color: transparent;}
    [data-testid="stAppViewBlockContainer"] {
        transition: all 0.3s ease-in-out;
    }
    .st-emotion-cache-16idsys p {
        font-size: 15px;
    }
    button[kind="primary"] {
        transition: all 0.3s ease !important;
    }
    button[kind="primary"]:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(31, 95, 153, 0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

lottie_scanning = load_lottieurl("https://lottie.host/8b4568e6-7871-450f-90e6-b63e9f4a13a4/5X8XjSGB2v.json")
DB_PATH = 'data/wut_system.db'

# ==========================================
# 2. 数据库小助手工具箱 (所有函数必须贴墙站)
# ==========================================
def init_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 创建基础学生表
    cursor.execute('''CREATE TABLE IF NOT EXISTS students 
                      (student_id TEXT PRIMARY KEY, name TEXT, major TEXT)''')
                      
    # ✨ 核心修复：自动给老数据库打补丁，加上 email 这一列！
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN email TEXT")
    except:
        pass # 如果已经有 email 列了，它会自动忽略，绝不报错
        
    # 2. 创建基础记录表
    cursor.execute('''CREATE TABLE IF NOT EXISTS records 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, 
                       contest_name TEXT, award_level TEXT, user_rank INTEGER, 
                       ai_score REAL, status TEXT, image_path TEXT)''')
                       
    # 自动给记录表加上 comment 列
    try:
        cursor.execute("ALTER TABLE records ADD COLUMN comment TEXT")
    except:
        pass 
        
    # 插入一个测试用的张三（规范了列名，防止对不齐）
    cursor.execute("INSERT OR IGNORE INTO students (student_id, name, major) VALUES ('2024001', '张三', '智能经济')")
    
    conn.commit()
    conn.close()

init_db()

def verify_student(student_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id=? AND name=?", (student_id, name))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def get_latest_comment(student_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT status, comment FROM records WHERE student_id=? ORDER BY id DESC LIMIT 1", (student_id,))
    res = cursor.fetchone()
    conn.close()
    return res

def bulk_import_students(df):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    success_count = 0
    for index, row in df.iterrows():
        try:
            stu_id = str(row['学号']).strip()
            name = str(row['姓名']).strip()
            major = str(row.get('专业', '未知')).strip()
            cursor.execute("INSERT OR REPLACE INTO students (student_id, name, major) VALUES (?, ?, ?)", 
                           (stu_id, name, major))
            success_count += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return success_count

def save_application(student_id, contest_name, award_level, user_rank, ai_score, image_path, status, comment=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO records (student_id, contest_name, award_level, user_rank, ai_score, status, image_path, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (student_id, contest_name, award_level, user_rank, ai_score, status, image_path, comment))
    conn.commit()
    conn.close()

def update_record(record_id, new_score, new_status, comment):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE records 
        SET ai_score = ?, status = ?, comment = ? 
        WHERE id = ?
    ''', (new_score, new_status, comment, record_id))
    conn.commit()
    conn.close()

def delete_records(record_ids):
    if not os.path.exists(DB_PATH) or not record_ids: return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(record_ids))
    cursor.execute(f"DELETE FROM records WHERE id IN ({placeholders})", tuple(record_ids))
    conn.commit()
    conn.close()
# ==========================================
# 🔗 账号绑定与查询核心引擎 (三重锁)
# ==========================================

def get_student_by_email(email):
    """【登录用】通过邮箱直接把学号和姓名捞出来"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT student_id, name FROM students WHERE email=?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def bind_student_email(student_id, name, email):
    """【注册用】带三重锁的防盗号绑定引擎"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 第 1 重锁：核对教务处底表，查无此人直接踢回
    cursor.execute("SELECT email FROM students WHERE student_id=? AND name=?", (student_id, name))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return "not_found"
        
    # 第 2 重锁：这个学号是不是已经被别人绑过了？
    if row[0]: 
        conn.close()
        return "already_bound"
        
    # 第 3 重锁：这个邮箱是不是已经被用来绑过其他学号了？
    cursor.execute("SELECT student_id FROM students WHERE email=?", (email,))
    if cursor.fetchone():
        conn.close()
        return "email_used"
        
    # 三重锁全部通过，正式写入数据库！
    cursor.execute("UPDATE students SET email=? WHERE student_id=? AND name=?", (email, student_id, name))
    conn.commit()
    conn.close()
    return "success"

# ==========================================
# 3. 独立刷新结界：审核操作台 (必须贴墙站)
# ==========================================
@st.fragment
def render_audit_form(t_id, t_score, t_status, t_name):
    st.markdown(f"#### ✍️ 正在审核：{t_name}")
    
    with st.container(border=True):
        m1, m2 = st.columns(2)
        m1.metric("AI 建议加分", f"{t_score} 分")
        m2.metric("当前系统状态", t_status)
        
        st.divider()
        
        new_score = st.number_input("💰 最终核定分", min_value=0.0, step=0.1, value=float(t_score), key=f"score_{t_id}")
        
        status_list = ["人工已通过", "人工已驳回", "需补交材料", "AI已通过", "打回需人工核查"]
        status_index = status_list.index(t_status) if t_status in status_list else 0
        new_status = st.selectbox("🏷️ 修改处理结论", status_list, index=status_index, key=f"status_{t_id}")
        
        comment = st.text_area("📝 教务评语 (必填)", placeholder="例如：图片清晰，予以通过...", key=f"comment_{t_id}")
        
        st.write("") 
        
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("🚀 提交结论", type="primary", use_container_width=True, key=f"btn_sub_{t_id}"):
                if new_status in ["人工已驳回", "需补交材料"] and not comment.strip():
                    st.warning("⚠️ 打回或要求补交材料时，必须填写评语哦！")
                else:
                    update_record(t_id, new_score, new_status, comment)
                    st.success("✅ 保存成功！左侧图片并未重新加载。")
        
        with btn_c2:
            if st.button("🗑️ 彻底删除", type="secondary", use_container_width=True, key=f"btn_del_{t_id}"):
                delete_records([t_id])
                st.error("💥 记录已彻底毁灭！")
                time.sleep(1)
                st.rerun()

# ==========================================
# 4. 侧边栏：系统导航
# ==========================================
if os.path.exists("mmexport1774425273356.jpg"):
    st.sidebar.image("mmexport1774425273356.jpg", width=80)

st.sidebar.title("系统导航")
page = st.sidebar.radio("请选择身份入口", ["👨‍🎓 学生提交端", "👨‍🏫 教师审核端 (加密)"])

# ==========================================
# 5. 页面一：学生提交端 (带邮箱安全登录)
# ==========================================
if page == "👨‍🎓 学生提交端":
    st.markdown("<h1 style='text-align: center; color: #1f5f99;'>学生科研能力分析系统</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>武汉理工大学经济学院 · 智能加分引擎</p>", unsafe_allow_html=True)
    st.divider()

    # --- 拦截器：判断是否已经登录 ---
    if 'logged_in_student' not in st.session_state:
        # ========================================
        # 未登录状态：显示现代化的双模登录界面
        # ========================================
        login_col1, login_col2, login_col3 = st.columns([1, 2, 1])
        
        with login_col2:
            st.markdown("### 🎓 经院学术系统统一认证")
            
            # ✨ 核心设计：双标签页区分“老用户”和“新用户”
            login_tab, bind_tab = st.tabs(["📱 快捷登录 (已绑定邮箱)", "🔗 首次激活 (未绑定邮箱)"])
            
            # ----------------------------------------
            # 面板 A：日常快捷登录
            # ----------------------------------------
            with login_tab:
                with st.container(border=True):
                    user_email = st.text_input("📧 登录邮箱", placeholder="输入已绑定的邮箱地址...")
                    
                    if 'v_code' not in st.session_state:
                        st.session_state.v_code = None
                    
                    if st.button("✈️ 获取验证码", use_container_width=True, key="btn_get_code"):
                        if not user_email:
                            st.warning("宝贝，请输入邮箱哦！")
                        else:
                            student_info = get_student_by_email(user_email)
                            if student_info:
                                code = generate_code()
                                st.session_state.v_code = code
                                st.session_state.temp_email = user_email
                                st.session_state.temp_stu_id = student_info[0]
                                st.session_state.temp_name = student_info[1]
                                
                                with st.spinner("正在呼叫邮件机器人发送..."):
                                    if send_verification_email(user_email, code):
                                        st.success(f"✅ 验证码已发送至 {user_email}，请查收！")
                                    else:
                                        st.error("❌ 邮件发送失败，请检查后台设置。")
                            else:
                                st.error("❌ 查无此邮箱！如果是首次使用，请先在旁边【首次激活】绑定账号。")
                    
                    input_code = st.text_input("🔢 6 位动态验证码", max_chars=6)
                    
                    if st.button("🚀 安全登录", type="primary", use_container_width=True, key="btn_login"):
                        if input_code and st.session_state.v_code:
                            if input_code == st.session_state.v_code and user_email == st.session_state.temp_email:
                                st.success("✅ 身份核实完毕！正在进入系统...")
                                st.session_state.logged_in_student = {
                                    "id": st.session_state.temp_stu_id,
                                    "name": st.session_state.temp_name
                                }
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ 验证码不匹配或已失效！")
                        else:
                            st.warning("请先获取并输入验证码！")

            # ----------------------------------------
            # 面板 B：新生首次激活账号
            # ----------------------------------------
            with bind_tab:
                with st.container(border=True):
                    st.info("💡 **新生必读**：首次使用系统需核实验明学号与姓名，并绑定您的个人邮箱。绑定后即可通过邮箱验证码直接登录。")
                    
                    bind_id = st.text_input("👤 学号", placeholder="例如：2024001")
                    bind_name = st.text_input("📝 真实姓名", placeholder="例如：张三")
                    bind_email = st.text_input("📧 欲绑定的邮箱", placeholder="强烈建议使用常用邮箱")
                    
                    if st.button("🔗 验证身份并绑定", type="primary", use_container_width=True):
                        if not all([bind_id, bind_name, bind_email]):
                            st.warning("请将信息填写完整！")
                        elif "@" not in bind_email:
                            st.error("邮箱格式看起来不对哦！")
                        else:
                            result = bind_student_email(bind_id, bind_name, bind_email)
                            
                            if result == "success":
                                st.success(f"🎉 激活成功！{bind_name} 同学，您的账号已与 {bind_email} 绑定。请切换到左侧【快捷登录】进入系统！")
                                st.balloons()
                            elif result == "not_found":
                                st.error("❌ 激活失败：在教务总库中未找到您的学号与姓名匹配记录，请检查是否填错。")
                            elif result == "already_bound":
                                st.error("⚠️ 激活失败：该学号已被其他邮箱激活！如非本人操作，请立即联系辅导员。")
                            elif result == "email_used":
                                st.error("⚠️ 激活失败：该邮箱已被占用，请更换邮箱！")

    else:
        # ========================================
        # 已登录状态：全新的学生个人中心
        # ========================================
        current_student = st.session_state.logged_in_student
        student_id = current_student['id']
        student_name = current_student['name']
        
        # 顶部欢迎横幅
        col_wel, col_exit = st.columns([5, 1])
        with col_wel:
            st.success(f"?? 欢迎来到经院个人学术中心，**{student_name}** 同学 (学号: {student_id})！")
        with col_exit:
            if st.button("?? 安全退出", use_container_width=True):
                del st.session_state.logged_in_student
                st.rerun()
                
        st.write("") 
        
        # 连接数据库，准备捞取个人数据
        conn = sqlite3.connect(DB_PATH)
        
        # ? 核心大招：学生端专属三标签页
        stu_tab1, stu_tab2, stu_tab3 = st.tabs(["?? 提交新申请", "?? 我的加分档案与凭证", "?? 专属 AI 教务助理"])

        # ----------------------------------------
        # 标签页 1：提交申请 (保留你原来优秀的逻辑)
        # ----------------------------------------
        with stu_tab1:
            col_left, col_right = st.columns([1, 1], gap="large")
            with col_left:
                st.subheader("?? 证书提交")
                with st.container(border=True):
                    st.info(f"身份已锁定，将自动记入 **{student_name}** 的档案。")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        contest_category = st.selectbox("申请等级", ["A1", "A2", "B1", "B2", "C类"])
                    with c2:
                        user_rank = st.number_input("自填位次 (例如队长填1)", min_value=1, max_value=10, value=1)
                    
                    uploaded_file = st.file_uploader("点击或拖拽上传证书图片", type=['png', 'jpg', 'jpeg'])

                submit_btn = st.button("? 智能识别并提交申请", type="primary", use_container_width=True)

            with col_right:
                st.subheader("?? 智能分析结果")
                if not submit_btn:
                    st.info("?? 请在左侧上传证书，点击提交后，系统将进行全自动核算并存入数据库。")
                
                if submit_btn:
                    if not uploaded_file:
                        st.error("宝贝，证书图片还没传呢！")
                    else:
                        with st.status("?? 正在建立深度神经网络连接...", expanded=True) as status:
                            if lottie_scanning: st_lottie(lottie_scanning, height=150, key="scan")
                            
                            save_dir = "data/uploads"
                            os.makedirs(save_dir, exist_ok=True)
                            img_path = f"{save_dir}/{student_id}_{int(time.time())}.jpg"
                            with open(img_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            
                            st.write("?? 唤醒 OCR 引擎与大模型进行双重校验...")
                            raw_text = get_ocr_text(img_path)
                            info = ai_verify_workflow(raw_text, student_name, user_rank)
                            
                            if info.get('is_rank_correct'):
                                status.update(label="? AI 核验完成，身份无误！", state="complete", expanded=False)
                                score = calculate_score(contest_category, info.get('award_level', '未知'), user_rank)
                                save_application(student_id, info.get('contest_name', '未知'), info.get('award_level', '未知'), user_rank, score, img_path, "AI已通过", "系统自动核验通过。")
                                
                                m1, m2, m3 = st.columns(3)
                                m1.metric("提取竞赛名称", info.get('contest_name', '未知'))
                                m2.metric("识别获奖等级", info.get('award_level', '未知'))
                                m3.metric("保研综测加分", f"{score} 分")
                                st.balloons()
                            else:
                                status.update(label="?? AI 核验发现异常请求！", state="error", expanded=True)
                                st.error("?? AI 拦截原因：你填写的排名与奖状文字不符！已标记为风险并驳回。")
                                save_application(student_id, info.get('contest_name', '未知'), info.get('award_level', '未知'), user_rank, 0.0, img_path, "打回需人工核查", "AI识别：名单排位与自填不符。")

        # ----------------------------------------
        # 标签页 2：我的加分档案 (表格直观展示 + 查图片)
        # ----------------------------------------
        with stu_tab2:
            st.subheader("??? 个人科研档案库")
            
            # 只捞取这个登录学生的独家数据！
            df_my = pd.read_sql_query('''
                SELECT id as 记录号, contest_name as 竞赛名称, award_level as 级别, 
                       user_rank as 位次, ai_score as 核定分, status as 当前状态, comment as 教务评语, image_path
                FROM records WHERE student_id = ? ORDER BY id DESC
            ''', conn, params=(student_id,))
            
            if not df_my.empty:
                # 1. 顶部炫酷仪表盘
                total_score = df_my['核定分'].sum()
                pass_df = df_my[df_my['当前状态'].str.contains('通过')]
                pass_count = len(pass_df)
                
                dash1, dash2, dash3 = st.columns(3)
                dash1.metric("?? 累计综测加分", f"{total_score:.1f} 分")
                dash2.metric("? 已通过项目数", f"{pass_count} 项")
                dash3.metric("? 待处理/被驳回", f"{len(df_my) - pass_count} 项")
                
                st.divider()
                
                # 2. 隐藏图片路径列，展示干净清爽的表格
                display_df = df_my.drop(columns=['image_path'])
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                st.divider()
                
                # 3. 极其优雅的“证书原件提取器”
                st.markdown("#### ??? 调取证书原件查验")
                records_list = df_my.to_dict('records')
                # 做一个下拉菜单供学生选择看哪一张
                img_options = {f"申请记录 #{r['记录号']} | {r['竞赛名称']} ({r['当前状态']})": r for r in records_list}
                selected_key = st.selectbox("?? 请选择您要查看的证书历史记录：", list(img_options.keys()))
                
                if selected_key:
                    selected_r = img_options[selected_key]
                    img_p = selected_r['image_path']
                    if img_p and os.path.exists(img_p):
                        # 给图片加个好看的边框容器
                        with st.container(border=True):
                            st.image(img_p, caption=f"上传凭证：{selected_r['竞赛名称']} (当时系统核定为: {selected_r['核定分']}分)", width=600)
                    else:
                        st.warning("?? 证书原件可能已被管理员清理或路径丢失。")
            else:
                st.info("您还没有提交过任何加分申请哦，快去隔壁【提交新申请】吧！")

        # ----------------------------------------
        # 标签页 3：专属 AI 助理 (防越权沙盒版)
        # ----------------------------------------
        with stu_tab3:
            st.subheader("?? 专属教务 AI (沙盒模式)")
            st.info("?? 你可以问它：我目前总分多少？哪几项被驳回了？接下来该怎么做？(注：AI无法查看其他同学隐私数据)")
            
            user_question = st.text_input("请向 AI 助理提问：", placeholder="例如：帮我分析一下我为什么有一项被驳回了？")
            
            if st.button("?? 发送给助理", use_container_width=True):
                if user_question:
                    with st.spinner("助理正在调阅您的个人档案..."):
                        try:
                            from engine import ask_student_assistant
                            # 把该学生的 DataFrame 转换成文本，作为上下文喂给大模型
                            if not df_my.empty:
                                personal_data_str = df_my.drop(columns=['image_path']).to_string(index=False)
                            else:
                                personal_data_str = "该同学目前没有任何提交记录。"
                                
                            answer = ask_student_assistant(student_name, personal_data_str, user_question)
                            with st.chat_message("assistant", avatar="??"):
                                st.markdown(answer)
                        except ImportError:
                            st.error("?? 未找到问答模块，请确保 `engine.py` 中已配置 `ask_student_assistant` 函数。")
                else:
                    st.warning("您还没说话呢！")
        
        conn.close() # 记得关闭数据库连接
# ==========================================
# 6. 页面二：教师审核端 (大结局完美版)
# ==========================================
elif page == "👨‍🏫 教师审核端 (加密)":
    st.markdown("## 🛡️ 经济学院科研加分管理后台")
    pwd = st.text_input("请输入管理员密码", type="password")
    
    if pwd == "123456":
        st.success("登录成功！欢迎回来，尊贵的管理员。")
        
        tab1, tab2, tab3 = st.tabs(["📋 审批工作台", "📊 院系数据总览", "🤖 AI 教务大脑"])
        conn = sqlite3.connect(DB_PATH)
        
        # --- Tab 1 ---
        with tab1:
            st.subheader("🛠️ 专家人工复核系统")
            cursor = conn.cursor()
            records_info = cursor.execute('''
                SELECT r.id, s.name, r.contest_name, r.status, r.ai_score, r.image_path, r.student_id 
                FROM records r JOIN students s ON r.student_id = s.student_id 
                ORDER BY r.id DESC
            ''').fetchall()
            
            if not records_info:
                st.info("🎉 院系看板目前非常清爽，暂时没有需要处理的申请。")
            else:
                select_options = {f"#{r[0]} | {r[1]} - {r[2]} ({r[3]})": r for r in records_info}
                selected_label = st.selectbox("🔍 搜索或选择申请记录：", list(select_options.keys()))
                
                selected_r = select_options[selected_label]
                r_id, r_name, r_contest, r_status, r_score, r_img, r_sid = selected_r
                
                st.divider()
                view_col, audit_col = st.columns([1.5, 1], gap="large")
                
                with view_col:
                    st.markdown(f"##### 🖼️ 证书原件核验 ({r_sid})")
                    if r_img and os.path.exists(r_img):
                        st.image(r_img, use_container_width=True, caption=f"竞赛：{r_contest}")
                    else:
                        st.warning("⚠️ 该记录的图片文件已丢失。")
                
                with audit_col:
                    render_audit_form(r_id, r_score, r_status, r_name)
                                
        # --- Tab 2 ---
        with tab2:
            st.subheader("📁 学生花名册批量导入")
            uploaded_excel = st.file_uploader("拖拽或点击上传 Excel (.xlsx) 文件", type=["xlsx", "xls"])
            if uploaded_excel is not None:
                if st.button("🚀 开始批量无感录入", type="primary"):
                    with st.spinner("正在写入数据库..."):
                        try:
                            df = pd.read_excel(uploaded_excel)
                            if '学号' in df.columns and '姓名' in df.columns:
                                imported_count = bulk_import_students(df)
                                st.success(f"✅ 成功导入/更新了 {imported_count} 名学生！")
                                time.sleep(1.5)
                                st.rerun() 
                            else:
                                st.error("⚠️ 表头必须包含『学号』和『姓名』！")
                        except Exception as e:
                            st.error(f"读取失败：{e}")
            
            st.divider()
            
            st.subheader("📋 全院学生加分流水总表")
            df_records = pd.read_sql_query('''
                SELECT r.id as 记录号, s.name as 姓名, s.major as 专业, 
                       r.contest_name as 竞赛名, r.award_level as 等级, 
                       r.user_rank as 排名, r.ai_score as 核定分数, r.status as 状态, r.comment as 教务评语
                FROM records r JOIN students s ON r.student_id = s.student_id
                ORDER BY r.id DESC
            ''', conn)
            
            if not df_records.empty:
                df_records.insert(0, '序号', range(1, len(df_records) + 1))
                st.dataframe(df_records, use_container_width=True, hide_index=True)
                csv = df_records.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 导出公示表", data=csv, file_name="经济学院加分公示表.csv", mime="text/csv")
                
                st.divider()
                with st.expander("⚠️ 危险操作区：批量清理老数据", expanded=False):
                    del_c1, del_c2 = st.columns([3, 1], gap="medium")
                    with del_c1:
                        del_ids_str = st.text_input("请输入要删除的【记录号】", placeholder="例如：1, 3, 5")
                    with del_c2:
                        st.write("")
                        st.write("")
                        if st.button("🗑️ 确认批量摧毁", type="primary"):
                            if del_ids_str:
                                try:
                                    id_list = [int(x.strip()) for x in del_ids_str.split(',') if x.strip().isdigit()]
                                    if id_list:
                                        delete_records(id_list)
                                        st.success(f"✅ 成功摧毁 {len(id_list)} 条记录！")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.warning("请输入有效数字 ID。")
                                except Exception as e:
                                    st.error(f"操作失败：{e}")
                            else:
                                st.warning("请输入要删除的记录号！")
            else:
                st.info("空空如也，暂无数据。")

        # --- Tab 3 ---
        with tab3:
            st.subheader("🧠 数据库智能对话助理")
            user_question = st.text_input("请下达您的查询指令：", placeholder="例如：张三一共加了多少分？")
            if st.button("🔍 唤醒大脑进行分析", use_container_width=True):
                if user_question:
                    with st.spinner("正在生成底层查询逻辑..."):
                        try:
                            from engine import ask_database 
                            answer = ask_database(user_question)
                            with st.chat_message("assistant", avatar="🤖"):
                                st.markdown(f"**分析报告：**\n{answer}")
                        except ImportError:
                            st.error("⚠️ 请确保 engine.py 中已配置 ask_database 函数。")
                else:
                    st.warning("请输入指令！")

        conn.close()
    elif pwd != "":
        st.error("密码错误！")