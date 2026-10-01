from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Справочник врача-терапевта")

# ---------- МКБ-10 КОДЫ ----------
MKB10 = {
    "ОРВИ": "J06.9", "Грипп": "J11.1", "Пневмония": "J18.9",
    "Бронхит": "J20.9", "Астма": "J45.9", "Аллергия": "T78.4",
    "Синусит": "J32.9", "Ангина": "J03.9", "Фарингит": "J02.9",
    "Стенокардия": "I20.9", "Инфаркт миокарда": "I21.9",
    "Сердечная недостаточность": "I50.9", "Гипертония": "I10",
    "Аритмия": "I49.9", "Мигрень": "G43.9", "Остеохондроз": "M42.9",
    "Радикулит": "M54.1", "Гастрит": "K29.7", "Язвенная болезнь": "K27.9",
    "ГЭРБ": "K21.0", "Панкреатит": "K85.9", "Аппендицит": "K35.8",
    "Пиелонефрит": "N10", "Цистит": "N30.0", "Анемия": "D64.9",
    "Сахарный диабет": "E11.9", "Гипотиреоз": "E03.9",
    "Артрит": "M13.9", "Подагра": "M10.9", "Крапивница": "L50.9",
    "Миозит": "M60.9", "Онкология": "C80.9",
}

