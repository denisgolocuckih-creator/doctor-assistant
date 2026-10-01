from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Справочник врача-терапевта")

# ---------- БАЗА ЗНАНИЙ ----------
# симптом: {диагноз: вес}
KNOWLEDGE_BASE = {
    "температура": {"ОРВИ": 0.8, "Грипп": 0.7, "Пневмония": 0.4, "Пиелонефрит": 0.4},
    "высокая температура": {"Грипп": 0.8, "Пневмония": 0.6, "Пиелонефрит": 0.5},
    "кашель": {"ОРВИ": 0.7, "Бронхит": 0.6, "Пневмония": 0.5, "Астма": 0.4},
    "сухой кашель": {"Бронхит": 0.6, "Астма": 0.5, "ОРВИ": 0.5},
    "влажный кашель": {"Бронхит": 0.7, "Пневмония": 0.6, "ОРВИ": 0.5},
    "насморк": {"ОРВИ": 0.8, "Аллергия": 0.5, "Синусит": 0.5},
    "боль в горле": {"ОРВИ": 0.7, "Ангина": 0.7, "Фарингит": 0.6},
    "боль в груди": {"Стенокардия": 0.7, "Пневмония": 0.5, "Остеохондроз": 0.4, "Инфаркт миокарда": 0.6},
    "одышка": {"Пневмония": 0.7, "Бронхит": 0.6, "Сердечная недостаточность": 0.6, "Астма": 0.6},
    "головная боль": {"Мигрень": 0.7, "Гипертония": 0.6, "ОРВИ": 0.4, "Остеохондроз": 0.4},
    "головокружение": {"Гипертония": 0.6, "Остеохондроз": 0.5, "Анемия": 0.5},
    "боль в животе": {"Гастрит": 0.7, "Аппендицит": 0.5, "Панкреатит": 0.5, "Язвенная болезнь": 0.6},
    "тошнота": {"Гастрит": 0.6, "Панкреатит": 0.5, "Мигрень": 0.4, "Аппендицит": 0.4},
    "рвота": {"Панкреатит": 0.6, "Аппендицит": 0.5, "Гастрит": 0.5},
    "изжога": {"Гастрит": 0.7, "Язвенная болезнь": 0.6, "ГЭРБ": 0.7},
    "боль в пояснице": {"Остеохондроз": 0.7, "Пиелонефрит": 0.6, "Радикулит": 0.6},
    "частое мочеиспускание": {"Пиелонефрит": 0.6, "Цистит": 0.7, "Сахарный диабет": 0.5},
    "боль при мочеиспускании": {"Цистит": 0.8, "Пиелонефрит": 0.6},
    "слабость": {"ОРВИ": 0.5, "Анемия": 0.6, "Грипп": 0.5, "Сахарный диабет": 0.4},
    "утомляемость": {"Анемия": 0.6, "Сахарный диабет": 0.5, "Гипотиреоз": 0.5},
    "сердцебиение": {"Гипертония": 0.5, "Аритмия": 0.7, "Анемия": 0.5},
    "повышенное давление": {"Гипертония": 0.9},
    "отёки": {"Сердечная недостаточность": 0.7, "Пиелонефрит": 0.5, "Гипотиреоз": 0.5},
    "сыпь": {"Аллергия": 0.7, "ОРВИ": 0.4, "Крапивница": 0.6},
    "зуд": {"Аллергия": 0.7, "Крапивница": 0.5},
    "потеря веса": {"Сахарный диабет": 0.6, "Гипотиреоз": 0.4, "Онкология": 0.4},
    "жажда": {"Сахарный диабет": 0.8},
    "онемение конечностей": {"Остеохондроз": 0.6, "Сахарный диабет": 0.6, "Радикулит": 0.5},
    "боль в суставах": {"Артрит": 0.7, "Остеохондроз": 0.4, "Подагра": 0.6},
    "боль в мышцах": {"ОРВИ": 0.6, "Грипп": 0.7, "Миозит": 0.5},
}

# Красные флаги: симптом -> рекомендация и срочность
RED_FLAGS = {
    "боль в груди": ("ЭКГ, тропонины, вызов кардиолога", "экстренно"),
    "одышка": ("Пульсоксиметрия, рентген грудной клетки", "экстренно"),
    "потеря сознания": ("Измерение АД, глюкоза, ЭКГ", "экстренно"),
    "кровь": ("Осмотр, общий анализ крови, консультация", "экстренно"),
    "судороги": ("Неврологический осмотр, КТ/МРТ", "экстренно"),
    "резкая боль в животе": ("Осмотр хирурга, УЗИ, исключить аппендицит", "экстренно"),
    "высокая температура": ("Жаропонижающие, контроль, при >39 — осмотр", "срочно"),
    "рвота": ("Регидратация, осмотр, исключить хирургию", "срочно"),
    "потеря веса": ("Онкопоиск, гормоны щитовидной железы, глюкоза", "срочно"),
}

# Поправки по возрасту и полу (диагноз: (мин_возраст, макс_возраст, пол))
AGE_SEX_RULES = {
    "Инфаркт миокарда": (45, 120, None),
    "Стенокардия": (40, 120, None),
    "Гипертония": (35, 120, None),
    "Астма": (0, 60, None),
    "Ангина": (3, 40, None),
    "Мигрень": (10, 50, "female"),
    "Цистит": (18, 90, "female"),
    "Пиелонефрит": (18, 90, "female"),
    "Подагра": (40, 90, "male"),
}

