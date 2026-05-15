"""
Agentic sales qualification workflow — LLM-driven profile extraction,
pain-point discovery, interest alignment, and progressive RAG planning.
"""
import json
from typing import Dict, Any

QUALIFICATION_FIELDS = [
    "project_interest",  # which project / which area?
    "budget",
    "purpose",           # ở / đầu tư / cho thuê
    "area_preference",
    "unit_type",         # 1PN / 2PN / 3PN / shophouse
    "timeline",
    "pain_points",       # what problems are they facing?
    "must_haves",        # non-negotiable requirements
    "deal_breakers",     # what they absolutely don't want
    "family_size",       # how many people
    "financing_method",  # vay ngân hàng / trả thẳng / trả góp CĐT
]

# ------------------------------------------------------------------
# 1. PROFILE EXTRACTION  (after every user message)
# ------------------------------------------------------------------

EXTRACTION_PROMPT = """Bạn là hệ thống trích xuất thông tin khách hàng bất động sản.
Phân tích câu trả lời của khách và trích xuất JSON có cấu trúc.

Các trường (tất cả optional, null nếu không có):
- project_interest: dự án / khu vực quan tâm
- budget: ngân sách (ví dụ: "3-4 tỷ", "dưới 5 tỷ")
- purpose: mục đích (để ở, đầu tư, cho thuê, mua cho con, v.v.)
- area_preference: quận/huyện ưu tiên
- unit_type: loại căn (1PN, 2PN, 3PN, penthouse, shophouse)
- timeline: thời gian dự kiến (ngay, 1 tháng, 6 tháng, v.v.)
- pain_points: vấn đề / bất tiện hiện tại (ví dụ: "nhà cũ chật", "không có chỗ để xe", "xa chỗ làm")
- must_haves: yêu cầu bắt buộc (gần trường học, view hồ, tiện ích đầy đủ)
- deal_breakers: điều tuyệt đối không muốn (nhà cũ, xa trung tâm, thiếu tiện ích)
- family_size: số người ở (cặp vợ chồng, 3 người, 2 thế hệ)
- financing_method: cách thanh toán (trả thẳng, vay ngân hàng, trả góp CĐT)

Quy tắc:
1. Trích xuất MỌI thông tin được đề cập, kể cả ngầm.
2. Phân biệt rõ pain_points (đau đớn hiện tại) vs must_haves (mong muốn tương lai).
3. Trả về JSON thuần túy, không bọc markdown.

Ví dụ:
{{"budget":"3.2-4 tỷ","purpose":"mua để ở","area_preference":"Quận Tây Hồ","unit_type":"2PN","timeline":"trong 3 tháng","pain_points":"nhà đang thuê chật, không có hồ bơi cho con","must_haves":"gần trường học, tiện ích đầy đủ","deal_breakers":"nhà cũ, thiếu chỗ để xe","family_size":"3 người (2 vợ chồng + 1 con nhỏ)","financing_method":"vay ngân hàng 70%","project_interest":"Green Park"}}

Câu khách: {text}
"""


async def extract_profile_with_llm(llm_generate, text: str, existing_profile: dict) -> Dict[str, Any]:
    raw = await llm_generate([
        {"role": "user", "content": EXTRACTION_PROMPT.format(text=text)}
    ])
    extracted = {}
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        extracted = json.loads(cleaned)
    except Exception:
        pass
    merged = dict(existing_profile)
    for key in QUALIFICATION_FIELDS + ["last_intent"]:
        if key in extracted and extracted[key] not in (None, "", "null"):
            merged[key] = extracted[key]
    return merged


# ------------------------------------------------------------------
# 2. PLAN / ASSESSMENT — what is still missing?
# ------------------------------------------------------------------

