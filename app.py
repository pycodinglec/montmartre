import streamlit as st
import os
import openai
import io
import base64
from PIL import Image, ImageDraw
import requests
from datetime import datetime
from openai import OpenAI
import httpx

# 페이지 구성
st.set_page_config(
    page_title="Montmartre - AI 이미지 스튜디오",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 스타일 추가
st.markdown("""
<style>
    .main-header {
        font-size: 3em;
        font-weight: bold;
        margin-bottom: 0.5em;
        color: #1E3A8A;
    }
    .sub-header {
        font-size: 1.5em;
        font-weight: 400;
        margin-bottom: 2em;
        color: #6B7280;
    }
    .card {
        padding: 1.5em;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1em;
        background-color: #F9FAFB;
    }
    .image-result {
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
        margin-top: 1em;
    }
    .footer {
        text-align: center;
        margin-top: 3em;
        padding: 1em;
        font-size: 0.8em;
        color: #6B7280;
    }
    .stButton>button {
        width: 100%;
        height: 3em;
        font-weight: bold;
        background-color: #2563EB;
        color: white;
    }
    .stButton>button:hover {
        background-color: #1D4ED8;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 헤더 섹션
st.markdown("<div class='main-header'>Montmartre</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>GPT-image-1 기반 AI 이미지 스튜디오</div>", unsafe_allow_html=True)

# OpenAI 클라이언트 초기화 - 단순화
from openai import OpenAI
client = OpenAI(api_key=st.secrets["api_key"]["openai"])

# 사이드바 설정
with st.sidebar:
    st.markdown("### 🔐 접근 인증")
    password_input = st.text_input("암호 입력", type="password", placeholder="암호를 입력하세요")
    
    # 암호 확인
    try:
        correct_password = st.secrets["password"]["app_password"]
        password_correct = password_input == correct_password
    except KeyError:
        st.error("암호 설정이 올바르지 않습니다. secrets.toml을 확인해주세요.")
        password_correct = False
    
    if password_input and not password_correct:
        st.error("잘못된 암호입니다.")
    
    st.markdown("---")
    
    st.markdown("### ⚙️ 설정")    
    
    st.markdown("---")
    

    
    # 이미지 설정
    st.markdown("### 🖼️ 이미지 설정")
    
    # 품질 선택
    quality = st.select_slider(
        "이미지 품질",
        options=["low", "medium", "high"],
        value="medium",
        help="품질이 높을수록 더 상세한 이미지가 생성되지만 비용이 증가합니다."
    )
    
    # 크기 선택
    size_options = ["1024x1024", "1024x1536", "1536x1024"]
    size = st.select_slider(
        "이미지 크기",
        options=size_options,
        value="1024x1024",
        help="사진 비율을 선택하세요. 정사각형(1:1), 세로(2:3), 가로(3:2)"
    )
    
    # 생성 수량
    n_images = st.slider("생성 수량", 1, 4, 1, help="한 번에 생성할 이미지 수")
    
    # 저장 폴더
    save_dir = "generated_images"
    os.makedirs(save_dir, exist_ok=True)

# 유틸리티 함수
def save_image(image, prompt):
    """이미지 저장 함수"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_prompt = prompt[:20].replace(" ", "_")
    filename = f"{save_dir}/{timestamp}_{short_prompt}.png"
    
    image.save(filename)
    return filename

def display_image_grid(images, captions=None, cols=2):
    """이미지 그리드 표시 함수"""
    rows = (len(images) + cols - 1) // cols
    
    for row in range(rows):
        with st.container():
            columns = st.columns(cols)
            for col in range(cols):
                idx = row * cols + col
                if idx < len(images):
                    with columns[col]:
                        st.image(
                            images[idx], 
                            caption=captions[idx] if captions else None,
                            use_container_width=True,
                            output_format="PNG",
                            clamp=True
                        )
                        
                        # 이미지 다운로드 버튼
                        img_bytes = io.BytesIO()
                        images[idx].save(img_bytes, format="PNG")
                        img_b64 = base64.b64encode(img_bytes.getvalue()).decode()
                        
                        href = f'<a href="data:file/png;base64,{img_b64}" download="image_{idx}.png"><button style="padding: 5px 10px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer;">다운로드</button></a>'
                        st.markdown(href, unsafe_allow_html=True)

def process_openai_image_response(response):
    """OpenAI API 응답에서 이미지 처리"""
    images = []
    
    try:
        if hasattr(response, 'data') and response.data:
            for i, image_data in enumerate(response.data):
                try:
                    # 방법 1: b64_json 속성 확인
                    if hasattr(image_data, 'b64_json') and image_data.b64_json:
                        try:
                            # 성공 메시지 제거
                            img_data = base64.b64decode(image_data.b64_json)
                            img = Image.open(io.BytesIO(img_data))
                            images.append(img)
                            
                            # 이미지 저장
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{save_dir}/{timestamp}_{i+1}.png"
                            img.save(filename)
                            # 저장 메시지 제거
                            continue
                        except Exception as e:
                            st.error(f"b64_json 처리 중 오류: {str(e)}")
                    
                    # 방법 2: url 속성 확인
                    if hasattr(image_data, 'url') and image_data.url:
                        try:
                            # URL 메시지 제거
                            response = requests.get(image_data.url)
                            img = Image.open(io.BytesIO(response.content))
                            images.append(img)
                            
                            # 이미지 저장
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{save_dir}/{timestamp}_{i+1}.png"
                            img.save(filename)
                            # 저장 메시지 제거
                            continue
                        except Exception as e:
                            st.error(f"URL 처리 중 오류: {str(e)}")
                    
                except Exception as e:
                    st.error(f"이미지 {i+1} 처리 중 오류: {str(e)}")
        else:
            st.error("API 응답에서 이미지 데이터를 찾을 수 없습니다.")
    
    except Exception as e:
        st.error(f"응답 처리 중 오류 발생: {str(e)}")
    
    return images

# 암호가 올바른 경우에만 앱 실행
if password_correct:
    # 이미지 생성
    with st.container():
        st.markdown("## 📝 이미지 생성")
        st.markdown("아래에 원하는 이미지에 대한 상세한 프롬프트를 입력하세요.")
        
        with st.form("generation_form"):
            prompt = st.text_area(
                "프롬프트",
                height=100,
                placeholder="예: 세련된 미니멀리스트 스타일의 거실 인테리어, 푸른색 계열, 큰 창문에서 햇빛이 들어오는 모습, 부드러운 가구, 나무 바닥, 8k 해상도",
                help="상세하고 구체적인 프롬프트를 입력할수록 더 좋은 결과를 얻을 수 있습니다."
            )
            
            style_guide = st.text_input(
                "스타일 가이드 (선택사항)",
                placeholder="예: 스튜디오 지브리, 사이버펑크, 팝아트, 유화, 파스텔톤, 사진 현실적, 디지털 아트",
                help="특정 스타일을 적용하려면 여기에 입력하세요."
            )
            
            # 최종 프롬프트 구성
            final_prompt = prompt
            if style_guide:
                final_prompt += f". 스타일: {style_guide}"
            
            generate_button = st.form_submit_button("이미지 생성하기")
        
        if generate_button:
            if not prompt:
                st.error("프롬프트를 입력해주세요!")
            else:
                with st.spinner("이미지를 생성 중입니다..."):
                    try:
                        width, height = map(int, size.split('x'))
                        
                        response = client.images.generate(
                            model="gpt-image-1",
                            prompt=final_prompt,
                            n=n_images,
                            size=f"{width}x{height}",
                            quality=quality
                        )
                        
                        images = process_openai_image_response(response)
                        
                        st.markdown("### 생성된 이미지")
                        display_image_grid(images)
                        
                    except Exception as e:
                        st.error(f"이미지 생성 중 오류가 발생했습니다: {str(e)}")
                        st.error(f"자세한 오류: {repr(e)}")
else:
    if password_input:
        st.warning("올바른 암호를 입력해주세요.")
    else:
        st.info("암호를 입력하면 앱을 사용할 수 있습니다.")

# 푸터
st.markdown("""
<div class="footer">
    <p>Montmartre AI 이미지 스튜디오 - OpenAI GPT-image-1 API 기반</p>
    <p>© 2025 Montmartre</p>
</div>
""", unsafe_allow_html=True)

# 주의사항 및 크레딧
with st.expander("주의사항 및 사용 안내"):
    st.markdown("""
    ### 주의사항
    - 이 애플리케이션은 OpenAI의 GPT-image-1 API를 사용합니다.
    - API 사용에는 비용이 발생합니다. 자세한 가격 정보는 [OpenAI 공식 홈페이지](https://openai.com/pricing)에서 확인하세요.
    - 생성된 이미지는 저작권 관련 법규를 준수하여 사용해주세요.
    - 이미지 품질에 따라 다음과 같은 비용이 대략적으로 발생합니다:
      - 저품질: 약 $0.02/이미지
      - 중간품질: 약 $0.07/이미지
      - 고품질: 약 $0.19/이미지
    
    ### 사용 팁
    - 상세하고 구체적인 프롬프트를 사용할수록 더 좋은 결과를 얻을 수 있습니다.
    - 스타일 가이드를 추가하여 특정 예술 스타일이나 분위기를 지정할 수 있습니다.
    - 고품질 이미지는 더 상세하지만 생성 시간이 길어지고 비용이 더 많이 발생합니다.
    """) 