# ---------- ПРЕПАРАТЫ (демо-данные) ----------
# Потом заменить на данные из ГРЛС / Vidal
DRUGS = {
    "ОРВИ": [
        {"name": "Парацетамол", "substance": "Парацетамол",
         "form": "Таблетки 500 мг", "dose": "500–1000 мг до 4 раз в сутки",
         "indication": "Жар, головная боль", "contra": "Тяжёлые нарушения печени",
         "producer": "Разные"},
        {"name": "Оциллококцинум", "substance": "Оциллококцинум",
         "form": "Гранулы", "dose": "1 доза 2–3 раза в день",
         "indication": "Профилактика и лечение ОРВИ", "contra": "Индивидуальная непереносимость",
         "producer": "Boiron"},
        {"name": "Арбидол", "substance": "Умифеновир",
         "form": "Капсулы 50 мг", "dose": "200 мг 4 раза в сутки",
         "indication": "Противовирусное", "contra": "Дети до 2 лет",
         "producer": "Фармстандарт"},
    ],
    "Грипп": [
        {"name": "Осельтамивир", "substance": "Осельтамивир",
         "form": "Капсулы 75 мг", "dose": "75 мг 2 раза в сутки, 5 дней",
         "indication": "Лечение гриппа A и B", "contra": "Тяжёлая почечная недостаточность",
         "producer": "Разные"},
        {"name": "Парацетамол", "substance": "Парацетамол",
         "form": "Таблетки 500 мг", "dose": "500–1000 мг до 4 раз в сутки",
         "indication": "Жар, головная боль", "contra": "Тяжёлые нарушения печени",
         "producer": "Разные"},
    ],
    "Пневмония": [
        {"name": "Амоксициллин", "substance": "Амоксициллин",
         "form": "Таблетки 500 мг", "dose": "500–1000 мг 2–3 раза в сутки",
         "indication": "Бактериальная пневмония", "contra": "Аллергия на пенициллины",
         "producer": "Разные"},
        {"name": "Азитромицин", "substance": "Азитромицин",
         "form": "Таблетки 500 мг", "dose": "500 мг 1 раз в сутки, 3 дня",
         "indication": "Атипичная пневмония", "contra": "Тяжёлые нарушения печени",
         "producer": "Разные"},
    ],
    "Стенокардия": [
        {"name": "Нитроглицерин", "substance": "Нитроглицерин",
         "form": "Таблетки 0,5 мг", "dose": "1 таблетка под язык при приступе",
         "indication": "Купирование приступа", "contra": "Гипотония, инфаркт правого желудочка",
         "producer": "Разные"},
        {"name": "Атенолол", "substance": "Атенолол",
         "form": "Таблетки 50 мг", "dose": "50–100 мг 1 раз в сутки",
         "indication": "Профилактика приступов", "contra": "Брадикардия, бронхиальная астма",
         "producer": "Разные"},
        {"name": "Амлодипин", "substance": "Амлодипин",
         "form": "Таблетки 5 мг", "dose": "5–10 мг 1 раз в сутки",
         "indication": "Стенокардия, гипертония", "contra": "Тяжёлая гипотония",
         "producer": "Разные"},
    ],
    "Инфаркт миокарда": [
        {"name": "Аспирин", "substance": "Ацетилсалициловая кислота",
         "form": "Таблетки 100 мг", "dose": "100–300 мг сразу, разжевать",
         "indication": "Антиагрегант", "contra": "Язвенная болезнь, кровотечения",
         "producer": "Разные"},
        {"name": "Морфин", "substance": "Морфин",
         "form": "Раствор 1%", "dose": "2–4 мг в/в",
         "indication": "Купирование боли", "contra": "Угнетение дыхания",
         "producer": "Разные"},
    ],
    "Бронхит": [
        {"name": "Амброксол", "substance": "Амброксол",
         "form": "Таблетки 30 мг", "dose": "30 мг 2–3 раза в сутки",
         "indication": "Муколитик", "contra": "Язвенная болезнь",
         "producer": "Разные"},
        {"name": "Сальбутамол", "substance": "Сальбутамол",
         "form": "Аэрозоль 100 мкг", "dose": "1–2 вдоха при необходимости",
         "indication": "Бронхоспазм", "contra": "Тахиаритмия",
         "producer": "Разные"},
    ],
    "Астма": [
        {"name": "Сальбутамол", "substance": "Сальбутамол",
         "form": "Аэрозоль 100 мкг", "dose": "1–2 вдоха при приступе",
         "indication": "Купирование приступа", "contra": "Тахиаритмия",
         "producer": "Разные"},
        {"name": "Будесонид", "substance": "Будесонид",
         "form": "Аэрозоль 200 мкг", "dose": "200–400 мкг 2 раза в сутки",
         "indication": "Базисная терапия", "contra": "Индивидуальная непереносимость",
         "producer": "Разные"},
    ],
    "Аллергия": [
        {"name": "Лоратадин", "substance": "Лоратадин",
         "form": "Таблетки 10 мг", "dose": "10 мг 1 раз в сутки",
         "indication": "Антигистаминное", "contra": "Дети до 2 лет",
         "producer": "Разные"},
        {"name": "Цетиризин", "substance": "Цетиризин",
         "form": "Таблетки 10 мг", "dose": "10 мг 1 раз в сутки",
         "indication": "Антигистаминное", "contra": "Тяжёлая почечная недостаточность",
         "producer": "Разные"},
    ],
    "Гастрит": [
        {"name": "Омепразол", "substance": "Омепразол",
         "form": "Капсулы 20 мг", "dose": "20 мг 1–2 раза в сутки",
         "indication": "Ингибитор протонной помпы", "contra": "Индивидуальная непереносимость",
         "producer": "Разные"},
        {"name": "Де-Нол", "substance": "Висмута трикалия дицитрат",
         "form": "Таблетки 120 мг", "dose": "120 мг 4 раза в сутки",
         "indication": "Гастропротектор", "contra": "Тяжёлая почечная недостаточность",
         "producer": "Разные"},
    ],
    "Язвенная болезнь": [
        {"name": "Омепразол", "substance": "Омепразол",
         "form": "Капсулы 20 мг", "dose": "20 мг 2 раза в сутки",
         "indication": "Ингибитор протонной помпы", "contra": "Индивидуальная непереносимость",
         "producer": "Разные"},
        {"name": "Амоксициллин", "substance": "Амоксициллин",
         "form": "Таблетки 500 мг", "dose": "1000 мг 2 раза в сутки (эрадикация)",
         "indication": "H. pylori", "contra": "Аллергия на пенициллины",
         "producer": "Разные"},
    ],
    "Пиелонефрит": [
        {"name": "Ципрофлоксацин", "substance": "Ципрофлоксацин",
         "form": "Таблетки 500 мг", "dose": "500 мг 2 раза в сутки",
         "indication": "Антибактериальное", "contra": "Беременность, дети",
         "producer": "Разные"},
    ],
    "Цистит": [
        {"name": "Фосфомицин", "substance": "Фосфомицин",
         "form": "Порошок 3 г", "dose": "3 г однократно",
         "indication": "Антибактериальное", "contra": "Тяжёлая почечная недостаточность",
         "producer": "Разные"},
        {"name": "Нитрофурантоин", "substance": "Нитрофурантоин",
         "form": "Таблетки 100 мг", "dose": "100 мг 4 раза в сутки",
         "indication": "Антибактериальное", "contra": "Почечная недостаточность",
         "producer": "Разные"},
    ],
    "Гипертония": [
        {"name": "Эналаприл", "substance": "Эналаприл",
         "form": "Таблетки 10 мг", "dose": "10–20 мг 1–2 раза в сутки",
         "indication": "АКФ-ингибитор", "contra": "Беременность, ангионевротический отёк",
         "producer": "Разные"},
        {"name": "Амлодипин", "substance": "Амлодипин",
         "form": "Таблетки 5 мг", "dose": "5–10 мг 1 раз в сутки",
         "indication": "Блокатор кальциевых каналов", "contra": "Тяжёлая гипотония",
         "producer": "Разные"},
    ],
    "Сахарный диабет": [
        {"name": "Метформин", "substance": "Метформин",
         "form": "Таблетки 500 мг", "dose": "500–1000 мг 2 раза в сутки",
         "indication": "Сахарный диабет 2 типа", "contra": "Почечная недостаточность",
         "producer": "Разные"},
    ],
    "Анемия": [
        {"name": "Сорбифер", "substance": "Железа сульфат",
         "form": "Таблетки", "dose": "1 таблетка 2 раза в сутки",
         "indication": "Железодефицитная анемия", "contra": "Гемохроматоз",
         "producer": "Разные"},
    ],
    "Мигрень": [
        {"name": "Суматриптан", "substance": "Суматриптан",
         "form": "Таблетки 50 мг", "dose": "50–100 мг при приступе",
         "indication": "Купирование приступа мигрени", "contra": "ИБС, гипертония",
         "producer": "Разные"},
        {"name": "Ибупрофен", "substance": "Ибупрофен",
         "form": "Таблетки 400 мг", "dose": "400 мг при приступе",
         "indication": "НПВС", "contra": "Язвенная болезнь",
         "producer": "Разные"},
    ],
    "Остеохондроз": [
        {"name": "Диклофенак", "substance": "Диклофенак",
         "form": "Таблетки 50 мг", "dose": "50 мг 2–3 раза в сутки",
         "indication": "НПВС", "contra": "Язвенная болезнь",
         "producer": "Разные"},
        {"name": "Миорелаксанты", "substance": "Тизанидин",
         "form": "Таблетки 2 мг", "dose": "2–4 мг 2–3 раза в сутки",
         "indication": "Мышечный спазм", "contra": "Тяжёлая печёночная недостаточность",
         "producer": "Разные"},
    ],
}

