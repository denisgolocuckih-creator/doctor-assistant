# cbc_gui.py
# Полная программа для анализа общего анализа крови
# С поддержкой R для графиков и БД SQLite

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os
import subprocess
import sqlite3
from datetime import datetime


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


# ========== ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ==========

class CBCApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализ общего анализа крови - с БД и графиками")
        self.root.geometry("1300x850")
        self.root.resizable(True, True)

        # Инициализация БД
        init_database()

        self.filepath = None
        self.refs = load_references()
        self.current_patient_id = None
        self.current_test_data = None

        if self.refs is None:
            messagebox.showerror("Ошибка", "Файл reference_intervals.xlsx не найден!")
            root.destroy()
            return

        self._create_widgets()
        self._load_patients_list()

    def _create_widgets(self):
        """Создание виджетов"""

        # Заголовок
        title = tk.Label(self.root, text="ПРОГРАММНЫЙ МОДУЛЬ ДЛЯ АНАЛИЗА ОБЩЕГО АНАЛИЗА КРОВИ",
                         font=("Arial", 14, "bold"))
        title.pack(pady=10)

        # Верхняя панель: пациенты
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)

        # Левый фрейм - список пациентов
        left_frame = tk.LabelFrame(top_frame, text="Список пациентов", width=280)
        left_frame.pack(side="left", fill="both", expand=False)
        left_frame.pack_propagate(False)

        self.patients_listbox = tk.Listbox(left_frame, height=12, font=("Arial", 10))
        self.patients_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.patients_listbox.bind('<<ListboxSelect>>', self.on_patient_select)

        # Кнопки управления пациентами
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        tk.Button(btn_frame, text="Новый пациент", command=self.new_patient_dialog,
                  bg="#4CAF50", fg="white").pack(side="left", padx=2)
        tk.Button(btn_frame, text="Удалить пациента", command=self.delete_patient,
                  bg="#f44336", fg="white").pack(side="left", padx=2)

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

        self.btn_load = tk.Button(file_frame, text="Загрузить CSV файл",
                                  command=self.load_file, bg="#2196F3", fg="white", width=20)
        self.btn_load.pack(side="left", padx=5, pady=5)

        self.status_label = tk.Label(file_frame, text="Файл не выбран", fg="gray")
        self.status_label.pack(side="left", padx=10)

        self.btn_analyze = tk.Button(file_frame, text="Выполнить анализ",
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

        self.btn_save = tk.Button(save_btn_frame, text="Сохранить анализ в БД",
                                  command=self.save_current_test, state="disabled",
                                  bg="#9C27B0", fg="white", width=20)
        self.btn_save.pack(side="left", padx=5)

        tk.Button(save_btn_frame, text="История анализов", command=self.show_history,
                  bg="#00BCD4", fg="white", width=20).pack(side="left", padx=5)

        tk.Button(save_btn_frame, text="Показать графики",
                  command=lambda: self.show_plots_from_folder("./plots"),
                  bg="#4CAF50", fg="white", width=20).pack(side="left", padx=5)

        # Статус
        self.status_bar = tk.Label(self.root, text="Готов к работе", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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
                        self.patient_info_label.config(
                            text=f"Пациент: {p[1]} | Пол: {p[2]} | Дата рождения: {p[3] or 'не указана'}"
                        )
                        break

                latest = get_latest_test(patient_id)
                if latest:
                    self.status_bar.config(text=f"Последний анализ от {latest[0]}")
                else:
                    self.status_bar.config(text="Нет сохранённых анализов")

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

    def show_history(self):
        """Показать историю анализов пациента"""
        if not self.current_patient_id:
            messagebox.showwarning("Внимание", "Выберите пациента!")
            return

        history = get_patient_history(self.current_patient_id)

        if not history:
            messagebox.showinfo("Информация", "Нет сохранённых анализов")
            return

        hist_window = tk.Toplevel(self.root)
        hist_window.title("История анализов")
        hist_window.geometry("1000x500")

        frame = tk.Frame(hist_window)
        frame.pack(fill="both", expand=True)

        columns = ("Дата", "HGB", "RBC", "WBC", "PLT", "MCV", "Диагноз")
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)

        col_widths = [180, 80, 80, 80, 80, 80, 350]
        for col, width in zip(columns, col_widths):
            tree.heading(col, text=col)
            tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for row in history:
            tree.insert("", "end", values=row)

        tk.Button(hist_window, text="Экспорт в Excel",
                  command=lambda: self.export_history_to_excel(history),
                  bg="#4CAF50", fg="white").pack(pady=5)

    def export_history_to_excel(self, history):
        """Экспорт истории в Excel"""
        df = pd.DataFrame(history, columns=["Дата", "HGB", "RBC", "WBC", "PLT", "MCV", "Диагноз"])
        filepath = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")])
        if filepath:
            df.to_excel(filepath, index=False)
            messagebox.showinfo("Успех", f"История сохранена в {filepath}")

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

        gender = self.patient_info_label.cget("text")
        if "Пол: M" in gender:
            gender = "M"
        elif "Пол: F" in gender:
            gender = "F"
        else:
            gender = "M"

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