MISSING_INFO_PROMPT = """Bạn là hệ thống đánh giá profile khách hàng bất động sản.
Dựa trên profile hiện tại, xác định các thông tin CÒN THIẾU quan trọng nhất để tư vấn.

Profile hiện tại:
{profile}

Danh sách thông tin cần thu thập:
{fields}

Quy tắc:
1. Liệt kê các trường chưa có giá trị hoặc giá trị quá mơ hồ.
2. Sắp xếp theo mức độ quan trọng cho việc retrieve dữ liệu phù hợp.
3. Trả về JSON: {{"missing":["field1","field2"],"priority":"field1","reason":"..."}}

Ví dụ:
{{"missing":["budget","purpose","timeline"],"priority":"budget","reason":"Không biết ngân sách thì không thể lọc căn phù hợp"}}
"""


async def assess_missing_info(llm_generate, profile: dict) -> Dict[str, Any]:
    raw = await llm_generate([
        {"role": "user", "content": MISSING_INFO_PROMPT.format(
            profile=json.dumps(profile, ensure_ascii=False, indent=2),
            fields=", ".join(QUALIFICATION_FIELDS),
        )}
    ])
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception:
        # heuristic fallback
        missing = [f for f in QUALIFICATION_FIELDS if f not in profile or not profile[f]]
        return {"missing": missing, "priority": missing[0] if missing else None, "reason": "default fallback"}


# ------------------------------------------------------------------
# 3. DISCOVERY QUESTION — ask ONE targeted question
# ------------------------------------------------------------------

DISCOVERY_PROMPT = """Bạn là trợ lý AI sales bất động sản chuyên nghiệp.
Bạn đang tư vấn khách hàng. Hãy sinh MỘT câu hỏi duy nhất để thu thập thông tin còn thiếu.

Profile hiện tại:
{profile}

Thông tin còn thiếu quan trọng nhất: {priority}
Lý do: {reason}

Lịch sử hội thoại gần nhất:
{history}

Quy tắc:
1. Chỉ 1 câu hỏi, ngắn gọn (< 30 từ), tự nhiên.
2. Không hỏi lại thông tin đã có trong profile.
3. Dùng ngôn ngữ sales thân thiện ("anh/chị", "ạ").
4. Nếu đã đủ thông tin cơ bản (>= 5 trường), hỏi về pain_point hoặc đề xuất xem nhà mẫu.
5. Trả về chỉ câu hỏi, không thêm gì khác.
"""


async def generate_discovery_question_with_llm(llm_generate, profile: dict, history: str, assessment: dict) -> str:
    raw = await llm_generate([
        {"role": "system", "content": DISCOVERY_PROMPT.format(
            profile=json.dumps(profile, ensure_ascii=False, indent=2),
            priority=assessment.get("priority", "thông tin cơ bản"),
            reason=assessment.get("reason", ""),
            history=history,
        )}
    ])
    return raw.strip().strip('"').strip("'")


# ------------------------------------------------------------------
# 4. RAG QUERY BUILDER — once enough context is gathered
# ------------------------------------------------------------------

RAG_QUERY_PROMPT = """Bạn là hệ thống tạo truy vấn RAG cho bất động sản.
Dựa trên profile khách hàng, tạo câu truy vấn tối ưu để tìm kiếm thông tin từ database.

Profile khách:
{profile}

Câu hỏi gốc của khách: {original_query}

Quy tắc:
1. Kết hợp project_interest + unit_type + budget + purpose để tạo query phong phú.
2. Query phải bằng tiếng Việt, chứa các từ khóa dự án + loại căn + tiện ích + chính sách.
3. Trả về chỉ câu truy vấn, không giải thích.

Ví dụ:
Profile: Green Park, 2PN, 3.5 tỷ, mua để ở, gần trường học
Original: "Dự án này có gì?"
→ "Green Park căn hộ 2PN giá 3.5 tỷ tiện ích gần trường học chính sách thanh toán"
"""


async def build_rag_query(llm_generate, profile: dict, original_query: str) -> str:
    raw = await llm_generate([
        {"role": "user", "content": RAG_QUERY_PROMPT.format(
            profile=json.dumps(profile, ensure_ascii=False, indent=2),
            original_query=original_query,
        )}
    ])
    return raw.strip().strip('"').strip("'")