# ---------- БАЗА ЗНАНИЙ ----------
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

class Complaints(BaseModel):
    text: str
    age: Optional[int] = None
    sex: Optional[str] = None

def apply_age_sex(diagnosis, weight, age, sex):
    rule = AGE_SEX_RULES.get(diagnosis)
    if not rule:
        return weight
    min_age, max_age, req_sex = rule
    if age is not None and not (min_age <= age <= max_age):
        weight *= 0.2
    if req_sex and sex and sex != req_sex:
        weight *= 0.3
    return weight

def analyze(text, age=None, sex=None):
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
        [{"name": k, "mkb": MKB10.get(k, "—"),
          "probability": round(v / total * 100),
          "has_drugs": k in DRUGS}
         for k, v in scores.items()],
        key=lambda x: -x["probability"]
    )

    return {"diagnoses": ranked[:7], "symptoms": found_symptoms, "red_flags": flags}

@app.post("/analyze")
def analyze_endpoint(data: Complaints):
    return analyze(data.text, data.age, data.sex)

@app.get("/drugs/{diagnosis}")
def get_drugs(diagnosis: str):
    return {"diagnosis": diagnosis, "drugs": DRUGS.get(diagnosis, [])}

@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Справочник врача-терапевта</title>
        <style>
            body { font-family: -apple-system, Arial, sans-serif; max-width: 860px;
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
            .diag { padding: 12px 16px; margin: 8px 0; background: #f0f6ff;
                    border-radius: 6px; display: flex; justify-content: space-between;
                    align-items: center; cursor: pointer; transition: background 0.2s; }
            .diag:hover { background: #e0ecff; }
            .diag.open { background: #dbe9ff; }
            .diag .left { display: flex; align-items: center; gap: 10px; }
            .diag .mkb { color: #1a5490; font-weight: 600; font-size: 13px; }
            .diag .arrow { color: #1a5490; font-size: 12px; }
            .diag .prob { font-weight: 700; color: #1a5490; }
            .drugs { margin: 4px 0 16px 0; padding: 0 16px; border-left: 3px solid #1a5490;
                     background: #fafcff; border-radius: 0 6px 6px 0; }
            .drug { padding: 12px 0; border-bottom: 1px solid #e6eefc; }
            .drug:last-child { border-bottom: none; }
            .drug .name { font-weight: 700; color: #1a5490; font-size: 15px; }
            .drug .substance { color: #666; font-size: 13px; margin: 2px 0 6px; }
            .drug .row { font-size: 13px; margin: 3px 0; }
            .drug .row b { color: #333; }
            .flag { padding: 10px 14px; border-radius: 6px; margin: 8px 0; font-size: 14px; }
            .flag.экстренно { background: #ffe6e6; color: #b00; border-left: 4px solid #c00; }
            .flag.срочно { background: #fff4e5; color: #a35b00; border-left: 4px solid #e08a00; }
            .symptom { display: inline-block; background: #e6f0ff; padding: 4px 10px;
                       border-radius: 12px; margin: 3px; font-size: 13px; }
            .hint { color: #888; font-size: 13px; margin-top: 4px; }
            .no-drugs { color: #888; font-size: 13px; padding: 8px 16px; font-style: italic; }
        </style>
    </head>
    <body>
        <h1>Справочник врача-терапевта</h1>
        <p class="sub">Система поддержки принятия врачебных решений · МКБ-10</p>

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
                render(data);
            }

            async function render(data) {
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
                    html += '<p><b>Вероятные диагнозы:</b> <span class="hint">' +
                            '(нажмите, чтобы увидеть препараты)</span></p>';
                    data.diagnoses.forEach((d, i) => {
                        const clickable = d.has_drugs ? 'onclick="toggleDrugs(\\'' + d.name + '\\', ' + i + ')"' : '';
                        const cursor = d.has_drugs ? '' : 'style="cursor:default"';
                        const arrow = d.has_drugs ? '<span class="arrow">▼</span>' : '';
                        html += '<div class="diag" id="diag-' + i + '" ' + clickable + ' ' + cursor + '>';
                        html += '<div class="left">' + arrow + '<span>' + d.name +
                                ' <span class="mkb">' + d.mkb + '</span></span></div>';
                        html += '<span class="prob">' + d.probability + '%</span>';
                        html += '</div>';
                        html += '<div id="drugs-' + i + '" style="display:none"></div>';
                    });
                } else if (!data.red_flags.length) {
                    html += '<p>Симптомы не распознаны. Попробуйте описать подробнее.</p>';
                }
                document.getElementById('result').innerHTML = html;
            }

            async function toggleDrugs(diagnosis, i) {
                const block = document.getElementById('drugs-' + i);
                const diag = document.getElementById('diag-' + i);

                if (block.style.display === 'block') {
                    block.style.display = 'none';
                    diag.classList.remove('open');
                    return;
                }

                const res = await fetch('/drugs/' + encodeURIComponent(diagnosis));
                const data = await res.json();

                if (!data.drugs.length) {
                    block.innerHTML = '<div class="no-drugs">Нет данных о препаратах</div>';
                } else {
                    let html = '<div class="drugs">';
                    data.drugs.forEach(drug => {
                        html += '<div class="drug">';
                        html += '<div class="name">' + drug.name + '</div>';
                        html += '<div class="substance">' + drug.substance + '</div>';
                        html += '<div class="row"><b>Форма:</b> ' + drug.form + '</div>';
                        html += '<div class="row"><b>Дозировка:</b> ' + drug.dose + '</div>';
                        html += '<div class="row"><b>Показания:</b> ' + drug.indication + '</div>';
                        html += '<div class="row"><b>Противопоказания:</b> ' + drug.contra + '</div>';
                        html += '<div class="row"><b>Производитель:</b> ' + drug.producer + '</div>';
                        html += '</div>';
                    });
                    html += '</div>';
                    block.innerHTML = html;
                }
                block.style.display = 'block';
                diag.classList.add('open');
            }
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)