# ---------- МОДЕЛЬ ЗАПРОСА ----------
class Complaints(BaseModel):
    text: str
    age: Optional[int] = None
    sex: Optional[str] = None  # "male" / "female"

# ---------- ЛОГИКА ----------
def apply_age_sex(diagnosis: str, weight: float, age, sex):
    rule = AGE_SEX_RULES.get(diagnosis)
    if not rule:
        return weight
    min_age, max_age, req_sex = rule
    if age is not None and not (min_age <= age <= max_age):
        weight *= 0.2
    if req_sex and sex and sex != req_sex:
        weight *= 0.3
    return weight

def analyze(text: str, age=None, sex=None):
    text_lower = text.lower()
    scores = {}
    found_symptoms = []
    flags = []

    for symptom, diagnoses in KNOWLEDGE_BASE.items():
        if symptom in text_lower:
            found_symptoms.append(symptom)
            for diag, weight in diagnoses.items():
                w = apply_age_sex(diag, weight, age, sex)
                scores[diag] = scores.get(diag, 0) + w

    for flag, (rec, urgency) in RED_FLAGS.items():
        if flag in text_lower:
            flags.append({"symptom": flag, "recommendation": rec, "urgency": urgency})

    if not scores:
        return {"diagnoses": [], "symptoms": found_symptoms, "red_flags": flags}

    total = sum(scores.values())
    ranked = sorted(
        [{"name": k, "probability": round(v / total * 100)} for k, v in scores.items()],
        key=lambda x: -x["probability"]
    )

    return {
        "diagnoses": ranked[:7],
        "symptoms": found_symptoms,
        "red_flags": flags
    }

# ---------- API ----------
@app.post("/analyze")
def analyze_endpoint(data: Complaints):
    return analyze(data.text, data.age, data.sex)

# ---------- ИНТЕРФЕЙС ----------
@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Справочник врача-терапевта</title>
        <style>
            body { font-family: -apple-system, Arial, sans-serif; max-width: 760px;
                   margin: 40px auto; padding: 20px; color: #222; }
            h1 { color: #1a5490; margin-bottom: 4px; }
            .sub { color: #777; margin-top: 0; }
            label { display: block; margin-top: 14px; font-weight: 600; font-size: 14px; }
            textarea { width: 100%; height: 90px; padding: 10px; font-size: 15px;
                       border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
            input, select { padding: 8px; font-size: 15px; border: 1px solid #ccc;
                            border-radius: 6px; margin-right: 8px; }
            button { background: #1a5490; color: white; padding: 12px 26px; border: none;
                     font-size: 16px; cursor: pointer; margin-top: 14px; border-radius: 6px; }
            button:hover { background: #0d3a66; }
            .result { margin-top: 22px; }
            .diag { padding: 10px 14px; margin: 6px 0; background: #f0f6ff;
                    border-radius: 6px; display: flex; justify-content: space-between; }
            .flag { padding: 10px 14px; border-radius: 6px; margin: 8px 0; font-size: 14px; }
            .flag.экстренно { background: #ffe6e6; color: #b00; border-left: 4px solid #c00; }
            .flag.срочно { background: #fff4e5; color: #a35b00; border-left: 4px solid #e08a00; }
            .symptom { display: inline-block; background: #e6f0ff; padding: 4px 10px;
                       border-radius: 12px; margin: 3px; font-size: 13px; }
            .hint { color: #888; font-size: 13px; margin-top: 4px; }
        </style>
    </head>
    <body>
        <h1>Справочник врача-терапевта</h1>
        <p class="sub">Система поддержки принятия врачебных решений</p>

        <label>Жалобы пациента</label>
        <textarea id="input" placeholder="Например: температура 38, кашель, насморк 3 дня"></textarea>

        <label>Возраст (необязательно)</label>
        <input type="number" id="age" placeholder="45" min="0" max="120">

        <label>Пол (необязательно)</label>
        <select id="sex">
            <option value="">—</option>
            <option value="male">Мужской</option>
            <option value="female">Женский</option>
        </select>

        <br>
        <button onclick="analyze()">Анализировать</button>

        <div class="result" id="result"></div>

        <script>
            async function analyze() {
                const text = document.getElementById('input').value;
                const age = document.getElementById('age').value;
                const sex = document.getElementById('sex').value;

                const res = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        text,
                        age: age ? parseInt(age) : null,
                        sex: sex || null
                    })
                });
                const data = await res.json();
                let html = '';

                if (data.red_flags.length) {
                    data.red_flags.forEach(f => {
                        html += '<div class="flag ' + f.urgency + '">⚠ <b>' +
                                f.symptom + '</b> — ' + f.recommendation +
                                ' <i>(' + f.urgency + ')</i></div>';
                    });
                }
                if (data.symptoms.length) {
                    html += '<p><b>Найдены симптомы:</b><br>';
                    data.symptoms.forEach(s => html += '<span class="symptom">' + s + '</span>');
                    html += '</p>';
                }
                if (data.diagnoses.length) {
                    html += '<p><b>Вероятные диагнозы:</b></p>';
                    data.diagnoses.forEach(d => {
                        html += '<div class="diag"><span>' + d.name +
                                '</span><b>' + d.probability + '%</b></div>';
                    });
                    html += '<p class="hint">Ранжирование на основе введённых симптомов. ' +
                            'Требуется клиническая верификация.</p>';
                } else if (!data.red_flags.length) {
                    html += '<p>Симптомы не распознаны. Попробуйте описать подробнее.</p>';
                }
                document.getElementById('result').innerHTML = html;
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)