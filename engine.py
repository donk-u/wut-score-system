import sys
import os
import time  
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase

print(f"当前厨师（Python）的位置: {sys.executable}")

# ==========================================
# 1. 导入必须的“魔法工具”
# ==========================================
from aip import AipOcr
import langchain
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# 导入数据库依赖，用于动态拉取老师设定的规则！
from db.database import SessionLocal
from db.models import CompetitionRule

# ==========================================
# 2. 配置系统的“眼睛” (百度 OCR)
# ==========================================
APP_ID = '7561459'
API_KEY = '74PX6d9ponKJXoFSyz1Irbrd'
SECRET_KEY = 'd0M53m2CsHepeyqVfDUeDIXOpieKPCEO'

client = AipOcr(APP_ID, API_KEY, SECRET_KEY)

def get_ocr_text(image_path):
    """把图片传给百度，换回文字"""
    try:
        if not os.path.exists(image_path):
            return f"❌ 找不到图片呀！请确认 {image_path} 是否和代码在同一个文件夹里。"
            
        with open(image_path, 'rb') as f:
            image_data = f.read()
            
        result = client.basicGeneral(image_data)
        
        if 'words_result' in result:
            words = [item['words'] for item in result['words_result']]
            return "\n".join(words)
        else:
            return "OCR 识别失败，请检查图片是否清晰，或者百度的 API 额度有没有用完。"
    except Exception as e:
        return f"读取图片出错: {e}"

# ==========================================
# 3. 配置系统的“大脑” (DeepSeek AI)
# ==========================================
llm = ChatOpenAI(
    model_name='deepseek-chat', 
    openai_api_key='sk-6a51e9be0e8548c8afb3865d4c12b3e2',  # 你的 DeepSeek 钥匙
    openai_api_base='https://api.deepseek.com',
    temperature=0  # 设为0，让 AI 变严谨，严格遵守规则！
)

# ==========================================
# 4. 🌟 获取动态红头文件 (规则引擎桥梁)
# ==========================================
def get_dynamic_rules():
    """每次 AI 算分前，去数据库拉取老师最新配置的规则"""
    db = SessionLocal()
    try:
        rules = db.query(CompetitionRule).all()
        if not rules:
            return "【注意】当前系统暂无特殊加分规则，请根据常规高校标准酌情给分，无法判断则给 0 分。"
            
        rule_text = "【武理经管学院 - 最新综测加分红头文件】\n请务必严格匹配以下规则算分（如不符合任何一条，加分必须为 0）：\n"
        for r in rules:
            rule_text += f"- 如果是 {r.category}类 赛事，级别为【{r.level}】，等次包含【{r.grade}】，且排在第 {r.position} 作者，那么强制加 {r.score} 分。\n"
        return rule_text
    finally:
        db.close()

# ===================================================================
# 5. Web 全栈专用：“智能证书识别引擎” (结合了动态规则)
# ===================================================================
class WebCertificateInfo(BaseModel):
    student_name: str = Field(description="提取证书上的学生姓名。如果没找到，返回 '未知'")
    award_name: str = Field(description="竞赛或奖项的完整名称")
    award_level: str = Field(description="奖项级别，例如：国家级一等奖、省级银奖等")
    suggested_score: float = Field(description="【最高指令】严格根据系统注入的红头文件规则打分。如果没找到匹配的规则，坚决填 0.0")
    reason: str = Field(description="作为审核员给出算分依据。例如：触发了某条红头文件规则；或未匹配到规则所以给0分。")

web_parser = JsonOutputParser(pydantic_object=WebCertificateInfo)

def ask_ai_to_extract(ocr_text: str) -> dict:
    """接收 OCR 文本，动态注入数据库规则，让大模型严格算分"""
    
    # 🌟 动态注入！把数据库里的规则拿出来！
    current_rules = get_dynamic_rules()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""你是一个极其严谨的高校经管学院 AI 教务审核助手。
你的任务是从杂乱的 OCR 扫描文本中精准提取获奖要素，并进行严格的加分核算。

{current_rules}

严格遵守以下 JSON 格式输出结果：
{{format_instructions}}"""),
        ("user", "这是识别出来的证书文字，请提取信息并严格算分：\n\n{text}")
    ])
    
    chain = prompt | llm | web_parser
    
    try:
        result = chain.invoke({
            "text": ocr_text,
            "format_instructions": web_parser.get_format_instructions()
        })
        return result
    except Exception as e:
        print(f"⚠️ 大模型网页提取失败: {str(e)}")
        return {
            "student_name": "识别异常",
            "award_name": "识别异常",
            "award_level": "未知",
            "suggested_score": 0.0,
            "reason": f"大模型解析失败: {str(e)}"
        }

# ==========================================
# 6. 教务端与学生端的 AI 智能管家
# ==========================================
def ask_teacher_assistant(teacher_name, context, question):
    """教务老师的专属 AI 助理，能读取待审核列表"""
    from langchain_core.messages import HumanMessage, SystemMessage
    system_prompt = f"""你是一个专业、高效的武理经管教务大模型管家。
你现在正在为【{teacher_name}】服务。
以下是当前系统数据库中的待审核队列快照：
{context}

请根据以上数据快照回答老师的问题。如果老师要求寻找异常，请仔细比对分数（比如明显过高的分数）。语气要专业、尊重、高效。"""
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        return llm.invoke(messages).content
    except Exception as e:
        return f"⚠️ 抱歉，AI 助理暂时在开小差：{str(e)}"

def ask_student_assistant(student_name, student_data_str, question):
    """学生端的专属 AI 助理"""
    from langchain_core.messages import HumanMessage, SystemMessage
    system_prompt = f"""你是一个温柔且专业的教务助理。
你现在正在单独为【{student_name}】同学服务。以下是该同学目前的加分档案：
{student_data_str}
请根据以上档案回答问题。若涉及其他同学数据，请委婉拒绝。语气要鼓励、亲切。"""
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question)
        ]
        return llm.invoke(messages).content
    except Exception as e:
        return f"⚠️ 抱歉，AI 助理暂时在开小差：{str(e)}"

# ==========================================
# 7. 数据库对话大脑 (SQL Agent)
# ==========================================
def ask_database(question):
    db_uri = "sqlite:///data/wut_system.db"
    db = SQLDatabase.from_uri(db_uri)
    
    agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True)
    try:
        return agent_executor.invoke({"input": question})["output"]
    except Exception as e:
        return f"⚠️ 大脑在查询数据库时遇到小麻烦：{str(e)}"

if __name__ == "__main__":
    pass