import streamlit as st
import requests
import json
import markdown

st.set_page_config(page_title="MultA Chat", page_icon="🤖", layout="wide")

# 设置页面样式
st.markdown("""
<style>
    .title {
        font-family: "Microsoft YaHei";
        font-size: 28px;
        font-weight: bold;
        text-align: center;
        color: #4A4A4A;
        margin-bottom: 20px;
    }
    .stTextArea textarea {
        font-family: "Microsoft YaHei";
    }
    div[data-testid="stVerticalBlock"] > div:has(div.stTextArea) {
        position: fixed;
        bottom: 0px;
        left: 0px;
        right: 0px;
        z-index: 999;
        padding: 20px;
    }
    .main-container {
        margin-bottom: 150px;  /* 为底部输入框留出空间 */
    }
    .chat-message {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .chat-message pre {
        background-color: #f6f8fa;
        padding: 10px;
        border-radius: 5px;
        overflow-x: auto;
    }
    .chat-message code {
        font-family: 'Courier New', Courier, monospace;
    }
    /* 移除输入区域的背景色 */
    .stTextArea>div {
        background-color: transparent !important;
    }
    .stButton>button {
        background-color: transparent !important;
    }
    /* Hide divider lines */
    hr {
        display: none !important;
    }
    .block-container {
        padding-bottom: 180px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="title">MultA is a dynamic multi agent system</p>', unsafe_allow_html=True)

# 初始化聊天历史和输入状态
if "messages" not in st.session_state:
    st.session_state.messages = []

if "input_key" not in st.session_state:
    st.session_state.input_key = 0

# 创建主容器
main_container = st.container()

# 创建底部输入区域
input_container = st.container()
with input_container:
    col1, col2 = st.columns([10, 1])
    with col1:
        # 使用动态key来强制重新创建输入框
        user_input = st.text_area(
            "输入您的问题：",
            key=f"user_input_{st.session_state.input_key}",
            height=100,
            label_visibility="collapsed",
            help="支持Markdown格式"
        )
    with col2:
        send_button = st.button("发送", use_container_width=True)

# 显示聊天历史
with main_container:
    for message in st.session_state.messages:
        with st.chat_message(
            message["role"],
            avatar="🧑‍💻" if message["role"] == "user" else "🤖"
        ):
            st.markdown(message["content"], unsafe_allow_html=True)

if send_button and user_input:
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    try:
        # 创建消息占位符
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            full_response = ""
            
            # 发送请求到后端
            response = requests.post(
                "http://localhost:8000/chat",
                json={"query": user_input},
                stream=True,
                headers={'Accept': 'text/event-stream'}
            )
            
            # 流式处理响应
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        if line.strip() == 'data: [DONE]':
                            break
                        try:
                            data = json.loads(line[6:])
                            if 'error' in data:
                                st.error(f"Error: {data['error']}")
                                break
                            new_content = data.get('content', '')
                            full_response += new_content
                            # 使用占位符更新内容
                            message_placeholder.markdown(full_response + "▌")
                        except json.JSONDecodeError:
                            continue
            
            # 完成后移除光标并更新最终内容
            message_placeholder.markdown(full_response)
        
        # 添加到消息历史
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        # 更新input_key来清空输入框
        st.session_state.input_key += 1
        
    except Exception as e:
        st.error(f"连接错误: {str(e)}")

# 保持聊天记录显示在最新位置
if st.session_state.messages:
    st.rerun()