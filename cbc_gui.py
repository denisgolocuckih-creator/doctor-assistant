# cbc_gui.py
# Полная программа для анализа общего анализа крови
# С поддержкой R для графиков, БД SQLite и вкладками

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os
import subprocess
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


# ========== РАБОТА С БАЗОЙ ДАННЫХ ==========

def init_database():
    """Создание таблиц в БД при первом запуске"""
    conn = sqlite3.connect('patients.db')
    conn.text_factory = str
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT NOT NULL,
            gender TEXT NOT NULL,
            birth_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS blood_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            test_date TEXT NOT NULL,
            hgb REAL,
            rbc REAL,
            wbc REAL,
            plt REAL,
            mcv REAL,
            neut REAL,
            lymph REAL,
            mono REAL,
            eo REAL,
            baso REAL,
            color_index REAL,
            diagnosis TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
    ''')

    conn.commit()
    conn.close()


def save_patient(fio, gender, birth_date):
    """Сохранить пациента в БД"""
    conn = sqlite3.connect('patients.db')
    conn.text_factory = str
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO patients (fio, gender, birth_date)
        VALUES (?, ?, ?)
    ''', (fio, gender, birth_date if birth_date else None))

    patient_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return patient_id


def save_blood_test(patient_id, test_data):
    """Сохранить анализ крови в БД"""
    conn = sqlite3.connect('patients.db')
    conn.text_factory = str
    cursor = conn.cursor()

    diagnosis = test_data.get('diagnosis', '')
    if isinstance(diagnosis, bytes):
        diagnosis = diagnosis.decode('utf-8')

    cursor.execute('''
        INSERT INTO blood_tests (
            patient_id, test_date, hgb, rbc, wbc, plt, mcv,
            neut, lymph, mono, eo, baso, color_index, diagnosis
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        patient_id, test_data['test_date'],
        float(test_data['hgb']), float(test_data['rbc']), float(test_data['wbc']),
        float(test_data['plt']), float(test_data['mcv']),
        float(test_data['neut']), float(test_data['lymph']),
        float(test_data['mono']), float(test_data['eo']), float(test_data['baso']),
        float(test_data['color_index']), diagnosis
    ))

    conn.commit()
    conn.close()


def get_all_patients():
    """Получить список всех пациентов"""
    conn = sqlite3.connect('patients.db')
    conn.text_factory = str
    cursor = conn.cursor()

    cursor.execute('SELECT id, fio, gender, birth_date FROM patients ORDER BY fio')
    patients = cursor.fetchall()

    conn.close()
    return patients


def get_patient_history(patient_id):
    """Получить историю анализов пациента"""
    conn = sqlite3.connect('patients.db')
    conn.text_factory = str
    cursor = conn.cursor()

    cursor.execute('''
        SELECT test_date, hgb, rbc, wbc, plt, mcv, diagnosis
        FROM blood_tests
        WHERE patient_id = ?
        ORDER BY test_date DESC
    ''', (patient_id,))

    history = cursor.fetchall()
    conn.close()

    cleaned_history = []
    for row in history:
        cleaned_row = []
        for item in row:
            if isinstance(item, bytes):
                try:
                    cleaned_row.append(item.decode('utf-8'))
                except:
                    cleaned_row.append(str(item))
            else:
                cleaned_row.append(item)
        cleaned_history.append(tuple(cleaned_row))

    return cleaned_history


def get_latest_test(patient_id):
    """Получить последний анализ пациента"""
    conn = sqlite3.connect('patients.db')
    conn.text_factory = str
    cursor = conn.cursor()

    cursor.execute('''
        SELECT test_date, hgb, rbc, wbc, plt, mcv, neut, lymph, mono, eo, baso
        FROM blood_tests
        WHERE patient_id = ?
        ORDER BY test_date DESC
        LIMIT 1
    ''', (patient_id,))

    test = cursor.fetchone()
    conn.close()
    return test


def delete_patient_from_db(patient_id):
    """Удалить пациента и все его анализы"""
    conn = sqlite3.connect('patients.db')
    conn.text_factory = str
    cursor = conn.cursor()

    cursor.execute('DELETE FROM blood_tests WHERE patient_id = ?', (patient_id,))
    cursor.execute('DELETE FROM patients WHERE id = ?', (patient_id,))

    conn.commit()
    conn.close()


# ========== ФУНКЦИИ АНАЛИЗА ==========

def load_references(excel_path="reference_intervals.xlsx"):
    """Загружает референсные интервалы из Excel"""
    if not os.path.exists(excel_path):
        return None

    sheets = ['HGB', 'RBC', 'WBC', 'PLT', 'MCV']
    references = {}

    for sheet in sheets:
        try:
            references[sheet] = pd.read_excel(excel_path, sheet_name=sheet)
        except Exception:
            references[sheet] = None

    return references


def get_reference(ref_data, param_name, gender, age_group="adult"):
    """Возвращает норму для показателя"""
    df = ref_data.get(param_name)
    if df is None:
        return None, None

    filtered = df[(df['Gender'] == gender) & (df['Age_Group'] == age_group)]

    if len(filtered) == 0:
        filtered = df[df['Age_Group'] == 'adult']

    if len(filtered) > 0:
        return filtered['Low'].values[0], filtered['High'].values[0]

    return None, None


def check_deviation(value, low, high):
    """Проверка отклонения"""
    if value < low:
        return "ниже нормы"
    elif value > high:
        return "выше нормы"
    else:
        return "норма"


def calculate_color_index(hgb, rbc):
    """Расчёт цветового показателя"""
    rbc_str = str(int(rbc))
    rbc_first = int(rbc_str[:3])
    return round((hgb * 3) / rbc_first, 2)


def classify_anemia(hgb, cp, mcv, gender):
    """Классификация анемии"""
    if gender == 'M':
        if hgb >= 130:
            return None
        elif hgb >= 120:
            severity = "легкая"
        elif hgb >= 70:
            severity = "средняя"
        else:
            severity = "тяжелая"
    else:
        if hgb >= 120:
            return None
        elif hgb >= 110:
            severity = "легкая"
        elif hgb >= 70:
            severity = "средняя"
        else:
            severity = "тяжелая"

    if cp < 0.85:
        color_type = "гипохромная"
    elif cp > 1.05:
        color_type = "гиперхромная"
    else:
        color_type = "нормохромная"

    if mcv < 80:
        size_type = "микроцитарная"
    elif mcv > 100:
        size_type = "макроцитарная"
    else:
        size_type = "нормоцитарная"

    return f"{severity} {color_type} {size_type} анемия"


def calculate_nlr(neut, lymph):
    """Нейтрофильно-лимфоцитарное соотношение"""
    return round(neut / lymph, 2) if lymph > 0 else 0


# ========== ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ==========

class CBCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализ общего анализа крови - с вкладками")
        self.root.geometry("1300x850")
        self.root.resizable(True, True)

        # Инициализация БД
        init_database()

        self.filepath = None
        self.refs = load_references()
        self.current_patient_id = None
        self.current_test_data = None
        self.current_patient_name = ""

        if self.refs is None:
            messagebox.showerror("Ошибка", "Файл reference_intervals.xlsx не найден!")
            root.destroy()
            return

        self._create_notebook()
        self._create_tab_analysis()
        self._create_tab_history()
        self._create_tab_dynamics()
        self._create_tab_help()
        self._load_patients_list()

    def _create_notebook(self):
        """Создание вкладок"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

    def _create_tab_analysis(self):
        """Вкладка 1: Анализ"""
        self.tab_analysis = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_analysis, text="🏥 Анализ крови")

        # Верхняя панель: пациенты
        top_frame = tk.Frame(self.tab_analysis)
        top_frame.pack(fill="x", padx=10, pady=5)

        # Левый фрейм - список пациентов
        left_frame = tk.LabelFrame(top_frame, text="Список пациентов", width=280)
        left_frame.pack(side="left", fill="both", expand=False)
        left_frame.pack_propagate(False)

        # Строка поиска
        search_frame = tk.Frame(left_frame)
        search_frame.pack(fill="x", padx=5, pady=5)
        tk.Label(search_frame, text="🔍 Поиск:").pack(side="left")
        self.search_entry = tk.Entry(search_frame)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.search_entry.bind('<KeyRelease>', self.search_patients)

        self.patients_listbox = tk.Listbox(left_frame, height=10, font=("Arial", 10))
        self.patients_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.patients_listbox.bind('<<ListboxSelect>>', self.on_patient_select)

        # Кнопки управления пациентами
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        tk.Button(btn_frame, text="Новый пациент", command=self.new_patient_dialog,
                  bg="#4CAF50", fg="white", width=12).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Удалить", command=self.delete_patient,
                  bg="#f44336", fg="white", width=12).pack(side="left", padx=2)

        # Правый фрейм
        right_frame = tk.Frame(top_frame)
        right_frame.pack(side="left", fill="both", expand=True, padx=10)

        # Информация о пациенте
        info_frame = tk.LabelFrame(right_frame, text="Информация о пациенте")
        info_frame.pack(fill="x", pady=5)

        self.patient_info_label = tk.Label(info_frame, text="Не выбран пациент",
                                           font=("Arial", 10), fg="blue")
        self.patient_info_label.pack(pady=5)

        # Загрузка файла
        file_frame = tk.LabelFrame(right_frame, text="Загрузка данных")
        file_frame.pack(fill="x", pady=5)

        self.btn_load = tk.Button(file_frame, text="📂 Загрузить CSV файл",
                                  command=self.load_file, bg="#2196F3", fg="white", width=20)
        self.btn_load.pack(side="left", padx=5, pady=5)

        self.status_label = tk.Label(file_frame, text="Файл не выбран", fg="gray")
        self.status_label.pack(side="left", padx=10)

        self.btn_analyze = tk.Button(file_frame, text="🔬 Выполнить анализ",
                                     command=self.run_analysis, state="disabled",
                                     bg="#FF9800", fg="white", width=20)
        self.btn_analyze.pack(side="left", padx=5)

        self.progress = ttk.Progressbar(file_frame, orient="horizontal", length=200, mode="determinate")
        self.progress.pack(side="left", padx=10)

        # Таблица результатов
        result_frame = tk.LabelFrame(right_frame, text="Результаты анализа")
        result_frame.pack(fill="both", expand=True, pady=5)

        columns = ("Показатель", "Значение", "Ед.изм", "Норма", "Отклонение")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=8)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("normal", background="#ccffcc")
        self.tree.tag_configure("abnormal", background="#ffcccc")

        # Диагноз
        diag_frame = tk.LabelFrame(right_frame, text="Диагностическое заключение")
        diag_frame.pack(fill="x", pady=5)

        self.diagnosis_text = tk.Text(diag_frame, height=5, wrap="word", font=("Courier", 10))
        self.diagnosis_text.pack(fill="both", expand=True)

        # Кнопки действий
        save_btn_frame = tk.Frame(right_frame)
        save_btn_frame.pack(fill="x", pady=5)

        self.btn_save = tk.Button(save_btn_frame, text="💾 Сохранить анализ в БД",
                                  command=self.save_current_test, state="disabled",
                                  bg="#9C27B0", fg="white", width=22)
        self.btn_save.pack(side="left", padx=5)

        tk.Button(save_btn_frame, text="📊 Показать графики",
                  command=lambda: self.show_plots_from_folder("./plots"),
                  bg="#4CAF50", fg="white", width=22).pack(side="left", padx=5)

        # Дополнительные индексы
        indices_frame = tk.LabelFrame(right_frame, text="Дополнительные индексы")
        indices_frame.pack(fill="x", pady=5)

        self.indices_label = tk.Label(indices_frame, text="NLR: -- | PLR: -- | Риск: --",
                                      font=("Arial", 10), fg="gray")
        self.indices_label.pack(pady=5)

        # Статус
        self.status_bar = tk.Label(self.tab_analysis, text="Готов к работе", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_tab_history(self):
        """Вкладка 2: История анализов"""
        self.tab_history = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_history, text="📋 История")

        # Фрейм для фильтров
        filter_frame = tk.Frame(self.tab_history)
        filter_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(filter_frame, text="Период с:").pack(side="left", padx=5)
        self.start_date_entry = tk.Entry(filter_frame, width=12)
        self.start_date_entry.pack(side="left", padx=5)
        self.start_date_entry.insert(0, "2024-01-01")

        tk.Label(filter_frame, text="по:").pack(side="left", padx=5)
        self.end_date_entry = tk.Entry(filter_frame, width=12)
        self.end_date_entry.pack(side="left", padx=5)
        self.end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        tk.Button(filter_frame, text="Применить фильтр", command=self.apply_filter,
                  bg="#2196F3", fg="white").pack(side="left", padx=10)

        tk.Button(filter_frame, text="📊 Построить график динамики", command=self.plot_dynamics,
                  bg="#4CAF50", fg="white").pack(side="left", padx=10)

        # Таблица истории
        history_frame = tk.Frame(self.tab_history)
        history_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("Дата", "HGB", "RBC", "WBC", "PLT", "MCV", "ЦП", "Диагноз")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=15)

        col_widths = [150, 80, 80, 80, 80, 80, 80, 350]
        for col, width in zip(columns, col_widths):
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Кнопка экспорта
        export_frame = tk.Frame(self.tab_history)
        export_frame.pack(fill="x", padx=10, pady=5)
        tk.Button(export_frame, text="📎 Экспорт в Excel", command=self.export_to_excel,
                  bg="#4CAF50", fg="white", width=20).pack(pady=5)

    def _create_tab_dynamics(self):
        """Вкладка 3: Динамика показателей"""
        self.tab_dynamics = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_dynamics, text="📈 Динамика")

        # Выбор показателя
        select_frame = tk.Frame(self.tab_dynamics)
        select_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(select_frame, text="Выберите показатель:").pack(side="left", padx=5)
        self.param_var = tk.StringVar(value="HGB")
        params_combo = ttk.Combobox(select_frame, textvariable=self.param_var,
                                    values=["HGB", "RBC", "WBC", "PLT", "MCV"],
                                    width=10, state="readonly")
        params_combo.pack(side="left", padx=5)

        tk.Button(select_frame, text="Построить график", command=self.plot_selected_dynamics,
                  bg="#4CAF50", fg="white").pack(side="left", padx=10)

        tk.Button(select_frame, text="Сохранить график", command=self.save_dynamics_plot,
                  bg="#2196F3", fg="white").pack(side="left", padx=10)

        # Фрейм для графика
        self.plot_frame = tk.Frame(self.tab_dynamics, bg="white")
        self.plot_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.plot_label = tk.Label(self.plot_frame, text="Выберите пациента и показатель для отображения графика",
                                   font=("Arial", 12), fg="gray")
        self.plot_label.pack(expand=True)

    def _create_tab_help(self):
        """Вкладка 4: Справка"""
        self.tab_help = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_help, text="❓ Справка")

        help_text = """
        📌 ИНСТРУКЦИЯ ПО РАБОТЕ С ПРОГРАММОЙ
        ═══════════════════════════════════════════════════════════

        1. ДОБАВЛЕНИЕ ПАЦИЕНТА
           → Нажмите кнопку "Новый пациент"
           → Заполните ФИО, пол и дату рождения
           → Нажмите "Сохранить"

        2. ЗАГРУЗКА ДАННЫХ АНАЛИЗА
           → Выберите пациента из списка
           → Нажмите "Загрузить CSV файл"
           → Выберите файл с результатами анализа

        3. АНАЛИЗ
           → Нажмите "Выполнить анализ"
           → Просмотрите результаты в таблице и диагноз
           → При необходимости сохраните анализ в БД

        4. ПРОСМОТР ГРАФИКОВ
           → Нажмите "Показать графики" для открытия папки с PNG-файлами
           → Или перейдите на вкладку "Динамика" для графиков по времени

        5. ИСТОРИЯ
           → Перейдите на вкладку "История"
           → Выберите период фильтрации
           → При необходимости экспортируйте в Excel

        🔬 РАСШИФРОВКА ПОКАЗАТЕЛЕЙ:
        ───────────────────────────────────────────────────────────
        HGB  - Гемоглобин (г/л)          Норма М:130-160, Ж:120-140
        RBC  - Эритроциты (×10¹²/л)      Норма М:4.0-5.0, Ж:3.5-4.7
        WBC  - Лейкоциты (×10⁹/л)        Норма: 4.0-9.0
        PLT  - Тромбоциты (×10⁹/л)       Норма: 180-320
        MCV  - Объём эритроцита (фл)     Норма: 80-100
        ЦП   - Цветовой показатель       Норма: 0.85-1.05

        📊 ДОПОЛНИТЕЛЬНЫЕ ИНДЕКСЫ:
        ───────────────────────────────────────────────────────────
        NLR - Нейтрофильно-лимфоцитарное соотношение
              >3.0 может указывать на воспаление
        PLR - Тромбоцитарно-лимфоцитарное соотношение
              >150 может указывать на системное воспаление

        ⚠️ ВНИМАНИЕ:
        Программа носит информационный характер и не заменяет 
        консультацию врача!

        """

        help_text_widget = tk.Text(self.tab_help, wrap="word", font=("Courier", 10))
        help_text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        help_text_widget.insert("1.0", help_text)
        help_text_widget.config(state="disabled")

    def search_patients(self, event):
        """Поиск пациентов"""
        text = self.search_entry.get().lower()
        self.patients_listbox.delete(0, tk.END)

        all_patients = get_all_patients()
        for p in all_patients:
            if text in p[1].lower():
                display_text = f"{p[0]}. {p[1]} ({p[2]})"
                self.patients_listbox.insert(tk.END, display_text)
                self.patients_dict[display_text] = p[0]

    def _load_patients_list(self):
        """Загрузка списка пациентов"""
        self.patients_listbox.delete(0, tk.END)
        patients = get_all_patients()
        self.patients_dict = {}

        for patient in patients:
            display_text = f"{patient[0]}. {patient[1]} ({patient[2]})"
            self.patients_listbox.insert(tk.END, display_text)
            self.patients_dict[display_text] = patient[0]

    def on_patient_select(self, event):
        """Выбор пациента из списка"""
        selection = self.patients_listbox.curselection()
        if selection:
            text = self.patients_listbox.get(selection[0])
            patient_id = self.patients_dict.get(text)
            if patient_id:
                self.current_patient_id = patient_id
                patients = get_all_patients()
                for p in patients:
                    if p[0] == patient_id:
                        self.current_patient_name = p[1]
                        self.patient_info_label.config(
                            text=f"Пациент: {p[1]} | Пол: {p[2]} | Дата рождения: {p[3] or 'не указана'}"
                        )
                        break

                latest = get_latest_test(patient_id)
                if latest:
                    self.status_bar.config(text=f"Последний анализ от {latest[0]}")
                    self._update_history_table()
                    self.plot_dynamics()
                else:
                    self.status_bar.config(text="Нет сохранённых анализов")

    def _update_history_table(self):
        """Обновить таблицу истории"""
        if not self.current_patient_id:
            return

        history = get_patient_history(self.current_patient_id)

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for row in history:
            self.history_tree.insert("", "end", values=row)

    def apply_filter(self):
        """Применить фильтр по дате"""
        if not self.current_patient_id:
            return

        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()

        conn = sqlite3.connect('patients.db')
        conn.text_factory = str
        cursor = conn.cursor()

        cursor.execute('''
            SELECT test_date, hgb, rbc, wbc, plt, mcv, diagnosis
            FROM blood_tests
            WHERE patient_id = ? AND test_date BETWEEN ? AND ?
            ORDER BY test_date DESC
        ''', (self.current_patient_id, start_date, end_date))

        history = cursor.fetchall()
        conn.close()

        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for row in history:
            self.history_tree.insert("", "end", values=row)

    def plot_dynamics(self):
        """Построить график динамики"""
        if not self.current_patient_id:
            return

        conn = sqlite3.connect('patients.db')
        df = pd.read_sql_query('''
            SELECT test_date, hgb, rbc, wbc, plt, mcv 
            FROM blood_tests 
            WHERE patient_id = ? 
            ORDER BY test_date
        ''', conn, params=(self.current_patient_id,))
        conn.close()

        if len(df) < 2:
            return

        # Очистка фрейма
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        fig, axes = plt.subplots(2, 2, figsize=(10, 6))
        fig.suptitle(f'Динамика показателей - {self.current_patient_name}', fontsize=12)

        axes[0, 0].plot(df['test_date'], df['hgb'], 'o-', color='red')
        axes[0, 0].axhline(y=130, color='green', linestyle='--')
        axes[0, 0].axhline(y=120, color='orange', linestyle='--')
        axes[0, 0].set_title('Гемоглобин (г/л)')
        axes[0, 0].tick_params(axis='x', rotation=45)

        axes[0, 1].plot(df['test_date'], df['wbc'], 'o-', color='blue')
        axes[0, 1].axhline(y=9.0, color='green', linestyle='--')
        axes[0, 1].axhline(y=4.0, color='orange', linestyle='--')
        axes[0, 1].set_title('Лейкоциты (×10⁹/л)')
        axes[0, 1].tick_params(axis='x', rotation=45)

        axes[1, 0].plot(df['test_date'], df['plt'], 'o-', color='green')
        axes[1, 0].axhline(y=320, color='green', linestyle='--')
        axes[1, 0].axhline(y=180, color='orange', linestyle='--')
        axes[1, 0].set_title('Тромбоциты (×10⁹/л)')
        axes[1, 0].tick_params(axis='x', rotation=45)

        axes[1, 1].plot(df['test_date'], df['mcv'], 'o-', color='purple')
        axes[1, 1].axhline(y=100, color='green', linestyle='--')
        axes[1, 1].axhline(y=80, color='orange', linestyle='--')
        axes[1, 1].set_title('MCV (фл)')
        axes[1, 1].tick_params(axis='x', rotation=45)

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def plot_selected_dynamics(self):
        """Построить график выбранного показателя"""
        if not self.current_patient_id:
            messagebox.showwarning("Внимание", "Выберите пациента!")
            return

        param = self.param_var.get()

        conn = sqlite3.connect('patients.db')
        df = pd.read_sql_query(f'''
            SELECT test_date, {param} 
            FROM blood_tests 
            WHERE patient_id = ? 
            ORDER BY test_date
        ''', conn, params=(self.current_patient_id,))
        conn.close()

        if len(df) < 2:
            messagebox.showinfo("Информация", "Недостаточно данных для графика (нужно минимум 2 анализа)")
            return

        # Очистка фрейма
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        fig, ax = plt.subplots(figsize=(10, 5))

        param_names = {'HGB': 'Гемоглобин (г/л)', 'RBC': 'Эритроциты (×10¹²/л)',
                       'WBC': 'Лейкоциты (×10⁹/л)', 'PLT': 'Тромбоциты (×10⁹/л)',
                       'MCV': 'MCV (фл)'}

        ax.plot(df['test_date'], df[param], 'o-', color='steelblue', linewidth=2, markersize=8)
        ax.set_title(f'Динамика {param_names.get(param, param)} - {self.current_patient_name}')
        ax.set_xlabel('Дата')
        ax.set_ylabel(param_names.get(param, param))
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        self.current_fig = fig

    def save_dynamics_plot(self):
        """Сохранить график динамики"""
        if hasattr(self, 'current_fig'):
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )
            if filepath:
                self.current_fig.savefig(filepath, dpi=150, bbox_inches='tight')
                messagebox.showinfo("Успех", f"График сохранён в {filepath}")

    def export_to_excel(self):
        """Экспорт истории в Excel"""
        if not self.current_patient_id:
            messagebox.showwarning("Внимание", "Выберите пациента!")
            return

        conn = sqlite3.connect('patients.db')
        df = pd.read_sql_query('''
            SELECT test_date, hgb, rbc, wbc, plt, mcv, color_index, diagnosis
            FROM blood_tests 
            WHERE patient_id = ?
            ORDER BY test_date DESC
        ''', conn, params=(self.current_patient_id,))
        conn.close()

        if df.empty:
            messagebox.showinfo("Информация", "Нет данных для экспорта")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if filepath:
            df.to_excel(filepath, index=False)
            messagebox.showinfo("Успех", f"История сохранена в {filepath}")

    def new_patient_dialog(self):
        """Диалог добавления нового пациента"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Новый пациент")
        dialog.geometry("400x300")
        dialog.grab_set()

        tk.Label(dialog, text="ФИО:", font=("Arial", 10)).pack(pady=5)
        fio_entry = tk.Entry(dialog, width=40)
        fio_entry.pack(pady=5)

        tk.Label(dialog, text="Пол (M/F):", font=("Arial", 10)).pack(pady=5)
        gender_combo = ttk.Combobox(dialog, values=["M", "F"], width=5, state="readonly")
        gender_combo.pack(pady=5)

        tk.Label(dialog, text="Дата рождения (ГГГГ-ММ-ДД):", font=("Arial", 10)).pack(pady=5)
        birth_entry = tk.Entry(dialog, width=30)
        birth_entry.pack(pady=5)

        def save():
            fio = fio_entry.get().strip()
            gender = gender_combo.get()
            birth = birth_entry.get().strip()

            if not fio or not gender:
                messagebox.showwarning("Внимание", "Заполните ФИО и пол!")
                return

            save_patient(fio, gender, birth if birth else None)
            self._load_patients_list()
            dialog.destroy()
            messagebox.showinfo("Успех", f"Пациент {fio} добавлен!")

        tk.Button(dialog, text="Сохранить", command=save, bg="#4CAF50", fg="white").pack(pady=20)

    def delete_patient(self):
        """Удаление пациента"""
        if not self.current_patient_id:
            messagebox.showwarning("Внимание", "Выберите пациента!")
            return

        if messagebox.askyesno("Подтверждение", "Удалить пациента и все его анализы?"):
            delete_patient_from_db(self.current_patient_id)
            self.current_patient_id = None
            self.patient_info_label.config(text="Не выбран пациент")
            self._load_patients_list()
            self.btn_save.config(state="disabled")
            messagebox.showinfo("Успех", "Пациент удалён!")

    def save_current_test(self):
        """Сохранение текущего анализа в БД"""
        if not self.current_patient_id:
            messagebox.showwarning("Внимание", "Сначала выберите пациента!")
            return

        if not self.current_test_data:
            messagebox.showwarning("Внимание", "Сначала выполните анализ!")
            return

        test_data = self.current_test_data.copy()
        test_data['test_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        save_blood_test(self.current_patient_id, test_data)
        messagebox.showinfo("Успех", "Анализ сохранён в базу данных!")
        self._update_history_table()

    def show_plots_from_folder(self, output_dir="./plots"):
        """Открыть папку с графиками в проводнике"""
        try:
            full_path = os.path.abspath(output_dir)
            if os.path.exists(full_path):
                os.startfile(full_path)
            else:
                messagebox.showwarning("Внимание", f"Папка {full_path} не существует\nСначала выполните анализ")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    def call_r_plots(self, csv_path, output_dir="./plots"):
        """Вызов R для построения графиков"""
        try:
            possible_paths = [
                "Rscript",
                r"C:\Program Files\R\R-4.6.0\bin\Rscript.exe",
                r"C:\Program Files\R\R-4.5.0\bin\Rscript.exe",
                r"C:\Program Files\R\R-4.4.0\bin\Rscript.exe",
            ]

            rscript_path = None
            for path in possible_paths:
                try:
                    result = subprocess.run([path, "--version"],
                                            capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        rscript_path = path
                        break
                except:
                    continue

            if rscript_path is None:
                self.status_bar.config(text="Rscript не найден. Установите R")
                return False

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            r_script_content = f'''
data <- read.csv("{csv_path}")
patient <- data[1, ]

hgb <- patient$HGB
gender <- as.character(patient$Gender)

if (gender == "M") {{
    hgb_norm_low <- 130
    hgb_norm_high <- 160
}} else {{
    hgb_norm_low <- 120
    hgb_norm_high <- 140
}}

png(file.path("{output_dir}", "plot_histogram.png"), width = 800, height = 600)
set.seed(123)
ref_hgb <- rnorm(1000, mean = (hgb_norm_low + hgb_norm_high)/2, 
                 sd = (hgb_norm_high - hgb_norm_low)/6)
hist(ref_hgb, breaks = 30, col = "steelblue", border = "black",
     main = "Распределение уровня гемоглобина",
     xlab = "Гемоглобин (г/л)", ylab = "Частота")
abline(v = hgb, col = "red", lwd = 3)
abline(v = c(hgb_norm_low, hgb_norm_high), col = "green", lwd = 2, lty = 2)
legend("topright", legend = c("Пациент", "Норма"), col = c("red", "green"), lwd = 2)
dev.off()

if (all(c("NEUT", "LYMPH", "MONO", "EO", "BASO") %in% names(patient))) {{
    png(file.path("{output_dir}", "plot_pie.png"), width = 700, height = 700)
    leuk <- c(patient$NEUT, patient$LYMPH, patient$MONO, patient$EO, patient$BASO)
    labels <- c("Нейтрофилы", "Лимфоциты", "Моноциты", "Эозинофилы", "Базофилы")
    cols <- c("#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#F44336")
    pie(leuk, labels = paste0(labels, "\\n", leuk, "%"), col = cols,
        main = "Лейкоцитарная формула")
    dev.off()
}}

png(file.path("{output_dir}", "plot_boxplot.png"), width = 800, height = 600)
params <- data.frame(
    name = c("HGB", "RBC", "WBC", "PLT"),
    label = c("Гемоглобин", "Эритроциты", "Лейкоциты", "Тромбоциты"),
    value = c(patient$HGB, patient$RBC, patient$WBC, patient$PLT)
)
boxplot(value ~ name, data = params, col = "lightblue",
        main = "Сравнение показателей пациента",
        ylab = "Значение", xlab = "Показатель")
points(1:4, params$value, col = "red", pch = 19, cex = 2)
dev.off()

cat("Графики сохранены в:", "{output_dir}", "\\n")
'''
            temp_script = "temp_plots_script.R"
            with open(temp_script, "w", encoding="utf-8") as f:
                f.write(r_script_content)

            self.status_bar.config(text="Построение графиков в R...")
            self.root.update()

            result = subprocess.run([rscript_path, temp_script],
                                    capture_output=True, text=True, timeout=60)

            if os.path.exists(temp_script):
                os.remove(temp_script)

            if result.returncode == 0:
                self.status_bar.config(text=f"Графики сохранены в {output_dir}")
                return True
            else:
                self.status_bar.config(text="Ошибка R скрипта")
                return False

        except subprocess.TimeoutExpired:
            self.status_bar.config(text="Превышено время выполнения R")
            return False
        except Exception as e:
            self.status_bar.config(text=f"Ошибка: {str(e)[:50]}")
            return False

    def load_file(self):
        """Загрузка CSV файла"""
        filepath = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if filepath:
            self.filepath = filepath
            self.status_label.config(text=f"Загружен: {os.path.basename(filepath)}", fg="green")
            self.btn_analyze.config(state="normal")

    def run_analysis(self):
        """Запуск анализа"""
        if not self.filepath:
            messagebox.showwarning("Внимание", "Сначала загрузите CSV файл")
            return

        gender = "M"
        if self.current_patient_id:
            patients = get_all_patients()
            for p in patients:
                if p[0] == self.current_patient_id:
                    gender = p[1]
                    break

        try:
            self.progress['value'] = 0
            self.status_bar.config(text="Загрузка данных...")
            self.root.update()

            patient = pd.read_csv(self.filepath).iloc[0]
            self.progress['value'] = 30
            self.root.update()

            hgb = patient['HGB']
            rbc = patient['RBC']
            wbc = patient['WBC']
            plt = patient['PLT']
            mcv = patient.get('MCV', 90)
            neut = patient.get('NEUT', 50)
            lymph = patient.get('LYMPH', 30)

            cp = calculate_color_index(hgb, rbc)

            # Дополнительные индексы
            nlr = calculate_nlr(neut, lymph)
            risk = "Низкий" if nlr < 2 else "Средний" if nlr < 4 else "Высокий"
            self.indices_label.config(text=f"NLR: {nlr} | Риск: {risk}", fg="blue")

            self.progress['value'] = 50
            self.root.update()

            for item in self.tree.get_children():
                self.tree.delete(item)

            indicators = [
                ("Гемоглобин", "HGB", hgb, "г/л"),
                ("Эритроциты", "RBC", rbc, "×10¹²/л"),
                ("Лейкоциты", "WBC", wbc, "×10⁹/л"),
                ("Тромбоциты", "PLT", plt, "×10⁹/л"),
                ("MCV", "MCV", mcv, "фл"),
                ("Цветовой показатель", "CP", cp, "")
            ]

            for name, param, value, unit in indicators:
                if param != "CP":
                    low, high = get_reference(self.refs, param, gender, "adult")
                    if low and high:
                        deviation = check_deviation(value, low, high)
                        norm_text = f"{low}-{high}"
                        tag = "normal" if deviation == "норма" else "abnormal"
                    else:
                        deviation = "нет данных"
                        norm_text = "---"
                        tag = "normal"
                else:
                    if cp < 0.85 or cp > 1.05:
                        deviation = f"{value} (отклонение)"
                        tag = "abnormal"
                    else:
                        deviation = f"{value} (норма)"
                        tag = "normal"
                    norm_text = "0.85-1.05"

                self.tree.insert("", "end", values=(name, value, unit, norm_text, deviation), tags=(tag,))

            self.progress['value'] = 70
            self.root.update()

            self.diagnosis_text.delete(1.0, tk.END)
            lines = ["=" * 50, "ДИАГНОСТИЧЕСКОЕ ЗАКЛЮЧЕНИЕ", "=" * 50]

            anemia = classify_anemia(hgb, cp, mcv, gender)
            if anemia:
                lines.append(f"✓ {anemia.upper()}")
            else:
                lines.append("✓ Все показатели в пределах нормы")

            if nlr > 3:
                lines.append(f"✓ Повышен NLR ({nlr}) - возможно воспаление")

            lines.append("=" * 50)
            self.diagnosis_text.insert(1.0, "\n".join(lines))

            self.current_test_data = {
                'hgb': hgb, 'rbc': rbc, 'wbc': wbc, 'plt': plt, 'mcv': mcv,
                'neut': neut, 'lymph': lymph, 'mono': 8, 'eo': 1.5, 'baso': 0.5,
                'color_index': cp, 'diagnosis': anemia if anemia else "Норма"
            }

            self.btn_save.config(state="normal")
            self.progress['value'] = 85
            self.root.update()

            temp_csv = "temp_patient_data.csv"
            pd.DataFrame([{
                'HGB': hgb, 'RBC': rbc, 'WBC': wbc, 'PLT': plt, 'MCV': mcv,
                'NEUT': neut, 'LYMPH': lymph, 'MONO': 8, 'EO': 1.5, 'BASO': 0.5,
                'Gender': gender
            }]).to_csv(temp_csv, index=False)

            self.call_r_plots(temp_csv, "./plots")

            if os.path.exists(temp_csv):
                os.remove(temp_csv)

            self.progress['value'] = 100
            self.status_bar.config(text="Анализ завершён. Графики в папке ./plots")

            messagebox.showinfo("Успех", "Анализ выполнен!\nГрафики сохранены в папку ./plots")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось выполнить анализ:\n{e}")
            self.progress['value'] = 0


# ========== ЗАПУСК ==========

if __name__ == "__main__":
    root = tk.Tk()
    app = CBCApp(root)
    root.mainloop()