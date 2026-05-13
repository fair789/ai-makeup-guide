"""
AI メイク分析ガイド
==================
【セットアップ手順】
1. pip install -r requirements.txt
2. APIキーを環境変数に設定:
   export ANTHROPIC_API_KEY="sk-ant-xxxxxxxx"
   (または起動後にサイドバーで入力可能)
3. streamlit run app.py
"""

import os
import io
import json
import math
import random
import hashlib
import datetime
import base64 as b64

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import anthropic

MODEL  = "claude-sonnet-4-6"
TODAY  = datetime.date.today().strftime("%Y.%m.%d")

# ── カラーパレット（Python 定数）
C_ACCENT  = "#C4887A"   # メインアクセント（ミューズドローズ）
C_LIGHT   = "#EDD5C5"   # 淡いピーチ（バッジ・ボーダー）
C_BG      = "#FAF0EC"   # 温かみクリーム（背景）
C_CARD    = "#FFFAF8"   # カード背景
C_TEXT    = "#5C4040"   # 文字（ウォームダーク）
C_SUB     = "#9C7A7A"   # サブテキスト

st.set_page_config(
    page_title="AI メイク分析ガイド",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ==================== CSS ====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600&family=Noto+Serif+JP:wght@400;700&family=Noto+Sans+JP:wght@400;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
}
.stApp { background-color: #FAF0EC; color: #5C4040; }

/* ===== マガジンヘッダー ===== */
.mag-header { text-align: center; padding: 1.4rem 1rem 1rem; margin-bottom: 0.5rem; }
.mag-deco   { font-size: 0.78rem; color: #C4887A; letter-spacing: 0.4em; }
.mag-title  {
    font-family: 'Noto Serif JP', serif;
    font-size: 2.1rem; font-weight: 700;
    color: #5C4040; letter-spacing: 0.08em; margin: 0.2rem 0 0;
}
.mag-sub-jp {
    font-family: 'Noto Serif JP', serif;
    font-size: 0.78rem; color: #9C7A7A;
    border: 1px solid #EDD5C5;
    display: inline-block;
    padding: 0.15rem 1.2rem;
    margin: 0.3rem 0;
    letter-spacing: 0.15em;
}
.mag-sub-en {
    font-family: 'Dancing Script', cursive;
    font-size: 1.05rem; color: #C4887A;
    display: block; margin-top: 0.2rem;
}
.mag-divider {
    display: flex; align-items: center; gap: 0.6rem;
    margin: 0.5rem auto; max-width: 240px;
}
.mag-divider::before, .mag-divider::after {
    content: ''; flex: 1; height: 1px; background: #D8BAA8;
}
.mag-divider span { font-size: 0.7rem; color: #C4887A; }
.diag-line { font-family: monospace; font-size: 0.66rem; color: #C4C4C4; text-align: center; }

/* ===== セクションバッジ ===== */
.sec-badge {
    display: inline-block; background: #EDD5C5; color: #8C6060;
    font-size: 0.68rem; font-weight: 700;
    padding: 0.18rem 0.75rem; border-radius: 20px; letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
}

/* ===== 汎用カード ===== */
.mag-card {
    background: #FFFAF8; border: 1px solid #EDD5C5;
    border-radius: 10px; padding: 1rem 1.2rem; margin: 0.5rem 0;
}

/* ===== キャッチコピー ===== */
.catch-wrap { padding: 0.5rem 0 0.8rem; }
.catch-text {
    font-family: 'Noto Serif JP', serif;
    font-size: 1.0rem; color: #5C4040;
    line-height: 1.9; font-weight: 700;
}

/* ===== POINT セクション ===== */
.point-box {
    background: #FFFAF8; border: 1px solid #EDD5C5;
    border-radius: 8px; padding: 0.7rem 1rem; margin-top: 0.6rem;
}
.point-title { font-size: 0.68rem; font-weight: 700; color: #C4887A; letter-spacing: 0.2em; margin-bottom: 0.4rem; }
.point-item { font-size: 0.82rem; color: #5C4040; margin: 0.25rem 0; line-height: 1.5; }
.point-item::before { content: '☑ '; color: #C4887A; }

/* ===== EYE / CHEEK / LIP カード ===== */
.part-card {
    background: #FFFAF8; border: 1px solid #EDD5C5;
    border-radius: 10px; padding: 0.85rem 1rem;
    margin-bottom: 0.55rem;
}
.part-label {
    font-size: 0.66rem; font-weight: 700;
    letter-spacing: 0.25em; color: #C4887A;
    border-bottom: 1px solid #EDD5C5;
    padding-bottom: 0.3rem; margin-bottom: 0.45rem;
}
.part-title { font-family: 'Noto Serif JP', serif; font-size: 0.88rem; color: #5C4040; margin-bottom: 0.4rem; }
.part-point { font-size: 0.78rem; color: #5C4040; margin: 0.22rem 0; line-height: 1.5; }
.part-point::before { content: '☑ '; color: #C4887A; }
.part-colors { font-size: 0.72rem; color: #9C7A7A; margin-top: 0.45rem; }
.color-label { font-size: 0.65rem; color: #C4887A; font-weight: 700; letter-spacing: 0.1em; }

/* ===== スコアミニカード ===== */
.score-mini {
    background: #FFFAF8; border: 1px solid #EDD5C5;
    border-radius: 10px; padding: 1rem 1.2rem;
    text-align: center; margin: 0.8rem 0;
}
.score-big-warm {
    font-family: 'Noto Serif JP', serif;
    font-size: 4.5rem; font-weight: 700;
    color: #C4887A; line-height: 1;
}
.score-sub { font-size: 0.78rem; color: #9C7A7A; }
.score-bar-bg { background: #F0DDD5; border-radius: 5px; height: 10px; margin: 0.8rem 0 0.5rem; overflow: hidden; }
.score-bar-fg { height: 100%; border-radius: 5px; background: linear-gradient(90deg, #DEB8A8, #C4887A); }
.type-badge {
    display: inline-block;
    background: #EDD5C5; color: #8C6060;
    font-size: 0.8rem; font-weight: 700;
    padding: 0.25rem 1rem; border-radius: 20px; margin-top: 0.4rem;
}

/* ===== パーソナルカラー ===== */
.pc-type {
    font-family: 'Noto Serif JP', serif;
    font-size: 2rem; font-weight: 700; color: #5C4040;
    line-height: 1; margin: 0.3rem 0;
}
.pc-desc { font-size: 0.78rem; color: #9C7A7A; line-height: 1.6; margin-top: 0.5rem; }

/* ===== 魅力と印象 ===== */
.appeal-row { display: flex; gap: 0.55rem; margin: 0.5rem 0; align-items: flex-start; }
.appeal-tag {
    background: #EDD5C5; color: #8C6060;
    font-size: 0.68rem; font-weight: 700;
    padding: 0.2rem 0.5rem; border-radius: 4px;
    flex-shrink: 0; white-space: nowrap; margin-top: 2px;
}
.appeal-text { font-size: 0.82rem; color: #5C4040; line-height: 1.55; }

/* ===== スタイル ===== */
.style-row { display: flex; gap: 0.6rem; margin: 0.4rem 0; align-items: baseline; }
.style-tag {
    background: #EDD5C5; color: #8C6060;
    font-size: 0.65rem; font-weight: 700;
    padding: 0.15rem 0.5rem; border-radius: 4px;
    flex-shrink: 0;
}
.style-val { font-size: 0.82rem; color: #5C4040; }

/* ===== 長所 / 改善点 ===== */
.list-item { display: flex; gap: 0.5rem; margin: 0.4rem 0; align-items: flex-start; }
.badge-solid {
    background: #C4887A; color: #fff;
    font-size: 0.62rem; font-weight: 700;
    min-width: 18px; height: 18px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 2px;
}
.badge-outline {
    background: #FFFAF8; border: 1px solid #C4887A; color: #C4887A;
    font-size: 0.62rem; font-weight: 700;
    min-width: 18px; height: 18px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 2px;
}
.list-text { font-size: 0.84rem; color: #5C4040; line-height: 1.6; }

/* ===== 美容プラン ===== */
.plan-card { background: #FFFAF8; border: 1px solid #EDD5C5; border-radius: 8px; padding: 0.85rem; }
.plan-badge {
    display: inline-block; font-size: 0.62rem; font-weight: 700;
    padding: 0.15rem 0.5rem; border-radius: 4px; margin-bottom: 0.4rem;
}
.pl-light { background: #F5E8E0; color: #C4887A; }
.pl-skin  { background: #E0E8F5; color: #5878C4; }
.pl-adv   { background: #ECE0F5; color: #8858C4; }
.plan-body { font-size: 0.78rem; color: #5C4040; line-height: 1.65; }

/* ===== 予想スコア ===== */
.predicted-card {
    background: linear-gradient(135deg, #C4887A, #DEB8A8);
    border-radius: 12px; padding: 1.4rem; text-align: center; color: #fff; margin: 1rem 0;
}
.pred-score { font-family: 'Noto Serif JP', serif; font-size: 3.8rem; font-weight: 700; line-height: 1; }
.pred-delta { font-size: 1.1rem; font-weight: 700; opacity: 0.9; margin-top: 0.2rem; }
.pred-label { font-size: 0.78rem; opacity: 0.85; }
.closing-msg { font-style: italic; font-size: 0.85rem; opacity: 0.95; margin-top: 0.8rem; line-height: 1.65; }

/* ===== シェア ===== */
.share-row { display: flex; gap: 10px; margin-top: 0.8rem; }
.share-btn {
    flex: 1; display: block; text-align: center;
    padding: 0.7rem; border-radius: 8px; font-weight: 700;
    font-size: 0.85rem; text-decoration: none;
}
.btn-x    { background: #1A1A1A; color: #fff; }
.btn-line { background: #06C755; color: #fff; }

/* ===== Streamlit ボタン ===== */
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #C4887A, #DEB8A8);
    color: #fff; font-weight: 900; font-size: 1.05rem; border: none; border-radius: 8px;
}
[data-testid="stFileUploader"] {
    border: 2px dashed #EDD5C5; border-radius: 12px; background: #FFFAF8;
}
.disclaimer {
    font-size: 0.68rem; color: #CCC; text-align: center;
    margin-top: 2rem; padding: 0.8rem; border-top: 1px solid #EDD5C5;
}
</style>
""", unsafe_allow_html=True)


# ==================== 顔検出（存在確認のみ） ====================

def has_face(pil_image: Image.Image) -> bool:
    img = np.array(pil_image.convert("RGB"))
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return len(cascade.detectMultiScale(gray, 1.05, 3, minSize=(60, 60))) > 0


# ==================== Claude API ====================

SYSTEM_PROMPT = """あなたは忖度なしの美容分析官兼美容外科ドクターです。
添付した顔写真を元にして「顔面偏差値カルテ」を作成してください。

必ず以下のJSON形式のみで返してください（他のテキスト・説明は一切不要）:
{
  "deviation_score": 顔面偏差値（整数、20〜85、全国平均50）,
  "overall_comment": "辛口だけど愛がある刺さる系の一言レビュー（例:完成度は高い。あとは垢抜けの起爆剤待ち。）",
  "face_type": "顔タイプ診断（ソフトエレガント／クール／フェミニン／クールカジュアル／フレッシュ等）",
  "catchphrase": "この人のための印象コピー（例:透明感×柔らかさでつくる、儚げフェミニン）",
  "key_points": ["POINT1（20字以内）", "POINT2（20字以内）", "POINT3（20字以内）"],
  "personal_color": "パーソナルカラータイプ（ブルベ夏／イエベ春／イエベ秋／ブルベ冬）",
  "personal_color_palette": ["#hex1", "#hex2", "#hex3", "#hex4", "#hex5", "#hex6"],
  "personal_color_desc": "パーソナルカラーの特徴説明（2文以内）",
  "appeal": {
    "transparency": 透明感（1〜5整数）,
    "softness": 柔らかさ（1〜5整数）,
    "femininity": 女性らしさ（1〜5整数）,
    "glamour": 華やかさ（1〜5整数）,
    "elegance": 清楚さ（1〜5整数）
  },
  "appeal_points": [
    {"tag": "キーワード（4字以内）", "description": "説明（30字以内）"},
    {"tag": "キーワード2", "description": "説明2"},
    {"tag": "キーワード3", "description": "説明3"}
  ],
  "eye_makeup": {
    "title": "目もとの印象コピー（15字以内）",
    "colors": ["カラー名1", "カラー名2", "カラー名3"],
    "points": ["テクニック1", "テクニック2", "テクニック3"]
  },
  "cheek_makeup": {
    "title": "チークの印象コピー（15字以内）",
    "colors": ["カラー名1", "カラー名2", "カラー名3"],
    "points": ["テクニック1", "テクニック2", "テクニック3"]
  },
  "lip_makeup": {
    "title": "リップの印象コピー（15字以内）",
    "colors": ["カラー名1", "カラー名2", "カラー名3"],
    "points": ["テクニック1", "テクニック2", "テクニック3"]
  },
  "style": {
    "makeup": "おすすめメイクスタイル",
    "fashion": "おすすめファッション",
    "hair": "おすすめヘアスタイル"
  },
  "parts": {
    "eyes": 目力（1〜5整数）,
    "nose": 鼻筋（1〜5整数）,
    "mouth": 口元（1〜5整数）,
    "contour": 輪郭（1〜5整数）,
    "skin": 肌印象（1〜5整数）,
    "balance": 顔バランス（1〜5整数）
  },
  "strengths": ["長所1（具体的な解説）", "長所2", "長所3"],
  "improvements": ["垢抜けポイント1（辛口）", "改善点2", "改善点3"],
  "beauty_plan": {
    "light": "ライト美容プランと理由",
    "skin": "肌管理・美容医療プランと理由",
    "advanced": "本格アップデート枠と理由"
  },
  "predicted_score": 垢抜け後の予想偏差値（整数）,
  "score_increase": スコアアップ幅（整数）,
  "closing": "前向きな締めメッセージ（変われそうと思える内容）"
}

【トーン指定】
・辛口だけど、人格否定はしないこと
・"ダメ出し"ではなく"伸びしろ分析"として表現すること
・最後は「変われそう」と思える前向きな締めで終えること"""


def _img_to_b64(pil_image: Image.Image) -> str:
    buf = io.BytesIO()
    pil_image.convert("RGB").save(buf, format="JPEG", quality=85)
    return b64.b64encode(buf.getvalue()).decode()


def _img_data_url(pil_image: Image.Image, max_w: int = 800) -> str:
    img = pil_image.copy()
    if img.width > max_w:
        img.thumbnail((max_w, max_w * 2))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=80)
    return "data:image/jpeg;base64," + b64.b64encode(buf.getvalue()).decode()


def get_karte(pil_image: Image.Image, api_key: str) -> dict:
    if not api_key:
        return _fallback_karte()
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _img_to_b64(pil_image)}},
                    {"type": "text", "text": "この顔写真をもとに、顔面偏差値カルテをJSONで作成してください。"},
                ],
            }],
        )
        text = response.content[0].text
        s, e = text.find("{"), text.rfind("}") + 1
        if s != -1 and e > s:
            return json.loads(text[s:e])
    except Exception as ex:
        st.warning(f"AI分析に失敗しました（フォールバック使用）: {ex}")
    return _fallback_karte()


def _fallback_karte() -> dict:
    return {
        "deviation_score": 55,
        "overall_comment": "ポテンシャルは確かにある。あとは磨き方次第で化ける一枚。",
        "face_type": "ソフトエレガント",
        "catchphrase": "透明感×柔らかさでつくる、儚げフェミニン",
        "key_points": ["うるみ感で透明感UP", "ピンクベージュでやさしい印象に", "涙袋で自然な立体感をプラス"],
        "personal_color": "ブルベ夏",
        "personal_color_palette": ["#E8D5E0", "#C4A8B8", "#A890A8", "#7A6080", "#B8D0D8", "#90B0C0"],
        "personal_color_desc": "透明感のあるソフトな色味が得意。淡くくすみのあるカラーでやさしい印象に。",
        "appeal": {"transparency": 4, "softness": 5, "femininity": 4, "glamour": 3, "elegance": 4},
        "appeal_points": [
            {"tag": "透明感", "description": "透き通るような自肌とうるんだ瞳が魅力"},
            {"tag": "柔らかさ", "description": "優しい雰囲気で親しみやすい印象"},
            {"tag": "女性らしさ", "description": "フェミニンなパーツバランスで愛され顔に"},
        ],
        "eye_makeup": {
            "title": "やわらかくナチュラルに盛る",
            "colors": ["ピンクベージュ", "ラベンダーベージュ", "シャンパンベージュ"],
            "points": ["まぶたに自然な奥行きを", "涙袋は細めに、うるみを演出", "まつ毛はカールキープで縦幅を強調"],
        },
        "cheek_makeup": {
            "title": "ふんわり血色感を仕込む",
            "colors": ["ライラックピンク", "ベビーピンク", "シアーピンク"],
            "points": ["高めの位置にふんわりと", "青みピンクで透明感を底上げ", "ハイライトでツヤと立体感を"],
        },
        "lip_makeup": {
            "title": "うるっと自然に血色をプラス",
            "colors": ["ローズピンク", "モーヴピンク", "コーラルピンク"],
            "points": ["粘膜カラーで自然な血色感", "ツヤでうるみをプラス", "輪郭はぼかして柔らかく"],
        },
        "style": {"makeup": "ツヤ・シアー・透明感重視", "fashion": "柔らかい素材・フリル・レース", "hair": "ゆる巻き・シースルーバング"},
        "parts": {"eyes": 4, "nose": 3, "mouth": 4, "contour": 3, "skin": 4, "balance": 3},
        "strengths": [
            "自然な親しみやすさ：初対面でも警戒されない好感度の高い顔立ち。",
            "うるんだ瞳：ハイライトを仕込むだけで一気に印象が変わる伸びしろがある。",
            "バランス型：スタイリング次第で多彩な印象を演出できる可能性を秘めている。",
        ],
        "improvements": [
            "眉毛の設計：形を整えるだけで顔の骨格感が一段変わる。今すぐできる最大の投資。",
            "肌の均一感：くすみや毛穴が印象を下げている。スキンケアの見直しで偏差値+5は堅い。",
            "フェイスラインのシャープ化：小顔効果を狙うだけで全体の完成度が跳ね上がる。",
        ],
        "beauty_plan": {
            "light": "ボトックス（エラ）＋ヒアルロン酸（鼻根・顎先）→ 小顔と立体感を最短で手に入れる。",
            "skin": "ハイフ＋ピーリング定期施術 → たるみ予防＆肌質改善で土台から整える。",
            "advanced": "鼻筋プロテーゼ → 顔の縦ラインが強化され全体のバランスが激変する。",
        },
        "predicted_score": 63,
        "score_increase": 8,
        "closing": "やることは決まった。あとは動くだけ。3ヶ月後の自分が今より確実に好きになれる。",
    }


# ==================== SVG ヘルパー ====================

def _pentagon_svg(appeal: dict, size: int = 180) -> str:
    """魅力チャート（5軸ペンタゴン）"""
    keys   = ["transparency", "softness", "femininity", "glamour", "elegance"]
    labels = ["透明感", "柔らかさ", "女性らしさ", "華やかさ", "清楚さ"]
    n = 5
    cx = cy = size / 2
    r  = size / 2 - 30

    def pt(lv, i):
        a = i * 2 * math.pi / n - math.pi / 2
        return cx + r * lv / 5 * math.cos(a), cy + r * lv / 5 * math.sin(a)

    buf = [f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">']
    for lv in range(1, 6):
        pts = " ".join(f"{pt(lv, i)[0]:.1f},{pt(lv, i)[1]:.1f}" for i in range(n))
        buf.append(f'<polygon points="{pts}" fill="none" stroke="#EDD5C5" stroke-width="0.8"/>')
    for i in range(n):
        x5, y5 = pt(5, i)
        buf.append(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{x5:.1f}" y2="{y5:.1f}" stroke="#EDD5C5" stroke-width="0.8"/>')
    data = []
    for i, k in enumerate(keys):
        v = min(5, max(1, appeal.get(k, 3)))
        data.append(pt(v, i))
    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in data)
    buf.append(f'<polygon points="{pts_str}" fill="rgba(196,136,122,0.22)" stroke="#C4887A" stroke-width="2"/>')
    for x, y in data:
        buf.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#C4887A"/>')
    for i, lb in enumerate(labels):
        lx, ly = pt(5.9, i)
        buf.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="9.5" fill="#9C7A7A" font-family="sans-serif">{lb}</text>')
    buf.append('</svg>')
    return "".join(buf)


def _swatches_html(colors: list) -> str:
    dots = "".join(
        f'<div style="width:26px;height:26px;border-radius:50%;background:{c};border:2px solid rgba(0,0,0,0.07);display:inline-block;margin:3px 4px;vertical-align:middle"></div>'
        for c in colors
    )
    return f'<div style="margin-top:0.5rem">{dots}</div>'


# ==================== シェア画像生成 ====================

def _load_font(size: int) -> ImageFont.ImageFont:
    for path in [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap(draw, text, x, y, font, fill, max_w, anchor="mm", max_lines=3):
    line, lines = "", []
    for ch in text:
        if draw.textbbox((0, 0), line + ch, font=font)[2] > max_w and line:
            lines.append(line); line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    lh = (font.size if hasattr(font, "size") else 18) + 6
    for i, ln in enumerate(lines[:max_lines]):
        draw.text((x, y + i * lh), ln, fill=fill, font=font, anchor=anchor)


def generate_share_image(pil_image: Image.Image, karte: dict, diag_no: int) -> Image.Image:
    """Instagram Stories (1080×1920) マガジン風シェア画像。ウォームクリーム＋ローズ。"""
    W, H = 1080, 1920
    BG    = (250, 240, 236)   # cream
    ROSE  = (196, 136, 122)   # muted rose
    LIGHT = (237, 213, 197)   # peach border
    WHITE = (255, 250, 248)
    TEXT  = (92, 64, 64)
    GRAY  = (156, 122, 122)

    canvas = Image.new("RGB", (W, H), BG)
    draw   = ImageDraw.Draw(canvas)

    f80 = _load_font(80); f60 = _load_font(60); f44 = _load_font(44)
    f34 = _load_font(34); f26 = _load_font(26); f20 = _load_font(20)

    # ヘッダー
    draw.rectangle([(0, 0), (W, 130)], fill=WHITE)
    draw.rectangle([(0, 126), (W, 134)], fill=ROSE)
    draw.text((W // 2, 50), "✦ AI メイク分析ガイド ✦", fill=ROSE, font=f44, anchor="mm")
    draw.text((W // 2, 100), "Makeup Analysis Guide", fill=LIGHT, font=f26, anchor="mm")

    # 顔写真
    ps = 340
    face = pil_image.copy()
    fw, fh = face.size
    d = min(fw, fh)
    face = face.crop(((fw-d)//2, (fh-d)//2, (fw+d)//2, (fh+d)//2))
    face = face.resize((ps, ps), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (ps, ps), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, ps-1, ps-1], fill=255)
    face.putalpha(mask)
    brd = Image.new("RGBA", (ps+10, ps+10), (0,0,0,0))
    ImageDraw.Draw(brd).ellipse([0, 0, ps+9, ps+9], outline=ROSE, width=4)
    canvas.paste(brd, (70, 165), brd)
    canvas.paste(face, (75, 170), face)

    # キャッチコピー
    _wrap(draw, karte.get("catchphrase", ""), W//2, 200, f34, TEXT, W-160)

    # スコア（右）
    score = karte.get("deviation_score", 55)
    draw.text((790, 270), str(score), fill=ROSE, font=_load_font(140), anchor="mm")
    draw.text((790, 380), "顔面偏差値", fill=GRAY, font=f34, anchor="mm")
    ft = karte.get("face_type", "")
    draw.rounded_rectangle([(560, 410), (1020, 455)], radius=22, fill=LIGHT)
    draw.text((790, 433), ft, fill=ROSE, font=f26, anchor="mm")

    # スコアバー
    bx, by, bw, bh = 70, 528, W-140, 16
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=8, fill=LIGHT)
    draw.rounded_rectangle([bx, by, bx+int(bw*score/100), by+bh], radius=8, fill=ROSE)

    # パーソナルカラー
    draw.text((70, 580), karte.get("personal_color", ""), fill=ROSE, font=f60, anchor="la")
    _wrap(draw, karte.get("personal_color_desc", ""), 70, 650, f20, GRAY, W-140, anchor="la")

    # POINT
    draw.text((70, 720), "POINT", fill=ROSE, font=f26, anchor="la")
    for i, pt in enumerate(karte.get("key_points", [])[:3]):
        draw.text((70, 760 + i*50), f"☑  {pt}", fill=TEXT, font=f26, anchor="la")

    # EYE / CHEEK / LIP
    parts_info = [
        ("EYE",   karte.get("eye_makeup", {}),   920),
        ("CHEEK", karte.get("cheek_makeup", {}), 1070),
        ("LIP",   karte.get("lip_makeup", {}),   1220),
    ]
    for label, mk, y0 in parts_info:
        draw.rounded_rectangle([(60, y0), (W-60, y0+120)], radius=12, fill=WHITE)
        draw.text((90, y0+20), f"* {label}", fill=ROSE, font=f26, anchor="la")
        draw.text((90, y0+58), mk.get("title", ""), fill=TEXT, font=f26, anchor="la")
        colors_text = "  ".join(mk.get("colors", [])[:3])
        draw.text((90, y0+96), colors_text, fill=GRAY, font=f20, anchor="la")

    # 垢抜け後
    pred = karte.get("predicted_score", score+8)
    delta = karte.get("score_increase", 8)
    draw.rounded_rectangle([(60, 1380), (W-60, 1530)], radius=20, fill=ROSE)
    draw.text((W//2, 1430), "垢抜け後の予想偏差値", fill=WHITE, font=f26, anchor="mm")
    draw.text((W//2, 1500), f"{pred}  ( ＋{delta}点 )", fill=WHITE, font=_load_font(72), anchor="mm")

    # 締め
    _wrap(draw, karte.get("closing", ""), W//2, 1570, f26, TEXT, W-160)

    # フッター
    draw.rectangle([(0, H-85), (W, H)], fill=WHITE)
    draw.rectangle([(0, H-85), (W, H-80)], fill=ROSE)
    draw.text((80, H-42), "#AIメイク分析ガイド  #美容診断  #垢抜け", fill=GRAY, font=f20, anchor="lm")
    draw.text((W-80, H-42), f"No.{diag_no:06d}  {TODAY}", fill=GRAY, font=f20, anchor="rm")

    return canvas


# ==================== USAGE TRACKING ====================

MONTHLY_LIMIT = 3


@st.cache_resource
def _get_sb():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_SERVICE_KEY", "")
    if not (url and key):
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None


def _get_ip_hash() -> str:
    try:
        headers = dict(st.context.headers)
        for h in ("x-forwarded-for", "x-real-ip", "cf-connecting-ip"):
            val = headers.get(h, "")
            if val:
                raw = val.split(",")[0].strip()
                return hashlib.sha256(raw.encode()).hexdigest()[:20]
    except Exception:
        pass
    # Supabaseが未設定のローカル開発環境のみ"local"を返す
    if not (st.secrets.get("SUPABASE_URL", "") and st.secrets.get("SUPABASE_SERVICE_KEY", "")):
        return "local"
    # IP取得不可の場合はセッションIDで代替（リロードでリセットされるが無制限にはならない）
    if "anon_id" not in st.session_state:
        import uuid
        st.session_state["anon_id"] = hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:20]
    return st.session_state["anon_id"]


def _this_month() -> str:
    return datetime.date.today().strftime("%Y-%m")


def _get_usage(sb, ip_hash: str) -> int:
    if not sb or ip_hash == "local":
        return 0
    try:
        r = sb.table("usage").select("count").eq("ip_hash", ip_hash).eq("month", _this_month()).execute()
        return r.data[0]["count"] if r.data else 0
    except Exception:
        return 0


def _inc_usage(sb, ip_hash: str):
    if not sb or ip_hash == "local":
        return
    m = _this_month()
    try:
        r = sb.table("usage").select("count").eq("ip_hash", ip_hash).eq("month", m).execute()
        if r.data:
            sb.table("usage").update({"count": r.data[0]["count"] + 1}).eq("ip_hash", ip_hash).eq("month", m).execute()
        else:
            sb.table("usage").insert({"ip_hash": ip_hash, "month": m, "count": 1}).execute()
    except Exception:
        pass


def _is_premium(sb, ip_hash: str) -> bool:
    if not sb or ip_hash == "local":
        return True
    try:
        today = datetime.date.today().isoformat()
        r = sb.table("premium_ips").select("id").eq("ip_hash", ip_hash).gte("expires_at", today).execute()
        return len(r.data) > 0
    except Exception:
        return False


def _activate_code(sb, ip_hash: str, code: str) -> bool:
    if not sb:
        return False
    try:
        r = sb.table("access_codes").select("*").eq("code", code.upper()).eq("used", False).execute()
        if not r.data:
            return False
        sb.table("access_codes").update({"used": True, "activated_ip": ip_hash}).eq("code", code.upper()).execute()
        expires = (datetime.date.today() + datetime.timedelta(days=31)).isoformat()
        sb.table("premium_ips").insert({"ip_hash": ip_hash, "expires_at": expires, "code": code.upper()}).execute()
        return True
    except Exception:
        return False


def _show_paywall(sb, ip_hash: str):
    stripe_link = st.secrets.get("STRIPE_LINK", "#")
    st.markdown(f"""
    <div style="background:{C_CARD}; border:2px solid {C_LIGHT}; border-radius:16px;
                padding:2rem; text-align:center; margin:2rem 0;">
        <div style="font-size:2.5rem; color:{C_ACCENT};">✦</div>
        <div style="font-family:'Noto Serif JP',serif; font-size:1.3rem; color:{C_TEXT};
                    font-weight:700; margin:0.6rem 0;">
            今月の無料枠（{MONTHLY_LIMIT}回）を<br>使い切りました
        </div>
        <p style="color:{C_SUB}; font-size:0.85rem; margin:0.4rem 0 1.2rem;">
            来月になると自動でリセットされます。<br>
            今すぐ続けたい場合はプレミアムプランへどうぞ。
        </p>
        <div style="background:{C_BG}; border-radius:12px; padding:1.2rem; margin-bottom:1.4rem; text-align:left;">
            <div style="font-size:1.7rem; font-weight:900; color:{C_ACCENT}; text-align:center;">
                ¥980<span style="font-size:0.85rem; font-weight:400; color:{C_SUB};">/月</span>
            </div>
            <ul style="color:{C_TEXT}; font-size:0.85rem; line-height:2.1; margin:0.8rem 0 0; padding-left:1.2rem;">
                <li>月間 <b>無制限</b> の顔面カルテ診断</li>
                <li>パーソナルカラー・メイク詳細分析</li>
                <li>垢抜けアドバイス全項目</li>
            </ul>
        </div>
        <a href="{stripe_link}" target="_blank" style="
            display:block; background:linear-gradient(90deg,{C_ACCENT},{C_LIGHT});
            color:white; font-weight:900; font-size:1rem; padding:0.9rem;
            border-radius:10px; text-decoration:none; margin-bottom:0.5rem;
        ">✦ プレミアムに登録する</a>
        <p style="color:{C_SUB}; font-size:0.75rem;">
            ※ 登録後にアクセスコードをメールでお送りします
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("アクセスコードをお持ちの方"):
        code_in = st.text_input("コードを入力", placeholder="XXXX-XXXX-XXXX", key="code_input")
        if st.button("適用する", key="apply_code"):
            if _activate_code(sb, ip_hash, code_in):
                st.success("✓ プレミアムが有効になりました！")
                st.rerun()
            else:
                st.error("コードが無効か、使用済みです。")


# ==================== UI ====================

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "") or st.secrets.get("ANTHROPIC_API_KEY", "")
    diag_no = random.randint(100000, 999999)

    sb       = _get_sb()
    ip_hash  = _get_ip_hash()
    premium  = _is_premium(sb, ip_hash)
    usage    = _get_usage(sb, ip_hash)
    remaining = max(0, MONTHLY_LIMIT - usage) if not premium else None

    with st.sidebar:
        st.markdown("### ✦ 今月の残り回数")
        if premium:
            st.success("プレミアム会員 ✦ 無制限")
        elif sb:
            st.info(f"残り **{remaining}** 回 / 月{MONTHLY_LIMIT}回")
            st.progress(max(0.0, 1.0 - usage / MONTHLY_LIMIT))
        else:
            st.info("無料プラン")

    # マガジンヘッダー
    st.markdown(f"""
    <div class="mag-header">
        <div class="mag-deco">✦ あなたの魅力を引き出す ✦</div>
        <div class="mag-title">メイク分析ガイド</div>
        <div class="mag-sub-jp">- natural elegance -</div>
        <div class="mag-sub-en">Makeup Analysis Guide</div>
        <div class="mag-divider"><span>✦</span></div>
        <div class="diag-line">No.{diag_no:06d} &nbsp;|&nbsp; {TODAY}</div>
    </div>
    """, unsafe_allow_html=True)

    if not premium and usage >= MONTHLY_LIMIT:
        _show_paywall(sb, ip_hash)
    else:
        uploaded = st.file_uploader(
            "顔写真をアップロード",
            type=["jpg", "jpeg", "png", "webp"],
            help="正面向き・明るい環境の写真が最適です",
        )

        if uploaded:
            image = Image.open(uploaded)
            st.image(image, use_container_width=True, caption="アップロード完了")

            if st.button("分析ガイドを作成する", type="primary", use_container_width=True):
                with st.spinner("AIが分析中… 少々お待ちください"):
                    if not has_face(image):
                        st.error("顔を検出できませんでした。正面向きの写真を使用してください。")
                        return
                    karte = get_karte(image, api_key)
                _inc_usage(sb, ip_hash)
                _display_karte(image, karte, diag_no)

    st.markdown(
        '<div class="disclaimer">※ このアプリはエンターテインメント目的のAI診断です。医療行為ではありません。</div>',
        unsafe_allow_html=True,
    )


def _display_karte(image: Image.Image, karte: dict, diag_no: int):
    score  = karte.get("deviation_score", 55)
    ft     = karte.get("face_type", "")
    parts  = karte.get("parts", {})
    appeal = karte.get("appeal", {})

    # ===== 写真 + キャッチコピー & EYE/CHEEK/LIP =====
    col_l, col_r = st.columns([1, 1])

    with col_l:
        st.image(image, use_container_width=True)
        # POINT
        points_html = "".join(f'<div class="point-item">{p}</div>' for p in karte.get("key_points", []))
        st.markdown(f"""
        <div class="point-box">
            <div class="point-title">✦ POINT</div>
            {points_html}
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        # キャッチコピー
        st.markdown(f"""
        <div class="catch-wrap">
            <div class="catch-text">{karte.get('catchphrase', '')}</div>
        </div>
        """, unsafe_allow_html=True)

        # EYE
        em = karte.get("eye_makeup", {})
        eye_pts = "".join(f'<div class="part-point">{p}</div>' for p in em.get("points", []))
        st.markdown(f"""
        <div class="part-card">
            <div class="part-label">* EYE</div>
            <div class="part-title">{em.get('title','')}</div>
            {eye_pts}
            <div class="part-colors">
                <span class="color-label">おすすめカラー</span><br>
                {'、'.join(em.get('colors', []))}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # CHEEK
        cm = karte.get("cheek_makeup", {})
        chk_pts = "".join(f'<div class="part-point">{p}</div>' for p in cm.get("points", []))
        st.markdown(f"""
        <div class="part-card">
            <div class="part-label">* CHEEK</div>
            <div class="part-title">{cm.get('title','')}</div>
            {chk_pts}
            <div class="part-colors">
                <span class="color-label">おすすめカラー</span><br>
                {'、'.join(cm.get('colors', []))}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # LIP
        lm = karte.get("lip_makeup", {})
        lip_pts = "".join(f'<div class="part-point">{p}</div>' for p in lm.get("points", []))
        st.markdown(f"""
        <div class="part-card">
            <div class="part-label">* LIP</div>
            <div class="part-title">{lm.get('title','')}</div>
            {lip_pts}
            <div class="part-colors">
                <span class="color-label">おすすめカラー</span><br>
                {'、'.join(lm.get('colors', []))}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ===== スコアミニ & 総評 =====
    st.markdown(f"""
    <div class="score-mini">
        <div class="score-sub">顔面偏差値（全国平均 50）</div>
        <div class="score-big-warm">{score}</div>
        <div class="score-bar-bg">
            <div class="score-bar-fg" style="width:{score}%"></div>
        </div>
        <div class="type-badge">顔タイプ：{ft}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="mag-card" style="font-family:'Noto Serif JP',serif;font-style:italic;font-size:0.98rem;color:#5C4040;line-height:1.8;text-align:center">
        {karte.get('overall_comment','')}
    </div>
    """, unsafe_allow_html=True)

    # ===== 3カラムグリッド: パーソナルカラー | 顔タイプ診断 | 魅力と印象 =====
    c1, c2, c3 = st.columns(3)

    with c1:
        palette_html = _swatches_html(karte.get("personal_color_palette", []))
        st.markdown(f"""
        <div class="mag-card">
            <div class="sec-badge">パーソナルカラー</div>
            <div class="pc-type">{karte.get('personal_color','')}</div>
            {palette_html}
            <div class="pc-desc">{karte.get('personal_color_desc','')}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        pentagon = _pentagon_svg(appeal, size=180)
        st.markdown(f"""
        <div class="mag-card" style="text-align:center">
            <div class="sec-badge">顔タイプ診断</div>
            <div style="font-family:'Noto Serif JP',serif;font-size:1.2rem;font-weight:700;color:#5C4040;margin-bottom:0.3rem">{ft}</div>
            {pentagon}
        </div>
        """, unsafe_allow_html=True)

    with c3:
        appeal_html = "".join(
            f'<div class="appeal-row"><span class="appeal-tag">{ap["tag"]}</span><span class="appeal-text">{ap["description"]}</span></div>'
            for ap in karte.get("appeal_points", [])
        )
        st.markdown(f"""
        <div class="mag-card">
            <div class="sec-badge">魅力と印象</div>
            {appeal_html}
        </div>
        """, unsafe_allow_html=True)

    # ===== おすすめ質感・スタイル =====
    sty = karte.get("style", {})
    style_html = "".join(
        f'<div class="style-row"><span class="style-tag">{lbl}</span><span class="style-val">{val}</span></div>'
        for lbl, val in [("メイク", sty.get("makeup","")), ("ファッション", sty.get("fashion","")), ("ヘア", sty.get("hair",""))]
    )
    st.markdown(f"""
    <div class="mag-card">
        <div class="sec-badge">おすすめ 質感・スタイル</div>
        {style_html}
    </div>
    """, unsafe_allow_html=True)

    # ===== パーツ別評価バー =====
    part_labels = [("eyes","目力"),("nose","鼻筋"),("mouth","口元"),("contour","輪郭"),("skin","肌印象"),("balance","顔バランス")]
    bars = "".join(
        f"""<div style="display:flex;align-items:center;gap:0.7rem;margin:0.4rem 0">
            <div style="font-size:0.78rem;color:#9C7A7A;width:72px;flex-shrink:0">{lb}</div>
            <div style="flex:1;background:#F0DDD5;border-radius:4px;height:8px;overflow:hidden">
                <div style="width:{parts.get(k,3)/5*100:.0f}%;height:100%;border-radius:4px;background:linear-gradient(90deg,#DEB8A8,#C4887A)"></div>
            </div>
            <div style="font-size:0.78rem;font-weight:700;color:#C4887A;width:24px;text-align:right">{parts.get(k,3)}/5</div>
           </div>"""
        for k, lb in part_labels
    )
    st.markdown(f"""
    <div class="mag-card">
        <div class="sec-badge">■ パーツ別評価</div>
        {bars}
    </div>
    """, unsafe_allow_html=True)

    # ===== 長所 & 改善点 =====
    def _list(items, badge_cls):
        return "".join(
            f'<div class="list-item"><div class="{badge_cls}">{i+1}</div><div class="list-text">{s}</div></div>'
            for i, s in enumerate(items)
        )

    ca, cb = st.columns(2)
    with ca:
        st.markdown(f"""
        <div class="mag-card">
            <div class="sec-badge">★ 長所 TOP3</div>
            {_list(karte.get('strengths',[]), 'badge-solid')}
        </div>
        """, unsafe_allow_html=True)
    with cb:
        st.markdown(f"""
        <div class="mag-card">
            <div class="sec-badge">▲ 垢抜けポイント TOP3</div>
            {_list(karte.get('improvements',[]), 'badge-outline')}
        </div>
        """, unsafe_allow_html=True)

    # ===== 美容プラン =====
    bp = karte.get("beauty_plan", {})
    st.markdown('<div class="sec-badge" style="margin:0.8rem 0 0.4rem">▼ おすすめ美容プラン【優先順位付き】</div>', unsafe_allow_html=True)
    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown(f'<div class="plan-card"><span class="plan-badge pl-light">ライト美容</span><div class="plan-body">{bp.get("light","")}</div></div>', unsafe_allow_html=True)
    with p2:
        st.markdown(f'<div class="plan-card"><span class="plan-badge pl-skin">肌管理・医療</span><div class="plan-body">{bp.get("skin","")}</div></div>', unsafe_allow_html=True)
    with p3:
        st.markdown(f'<div class="plan-card"><span class="plan-badge pl-adv">本格アップデート</span><div class="plan-body">{bp.get("advanced","")}</div></div>', unsafe_allow_html=True)

    # ===== 垢抜け後スコア =====
    pred  = karte.get("predicted_score", score + 8)
    delta = karte.get("score_increase", 8)
    st.markdown(f"""
    <div class="predicted-card">
        <div class="pred-label">垢抜け後の予想偏差値</div>
        <div class="pred-score">{pred}</div>
        <div class="pred-delta">＋{delta}点アップ</div>
        <div class="closing-msg">{karte.get('closing','')}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div style="text-align:right;font-size:0.66rem;color:#ccc">No.{diag_no:06d} &nbsp;|&nbsp; {TODAY}</div>', unsafe_allow_html=True)

    # ===== シェア画像 DL =====
    st.markdown("---")
    share_img = generate_share_image(image, karte, diag_no)
    buf = io.BytesIO()
    share_img.save(buf, format="PNG")
    buf.seek(0)
    st.download_button(
        "📸 分析ガイドをダウンロード（SNSシェア用）",
        data=buf, file_name=f"makeup_guide_{diag_no}.png",
        mime="image/png", use_container_width=True,
    )

    tweet = (
        f"AIメイク分析ガイド：{karte.get('personal_color','')}×{karte.get('face_type','')}タイプ診断！"
        f"偏差値{score}→垢抜け後{pred}（＋{delta}点）"
        f" #AIメイク分析 #パーソナルカラー #垢抜け"
    )
    tw   = "https://twitter.com/intent/tweet?text=" + tweet.replace(" ", "%20")
    line = "https://social-plugins.line.me/lineit/share?text=" + tweet.replace(" ", "%20")
    st.markdown(f"""
    <div class="share-row">
        <a class="share-btn btn-x" href="{tw}" target="_blank">𝕏 でシェア</a>
        <a class="share-btn btn-line" href="{line}" target="_blank">LINE でシェア</a>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
