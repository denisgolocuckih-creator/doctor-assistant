# cbc_analyzer.py
# Программа для анализа общего анализа крови

import pandas as pd
import os


# ========== 1. ЗАГРУЗКА РЕФЕРЕНСОВ ИЗ EXCEL ==========

def load_references(excel_path="reference_intervals.xlsx"):
    """Загружает референсные интервалы из Excel"""
    print("Загрузка референсных интервалов...")

    # Проверяем, существует ли файл
    if not os.path.exists(excel_path):
        print(f"ОШИБКА: Файл {excel_path} не найден!")
        return None

    # Список листов для загрузки
    sheets = ['HGB', 'RBC', 'WBC', 'PLT', 'MCV', 'NEUT', 'LYMPH', 'MONO', 'EO', 'BASO']
    references = {}

    for sheet in sheets:
        try:
            references[sheet] = pd.read_excel(excel_path, sheet_name=sheet)
            print(f"  ✓ Загружен лист {sheet} ({len(references[sheet])} записей)")
        except Exception as e:
            print(f"  ✗ Ошибка загрузки {sheet}: {e}")
            references[sheet] = None

    return references


# ========== 2. ПОЛУЧЕНИЕ РЕФЕРЕНСНОГО ИНТЕРВАЛА ==========

def get_reference(ref_data, param_name, gender, age_group="adult"):
    """Возвращает норму (Low, High) для показателя, пола и возраста"""
    df = ref_data.get(param_name)
    if df is None:
        return None, None

    # Ищем строку, где Gender и Age_Group совпадают
    filtered = df[(df['Gender'] == gender) & (df['Age_Group'] == age_group)]

    if len(filtered) == 0:
        # Если не нашли точное совпадение, ищем для любого пола (*) или просто берём adult
        filtered = df[(df['Gender'] == gender) & (df['Age_Group'] == 'adult')]
        if len(filtered) == 0:
            filtered = df[df['Age_Group'] == age_group]
        if len(filtered) == 0:
            filtered = df[df['Age_Group'] == 'adult']

    if len(filtered) > 0:
        low = filtered['Low'].values[0]
        high = filtered['High'].values[0]
        return low, high

    return None, None


# ========== 3. ПРОВЕРКА ОТКЛОНЕНИЯ ==========

def check_deviation(value, low, high):
    """Возвращает строку: ниже нормы / норма / выше нормы"""
    if value < low:
        return "ниже нормы"
    elif value > high:
        return "выше нормы"
    else:
        return "норма"


# ========== 4. РАСЧЁТ ЦВЕТОВОГО ПОКАЗАТЕЛЯ ==========

def calculate_color_index(hgb, rbc):
    """Расчёт цветового показателя = (HGB * 3) / (первые 3 цифры RBC)"""
    rbc_str = str(int(rbc))  # 3.2 -> "3"
    rbc_first = int(rbc_str[:3])  # берём первые 3 символа
    cp = (hgb * 3) / rbc_first
    return round(cp, 2)


# ========== 5. КЛАССИФИКАЦИЯ АНЕМИИ ==========

def classify_anemia(hgb, cp, mcv, gender):
    """Классифицирует анемию по степени, цвету и размеру"""

    # Определение степени тяжести
    if gender == 'M':
        if hgb >= 130:
            return None  # нет анемии
        elif hgb >= 120:
            severity = "легкая"
        elif hgb >= 70:
            severity = "средняя"
        else:
            severity = "тяжелая"
    else:  # Female
        if hgb >= 120:
            return None
        elif hgb >= 110:
            severity = "легкая"
        elif hgb >= 70:
            severity = "средняя"
        else:
            severity = "тяжелая"

    # Определение типа по цветовому показателю
    if cp < 0.85:
        color_type = "гипохромная"
    elif cp > 1.05:
        color_type = "гиперхромная"
    else:
        color_type = "нормохромная"

    # Определение типа по MCV
    if mcv < 80:
        size_type = "микроцитарная"
    elif mcv > 100:
        size_type = "макроцитарная"
    else:
        size_type = "нормоцитарная"

    return f"{severity} {color_type} {size_type} анемия"


# ========== 6. КЛАССИФИКАЦИЯ ЛЕЙКОЦИТОЗА ==========

def classify_leukocytosis(wbc, neut_pct, lymph_pct):
    """Определяет тип лейкоцитоза"""
    if wbc <= 9.0:
        return None

    neut_abs = wbc * neut_pct / 100
    lymph_abs = wbc * lymph_pct / 100

    if neut_abs > 6.0:
        return "нейтрофильный лейкоцитоз"
    elif lymph_abs > 4.0:
        return "лимфоцитарный лейкоцитоз"
    else:
        return "недифференцированный лейкоцитоз"


# ========== 7. ГЛАВНАЯ ФУНКЦИЯ АНАЛИЗА ==========

def analyze_patient(csv_file, gender, age, ref_data, age_group="adult"):
    """Анализирует данные пациента и выводит диагноз"""

    print("\n" + "=" * 50)
    print("АНАЛИЗ ОБЩЕГО АНАЛИЗА КРОВИ")
    print("=" * 50)

    # Загрузка данных пациента
    patient = pd.read_csv(csv_file).iloc[0]

    # Извлечение показателей
    hgb = patient['HGB']
    rbc = patient['RBC']
    wbc = patient['WBC']
    plt = patient['PLT']
    mcv = patient.get('MCV', 90)
    neut = patient.get('NEUT', 50)
    lymph = patient.get('LYMPH', 30)

    # Расчёт цветового показателя
    cp = calculate_color_index(hgb, rbc)
    print(f"\nЦветовой показатель: {cp}")

    # Проверка отклонений
    print("\n--- ОТКЛОНЕНИЯ ПОКАЗАТЕЛЕЙ ---")

    results = {}

    # HGB
    low, high = get_reference(ref_data, 'HGB', gender, age_group)
    if low and high:
        dev = check_deviation(hgb, low, high)
        results['HGB'] = dev
        print(f"HGB ({hgb} г/л): норма {low}-{high} → {dev}")

    # RBC
    low, high = get_reference(ref_data, 'RBC', gender, age_group)
    if low and high:
        dev = check_deviation(rbc, low, high)
        results['RBC'] = dev
        print(f"RBC ({rbc}): норма {low}-{high} → {dev}")

    # WBC
    low, high = get_reference(ref_data, 'WBC', gender, age_group)
    if low and high:
        dev = check_deviation(wbc, low, high)
        results['WBC'] = dev
        print(f"WBC ({wbc}): норма {low}-{high} → {dev}")

    # PLT
    low, high = get_reference(ref_data, 'PLT', gender, age_group)
    if low and high:
        dev = check_deviation(plt, low, high)
        results['PLT'] = dev
        print(f"PLT ({plt}): норма {low}-{high} → {dev}")

    # ========== ДИАГНОСТИЧЕСКОЕ ЗАКЛЮЧЕНИЕ ==========
    print("\n" + "=" * 50)
    print("ДИАГНОСТИЧЕСКОЕ ЗАКЛЮЧЕНИЕ")
    print("=" * 50)

    diagnosis_found = False

    # 1. Анемия
    anemia = classify_anemia(hgb, cp, mcv, gender)
    if anemia:
        print(f"✓ {anemia}")
        diagnosis_found = True
    elif results.get('HGB') == 'выше нормы':
        print("✓ Выявлен эритроцитоз (повышение гемоглобина)")
        diagnosis_found = True

    # 2. Лейкоцитоз / лейкопения
    if results.get('WBC') == 'выше нормы':
        leuko_type = classify_leukocytosis(wbc, neut, lymph)
        if leuko_type:
            print(f"✓ {leuko_type}")
        else:
            print("✓ Выявлен лейкоцитоз")
        diagnosis_found = True
    elif results.get('WBC') == 'ниже нормы':
        print("✓ Выявлена лейкопения (снижение лейкоцитов)")
        diagnosis_found = True

    # 3. Тромбоцитоз / тромбоцитопения
    if results.get('PLT') == 'выше нормы':
        print("✓ Выявлен тромбоцитоз")
        diagnosis_found = True
    elif results.get('PLT') == 'ниже нормы':
        print("✓ Выявлена тромбоцитопения")
        diagnosis_found = True

    if not diagnosis_found:
        print("✓ Все показатели в пределах нормы")

    print("=" * 50)

    return results


# ========== 8. ЗАПУСК ==========

if __name__ == "__main__":
    # Загружаем референсы
    refs = load_references("reference_intervals.xlsx")

    if refs is None:
        print("Не удалось загрузить референсы. Проверьте файл Excel.")
    else:
        # Анализируем пациента
        analyze_patient("patient1.csv", gender='M', age=45, ref_data=refs, age_group="adult")